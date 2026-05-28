from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import app, user_collection
import humanize
import random

# Tiny caps (small caps) formatting dictionary
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ', ' ': ' '
}

def to_tiny_caps(text: str) -> str:
    """Convert text to tiny caps (small caps)"""
    return ''.join(TINY_CAPS.get(c.lower(), c) for c in text)

# Gold emoji variations
GOLD_EMOJIS = ["🪙", "💰", "🏆", "💎", "👑", "✨", "🔱", "🤑", "💸", "🫅"]

async def get_random_gold_emoji():
    return random.choice(GOLD_EMOJIS)

# Gold check command
@app.on_message(filters.command("mygold"))
async def check_gold(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text(to_tiny_caps("⚠️ unable to identify user. please try again."))
        return

    user_id = user.id
    mention = f"[{user.first_name}](tg://user?id={user_id})"
    
    # Fetch user data
    user_data = await user_collection.find_one(
        {'id': user_id},
        projection={'gold': 1, 'first_name': 1, 'last_gold_emoji': 1}
    )

    # Get gold amount
    gold_amount = user_data.get('gold', 0) if user_data else 0
    
    try:
        gold_amount = float(str(gold_amount).replace(',', '')) if isinstance(gold_amount, str) else float(gold_amount)
    except (ValueError, TypeError):
        gold_amount = 0.0

    # Get or generate gold emoji
    gold_emoji = user_data.get('last_gold_emoji') if user_data else None
    if not gold_emoji or gold_emoji not in GOLD_EMOJIS:
        gold_emoji = await get_random_gold_emoji()
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'last_gold_emoji': gold_emoji}},
            upsert=True
        )

    # Formatting - always show exact number
    formatted_gold = humanize.intcomma(gold_amount)
    wealth_level = (
        "ʙᴇɢɢᴀʀ" if gold_amount < 100 else
        "ɴᴏᴠɪᴄᴇ" if gold_amount < 500 else
        "ᴛʀᴀᴅᴇʀ" if gold_amount < 2000 else
        "ᴍᴇʀᴄʜᴀɴᴛ" if gold_amount < 5000 else
        "ʟᴏʀᴅ" if gold_amount < 10000 else
        "ᴋɪɴɢ" if gold_amount < 50000 else
        "ᴇᴍᴘᴇʀᴏʀ" if gold_amount < 100000 else
        "ᴅʀᴀɢᴏɴ ʜᴏᴀʀᴅ"
    )

    # Create rich message
    gold_message = (
        f"❖ {mention}'s ᴡᴀʟʟᴇᴛ\n"
        "── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──\n\n"
        f"● ᴀᴍᴏᴜɴᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ➠ `{formatted_gold}` ₲\n"
        f"● sᴛᴀᴛᴜs ➠ `{wealth_level}`\n\n"
        "── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──"
    )

    # Try to send with profile photo
    try:
        async for photo in client.get_chat_photos(user_id, limit=1):
            await message.reply_photo(
                photo=photo.file_id,
                caption=gold_message,
                reply_to_message_id=message.id
            )
            return
    except Exception:
        pass

    # Fallback to text
    await message.reply_text(
        gold_message,
        reply_to_message_id=message.id
    )

# Admin gold add command
@app.on_message(filters.command("addg") & filters.user(7861332030))  # Replace with your owner ID
async def add_gold(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ reply to a user to add gold."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ provide the amount of gold to add. example: /addg 100"))
        return

    target_user = message.reply_to_message.from_user
    if not target_user:
        await message.reply_text(to_tiny_caps("⚠️ couldn't identify the target user."))
        return

    target_id = target_user.id

    user_data = await user_collection.find_one({'id': target_id})
    current_gold = float(user_data.get('gold', 0)) if user_data else 0

    new_total = current_gold + amount

    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'gold': new_total, 'first_name': target_user.first_name}},
        upsert=True
    )

    gold_emoji = await get_random_gold_emoji()
    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'last_gold_emoji': gold_emoji}},
        upsert=True
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ successfully added {humanize.intcomma(amount)} gold to {target_user.first_name}'s account!"
        )
    )

# Gold payment command
@app.on_message(filters.command("gpay"))
async def pay_gold(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ reply to a user to send gold."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ provide the amount of gold to send. example: /gpay 100"))
        return

    sender = message.from_user
    receiver = message.reply_to_message.from_user
    
    if not sender or not receiver:
        await message.reply_text(to_tiny_caps("⚠️ couldn't identify users."))
        return
    
    if sender.id == receiver.id:
        await message.reply_text(to_tiny_caps("⚠️ you can't send gold to yourself."))
        return

    if amount <= 0:
        await message.reply_text(to_tiny_caps("⚠️ amount must be positive."))
        return

    # Get sender's data
    sender_data = await user_collection.find_one({'id': sender.id})
    sender_gold = float(sender_data.get('gold', 0)) if sender_data else 0

    if sender_gold < amount:
        await message.reply_text(to_tiny_caps("⚠️ you don't have enough gold."))
        return

    # Get receiver's data
    receiver_data = await user_collection.find_one({'id': receiver.id})
    receiver_gold = float(receiver_data.get('gold', 0)) if receiver_data else 0

    # Update both accounts
    await user_collection.update_one(
        {'id': sender.id},
        {'$set': {'gold': sender_gold - amount}},
        upsert=True
    )

    await user_collection.update_one(
        {'id': receiver.id},
        {'$set': {'gold': receiver_gold + amount, 'first_name': receiver.first_name}},
        upsert=True
    )

    # Get random emoji for receiver
    gold_emoji = await get_random_gold_emoji()
    await user_collection.update_one(
        {'id': receiver.id},
        {'$set': {'last_gold_emoji': gold_emoji}},
        upsert=True
    )

    # Create payment message
    payment_message = (
        f"✨ ɢᴏʟᴅ ᴛʀᴀɴsғᴇʀ sᴜᴄᴄᴇssғᴜʟ ✨\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──\n\n"
        f"● ғʀᴏᴍ ➠ [{sender.first_name}](tg://user?id={sender.id})\n"
        f"● ᴛᴏ ➠ [{receiver.first_name}](tg://user?id={receiver.id})\n"
        f"● ᴀᴍᴏᴜɴᴛ ➠ `{humanize.intcomma(amount)}` ₲\n\n"
        f"── ⋅ ⋅ ⋅ ⋅ ─── ⋅ ⋅ ─── ⋅ ⋅ ⋅ ⋅ ──"
    )

    await message.reply_text(
        payment_message,
        reply_to_message_id=message.id
)
