from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
from . import app, user_collection, capsify
from .profile import custom_format_number
from .block import block_dec, temp_block, block_cbq
import time

LEADERBOARD_LIMIT = 10
LEADERBOARD_BANNER_URL = "https://files.catbox.moe/nvu1v6.jpg"

# Cache for leaderboard data to make pagination faster
leaderboard_cache = {
    "gold": {"data": None, "timestamp": 0},
    "rubies": {"data": None, "timestamp": 0},
    "balance": {"data": None, "timestamp": 0}
}
CACHE_EXPIRY = 300  # 5 minutes

leaderboard_types = {
    "gold": "🏅 ɢᴏʟᴅ",
    "rubies": "💎 ʀᴜʙɪᴇꜱ",
    "balance": "💰 ʙᴀʟᴀɴᴄᴇ"
}

async def get_sorted_users(list_type):
    """Get sorted users with caching mechanism"""
    current_time = time.time()
    
    # Check if cache is valid
    if (leaderboard_cache[list_type]["data"] and 
        current_time - leaderboard_cache[list_type]["timestamp"] < CACHE_EXPIRY):
        return leaderboard_cache[list_type]["data"]
    
    # Fetch fresh data from database
    all_users = await user_collection.find({}, {
        "id": 1,
        "first_name": 1,
        list_type: 1
    }).to_list(length=None)
    
    # Sort and cache
    sorted_users = sorted(
        [u for u in all_users if u.get(list_type)],
        key=lambda x: float(str(x.get(list_type)).replace(",", "")),
        reverse=True
    )
    
    leaderboard_cache[list_type]["data"] = sorted_users
    leaderboard_cache[list_type]["timestamp"] = current_time
    return sorted_users

@app.on_message(filters.command("tops"))
@block_dec
async def show_top_menu(client, message):
    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return
    
    await message.reply_photo(
        photo=LEADERBOARD_BANNER_URL,
        caption=capsify("🏆 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ɢʟᴏʙᴀʟ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ 🏆\n\nꜱᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ ʙᴇʟᴏᴡ:"),
        reply_markup=IKM([
            [IKB(capsify("🏅 ᴛᴏᴘ ɢᴏʟᴅ"), callback_data="top_gold_1"),
             IKB(capsify("💎 ᴛᴏᴘ ʀᴜʙɪᴇꜱ"), callback_data="top_rubies_1")],
            [IKB(capsify("💰 ᴛᴏᴘ ʙᴀʟᴀɴᴄᴇ"), callback_data="top_balance_1")]
        ])
    )

@app.on_callback_query(filters.regex(r"^top_(gold|rubies|balance)_(\d+)$"))
async def show_top_list(client, cq):
    list_type, page = cq.data.split("_")[1], int(cq.data.split("_")[2])
    
    # Get sorted users (from cache if available)
    sorted_users = await get_sorted_users(list_type)
    total = len(sorted_users)
    
    # Calculate pagination
    start, end = (page - 1) * LEADERBOARD_LIMIT, page * LEADERBOARD_LIMIT
    displayed = sorted_users[start:end]
    
    # Build message
    title = leaderboard_types.get(list_type, "🏆 ᴛᴏᴘ")
    msg = f"{capsify(title)}\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for idx, user in enumerate(displayed, start=start + 1):
        medal = medals[idx - start - 1] if idx - start <= 3 else f"`#{idx}`"
        value = float(str(user.get(list_type)).replace(",", ""))
        pretty = custom_format_number(value)
        mention = f"[{user.get('first_name', 'ᴜɴᴋɴᴏᴡɴ')}]({'tg://user?id=' + str(user['id'])})"
        msg += f"{medal} {mention} ─ `{pretty}`\n"
    
    # Build buttons
    buttons = []
    if page > 1:
        buttons.append(IKB("⬅️ ᴘʀᴇᴠ", callback_data=f"top_{list_type}_{page - 1}"))
    if end < total:
        buttons.append(IKB("ɴᴇxᴛ ➡️", callback_data=f"top_{list_type}_{page + 1}"))
    
    # Add fast navigation buttons (for jumping multiple pages)
    if total > LEADERBOARD_LIMIT * 3:
        if page > 1:
            buttons.append(IKB("⏪", callback_data=f"top_{list_type}_{max(1, page - 5)}"))
        if end < total:
            buttons.append(IKB("⏩", callback_data=f"top_{list_type}_{min((total // LEADERBOARD_LIMIT) + 1, page + 5)}"))
    
    # Edit message
    try:
        await cq.message.edit_caption(
            caption=msg,
            reply_markup=IKM([
                buttons if buttons else [],
                [IKB("🔙 ʙᴀᴄᴋ", callback_data="back_to_menu")]
            ])
        )
    except:
        await cq.answer("No changes made.", show_alert=False)

@app.on_callback_query(filters.regex("back_to_menu"))
@block_cbq
async def back_to_menu(client, cq):
    await cq.message.edit_caption(
        caption=capsify("🏆 ᴡᴇʟᴄᴏᴍᴇ ʙᴀᴄᴋ ᴛᴏ ᴛʜᴇ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ ᴍᴇɴᴜ 🏆\n\nᴘɪᴄᴋ ᴀ ᴄᴀᴛᴇɢᴏʀʏ ʙᴇʟᴏᴡ:"),
        reply_markup=IKM([
            [IKB(capsify("🏅 ᴛᴏᴘ ɢᴏʟᴅ"), callback_data="top_gold_1"),
             IKB(capsify("💎 ᴛᴏᴘ ʀᴜʙɪᴇꜱ"), callback_data="top_rubies_1")],
            [IKB(capsify("💰 ᴛᴏᴘ ʙᴀʟᴀɴᴄᴇ"), callback_data="top_balance_1")]
        ])
    )
