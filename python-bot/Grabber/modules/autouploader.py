"""
autouploader.py
===============
COMMANDS (Owner only):
  /add <user_id>        — Grant upload access
  /removeuploader       — Revoke upload access
  /listuploader         — List all uploaders

COMMANDS (Owner + Uploaders):
  /upload               — Reply to photo/mp4:
                          /upload <anime> | <char> | <rarity_no>
                          /upload <anime> - <char> - <rarity_no>
  /il <rarity_no>       — Reply to any spawn, auto-detects name & anime (10 patterns)
  /uchar media  <id>    — Reply to new photo/mp4 → updates DB + edits channel post
  /uchar rarity <id> <rarity_no>  → updates DB + edits channel post
  /uchar name   <id> <new name>   → updates DB + edits channel post
  /uchar anime  <id> <new anime>  → updates DB + edits channel post
"""

import asyncio
import os
import re
import shutil
import tempfile
import random
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified

from Grabber import db, collection
from Grabber.config import OWNER_IDS, CATBOX_USERHASH
from . import app


# ── Channels ──────────────────────────────────────────────────────────────────
UPLOAD_CHANNEL_ID = -1002672414862
UPLOAD_GC_ID      = -1002313549356

# ── DB ────────────────────────────────────────────────────────────────────────
sequences_db   = db.sequences
collection_ref = collection
uploaders_db   = db.uploaders

# ── Rarity map ────────────────────────────────────────────────────────────────
RARITY_MAP = {
    1:  "🔴 Common",
    2:  "🔵 Uncommon",
    3:  "🟠 Rare",
    4:  "🟡 Legendary",
    5:  "⚪ Epic",
    6:  "🔮 Limited Edition",
    7:  "🫧 Premium",
    8:  "🏵️ Exotic",
    9:  "⚜️ Animated",
    10: "🌼 Celebrity",
    11: "🎐 Crystal",
    12: "🍹 Neon",
    13: "🧿 Supreme",
    14: "⚡ Thundra",
    15: "🛸 Galvoria",
    16: "🌟 Solar Verse",
}
ANIMATED_RARITY  = "⚜️ Animated"
RARITY_LIST_TEXT = "\n".join(f"`{k:>2}` {v}" for k, v in RARITY_MAP.items())


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD QUEUE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class UploadJob:
    file_path:  str
    chat_id:    int
    char_name:  str
    anime:      str
    rarity:     str
    mention:    str
    is_video:   bool
    notify_msg: Message
    position:   int   = 0
    queued_at:  float = field(default_factory=time.time)


_upload_queue:   asyncio.Queue       = asyncio.Queue()
_queue_list:     List[UploadJob]     = []
_worker_running: bool                = False
_current_job:    Optional[UploadJob] = None


async def _queue_worker(client: Client):
    global _worker_running, _current_job, _queue_list
    _worker_running = True
    while True:
        try:
            job: UploadJob = await asyncio.wait_for(_upload_queue.get(), timeout=30)
        except asyncio.TimeoutError:
            if _upload_queue.empty():
                _worker_running = False
                _current_job    = None
                return
            continue
        _current_job = job
        if job in _queue_list:
            _queue_list.remove(job)
        try:
            await _process_job(client, job)
        except Exception as e:
            try:
                await job.notify_msg.reply_text(
                    f"❌ Upload failed for `{job.char_name}`\n`{e}`"
                )
            except Exception:
                pass
        finally:
            _current_job = None
            _upload_queue.task_done()


def _ensure_worker(client: Client):
    global _worker_running
    if not _worker_running:
        asyncio.get_event_loop().create_task(_queue_worker(client))
        _worker_running = True


async def _enqueue(client: Client, job: UploadJob) -> int:
    _queue_list.append(job)
    pos = len(_queue_list)
    job.position = pos
    await _upload_queue.put(job)
    _ensure_worker(client)
    return pos


# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS  — screenshot-style card UI
# ══════════════════════════════════════════════════════════════════════════════

def _bar(pct: int, width: int = 20) -> str:
    filled = round(width * pct / 100)
    return "▓" * filled + "░" * (width - filled)


def _size_fmt(kb: float) -> str:
    return f"{kb / 1024:.2f} MB" if kb >= 1024 else f"{kb:.1f} KB"


def _eta(elapsed: float, pct: int) -> str:
    if pct < 3:
        return "–"
    rem = elapsed / pct * (100 - pct)
    return f"{int(rem)}s" if rem < 60 else f"{rem / 60:.1f}m"


