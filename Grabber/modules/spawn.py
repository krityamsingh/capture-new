import time
import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from . import collection, user_collection, group_user_totals_collection, top_global_groups_collection, app, capsify, show, deduct
from asyncio import Lock
from .watchers import character_watcher
from .block import block_dec, block_cbq
from datetime import datetime, timedelta
import humanize

message_counts = {}
spawn_locks = {}
spawned_characters = {}
chat_locks = {}
last_despawned_characters = {}
user_daily_seizes = {}
user_animated_limits = {}
owner_id = 6118760915  # Replace with your owner ID

# ✅ NEW: Custom spawn frequencies set by owner per chat (overrides DB value)
custom_spawn_frequencies = {}

# Rarity to gold reward mapping
RARITY_GOLD_REWARDS = {
    '🔴 Common': 5,
    '🔵 Uncommon': 10,
    '🟠 Rare': 15,
    '🟡 Legendary': 35,
    '🫧 Premium': 45,
    '🔮 Limited Edition': 55,
    '🏵️ Exotic': 100,
    '⚜️ Animated': 200,
    '🌼 Celebrity': 250,
    '🎐 Crystal': 300,
    '🍹 Neon': 400,
    '🧿 Supreme': 500,
    '⚡ Thundra': 600,
    '🛸 Galvoria': 750
}

# Rarity spawn rates (in percentage) - Only rarity_map rarities
RARITY_SPAWN_RATES = {
    '🔴 Common': 40,      # 40%
    '🔵 Uncommon': 25,    # 25%
    '🟠 Rare': 15,        # 15%
    '🟡 Legendary': 10,   # 10%
    '🫧 Premium': 5,      # 5%
    '🔮 Limited Edition': 3,  # 3%
    '🏵️ Exotic': 1.5,     # 1.5%
    '⚜️ Animated': 0.5    # 0.5%
}

# Special rarity limits (global spawn limits)
SPECIAL_RARITY_LIMITS = {
    '🟡 Legendary': 10,
    '🌼 Celebrity': 5,
    '🎐 Crystal': 4,
    '🍹 Neon': 3,
    '🧿 Supreme': 2,
    '⚡ Thundra': 1,
    '🛸 Galvoria': 1
}

# Global spawn counters
global_spawn_counters = {}

# Locked rarities (won't spawn anywhere)
locked_rarities = set()

# Gold emojis for rewards
GOLD_EMOJIS = ["💰", "🏆", "🎖️", "🏅", "🥇", "💎", "👑", "🪙", "💴", "💵", "💶", "💷"]

# Rarity map with emojis
rarity_map = {
    '🔴 Common': '🔴',
    '🔮 Limited Edition': '🔮',
    '🫧 Premium': '🫧',
    '🟡 Legendary': '🟡',
    '🟠 Rare': '🔴',
    '🔵 Uncommon': '🔵',
    '🏵️ Exotic': '🏵️',
    '⚜️ Animated': '⚜️'
}

# Unique rarity map
unique_rarity_map = {
    '🌼 Celebrity': '🌼',
    '🎐 Crystal': '🎐',
    '🍹 Neon': '🍹',
    '🧿 Supreme': '🧿',
    '⚡ Thundra': '⚡',
    '🛸 Galvoria': '🛸'
}

async def get_random_gold_emoji():
    return random.choice(GOLD_EMOJIS)

def reset_daily_limits():
    global user_daily_seizes, user_animated_limits
    user_daily_seizes = {}
    user_animated_limits = {}
    print("Daily limits reset!")

# Schedule daily reset
async def schedule_daily_reset():
    while True:
        now = datetime.now()
        target_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        reset_daily_limits()

async def startup_scheduler():
    asyncio.create_task(schedule_daily_reset())

# The event loop is already running at import time (started by asyncio.run in
# __main__.py), so we can safely schedule the task directly without app.run().
asyncio.get_event_loop().create_task(startup_scheduler())

async def get_all_characters():
    """Get all characters available for spawning"""
    return await collection.find({
        '$or': [
            {'img_url': {'$exists': True, '$ne': None}},
            {'video_url': {'$exists': True, '$ne': None}}
        ]
    }).to_list(length=None)

async def can_spawn_rarity(rarity):
    """Check if a rarity can be spawned based on global limits"""
    if rarity not in SPECIAL_RARITY_LIMITS:
        return True
    
    if rarity not in global_spawn_counters:
        global_spawn_counters[rarity] = 0
    
    return global_spawn_counters[rarity] < SPECIAL_RARITY_LIMITS[rarity]

async def increment_rarity_counter(rarity):
    """Increment global spawn counter for a rarity"""
    if rarity in SPECIAL_RARITY_LIMITS:
        if rarity not in global_spawn_counters:
            global_spawn_counters[rarity] = 0
        global_spawn_counters[rarity] += 1

