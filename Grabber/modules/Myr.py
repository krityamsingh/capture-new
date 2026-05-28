from pyrogram import Client, filters
from pyrogram.types import Message
from . import app, user_collection
import humanize
import random

# Tiny caps format
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ', ' ': ' '
}

def to_tiny_caps(text: str) -> str:
    return ''.join(TINY_CAPS.get(c.lower(), c) for c in text)

# Ruby emoji variations
RUBY_EMOJIS = ["💎", "🔮", "🧿", "💠", "🪬", "💜", "💗", "🌌", "🔷", "✨"]

async def get_random_ruby_emoji():
    return random.choice(RUBY_EMOJIS)

@app.on_message(filters.command("myrubies"))
async def check_rubies(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text(to_tiny_caps("⚠️ unable to identify user. please try again."))
        return

    user_id = user.id
    mention = f"[{user.first_name}](tg://user?id={user_id})"

    user_data = await user_collection.find_one(
        {'id': user_id},
        projection={'rubies': 1, 'first_name': 1, 'last_ruby_emoji': 1}
    )

    rubies = user_data.get('rubies', 0) if user_data else 0
    try:
        rubies = float(str(rubies).replace(',', '')) if isinstance(rubies, str) else float(rubies)
    except (ValueError, TypeError):
        rubies = 0.0

    ruby_emoji = user_data.get('last_ruby_emoji') if user_data else None
    if not ruby_emoji or ruby_emoji not in RUBY_EMOJIS:
        ruby_emoji = await get_random_ruby_emoji()
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'last_ruby_emoji': ruby_emoji}},
            upsert=True
        )

    formatted_rubies = humanize.intcomma(rubies)  # Always show full number without converting to words
    rank = (
        "sᴄᴀʀᴄᴇ" if rubies < 50 else
        "ʟᴜᴄᴋʏ ᴏɴᴇ" if rubies < 200 else
        "ɢᴀᴛʜᴇʀᴇʀ" if rubies < 1000 else
        "ʀᴜʙʏ ᴋɪɴɢ" if rubies < 5000 else
        "ᴍʏsᴛɪᴄ ʜᴏʟᴅᴇʀ" if rubies < 10000 else
        "ᴄʀʏsᴛᴀʟ ʟᴏʀᴅ"
    )

    ruby_message = (
        f"♦️ {mention}'s ʀᴜʙʏ ᴄᴏʟʟᴇᴄᴛɪᴏɴ\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──\n\n"
        f"● ᴀᴍᴏᴜɴᴛ ➠ `{formatted_rubies}` {ruby_emoji}\n"
        f"● sᴛᴀᴛᴜs ➠ `{rank}`\n\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──"
    )

    try:
        async for photo in client.get_chat_photos(user_id, limit=1):
            await message.reply_photo(
                photo=photo.file_id,
                caption=ruby_message,
                reply_to_message_id=message.id
            )
            return
    except Exception:
        pass

    await message.reply_text(
        ruby_message,
        reply_to_message_id=message.id
        )

@app.on_message(filters.command("addr") & filters.user(7861332030))
async def add_rubies(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ reply to a user to add rubies."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ provide the amount of rubies to add. example: /addr 100"))
        return

    target_user = message.reply_to_message.from_user
    if not target_user:
        await message.reply_text(to_tiny_caps("⚠️ couldn't identify the target user."))
        return

    target_id = target_user.id

    user_data = await user_collection.find_one({'id': target_id})
    current_rubies = float(user_data.get('rubies', 0)) if user_data else 0

    new_total = current_rubies + amount

    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'rubies': new_total, 'first_name': target_user.first_name}},
        upsert=True
    )

    ruby_emoji = await get_random_ruby_emoji()
    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'last_ruby_emoji': ruby_emoji}},
        upsert=True
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ successfully added {amount} rubies to {target_user.first_name}'s account!"
        )
    )

@app.on_message(filters.command("rpay"))
async def pay_rubies(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ reply to a user to send rubies."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ provide the amount of rubies to send. example: /rpay 100"))
        return

    sender = message.from_user
    receiver = message.reply_to_message.from_user
    
    if not sender or not receiver:
        await message.reply_text(to_tiny_caps("⚠️ couldn't identify users."))
        return
    
    if sender.id == receiver.id:
        await message.reply_text(to_tiny_caps("⚠️ you can't send rubies to yourself."))
        return

    if amount <= 0:
        await message.reply_text(to_tiny_caps("⚠️ amount must be positive."))
        return

    # Get sender's data
    sender_data = await user_collection.find_one({'id': sender.id})
    sender_rubies = float(sender_data.get('rubies', 0)) if sender_data else 0

    if sender_rubies < amount:
        await message.reply_text(to_tiny_caps("⚠️ you don't have enough rubies."))
        return

    # Get receiver's data
    receiver_data = await user_collection.find_one({'id': receiver.id})
    receiver_rubies = float(receiver_data.get('rubies', 0)) if receiver_data else 0

    # Update both accounts
    await user_collection.update_one(
        {'id': sender.id},
        {'$set': {'rubies': sender_rubies - amount}},
        upsert=True
    )

    await user_collection.update_one(
        {'id': receiver.id},
        {'$set': {'rubies': receiver_rubies + amount, 'first_name': receiver.first_name}},
        upsert=True
    )

    # Get random emoji for receiver
    ruby_emoji = await get_random_ruby_emoji()
    await user_collection.update_one(
        {'id': receiver.id},
        {'$set': {'last_ruby_emoji': ruby_emoji}},
        upsert=True
    )

    # Create payment message
    payment_message = (
        f"✨ ʀᴜʙʏ ᴛʀᴀɴsғᴇʀ sᴜᴄᴄᴇssғᴜʟ ✨\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──\n\n"
        f"● ғʀᴏᴍ ➠ [{sender.first_name}](tg://user?id={sender.id})\n"
        f"● ᴛᴏ ➠ [{receiver.first_name}](tg://user?id={receiver.id})\n"
        f"● ᴀᴍᴏᴜɴᴛ ➠ `{humanize.intcomma(amount)}` {ruby_emoji}\n\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──"
    )

    await message.reply_text(
        payment_message,
        reply_to_message_id=message.id
    )