def _progress_msg(
    step: int,
    char_name: str,
    rarity: str,
    pct: int,
    size_kb: float,
    done_kb: float = 0,
    speed: str = "",
    elapsed: float = 0,
    extra: str = "",
) -> str:
    step_labels = {
        1: "📥 Fetching Media",
        2: "☁️ Uploading to Catbox",
        3: "💾 Saving to Database",
        4: "📢 Publishing to Channels",
    }
    media_type = "Video" if "⚜️" in rarity else "Image"

    lines = [
        f"**{step_labels.get(step, 'Processing...')}**",
        f"",
        f"🆔 **ID**            `Generating...`",
        f"🗂 **Media Type**    `{media_type}`",
        f"🎭 **Name**          `{char_name}`",
        f"⭐ **Rarity**        `{rarity}`",
        f"☁️ **Upload To**     `Catbox`",
    ]

    if size_kb > 0:
        lines.append(f"📦 **Size**          `{_size_fmt(done_kb)} / {_size_fmt(size_kb)}`")
    if speed:
        lines.append(f"⚡ **Speed**         `{speed}`")
    if elapsed > 0 and pct > 0:
        lines.append(f"⏱ **ETA**           `{_eta(elapsed, pct)}`")

    lines += [
        f"",
        f"`{_bar(pct)}` **{pct}%**",
    ]

    if extra:
        lines += ["", extra]

    return "\n".join(lines)


def _done_msg(
    char_name: str, anime: str, rarity: str,
    price: int, char_id: str, img_url: str, is_video: bool,
    uploader_mention: str = "",
    queue_next: str = "",
) -> str:
    media_type = "Video" if is_video else "Image"
    icon = "🎬" if is_video else "🖼"

    lines = [
        f"✅ **Upload Complete**",
        f"",
        f"🆔 **ID**            `{char_id}`",
        f"🗂 **Media Type**    `{media_type}`",
        f"🎭 **Name**          `{char_name}`",
        f"📺 **Anime**         `{anime}`",
        f"⭐ **Rarity**        `{rarity}`",
        f"💰 **Price**         `{price:,} coins`",
        f"☁️ **Uploaded To**   `Catbox`",
        f"👤 **By**            {uploader_mention}",
        f"{icon} **URL**           [View File]({img_url})",
        f"",
        f"`{'▓' * 20}` **100%**",
        f"",
        f"🟢 **Live in both channels**",
    ]

    if queue_next:
        lines += ["", f"⏭ **Next in Queue:** `{queue_next}`"]

    return "\n".join(lines)


def _queue_card(
    char_name: str, anime: str, rarity: str,
    pos: int, total: int, queue_lines: List[str],
    current_job_name: str = "",
) -> str:
    media_type = "Video" if "⚜️" in rarity else "Image"

    lines = [
        f"📋 **Queued Successfully**",
        f"",
        f"🎭 **Name**          `{char_name}`",
        f"📺 **Anime**         `{anime}`",
        f"⭐ **Rarity**        `{rarity}`",
        f"🗂 **Media Type**    `{media_type}`",
        f"",
        f"📊 **Position**      `#{pos} of {total} in queue`",
    ]

    if current_job_name:
        lines.append(f"🔄 **Now uploading** `{current_job_name}`")

    if queue_lines:
        lines += ["", "**Queue:**"]
        lines += queue_lines

    lines += [
        "",
        "⏳ _Starts automatically after current upload._",
    ]
    return "\n".join(lines)


# ── Rate-limited caption editor ───────────────────────────────────────────────
# Telegram allows ~20 edits/min per message → 3s gap is safe and fast
_edit_last: Dict[int, float] = {}
_EDIT_GAP = 3.0


async def _sedit(msg: Message, text: str):
    now = time.time()
    gap = _EDIT_GAP - (now - _edit_last.get(msg.id, 0))
    if gap > 0:
        await asyncio.sleep(gap)
    for _ in range(3):
        try:
            await msg.edit_caption(text)
            _edit_last[msg.id] = time.time()
            return
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except MessageNotModified:
            return
        except Exception:
            return


async def _sedit_text(msg: Message, text: str):
    now = time.time()
    gap = _EDIT_GAP - (now - _edit_last.get(msg.id, 0))
    if gap > 0:
        await asyncio.sleep(gap)
    for _ in range(3):
        try:
            await msg.edit_text(text)
            _edit_last[msg.id] = time.time()
            return
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception:
            return


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "*/*",
    "Connection": "keep-alive",
}


