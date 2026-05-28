from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from . import app, user_collection
import random
import time
import humanize
from datetime import datetime, timedelta
import asyncio

# Enhanced Blue Lock characters database with more characters including Kaiser
BLUE_LOCK_CHARACTERS = {
    "yoichi_isagi": {
        "name": "ʏᴏɪᴄʜɪ ɪsᴀɢɪ",
        "emoji": "🔵",
        "win_video": "https://files.catbox.moe/1xdj2v.mp4",
        "lose_video": "https://files.catbox.moe/hpq6lf.mp4",
        "start_video": "https://files.catbox.moe/ogsx37.mp4",
        "cooldown_video": "https://files.catbox.moe/eq2p75.mp4",
        "image": "https://files.catbox.moe/bdpc8p.jpg",
        "quote": "ɪ'ʟʟ ᴅᴇsᴛʀᴏʏ ᴇᴠᴇʀʏᴛʜɪɴɢ ᴛʜᴀᴛ ɢᴇᴛs ɪɴ ᴍʏ ᴡᴀʏ!",
        "cooldown_quotes": [
            "ɪ ɴᴇᴇᴅ ᴛɪᴍᴇ ᴛᴏ ᴀɴᴀʟʏᴢᴇ ᴍʏ ɴᴇxᴛ ᴍᴏᴠᴇ!",
            "ᴇᴠᴇɴ ᴀ ᴅᴇᴍᴏɴ ɴᴇᴇᴅs ᴀ ʙʀᴇᴀᴋ...",
            "ᴛʜɪs ɪsɴ'ᴛ ᴛʜᴇ ᴇɴᴅ! ɪ'ʟʟ ʙᴇ ʙᴀᴄᴋ!"
        ],
        "win_quotes": [
            "ᴛʜɪs ɪs ᴍʏ ᴇɢᴏɪsᴛ's ᴠɪᴄᴛᴏʀʏ!",
            "ɪ sᴀᴡ ᴛʜʀᴏᴜɢʜ ʏᴏᴜʀ ᴇɴᴛɪʀᴇ ᴘʟᴀʏ!",
            "ɴᴇxᴛ ɢᴏᴀʟ: ᴡᴏʀʟᴅ ᴅᴏᴍɪɴᴀᴛɪᴏɴ!"
        ],
        "lose_quotes": [
            "ɴᴏ... ᴛʜɪs ᴄᴀɴ'ᴛ ʙᴇ ᴛʜᴇ ᴇɴᴅ!",
            "ɪ'ʟʟ ᴅᴇᴠᴏᴜʀ ʏᴏᴜ ɴᴇxᴛ ᴛɪᴍᴇ!",
            "ᴍʏ ᴇɢᴏ... ɪᴛ's ɴᴏᴛ ᴅᴇᴀᴅ ʏᴇᴛ!"
        ]
    },
    "rin_itoshi": {
        "name": "ʀɪɴ ɪᴛᴏsʜɪ",
        "emoji": "🔥",
        "win_video": "https://files.catbox.moe/7f18ql.mp4",
        "lose_video": "https://files.catbox.moe/7p2w6o.mp4",
        "start_video": "https://files.catbox.moe/zb0dsb.mp4",
        "cooldown_video": "https://files.catbox.moe/zyk9jp.mp4",
        "image": "https://files.catbox.moe/7vjvbg.jpg",
        "quote": "ɪ ᴅᴏɴ'ᴛ ɴᴇᴇᴅ ᴀɴʏᴏɴᴇ. ɪ'ᴍ ᴛʜᴇ sᴏʟᴇ sᴛʀɪᴋᴇʀ!",
        "cooldown_quotes": [
            "ɪ ᴡᴏɴ'ᴛ ᴡᴀsᴛᴇ ᴍʏ sᴛʀᴇɴɢᴛʜ ᴏɴ ᴛʜɪs ʀɪɢʜᴛ ɴᴏᴡ!",
            "ᴛʜᴇ ɴᴇxᴛ ᴛɪᴍᴇ ɪ'ʟʟ ᴅᴇsᴛʀᴏʏ ʏᴏᴜ ᴄᴏᴍᴘʟᴇᴛᴇʟʏ!",
            "ᴛʜɪs ɪs ʙᴇɴᴇᴀᴛʜ ᴍᴇ... ɪ'ʟʟ ᴡᴀɪᴛ ғᴏʀ ᴀ ʀᴇᴀʟ ᴄʜᴀʟʟᴇɴɢᴇ!"
        ],
        "win_quotes": [
            "ᴘᴀᴛʜᴇᴛɪᴄ. ʏᴏᴜ ᴡᴇʀᴇ ɴᴇᴠᴇʀ ᴍʏ ᴍᴀᴛᴄʜ!",
            "ᴛʜɪs ɪs ᴛʜᴇ ᴅɪғғᴇʀᴇɴᴄᴇ ʙᴇᴛᴡᴇᴇɴ ᴜs!",
            "ɪ ᴀᴍ ᴛʜᴇ ʜᴇɪʀ ᴛᴏ ᴊᴀᴘᴀɴᴇsᴇ ғᴏᴏᴛʙᴀʟʟ!"
        ],
        "lose_quotes": [
            "ɪᴍᴘᴏssɪʙʟᴇ... ʜᴏᴡ ᴅᴀʀᴇ ʏᴏᴜ!",
            "ɴᴅᴇxᴛ ᴛɪᴍᴇ... ɪ'ʟʟ ᴋɪʟʟ ʏᴏᴜ!",
            "ᴛʜɪs ᴡᴀsɴ'ᴛ ᴍʏ ғᴜʟʟ sᴛʀᴇɴɢᴛʜ!"
        ]
    },
    "seishiro_nagi": {
        "name": "sᴇɪsʜɪʀō ɴᴀɢɪ",
        "emoji": "❄️",
        "win_video": "https://files.catbox.moe/ezbu8g.mp4",
        "lose_video": "https://files.catbox.moe/rlsz5u.mp4",
        "start_video": "https://files.catbox.moe/tq5opy.mp4",
        "cooldown_video": "https://files.catbox.moe/rlsz5u.mp4",
        "image": "https://files.catbox.moe/67sokc.jpg",
        "quote": "ғᴏᴏᴛʙᴀʟʟ ɪs ᴇᴀsʏ... ʟɪᴋᴇ ᴀ ᴠɪᴅᴇᴏ ɢᴀᴍᴇ.",
        "cooldown_quotes": [
            "ɪ'ᴍ ʙᴏʀᴇᴅ... ᴡᴀᴋᴇ ᴍᴇ ᴡʜᴇɴ ɪᴛ's ᴛɪᴍᴇ ᴛᴏ ᴘʟᴀʏ.",
            "ᴛʜɪs ɪs ᴛᴏᴏ ᴇᴀsʏ... ɪ ɴᴇᴇᴅ ᴀ ʀᴇᴀʟ ᴄʜᴀʟʟᴇɴɢᴇ.",
            "ᴢᴢᴢ... ᴡʜᴀᴛ? ᴏʜ, ɪ ᴡᴀs sʟᴇᴇᴘɪɴɢ."
        ],
        "win_quotes": [
            "ᴛᴏᴏ ᴇᴀsʏ... ᴡʜᴇɴ ᴡɪʟʟ ɪ ғɪɴᴅ ᴀ ʀᴇᴀʟ ᴄʜᴀʟʟᴇɴɢᴇ?",
            "ɪ ᴡᴏɴ ʙᴇᴄᴀᴜsᴇ ɪ ғᴇʟᴛ ʟɪᴋᴇ ɪᴛ.",
            "ʏᴏᴜ ʀᴇᴀʟʟʏ ᴛʜᴏᴜɢʜᴛ ʏᴏᴜ ᴄᴏᴜʟᴅ ᴡɪɴ?"
        ],
        "lose_quotes": [
            "ʜᴜʜ... ɪ ɢᴜᴇss ɪ ʟᴏsᴛ.",
            "ᴍᴇʜ... ɪ ᴡᴀsɴ'ᴛ ʀᴇᴀʟʟʏ ᴛʀʏɪɴɢ.",
            "ɪғ ɪ ᴀᴄᴛᴜᴀʟʟʏ ᴄᴀʀᴇᴅ, ɪ ᴡᴏᴜʟᴅ'ᴠᴇ ᴡᴏɴ."
        ]
    },
    "meguru_bachira": {
        "name": "ᴍᴇɢᴜʀᴜ ʙᴀᴄʜɪʀᴀ",
        "emoji": "🦋",
        "win_video": "https://files.catbox.moe/fwzxkf.mp4",
        "lose_video": "https://files.catbox.moe/reikre.mp4",
        "start_video": "https://files.catbox.moe/uhyeua.mp4",
        "cooldown_video": "https://files.catbox.moe/lh7qzm.mp4",
        "image": "https://files.catbox.moe/5x7i3a.jpg",
        "quote": "ʟᴇᴛ's ᴘʟᴀʏ sᴏᴍᴇ ғᴜɴ ғᴏᴏᴛʙᴀʟʟ!",
        "cooldown_quotes": [
            "ᴛɪᴍᴇ ᴏᴜᴛ? ʙᴜᴛ ɪ ᴡᴀɴᴛ ᴛᴏ ᴋᴇᴇᴘ ᴘʟᴀʏɪɴɢ!",
            "ᴍʏ ᴍᴏɴsᴛᴇʀ ɪs ɢᴇᴛᴛɪɴɢ ʀᴇsᴛʟᴇss...",
            "ɪ'ʟʟ ʙᴇ ʙᴀᴄᴋ sᴏᴏɴ ᴡɪᴛʜ ᴍᴏʀᴇ ᴛʀɪᴄᴋs!"
        ],
        "win_quotes": [
            "ᴡᴏᴏʜᴏᴏ! ᴛʜᴀᴛ ᴡᴀs ғᴜɴ!",
            "ᴍʏ ᴍᴏɴsᴛᴇʀ ᴡᴀɴᴛs ᴛᴏ ᴘʟᴀʏ ᴍᴏʀᴇ!",
            "ʟᴇᴛ's ᴅᴀɴᴄᴇ ᴏɴ ᴛʜᴇ ғɪᴇʟᴅ!"
        ],
        "lose_quotes": [
            "ᴀᴡᴡ... ʙᴜᴛ ɪ ᴡᴀs ʜᴀᴠɪɴɢ ғᴜɴ!",
            "ᴍʏ ᴍᴏɴsᴛᴇʀ ɪs sᴀᴅ ɴᴏᴡ...",
            "ɴᴇxᴛ ᴛɪᴍᴇ ɪ'ʟʟ sʜᴏᴡ ʏᴏᴜ sᴏᴍᴇᴛʜɪɴɢ ᴄᴏᴏʟᴇʀ!"
        ]
    },
    "michael_kaiser": {
        "name": "ᴍɪᴄʜᴀᴇʟ ᴋᴀɪsᴇʀ",
        "emoji": "👑",
        "win_video": "https://files.catbox.moe/lbjtsn.mp4",
        "lose_video": "https://files.catbox.moe/g6eod1.mp4",
        "start_video": "https://files.catbox.moe/nh2amv.mp4",
        "cooldown_video": "https://files.catbox.moe/n3ljbe.mp4",
        "image": "https://files.catbox.moe/q8e4ki.jpg",
        "quote": "ɪ ᴀᴍ ᴛʜᴇ ᴇᴍᴘᴇʀᴏʀ! ɴᴏ ᴏɴᴇ ᴄᴀɴ sᴛᴀɴᴅ ɪɴ ᴍʏ ᴡᴀʏ!",
        "cooldown_quotes": [
            "ᴇᴠᴇɴ ᴀɴ ᴇᴍᴘᴇʀᴏʀ ɴᴇᴇᴅs ᴀ ʙʀᴇᴀᴋ!",
            "ᴛʜɪs ɪs ʙᴇɴᴇᴀᴛʜ ᴍʏ ᴅɪɢɴɪᴛʏ...",
            "ɪ'ʟʟ ʀᴇᴛᴜʀɴ ᴡʜᴇɴ ʏᴏᴜ'ʀᴇ ᴡᴏʀᴛʜʏ ᴏғ ᴍʏ ᴛɪᴍᴇ!"
        ],
        "win_quotes": [
            "ᴋɴᴇᴇʟ ʙᴇғᴏʀᴇ ʏᴏᴜʀ ᴇᴍᴘᴇʀᴏʀ!",
            "ᴛʜɪs ɪs ᴡʜʏ ɪ'ᴍ ᴛʜᴇ ʙᴇsᴛ ɪɴ ᴛʜᴇ ᴡᴏʀʟᴅ!",
            "ᴘᴀᴛʜᴇᴛɪᴄ. ʏᴏᴜ sᴛᴀɴᴅ ɴᴏ ᴄʜᴀɴᴄᴇ ᴀɢᴀɪɴsᴛ ᴍᴇ!"
        ],
        "lose_quotes": [
            "ɪᴍᴘᴏssɪʙʟᴇ! ɴᴏ ᴏɴᴇ ᴄᴀɴ ᴅᴇғᴇᴀᴛ ᴛʜᴇ ᴇᴍᴘᴇʀᴏʀ!",
            "ᴛʜɪs ɪs ᴊᴜsᴛ ᴀ sᴇᴛʙᴀᴄᴋ... ɪ'ʟʟ ʀᴇᴛᴜʀɴ sᴛʀᴏɴɢᴇʀ!",
            "ʏᴏᴜ ɢᴏᴛ ʟᴜᴄᴋʏ! ɴᴇxᴛ ᴛɪᴍᴇ ɪ ᴡᴏɴ'ᴛ ʜᴏʟᴅ ʙᴀᴄᴋ!"
        ]
    }
}