async def spawn_character(chat_id, chat_title):
    # Initialize lock if not exists
    if chat_id not in spawn_locks:
        spawn_locks[chat_id] = Lock()

    async with spawn_locks[chat_id]:
        # Check if already spawned
        if chat_id in spawned_characters:
            return False

        # Get chat modes
        chat_modes = await group_user_totals_collection.find_one({"chat_id": chat_id})    
        if not chat_modes:    
            chat_modes = {"chat_id": chat_id, "character": True, "words": True, "maths": True}    
            await group_user_totals_collection.update_one({"chat_id": chat_id}, {"$set": chat_modes}, upsert=True)    
        
        # Check if character mode is enabled
        if not chat_modes.get('character', True):    
            return False    
        
        # Get all characters with valid media
        all_characters = await get_all_characters()
        
        if not all_characters:    
            return False    
        
        # Select character based on rarity spawn rates and global limits
        character = await select_character_by_rarity(all_characters)
        
        if not character:
            return False  # No valid character found
            
        spawned_characters[chat_id] = character    
        
        # Get appropriate emoji based on rarity type
        if character["rarity"] in rarity_map:
            rarity_emoji = rarity_map[character["rarity"]]
        elif character["rarity"] in unique_rarity_map:
            rarity_emoji = unique_rarity_map[character["rarity"]]
        else:
            rarity_emoji = "❓"

        # Send sticker first
        try:
            sticker = await app.send_sticker(chat_id, sticker="CAACAgQAAxkBAAEkaTxoi2M-dTFFTRuPg3vwdQevpAIlpgACJhAAAmfdcVD7uxkx_OIj5DYE")
        except Exception:
            pass  # Continue even if sticker fails

        # Prepare the caption
        caption = (
            f"<blockquote>ᴀ {rarity_emoji} ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀꜱ ᴀᴘᴘᴇᴀʀᴇᴅ ɪɴ {chat_title}</blockquote>\n\n"
            f"**ᴄᴀᴘᴛᴜʀᴇ ʜɪᴍ ᴀɴᴅ ɢɪᴠᴇ ʏᴏᴜʀ ʜᴀʀᴇᴍ ꜱᴏᴍᴇ ᴀᴜʀᴀ ᴡɪᴛʜ** /capture"
        )

        # Get character media - ensure at least one exists
        char_img = character.get("img_url")
        char_video = character.get("video_url")
        message = None

        # Try to send video first if available
        if char_video:
            try:
                message = await app.send_video(    
                    chat_id=chat_id,    
                    video=char_video,    
                    caption=caption,    
                    has_spoiler=True    
                )
            except Exception as e:
                print(f"Failed to send video: {e}")
                char_video = None

        # If video failed or not available, try photo
        if not message and char_img:
            try:
                message = await app.send_photo(    
                    chat_id=chat_id,    
                    photo=char_img,    
                    caption=caption,    
                    has_spoiler=True    
                )
            except Exception as e:
                print(f"Failed to send photo: {e}")
                return False

        # If no media could be sent, send text only
        if not message:
            message = await app.send_message(
                chat_id=chat_id,
                text=caption
            )

        # Store message ID and spawn time
        character["message_id"] = message.id
        character["spawn_time"] = time.time()

        # Increment global rarity counter for limited rarities
        await increment_rarity_counter(character["rarity"])

        # Set timeout for removal
        asyncio.create_task(remove_spawn_after_timeout(chat_id, character, timeout=120))
        return True

async def select_character_by_rarity(all_characters):
    """Select a character based on rarity spawn rates and global limits"""
    # Filter out locked rarities and check global limits
    available_characters = []
    
    for character in all_characters:
        rarity = character['rarity']
        
        # Skip if rarity is locked
        if rarity in locked_rarities:
            continue
            
        # Check global spawn limits for special rarities
        if not await can_spawn_rarity(rarity):
            continue
            
        available_characters.append(character)
    
    if not available_characters:
        return None
    
    # Create weighted list based on spawn rates (only for rarity_map rarities)
    weighted_characters = []
    
    for character in available_characters:
        rarity = character['rarity']
        
        # Only apply spawn rates to rarity_map rarities
        if rarity in RARITY_SPAWN_RATES:
            weight = RARITY_SPAWN_RATES[rarity]
            weighted_characters.extend([character] * int(weight * 10))
        else:
            # For unique rarities, use a very low base weight
            weighted_characters.extend([character] * 1)
    
    # If no characters found with proper weights, fallback to random from available
    if not weighted_characters:
        return random.choice(available_characters) if available_characters else None
    
    return random.choice(weighted_characters)