def _catbox_post(path: str, retries: int = 5) -> str:
    for attempt in range(retries):
        try:
            with requests.Session() as s:
                s.headers.update(_HEADERS)
                with open(path, "rb") as fh:
                    r = s.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload", "userhash": CATBOX_USERHASH},
                        files={"fileToUpload": fh},
                        timeout=(10, 120),
                    )
                if r.status_code == 200 and r.text.strip().startswith("https://"):
                    return r.text.strip()
                raise RuntimeError(f"Bad response: {r.text[:80]}")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise RuntimeError(f"Catbox upload failed ({retries} attempts): {e}")


def _catbox_dl(url: str, dest: str, retries: int = 5):
    for attempt in range(retries):
        try:
            with requests.Session() as s:
                s.headers.update(_HEADERS)
                r = s.get(url, timeout=(10, 90), stream=True)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                return
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise RuntimeError(f"Catbox download failed ({retries} attempts): {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def _next_id() -> str:
    docs     = await collection_ref.find({"id": {"$exists": True}}, {"id": 1}).to_list(None)
    existing = [int(c["id"]) for c in docs if str(c.get("id", "")).isdigit()]
    db_max   = max(existing) if existing else 0
    seq      = await sequences_db.find_one({"_id": "character_id"})
    seq_val  = seq["sequence_value"] if seq else 0
    nxt      = max(db_max, seq_val) + 1
    await sequences_db.update_one(
        {"_id": "character_id"}, {"$set": {"sequence_value": nxt}}, upsert=True
    )
    return str(nxt).zfill(2)


def _build_channel_caption(
    char_name: str, anime: str, rarity: str,
    price: int, char_id: str, mention: str,
) -> str:
    return (
        f"✨ **New Character Added!**\n\n"
        f"🎭 **Name**   {char_name}\n"
        f"📺 **Anime**  {anime}\n"
        f"⭐ **Rarity** {rarity}\n"
        f"💰 **Price**  {price:,} coins\n"
        f"🆔 **ID**     `{char_id}`\n"
        f"👤 **By**     {mention}"
    )


async def _edit_channel_post(client: Client, char_id: str) -> Optional[str]:
    char = await collection_ref.find_one({"id": char_id})
    if not char:
        return f"Character `{char_id}` not found in DB"

    msg_id = char.get("message_id")
    if not msg_id:
        return "No message_id stored — channel post cannot be edited (old upload)"

    mention     = char.get("mention") or "unknown"
    new_caption = _build_channel_caption(
        char["name"], char["anime"], char["rarity"],
        char.get("price", 0), char["id"], mention,
    )

    last_err = None
    for chat_id in (UPLOAD_CHANNEL_ID, UPLOAD_GC_ID):
        try:
            await client.edit_message_caption(
                chat_id=chat_id, message_id=msg_id, caption=new_caption
            )
        except MessageNotModified:
            pass
        except Exception as e:
            last_err = str(e)

    return last_err


# ══════════════════════════════════════════════════════════════════════════════
#  CATBOX UPLOAD — animated progress
# ══════════════════════════════════════════════════════════════════════════════

async def _catbox_upload(
    file_path:   str,
    chat_id:     int,
    client:      Client,
    char_name:   str,
    rarity:      str,
    preview_msg: Message,
    is_video:    bool = False,
) -> tuple:
    """
    Uploads file to Catbox with animated plain-text progress card.
    No image/video shown during progress — clean text card only.
    Returns (catbox_url, progress_msg).
    """
    size_kb = os.path.getsize(file_path) / 1024

    await _sedit_text(preview_msg, _progress_msg(2, char_name, rarity, 0, size_kb))
    _edit_last[preview_msg.id] = time.time()
    progress_msg = preview_msg

    # Upload — no edits until done
    result: dict = {"url": None, "err": None}
    loop = asyncio.get_event_loop()
    try:
        result["url"] = await loop.run_in_executor(None, lambda: _catbox_post(file_path))
    except Exception as e:
        result["err"] = str(e)

    if result["err"]:
        raise RuntimeError(result["err"])

    return result["url"], progress_msg


# ══════════════════════════════════════════════════════════════════════════════
#  JOB PROCESSOR
# ══════════════════════════════════════════════════════════════════════════════

async def _process_job(client: Client, job: UploadJob):
    try:
        preview = await job.notify_msg.reply_text(
            f"⏳ Starting upload for `{job.char_name}`…"
        )

        img_url, progress_msg = await _catbox_upload(
            job.file_path, job.chat_id, client,
            job.char_name, job.rarity, preview, job.is_video
        )

        char_id = await _next_id()
        price   = random.randint(60_000, 80_000)
        char_doc = {
            "img_url":  img_url,
            "name":     job.char_name,
            "anime":    job.anime,
            "rarity":   job.rarity,
            "price":    price,
            "id":       char_id,
            "mention":  job.mention,
        }
        await collection_ref.insert_one(char_doc)

        pub_caption = _build_channel_caption(
            job.char_name, job.anime, job.rarity,
            price, char_id, job.mention,
        )

        if job.is_video:
            sent = await client.send_video(
                chat_id=UPLOAD_CHANNEL_ID, video=job.file_path, caption=pub_caption
            )
            char_doc["message_id"] = sent.id
            await collection_ref.update_one({"id": char_id}, {"$set": {"message_id": sent.id}})
            try:
                await client.send_video(chat_id=UPLOAD_GC_ID, video=job.file_path, caption=pub_caption)
            except Exception:
                pass
        else:
            sent = await client.send_photo(
                chat_id=UPLOAD_CHANNEL_ID, photo=job.file_path, caption=pub_caption
            )
            char_doc["message_id"] = sent.id
            await collection_ref.update_one({"id": char_id}, {"$set": {"message_id": sent.id}})
            try:
                await client.send_photo(chat_id=UPLOAD_GC_ID, photo=job.file_path, caption=pub_caption)
            except Exception:
                pass

        next_name = _queue_list[0].char_name if _queue_list else ""
        await _sedit_text(progress_msg, _done_msg(
            job.char_name, job.anime, job.rarity,
            price, char_id, img_url, job.is_video,
            uploader_mention=job.mention,
            queue_next=next_name,
        ))

    finally:
        try:
            os.unlink(job.file_path)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  MEDIA DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _get_media(reply: Message):
    if reply.video:
        return reply.video, True
    if reply.document and reply.document.mime_type == "video/mp4":
        return reply.document, True
    if reply.photo:
        return reply.photo, False
    if reply.document:
        return reply.document, False
    return None, False


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD FORMAT PARSER  — supports | and - separators
# ══════════════════════════════════════════════════════════════════════════════

def _parse_upload_args(raw: str):
    """
    Parses upload arguments supporting two formats:
      Format 1: anime | character | rarity_no
      Format 2: anime - character - rarity_no

    Returns (anime, char_name, rarity_no_str) or None if invalid.
    Pipe takes priority; dash is only used as separator if no pipe found.
    """
    raw = raw.strip()

    # Format 1 — pipe separator
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        return None

    # Format 2 — dash separator (split on " - " with spaces to avoid breaking names)
    if " - " in raw:
        parts = [p.strip() for p in raw.split(" - ")]
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        return None

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

_uploader_cache: Optional[set] = None


async def _get_uploaders() -> set:
    global _uploader_cache
    if _uploader_cache is None:
        docs            = await uploaders_db.find({}).to_list(length=None)
        _uploader_cache = {int(d["user_id"]) for d in docs}
    return _uploader_cache


async def _is_uploader(uid: int) -> bool:
    return uid in OWNER_IDS or uid in await _get_uploaders()


def _is_owner(_, __, m: Message) -> bool:
    return bool(m.from_user and m.from_user.id in OWNER_IDS)


async def _is_uploader_filter(_, __, m: Message) -> bool:
    return bool(m.from_user) and await _is_uploader(m.from_user.id)


owner_filter    = filters.create(_is_owner)
uploader_filter = filters.create(_is_uploader_filter)


# ══════════════════════════════════════════════════════════════════════════════
#  HELP STRINGS
# ══════════════════════════════════════════════════════════════════════════════

HELP_UPLOAD = (
    "❌ **Wrong format!**\n\n"
    "Reply to a **photo or mp4**, then use one of:\n\n"
    "**Format 1 — Pipe separator:**\n"
    "`/upload <anime> | <character> | <rarity_no>`\n\n"
    "**Format 2 — Dash separator:**\n"
    "`/upload <anime> - <character> - <rarity_no>`\n\n"
    "📌 mp4 → rarity auto-set to ⚜️ Animated\n\n"
    "**Examples:**\n"
    "`/upload One Punch Man | Fubuki | 3`\n"
    "`/upload One Punch Man - Fubuki - 3`\n\n"
    f"**Rarities:**\n{RARITY_LIST_TEXT}"
)

HELP_IL = (
    "❌ **Wrong format!**\n\n"
    "Reply to a **character photo/video**, then:\n"
    "`/il <rarity_no>`\n\n"
    "Name & anime are **auto-detected** from caption.\n"
    "mp4 → rarity auto-set to ⚜️ Animated\n\n"
    f"**Rarities:**\n{RARITY_LIST_TEXT}"
)

HELP_UCHAR = (
    "❌ **Wrong format!**\n\n"
    "`/uchar media  <id>` — reply to new photo/mp4\n"
    "`/uchar rarity <id> <no>`\n"
    "`/uchar name   <id> <new name>`\n"
    "`/uchar anime  <id> <new anime>`\n\n"
    "All changes also update the channel post automatically."
)


# ══════════════════════════════════════════════════════════════════════════════
#  IL AUTO-EXTRACTION  — 10 patterns
# ══════════════════════════════════════════════════════════════════════════════

_IL_PATTERNS = [
    re.compile(
        r"(?:OwO[^\n]*\n+)?(?P<anime>[^\n]+)\n\d+\s*:\s*(?P<n>[^\n]+)",
        re.I | re.S,
    ),
    re.compile(
        r"[Nn]ame\s*[:=]\s*(?P<n>[^\n]+)\n.*?[Aa]nime\s*[:=]\s*(?P<anime>[^\n]+)",
        re.S,
    ),
    re.compile(
        r"[Aa]nime\s*[:=]\s*(?P<anime>[^\n]+)\n.*?[Nn]ame\s*[:=]\s*(?P<n>[^\n]+)",
        re.S,
    ),
    re.compile(
        r"[Cc]har(?:acter)?\s*[:=]\s*(?P<n>[^\n]+)\n.*?(?:[Ss]eries|[Ss]how|[Ss]ource)\s*[:=]\s*(?P<anime>[^\n]+)",
        re.S,
    ),
    re.compile(r"^(?P<a>[^|\n]{2,40})\s*\|\s*(?P<b>[^|\n]{2,60})$", re.M),
    re.compile(
        r"[Ff]rom\s*[:=]\s*(?P<anime>[^\n]+)\n.*?[Cc]har(?:acter)?\s*[:=]\s*(?P<n>[^\n]+)",
        re.S,
    ),
    re.compile(r"(?:[Tt]itle\s*:\s*)?(?P<n>[^\n(]{2,40})\s*\((?P<anime>[^)]{2,60})\)"),
    re.compile(r"\*\*(?P<n>[^*\n]{2,40})\*\*\s*\n\s*\*\*(?P<anime>[^*\n]{2,60})\*\*"),
    re.compile(r"^(?P<n>[^\n—–]{2,40})\s*[—–]\s*(?P<anime>[^\n]{2,60})$", re.M),
    re.compile(r"^(?P<n>[^\n]{2,40})\n(?P<anime>[^\n]{2,60})$", re.M),
]

_POPULAR_ANIME = {
    "naruto", "one piece", "bleach", "dragon ball", "my hero academia",
    "attack on titan", "demon slayer", "jujutsu kaisen", "one punch man",
    "tokyo ghoul", "sword art online", "fate", "code geass", "steins gate",
    "mob psycho", "vinland saga", "chainsaw man", "spy x family", "wind breaker",
    "black clover", "fairy tail", "hunter x hunter", "fullmetal alchemist",
    "re zero", "overlord", "konosuba", "danmachi", "fire force", "blue lock",
    "haikyuu", "kuroko no basket", "death note", "evangelion", "cowboy bebop",
    "trigun", "inuyasha", "soul eater", "noragami", "the promised neverland",
    "your lie in april", "anohana", "clannad", "toradora",
    "rising of the shield hero", "that time i got reincarnated", "tensura",
    "black butler", "ouran", "fruits basket", "vampire knight",
}

_ANIME_KEYWORDS = {
    "saga", "season", "arc", "legend", "chronicle", "story", "tale",
    "adventure", "quest", "journey", "war", "battle", "part", "zero",
    "online", "force", "hero", "king", "world", "no", "academy",
    "shippuden", "kai", "super", "ultimate", "returns", "reborn",
}


def _looks_like_anime(t: str) -> bool:
    tl = t.lower().strip()
    if any(a in tl for a in _POPULAR_ANIME):
        return True
    words = set(re.findall(r"\w+", tl))
    return bool(_ANIME_KEYWORDS & words)


def _clean(s: str) -> str:
    s = re.sub(r"\*+", "", s)
    s = re.sub(r"[^\w\s'-]", " ", s)
    return " ".join(s.split()).title()


def _strip_noise(s: str) -> str:
    s = re.split(r"RARITY|rarity|🔴|🔵|🟠|🟡|⚪|🔮|🫧|🏵|⚜|🌼|🎐|🍹|🧿|⚡|🛸|🌟", s)[0]
    s = re.sub(r"^\d+\s*[:.]\s*", "", s.strip())
    return s.strip()


def _extract_il(text: str):
    text = text.strip()
    for i, pat in enumerate(_IL_PATTERNS):
        m = pat.search(text)
        if not m:
            continue
        gd = m.groupdict()

        if "a" in gd and "b" in gd:
            a = _strip_noise(gd["a"].strip())
            b = _strip_noise(gd["b"].strip())
            if not a or not b:
                continue
            if _looks_like_anime(a):
                return _clean(b), _clean(a)
            return _clean(a), _clean(b)

        raw_name  = _strip_noise(gd.get("n", "").strip())
        raw_anime = _strip_noise(gd.get("anime", "").strip())
        raw_name  = re.split(r"\n", raw_name)[0].strip()
        raw_anime = re.split(r"\n", raw_anime)[0].strip()

        if raw_name and raw_anime and len(raw_name) > 1 and len(raw_anime) > 1:
            return _clean(raw_name), _clean(raw_anime)

    lines = []
    for ln in text.splitlines():
        ln = _strip_noise(ln.strip())
        if len(ln) > 2 and not ln.startswith("/"):
            lines.append(ln)
    if len(lines) >= 2:
        a, b = lines[0], lines[1]
        if _looks_like_anime(a):
            return _clean(b), _clean(a)
        return _clean(a), _clean(b)
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED ENQUEUE HELPER
# ══════════════════════════════════════════════════════════════════════════════

async def _do_enqueue(
    client: Client, message: Message, reply: Message,
    char_name: str, anime: str, rarity: str, is_video: bool,
):
    uploader = message.from_user
    mention  = f"[{uploader.first_name}](tg://user?id={uploader.id})"
    suffix   = ".mp4" if is_video else ".jpg"
    media, _ = _get_media(reply)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        dl_path = tmp.name

    dl_msg = await message.reply_text(f"⬇️ Downloading `{char_name}`…")
    try:
        await client.download_media(media, file_name=dl_path)
    except Exception as e:
        await dl_msg.edit_text(f"❌ Download failed: `{e}`")
        try:
            os.unlink(dl_path)
        except OSError:
            pass
        return
    await dl_msg.delete()

    job = UploadJob(
        file_path=dl_path, chat_id=message.chat.id,
        char_name=char_name, anime=anime, rarity=rarity,
        mention=mention, is_video=is_video, notify_msg=message,
    )

    pos         = await _enqueue(client, job)
    queue_total = _upload_queue.qsize() + (1 if _current_job else 0)

    if pos == 1 and not _current_job:
        return

    queue_lines = []
    for idx, j in enumerate(_queue_list, 1):
        marker = "▶️" if idx == 1 else f"`{idx}.`"
        queue_lines.append(f"{marker} `{j.char_name}` · {j.rarity}")

    current_name = _current_job.char_name if _current_job else ""

    await message.reply_text(_queue_card(
        char_name, anime, rarity,
        pos, queue_total, queue_lines,
        current_job_name=current_name,
    ))


# ══════════════════════════════════════════════════════════════════════════════
#  /upload  — supports | and - formats
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("upload") & uploader_filter)
async def upload_cmd(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply:
        return await message.reply_text(HELP_UPLOAD)
    media, is_video = _get_media(reply)
    if not media:
        return await message.reply_text(HELP_UPLOAD)

    raw = message.text.split(None, 1)
    if len(raw) < 2:
        return await message.reply_text(HELP_UPLOAD)

    parsed = _parse_upload_args(raw[1])
    if not parsed:
        return await message.reply_text(HELP_UPLOAD)

    anime, char_name, rarity_raw = parsed

    if not anime or not char_name:
        return await message.reply_text(HELP_UPLOAD)

    if not rarity_raw.isdigit() or int(rarity_raw) not in RARITY_MAP:
        return await message.reply_text(HELP_UPLOAD)

    rarity = ANIMATED_RARITY if is_video else RARITY_MAP[int(rarity_raw)]
    await _do_enqueue(client, message, reply, char_name, anime, rarity, is_video)


# ══════════════════════════════════════════════════════════════════════════════
#  /il
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("il") & uploader_filter)
async def il_cmd(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply:
        return await message.reply_text(HELP_IL)
    media, is_video = _get_media(reply)
    if not media:
        return await message.reply_text(HELP_IL)

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit() or int(args[1]) not in RARITY_MAP:
        return await message.reply_text(HELP_IL)

    rarity           = ANIMATED_RARITY if is_video else RARITY_MAP[int(args[1])]
    caption          = (reply.caption or reply.text or "").strip()
    char_name, anime = _extract_il(caption)

    if not char_name or not anime:
        return await message.reply_text(
            "❌ Could not detect character info from caption.\n\n"
            "Use `/upload` to enter manually."
        )

    await _do_enqueue(client, message, reply, char_name, anime, rarity, is_video)


# ══════════════════════════════════════════════════════════════════════════════
#  /uchar  — update fields + edit channel post
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command(["uchar", "updatechar"]) & uploader_filter)
async def uchar_cmd(client: Client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply_text(HELP_UCHAR)
    sub_raw = args[1].strip()
    sub     = sub_raw.split()[0].lower()

    # ── media ─────────────────────────────────────────────────────────────────
    if sub == "media":
        reply = message.reply_to_message
        if not reply:
            return await message.reply_text("❌ Reply to a photo or mp4 with `/uchar media <id>`")
        media, is_video = _get_media(reply)
        if not media:
            return await message.reply_text("❌ Reply to a photo or mp4 with `/uchar media <id>`")
        parts = sub_raw.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return await message.reply_text("❌ Provide character ID. Example: `/uchar media 42`")

        char_id = parts[1].zfill(2)
        char    = await collection_ref.find_one({"id": char_id})
        if not char:
            return await message.reply_text(f"❌ Character `{char_id}` not found.")

        new_rarity = ANIMATED_RARITY if is_video else char.get("rarity", "?")
        suffix     = ".mp4" if is_video else ".jpg"

        dl_msg = await message.reply_text(f"⬇️ Downloading for `{char.get('name','?')}`…")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        try:
            await client.download_media(media, file_name=tmp_path)
            await dl_msg.delete()

            preview = await message.reply_text("⏳ Uploading…")
            new_url, media_msg = await _catbox_upload(
                tmp_path, message.chat.id, client,
                char.get("name", "?"), new_rarity, preview, is_video,
            )
            update_fields = {"img_url": new_url}
            if is_video:
                update_fields["rarity"] = new_rarity
            await collection_ref.update_one({"id": char_id}, {"$set": update_fields})

            ch_err    = await _edit_channel_post(client, char_id)
            ch_status = "📡 Channel post updated." if not ch_err else f"⚠️ Channel edit: `{ch_err}`"
            icon      = "🎬" if is_video else "🖼"

            await _sedit_text(media_msg,
                f"✅ **Media Updated**\n\n"
                f"🆔 **ID**          `{char_id}`\n"
                f"🎭 **Name**        `{char.get('name','?')}`\n"
                f"⭐ **Rarity**      `{new_rarity}`\n"
                f"☁️ **Uploaded To** `Catbox`\n"
                f"{icon} **URL**         [View File]({new_url})\n\n"
                f"`{'▓' * 20}` **100%**\n\n"
                f"{ch_status}"
            )
        except Exception as e:
            await message.reply_text(f"❌ Failed: `{e}`")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return

    # ── rarity ────────────────────────────────────────────────────────────────
    if sub == "rarity":
        parts = sub_raw.split()
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            return await message.reply_text(
                f"❌ Usage: `/uchar rarity <id> <no>`\n\n{RARITY_LIST_TEXT}"
            )
        char_id    = parts[1].zfill(2)
        new_rarity = RARITY_MAP.get(int(parts[2]))
        if not new_rarity:
            return await message.reply_text(f"❌ Invalid rarity.\n\n{RARITY_LIST_TEXT}")
        char = await collection_ref.find_one({"id": char_id})
        if not char:
            return await message.reply_text(f"❌ Character `{char_id}` not found.")
        old = char.get("rarity", "?")
        await collection_ref.update_one({"id": char_id}, {"$set": {"rarity": new_rarity}})
        ch_err    = await _edit_channel_post(client, char_id)
        ch_status = "📡 Channel post updated." if not ch_err else f"⚠️ Channel edit: `{ch_err}`"
        return await message.reply_text(
            f"✅ **Rarity Updated**\n\n"
            f"🆔 **ID**     `{char_id}`\n"
            f"🎭 **Name**   `{char.get('name','?')}`\n"
            f"⭐ **Old**    `{old}`\n"
            f"⭐ **New**    `{new_rarity}`\n\n"
            f"{ch_status}"
        )

    # ── name ──────────────────────────────────────────────────────────────────
    if sub == "name":
        parts = sub_raw.split(None, 2)
        if len(parts) < 3 or not parts[1].isdigit():
            return await message.reply_text("❌ Usage: `/uchar name <id> <new name>`")
        char_id  = parts[1].zfill(2)
        new_name = parts[2].strip()
        char = await collection_ref.find_one({"id": char_id})
        if not char:
            return await message.reply_text(f"❌ Character `{char_id}` not found.")
        old = char.get("name", "?")
        await collection_ref.update_one({"id": char_id}, {"$set": {"name": new_name}})
        ch_err    = await _edit_channel_post(client, char_id)
        ch_status = "📡 Channel post updated." if not ch_err else f"⚠️ Channel edit: `{ch_err}`"
        return await message.reply_text(
            f"✅ **Name Updated**\n\n"
            f"🆔 **ID**    `{char_id}`\n"
            f"📝 **Old**   `{old}`\n"
            f"📝 **New**   `{new_name}`\n\n"
            f"{ch_status}"
        )

    # ── anime ─────────────────────────────────────────────────────────────────
    if sub == "anime":
        parts = sub_raw.split(None, 2)
        if len(parts) < 3 or not parts[1].isdigit():
            return await message.reply_text("❌ Usage: `/uchar anime <id> <new anime>`")
        char_id   = parts[1].zfill(2)
        new_anime = parts[2].strip()
        char = await collection_ref.find_one({"id": char_id})
        if not char:
            return await message.reply_text(f"❌ Character `{char_id}` not found.")
        old = char.get("anime", "?")
        await collection_ref.update_one({"id": char_id}, {"$set": {"anime": new_anime}})
        ch_err    = await _edit_channel_post(client, char_id)
        ch_status = "📡 Channel post updated." if not ch_err else f"⚠️ Channel edit: `{ch_err}`"
        return await message.reply_text(
            f"✅ **Anime Updated**\n\n"
            f"🆔 **ID**    `{char_id}`\n"
            f"📺 **Old**   `{old}`\n"
            f"📺 **New**   `{new_anime}`\n\n"
            f"{ch_status}"
        )

    await message.reply_text(HELP_UCHAR)


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOADER MANAGEMENT  (Owner only)
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("add") & owner_filter)
async def add_uploader_cmd(client: Client, message: Message):
    tid, tname = None, "Unknown"
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        tid, tname = u.id, u.first_name or str(u.id)
    elif len(message.command) > 1 and message.command[1].isdigit():
        tid, tname = int(message.command[1]), f"User `{message.command[1]}`"
    else:
        return await message.reply_text("❌ Reply to user or `/add <user_id>`")

    if tid in OWNER_IDS:
        return await message.reply_text("ℹ️ That user is already an owner.")
    uploaders = await _get_uploaders()
    if tid in uploaders:
        return await message.reply_text(f"ℹ️ **{tname}** is already an uploader.")
    await uploaders_db.insert_one({"user_id": tid, "added_at": datetime.utcnow()})
    uploaders.add(tid)
    await message.reply_text(
        f"✅ **Uploader Added**\n\n"
        f"👤 **Name**  {tname}\n"
        f"🆔 **ID**    `{tid}`\n\n"
        f"They can now use `/upload`, `/il`, `/uchar`."
    )


