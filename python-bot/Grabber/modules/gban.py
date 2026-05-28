import asyncio
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from Grabber.utils.gban import (
    add_to_global_ban,
    remove_from_global_ban,
    fetch_globally_banned_users,
    get_all_chats,
    is_user_globally_banned,
    add_to_global_mute,
    remove_from_global_mute,
    fetch_globally_muted_users,
    is_user_globally_muted
)
import time
from . import sudo_filter, capsify, app
from .watchers import gban_watcher, gmute_watcher

# Global variables for tracking
active_gbans = {}
active_gmutes = {}

async def get_user_info(client, user_id):
    try:
        user = await client.get_users(user_id)
        return user.first_name, user.username
    except:
        return f"User-{user_id}", None

async def send_progress_message(client, chat_id, message_id, text):
    try:
        await client.edit_message_text(chat_id, message_id, text)
    except:
        pass

@app.on_message(filters.command(["gban"]) & sudo_filter)
async def gban_user(client, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(capsify("Usage: `/gban <user_id/reply> <reason>`"))
        return

    # Extract user information
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name or f"User-{user_id}"
        reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason provided"
    else:
        try:
            user_id = int(message.command[1])
            user_name = f"User-{user_id}"
            reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
        except ValueError:
            await message.reply_text(capsify("Invalid user ID. Please provide a valid user ID."))
            return

    # Get proper username
    user_name, username = await get_user_info(client, user_id)
    mention = f"[{user_name}](tg://user?id={user_id})" if username else user_name

    # Check if already gbanned
    if await is_user_globally_banned(user_id):
        await message.reply_text(capsify(f"⚠️ {mention} is already globally banned!"))
        return

    # Add to global ban
    await add_to_global_ban(user_id, reason, message.from_user.id)
    all_chats = await get_all_chats()
    total_chats = len(all_chats)
    banned_chats = 0
    failed_chats = 0

    # Initial message with progress
    progress_msg = await message.reply_text(
        capsify(
            f"🚀 **Starting Global Ban**\n"
            f"• Target: {mention}\n"
            f"• Reason: `{reason}`\n"
            f"• Total Chats: `{total_chats}`\n"
            f"• Progress: `0/{total_chats}` (0%)\n"
            f"⏳ Estimated time: ~{total_chats * 0.75:.1f}s"
        )
    )

    start_time = time.time()
    active_gbans[user_id] = {"start": start_time, "total": total_chats}

    # Process banning in chunks
    chunk_size = 10
    for i in range(0, total_chats, chunk_size):
        chunk = all_chats[i:i + chunk_size]
        tasks = []
        
        for chat_id in chunk:
            tasks.append(
                client.ban_chat_member(
                    chat_id,
                    user_id,
                    until_date=datetime.now() + timedelta(days=365)
                )
            )
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    failed_chats += 1
                else:
                    banned_chats += 1
            
            # Update progress
            progress = banned_chats + failed_chats
            percentage = (progress / total_chats) * 100
            
            await send_progress_message(
                client,
                message.chat.id,
                progress_msg.id,
                capsify(
                    f"🚀 **Global Ban Progress**\n"
                    f"• Target: {mention}\n"
                    f"• Reason: `{reason}`\n"
                    f"• Total Chats: `{total_chats}`\n"
                    f"• Banned: `{banned_chats}` | Failed: `{failed_chats}`\n"
                    f"• Progress: `{progress}/{total_chats}` ({percentage:.1f}%)\n"
                    f"⏳ Elapsed: {time.time() - start_time:.1f}s"
                )
            )
            
            await asyncio.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"Error in gban chunk processing: {e}")
            failed_chats += len(chunk)

    # Final result
    duration = time.time() - start_time
    del active_gbans[user_id]

    # Broadcast the gban
    broadcast_text = (
        f"🚨 **Global Ban Notice** 🚨\n\n"
        f"• User: {mention}\n"
        f"• ID: `{user_id}`\n"
        f"• Reason: `{reason}`\n"
        f"• Banned by: {message.from_user.mention}\n"
        f"• Banned in: `{banned_chats}` chats\n"
        f"• Time taken: `{duration:.2f}s`"
    )

    await progress_msg.edit_text(capsify(broadcast_text))
    
    # Broadcast to all chats
    try:
        broadcast_msg = await client.send_message(
            message.chat.id,
            capsify("🌐 Broadcasting ban notice to all chats...")
        )
        
        sent_count = 0
        for chat_id in all_chats:
            try:
                await client.send_message(
                    chat_id,
                    broadcast_text,
                    disable_notification=True
                )
                sent_count += 1
                await asyncio.sleep(0.3)
            except:
                pass
        
        await broadcast_msg.edit_text(
            capsify(f"✅ Broadcast complete! Sent to {sent_count} chats.")
        )
    except Exception as e:
        print(f"Error broadcasting gban: {e}")

