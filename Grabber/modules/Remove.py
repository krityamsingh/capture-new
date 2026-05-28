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

# Owner ID (replace with your actual owner ID)
OWNER_IDS = [8496760733, 7878477646, 6118760915]

@app.on_message(filters.command("rmr") & filters.user(OWNER_IDS))
async def remove_rubies(client: Client, message: Message):
    """Remove rubies from a specific user (owner only)"""
    if not message.reply_to_message:
        await message.reply_text(to_tiny_caps("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ʀᴇᴍᴏᴠᴇ ʀᴜʙɪᴇs."))
        return

    try:
        amount = float(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ᴏғ ʀᴜʙɪᴇs ᴛᴏ ʀᴇᴍᴏᴠᴇ. ᴇxᴀᴍᴘʟᴇ: /rmr 100"))
        return

    target_user = message.reply_to_message.from_user
    if not target_user:
        await message.reply_text(to_tiny_caps("⚠️ ᴄᴏᴜʟᴅɴ'ᴛ ɪᴅᴇɴᴛɪғʏ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴜsᴇʀ."))
        return

    target_id = target_user.id

    user_data = await user_collection.find_one({'id': target_id})
    current_rubies = float(user_data.get('rubies', 0)) if user_data else 0

    new_total = max(0, current_rubies - amount)  # Prevent negative rubies

    await user_collection.update_one(
        {'id': target_id},
        {'$set': {'rubies': new_total, 'first_name': target_user.first_name}},
        upsert=True
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ {amount} ʀᴜʙɪᴇs ғʀᴏᴍ {target_user.first_name}'s ᴀᴄᴄᴏᴜɴᴛ!"
        )
    )

@app.on_message(filters.command("remr") & filters.user(OWNER_IDS))
async def remove_rubies_globally(client: Client, message: Message):
    """Remove fixed amount from all users (owner only)"""
    try:
        amount = float(message.text.split(maxsplit=1)[1])
        if amount <= 0:
            raise ValueError
    except (IndexError, ValueError):
        await message.reply_text(to_tiny_caps("⚠️ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ. ᴇxᴀᴍᴘʟᴇ: /remr 50"))
        return

    # Get count of all users who have rubies
    total_users = await user_collection.count_documents({"rubies": {"$gt": 0}})
    
    if total_users == 0:
        await message.reply_text(to_tiny_caps("⚠️ ɴᴏ ᴜsᴇʀs ᴡɪᴛʜ ʀᴜʙɪᴇs ғᴏᴜɴᴅ."))
        return

    # Update all users' rubies (subtract amount, minimum 0)
    result = await user_collection.update_many(
        {"rubies": {"$gt": 0}},
        [{"$set": {"rubies": {"$max": [{"$subtract": ["$rubies", amount]}, 0]}}}]
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ ʀᴇᴍᴏᴠᴇᴅ {amount} ʀᴜʙɪᴇs ғʀᴏᴍ {result.modified_count} �ᴜsᴇʀs' ᴀᴄᴄᴏᴜɴᴛs!"
        )
    )

@app.on_message(filters.command("removerall") & filters.user(OWNER_IDS))
async def reset_all_rubies(client: Client, message: Message):
    """Reset all users' rubies to 0 (owner only) - without confirmation"""
    # Get count of all users who have rubies
    total_users = await user_collection.count_documents({"rubies": {"$gt": 0}})
    
    if total_users == 0:
        await message.reply_text(to_tiny_caps("⚠️ ɴᴏ ᴜsᴇʀs ᴡɪᴛʜ ʀᴜʙɪᴇs ғᴏᴜɴᴅ."))
        return

    # Reset all rubies to 0 without confirmation
    result = await user_collection.update_many(
        {"rubies": {"$gt": 0}},
        {"$set": {"rubies": 0}}
    )

    await message.reply_text(
        to_tiny_caps(
            f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ ʀᴇsᴇᴛ {result.modified_count} ᴜsᴇʀs' ʀᴜʙɪᴇs ᴛᴏ 0!"
        )
    )