@app.on_message(filters.command("removeuploader") & owner_filter)
async def remove_uploader_cmd(client: Client, message: Message):
    tid, tname = None, "Unknown"
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        tid, tname = u.id, u.first_name or str(u.id)
    elif len(message.command) > 1 and message.command[1].isdigit():
        tid, tname = int(message.command[1]), f"User `{message.command[1]}`"
    else:
        return await message.reply_text("❌ Reply to user or `/removeuploader <user_id>`")

    uploaders = await _get_uploaders()
    if tid not in uploaders:
        return await message.reply_text(f"ℹ️ **{tname}** is not an uploader.")
    await uploaders_db.delete_one({"user_id": tid})
    uploaders.discard(tid)
    await message.reply_text(
        f"🗑 **Uploader Removed**\n\n"
        f"👤 **Name**  {tname}\n"
        f"🆔 **ID**    `{tid}`"
    )


@app.on_message(filters.command("listuploader") & owner_filter)
async def list_uploader_cmd(client: Client, message: Message):
    docs = await uploaders_db.find({}).sort("added_at", 1).to_list(length=None)
    if not docs:
        return await message.reply_text("📭 No uploaders yet. Use `/add` to add one.")
    lines = [f"👥 **Uploaders** — `{len(docs)}`\n"]
    for i, doc in enumerate(docs, 1):
        uid  = doc["user_id"]
        dt   = doc.get("added_at")
        date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else "?"
        lines.append(f"`{i}.` `{uid}` · {date}")
    lines.append("\nUse `/removeuploader <id>` to revoke.")
    await message.reply_text("\n".join(lines))
