import re
import time
import asyncio
import random
import string
from cachetools import TTLCache
from pymongo import DESCENDING
from telegram import Update, InlineQueryResultPhoto as IQP, InlineQueryResultVideo as IQV
from telegram.ext import InlineQueryHandler, CallbackContext

from . import user_collection, collection, application, db
from .block import block_inl_ptb

# Concurrency lock
lock = asyncio.Lock()

# Indexes
db.characters.create_index([('id', DESCENDING)])
db.characters.create_index([('anime', DESCENDING)])
db.characters.create_index([('img_url', DESCENDING)])
db.user_collection.create_index([('characters.id', DESCENDING)])
db.user_collection.create_index([('characters.name', DESCENDING)])

# Caches with optimized TTLs
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)
user_profile_cache = TTLCache(maxsize=10000, ttl=3600)
rarity_characters_cache = TTLCache(maxsize=100, ttl=3600)
search_results_cache = TTLCache(maxsize=1000, ttl=300)
anime_counts_cache = TTLCache(maxsize=10000, ttl=3600)
character_details_cache = TTLCache(maxsize=50000, ttl=3600)

# Emoji Maps
rarity_map = {
    '🔴 Common': '🔴', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧',
    '🟡 Legendary': '🟡', '⚪ Epic': '⚪', '🟠 Rare': '🟠', '🔵 Uncommon': '🔵',
    '🏵️ Exotic': '🏵️', '⚜️ Animated': '⚜️', '🌼 Celebrity': '🌼', '🎐 Crystal': '🎐', '🍹 Neon': '🍹', '🧿 Supreme': '🧿',
    '⚡ Thundra': '⚡', '🛸 Galvoria': '🛸', '🔮 Arcane Verse': '🔮', '🫧 Aether Verse': '🫧',
    '🟡 Solar Verse': '🟡'
}
emoji_to_rarity = {v: k for k, v in rarity_map.items()}
event_map = {
    '💉': '💉𝑵𝒖𝒓𝒔𝒆💉',
    '🐰': '🐰𝑩𝒖𝒏𝒏𝒚🐰',
    '🧹': '🧹𝑴𝒂𝒊𝒅🧹',
    '🎃': '🎃𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏🎃',
    '🎄': '🎄𝑪𝒉𝒓𝒊𝒔𝒕𝒎𝒂𝒔🎄',
    '🎩': '🎩𝑻𝒖𝒙𝒆𝒅𝒐🎩',
    '☃️': '☃️𝑾𝒊𝒏𝒕𝒆𝒓☃️',
    '👘': '👘𝑲𝒊𝒎𝒐𝒏𝒐👘',
    '🎒': '🎒𝑺𝒄𝒉𝒐𝒐𝒍🎒',
    '🥻': '🥻𝑺𝒂𝒓𝒆𝒆🥻',
    '🏖': '🏖𝒔𝒖𝒎𝒎𝒆𝒓🏖',
    '🏀': '🏀𝑩𝒂𝒔𝒌𝒆𝒕𝒃𝒂𝒍𝒍🏀',
    '⚽': '⚽𝑭𝒐𝒐𝒕𝒃𝒂𝒍𝒍⚽',
    '🏜️': '🏜️𝑬𝒈𝒚𝒑𝒕🏜️',
    '💞': '💞𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆💞',
    '👥': '👥𝐃𝐮𝐨👥',
    '🤝': '🤝𝐆𝐫𝐨𝐮𝐩🤝',
    '🏮': '🏮𝑪𝒉𝒊𝒏𝒆𝒔𝒆🏮',
    '📙': '📙𝑴𝒂𝒏𝒉𝒘𝒂📙',
    '👙': '👙𝑩𝒊𝒌𝒊𝒏𝒊👙',
    '🎊': '🎊𝑪𝒉𝒆𝒆𝒓𝒍𝒆𝒂𝒅𝒆𝒓𝒔🎊',
    '🎮': '🎮𝑮𝒂𝒎𝒆🎮',
    '💍': '💍𝑴𝒂𝒓𝒓𝒊𝒆𝒅💍',
    '👶': '👶𝑪𝒉𝒊𝒃𝒊👶',
    '🕷️': '🕷️𝑺𝒑𝒊𝒅𝒆𝒓🕷️',
    '🔞': '🔞𝑵𝒖𝒅𝒆𝒔🔞',
    '🎗️': '🎗️𝑪𝒐𝒍𝒍𝒆𝒄𝒕𝒐𝒓🎗️',
    '⛩️': '⛩️𝑺𝒉𝒊𝒏𝒕𝒐⛩️',
    '🎆': '🎆𝑭𝒊𝒓𝒆𝒘𝒐𝒓𝒌𝒔🎆',
    '⚔️': '⚔️𝑾𝒂𝒓𝒓𝒊𝒐𝒓⚔️',
    '⛷️': '⛷️𝑺𝒌𝒊⛷️',
    '🧛': '🧛𝑽𝒂𝒎𝒑𝒊𝒓𝒆🧛',
    '🐉': '🐉𝑫𝒓𝒂𝒈𝒐𝒏🐉',
    '🌑': '🌑𝒏𝒖𝒏🌑',
    '🏐': '🏐𝑽𝒐𝒍𝒍𝒆𝒚𝒃𝒂𝒍𝒍🏐'
}

