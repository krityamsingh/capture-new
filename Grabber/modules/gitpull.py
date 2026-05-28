import os
import sys
import subprocess
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from . import app, dev_filter

# Global variable to track automatic restart status
AUTO_RESTART_ENABLED = True
NEXT_RESTART_TIME = datetime.now() + timedelta(hours=1)

# Git Pull Command
@app.on_message(filters.command("gitpull") & dev_filter)
async def git_pull(client, message: Message):
    await message.reply("`⏳ Pulling updates from the repo... please wait.`")

    try:
        github_token = os.environ.get("GITHUB_TOKEN", "")
        pull_url = f"https://{github_token}@github.com/Og-peter/Chut" if github_token else "https://github.com/Og-peter/Chut"
        result = subprocess.run(
            ["git", "pull", pull_url, "main"],
            capture_output=True, text=True, check=True, timeout=60
        )

        if "Already up to date" in result.stdout:
            return await message.reply("✅ **Already up-to-date!**\n\n`No new changes found.`")
        
        elif result.returncode == 0:
            await message.reply(
                f"✅ **Git Pull Successful!**\n\n"
                f"```{result.stdout}```\n\n"
                "`Restarting the bot to apply updates...`"
            )
            await restart_bot(message)

        else:
            await message.reply("❌ **Git pull failed. Please check the logs!**")
            return

    except subprocess.CalledProcessError as e:
        await message.reply(f"❌ **Git Pull Failed!**\n\n```{e.stderr}```")
    except subprocess.TimeoutExpired:
        await message.reply("❌ **Git Pull Timed Out!**\n\n`Check your internet connection and try again.`")
    except Exception as e:
        await message.reply(f"❌ **Unexpected Error Occurred!**\n\n```{str(e)}```")


# Restart Command
@app.on_message(filters.command("restart") & dev_filter)
async def manual_restart(client, message: Message):
    await message.reply("`♻️ Restarting the bot... please wait.`")
    await restart_bot(message)


# Auto Restart Toggle Command
@app.on_message(filters.command("autorestart") & dev_filter)
async def toggle_auto_restart(client, message: Message):
    global AUTO_RESTART_ENABLED, NEXT_RESTART_TIME
    AUTO_RESTART_ENABLED = not AUTO_RESTART_ENABLED
    status = "enabled" if AUTO_RESTART_ENABLED else "disabled"
    if AUTO_RESTART_ENABLED:
        NEXT_RESTART_TIME = datetime.now() + timedelta(hours=1)
    await message.reply(f"🔄 **Auto-restart has been {status}!**\n\n"
                      f"Bot will {'now' if AUTO_RESTART_ENABLED else 'not'} restart automatically every hour.\n"
                      f"Next restart: {NEXT_RESTART_TIME if AUTO_RESTART_ENABLED else 'N/A'}")


# Status Command
@app.on_message(filters.command("restartstatus") & dev_filter)
async def restart_status(client, message: Message):
    status = "enabled" if AUTO_RESTART_ENABLED else "disabled"
    await message.reply(f"🔄 **Auto-restart status:** {status}\n"
                      f"⏰ **Next restart at:** {NEXT_RESTART_TIME if AUTO_RESTART_ENABLED else 'N/A'}")


# Bot Restart Handler
async def restart_bot(message=None):
    try:
        # Small sleep for better UX
        if message:
            await asyncio.sleep(2)
        args = [sys.executable, "-m", "Grabber"]  # Replace 'Grabber' with your bot's main module if needed
        subprocess.Popen(args)
        sys.exit()
    except Exception as e:
        if message:
            await message.reply(f"❌ **Failed to restart the bot!**\n\n```{str(e)}```")


# Automatic Restart Scheduler
async def auto_restart_scheduler():
    global NEXT_RESTART_TIME
    while True:
        if AUTO_RESTART_ENABLED:
            now = datetime.now()
            if now >= NEXT_RESTART_TIME:
                # Send notification if possible
                try:
                    await app.send_message(
                        chat_id="me",  # Or your admin chat ID
                        text=f"🕒 **Scheduled Restart**\n\n"
                            f"Bot is restarting automatically as part of hourly maintenance.\n"
                            f"Next restart at: {datetime.now() + timedelta(hours=1)}"
                    )
                except:
                    pass
                
                NEXT_RESTART_TIME = datetime.now() + timedelta(hours=1)
                await restart_bot()
            
            # Sleep for 1 minute before checking again
            await asyncio.sleep(60)
        else:
            # Check every minute if auto-restart has been enabled
            await asyncio.sleep(60)


# Start the scheduler when the bot starts
async def start_bot():
    # Start the auto-restart scheduler in the background
    asyncio.create_task(auto_restart_scheduler())
    
    # Start the Pyrogram client
    await app.start()
    print("Bot started successfully!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    # This block ensures the scheduler only starts when the script is run directly
    # and not when imported as a module
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