# Store user character selections
user_characters = {}
# Store cooldown timestamps
user_cooldowns = {}
# Store active games to prevent multiple games at once
active_games = set()
# Store PvP challenges
pvp_challenges = {}

# Start Blue Lock game with enhanced interface
@app.on_message(filters.command(["startblue", "bluelock"]))
async def start_blue_lock(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text("⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪғʏ ᴜsᴇʀ.")
        return
    
    # Create character selection interface with images
    keyboard = []
    row = []
    for i, (char_id, char) in enumerate(BLUE_LOCK_CHARACTERS.items()):
        row.append(InlineKeyboardButton(
            f"{char['emoji']} {char['name']}",
            callback_data=f"blueselect_{char_id}"
        ))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    if row:  # Add remaining buttons if any
        keyboard.append(row)
    
    await message.reply_photo(
        photo="https://files.catbox.moe/pvdxav.jpg",  # Blue Lock title image
        caption=(
            "╭━━━━━━━━━━━━━━━━━━━━━╮\n"
            "       **ʙʟᴜᴇ ʟᴏᴄᴋ ᴀʀᴇɴᴀ**      \n"
            "╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "**ᴄʜᴏᴏsᴇ ʏᴏᴜʀ sᴛʀɪᴋᴇʀ ᴛᴏ ᴇɴᴛᴇʀ ᴛʜᴇ ʙᴀᴛᴛʟᴇ:**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            "⚽ ᴇᴠᴏʟᴠᴇ ʏᴏᴜʀ ᴇɢᴏ ᴀɴᴅ ʙᴇᴄᴏᴍᴇ ᴛʜᴇ ᴡᴏʀʟᴅ's ɢʀᴇᴀᴛᴇsᴛ sᴛʀɪᴋᴇʀ!"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Character selection handler with enhanced interface
@app.on_callback_query(filters.regex(r"^blueselect_"))
async def select_character(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        character_id = callback_query.data.split("_", 1)[1]
        
        if character_id not in BLUE_LOCK_CHARACTERS:
            await callback_query.answer("ɪɴᴠᴀʟɪᴅ ᴄʜᴀʀᴀᴄᴛᴇʀ sᴇʟᴇᴄᴛᴇᴅ!", show_alert=True)
            return
        
        character = BLUE_LOCK_CHARACTERS[character_id]
        user_characters[user_id] = character_id
        
        await callback_query.message.edit_media(
            media=InputMediaPhoto(
                media=character["image"],
                caption=(
                    f"╭━━━━━━━━━━━━━━━━━━━━━╮\n"
                    f"   **{character['emoji']} {character['name']} sᴇʟᴇᴄᴛᴇᴅ!**   \n"
                    f"╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                    f"✦ **{character['quote']}**\n"
                    f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    f"ᴜsᴇ /blue ᴛᴏ sᴛᴀʀᴛ ᴀ ᴍᴀᴛᴄʜ (40% ᴏғ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ʙᴇᴛ)\n"
                    f"ᴏʀ /startblue ᴛᴏ sᴇʟᴇᴄᴛ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀʀᴀᴄᴛᴇʀ"
                )
            ),
            reply_markup=None
        )
        
        # Send character introduction video
        await callback_query.message.reply_video(
            character["start_video"],
            caption=(
                f"⚡ **{character['name']} {character['emoji']} ʜᴀs ᴇɴᴛᴇʀᴇᴅ ᴛʜᴇ ғɪᴇʟᴅ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **{character['quote']}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
            )
        )
        await callback_query.answer(f"ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ {character['name']}")
    except Exception as e:
        print(f"Error in select_character: {e}")
        await callback_query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!", show_alert=True)

# Enhanced Blue Lock game command with anime-style interface
@app.on_message(filters.command(["blue", "bluematch"]))
async def play_blue_lock(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text("⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪғʏ ᴜsᴇʀ.")
        return
    
    # Prevent multiple games at once
    if user.id in active_games:
        await message.reply_text(
            "⚠️ **ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ!**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ɪᴛ ᴛᴏ ғɪɴɪsʜ."
        )
        return
    
    active_games.add(user.id)
    
    try:
        # Check cooldown first
        current_time = datetime.now()
        if user.id in user_cooldowns:
            cooldown_end = user_cooldowns[user.id]
            if current_time < cooldown_end:
                remaining = cooldown_end - current_time
                remaining_seconds = int(remaining.total_seconds())
                
                # Get user's character
                if user.id in user_characters:
                    character = BLUE_LOCK_CHARACTERS[user_characters[user.id]]
                    cooldown_quote = random.choice(character["cooldown_quotes"])
                    
                    # Send cooldown message with video
                    await message.reply_video(
                        character["cooldown_video"],
                        caption=(
                            f"⏳ **{character['name']} {character['emoji']} ɪs ɪɴ ᴄᴏᴏʟᴅᴏᴡɴ!**\n\n"
                            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                            f"✦ **{cooldown_quote}**\n"
                            f"✦ **ᴛɪᴍᴇ ʀᴇᴍᴀɪɴɪɴɢ:** {humanize.naturaldelta(remaining)}\n"
                            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
                        ),
                        reply_to_message_id=message.id
                    )
                else:
                    await message.reply_text(
                        f"⏳ **ʏᴏᴜ'ʀᴇ ɪɴ ᴄᴏᴏʟᴅᴏᴡɴ!**\n"
                        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                        f"ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {humanize.naturaldelta(remaining)} ʙᴇғᴏʀᴇ ᴘʟᴀʏɪɴɢ ᴀɢᴀɪɴ.\n"
                        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
                    )
                return
        
        # Get user balance
        user_data = await user_collection.find_one({'id': user.id})
        current_gold = float(user_data.get('gold', 0)) if user_data else 0
        
        if current_gold <= 0:
            await message.reply_text(
                "⚠️ **ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴʏ ɢᴏʟᴅ ᴛᴏ ᴘʟᴀʏ!**\n"
                "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                "ᴇᴀʀɴ sᴏᴍᴇ ɢᴏʟᴅ ғɪʀsᴛ ʙʏ ᴘʟᴀʏɪɴɢ ᴏᴛʜᴇʀ ɢᴀᴍᴇs!"
            )
            return
        
        # Check if user has selected a character
        if user.id not in user_characters:
            await message.reply_text(
                "⚠️ **ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ғɪʀsᴛ!**\n"
                "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                "ᴜsᴇ /startblue ᴛᴏ ᴄʜᴏᴏsᴇ ʏᴏᴜʀ sᴛʀɪᴋᴇʀ."
            )
            return
        
        character_id = user_characters[user.id]
        character = BLUE_LOCK_CHARACTERS[character_id]
        
        # Calculate 40% of balance (minimum 1 gold)
        amount = max(1, round(current_gold * 0.4, 2))
        
        # Deduct the gold
        await user_collection.update_one(
            {'id': user.id},
            {'$inc': {'gold': -amount}},
            upsert=True
        )
        
        # Send loading message with anime-style countdown
        processing_msg = await message.reply_photo(
            photo=character["image"],
            caption=(
                f"⚽ **{character['name']} {character['emoji']} ɪs ʀᴜɴɴɪɴɢ...**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ᴀᴜᴛᴏ ʙᴇᴛ:** {humanize.intcomma(amount)} ₲ (40% ᴏғ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ)\n"
                f"✦ **ᴘʀᴇᴘᴀʀɪɴɢ ᴛʜᴇ ᴍᴀᴛᴄʜ...**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                "⚡ _ᴛʜᴇ ᴍᴀᴛᴄʜ ᴡɪʟʟ sᴛᴀʀᴛ ɪɴ 3... 2... 1..._"
            )
        )
        
        # Simulate processing with anime-style countdown
        for i in range(3, 0, -1):
            time.sleep(1)
            await processing_msg.edit_caption(
                f"⚽ **{character['name']} {character['emoji']} ɪs ʀᴜɴɴɪɴɢ...**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ᴀᴜᴛᴏ ʙᴇᴛ:** {humanize.intcomma(amount)} ₲ (40% ᴏғ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ)\n"
                f"✦ **ᴘʀᴇᴘᴀʀɪɴɢ ᴛʜᴇ ᴍᴀᴛᴄʜ...**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"⚡ _ᴛʜᴇ ᴍᴀᴛᴄʜ ᴡɪʟʟ sᴛᴀʀᴛ ɪɴ {i}..._"
            )
        
        # 50% chance to win
        is_winner = random.random() < 0.5
        
        # Calculate multiplier with more exciting possibilities
        if is_winner:
            # 70% chance for 2x, 20% chance for 2.5x, 10% chance for higher (3x-5x)
            rand = random.random()
            if rand < 0.7:
                multiplier = 2.0
            elif rand < 0.9:
                multiplier = 2.5
            else:
                multiplier = round(random.uniform(3.0, 5.0), 1)
        else:
            multiplier = 0
        
        # Calculate winnings
        winnings = round(amount * multiplier, 2)
        
        # Update user's gold if they won
        if is_winner:
            await user_collection.update_one(
                {'id': user.id},
                {'$inc': {'gold': winnings}},
                upsert=True
            )
        
        # Prepare result message with anime-style effects
        if is_winner:
            result_quote = random.choice(character["win_quotes"])
            result_text = (
                f"🎉 **ɢᴏᴀʟ! {character['name']} {character['emoji']} sᴄᴏʀᴇᴅ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ʏᴏᴜ ᴡᴏɴ:** {humanize.intcomma(winnings)} ₲\n"
                f"✦ **ᴍᴜʟᴛɪᴘʟɪᴇʀ:** x{multiplier:.1f}\n"
                f"✦ **{result_quote}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"⚡ ʏᴏᴜʀ ᴇɢᴏ ʜᴀs ɢʀᴏᴡɴ sᴛʀᴏɴɢᴇʀ!"
            )
            video_url = character["win_video"]
        else:
            result_quote = random.choice(character["lose_quotes"])
            result_text = (
                f"❌ **ᴍɪss! {character['name']} {character['emoji']} ғᴀɪʟᴇᴅ ᴛᴏ sᴄᴏʀᴇ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ʏᴏᴜ ʟᴏsᴛ:** {humanize.intcomma(amount)} ₲\n"
                f"✦ **{result_quote}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"⚡ ʏᴏᴜʀ ᴇɢᴏ ʜᴀs ʙᴇᴇɴ ᴄʀᴜsʜᴇᴅ... ʙᴜᴛ ɪᴛ ᴡɪʟʟ ʀᴇᴛᴜʀɴ sᴛʀᴏɴɢᴇʀ!"
            )
            video_url = character["lose_video"]
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send result with video
        await message.reply_video(
            video_url,
            caption=result_text,
            reply_to_message_id=message.id
        )
        
        # Set cooldown (2 minutes)
        user_cooldowns[user.id] = current_time + timedelta(minutes=2)
        
    except Exception as e:
        print(f"Error in play_blue_lock: {e}")
        await message.reply_text(
            "⚠️ **ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."
        )
    finally:
        # Remove user from active games
        if user.id in active_games:
            active_games.remove(user.id)

# PvP Blue Lock game command
@app.on_message(filters.command(["pblue", "bluepvp"]))
async def pvp_blue_lock(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text("⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪғʏ ᴜsᴇʀ.")
        return
    
    # Check if message is a reply
    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ **ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ's ᴍᴇssᴀɢᴇ!**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "ᴜsᴀɢᴇ: ʀᴇᴘʟʏ `/pblue <ᴀᴍᴏᴜɴᴛ>` ᴛᴏ ᴀ ᴜsᴇʀ's ᴍᴇssᴀɢᴇ"
        )
        return
    
    target_user = message.reply_to_message.from_user
    if not target_user:
        await message.reply_text("⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪғʏ ᴛᴀʀɢᴇᴛ ᴜsᴇʀ.")
        return
    
    if user.id == target_user.id:
        await message.reply_text("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴄʜᴀʟʟᴇɴɢᴇ ʏᴏᴜʀsᴇʟғ!")
        return
    
    # Parse amount
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("⚠️ ᴘʟᴇᴀsᴇ sᴘᴇᴄɪғʏ ᴀɴ ᴀᴍᴏᴜɴᴛ. ᴜsᴀɢᴇ: /pblue <ᴀᴍᴏᴜɴᴛ>")
            return
        
        amount = float(parts[1])
        if amount <= 0:
            await message.reply_text("⚠️ ᴀᴍᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ ᴘᴏsɪᴛɪᴠᴇ!")
            return
    except ValueError:
        await message.reply_text("⚠️ ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ!")
        return
    
    # Check if user has enough gold
    user_data = await user_collection.find_one({'id': user.id})
    user_gold = float(user_data.get('gold', 0)) if user_data else 0
    
    if user_gold < amount:
        await message.reply_text(
            f"⚠️ **ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"ʏᴏᴜ ɴᴇᴇᴅ: {humanize.intcomma(amount)} ₲\n"
            f"ʏᴏᴜ ʜᴀᴠᴇ: {humanize.intcomma(user_gold)} ₲"
        )
        return
    
    # Check if target user has enough gold
    target_data = await user_collection.find_one({'id': target_user.id})
    target_gold = float(target_data.get('gold', 0)) if target_data else 0
    
    if target_gold < amount:
        await message.reply_text(
            f"⚠️ **{target_user.first_name} ᴅᴏᴇsɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"ᴛʜᴇʏ ɴᴇᴇᴅ: {humanize.intcomma(amount)} ₲\n"
            f"ᴛʜᴇʏ ʜᴀᴠᴇ: {humanize.intcomma(target_gold)} ₲"
        )
        return
    
    # Check if target user already has a pending challenge
    if target_user.id in pvp_challenges:
        await message.reply_text(
            f"⚠️ **{target_user.first_name} ᴀʟʀᴇᴀᴅʏ ʜᴀs ᴀ ᴘᴇɴᴅɪɴɢ ᴄʜᴀʟʟᴇɴɢᴇ!**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟ ᴛʜᴇʏ ʀᴇsᴘᴏɴᴅ ᴛᴏ ɪᴛ."
        )
        return
    
    # Create challenge
    challenge_id = f"{user.id}_{target_user.id}_{int(time.time())}"
    pvp_challenges[target_user.id] = {
        'challenger_id': user.id,
        'challenger_name': user.first_name,
        'amount': amount,
        'challenge_id': challenge_id,
        'timestamp': datetime.now()
    }
    
    # Send challenge message with accept/reject buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ᴀᴄᴄᴇᴘᴛ", callback_data=f"pvpaccept_{challenge_id}"),
            InlineKeyboardButton("❌ ʀᴇᴊᴇᴄᴛ", callback_data=f"pvreject_{challenge_id}")
        ]
    ])
    
    challenge_msg = await message.reply_text(
        f"⚔️ **ʙʟᴜᴇ ʟᴏᴄᴋ ᴘᴠᴘ ᴄʜᴀʟʟᴇɴɢᴇ!**\n\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        f"✦ **ᴄʜᴀʟʟᴇɴɢᴇʀ:** {user.first_name}\n"
        f"✦ **ᴛᴀʀɢᴇᴛ:** {target_user.first_name}\n"
        f"✦ **ʙᴇᴛ ᴀᴍᴏᴜɴᴛ:** {humanize.intcomma(amount)} ₲\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
        f"{target_user.first_name}, ᴅᴏ ʏᴏᴜ ᴀᴄᴄᴇᴘᴛ ᴛʜɪs ᴄʜᴀʟʟᴇɴɢᴇ?",
        reply_markup=keyboard
    )
    
    # Store challenge message ID for later editing
    pvp_challenges[target_user.id]['message_id'] = challenge_msg.id
    
    # Set timeout for challenge (2 minutes)
    await asyncio.sleep(120)
    if target_user.id in pvp_challenges and pvp_challenges[target_user.id]['challenge_id'] == challenge_id:
        del pvp_challenges[target_user.id]
        await challenge_msg.edit_text(
            f"⏰ **ᴄʜᴀʟʟᴇɴɢᴇ ᴇxᴘɪʀᴇᴅ!**\n\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"{target_user.first_name} ᴅɪᴅ ɴᴏᴛ ʀᴇsᴘᴏɴᴅ ᴛᴏ ᴛʜᴇ ᴄʜᴀʟʟᴇɴɢᴇ ɪɴ ᴛɪᴍᴇ."
        )

# PvP challenge response handler
@app.on_callback_query(filters.regex(r"^pvpaccept_|pvreject_"))
async def handle_pvp_response(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        action, challenge_id = data.split("_", 1)
        
        # Check if user has a pending challenge
        if user_id not in pvp_challenges or pvp_challenges[user_id]['challenge_id'] != challenge_id:
            await callback_query.answer("ᴛʜɪs ᴄʜᴀʟʟᴇɴɢᴇ ʜᴀs ᴇxᴘɪʀᴇᴅ ᴏʀ ᴅᴏᴇsɴ'ᴛ ᴇxɪsᴛ!", show_alert=True)
            return
        
        challenge = pvp_challenges[user_id]
        challenger_id = challenge['challenger_id']
        amount = challenge['amount']
        
        if action == "pvreject":
            # Remove challenge
            del pvp_challenges[user_id]
            
            await callback_query.message.edit_text(
                f"❌ **ᴄʜᴀʟʟᴇɴɢᴇ ʀᴇᴊᴇᴄᴛᴇᴅ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"{callback_query.from_user.first_name} ʀᴇᴊᴇᴄᴛᴇᴅ {challenge['challenger_name']}'s ᴄʜᴀʟʟᴇɴɢᴇ."
            )
            await callback_query.answer("ᴄʜᴀʟʟᴇɴɢᴇ ʀᴇᴊᴇᴄᴛᴇᴅ!")
            return
        
        # Challenge accepted - remove it from pending
        del pvp_challenges[user_id]
        
        # Get both users' data
        challenger_data = await user_collection.find_one({'id': challenger_id})
        target_data = await user_collection.find_one({'id': user_id})
        
        # Check if both users still have enough gold
        challenger_gold = float(challenger_data.get('gold', 0)) if challenger_data else 0
        target_gold = float(target_data.get('gold', 0)) if target_data else 0
        
        if challenger_gold < amount or target_gold < amount:
            await callback_query.message.edit_text(
                f"⚠️ **ɴᴏᴛ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"ᴏɴᴇ ᴏʀ ʙᴏᴛʜ ᴜsᴇʀs ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ ғᴏʀ ᴛʜᴇ ʙᴇᴛ."
            )
            await callback_query.answer("ɴᴏᴛ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!")
            return
        
        # Deduct gold from both users
        await user_collection.update_one(
            {'id': challenger_id},
            {'$inc': {'gold': -amount}},
            upsert=True
        )
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'gold': -amount}},
            upsert=True
        )
        
        # Select random characters for both users
        challenger_char_id = random.choice(list(BLUE_LOCK_CHARACTERS.keys()))
        target_char_id = random.choice(list(BLUE_LOCK_CHARACTERS.keys()))
        
        challenger_char = BLUE_LOCK_CHARACTERS[challenger_char_id]
        target_char = BLUE_LOCK_CHARACTERS[target_char_id]
        
        # Update message to show characters
        await callback_query.message.edit_text(
            f"⚔️ **ʙʟᴜᴇ ʟᴏᴄᴋ ᴘᴠᴘ ʙᴀᴛᴛʟᴇ!**\n\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"✦ **{challenge['challenger_name']}:** {challenger_char['name']} {challenger_char['emoji']}\n"
            f"✦ **{callback_query.from_user.first_name}:** {target_char['name']} {target_char['emoji']}\n"
            f"✦ **ʙᴇᴛ ᴀᴍᴏᴜɴᴛ:** {humanize.intcomma(amount)} ₲\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"⚡ _ᴛʜᴇ ʙᴀᴛᴛʟᴇ ɪs sᴛᴀʀᴛɪɴɢ..._"
        )
        
        # Send character videos
        await callback_query.message.reply_video(
            challenger_char["start_video"],
            caption=f"⚡ **{challenge['challenger_name']}'s sᴛʀɪᴋᴇʀ:** {challenger_char['name']} {challenger_char['emoji']}\n✦ **{challenger_char['quote']}**"
        )
        
        await callback_query.message.reply_video(
            target_char["start_video"],
            caption=f"⚡ **{callback_query.from_user.first_name}'s sᴛʀɪᴋᴇʀ:** {target_char['name']} {target_char['emoji']}\n✦ **{target_char['quote']}**"
        )
        
        # Simulate battle with countdown
        battle_msg = await callback_query.message.reply_text(
            f"🥅 **ᴛʜᴇ ʙᴀᴛᴛʟᴇ ʙᴇɢɪɴs!**\n\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"✦ **{challenger_char['name']}** vs **{target_char['name']}**\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"⚡ _3..._"
        )
        
        for i in range(2, 0, -1):
            await asyncio.sleep(1)
            await battle_msg.edit_text(
                f"🥅 **ᴛʜᴇ ʙᴀᴛᴛʟᴇ ʙᴇɢɪɴs!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **{challenger_char['name']}** vs **{target_char['name']}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"⚡ _{i}..._"
            )
        
        await asyncio.sleep(1)
        
        # Determine winner (50/50 chance)
        challenger_wins = random.random() < 0.5
        
        if challenger_wins:
            winner_id = challenger_id
            winner_name = challenge['challenger_name']
            winner_char = challenger_char
            loser_id = user_id
            loser_name = callback_query.from_user.first_name
            loser_char = target_char
        else:
            winner_id = user_id
            winner_name = callback_query.from_user.first_name
            winner_char = target_char
            loser_id = challenger_id
            loser_name = challenge['challenger_name']
            loser_char = challenger_char
        
        # Calculate winnings (winner gets both bets)
        winnings = amount * 2
        
        # Update winner's gold
        await user_collection.update_one(
            {'id': winner_id},
            {'$inc': {'gold': winnings}},
            upsert=True
        )
        
        # Send battle result with videos
        await battle_msg.delete()
        
        # Send winner's video
        await callback_query.message.reply_video(
            winner_char["win_video"],
            caption=(
                f"🎉 **{winner_name}'s {winner_char['name']} {winner_char['emoji']} sᴄᴏʀᴇᴅ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ᴡɪɴɴᴇʀ:** {winner_name}\n"
                f"✦ **ᴡɪɴɴɪɴɢs:** {humanize.intcomma(winnings)} ₲\n"
                f"✦ **{random.choice(winner_char['win_quotes'])}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
            )
        )
        
        # Send loser's video
        await callback_query.message.reply_video(
            loser_char["lose_video"],
            caption=(
                f"❌ **{loser_name}'s {loser_char['name']} {loser_char['emoji']} ғᴀɪʟᴇᴅ ᴛᴏ sᴄᴏʀᴇ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ʟᴏsᴇʀ:** {loser_name}\n"
                f"✦ **ʟᴏss:** {humanize.intcomma(amount)} ₲\n"
                f"✦ **{random.choice(loser_char['lose_quotes'])}**\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
            )
        )
        
        # Send final battle result image
        await callback_query.message.reply_photo(
            photo="https://files.catbox.moe/y9di3c.jpg",  # Battle result image
            caption=(
                f"🏆 **ʙᴀᴛᴛʟᴇ ʀᴇsᴜʟᴛ!**\n\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
                f"✦ **ᴡɪɴɴᴇʀ:** {winner_name} ({winner_char['name']} {winner_char['emoji']})\n"
                f"✦ **ᴡɪɴɴɪɴɢs:** {humanize.intcomma(winnings)} ₲\n\n"
                f"✦ **ʟᴏsᴇʀ:** {loser_name} ({loser_char['name']} {loser_char['emoji']})\n"
                f"✦ **ʟᴏss:** {humanize.intcomma(amount)} ₲\n"
                f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"⚡ ᴛʜᴇ ᴇɢᴏ ʙᴀᴛᴛʟᴇ ʜᴀs ʙᴇᴇɴ sᴇᴛᴛʟᴇᴅ!"
            )
        )
        
        await callback_query.answer("ʙᴀᴛᴛʟᴇ ᴄᴏᴍᴘʟᴇᴛᴇ!")
        
    except Exception as e:
        print(f"Error in handle_pvp_response: {e}")
        await callback_query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!", show_alert=True)