def generate_unique_id():
    """Generate a unique ID combining timestamp and random string"""
    timestamp = int(time.time() * 1000)
    rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"{timestamp}_{rand_str}"

def clear_all_caches():
    """Clear all caches to free memory"""
    all_characters_cache.clear()
    user_collection_cache.clear()
    user_profile_cache.clear()
    rarity_characters_cache.clear()
    search_results_cache.clear()
    anime_counts_cache.clear()
    character_details_cache.clear()

async def get_character_details(char_id):
    """Get character details with caching"""
    cached = character_details_cache.get(char_id)
    if cached:
        return cached
    
    char = await collection.find_one(
        {'id': char_id},
        {'name': 1, 'anime': 1, 'img_url': 1, 'video_url': 1, 'rarity': 1, 'price': 1}
    )
    
    if char:
        character_details_cache[char_id] = char
    return char

async def get_anime_count(anime_name):
    """Get count of characters in an anime with caching"""
    cached = anime_counts_cache.get(anime_name)
    if cached:
        return cached
    
    count = await collection.count_documents({'anime': anime_name})
    anime_counts_cache[anime_name] = count
    return count

async def get_characters_by_rarity(rarity_name):
    """Get characters by rarity with optimized query"""
    cached = rarity_characters_cache.get(rarity_name)
    if cached:
        return cached
    
    filters = {"rarity": rarity_name}
    if rarity_name == "⚜️ Animated":
        filters["video_url"] = {"$ne": ""}
    elif rarity_name == "☀️ Summer[Su]":
        filters["img_url"] = {"$ne": ""}
    
    chars = await collection.find(
        filters,
        {'name': 1, 'anime': 1, 'img_url': 1, 'video_url': 1, 'id': 1, 'rarity': 1, 'price': 1}
    ).limit(100).to_list(length=100)
    
    rarity_characters_cache[rarity_name] = chars
    return chars

async def get_user_collection(user_id):
    """Get user collection with optimized caching"""
    cached = user_collection_cache.get(str(user_id))
    if cached:
        return cached
    
    user = await user_collection.find_one(
        {'id': user_id},
        {'characters': 1, 'first_name': 1, 'last_name': 1, 'username': 1}
    )
    
    if user:
        user_collection_cache[str(user_id)] = user
    return user

async def get_all_characters():
    """Get all characters with pagination support"""
    cached = all_characters_cache.get('all_characters')
    if cached:
        return cached
    
    chars = await collection.find(
        {},
        {'name': 1, 'anime': 1, 'img_url': 1, 'video_url': 1, 'id': 1, 'rarity': 1, 'price': 1}
    ).limit(1000).to_list(length=1000)
    
    all_characters_cache['all_characters'] = chars
    return chars

async def search_characters(query):
    """Search characters with optimized regex and caching"""
    cache_key = f"search_{query.lower()}"
    cached = search_results_cache.get(cache_key)
    if cached:
        return cached
    
    # Use text index if available, otherwise fallback to regex
    try:
        chars = await collection.find(
            {"$text": {"$search": query}},
            {'score': {'$meta': "textScore"}, 'name': 1, 'anime': 1, 'img_url': 1, 
             'video_url': 1, 'id': 1, 'rarity': 1, 'price': 1}
        ).sort([('score', {'$meta': "textScore"})]).limit(100).to_list(length=100)
    except:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        chars = await collection.find(
            {"$or": [{"name": regex}, {"anime": regex}]},
            {'name': 1, 'anime': 1, 'img_url': 1, 'video_url': 1, 'id': 1, 'rarity': 1, 'price': 1}
        ).limit(100).to_list(length=100)
    
    search_results_cache[cache_key] = chars
    return chars