# ============================================================
# ✅ NEW: /setspawn command — Owner sets spawn frequency
# ============================================================
@app.on_message(filters.command("setspawn"))
async def set_spawn_frequency(_, message):
    """Owner sets how many messages trigger a character spawn (e.g. 10, 20, 30...)"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    # Usage: /setspawn [frequency] OR /setspawn [chat_id] [frequency]
    args = message.command[1:]

    if len(args) == 1:
        # Apply to current chat
        target_chat_id = message.chat.id
        try:
            frequency = int(args[0])
        except ValueError:
            await message.reply_text("❌ Frequency must be a number.\n\n**Usage:** `/setspawn 20`\nor `/setspawn -100123456789 20`")
            return

    elif len(args) == 2:
        # Apply to specific chat
        try:
            target_chat_id = int(args[0])
            frequency = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid format.\n\n**Usage:** `/setspawn [chat_id] [frequency]`\n**Example:** `/setspawn -100123456789 30`")
            return
    else:
        await message.reply_text(
            "**⚙️ Set Spawn Frequency**\n\n"
            "**Usage:**\n"
            "• `/setspawn 20` — set in current chat\n"
            "• `/setspawn -100123456789 20` — set in specific chat\n\n"
            "**Examples:**\n"
            "`/setspawn 10` → spawn every 10 messages\n"
            "`/setspawn 20` → spawn every 20 messages\n"
            "`/setspawn 30` → spawn every 30 messages\n"
            "`/setspawn 40` → spawn every 40 messages\n"
            "`/setspawn 50` → spawn every 50 messages\n\n"
            "**Min:** 5  |  **Max:** 1000"
        )
        return

    # Validate range
    if frequency < 5 or frequency > 1000:
        await message.reply_text("❌ Frequency must be between **5** and **1000**.")
        return

    # Save to memory (overrides DB)
    custom_spawn_frequencies[target_chat_id] = frequency

    # Also persist to DB so it survives restarts
    await group_user_totals_collection.update_one(
        {"chat_id": target_chat_id},
        {"$set": {"message_frequency": frequency}},
        upsert=True
    )

    await message.reply_text(
        f"✅ **Spawn frequency updated!**\n\n"
        f"📍 **Chat ID:** `{target_chat_id}`\n"
        f"⚡ **New Frequency:** Every `{frequency}` messages\n\n"
        f"A character will now spawn after every **{frequency}** messages in that chat."
    )

# ✅ NEW: /spawninfo command — Check current spawn frequency of a chat
@app.on_message(filters.command("spawninfo"))
async def spawn_info(_, message):
    """Check the current spawn frequency for the current or a specific chat"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    args = message.command[1:]
    target_chat_id = int(args[0]) if args else message.chat.id

    # Check memory first
    if target_chat_id in custom_spawn_frequencies:
        frequency = custom_spawn_frequencies[target_chat_id]
        source = "🟢 Custom (set by owner)"
    else:
        chat_data = await group_user_totals_collection.find_one({'chat_id': target_chat_id})
        frequency = chat_data.get('message_frequency', 100) if chat_data else 100
        source = "🔵 Default (from DB or 100)"

    current_count = message_counts.get(target_chat_id, 0)

    await message.reply_text(
        f"**📊 Spawn Info**\n\n"
        f"📍 **Chat ID:** `{target_chat_id}`\n"
        f"⚡ **Spawn every:** `{frequency}` messages\n"
        f"📨 **Current message count:** `{current_count}/{frequency}`\n"
        f"🔧 **Source:** {source}"
    )

