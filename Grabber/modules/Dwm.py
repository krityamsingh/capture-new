from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta
from . import app, user_collection
import random
import humanize

# Predefined constants for faster access
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ', ' ': ' '
}

# Precomputed tiny caps for common words
PRECOMPUTED_TINY = {
    'daily': 'ᴅᴀɪʟʏ',
    'weekly': 'ᴡᴇᴇᴋʟʏ',
    'monthly': 'ᴍᴏɴᴛʜʟʏ',
    'reward': 'ʀᴇᴡᴀʀᴅ',
    'gold': 'ɢᴏʟᴅ',
    'rubies': 'ʀᴜʙɪᴇs',
    'Oopsie': '⏳ Oᴏᴘsɪᴇ',
    'Moshi Moshi': '⌛ Mᴏsʜɪ Mᴏsʜɪ'
}

REWARD_STICKERS = {
    'daily': "CAACAgIAAxkBAAIIFGgrMJWiPdSK6UPJUhhk4item1ToAAJRXgACq9NBSZmPuaYuHFiHNgQ",
    'weekly': "CAACAgIAAxkBAAIIE2grL1kbUHk0HiOfYlNZhQiAxbaWAAL8YgACy6CISOzLmn2pMUwjNgQ",
    'monthly': "CAACAgUAAxkBAAIIFWgrMPJ5cT0MSul4lYUQ7HyuRdVwAAI-FAAC-1zRVa9ZOsm6MLAfNgQ"
}

GOLD_EMOJIS = ["🪙", "💰", "🏆", "💎", "👑"]
RUBY_EMOJIS = ["💎", "🔮", "🧿", "💠", "🪬"]

REWARDS = {
    'daily': {'gold': (50, 100), 'rubies': (1, 5)},
    'weekly': {'gold': (300, 500), 'rubies': (10, 20)},
    'monthly': {'gold': (1000, 2000), 'rubies': (50, 100)}
}

# Cache for user data to reduce DB calls
user_cache = {}

async def to_tiny_caps(text: str) -> str:
    """Optimized tiny caps conversion with caching"""
    if text in PRECOMPUTED_TINY:
        return PRECOMPUTED_TINY[text]
    return ''.join(TINY_CAPS.get(c.lower(), c) for c in text)

async def get_random_emoji(emoji_list):
    return random.choice(emoji_list)

async def ensure_numeric_fields(user_id):
    """Optimized field checking with cache"""
    if user_id in user_cache:
        return user_cache[user_id]
    
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        user_data = {
            'id': user_id,
            'gold': 0,
            'rubies': 0,
            'first_name': "User",
            'last_daily_claim': None,
            'last_weekly_claim': None,
            'last_monthly_claim': None
        }
        await user_collection.insert_one(user_data)
        user_cache[user_id] = user_data
        return user_data
    
    updates = {}
    if 'gold' not in user_data or not isinstance(user_data['gold'], int):
        updates['gold'] = int(user_data.get('gold', 0))
    if 'rubies' not in user_data or not isinstance(user_data['rubies'], int):
        updates['rubies'] = int(user_data.get('rubies', 0))
    
    for reward_type in ['daily', 'weekly', 'monthly']:
        field = f'last_{reward_type}_claim'
        if field not in user_data:
            updates[field] = None
    
    if updates:
        await user_collection.update_one({'id': user_id}, {'$set': updates})
        user_data.update(updates)
    
    user_cache[user_id] = user_data
    return user_data

async def check_cooldown(user_id, reward_type):
    """Optimized cooldown check with cached data"""
    user_data = await ensure_numeric_fields(user_id)
    cooldown_key = f"last_{reward_type}_claim"
    last_claim = user_data.get(cooldown_key)
    
    if not last_claim:
        return True, None
    
    now = datetime.now()
    if reward_type == 'daily':
        cooldown = timedelta(hours=24)
    elif reward_type == 'weekly':
        cooldown = timedelta(weeks=1)
    else:  # monthly
        cooldown = timedelta(days=30)
    
    if now - last_claim < cooldown:
        return False, last_claim + cooldown
    
    return True, None

def format_time_left(time_left):
    """Optimized time formatting"""
    days = time_left.days
    hours = time_left.seconds // 3600
    minutes = (time_left.seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

async def give_reward(user_id, reward_type):
    """Optimized reward giving with bulk operations"""
    gold = random.randint(*REWARDS[reward_type]['gold'])
    rubies = random.randint(*REWARDS[reward_type]['rubies'])
    
    try:
        user = await app.get_users(user_id)
        first_name = user.first_name
    except Exception:
        first_name = "User"

    update_data = {
        '$inc': {'gold': gold, 'rubies': rubies},
        '$set': {
            f'last_{reward_type}_claim': datetime.now(),
            'first_name': first_name,
            'last_gold_emoji': random.choice(GOLD_EMOJIS),
            'last_ruby_emoji': random.choice(RUBY_EMOJIS)
        }
    }

    result = await user_collection.find_one_and_update(
        {'id': user_id},
        update_data,
        upsert=True,
        return_document=True
    )
    
    # Update cache
    if user_id in user_cache:
        user_cache[user_id].update(result)
    
    return gold, rubies

@app.on_message(filters.command(["daily", "weekly", "monthly"]))
async def claim_rewards(client: Client, message: Message):
    """Optimized reward claiming handler"""
    user = message.from_user
    if not user:
        await message.reply("⚠️ Who are you? I can't see you... B-Baka!!")
        return
    
    reward_type = message.command[0].lower()
    
    # Send sticker immediately without waiting
    sticker_task = client.send_sticker(
        chat_id=message.chat.id,
        sticker=REWARD_STICKERS[reward_type],
        reply_to_message_id=message.id
    )
    
    # Process reward in parallel
    can_claim, next_claim = await check_cooldown(user.id, reward_type)
    if not can_claim:
        time_left = next_claim - datetime.now()
        reply_text = (
            f"⏳ Oopsie! Already claimed {reward_type} reward!\n"
            f"⌛ Next reward in: {format_time_left(time_left)}"
        )
        await message.reply(reply_text)
        return
    
    gold, rubies = await give_reward(user.id, reward_type)
    
    # Prepare optimized response
    reward_msg = (
        f"{reward_type.upper()} REWARD ₓ⋆:°\n\n"
        f"GOLD: {humanize.intcomma(gold)} ₲\n"
        f"RUBIES: {humanize.intcomma(rubies)}\n\n"
        f"UwU~ {user.first_name}, you're so lucky today!\n"
        f"Rewards added to your pocket! Come back soon!"
    )
    
    # Try to send with photo first
    try:
        async for photo in client.get_chat_photos(user.id, limit=1):
            await message.reply_photo(photo.file_id, caption=reward_msg)
            return
    except Exception:
        await message.reply(reward_msg)
