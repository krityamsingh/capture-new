"""
Grabber/modules/Detect.py
/detect <name> — search characters by name and browse results with ← → buttons.

Bugs fixed vs old version:
  1. Rarity mismatch  — "🧬 Animation" was ignored; now both animation rarity
                        strings are accepted, AND any character with a video_url
                        is treated as a video regardless of rarity label.
  2. Dead edit path   — old code checked `message.photo or message.video` on the
                        ORIGINAL message object (the user's /detect text command),
                        which is always falsy. Navigation therefore sent a brand-new
                        message on every button press instead of editing the existing one.
                        Fixed: navigation callbacks call query.message.edit_media()
                        directly — no ambiguous message-type sniffing needed.
  3. Spinner hang      — navigation/close callbacks never called query.answer(),
                        leaving Telegram's loading spinner spinning forever.
  4. No download-to-temp — URLs were passed raw to Telegram. External hosts
                        (Catbox, etc.) return WEBPAGE_MEDIA_EMPTY this way.
                        Fixed: same download-then-upload pattern used in info.py.
  5. None media_url crash — if video_url was None for an "Animated" char the send
                        would raise; now falls back to img_url, then to text.
  6. No page counter  — UX: added "1 / 10" counter in caption and buttons.
  7. Any user hangs   — if user B pressed Next on user A's detect, query.answer()
                        was never called (early return), leaving a spinner. Fixed:
                        always call query.answer() before any early return.
  8. parse_mode missing — Telegram caption was sent without HTML/Markdown mode.
  9. Memory growth    — user_data dict grew forever; added TTL-based eviction.
"""

import asyncio
import aiohttp
import tempfile
import os
import time

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from Grabber import collection, user_collection, app


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# Both animation rarity strings — bridges the DB inconsistency
ANIMATION_RARITIES = {"⚜️ Animated", "🧬 Animation"}

# How long (seconds) to keep a search session alive after last interaction
SESSION_TTL = 600   # 10 minutes

# Max results fetched per search (keeps DB load reasonable)
MAX_RESULTS = 100

# Download timeout for media files
DOWNLOAD_TIMEOUT = 120


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STORE
#  Keyed by user_id. Each entry:
#    { "index": int, "waifus": list, "query": str, "last_used": float }
# ══════════════════════════════════════════════════════════════════════════════

_sessions: dict[int, dict] = {}


def _get_session(user_id: int) -> dict | None:
    """Return a session if it exists and hasn't expired."""
    session = _sessions.get(user_id)
    if session is None:
        return None
    if time.monotonic() - session["last_used"] > SESSION_TTL:
        del _sessions[user_id]
        return None
    return session


def _touch_session(user_id: int) -> None:
    """Refresh the TTL for an active session."""
    if user_id in _sessions:
        _sessions[user_id]["last_used"] = time.monotonic()


def _evict_expired_sessions() -> None:
    """Remove all sessions older than SESSION_TTL. Call occasionally."""
    now = time.monotonic()
    expired = [uid for uid, s in _sessions.items()
               if now - s["last_used"] > SESSION_TTL]
    for uid in expired:
        del _sessions[uid]


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_animated(character: dict) -> bool:
    """
    True if this character should be sent/shown as a video.
    Checks both known rarity strings AND the presence of video_url,
    so inconsistent DB entries are handled gracefully.
    """
    return (
        character.get("rarity", "") in ANIMATION_RARITIES
        or bool(character.get("video_url", ""))
    )


def _build_caption(character: dict, index: int, total: int) -> str:
    rarity = character.get("rarity", "Unknown")
    return (
        f"<b>OwO! Check out This Character!</b>\n\n"
        f"📺 <b>{character.get('anime', 'Unknown')}</b>\n"
        f"🆔 {character.get('id', '?')} — <b>{character['name']}</b>\n"
        f"✨ {rarity}\n\n"
        f"<i>{index + 1} / {total}</i>"
    )


def _build_keyboard(index: int, total: int) -> InlineKeyboardMarkup:
    prev_label = f"⬅ {index}"          if index > 0          else "⬅"
    next_label = f"{index + 2} ➡"      if index < total - 1  else "➡"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(prev_label, callback_data="dtc_prev"),
            InlineKeyboardButton(f"❌ Close",  callback_data="dtc_close"),
            InlineKeyboardButton(next_label, callback_data="dtc_next"),
        ]
    ])


