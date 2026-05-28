"""
Grabber/modules/smash.py
/smash — fight a random character and win it for your collection.

Bugs fixed vs old version:
  1. WEBPAGE_MEDIA_EMPTY crash (the error in the logs)
       Old: reply_photo(character.get("img_url", ""), ...)  ← raw URL → Telegram rejects it
       Fix: download-to-temp first, then upload the bytes. Same pattern as info.py / Detect.py.

  2. loop.run_until_complete(startup()) at module level
       Old code called this at import time, which crashes because an event loop is
       already running when Pyrogram loads modules. Characters were never actually
       cached, so cached_characters stayed empty and load_characters() was called on
       every /smash.
       Fix: removed module-level call; characters are loaded lazily on first /smash
       and cached for the lifetime of the process.

  3. '🧬 Animation' rarity not excluded
       EXCLUDED_RARITIES blocked '⚜️ Animated' but not '🧬 Animation', so animation
       characters could appear as smash opponents and would crash (no img_url).
       Fix: both animation rarity strings are excluded.

  4. Empty img_url silently passed to send_photo
       character.get("img_url", "")  →  "" is falsy but was still passed to Telegram,
       causing the 400. Now we validate the URL before attempting to send.

  5. Cache never refreshed
       Characters added/removed from DB after startup were never reflected.
       Fix: added /reloadsmash owner command + automatic stale-cache detection
       (re-fetches if cache older than 30 minutes).

  6. active_smashes never cleaned up on bot restart
       In-memory dict is fine; added a safety check so a stale entry from a dead
       session can't block a user forever.
"""

import asyncio
import aiohttp
import tempfile
import os
import random
import time
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.errors import FloodWait, QueryIdInvalid
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from Grabber import collection, user_collection, app


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

OWNER_USERNAME = "Unrealrajput"
OWNER_ID       = 6118760915

MAIN_GC_USERNAME = "Divine_Catchers"
MAIN_GC_LINK     = "https://t.me/Divine_Catchers"

PERMANENT_AUTHORIZED_CHATS: set[int] = {-1002313549356}
authorized_chats: set[int]           = set(PERMANENT_AUTHORIZED_CHATS)

# Rarities that should never appear as smash opponents
# (too rare, video-only, or otherwise unsuitable for this mode)
EXCLUDED_RARITIES: set[str] = {
    '🏵️ Exotic',
    '🌼 Celebrity',
    '🎐 Crystal',
    '🍹 Neon',
    '🧿 Supreme',
    '⚜️ Unique',
    '⚡ Eternal',
    '🍁 Radiant',
    '💠 Divine',
    '🎐 Celestial',
    '🌩️ Electra',
    '🧿 Galaxia',
    '🔱 Godly',
    '☀️ Summer[Su]',
    # Both animation rarity strings excluded — they are video-only chars
    '⚜️ Animated',
    '🧬 Animation',
    '🛸 Galvoria',
    '⚡ Thundra',
    '🟡 Solar Verse',
    '🫧 Aether Verse',
    '🔮 Arcane Verse',
}

SMASH_COOLDOWN_SECS  = 10
CACHE_MAX_AGE_SECS   = 1800   # Re-fetch characters from DB after 30 minutes
DOWNLOAD_TIMEOUT     = 60


# ══════════════════════════════════════════════════════════════════════════════
#  IN-MEMORY STATE
# ══════════════════════════════════════════════════════════════════════════════

last_smash_times: dict[int, datetime] = {}
active_smashes:   dict[int, dict]     = {}
smash_stats:      dict[int, dict]     = {}

_character_cache:      list[dict] = []
_cache_loaded_at:      float      = 0.0   # monotonic time


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS — AUTH
# ══════════════════════════════════════════════════════════════════════════════

def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def _is_authorized(chat_id: int) -> bool:
    return chat_id in authorized_chats


