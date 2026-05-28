from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Grabber import collection, user_collection, app
from .block import block_dec
import math
import asyncio
from collections import Counter

# Tiny font converter - optimized with str.translate
_tiny_map = str.maketrans({
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ',
    'f': 'ꜰ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ',
    'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ',
    'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ',
    'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ',
    'z': 'ᴢ'
})

def tiny_font(text):
    return text.lower().translate(_tiny_map)

# Cache character lists to avoid repeated database queries
_char_cache = {}
_char_cache_time = 0
_cache_duration = 300  # 5 minutes cache

async def get_all_characters():
    global _char_cache, _char_cache_time
    current_time = asyncio.get_event_loop().time()
    
    if current_time - _char_cache_time > _cache_duration or not _char_cache:
        chars = await collection.find({}).to_list(length=None)
        _char_cache = {char['id']: char for char in chars if 'id' in char}
        _char_cache_time = current_time
    return _char_cache

async def get_user_characters(user_id):
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return set()
    
    # Fast extraction of character IDs
    char_ids = set()
    for char in user.get('characters', []):
        if isinstance(char, dict):
            char_ids.add(char.get('id'))
        elif isinstance(char, (str, int)):
            char_ids.add(char)
    return char_ids

def get_rarity_emoji(rarity):
    rarity_emojis = {
        '⚫ Common': '⚫', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧', '💮 Mythic': '💮',
        '🔱 Godly': '🔱', '🟡 Legendary': '🟡', '🟣 Epic': '🟣', '🟠 Rare': '🟠', '🟤 Uncommon': '🟤',
        '🏵️ Exotic': '🏵️', '⚜️ Unique': '⚜️', '⚡ Eternal': '⚡', '🌸 Radiant': '🌸',
        '💠 Divine': '💠', '🎐 Celestial': '🎐', '🌩️ Electra': '🌩️', '🧿 Galaxia': '🧿',
        '☀️ Summer[Su]': '☀️', '🧬 Animation': '🧬'
    }
    return rarity_emojis.get(rarity.lower(), '⚫')

@app.on_message(filters.command("uncollected"))
@block_dec
async def uncollected(_, message: Message):
    try:
        user_id = message.from_user.id
        user_chars = await get_user_characters(user_id)
        
        if not user_chars:
            await message.reply_text(tiny_font("ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ɢʀᴀʙʙᴇᴅ ᴀɴʏ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ʏᴇᴛ!"))
            return
        
        all_chars = await get_all_characters()
        uncollected_chars = [char for char_id, char in all_chars.items() if char_id not in user_chars]
        
        if not uncollected_chars:
            await message.reply_text(tiny_font("ʏᴏᴜ ʜᴀᴠᴇ ᴄᴏʟʟᴇᴄᴛᴇᴅ ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ! 🎉"))
            return
        
        # Sort by rarity and name
        uncollected_chars.sort(key=lambda x: (
            x.get('rarity', 'common').lower(), 
            x.get('name', '').lower()
        ))
        
        total_pages = math.ceil(len(uncollected_chars) / 10)
        await show_uncollected_page(message, uncollected_chars, 1, total_pages, user_id)
    
    except Exception as e:
        await message.reply_text(tiny_font(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {str(e)}"))

async def show_uncollected_page(message, chars, page, total_pages, user_id):
    start = (page - 1) * 10
    end = start + 10
    current_chars = chars[start:end]
    
    text = tiny_font(f"ᴜɴᴄᴏʟʟᴇᴄᴛᴇᴅ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ({page}/{total_pages}):\n\n")
    
    for char in current_chars:
        rarity = char.get('rarity', 'common').lower()
        emoji = get_rarity_emoji(rarity)
        text += f"{emoji} {char.get('name', 'Unknown')} - `{char.get('id', '?')}`\n"
    
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"unprev_{page}_{user_id}"))
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"unnext_{page}_{user_id}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    if message.from_user.is_self and message.reply_to_message:
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        await message.reply_text(text, reply_markup=reply_markup)