def process_character_name(name):
    """Process character name to extract event emoji and return cleaned name and event text"""
    if not name:
        return "Unknown", ""
        
    event_text = ""
    for event_emoji, event_name in event_map.items():
        if event_emoji in name:
            event_text = f"\n\n{event_name}"
            # Remove the emoji from the name if it's at the end
            if name.endswith(event_emoji):
                name = name[:-len(event_emoji)].strip()
            break
    return name, event_text

async def get_user_display_name(user_id, context):
    """Get user's display name with caching"""
    cached = user_profile_cache.get(user_id)
    if cached:
        return cached
    
    # Try to get from database first
    user_data = await user_collection.find_one({'id': user_id}, {'first_name': 1, 'last_name': 1, 'username': 1})
    if user_data:
        name = user_data.get('first_name', '')
        if user_data.get('last_name'):
            name += f" {user_data['last_name']}"
        if not name and user_data.get('username'):
            name = user_data['username']
        if name:
            user_profile_cache[user_id] = name
            return name
    
    # Fallback to Telegram API
    try:
        tg_user = await context.bot.get_chat(user_id)
        name = tg_user.first_name or ""
        if tg_user.last_name:
            name += f" {tg_user.last_name}"
        if not name and tg_user.username:
            name = tg_user.username
        if name:
            user_profile_cache[user_id] = name
            # Update database for future use
            await user_collection.update_one(
                {'id': user_id},
                {'$set': {'first_name': tg_user.first_name, 'last_name': tg_user.last_name, 'username': tg_user.username}},
                upsert=True
            )
            return name
    except Exception:
        pass
    
    return f"User {user_id}"