@app.on_message(filters.command(["ungban"]) & sudo_filter)
async def ungban_user(client, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(capsify("Usage: `/ungban <user_id/reply>`"))
        return

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text(capsify("Invalid user ID. Please provide a valid user ID."))
            return

    user_name, username = await get_user_info(client, user_id)
    mention = f"[{user_name}](tg://user?id={user_id})" if username else user_name

    if not await is_user_globally_banned(user_id):
        await message.reply_text(capsify(f"ℹ️ {mention} is not globally banned!"))
        return

    # Get ban info
    banned_users = await fetch_globally_banned_users()
    ban_info = next((u for u in banned_users if u["user_id"] == user_id), None)
    reason = ban_info["reason"] if ban_info else "No reason recorded"
    banned_by = ban_info["banned_by"] if ban_info else "Unknown"

    # Start unban process
    all_chats = await get_all_chats()
    total_chats = len(all_chats)
    unbanned_chats = 0
    failed_chats = 0

    progress_msg = await message.reply_text(
        capsify(
            f"🔓 **Starting Global Unban**\n"
            f"• Target: {mention}\n"
            f"• Originally banned for: `{reason}`\n"
            f"• Banned by: `{banned_by}`\n"
            f"• Total Chats: `{total_chats}`\n"
            f"• Progress: `0/{total_chats}` (0%)"
        )
    )

    start_time = time.time()

    # Process unbanning
    for chat_id in all_chats:
        try:
            await client.unban_chat_member(chat_id, user_id)
            unbanned_chats += 1
        except Exception as e:
            failed_chats += 1
        
        # Update progress every 10 chats
        if (unbanned_chats + failed_chats) % 10 == 0:
            progress = unbanned_chats + failed_chats
            percentage = (progress / total_chats) * 100
            
            await send_progress_message(
                client,
                message.chat.id,
                progress_msg.id,
                capsify(
                    f"🔓 **Global Unban Progress**\n"
                    f"• Target: {mention}\n"
                    f"• Total Chats: `{total_chats}`\n"
                    f"• Unbanned: `{unbanned_chats}` | Failed: `{failed_chats}`\n"
                    f"• Progress: `{progress}/{total_chats}` ({percentage:.1f}%)\n"
                    f"⏳ Elapsed: {time.time() - start_time:.1f}s"
                )
            )
        
        await asyncio.sleep(0.3)

    # Remove from global ban
    await remove_from_global_ban(user_id)
    duration = time.time() - start_time

    await progress_msg.edit_text(
        capsify(
            f"✅ **Global Unban Complete**\n"
            f"• User: {mention}\n"
            f"• Unbanned in: `{unbanned_chats}` chats\n"
            f"• Failed in: `{failed_chats}` chats\n"
            f"• Time taken: `{duration:.2f}s`\n"
            f"• Unbanned by: {message.from_user.mention}"
        )
    )

@app.on_message(filters.command(["gmute"]) & sudo_filter)
async def gmute_user(client, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(capsify("Usage: `/gmute <user_id/reply> <reason>`"))
        return

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason provided"
    else:
        try:
            user_id = int(message.command[1])
            reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
        except ValueError:
            await message.reply_text(capsify("Invalid user ID. Please provide a valid user ID."))
            return

    user_name, username = await get_user_info(client, user_id)
    mention = f"[{user_name}](tg://user?id={user_id})" if username else user_name

    if await is_user_globally_muted(user_id):
        await message.reply_text(capsify(f"⚠️ {mention} is already globally muted!"))
        return

    await add_to_global_mute(user_id, reason, message.from_user.id)
    await message.reply_text(
        capsify(
            f"🔇 **Global Mute Applied**\n"
            f"• User: {mention}\n"
            f"• ID: `{user_id}`\n"
            f"• Reason: `{reason}`\n"
            f"• Muted by: {message.from_user.mention}\n\n"
            f"Now this user will be muted in all chats where I'm admin."
        )
    )

@app.on_message(filters.command(["ungmute"]) & sudo_filter)
async def ungmute_user(client, message):
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(capsify("Usage: `/ungmute <user_id/reply>`"))
        return

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text(capsify("Invalid user ID. Please provide a valid user ID."))
            return

    user_name, username = await get_user_info(client, user_id)
    mention = f"[{user_name}](tg://user?id={user_id})" if username else user_name

    if not await is_user_globally_muted(user_id):
        await message.reply_text(capsify(f"ℹ️ {mention} is not globally muted!"))
        return

    await remove_from_global_mute(user_id)
    await message.reply_text(
        capsify(
            f"🔊 **Global Mute Removed**\n"
            f"• User: {mention}\n"
            f"• ID: `{user_id}`\n"
            f"• Unmuted by: {message.from_user.mention}\n\n"
            f"This user can now send messages again."
        )
    )

@app.on_message(filters.command(["gbanlist"]) & sudo_filter)
async def gban_list(client, message):
    banned_users = await fetch_globally_banned_users()
    if not banned_users:
        await message.reply_text(capsify("No users are globally banned."))
        return

    text = "🚨 **Globally Banned Users** 🚨\n\n"
    for user in banned_users[:50]:  # Limit to 50 to avoid message too long
        user_name, username = await get_user_info(client, user["user_id"])
        mention = f"[{user_name}](tg://user?id={user['user_id']})" if username else user_name
        text += (
            f"• {mention}\n"
            f"  ├ ID: `{user['user_id']}`\n"
            f"  ├ Reason: `{user['reason']}`\n"
            f"  └ Banned by: `{user['banned_by']}`\n\n"
        )

    if len(banned_users) > 50:
        text += f"\n...and {len(banned_users) - 50} more."

    await message.reply_text(capsify(text))

@app.on_message(filters.command(["gmotelist"]) & sudo_filter)
async def gmote_list(client, message):
    muted_users = await fetch_globally_muted_users()
    if not muted_users:
        await message.reply_text(capsify("No users are globally muted."))
        return

    text = "🔇 **Globally Muted Users** 🔇\n\n"
    for user in muted_users[:50]:  # Limit to 50
        user_name, username = await get_user_info(client, user["user_id"])
        mention = f"[{user_name}](tg://user?id={user['user_id']})" if username else user_name
        text += (
            f"• {mention}\n"
            f"  ├ ID: `{user['user_id']}`\n"
            f"  ├ Reason: `{user['reason']}`\n"
            f"  └ Muted by: `{user['banned_by']}`\n\n"
        )

    if len(muted_users) > 50:
        text += f"\n...and {len(muted_users) - 50} more."

    await message.reply_text(capsify(text))

@app.on_message(filters.group, group=gban_watcher)
async def check_global_ban(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    if await is_user_globally_banned(user_id):
        try:
            # Get ban info
            banned_users = await fetch_globally_banned_users()
            ban_info = next((u for u in banned_users if u["user_id"] == user_id), None)
            reason = ban_info["reason"] if ban_info else "No reason provided"
            
            # Ban the user
            await client.ban_chat_member(
                message.chat.id,
                user_id,
                until_date=datetime.now() + timedelta(days=365)
            )
            
            # Send alert
            await message.reply_text(
                capsify(
                    f"🚨 **Globally Banned User Detected**\n\n"
                    f"• User: {message.from_user.mention}\n"
                    f"• ID: `{user_id}`\n"
                    f"• Reason: `{reason}`\n\n"
                    f"This user has been banned from this chat."
                )
            )
            
            # Delete the message
            await message.delete()
        except Exception as e:
            print(f"Error handling gban watcher: {e}")

@app.on_message(filters.group, group=gmute_watcher)
async def check_global_mute(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    if await is_user_globally_muted(user_id):
        try:
            # Get mute info
            muted_users = await fetch_globally_muted_users()
            mute_info = next((u for u in muted_users if u["user_id"] == user_id), None)
            reason = mute_info["reason"] if mute_info else "No reason provided"
            
            # Delete the message
            await message.delete()
            
            # Send alert (only once per chat to avoid spam)
            chat_id = message.chat.id
            if chat_id not in active_gmutes.get(user_id, set()):
                if user_id not in active_gmutes:
                    active_gmutes[user_id] = set()
                active_gmutes[user_id].add(chat_id)
                
                alert = await message.reply_text(
                    capsify(
                        f"🔇 **Globally Muted User Detected**\n\n"
                        f"• User: {message.from_user.mention}\n"
                        f"• ID: `{user_id}`\n"
                        f"• Reason: `{reason}`\n\n"
                        f"This user is muted globally. Their messages will be deleted."
                    )
                )
                
                # Remove the alert after some time
                await asyncio.sleep(30)
                try:
                    await alert.delete()
                except:
                    pass
                
                active_gmutes[user_id].discard(chat_id)
        except Exception as e:
            print(f"Error handling gmute watcher: {e}")
