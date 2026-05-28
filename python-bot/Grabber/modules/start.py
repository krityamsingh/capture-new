import os
import time
import random
import re
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMemberUpdated,
)

# Import your database and app instance
from . import user_collection, collection, app

# ─────────────────── Config ────────────────────
VIDEO_URLS = [
    "https://files.catbox.moe/28291c.mp4",
    "https://files.catbox.moe/pqkx90.mp4",
]
START_IMAGE_URL = "https://files.catbox.moe/43vfsu.jpg"
GROUP_VID_URL = "https://files.catbox.moe/28291c.mp4"  # currently unused
STICKER_ID = "CAACAgQAAxkBAAEkaVVoi2qUJ_xfrzADYu6zXbX4tUO4lwACDhUAAv1c6VOHhn_KhsuzHDYE"

# Use environment variable for log chat ID, fallback to a safe default
LOG_CHAT_ID = int(os.environ.get("LOG_CHAT_ID", -1003695209406))

SUPPORT_URL = "https://t.me/Divine_Catchers"
UPDATES_URL = "https://t.me/Devince_Support"

# ─────────────────── Helpers ───────────────────
_start_time = time.time()


def _uptime() -> str:
    s = int(time.time() - _start_time)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}h {m}m {s}s"


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


async def _send_log(client: Client, text: str) -> None:
    """Fire-and-forget log message; never raises."""
    try:
        await client.send_message(LOG_CHAT_ID, text, disable_web_page_preview=True)
    except Exception as exc:
        print(f"[LOG] Failed to send log: {exc}")


async def _send_with_fallback(
    client: Client,
    chat_id: int,
    caption: str,
    buttons: InlineKeyboardMarkup,
    *,
    reply_to: int | None = None,
) -> None:
    """
    Try photo → video → plain text, in order.
    Pass reply_to to use reply_photo / reply_video / reply_text instead of send_*.
    """
    try:
        if reply_to:
            await client.send_photo(chat_id, START_IMAGE_URL, caption=caption, reply_markup=buttons, reply_to_message_id=reply_to)
        else:
            await client.send_photo(chat_id, START_IMAGE_URL, caption=caption, reply_markup=buttons)
        return
    except Exception as e:
        print(f"[SEND] Photo failed for {chat_id}: {e}")

    try:
        if reply_to:
            await client.send_video(chat_id, random.choice(VIDEO_URLS), caption=caption, reply_markup=buttons, reply_to_message_id=reply_to)
        else:
            await client.send_video(chat_id, random.choice(VIDEO_URLS), caption=caption, reply_markup=buttons)
        return
    except Exception as e:
        print(f"[SEND] Video fallback failed for {chat_id}: {e}")

    try:
        if reply_to:
            await client.send_message(chat_id, caption, reply_markup=buttons, disable_web_page_preview=True, reply_to_message_id=reply_to)
        else:
            await client.send_message(chat_id, caption, reply_markup=buttons, disable_web_page_preview=True)
    except Exception as e:
        print(f"[SEND] Text fallback failed for {chat_id}: {e}")


def _home_start_text(mention: str) -> str:
    return (
        f"🌟 ʜᴇʏᴀ {mention}\n"
        "ɪ'ᴍ ʏᴏᴜʀ ᴀɴɪᴍᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴄᴀᴘᴛᴜʀᴇ ʙᴏᴛ — ꜰᴜɴ ɢʀᴏᴜᴘ ɢᴀᴍᴇ!\n"
        "────────── ⋆⋅☆⋅⋆ ──────────\n"
        "I spawn random anime characters → You guess → You capture!"
    )


def _build_home_buttons(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add me to your group",
                              url=f"https://t.me/{bot_username}?startgroup=true")],
        [
            InlineKeyboardButton("💬 Support", url=SUPPORT_URL),
            InlineKeyboardButton("📢 Updates", url=UPDATES_URL),
        ],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu_1")],
    ])


# ─────────────────── Help menu (dynamic pages) ────────────────
HELP_PAGES = {
    1: (
        "📚 **Character Capture — Help** (1/3)\n\n"
        "/start — Start the bot\n"
        "/harem — View your character collection\n"
        "/cmode — Change collection view mode\n"
        "/capture — Buy, sell & capture characters\n"
        "/hstyle — Change harem caption style"
    ),
    2: (
        "📚 **Character Capture — Help** (2/3)\n\n"
        "/gift — Gift characters to other players\n"
        "/trade — Trade characters with others\n"
        "/check — Look up a character by ID\n"
        "/rarity — Browse characters by rarity\n"
        "/changetime — Adjust spawn rate in your group"
    ),
    3: (
        "📚 **Character Capture — Help** (3/3)\n\n"
        "/bal — Check token balance\n"
        "/pay — Send tokens to a player\n"
        "/status — View your bot stats\n"
        "/animelist — Browse anime & characters\n"
        "/claim — Claim daily character\n"
        "/gtop — Global top-10 collectors\n"
        "/fav — Mark characters as favourite"
    ),
}
TOTAL_HELP_PAGES = len(HELP_PAGES)