@app.on_callback_query(filters.regex(r"^un(prev|next)_(\d+)_(\d+)$"))
async def uncollected_nav_callback(_, query: CallbackQuery):
    try:
        direction = query.matches[0].group(1)
        current_page = int(query.matches[0].group(2))
        user_id = int(query.matches[0].group(3))
        
        # Verify the user initiating the callback is the same who used the command
        if query.from_user.id != user_id:
            await query.answer("ᴛʜɪs ɪsɴ'ᴛ ʏᴏᴜʀ ᴍᴇɴᴜ!", show_alert=True)
            return
            
        new_page = current_page - 1 if direction == "prev" else current_page + 1
        
        user_chars = await get_user_characters(user_id)
        all_chars = await get_all_characters()
        
        uncollected_chars = [char for char_id, char in all_chars.items() if char_id not in user_chars]
        # Sort by rarity and name
        uncollected_chars.sort(key=lambda x: (
            x.get('rarity', 'common').lower(), 
            x.get('name', '').lower()
        ))
        total_pages = math.ceil(len(uncollected_chars) / 10)
        
        await show_uncollected_page(query.message, uncollected_chars, new_page, total_pages, user_id)
        await query.answer()
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@app.on_message(filters.command("duplicate"))
@block_dec
async def duplicates(_, message: Message):
    try:
        user_id = message.from_user.id
        user = await user_collection.find_one({"id": user_id})
        
        if not user:
            await message.reply_text(tiny_font("ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ɢʀᴀʙʙᴇᴅ ᴀɴʏ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ʏᴇᴛ!"))
            return
        
        # Fast duplicate counting using collections.Counter
        char_ids = []
        for char in user.get('characters', []):
            if isinstance(char, dict):
                char_ids.append(char.get('id'))
            elif isinstance(char, (str, int)):
                char_ids.append(char)
        
        dup_counter = Counter(char_ids)
        duplicate_chars = {k: v for k, v in dup_counter.items() if v > 1}
        
        if not duplicate_chars:
            await message.reply_text(tiny_font("ɴᴏ ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ꜰᴏᴜɴᴅ ɪɴ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!"))
            return
        
        # Bulk fetch character details
        all_chars = await get_all_characters()
        duplicate_list = [{
            "char": all_chars.get(char_id, {"name": f"Unknown (ID: {char_id})", "id": char_id, "rarity": "common"}),
            "count": count
        } for char_id, count in duplicate_chars.items()]
        
        # Sort by count (descending), then rarity, then name
        duplicate_list.sort(key=lambda x: (
            -x['count'],
            x['char'].get('rarity', 'common').lower(),
            x['char'].get('name', '').lower()
        ))
        
        total_pages = math.ceil(len(duplicate_list) / 10)
        await show_duplicates_page(message, duplicate_list, 1, total_pages, user_id)
    
    except Exception as e:
        await message.reply_text(tiny_font(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {str(e)}"))

async def show_duplicates_page(message, chars, page, total_pages, user_id):
    start = (page - 1) * 10
    end = start + 10
    current_chars = chars[start:end]
    
    text = tiny_font(f"ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ({page}/{total_pages}):\n\n")
    
    for item in current_chars:
        char = item['char']
        rarity = char.get('rarity', 'common').lower()
        emoji = get_rarity_emoji(rarity)
        text += f"{emoji} {char.get('name', 'Unknown')} - `{char.get('id', '?')}` (×{item['count']})\n"
    
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"dupprev_{page}_{user_id}"))
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"dupnext_{page}_{user_id}"))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    if message.from_user.is_self and message.reply_to_message:
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        await message.reply_text(text, reply_markup=reply_markup)

@app.on_callback_query(filters.regex(r"^dup(prev|next)_(\d+)_(\d+)$"))
async def duplicates_nav_callback(_, query: CallbackQuery):
    try:
        direction = query.matches[0].group(1)
        current_page = int(query.matches[0].group(2))
        user_id = int(query.matches[0].group(3))
        
        # Verify the user initiating the callback is the same who used the command
        if query.from_user.id != user_id:
            await query.answer("ᴛʜɪs ɪsɴ'ᴛ ʏᴏᴜʀ ᴍᴇɴᴜ!", show_alert=True)
            return
            
        new_page = current_page - 1 if direction == "prev" else current_page + 1
        
        user = await user_collection.find_one({"id": user_id})
        if not user:
            await query.answer(tiny_font("User data not found!"), show_alert=True)
            return
        
        char_ids = []
        for char in user.get('characters', []):
            if isinstance(char, dict):
                char_ids.append(char.get('id'))
            elif isinstance(char, (str, int)):
                char_ids.append(char)
        
        dup_counter = Counter(char_ids)
        duplicate_chars = {k: v for k, v in dup_counter.items() if v > 1}
        
        all_chars = await get_all_characters()
        duplicate_list = [{
            "char": all_chars.get(char_id, {"name": f"Unknown (ID: {char_id})", "id": char_id, "rarity": "common"}),
            "count": count
        } for char_id, count in duplicate_chars.items()]
        
        # Sort by count (descending), then rarity, then name
        duplicate_list.sort(key=lambda x: (
            -x['count'],
            x['char'].get('rarity', 'common').lower(),
            x['char'].get('name', '').lower()
        ))
        
        total_pages = math.ceil(len(duplicate_list) / 10)
        await show_duplicates_page(query.message, duplicate_list, new_page, total_pages, user_id)
        await query.answer()
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)
