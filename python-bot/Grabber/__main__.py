import importlib
import asyncio
import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext

# Support group and sudo users
SUPPORT_GROUP_ID = -1003695209406
SUDO_USERS = [6118760915]

# Video & Buttons
VIDEO_URL = "https://files.catbox.moe/etymbj.mp4"
ADD_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ ʙᴀʙʏ", url="https://t.me/CaptureCharacterBot?startgroup=true")]]
)


# Boot message — sends video with high timeouts, falls back to text if it times out
async def notify_support_group(context: CallbackContext, status="Booting") -> None:
    from Grabber import application
    try:
        ping = round(time.time() - context.job.data, 3)
        message = f"""
⟳ <b>ᴄʜᴀʀᴀᴄᴛᴇʀ ᴄᴀᴘᴛᴜʀᴇ Bᴏᴏᴛɪɴɢ Uᴘ...</b>
Pʟᴇᴀsᴇ Wᴀɪᴛ ᴀ Mᴏᴍᴇɴᴛ! ⚙️

⟲ <i>Hᴀᴠɪɴɢ ᴛʀᴏᴜʙʟᴇ? Cʜᴇᴄᴋ ᴛʜᴇ ʟᴏɢs ғᴏʀ ᴅᴇᴛᴀɪʟs</i> 🧾

━━━━━━━━━━━━━━━━━━━
<b>⟡ Pʏᴛʜᴏɴ ⋉</b> 3.11.9
<b>⟡ Pᴛʙ ⋉</b> 20.6
<b>⟡ Pʏʀᴏɢʀᴀᴍ ⋉</b> 2.0.106
<b>⟡ Pɪɴɢ ⋉</b> <code>{ping} ms</code>
━━━━━━━━━━━━━━━━━━━
"""
        try:
            await context.bot.send_video(
                chat_id=SUPPORT_GROUP_ID,
                video=VIDEO_URL,
                caption=message,
                reply_markup=ADD_BUTTON,
                parse_mode="HTML",
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
            )
        except Exception:
            # Video timed out — fall back to text
            await context.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                text=message,
                reply_markup=ADD_BUTTON,
                parse_mode="HTML",
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
            )
    except Exception as e:
        print(f"Failed to send boot message to support group: {e}")


async def notify_sudo_users(bot, user_ids, message):
    for user_id in user_ids:
        try:
            user = await bot.get_chat(user_id)
            name = user.first_name
            msg = f"**Kᴏɴɪᴄʜɪᴡᴀ {name} sᴇɴᴘᴀɪ! 🌸**\n{message}"
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify {user_id}: {e}")


async def notify_on_start(context: CallbackContext) -> None:
    await notify_support_group(context, status="Alive")
    await notify_sudo_users(context.bot, SUDO_USERS, "Bot is now online! 🚀")


async def notify_on_stop() -> None:
    from Grabber import application
    for user_id in SUDO_USERS:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text="⚠ Bot is stopping! Please wait...",
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Failed to send stop message to {user_id}: {e}")


async def auto_restart(context: CallbackContext):
    from Grabber import Grabberu
    await notify_sudo_users(context.bot, SUDO_USERS, "♻️ **Auto-Restarting Bot in 5 seconds...**")
    await asyncio.sleep(5)
    Grabberu.restart()


async def restart(update: Update, context: CallbackContext) -> None:
    from Grabber import Grabberu
    if update.effective_user.id not in SUDO_USERS:
        return await update.message.reply_text("🚫 You are not authorized to restart the bot!")
    await update.message.reply_text("🔄 Restarting bot...")
    await notify_on_stop()
    await asyncio.sleep(2)
    Grabberu.restart()


async def main() -> None:
    # Step 1 — build all clients inside the running loop so they all share it
    from Grabber import init_clients
    init_clients()

    # Step 2 — now safe to import modules (they reference Grabber.collection etc.)
    from Grabber.modules import ALL_MODULES
    for module_name in ALL_MODULES:
        importlib.import_module("Grabber.modules." + module_name)

    from Grabber import Grabberu, application

    # Step 3 — start Pyrogram (non-blocking, same loop)
    await Grabberu.start()
    print("Pyrogram client started!")

    # Step 4 — register PTB handlers and start PTB
    application.add_handler(CommandHandler("restarttt", restart))
    await application.initialize()
    await application.start()

    job_queue = application.job_queue
    # 10s delay so bot is settled before hitting catbox.moe
    job_queue.run_once(notify_on_start, when=10, data=time.time())
    job_queue.run_repeating(auto_restart, interval=3600.0, first=3600.0)

    await application.updater.start_polling(drop_pending_updates=True)
    print("Bot fully started!")

    # Keep alive
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await Grabberu.stop()


if __name__ == "__main__":
    asyncio.run(main())
