import random 
from . import db, app, sudo_filter
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import Client, filters
import time
from . import capsify
from .watchers import block_watcher
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

dic1 = {}
dic2 = {}
t_block = {}
bdb = db.block

# Tracking spam and block status
temp_block = {}  # Stores temporarily blocked users
msg_count = {}  # Tracks text spam count
sticker_count = {}  # Tracks sticker spam count
media_count = {}  # Tracks media spam count
last_msg_time = {}  # Stores last message timestamp
unblock_requests = {}  # Stores unblock requests

def is_temp_blocked(user_id):
    """Check if a user is temporarily blocked."""
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return True
    temp_block.pop(user_id, None)  # Remove if expired
    return False

@app.on_message(filters.group, group=block_watcher)
async def anti_flood(_, m: Message):
    if not m.from_user:
        return

    user_id = m.from_user.id
    mention = f"[{m.from_user.first_name}](tg://user?id={user_id})"
    current_time = time.time()

    if is_temp_blocked(user_id):
        return  # Ignore messages from blocked users

    # Reset spam count if 10 sec have passed
    if user_id in last_msg_time and (current_time - last_msg_time[user_id]) > 10:
        msg_count[user_id] = 0
        sticker_count[user_id] = 0
        media_count[user_id] = 0

    # Detect message type
    is_text = bool(m.text)
    is_sticker = bool(m.sticker)
    is_media = bool(m.photo or m.video or m.document)

    # If messages are coming within 2 seconds, increase spam count
    if user_id in last_msg_time and (current_time - last_msg_time[user_id]) <= 2:
        if is_text:
            msg_count[user_id] = msg_count.get(user_id, 0) + 1
        if is_sticker:
            sticker_count[user_id] = sticker_count.get(user_id, 0) + 1
        if is_media:
            media_count[user_id] = media_count.get(user_id, 0) + 1
    else:
        msg_count[user_id] = 1 if is_text else 0
        sticker_count[user_id] = 1 if is_sticker else 0
        media_count[user_id] = 1 if is_media else 0

    last_msg_time[user_id] = current_time  # Update last message time

    # Block user if they spam:
    if msg_count[user_id] >= 4 or sticker_count[user_id] >= 5 or media_count[user_id] >= 4:
        if user_id not in temp_block:
            temp_block[user_id] = current_time + 300  # First block: 5 min
            block_time = "5 minutes"
        else:
            temp_block[user_id] += 300  # Increase block time for repeated offense
            block_time = "10 minutes" if temp_block[user_id] < current_time + 600 else "15 minutes"

        msg_count[user_id] = 0  # Reset counts after block
        sticker_count[user_id] = 0
        media_count[user_id] = 0

        # Notify user about their block
        txt = (
            f"**Ara Ara {mention}, you've been quite the naughty spammer!** ❤️\n\n"
            f"🚧 **You are blocked for {block_time} due to excessive spamming!** ⚠️\n"
            f"💢 **Spamming includes rapid text, stickers, and media flood!**"
        )
        await m.reply(txt, disable_web_page_preview=True)


# 🔹 Free Command - Allows Sudo Users to Unblock Any User
@app.on_message(filters.command("free") & sudo_filter)
async def free_user(client: Client, message: Message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        user_id = int(message.command[1])
    else:
        return await message.reply("⚠️ **Please provide a user ID or reply to a blocked user's message!**\nExample: `/free 123456789`")

    if user_id in temp_block:
        temp_block.pop(user_id)
        await message.reply(f"✅ **User [{user_id}](tg://user?id={user_id}) has been unblocked!**")
    else:
        await message.reply("❌ **This user is not blocked!**")

# 🔹 Request Command - Users Can Request to Be Unblocked
@app.on_message(filters.command("brequest"))
async def request_unblock(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in temp_block:
        return await message.reply("❌ **You are not blocked, so you don't need to request an unblock!**")

    if user_id in unblock_requests:
        return await message.reply("⚠️ **You have already requested an unblock. Please wait!**")

    unblock_requests[user_id] = True

    sudo_users = [7861332030]  # Replace with actual sudo user IDs
    sudo_mentions = " ".join([f"[Admin](tg://user?id={uid})" for uid in sudo_users])

    request_msg = await message.reply(
        f"⚠️ **Unblock Request Received!**\n\n"
        f"👤 **User:** [{message.from_user.first_name}](tg://user?id={user_id})\n"
        f"🔒 **Blocked Status:** Active\n\n"
        f"📢 {sudo_mentions}, please review this request.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Release", callback_data=f"release_{user_id}")]]
        )
    )