# ✅ NEW: /resetspawn — Reset spawn frequency to default (100)
@app.on_message(filters.command("resetspawn"))
async def reset_spawn_frequency(_, message):
    """Reset spawn frequency back to default for a chat"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    args = message.command[1:]
    target_chat_id = int(args[0]) if args else message.chat.id

    # Remove from memory
    if target_chat_id in custom_spawn_frequencies:
        del custom_spawn_frequencies[target_chat_id]

    # Reset in DB
    await group_user_totals_collection.update_one(
        {"chat_id": target_chat_id},
        {"$set": {"message_frequency": 100}},
        upsert=True
    )

    await message.reply_text(
        f"✅ **Spawn frequency reset to default!**\n\n"
        f"📍 **Chat ID:** `{target_chat_id}`\n"
        f"⚡ **Frequency:** Every `100` messages (default)"
    )

@app.on_message(filters.command("droprate"))
async def show_drop_rates(_, message):
    """Show spawn rates for all rarities"""
    drop_rates_text = "**🎯 Character Spawn Rates 🎯**\n\n"
    
    # Show rarity_map rates
    drop_rates_text += "**Standard Rarities:**\n"
    for rarity, rate in RARITY_SPAWN_RATES.items():
        emoji = rarity_map.get(rarity, "❓")
        drop_rates_text += f"**{rarity}**: `{rate}%`\n"
    
    # Show unique rarities (no fixed rates)
    drop_rates_text += "\n**Unique Rarities:**\n"
    for rarity, emoji in unique_rarity_map.items():
        limit = SPECIAL_RARITY_LIMITS.get(rarity, "Unlimited")
        current = global_spawn_counters.get(rarity, 0)
        drop_rates_text += f"**{rarity}**: `Global Limit: {current}/{limit}`\n"
    
    drop_rates_text += "\n**Note**: Standard rarities have percentage rates, unique rarities have global daily limits."
    
    await message.reply_text(drop_rates_text)

@app.on_message(filters.command("srarity"))
async def set_rarity_spawn(_, message):
    """Set spawn limit for a specific rarity"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if len(message.command) < 3:
        await message.reply_text(
            "**Usage:** /srarity [emoji] [limit]\n\n"
            "**Example:** /srarity 🟡 10\n"
            "This will set Legendary rarity to spawn only 10 times globally.\n\n"
            "**Available rarities:**\n"
            "🟡 Legendary, 🌼 Celebrity, 🎐 Crystal, 🍹 Neon, 🧿 Supreme, ⚡ Thundra, 🛸 Galvoria"
        )
        return
    
    emoji = message.command[1]
    try:
        limit = int(message.command[2])
    except ValueError:
        await message.reply_text("❌ Limit must be a number.")
        return
    
    # Find rarity from emoji
    rarity_name = None
    for rarity, rarity_emoji in list(rarity_map.items()) + list(unique_rarity_map.items()):
        if rarity_emoji == emoji:
            rarity_name = rarity
            break
    
    if not rarity_name:
        await message.reply_text("❌ Invalid rarity emoji.")
        return
    
    # Set the limit
    SPECIAL_RARITY_LIMITS[rarity_name] = limit
    global_spawn_counters[rarity_name] = 0  # Reset counter
    
    await message.reply_text(f"✅ **{rarity_name}** global spawn limit set to **{limit}** per day.")