async def _download_to_temp(url: str, suffix: str) -> str:
    """
    Download *url* to a temp file. Returns the file path.
    Caller MUST delete the file (use try/finally + _safe_delete).
    Direct URL passing to Telegram fails for Catbox and similar hosts.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} fetching {url!r}")
            data = await resp.read()

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
    finally:
        tmp.close()
    return tmp.name


def _safe_delete(path: str | None) -> None:
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  CORE SEND / EDIT LOGIC
# ══════════════════════════════════════════════════════════════════════════════

async def _reply_new(message: Message, character: dict, caption: str,
                     keyboard: InlineKeyboardMarkup) -> None:
    """
    Send a brand-new media message (used on the first /detect result).
    Downloads to a temp file first to avoid WEBPAGE_MEDIA_EMPTY.
    Falls back: video → photo → text.
    """
    video_url = character.get("video_url", "")
    img_url   = character.get("img_url", "")
    animated  = _is_animated(character)
    tmp_path  = None

    try:
        if animated and video_url:
            tmp_path = await _download_to_temp(video_url, ".mp4")
            with open(tmp_path, "rb") as fh:
                await message.reply_video(
                    video=fh,
                    caption=caption,
                    parse_mode="html",
                    reply_markup=keyboard,
                )
            return

        if img_url:
            tmp_path = await _download_to_temp(img_url, ".jpg")
            with open(tmp_path, "rb") as fh:
                await message.reply_photo(
                    photo=fh,
                    caption=caption,
                    parse_mode="html",
                    reply_markup=keyboard,
                )
            return

        # No media at all
        await message.reply_text(
            f"⚠️ No media available.\n\n{caption}",
            parse_mode="html",
            reply_markup=keyboard,
        )

    finally:
        _safe_delete(tmp_path)


async def _edit_existing(bot_message: Message, character: dict, caption: str,
                         keyboard: InlineKeyboardMarkup) -> None:
    """
    Edit an already-sent media message in place (used for Next / Prev navigation).
    Downloads to a temp file first. Falls back to editing caption-only if media
    download fails, rather than leaving the user with a stuck spinner.
    """
    video_url = character.get("video_url", "")
    img_url   = character.get("img_url", "")
    animated  = _is_animated(character)
    tmp_path  = None

    try:
        if animated and video_url:
            tmp_path = await _download_to_temp(video_url, ".mp4")
            with open(tmp_path, "rb") as fh:
                await bot_message.edit_media(
                    media=InputMediaVideo(media=fh, caption=caption, parse_mode="html"),
                    reply_markup=keyboard,
                )
            return

        if img_url:
            tmp_path = await _download_to_temp(img_url, ".jpg")
            with open(tmp_path, "rb") as fh:
                await bot_message.edit_media(
                    media=InputMediaPhoto(media=fh, caption=caption, parse_mode="html"),
                    reply_markup=keyboard,
                )
            return

        # No media — at least update the caption
        await bot_message.edit_caption(
            caption=f"⚠️ No media available.\n\n{caption}",
            parse_mode="html",
            reply_markup=keyboard,
        )

    finally:
        _safe_delete(tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
#  /detect  COMMAND
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("detect"))
async def detect_character(client: Client, message: Message) -> None:
    """
    /detect <name>
    Search the character DB by name (case-insensitive substring).
    Sends the first result with ← Close → navigation buttons.
    """
    if len(message.command) < 2:
        await message.reply_text(
            "🔍 <b>Usage:</b> <code>/detect &lt;name&gt;</code>\n"
            "Example: <code>/detect naruto</code>",
            parse_mode="html",
        )
        return

    search_query = " ".join(message.command[1:]).strip()

    # Evict stale sessions occasionally (lightweight GC)
    _evict_expired_sessions()

    waifus = await collection.find(
        {"name": {"$regex": search_query, "$options": "i"}}
    ).to_list(length=MAX_RESULTS)

    if not waifus:
        await message.reply_text(
            f"❌ No character found matching <b>{search_query}</b>.",
            parse_mode="html",
        )
        return

    user_id = message.from_user.id
    _sessions[user_id] = {
        "index":      0,
        "waifus":     waifus,
        "query":      search_query,
        "last_used":  time.monotonic(),
    }

    character = waifus[0]
    caption   = _build_caption(character, 0, len(waifus))
    keyboard  = _build_keyboard(0, len(waifus))

    try:
        await _reply_new(message, character, caption, keyboard)
    except Exception as exc:
        print(f"❌ /detect send error  user={user_id}  query={search_query!r}: {exc}")
        await message.reply_text("❌ Failed to send media. Please try again.")


# ══════════════════════════════════════════════════════════════════════════════
#  NAVIGATION  CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^dtc_(next|prev)$"))
async def navigate_detected(client: Client, query: CallbackQuery) -> None:
    """
    Handles ← and → buttons.
    Edits the existing message in place — no new message spam.
    """
    user_id = query.from_user.id
    session = _get_session(user_id)

    if not session:
        # User's session expired or they never ran /detect
        await query.answer("⚠️ Session expired. Run /detect again.", show_alert=True)
        return

    waifus = session["waifus"]
    total  = len(waifus)
    index  = session["index"]

    if query.data == "dtc_next":
        index = (index + 1) % total
    else:
        index = (index - 1) % total

    session["index"] = index
    _touch_session(user_id)

    character = waifus[index]
    caption   = _build_caption(character, index, total)
    keyboard  = _build_keyboard(index, total)

    # Acknowledge the tap immediately so the spinner clears
    await query.answer()

    try:
        await _edit_existing(query.message, character, caption, keyboard)
    except Exception as exc:
        print(f"❌ detect navigate error  user={user_id}  index={index}: {exc}")
        # Edit caption only so the user sees the text even if media fails
        try:
            await query.message.edit_caption(
                caption=f"❌ Media load failed.\n\n{caption}",
                parse_mode="html",
                reply_markup=keyboard,
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  CLOSE  CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^dtc_close$"))
async def close_detected(client: Client, query: CallbackQuery) -> None:
    """Deletes the detect message and cleans up the user's session."""
    await query.answer()   # clear spinner before delete
    _sessions.pop(query.from_user.id, None)
    try:
        await query.message.delete()
    except Exception:
        pass