# 🔹 Callback for Releasing Users from Block
@app.on_callback_query(filters.regex(r"release_(\d+)") & sudo_filter)
async def release_user_callback(client: Client, callback_query):
    user_id = int(callback_query.data.split("_")[1])

    if user_id in temp_block:
        temp_block.pop(user_id)
        unblock_requests.pop(user_id, None)

        await callback_query.message.edit_text(
            f"✅ **User [ID: {user_id}] has been unblocked by {callback_query.from_user.mention}!**"
        )
        await callback_query.answer("User has been unblocked!", show_alert=True)
    else:
        await callback_query.answer("This user is not blocked!", show_alert=True)

async def block(user_id):
    await bdb.insert_one({'user_id': user_id})

async def is_blocked(user_id) -> bool:
    x = await bdb.find_one({'user_id': user_id})
    return bool(x)

async def unblock(user_id):
    await bdb.delete_one({'user_id': user_id})

async def save_block_reason(user_id: int, reason: str):
    await bdb.update_one(
        {'user_id': user_id},
        {'$set': {'reason': reason}},
        upsert=True
    )
async def get_block_reason(user_id):
    result = await bdb.find_one(
        {'user_id': user_id},
        {'reason': 1}
    )
    return result.get('reason') if result else None

@app.on_message(filters.command("block") & sudo_filter)
async def block_command(client, message: Message):
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        try:
            target_id = int(message.text.split()[1])
            target_user = await client.get_users(target_id)
        except:
            return await message.reply(capsify("Either reply to a user or provide an ID."))

    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    target_id = target_user.id

    reason = None
    if "-r" in message.text:
        reason_start_index = message.text.index("-r") + 3
        reason = message.text[reason_start_index:].strip()

    if await is_blocked(target_id):
        return await message.reply(capsify(f"{user_mention} is already blocked. ❌"))

    # Block the user
    await block(target_id)
    
    if reason:
        await save_block_reason(target_id, reason)

    # Block messages with a teasing touch
    block_messages = [
        f"**Ara Ara~ {user_mention}, you’ve been a naughty one!** ❤️\n\n🚧 **Blocked for mischief.** Behave next time! ⚠️",
        f"**Oops, {user_mention}!** 😏\n\nYou've been **blocked** for causing trouble. Try being nice next time!",
        f"**Sayōnara, {user_mention}!** 👋\n\n🚫 You are now **blocked**. Better luck next time!",
        f"**Oh dear, {user_mention}, did you break the rules?** 😢\n\n🚷 You are **blocked** until further notice.",
        f"**Baka {user_mention}!** 🤨\n\nYou thought you could get away with it? **Blocked!** 🚧"
    ]
    
    block_message = random.choice(block_messages)

    # Unlock button for sudo users
    unlock_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 Unlock User", callback_data=f"unblock:{target_id}")]
    ])

    # Send block message with button
    await message.reply(capsify(block_message), reply_markup=unlock_button)

    # DM notification
    dm_message = f"**You have been blocked from using this bot.** 🚫\n\nReason: {reason or 'Not specified'}"
    try:
        await client.send_message(target_id, capsify(dm_message))
    except:
        pass  # Ignore if the user has DMs closed

    # Log block details
    admin = message.from_user.mention if message.from_user else "Unknown Admin"
    log_message = (
        f"🛑 **User Blocked!**\n\n"
        f"👤 **User:** {user_mention} (`{target_id}`)\n"
        f"🎭 **Blocked By:** {admin}\n"
        f"📌 **Reason:** {reason or 'Not specified'}\n"
        f"⏳ **Time:** {time.ctime()}"
    )
    print(log_message)  # Replace with actual logging if needed