@block_inl_ptb
async def inlinequery(update: Update, context: CallbackContext) -> None:
    start_time = time.time()
    query = update.inline_query.query.strip()
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0
    results_per_page = 50
    next_offset = ""
    results = []
    
    try:
        # Handle RARITY-only search
        rarity_filter = None
        for emoji, name in emoji_to_rarity.items():
            if query.lower() in [emoji.lower(), name.lower()]:
                rarity_filter = name
                break

        if rarity_filter:
            all_characters = await get_characters_by_rarity(rarity_filter)
            # For non-Animation rarities, filter to only show images
            if rarity_filter != "⚜️ Animated":
                all_characters = [c for c in all_characters if c.get('img_url')]
        elif query.startswith("collection."):
            parts = query.split(".")
            user_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else update.inline_query.from_user.id
            
            # Check if there's a name or rarity filter in the query
            name_filter = None
            rarity_emoji = None
            
            if len(parts) > 2:
                # Check if the part is a rarity emoji
                if parts[2] in emoji_to_rarity:
                    rarity_emoji = parts[2]
                else:
                    # Treat as name filter
                    name_filter = " ".join(parts[2:]).strip()
            
            user = await get_user_collection(user_id)
            if user:
                user_chars = user.get('characters', [])
                
                # Apply rarity filter if specified
                if rarity_emoji:
                    rarity_name = emoji_to_rarity[rarity_emoji]
                    user_chars = [
                        c for c in user_chars
                        if c.get('rarity') == rarity_name and (
                            (rarity_name == "⚜️ Animated" and c.get('video_url')) or
                            (rarity_name == "☀️ Summer[Su]" and c.get('img_url')) or
                            (rarity_name not in ["⚜️ Animated", "☀️ Summer[Su]"])
                        )
                    ]
                
                # Apply name filter if specified
                if name_filter:
                    regex = re.compile(re.escape(name_filter), re.IGNORECASE)
                    user_chars = [c for c in user_chars if regex.search(c.get('name', ''))]
                
                all_characters = user_chars
            else:
                all_characters = []
        elif query.isdigit():
            char = await get_character_details(int(query))
            all_characters = [char] if char else []
        elif not query:
            all_characters = await get_all_characters()
        else:
            all_characters = await search_characters(query)

        # Convert to list if it's a cursor or ensure it's a list
        characters = list(all_characters)[offset:offset + results_per_page]
        if not characters:
            await update.inline_query.answer([], cache_time=5, is_personal=True)
            return

        next_offset = str(offset + results_per_page) if len(characters) == results_per_page else ""

        # Pre-calculate counts for user collection
        user = None
        anime_counts = {}
        char_counts = {}
        if query.startswith('collection.'):
            parts = query.split(".")
            user_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else update.inline_query.from_user.id
            user = await get_user_collection(user_id)
            if user:
                owned_chars = user.get('characters', [])
                for c in owned_chars:
                    anime = c.get('anime')
                    char_id = c.get('id')
                    if anime:
                        anime_counts[anime] = anime_counts.get(anime, 0) + 1
                    if char_id:
                        char_counts[char_id] = char_counts.get(char_id, 0) + 1

        # Process results in batches for better performance
        batch_size = 20
        for i in range(0, len(characters), batch_size):
            batch = characters[i:i + batch_size]
            batch_tasks = []
            
            for character in batch:
                if time.time() - start_time > 4.5:  # Telegram has a 5-second timeout
                    break
                
                char_id = character.get('id', 'Unknown')
                original_name = character.get('name', 'Unknown')
                anime = character.get('anime', 'Unknown')
                img_url = character.get('img_url', '').strip()
                video_url = character.get('video_url', '').strip()
                rarity = character.get('rarity', 'Unknown')
                emoji = rarity_map.get(rarity, '❔')

                # Skip if no media available
                if not img_url and not video_url:
                    continue

                # Process name to extract event emoji and get clean name
                name, event_text = process_character_name(original_name)

                if query.startswith('collection.') and user:
                    user_display_name = await get_user_display_name(user_id, context)
                    user_mention = f"<a href='tg://user?id={user_id}'>{user_display_name}</a>"
                    same_anime_owned = anime_counts.get(anime, 0)
                    total_anime_chars = await get_anime_count(anime)
                    char_count = char_counts.get(char_id, 0)

                    # Extract just the emoji from rarity
                    rarity_emoji_only = rarity_map.get(rarity, '❔').split()[0]
                    # Get rarity name without emoji
                    rarity_name_only = ' '.join(rarity.split()[1:]) if ' ' in rarity else rarity

                    caption = (
                        f"<b>ᴡᴏᴡ ᴄʜᴇᴄᴋ ᴏᴜᴛ {user_mention}'s ᴄʜᴀʀᴀᴄᴛᴇʀ!</b>\n\n"
                        f"<b>{anime}</b> ({same_anime_owned}/{total_anime_chars})\n"
                        f"<b>{char_id}:</b> <b>{name}</b> [x{char_count}]\n"
                        f"( {rarity_emoji_only} 𝙍𝘼𝙍𝙄𝙏𝙔: {rarity_name_only} ){event_text}"
                    )
                else:
                    # Extract just the emoji from rarity
                    rarity_emoji_only = rarity_map.get(rarity, '❔').split()[0]
                    # Get rarity name without emoji
                    rarity_name_only = ' '.join(rarity.split()[1:]) if ' ' in rarity else rarity

                    caption = (
                        f"<b>OwO! Check out This Character!</b>\n\n"
                        f"<b>{anime}</b>\n"
                        f"<b>{char_id}:</b> <b>{name}</b>\n"
                        f"﹝ {rarity_emoji_only} 𝙍𝘼𝙍𝙄𝙏𝙔: {rarity_name_only} ﹞{event_text}"
                    )

                # Generate unique ID for each result
                result_id = generate_unique_id()

                # Special handling for Animation rarity (show as video)
                if rarity == "⚜️ Animated" and video_url:
                    results.append(IQV(
                        id=result_id,
                        video_url=video_url,
                        mime_type="video/mp4",
                        thumbnail_url=img_url or video_url,
                        title=name[:64],
                        caption=caption,
                        parse_mode="HTML"
                    ))
                elif img_url:
                    # For all other rarities, show as photo that can be played
                    results.append(IQP(
                        id=result_id,
                        photo_url=img_url,
                        thumbnail_url=img_url,
                        caption=caption,
                        parse_mode="HTML"
                    ))
                
                if len(results) >= 50:
                    break

            # If we're approaching timeout, break early
            if time.time() - start_time > 4.5:
                break

    except Exception as e:
        print(f"Error in inlinequery: {e}")
        await update.inline_query.answer([], cache_time=5, is_personal=True)
        return

    # Ensure we don't exceed 50 results (Telegram limit)
    results = results[:50]
    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5, is_personal=True)

# Register handler with a lower group number for higher priority
application.add_handler(InlineQueryHandler(inlinequery, block=False), group=-1)
