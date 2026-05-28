from pyrogram import Client, filters
from pyrogram.types import Message
from Grabber import app, user_collection
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

# Gold emoji variations
GOLD_EMOJIS = ["🪙", "💰", "🏆", "💎", "👑", "✨", "🔱", "🤑", "💸", "🫅"]

async def get_random_gold_emoji():
    return random.choice(GOLD_EMOJIS)

# Owner IDs (list, not set)
OWNER_IDS = [8496760733, 7878477646, 6118760915]

@app.on_message(filters.command("rmg") & filters.user(OWNER_IDS))
async def remove_gold(client: Client, message: Message):
    """Remove gold from a specific user (owner only)"""
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ʀᴇᴍᴏᴠᴇ ɢᴏʟᴅ."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ᴏғ ɢᴏʟᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ. ᴇxᴀᴍᴘʟᴇ: /rmg 100"))
        return

    target_user = message.reply_to_message.from_user
    if not target_user:
        await message.reply_text(to_tiny_caps("⚠️ ᴄᴏᴜʟᴅɴ'ᴛ ɪᴅᴇɴᴛɪғʏ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴜsᴇʀ."))
        return

    target_id = target_user.id

    user_data = await user_collection.find_one({'id': target_id})
    current_gold = float(user_data.get('gold', 0)) if user_data else 0

    new_total = max(0, current_gold - amount)  # Prevent negative gold

    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'gold': new_total, 'first_name': target_user.first_name}},
        upsert=True
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ {amount} ɢᴏʟᴅ ғʀᴏᴍ {target_user.first_name}'s ᴀᴄᴄᴏᴜɴᴛ!"
        )
    )

@app.on_message(filters.command("remg") & filters.user(OWNER_IDS))
async def remove_gold_globally(client: Client, message: Message):
    """Remove fixed amount from all users (owner only)"""
    try:
        amount = float(message.text.split(maxsplit=1)[1])
        if amount <= 0:
            raise ValueError
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ. ᴇxᴀᴍᴘʟᴇ: /remg 50"))
        return

    # Get count of all users who have gold
    total_users = await user_collection.count_documents({"gold": {"$gt": 0}})
    
    if total_users == 0:
        await message.reply_text(to_tiny_caps("⚠️ ɴᴏ ᴜsᴇʀs ᴡɪᴛʜ ɢᴏʟᴅ ғᴏᴜɴᴅ."))
        return

    # Update all users' gold (subtract amount, minimum 0)
    result = await user_collection.update_many(
        {"gold": {"$gt": 0}},
        [{"$set": {"gold": {"$max": [{"$subtract": ["$gold", amount]}, 0]}}}]
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ ʀᴇᴍᴏᴠᴇᴅ {amount} ɢᴏʟᴅ ғʀᴏᴍ {result.modified_count} ᴜsᴇʀs' ᴀᴄᴄᴏᴜɴᴛs!"
        )
    )

@app.on_message(filters.command("removegoldall") & filters.user(OWNER_IDS))
async def reset_all_gold(client: Client, message: Message):
    """Reset all users' gold to 0 (owner only) - without confirmation"""
    # Get count of all users who have gold
    total_users = await user_collection.count_documents({"gold": {"$gt": 0}})
    
    if total_users == 0:
        await message.reply_text(to_tiny_caps("⚠️ ɴᴏ ᴜsᴇʀs ᴡɪᴛʜ ɢᴏʟᴅ ғᴏᴜɴᴅ."))
        return

    # Reset all gold to 0 without confirmation
    result = await user_collection.update_many(
        {"gold": {"$gt": 0}},
        {"$set": {"gold": 0}}
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇsᴇᴛ {result.modified_count} ᴜsᴇʀs' ɢᴏʟᴅ ᴛᴏ 0!"
        )
    )