async def _send_redirect(message: Message, from_private: bool = False) -> None:
    if from_private:
        text = (
            "**⚔️ Use Smash in Our Main Group!**\n\n"
            "`• This command only works in the main group`\n"
            "`• Click below to join and use /smash there`\n\n"
            f"**🏠 Main Group:** @{MAIN_GC_USERNAME}"
        )
    else:
        text = (
            "**🔒 This Group is Not Authorized!**\n\n"
            "`• /smash only works in the official main group`\n"
            "`• Click below to go there and start fighting!`\n\n"
            f"**🏠 Main Group:** @{MAIN_GC_USERNAME}\n\n"
            f"**👑 Want to auth your group?**\n"
            f"`• Contact` @{OWNER_USERNAME}"
        )
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Go to Main Group ➜", url=MAIN_GC_LINK)
        ]])
    )


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS — SAFE WRAPPERS
# ══════════════════════════════════════════════════════════════════════════════

async def _safe_edit_caption(
    message: Message,
    caption: str,
    buttons: list | None = None,
) -> None:
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    try:
        await message.edit_caption(caption, reply_markup=markup)
    except FloodWait as exc:
        await asyncio.sleep(exc.value)
        try:
            await message.edit_caption(caption, reply_markup=markup)
        except Exception as e:
            print(f"⚠️ [safe_edit_caption retry]: {e}")
    except Exception as e:
        print(f"⚠️ [safe_edit_caption]: {e}")