@app.on_message(filters.command("lockr"))
async def lock_rarity(_, message):
    """Lock a rarity from spawning globally"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** /lockr [emoji]\n\n"
            "**Example:** /lockr 🌼\n"
            "This will prevent Celebrity rarity from spawning anywhere.\n\n"
            "**Available rarities:**\n"
            "All standard and unique rarities"
        )
        return
    
    emoji = message.command[1]
    
    # Find rarity from emoji
    rarity_name = None
    for rarity, rarity_emoji in list(rarity_map.items()) + list(unique_rarity_map.items()):
        if rarity_emoji == emoji:
            rarity_name = rarity
            break
    
    if not rarity_name:
        await message.reply_text("❌ Invalid rarity emoji.")
        return
    
    # Lock the rarity
    locked_rarities.add(rarity_name)
    
    await message.reply_text(f"🔒 **{rarity_name}** has been locked and will not spawn anywhere.")

@app.on_message(filters.command("unlockr"))
async def unlock_rarity(_, message):
    """Unlock a rarity for spawning"""
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "**Usage:** /unlockr [emoji]\n\n"
            "**Example:** /unlockr 🌼\n"
            "This will allow Celebrity rarity to spawn again.\n\n"
            "**Available rarities:**\n"
            "All standard and unique rarities"
        )
        return
    
    emoji = message.command[1]
    
    # Find rarity from emoji
    rarity_name = None
    for rarity, rarity_emoji in list(rarity_map.items()) + list(unique_rarity_map.items()):
        if rarity_emoji == emoji:
            rarity_name = rarity
            break
    
    if not rarity_name:
        await message.reply_text("❌ Invalid rarity emoji.")
        return
    
    # Unlock the rarity
    if rarity_name in locked_rarities:
        locked_rarities.remove(rarity_name)
    
    await message.reply_text(f"🔓 **{rarity_name}** has been unlocked and can now spawn.")

@app.on_message(filters.command("lockstatus"))
async def lock_status(_, message):
    """Show status of locked rarities"""
    if not locked_rarities:
        await message.reply_text("🔓 **No rarities are currently locked.**")
        return
    
    status_text = "**🔒 Locked Rarities:**\n\n"
    for rarity in locked_rarities:
        # Find emoji for the rarity
        emoji = rarity_map.get(rarity) or unique_rarity_map.get(rarity) or "❓"
        status_text += f"{emoji} **{rarity}**\n"
    
    await message.reply_text(status_text)

@app.on_message(filters.all & filters.group, group=character_watcher)
async def handle_message(_, message):
    chat_id = message.chat.id
    chat_title = message.chat.title
    
    # Initialize message count if not exists
    if chat_id not in message_counts:
        message_counts[chat_id] = 0
    
    message_counts[chat_id] += 1
    
    # ✅ UPDATED: Check custom frequency first (set by owner), then fall back to DB/default
    if chat_id in custom_spawn_frequencies:
        frequency = custom_spawn_frequencies[chat_id]
    else:
        chat_data = await group_user_totals_collection.find_one({'chat_id': chat_id})
        frequency = chat_data['message_frequency'] if chat_data and 'message_frequency' in chat_data else 100

    # Check if spawn is already in progress
    if chat_id in spawn_locks and spawn_locks[chat_id].locked():
        return

    # Check if it's time to spawn
    if message_counts[chat_id] >= frequency:
        success = await spawn_character(chat_id, chat_title)
        if success:
            message_counts[chat_id] = 0

async def remove_spawn_after_timeout(chat_id, character, timeout):
    await asyncio.sleep(timeout)

    if chat_id in spawned_characters and spawned_characters[chat_id] == character:
        # Store last despawned character
        last_despawned_characters[chat_id] = {
            "user": None,
            "character": character,
            "spawn_time": character["spawn_time"]
        }
        
        # Send disappearance message
        keyboard = [[InlineKeyboardButton("🥂 ᴍᴏʀᴇ ɪɴғᴏ", callback_data=f"info_{chat_id}")]]
        await app.send_message(
            chat_id,
            f"🧋 Oᴏᴘs! ᴛʜᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs ᴅɪsᴀᴘᴘᴇᴀʀᴇᴅ ɪɴ ᴀ ʙʟɪɴᴋ ᴏғ ᴀɴ ᴇʏᴇ.\n"
            f"ʜɪs ɴᴀᴍᴇ ɪs {character['name']}, ʀᴇᴍᴇᴍʙᴇʀ ɪᴛ ғᴏʀ ɴᴇxᴛ ᴛɪᴍᴇ!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        del spawned_characters[chat_id]

@app.on_callback_query(filters.regex("^info_"))
async def character_info_callback(client, callback_query):
    chat_id = int(callback_query.data.split("_")[1])
    user = callback_query.from_user

    if chat_id in spawned_characters:
        character = spawned_characters[chat_id]
    elif chat_id in last_despawned_characters:
        character = last_despawned_characters[chat_id]["character"]
    else:
        await callback_query.answer("⛔ ᴄʜᴀʀᴀʀᴀᴄᴛᴇʀ ɪɴғᴏ ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ.", show_alert=True)
        return

    await callback_query.message.delete()

    caption = (
        f"╭─━━━━━━⊱✿⊰━━━━━━─╮\n"
        f" Uᴡᴜ! Cʜᴇᴄᴋ ᴛʜɪs ᴏᴜᴛ, sᴇɴᴘᴀɪ!\n"
        f"╰─━━━━━━⊱✿⊰━━━━━━─╯\n\n"
        f"🌀 Nᴀᴍᴇ: {character['name']}\n"
        f"🌸 Aɴɪᴍᴇ: {character['anime']}\n"
        f"💠 Rᴀʀɪᴛʏ: {character['rarity']}\n\n"
        f"➥ ᴄʟɪᴄᴋᴇᴅ ʙʏ: {user.first_name}"
    )

    if "video_url" in character and character["video_url"]:
        await client.send_video(chat_id, video=character["video_url"], caption=caption)
    else:
        await client.send_photo(chat_id, photo=character["img_url"], caption=caption)

    await callback_query.answer()

async def check_anime_completion(user_id, character):
    """Check if user has completed an anime collection"""
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data or 'characters' not in user_data:
        return False
    
    user_characters = user_data['characters']
    anime_name = character['anime']
    
    # Get all characters from this anime
    anime_characters = await collection.find({'anime': anime_name}).to_list(length=None)
    
    # Get user's characters from this anime
    user_anime_chars = [char for char in user_characters if char.get('anime') == anime_name]
    
    # Check if user has all characters from this anime
    anime_char_ids = {char['_id'] for char in anime_characters}
    user_anime_char_ids = {char['_id'] for char in user_anime_chars}
    
    return anime_char_ids.issubset(user_anime_char_ids)

def normalize_name(name):
    """Normalize name for comparison - remove extra spaces and convert to lowercase"""
    return ' '.join(name.split()).lower()

def is_valid_capture_name(guess, character_name):
    """Check if the guess matches the character name in any form"""
    guess_normalized = normalize_name(guess)
    char_name_normalized = normalize_name(character_name)
    
    # Split into name parts
    char_name_parts = char_name_normalized.split()
    
    # Check all possible combinations
    if len(char_name_parts) == 1:
        # Single word name - only full name works
        return guess_normalized == char_name_normalized
    else:
        # Multiple word name - check first name, last name, or full name
        first_name = char_name_parts[0]
        last_name = char_name_parts[-1]
        full_name = char_name_normalized
        
        return (guess_normalized == first_name or 
                guess_normalized == last_name or 
                guess_normalized == full_name)

@app.on_message(filters.command("capture"))
@block_dec
async def seize_character(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    today = datetime.now().date().isoformat()

    # Initialize daily seize count
    if user_id not in user_daily_seizes:
        user_daily_seizes[user_id] = {"date": today, "count": 0}
    elif user_daily_seizes[user_id]["date"] != today:
        user_daily_seizes[user_id] = {"date": today, "count": 0}

    # Initialize animated character limit
    if user_id not in user_animated_limits:
        user_animated_limits[user_id] = {"date": today, "count": 0}
    elif user_animated_limits[user_id]["date"] != today:
        user_animated_limits[user_id] = {"date": today, "count": 0}

    # Check if command has arguments
    if len(message.command) > 1:
        # User provided a name, process capture immediately
        await process_capture_with_name(message)
        return

    # If no arguments, show character info
    if chat_id in spawned_characters:
        character = spawned_characters[chat_id]
        
        # Check animated character limit
        if character['rarity'] == '⚜️ Animated' and user_id != owner_id:
            if user_animated_limits[user_id]["count"] >= 4:
                # Send DM about limit
                try:
                    await app.send_message(
                        user_id,
                        "**⚜️ Animated Character Limit Reached!**\n\n"
                        "You can only capture **4 animated characters** every 24 hours.\n"
                        "The limit will reset automatically at midnight.\n\n"
                        "Current animated captures today: **4/4**"
                    )
                except:
                    pass  # User hasn't started bot in DM
                
                await message.reply_text(
                    "**⛔ Animated Character Limit Reached!**\n\n"
                    "Check your DM for more information about the daily limit."
                )
                return
        
        # Send character info with capture button
        if character["rarity"] in rarity_map:
            rarity_emoji = rarity_map[character["rarity"]]
        elif character["rarity"] in unique_rarity_map:
            rarity_emoji = unique_rarity_map[character["rarity"]]
        else:
            rarity_emoji = "❓"
            
        caption = (
            f"**ᴀ {rarity_emoji} ᴄʜᴀʀᴀᴄᴛᴇʀ ɪs ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ {message.chat.title}**\n\n"
            f"**ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴠɪᴇᴡ ᴀɴᴅ ᴄᴀᴘᴛᴜʀᴇ ɪᴛ!**\n\n"
        )

        keyboard = [
            [InlineKeyboardButton("🔍 ᴠɪᴇᴡ ᴄʜᴀʀᴀᴄᴛᴇʀ", url=f"https://t.me/c/{str(chat_id)[4:]}/{character['message_id']}")]
        ]
        
        await message.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # If no character spawned, show last captured character
    last_seized = last_despawned_characters.get(chat_id)
    if last_seized:
        last_user = last_seized["user"] or "ɴᴏ ᴏɴᴇ"
        last_name = last_seized["character"]["name"]
        await message.reply_text(
            f"**❌ ɴᴏ ᴄᴀᴘᴛᴜʀᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ.**\n\n"
            f"🕊️ **ʟᴀꜱᴛ ꜱᴇɪᴢᴇᴅ ʙʏ** {last_user}:\n"
            f"➥ `{last_name}`"
        )
    else:
        await message.reply_text(
            "**🌫️ ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪɴ sɪɢʜᴛ...**\n"
            "ᴛʜᴇ ғɪᴇʟᴅ ɪs ᴇᴍᴘᴛʏ ʀɪɢʜᴛ ɴᴏᴡ.\n"
            "⚡ ᴡᴀɪᴛ ꜰᴏʀ ᴀ ɴᴇᴡ ᴡᴀɴᴅᴇʀᴇʀ ᴛᴏ ᴀʀʀɪᴠᴇ!"
        )

async def process_capture_with_name(message):
    """Process capture when user provides a character name"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    today = datetime.now().date().isoformat()

    # Initialize daily seize count if not exists
    if user_id not in user_daily_seizes:
        user_daily_seizes[user_id] = {"date": today, "count": 0}
    elif user_daily_seizes[user_id]["date"] != today:
        user_daily_seizes[user_id] = {"date": today, "count": 0}

    # Initialize animated character limit if not exists
    if user_id not in user_animated_limits:
        user_animated_limits[user_id] = {"date": today, "count": 0}
    elif user_animated_limits[user_id]["date"] != today:
        user_animated_limits[user_id] = {"date": today, "count": 0}

    # Check daily limit (25) unless owner
    if user_id != owner_id and user_daily_seizes[user_id]["count"] >= 25:
        await message.reply_text(
            "**⛔ ᴅᴀɪʟʏ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!**\n"
            "💤 ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄᴀᴘᴛᴜʀᴇᴅ 25 ᴄʜᴀʀᴀᴄᴛᴇʀs ᴛᴏᴅᴀʏ.\n"
            "🗓️ ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴛᴏᴍᴏʀʀᴏᴡ ᴛᴏ ᴄᴀᴛᴄʜ ᴍᴏʀᴇ!"
        )
        return

    # Initialize chat lock if not exists
    if chat_id not in chat_locks:
        chat_locks[chat_id] = Lock()

    async with chat_locks[chat_id]:
        start_time = time.time()

        # Validate input
        args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None    
        
        if not args or "()" in args or "&" in args:    
            await message.reply_text(
                "**⚠️ ɪɴᴠᴀʟɪᴅ ɴᴀᴍᴇ ᴇɴᴛᴇʀᴇᴅ!**\n"
                "➤ ᴘʟᴇᴀꜱᴇ ᴀᴠᴏɪᴅ ᴜsɪɴɢ sʏᴍʙᴏʟs ʟɪᴋᴇ `()` ᴏʀ `&`.\n"
                "ᴛʏᴘᴇ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ɴᴀᴍᴇ ᴏꜰ ᴛʜᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴛᴏ ᴄᴀᴘᴛᴜʀᴇ!"
            )
            return    
        
        guess = args.strip()    

        # Check if character is spawned
        if chat_id not in spawned_characters:    
            last_seized = last_despawned_characters.get(chat_id)    
            if last_seized:    
                last_user = last_seized["user"] or "ɴᴏ ᴏɴᴇ"
                last_name = last_seized["character"]["name"]    
                await message.reply_text(
                    f"**❌ ɴᴏ ᴄᴀᴘᴛᴜʀᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ.**\n\n"
                    f"🕊️ **ʟᴀꜱᴛ ꜱᴇɪᴢᴇᴅ ʙʏ** {last_user}:\n"
                    f"➥ `{last_name}`"
                )
            else:    
                await message.reply_text(
                    "**🌫️ ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪɴ sɪɢʜᴛ...**\n"
                    "ᴛʜᴇ ғɪᴇʟᴅ ɪs ᴇᴍᴘᴛʏ ʀɪɢʜᴛ ɴᴏᴡ.\n"
                    "⚡ ᴡᴀɪᴛ ꜰᴏʀ ᴀ ɴᴇᴡ ᴡᴀɴᴅᴇʀᴇʀ ᴛᴏ ᴀʀʀɪᴠᴇ!"
                )
            return    
        
        character = spawned_characters[chat_id]    
        character_name = character['name']    

        # Check animated character limit
        if character['rarity'] == '⚜️ Animated' and user_id != owner_id:
            if user_animated_limits[user_id]["count"] >= 4:
                # Send DM about limit
                try:
                    await app.send_message(
                        user_id,
                        "**⚜️ Animated Character Limit Reached!**\n\n"
                        "You can only capture **4 animated characters** every 24 hours.\n"
                        "The limit will reset automatically at midnight.\n\n"
                        "Current animated captures today: **4/4**"
                    )
                except:
                    pass  # User hasn't started bot in DM
                
                await message.reply_text(
                    "**⛔ Animated Character Limit Reached!**\n\n"
                    "Check your DM for more information about the daily limit."
                )
                return

        # Validate guess using the improved name matching function
        if not is_valid_capture_name(guess, character_name):    
            message_link = f"https://t.me/c/{str(chat_id)[4:]}/{character['message_id']}"    
            keyboard = [[InlineKeyboardButton("🔍 ᴠɪᴇᴡ ᴄʜᴀʀᴀᴄᴛᴇʀ", url=message_link)]]    
            
            # Show helpful hints about valid names
            char_name_parts = normalize_name(character_name).split()
            hint_text = ""
            if len(char_name_parts) > 1:
                hint_text = f"\n💡 **ᴛʀʏ**: `{char_name_parts[0]}` (ғɪʀsᴛ ɴᴀᴍᴇ) ᴏʀ `{char_name_parts[-1]}` (ʟᴀsᴛ ɴᴀᴍᴇ)"
            
            await message.reply_text(
                f"**🚫 ɢᴜᴇꜱꜱ ᴅᴇɴɪᴇᴅ!**\n"
                f"`{guess}` **ᴅᴏᴇsɴ'ᴛ ᴍᴀᴛᴄʜ ᴛʜɪꜱ ᴄʜᴀʀᴀᴄᴛᴇʀ.**\n"
                "🔎 ᴛᴀᴋᴇ ᴀ ᴄʟᴏꜱᴇʀ ʟᴏᴏᴋ ʙᴇғᴏʀᴇ ʏᴏᴜ ᴛʀʏ ᴀɢᴀɪɴ.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return    

        # SUCCESSFUL CAPTURE - Process the capture
        # Update daily seize count
        user_daily_seizes[user_id]["count"] += 1

        # Update animated limit if applicable
        if character['rarity'] == '⚜️ Animated':
            user_animated_limits[user_id]["count"] += 1

        # Calculate time taken
        end_time = time.time()
        elapsed = round(end_time - character["spawn_time"])
        minutes = elapsed // 60
        seconds = elapsed % 60
        time_taken = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        # Calculate gold reward based on rarity
        gold_reward = RARITY_GOLD_REWARDS.get(character["rarity"], 10)
        
        # Update user's gold balance
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'gold': gold_reward}},
            upsert=True
        )

        # Check if this completes an anime collection
        anime_completed = await check_anime_completion(user_id, character)
        
        # Update collections
        await user_collection.update_one(
            {'id': user_id}, 
            {'$push': {'characters': character}},
            upsert=True
        )
        
        await group_user_totals_collection.update_one(    
            {'user_id': user_id, 'group_id': chat_id},    
            {'$inc': {'count': 1}},    
            upsert=True    
        )    
        
        await top_global_groups_collection.update_one(    
            {'group_id': chat_id},    
            {'$inc': {'count': 1}, '$set': {'group_name': message.chat.title}},    
            upsert=True    
        )    

        # Store last seized character
        last_despawned_characters[chat_id] = {    
            "user": message.from_user.mention,    
            "character": character,
            "spawn_time": character["spawn_time"]
        }    

        # Fast emoji animation
        anim_msg = await message.reply_text("💙")    
        for emoji in ["🩵", "💜"]:    
            await asyncio.sleep(0.3)    
            await anim_msg.edit_text(emoji)    
        await anim_msg.delete()    

        # Final message with simple formatting
        remaining_seizes = max(0, 25 - user_daily_seizes[user_id]["count"]) if user_id != owner_id else "∞"
        
        final_msg = (
            f"<blockquote>{message.from_user.mention} sᴀɴ ʜᴀꜱ ᴄᴀᴘᴛᴜʀᴇᴅ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ!</blockquote>\n\n"
            f"**🎀 ɴᴀᴍᴇ:** `{character['name']}`\n"
            f"**🍄 ʀᴀʀɪᴛʏ:** `{character['rarity']}`\n"
            f"**⛩️ ᴀɴɪᴍᴇ:** `{character['anime']}`\n\n"
            f"**⏱️ ᴄᴀᴘᴛᴜʀᴇ ᴛɪᴍᴇ:** `{time_taken}`\n"
            f"**🧮 ᴅᴀɪʟʏ ᴄᴀᴘᴛᴜʀᴇs:** `{user_daily_seizes[user_id]['count']}/25`"
        )

        # Add anime completion message if applicable
        if anime_completed:
            final_msg += f"\n\n🎉 **CONGRATULATIONS!** 🎉\nYou have completed the **{character['anime']}** anime collection! 🏆"

        # Button with inline query
        buttons = [    
            [InlineKeyboardButton(    
                f"🧃 {message.from_user.first_name}'s ᴄᴏʟʟᴇᴄᴛɪᴏɴ",     
                switch_inline_query_current_chat=f"collection.{user_id}"    
            )]    
        ]    
        
        await message.reply_text(    
            final_msg,    
            reply_markup=InlineKeyboardMarkup(buttons)    
        )    

        # Send gold reward notification
        gold_emoji = await get_random_gold_emoji()
        await message.reply_text(
            f"{gold_emoji} **ʏᴏᴜ ʀᴇᴄᴇɪᴠᴇᴅ** `{gold_reward} ₲` **ғᴏʀ sᴇɪᴢɪɴɢ ᴀ {character['rarity']} ᴄʜᴀʀᴀᴄᴛᴇʀ!**\n"
            f"➥ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ᴡɪᴛʜ /mygold",
            reply_to_message_id=message.id
        )

        # Remove character and react with big reaction
        del spawned_characters[chat_id]    
        try:    
            await message.react("⚡", big=True)  # Big reaction
        except:    
            try:    
                await message.react(random.choice(["🔥", "⚡", "💯", "🎉"]))  # Fallback to normal reaction
            except:    
                pass

@app.on_message(filters.command("rmlimit"))
async def remove_limit(_, message):
    if not message.from_user or message.from_user.id != owner_id:
        await message.reply_text("❌ You are not authorized to use this command.")
        return
    
    target_id = None
    
    # Check if user is replied to
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID format.")
            return
    
    if not target_id:
        await message.reply_text("Usage: /rmlimit [user_id] or reply to a user's message with /rmlimit")
        return
    
    # Reset both daily seize limit and animated limit
    if target_id in user_daily_seizes:
        user_daily_seizes[target_id]["count"] = 0
    
    if target_id in user_animated_limits:
        user_animated_limits[target_id]["count"] = 0
    
    await message.reply_text(f"✅ Successfully reset daily limits for user {target_id}")