# Add a command to show current character
@app.on_message(filters.command("mycharacter"))
async def show_character(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply_text("⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪғʏ ᴜsᴇʀ.")
        return
    
    if user.id not in user_characters:
        await message.reply_text(
            "⚠️ **ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ sᴇʟᴇᴄᴛᴇᴅ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ʏᴇᴛ!**\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            "ᴜsᴇ /startblue ᴛᴏ ᴄʜᴏᴏsᴇ ʏᴏᴜʀ sᴛʀɪᴋᴇʀ."
        )
        return
    
    character = BLUE_LOCK_CHARACTERS[user_characters[user.id]]
    
    await message.reply_photo(
        photo=character["image"],
        caption=(
            f"╭━━━━━━━━━━━━━━━━━━━━━╮\n"
            f"   **ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴛʀɪᴋᴇʀ**   \n"
            f"╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
            f"✦ **ɴᴀᴍᴇ:** {character['name']} {character['emoji']}\n"
            f"✦ **sɪɢɴᴀᴛᴜʀᴇ ǫᴜᴏᴛᴇ:** {character['quote']}\n"
            f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            f"ᴜsᴇ /blue ᴛᴏ sᴛᴀʀᴛ ᴀ ᴍᴀᴛᴄʜ\n"
            f"ᴏʀ /startblue ᴛᴏ ᴄʜᴀɴɢᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ"
        )
            )