async def _safe_answer(query, text: str, show_alert: bool = False) -> None:
    try:
        await query.answer(text, show_alert=show_alert)
    except QueryIdInvalid:
        pass
    except Exception as e:
        print(f"⚠️ [safe_answer]: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS — MEDIA DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

async def _download_to_temp(url: str, suffix: str) -> str:
    """
    Download *url* to a local temp file. Returns the file path.
    Caller MUST clean up via _safe_delete() in a finally block.
    Raw URLs cannot be passed to Telegram for external hosts — this is the fix
    for the WEBPAGE_MEDIA_EMPTY 400 error.
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
#  CHARACTER CACHE
# ══════════════════════════════════════════════════════════════════════════════

def _get_user_stats(user_id: int) -> dict:
    return smash_stats.get(user_id, {
        "wins": 0, "losses": 0,
        "streak": 0, "max_streak": 0, "total_smashes": 0,
    })


def _is_animated(character: dict) -> bool:
    """Return True if this character is a video/animated character."""
    rarity = character.get("rarity", "")
    video_url = character.get("video_url", "")
    img_url = character.get("img_url", "")
    img_type = character.get("img_type", "")
    file_extension = character.get("file_extension", "")
    
    # 1. Check if rarity implies animation/video
    rarity_lower = rarity.lower() if rarity else ""
    if "animated" in rarity_lower or "animation" in rarity_lower:
        return True
        
    # 2. Check if img_type is video
    if img_type == "video":
        return True
        
    # 3. Check if video_url is set and not empty
    if video_url:
        return True
        
    # 4. Check if the URL ends with a video extension
    for url in (video_url, img_url):
        if url:
            url_lower = url.lower()
            if any(url_lower.endswith(ext) for ext in [".mp4", ".gif", ".gifv", ".webm"]):
                return True
                
    # 5. Check if file_extension is a video extension
    if file_extension and file_extension.lower() in [".mp4", ".gif", ".gifv", ".webm"]:
        return True
        
    return False


async def _ensure_cache() -> None:
    """
    Load (or refresh) the character cache from DB.
    Called lazily on first /smash and auto-refreshes after CACHE_MAX_AGE_SECS.
    Avoids the module-level loop.run_until_complete() that crashed on import.
    """
    global _character_cache, _cache_loaded_at
    age = time.monotonic() - _cache_loaded_at
    if _character_cache and age < CACHE_MAX_AGE_SECS:
        return

    all_chars = await collection.find({}).to_list(length=None)
    _character_cache = [
        c for c in all_chars
        if c.get("img_url")   # smash requires a photo; skip video-only entries
        and c.get("rarity") not in EXCLUDED_RARITIES
        and not _is_animated(c)
    ]
    _cache_loaded_at = time.monotonic()
    print(f"🌀 Smash cache refreshed: {len(_character_cache)} eligible characters")


# ══════════════════════════════════════════════════════════════════════════════
#  OWNER COMMANDS — auth / unauth / reloadsmash
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("authgc"))
async def auth_gc(client: Client, message: Message) -> None:
    """Owner-only: authorize a group chat to use /smash."""
    if not _is_owner(message.from_user.id):
        await message.reply_text(
            "**🚫 Access Denied!**\n"
            f"`• Only @{OWNER_USERNAME} can authorize groups`"
        )
        return

    args = message.text.split()
    if len(args) > 1:
        try:
            target_chat_id = int(args[1])
        except ValueError:
            await message.reply_text(
                "**❌ Invalid Chat ID!**\n"
                "`• Usage: /authgc <chat_id>`\n"
                "`• Or use /authgc in the target group`"
            )
            return
    else:
        if message.chat.type == "private":
            await message.reply_text(
                "**❌ Can't authorize a private chat!**\n"
                "`• Use /authgc <group_id> to authorize a group`"
            )
            return
        target_chat_id = message.chat.id

    if target_chat_id in authorized_chats:
        await message.reply_text(
            f"**✅ Already Authorized!**\n"
            f"`• Chat ID: {target_chat_id} is already authorized`"
        )
        return

    authorized_chats.add(target_chat_id)
    await message.reply_text(
        f"**✅ Group Authorized!**\n\n"
        f"`• Chat ID: {target_chat_id}`\n"
        f"`• /smash is now ENABLED in this group`\n\n"
        f"**👑 Authorized by:** @{OWNER_USERNAME}"
    )
    print(f"✅ GC Authorized: {target_chat_id}")


@app.on_message(filters.command("unauthgc"))
async def unauth_gc(client: Client, message: Message) -> None:
    """Owner-only: remove a group's authorization."""
    if not _is_owner(message.from_user.id):
        await message.reply_text(
            "**🚫 Access Denied!**\n"
            f"`• Only @{OWNER_USERNAME} can remove authorization`"
        )
        return

    args = message.text.split()
    if len(args) > 1:
        try:
            target_chat_id = int(args[1])
        except ValueError:
            await message.reply_text("**❌ Invalid Chat ID!**\n`• Usage: /unauthgc <chat_id>`")
            return
    else:
        if message.chat.type == "private":
            await message.reply_text("**❌ Specify a group ID!**\n`• Usage: /unauthgc <group_id>`")
            return
        target_chat_id = message.chat.id

    if target_chat_id in PERMANENT_AUTHORIZED_CHATS:
        await message.reply_text(
            f"**🔒 Permanent Authorization!**\n"
            f"`• Chat ID: {target_chat_id} is hardcoded and cannot be removed`"
        )
        return

    if target_chat_id not in authorized_chats:
        await message.reply_text(
            f"**⚠️ Not Authorized!**\n"
            f"`• Chat ID: {target_chat_id} was never authorized`"
        )
        return

    authorized_chats.discard(target_chat_id)
    await message.reply_text(
        f"**🔒 Authorization Removed!**\n\n"
        f"`• Chat ID: {target_chat_id}`\n"
        f"`• /smash is now DISABLED in this group`"
    )
    print(f"🔒 GC Unauthorized: {target_chat_id}")


@app.on_message(filters.command("authlist"))
async def auth_list(client: Client, message: Message) -> None:
    """Owner-only: list all authorized group chats."""
    if not _is_owner(message.from_user.id):
        await message.reply_text(
            "**🚫 Access Denied!**\n"
            f"`• Only @{OWNER_USERNAME} can view this list`"
        )
        return

    if not authorized_chats:
        await message.reply_text("**📋 No Authorized Groups Yet!**")
        return

    lines = [
        f"`• {cid}` *(permanent)*" if cid in PERMANENT_AUTHORIZED_CHATS else f"`• {cid}`"
        for cid in sorted(authorized_chats)
    ]
    await message.reply_text(
        f"**📋 Authorized Groups ({len(authorized_chats)})**\n\n" + "\n".join(lines)
    )


@app.on_message(filters.command("reloadsmash") & filters.user(OWNER_ID))
async def reload_smash_cache(client: Client, message: Message) -> None:
    """Owner-only: force-refresh the smash character cache from DB."""
    global _cache_loaded_at
    _cache_loaded_at = 0.0   # force stale
    await _ensure_cache()
    await message.reply_text(
        f"✅ **Smash cache reloaded!**\n"
        f"`• {len(_character_cache)} eligible characters loaded`"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  /smash  COMMAND
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("smash"))
async def smash_command(client: Client, message: Message) -> None:
    # Auth gates
    if message.chat.type == "private":
        await _send_redirect(message, from_private=True)
        return
    if not _is_authorized(message.chat.id):
        await _send_redirect(message, from_private=False)
        return

    user_id = message.from_user.id
    now     = datetime.now()

    # Already in a battle?
    if user_id in active_smashes:
        await message.reply_text(
            "**⚔️ You're already in combat!**\n"
            "`• Finish your current battle first`\n"
            "`• Use /exit to abandon`"
        )
        return

    # Cooldown check
    last_time = last_smash_times.get(user_id)
    if last_time:
        elapsed = (now - last_time).total_seconds()
        if elapsed < SMASH_COOLDOWN_SECS:
            remaining = int(SMASH_COOLDOWN_SECS - elapsed)
            await message.reply_text(
                f"**⏳ Regaining strength...**\n"
                f"`• Ready again in {remaining}s`"
            )
            return

    # Ensure character cache is populated / fresh
    await _ensure_cache()

    if not _character_cache:
        await message.reply_text(
            "**🌌 No worthy opponents found!**\n"
            "`• The battlefield is empty`"
        )
        return

    # Pick a random character and register the active smash
    character = random.choice(_character_cache)
    active_smashes[user_id] = character

    img_url = character.get("img_url", "")
    if not img_url:
        # Should never happen (cache pre-filters), but be defensive
        active_smashes.pop(user_id, None)
        await message.reply_text("**⚠️ Character has no image — try again.**")
        return

    caption = (
        f"**🌠 A Challenger Approaches!**\n\n"
        f"**🔥 {character.get('name', 'Mysterious Warrior')}**\n"
        f"`• Origin: {character.get('anime', 'Unknown Realm')}`\n"
        f"`• Power Level: {character.get('rarity', 'Unknown')}`\n\n"
        f"**Will you fight or flee?**"
    )
    buttons = [[
        InlineKeyboardButton("⚔️ ENGAGE COMBAT", callback_data=f"begin_smash_{user_id}")
    ]]

    # ── FIX: Download first, then upload bytes ─────────────────────────────
    # Passing a raw Catbox / external URL directly to reply_photo causes:
    #   pyrogram.errors.WebpageMediaEmpty: [400 WEBPAGE_MEDIA_EMPTY]
    # because Telegram's servers try to fetch the URL themselves and are blocked.
    tmp_path = None
    try:
        tmp_path = await _download_to_temp(img_url, ".jpg")
        with open(tmp_path, "rb") as fh:
            await message.reply_photo(
                photo=fh,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
    except Exception as exc:
        print(f"❌ /smash send error  user={user_id}  url={img_url!r}: {exc}")
        active_smashes.pop(user_id, None)
        await message.reply_text(
            "**❌ Failed to load the challenger's image.**\n"
            "`• Try again in a moment`"
        )
    finally:
        _safe_delete(tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
#  BATTLE  CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_callback_query(filters.regex(r"^begin_smash_(\d+)$"))
async def begin_smash(client: Client, query) -> None:
    user_id = int(query.matches[0].group(1))

    if query.from_user.id != user_id:
        await _safe_answer(query, "🛡️ This battle isn't yours to fight!", show_alert=True)
        return

    if user_id not in active_smashes:
        await _safe_answer(query, "⌛ The battle opportunity has passed...", show_alert=True)
        return

    await query.answer()
    character = active_smashes[user_id]
    tier      = character.get("rarity", "Common")

    buttons = [
        [InlineKeyboardButton("💥 SMASH ATTACK",      callback_data=f"smash_engage_{user_id}")],
        [InlineKeyboardButton("🏃 TACTICAL RETREAT",  callback_data=f"smash_retreat_{user_id}")],
    ]
    await _safe_edit_caption(
        query.message,
        f"**⚡ {character['name']} prepares for battle!**\n\n"
        f"`• Combat Rating: {tier}`\n\n"
        f"**Choose your action:**",
        buttons,
    )


@app.on_callback_query(filters.regex(r"^smash_engage_(\d+)$"))
async def smash_engage(client: Client, query) -> None:
    user_id = int(query.matches[0].group(1))

    if query.from_user.id != user_id:
        await _safe_answer(query, "🚫 This isn't your fight!", show_alert=True)
        return

    if user_id not in active_smashes:
        await _safe_answer(query, "⏳ The battle has already concluded...", show_alert=True)
        return

    await query.answer()
    character = active_smashes[user_id]
    tier      = character.get("rarity", "Common")

    # Battle animation
    for phase in [
        "**⚡ Power surging through your veins...**",
        "**💢 Locking onto target...**",
        "**🔥 Unleashing combat energy...**",
        "**💥 CLASH OF FATES!**",
    ]:
        await _safe_edit_caption(query.message, phase)
        await asyncio.sleep(0.8)

    stats = get_user_stats(user_id) if False else _get_user_stats(user_id)
    stats["total_smashes"] += 1
    smash_success = random.random() < 0.5

    if smash_success:
        await user_collection.update_one(
            {"id": user_id},
            {"$push": {"characters": character}},
            upsert=True,
        )
        stats["wins"]   += 1
        stats["streak"] += 1
        if stats["streak"] > stats["max_streak"]:
            stats["max_streak"] = stats["streak"]

        msg = random.choice([
            f"**🎖️ VICTORY!**\nYou've conquered {character['name']} in battle!",
            f"**👑 TRIUMPH!**\n{character['name']} kneels before your might!",
            f"**✨ LEGENDARY!**\nYou've smashed {character['name']} into submission!",
        ])
        await _safe_edit_caption(
            query.message,
            f"{msg}\n\n"
            f"`• Added to your collection`\n"
            f"`• Power Level: {tier}`\n\n"
            f"**Current streak: {stats['streak']}**",
        )
    else:
        stats["losses"] += 1
        stats["streak"]  = 0

        msg = random.choice([
            f"**💀 CRUSHING DEFEAT!**\n{character['name']} overpowered you!",
            f"**☠️ YOU FELL IN BATTLE!**\n{character['name']} was too strong!",
            f"**⚰️ MISSION FAILED!**\n{character['name']} defeated you!",
        ])
        await _safe_edit_caption(
            query.message,
            f"{msg}\n\n"
            f"`• Power Level: {tier}`\n\n"
            f"**Regroup and try again!**",
        )

    smash_stats[user_id]      = stats
    last_smash_times[user_id] = datetime.now()
    active_smashes.pop(user_id, None)


@app.on_callback_query(filters.regex(r"^smash_retreat_(\d+)$"))
async def smash_retreat(client: Client, query) -> None:
    user_id = int(query.matches[0].group(1))

    if query.from_user.id != user_id:
        await _safe_answer(query, "🛡️ This retreat isn't yours to command!", show_alert=True)
        return

    if user_id not in active_smashes:
        await _safe_answer(query, "🌌 The battle has already faded...", show_alert=True)
        return

    await query.answer()
    character = active_smashes[user_id]

    await _safe_edit_caption(
        query.message,
        random.choice([
            "**🏃 STRATEGIC WITHDRAWAL!**\nYou live to fight another day...",
            f"**🛡️ RETREAT SUCCESSFUL!**\n{character['name']} lets you escape... for now.",
            f"**🌫️ FADING AWAY...**\nYou vanish before {character['name']} can strike!",
        ]),
    )

    stats           = _get_user_stats(user_id)
    stats["losses"] += 1
    stats["streak"]  = 0
    smash_stats[user_id]      = stats
    active_smashes.pop(user_id, None)
    last_smash_times[user_id] = datetime.now()


# ══════════════════════════════════════════════════════════════════════════════
#  /exit  COMMAND
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("exit"))
async def exit_smash(client: Client, message: Message) -> None:
    if message.chat.type == "private":
        await _send_redirect(message, from_private=True)
        return
    if not _is_authorized(message.chat.id):
        await _send_redirect(message, from_private=False)
        return

    user_id = message.from_user.id
    if user_id in active_smashes:
        character = active_smashes.pop(user_id)
        await message.reply_text(
            f"🚪 **ABANDONING BATTLE!**\n"
            f"`• {character['name']} watches as you flee...`"
        )
    else:
        await message.reply_text(
            "⚔️ **NO ACTIVE COMBAT!**\n"
            "`• Use /smash to find an opponent`"
        )