@app.on_callback_query(filters.regex(r"^unblock:(\d+)") & sudo_filter)
async def unblock_user(client, callback_query):
    target_id = int(callback_query.data.split(":")[1])
    user = await client.get_users(target_id)
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"

    if not await is_blocked(target_id):
        return await callback_query.answer("User is not blocked!", show_alert=True)

    # Unblock the user
    await unblock(target_id)

    # Send success message
    await callback_query.message.edit_text(
        capsify(f"🔓 **{user_mention} has been unlocked!**\n\nThey can now use the bot again."),
        reply_markup=None
    )

    # Notify user in DM
    try:
        await client.send_message(target_id, capsify("You have been **unblocked**! 🎉\nYou can now use the bot again."))
    except:
        pass  # Ignore if the user has DMs closed

@app.on_message(filters.command("unblock") & sudo_filter)
async def unblock_command(client, message: Message):
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        try:
            target_id = int(message.text.split()[1])
            target_user = await client.get_users(target_id)
        except:
            return await message.reply(capsify("Either reply to a user or provide an ID."))

    user_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    target_id = target_user.id

    if not await is_blocked(target_id):
        return await message.reply(capsify(f"❌ {user_mention} is **not blocked.**"))

    # Unblock the user
    await unblock(target_id)

    # Random anime-style unblock messages
    unblock_messages = [
        f"**Ara Ara~ {user_mention}, looks like you've been forgiven!** ❤️\n\n🔓 **Unblocked!** Behave this time, okay? 😉",
        f"**Baka {user_mention}!** 😏\n\nYour **banishment has ended**! Welcome back, don’t mess up again! 🏆",
        f"**Oh? {user_mention} is back?!** 😲\n\n🚪 **Unblocked!** Let's hope you behave now!",
        f"**Surprise, {user_mention}!** 🎉\n\nYou are now **free to use the bot again!** Don't get blocked again!",
        f"**The gates have reopened, {user_mention}.** 🏰\n\nYou're **unblocked!** Make the most of your second chance!"
    ]
    
    unblock_message = random.choice(unblock_messages)

    # Send unblock message in group
    await message.reply(capsify(unblock_message))

    # Notify user in PM
    try:
        await client.send_message(target_id, capsify(f"**Good news, {user_mention}!** 🎊\n\nYou have been **unblocked** and can use the bot again!"))
    except:
        pass  # Ignore if user has DMs closed

    # Log unblock details
    admin = message.from_user.mention if message.from_user else "Unknown Admin"
    log_message = (
        f"✅ **User Unblocked!**\n\n"
        f"👤 **User:** {user_mention} (`{target_id}`)\n"
        f"🛠 **Unblocked By:** {admin}\n"
        f"⏳ **Time:** {time.ctime()}"
    )
    print(log_message)  # Replace with actual logging if needed

block_dic = {}

def block_dec(func):
    async def wrapper(client, message: Message):
        user_id = message.from_user.id
        mention = f"[{message.from_user.first_name}](tg://user?id={user_id})"

        if await is_blocked(user_id) or user_id in block_dic:
            reason = await get_block_reason(user_id)

            blocked_messages = [
                f"**Ara Ara~ {mention}, you naughty little thing!** 😏\n\n🚫 **You've been blocked!**\n💢 **Reason:** {reason or 'Not specified'}",
                f"**Oh no, {mention}!** 🫣\n\nYou've been **blocked from my service!** Behave next time, okay? 😘\n🛑 **Reason:** {reason or 'Not specified'}",
                f"**Baka! {mention}** 😡\n\n💀 **You're banned from using me!**\n🔪 **Reason:** {reason or 'Not specified'}\nTry begging me for mercy. Maybe I'll forgive you. 😈",
                f"**Uh-oh, {mention} got the boot!** 🚪\n\n😈 **You’ve been blocked from using me!**\n💢 **Reason:** {reason or 'Not specified'}\nGuess you made me mad! 😤"
            ]

            return await message.reply(capsify(random.choice(blocked_messages)))

        return await func(client, message)
    return wrapper


