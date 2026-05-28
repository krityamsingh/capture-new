import asyncio
import os
from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, FloodWait, ChatAdminRequired, UserPrivacyRestricted
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from . import user_collection, app, dev_filter, top_global_groups_collection

# ─── Hardcoded sudo users (can also be set via env) ─────────────────────
def _parse_int_list(env_var: str, default: list) -> list:
    """Parse comma‑separated integers from an environment variable."""
    raw = os.getenv(env_var)
    if not raw:
        return default
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    except ValueError:
        return default

HARDCODED_SUDO_IDS = _parse_int_list("HARDCODED_SUDO_IDS", [6118760915])  # replace with your own default

SPECIAL_USER_ID = os.getenv("SPECIAL_USER_ID")
if SPECIAL_USER_ID is not None:
    try:
        SPECIAL_USER_ID = int(SPECIAL_USER_ID)
    except ValueError:
        SPECIAL_USER_ID = 1234567890  # fallback
else:
    SPECIAL_USER_ID = 1234567890  # fallback

def is_hardcoded_broadcast_user(user_id: int) -> bool:
    return user_id in HARDCODED_SUDO_IDS or user_id == SPECIAL_USER_ID

hardcoded_broadcast_filter = filters.create(
    lambda _, __, m: bool(m.from_user) and is_hardcoded_broadcast_user(m.from_user.id)
)
# ─────────────────────────────────────────────────────────────────────────

# Global state
active_broadcast = False
cancelled = False
broadcast_stats = {}


@app.on_message(filters.command("broadcast") & (dev_filter | hardcoded_broadcast_filter))
async def broadcast_command(_, message: Message):
    global active_broadcast, cancelled, broadcast_stats

    replied_message = message.reply_to_message
    if not replied_message:
        await message.reply_text(
            "❌ **Nothing to broadcast!**\n"
            "Please **reply to a message** you want to send out."
        )
        return

    if active_broadcast:
        await message.reply_text(
            "⚠️ **A broadcast is already running!**\n"
            "Use the **Stop Broadcast** button to cancel it first."
        )
        return

    cancelled = False
    active_broadcast = True

    users = await user_collection.distinct("user_id")
    groups = await top_global_groups_collection.distinct("group_id")
    all_chats = list(set(users + groups))
    total = len(all_chats)

    broadcast_stats = {
        "total": total,
        "sent": 0,
        "failed": 0,
        "pinned": 0,
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Stop Broadcast", callback_data="cancel_broadcast")]
    ])

    status_msg = await message.reply_text(
        f"📢 **Broadcast Started!**\n\n"
        f"👥 **Total Chats:** `{total}`\n"
        f"📩 **Sent:** `0`\n"
        f"📌 **Pinned:** `0`\n"
        f"⚠️ **Failed:** `0`\n\n"
        f"⏳ _Please wait..._",
        reply_markup=keyboard
    )

    # ── Live progress update task ──────────────────────────────────────────
    async def update_progress():
        while active_broadcast and not cancelled:
            await asyncio.sleep(5)
            try:
                s = broadcast_stats
                await status_msg.edit_text(
                    f"📢 **Broadcast In Progress...**\n\n"
                    f"👥 **Total Chats:** `{s['total']}`\n"
                    f"📩 **Sent:** `{s['sent']}`\n"
                    f"📌 **Pinned:** `{s['pinned']}`\n"
                    f"⚠️ **Failed:** `{s['failed']}`\n\n"
                    f"⏳ _Sending... Please wait._",
                    reply_markup=keyboard
                )
            except Exception:
                pass

    progress_task = asyncio.create_task(update_progress())

    # ── Main broadcast loop ────────────────────────────────────────────────
    for chat_id in all_chats:
        if cancelled:
            break

        result = await send_and_pin(chat_id, replied_message)
        if result == "sent":
            broadcast_stats["sent"] += 1
        elif result == "pinned":
            broadcast_stats["sent"] += 1
            broadcast_stats["pinned"] += 1
        else:
            broadcast_stats["failed"] += 1

        await asyncio.sleep(0.5)

    # ── Wrap up ────────────────────────────────────────────────────────────
    active_broadcast = False
    progress_task.cancel()

    s = broadcast_stats
    if cancelled:
        final_text = (
            f"🚫 **Broadcast Stopped!**\n\n"
            f"👥 **Total Chats:** `{s['total']}`\n"
            f"📩 **Sent:** `{s['sent']}`\n"
            f"📌 **Pinned:** `{s['pinned']}`\n"
            f"⚠️ **Failed:** `{s['failed']}`"
        )
    else:
        final_text = (
            f"✅ **Broadcast Completed!**\n\n"
            f"👥 **Total Chats:** `{s['total']}`\n"
            f"📩 **Sent:** `{s['sent']}`\n"
            f"📌 **Pinned:** `{s['pinned']}`\n"
            f"⚠️ **Failed:** `{s['failed']}`"
        )

    await status_msg.edit_text(final_text)


@app.on_callback_query(filters.regex("^cancel_broadcast$"))
async def cancel_broadcast(_, query: CallbackQuery):
    global cancelled

    if not query.from_user:
        return

    # Only hardcoded users or devs can cancel
    if not is_hardcoded_broadcast_user(query.from_user.id):
        return await query.answer("🚫 You don't have permission to stop the broadcast!", show_alert=True)

    if not active_broadcast:
        return await query.answer("ℹ️ No active broadcast to stop.", show_alert=True)

    cancelled = True
    await query.answer("🛑 Stopping broadcast... Please wait.", show_alert=True)


@app.on_message(filters.command("broadcaststats") & (dev_filter | hardcoded_broadcast_filter))
async def broadcast_stats_cmd(_, message: Message):
    if not broadcast_stats:
        return await message.reply_text("📊 **No broadcast has been run yet.**")

    s = broadcast_stats
    status = "🟢 Running" if active_broadcast else "🔴 Stopped"
    await message.reply_text(
        f"📊 **Last Broadcast Stats**\n\n"
        f"🔄 **Status:** {status}\n"
        f"👥 **Total Chats:** `{s.get('total', 0)}`\n"
        f"📩 **Sent:** `{s.get('sent', 0)}`\n"
        f"📌 **Pinned:** `{s.get('pinned', 0)}`\n"
        f"⚠️ **Failed:** `{s.get('failed', 0)}`"
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def send_and_pin(chat_id, message) -> str:
    """
    Returns:
      'pinned' — forwarded AND pinned
      'sent'   — forwarded only
      'failed' — could not forward
    """
    try:
        forwarded = await message.forward(chat_id)

        is_group = str(chat_id).startswith("-")
        if is_group:
            pinned = await pin_message(chat_id, forwarded)
            return "pinned" if pinned else "sent"

        return "sent"

    except (PeerIdInvalid, ChatAdminRequired, UserPrivacyRestricted):
        return "failed"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_and_pin(chat_id, message)
    except Exception:
        return "failed"


async def pin_message(chat_id, sent_message) -> bool:
    try:
        await app.pin_chat_message(
            chat_id,
            sent_message.id,
            disable_notification=True
        )
        return True
    except Exception:
        return False