def _help_buttons(page: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"help_menu_{page - 1}"))
    if page < TOTAL_HELP_PAGES:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"help_menu_{page + 1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="home_menu")])
    return InlineKeyboardMarkup(rows)


@app.on_callback_query(filters.regex(r"^help_menu_(\d+)$"))
async def help_menu_callback(client: Client, cq: CallbackQuery):
    m = re.match(r"help_menu_(\d+)", cq.data or "")
    page = max(1, min(int(m.group(1)) if m else 1, TOTAL_HELP_PAGES))
    text = HELP_PAGES[page]

    try:
        await cq.message.edit_text(text, reply_markup=_help_buttons(page))
    except Exception:
        await cq.answer(text, show_alert=True)
        return
    finally:
        try:
            await cq.answer()
        except Exception:
            pass


# ─────────────────── Home button callback ────────────────
@app.on_callback_query(filters.regex(r"^home_menu$"))
async def home_menu_callback(client: Client, cq: CallbackQuery):
    user = cq.from_user
    mention = user.mention if user else "there"
    bot_me = await client.get_me()
    text = _home_start_text(mention)
    buttons = _build_home_buttons(bot_me.username)

    # Edit the existing bubble first (instant feedback)
    try:
        await cq.message.edit_text(text, reply_markup=buttons)
    except Exception:
        pass

    # Then send a fresh media message below
    await _send_with_fallback(client, cq.message.chat.id, caption=text, buttons=buttons)

    try:
        await cq.answer()
    except Exception:
        pass


# ─────────────────── Bot added/updated in a chat ─────────
@app.on_chat_member_updated(filters.me)
async def bot_chat_member_update(client: Client, update: ChatMemberUpdated):
    """Log whenever this bot transitions from absent → present in a chat."""
    try:
        chat = update.chat
        old_member = update.old_chat_member
        new_member = update.new_chat_member
        actor = update.from_user

        old_status = old_member.status if old_member else None
        new_status = new_member.status if new_member else None

        absent_statuses = {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}
        active_statuses = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}

        # Only care about: was absent → now active
        if old_status not in absent_statuses or new_status not in active_statuses:
            return

        chat_title = getattr(chat, "title", None) or str(chat.id)
        chat_id = chat.id

        lines = [
            "🔔 Bot added to a chat",
            f"Chat: {chat_title}",
            f"Chat ID: `{chat_id}`",
            f"Chat type: {chat.type}",
            f"Old status: {old_status}",
            f"New status: {new_status}",
            f"Time: {_now()}",
            f"Uptime: {_uptime()}",
        ]

        if actor:
            lines.insert(2, f"By: {actor.mention} (`{actor.id}`)")

        try:
            link = await client.export_chat_invite_link(chat_id)
            lines.append(f"Invite: {link}")
        except Exception:
            lines.append("Invite: (unavailable)")

        await _send_log(client, "\n".join(lines))

    except Exception as exc:
        print(f"[MEMBER_UPDATE] Error: {exc}")


# ─────────────────── Private start ─────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message):
    user = message.from_user
    mention = user.mention if user else "there"
    bot_me = await client.get_me()

    # Send sticker (optional)
    try:
        await message.reply_sticker(STICKER_ID)
    except Exception:
        pass

    await _send_with_fallback(
        client, message.chat.id,
        caption=_home_start_text(mention),
        buttons=_build_home_buttons(bot_me.username),
    )

    # Log
    uname = f"@{user.username}" if user and user.username else "—"
    fname = f"{user.first_name or ''} {user.last_name or ''}".strip()
    await _send_log(client,
        f"🟢 /start (private)\n"
        f"User: {mention}\n"
        f"UserID: `{user.id}`\n"
        f"Username: {uname}\n"
        f"Name: {fname}\n"
        f"Time: {_now()}\n"
        f"Uptime: {_uptime()}"
    )


# ─────────────────── Group start ───────────────────────
@app.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    bot_me = await client.get_me()
    bot_name = bot_me.first_name or bot_me.username or "Bot"
    caption = f"{bot_name} ɪs ᴀʟɪᴠᴇ ᴄᴜᴛɪᴇ\n\n✫ ᴜᴘᴛɪᴍᴇ : {_uptime()}"
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍄 Start Bot",
                                 url=f"https://t.me/{bot_me.username}?start=start"),
            InlineKeyboardButton("💬 Support", url=SUPPORT_URL),
        ],
        [InlineKeyboardButton("📢 Updates", url=UPDATES_URL)],
    ])

    await _send_with_fallback(
        client, message.chat.id,
        caption=caption,
        buttons=buttons,
        reply_to=message.id,
    )


# If you want to run the bot from this file (optional)
if __name__ == "__main__":
    print("Bot is running...")
    app.run()  # or app.start() and idle()