def block_cbq(func):
    async def wrapper(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        mention = f"[{callback_query.from_user.first_name}](tg://user?id={user_id})"

        if await is_blocked(user_id) or user_id in block_dic:
            reason = await get_block_reason(user_id)

            blocked_alerts = [
                f"**Ara Ara~ {mention}, you've been naughty!** 🚫\n\n💢 **You're blocked!** Reason: {reason or 'Not specified'}",
                f"**Oops! {mention}, you are forbidden from my services!** 🛑\n\n💢 **Blocked!** Reason: {reason or 'Not specified'}",
                f"**Baka {mention}, I don’t allow bad users like you!** 😏\n\n💀 **You are banned!** Reason: {reason or 'Not specified'}",
                f"**Nuh-uh, {mention}, you're locked out!** 🔒\n\n🚷 **Blocked!** Reason: {reason or 'Not specified'}"
            ]

            return await callback_query.answer(capsify(random.choice(blocked_alerts)), show_alert=True)

        return await func(client, callback_query)
    return wrapper

async def get_all_blocked_users():
    blocked_users = await db.block.find().to_list(None)
    return [user['user_id'] for user in blocked_users]

@app.on_message(filters.command("blocklist") & sudo_filter)
async def blocklist_command(client: Client, message: Message):
    blocked_users = await db.block.find().to_list(None)
    
    if not blocked_users:
        return await message.reply(capsify("No users are currently blocked."))

    user_list = "\n".join(
        [
            f" **[{user['first_name']}](tg://user?id={user['user_id']})** (`{user['user_id']}`)\n   💢 **Reason:** {user.get('reason', 'Not specified')}"
            for user in blocked_users
        ]
    )

    text = capsify(f"**Blocked Users List** 🚫\n\n{user_list}")

    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🚪 Close", callback_data=f"close_blocklist_{message.from_user.id}")]]
        )
    )


@app.on_callback_query(filters.regex(r"close_blocklist_(\d+)"))
async def close_callback(client: Client, callback_query: CallbackQuery):
    command_user_id = int(callback_query.data.split("_")[1])
    caller_user_id = callback_query.from_user.id
    mention = f"[{callback_query.from_user.first_name}](tg://user?id={caller_user_id})"

    if caller_user_id != command_user_id:
        reason = await get_block_reason(caller_user_id)
        reason_text = f"Reason: {reason}" if reason else "Reason: Not specified."
        await callback_query.answer(
            capsify(f"**Who are you to tell me what to do, {mention}?** 😏\n\n💢 {reason_text}"), 
            show_alert=True
        )
        return

    await callback_query.message.delete()
    await callback_query.answer(capsify("🚪 Blocklist Closed"), show_alert=False)

from telegram import Update
from telegram.ext import CallbackContext

def block_dec_ptb(func):
    async def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and (await is_blocked(user_id) or user_id in block_dic):
            return
        return await func(update, context)
    return wrapper

def block_cbq_ptb(func):
    async def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and (await is_blocked(user_id) or user_id in block_dic):
            reason = await get_block_reason(user_id)
            reason_text = f"Reason: {reason}" if reason else "Reason: Not specified."
            await update.callback_query.answer(
                capsify(f"You have been blocked.\n{reason_text}"), 
                show_alert=True
            )
            return
        return await func(update, context)
    return wrapper

def block_inl_ptb(func):
    async def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and (await is_blocked(user_id) or user_id in block_dic):
            reason = await get_block_reason(user_id)
            reason_text = f"Reason: {reason}" if reason else "Reason: Not specified."
            await update.inline_query.answer(capsify(f"You have been blocked.\n{reason_text}"))
            return
        return await func(update, context)
    return wrapper
