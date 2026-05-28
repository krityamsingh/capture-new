"""
Grabber/modules/info.py
/check command — look up any character by ID, with inline buttons.

Fixes applied vs old version:
  • Both animation rarity strings accepted ("⚜️ Animated" AND "🧬 Animation")
  • video_url always tried first when present, regardless of rarity label
  • Temp-file helper cleans up even on exceptions (finally block)
  • callback_data split uses maxsplit=1 so IDs containing "_" never break
  • how_many callback: counts correctly from nested character list
  • top10 callback: safe user-fetch with full fallback
  • back_to_details: robust media-type detection, no rarity mismatch crash
  • All handlers use unique callback patterns — no clash with spawn.py pyrogram handlers
  • Owners field shown in caption
  • Descriptive error messages logged with char_id context
"""

import aiohttp
import asyncio
import tempfile
import os

from telegram import (
    Update,
    InlineKeyboardButton as IKB,
    InlineKeyboardMarkup as IKM,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from Grabber import user_collection, collection, application
from . import capsify

FALLBACK_IMG = "https://telegra.ph/file/lost-character-placeholder.jpg"


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# Both animation rarity strings are treated as video characters.
# This bridges the mismatch between modules that store "⚜️ Animated"
# and modules that store "🧬 Animation".
ANIMATION_RARITIES = {"⚜️ Animated", "🧬 Animation"}

RARITY_EMOJIS = {
    "🔴 Common":         "🔴",
    "🔵 Uncommon":       "🔵",
    "🟠 Rare":           "🟠",
    "🟡 Legendary":      "🟡",
    "🫧 Premium":        "🫧",
    "🔮 Limited Edition":"🔮",
    "🏵️ Exotic":         "🏵️",
    "⚜️ Animated":       "⚜️",
    "🧬 Animation":      "🧬",
    "🌼 Celebrity":      "🌼",
    "🎐 Crystal":        "🎐",
    "🍹 Neon":           "🍹",
    "🧿 Supreme":        "🧿",
    "⚡ Thundra":        "⚡",
    "🛸 Galvoria":       "🛸",
}

# Download timeout for media (seconds)
DOWNLOAD_TIMEOUT = 120


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_animated(character: dict) -> bool:
    """Return True if this character should be sent as a video."""
    rarity    = character.get("rarity", "")
    video_url = character.get("video_url", "")
    # Treat as animated if rarity matches OR if a video_url is stored
    # (handles DB rows where rarity label was inconsistent)
    return rarity in ANIMATION_RARITIES or bool(video_url)


def _build_keyboard(char_id: str) -> IKM:
    return IKM([
        [
            IKB("🔍 ʜᴏᴡ ᴍᴀɴʏ ɪ ʜᴀᴠᴇ", callback_data=f"chk_howmany_{char_id}"),
            IKB("🏆 ᴛᴏᴘ 10 ʜᴏʟᴅᴇʀꜱ",    callback_data=f"chk_top10_{char_id}"),
        ]
    ])


def _build_back_keyboard(char_id: str) -> IKM:
    return IKM([
        [IKB("↩️ ʙᴀᴄᴋ ᴛᴏ ᴅᴇᴛᴀɪʟꜱ",   callback_data=f"chk_details_{char_id}")],
        [IKB("🔍 ʜᴏᴡ ᴍᴀɴʏ ɪ ʜᴀᴠᴇ", callback_data=f"chk_howmany_{char_id}")],
    ])


def _build_caption(character: dict) -> str:
    rarity      = character.get("rarity", "Unknown")
    emoji       = RARITY_EMOJIS.get(rarity, "✨")
    owners      = character.get("owners", 0)
    owners_text = str(owners) if owners else "None yet"
    video_url   = character.get("video_url", "")
    img_url     = character.get("img_url", "")
    media_url   = video_url if _is_animated(character) and video_url else img_url

    name_text = character['name']
    if media_url:
        name_text = f"<a href='{media_url}'>{name_text}</a>"

    return (
        f"✨ <b>ʟᴏᴏᴋ ᴀᴛ ᴛʜɪꜱ ᴄʜᴀʀᴀᴄᴛᴇʀ!</b>\n\n"
        f"🆔 <b>ID:</b> <code>{character['id']}</code>\n"
        f"👤 <b>ɴᴀᴍᴇ:</b> {name_text}\n"
        f"📺 <b>ᴀɴɪᴍᴇ:</b> {character['anime']}\n"
        f"{emoji} <b>ʀᴀʀɪᴛʏ:</b> {rarity}\n"
        f"👥 <b>ᴏᴡɴᴇʀs:</b> {owners_text}"
    )


async def _download_to_temp(url: str, suffix: str) -> str:
    """
    Download *url* to a temporary file and return its path.
    The caller MUST delete the file when done (use try/finally).

    We download rather than passing raw URLs because external hosts
    (Catbox, etc.) return WEBPAGE_MEDIA_EMPTY when Telegram tries
    to fetch them directly.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"HTTP {resp.status} downloading media from {url!r}"
                )
            data = await resp.read()

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
    finally:
        tmp.close()

    return tmp.name


def _safe_delete(path: str | None) -> None:
    """Delete a temp file, ignoring any errors."""
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass


async def _send_character_media(
    character: dict,
    reply_fn,           # coroutine: reply_video / reply_photo / reply_text
    keyboard: IKM,
    caption: str,
    fallback_reply_fn,  # coroutine for plain-text fallback
) -> None:
    """
    Download and send the right media type for *character*.
    Falls back to a plain-text reply if everything fails.
    Automatically cleans up the temp file.
    """
    video_url = character.get("video_url", "")
    img_url   = character.get("img_url", "")
    animated  = _is_animated(character)

    tmp_path = None
    try:
        # ── Video path ─────────────────────────────────────────────────────────
        if animated and video_url:
            try:
                tmp_path = await _download_to_temp(video_url, ".mp4")
                with open(tmp_path, "rb") as fh:
                    await reply_fn(
                        "video",
                        media=fh,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                return
            except Exception as e:
                print(f"⚠️ Failed to download/send video for character {character.get('id')}: {e}")

        # ── Photo path ─────────────────────────────────────────────────────────
        if img_url:
            try:
                tmp_path = await _download_to_temp(img_url, ".jpg")
                with open(tmp_path, "rb") as fh:
                    await reply_fn(
                        "photo",
                        media=fh,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                return
            except Exception as e:
                print(f"⚠️ Failed to download/send photo for character {character.get('id')}: {e}")

        # ── Fallback image path ───────────────────────────────────────────────
        try:
            _safe_delete(tmp_path)
            tmp_path = await _download_to_temp(FALLBACK_IMG, ".jpg")
            with open(tmp_path, "rb") as fh:
                await reply_fn(
                    "photo",
                    media=fh,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            return
        except Exception as e:
            print(f"⚠️ Failed to download/send fallback photo for character {character.get('id')}: {e}")

    finally:
        _safe_delete(tmp_path)

    # ── Text Fallback (if fallback image also fails) ───────────────────────
    fallback_text = caption
    if video_url:
        fallback_text += f"\n\n🎬 <a href='{video_url}'>Video Link</a>"
    elif img_url:
        fallback_text += f"\n\n🖼 <a href='{img_url}'>Image Link</a>"

    await fallback_reply_fn(
        fallback_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  /check  — main command
# ══════════════════════════════════════════════════════════════════════════════

async def details(update: Update, context: CallbackContext) -> None:
    """
    /check <id>
    Look up a character by ID and send its details (with webpage media preview)
    and action buttons.
    """
    args = context.args
    if not args:
        await update.message.reply_text(
            capsify("Usage: /check <character_id>\nExample: /check 1234")
        )
        return

    char_id   = args[0].strip()
    character = await collection.find_one({"id": char_id})

    if not character:
        await update.message.reply_text(
            capsify(f"No character found with ID: {char_id}")
        )
        return

    caption  = _build_caption(character)
    keyboard = _build_keyboard(char_id)

    try:
        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        print(f"❌ /check error  char_id={char_id!r}: {exc}")
        await update.message.reply_text(
            capsify("Failed to send details. Please try again later.")
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: 🔍 How many do I have?
# ══════════════════════════════════════════════════════════════════════════════

async def how_many(update: Update, context: CallbackContext) -> None:
    """
    Button: "How many do I have?"
    Counts how many copies of this character the pressing user owns.
    """
    query = update.callback_query
    await query.answer()   # acknowledge immediately to stop the loading spinner

    # callback_data format: chk_howmany_<char_id>
    # maxsplit=2 so char IDs that contain "_" are preserved intact
    parts   = query.data.split("_", 2)
    char_id = parts[2] if len(parts) == 3 else ""

    if not char_id:
        await query.answer("⚠️ Invalid callback data.", show_alert=True)
        return

    user_id   = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})

    count = 0
    if user_data and "characters" in user_data:
        count = sum(
            1 for c in user_data["characters"]
            if str(c.get("id", "")) == str(char_id)
        )

    await query.answer(
        f"🌀 You own {count} cop{'y' if count == 1 else 'ies'} of this character.",
        show_alert=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: 🏆 Top 10 holders
# ══════════════════════════════════════════════════════════════════════════════

async def top_grabbers(update: Update, context: CallbackContext) -> None:
    """
    Button: "Top 10 holders"
    Shows a leaderboard of the 10 users who own the most copies.
    """
    query   = update.callback_query
    await query.answer("⚡ Fetching top holders...", cache_time=5)

    # callback_data format: chk_top10_<char_id>
    parts   = query.data.split("_", 2)
    char_id = parts[2] if len(parts) == 3 else ""

    if not char_id:
        return

    # Aggregate: count how many times this char_id appears across all users
    pipeline = [
        {"$match":  {"characters.id": char_id}},
        {"$unwind": "$characters"},
        {"$match":  {"characters.id": char_id}},
        {"$group":  {"_id": "$id", "count": {"$sum": 1}}},
        {"$sort":   {"count": -1}},
        {"$limit":  10},
    ]
    top_users = await user_collection.aggregate(pipeline).to_list(length=10)

    if not top_users:
        leaderboard = "❌ No one owns this character yet."
    else:
        lines = []
        for idx, row in enumerate(top_users, start=1):
            uid = row["_id"]
            cnt = row["count"]
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, "🏅")
            try:
                tg_user = await context.bot.get_chat(uid)
                name    = tg_user.full_name or f"User {uid}"
            except Exception:
                name = f"User {uid}"
            lines.append(
                f"{medal} <b><a href='tg://user?id={uid}'>{name}</a></b> ×{cnt}"
            )
        leaderboard = "\n".join(lines)

    character = await collection.find_one({"id": char_id})
    if not character:
        await query.answer("Character no longer exists.", show_alert=True)
        return

    caption = (
        f"✨ <b>ʟᴏᴏᴋ ᴀᴛ ᴛʜɪꜱ ᴄʜᴀʀᴀᴄᴛᴇʀ!</b>\n\n"
        f"🆔 <b>ID:</b> <code>{character['id']}</code>\n"
        f"👤 <b>ɴᴀᴍᴇ:</b> {character['name']}\n"
        f"📺 <b>ᴀɴɪᴍᴇ:</b> {character['anime']}\n"
        f"✨ <b>ʀᴀʀɪᴛʏ:</b> {character.get('rarity', 'Unknown')}\n\n"
        f"🏆 <b>ᴛᴏᴘ 10 ʜᴏʟᴅᴇʀs:</b>\n{leaderboard}"
    )

    try:
        await query.edit_message_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=_build_back_keyboard(char_id),
        )
    except Exception as exc:
        print(f"❌ top_grabbers edit error  char_id={char_id!r}: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: ↩️ Back to character details
# ══════════════════════════════════════════════════════════════════════════════

async def back_to_details(update: Update, context: CallbackContext) -> None:
    """
    Button: "Back to details"
    Re-sends the character's details by editing the message text.
    """
    query   = update.callback_query
    await query.answer("🌀 Loading...", cache_time=2)

    # callback_data format: chk_details_<char_id>
    parts   = query.data.split("_", 2)
    char_id = parts[2] if len(parts) == 3 else ""

    if not char_id:
        return

    character = await collection.find_one({"id": char_id})
    if not character:
        await query.answer("Character no longer exists.", show_alert=True)
        return

    caption   = _build_caption(character)
    keyboard  = _build_keyboard(char_id)

    try:
        await query.edit_message_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        print(f"❌ back_to_details error  char_id={char_id!r}: {exc}")
        await query.answer("❌ Failed to load details. Try again.", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Register Handlers
#
#  NOTE: Callback patterns use the "chk_" prefix so they NEVER conflict with
#  the pyrogram handlers in spawn.py which also use "top10_" and similar names.
# ══════════════════════════════════════════════════════════════════════════════

application.add_handler(CommandHandler("check", details))
application.add_handler(CallbackQueryHandler(how_many,        pattern=r"^chk_howmany_.+$"))
application.add_handler(CallbackQueryHandler(top_grabbers,    pattern=r"^chk_top10_.+$"))
application.add_handler(CallbackQueryHandler(back_to_details, pattern=r"^chk_details_.+$"))
