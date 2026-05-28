from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
from . import app, db, user_collection, add
from .block import block_dec, temp_block, block_cbq
import time

bonus_db = db.bonus

# Config
DAILY_BONUS = 75000
WEEKLY_BONUS = 850000
BONUS_IMAGE = "https://files.catbox.moe/td95xk.jpg"

def get_next_day():
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

def get_next_week():
    today = datetime.now()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    return next_monday.replace(hour=0, minute=0, second=0, microsecond=0)

def parse_datetime(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value

async def get_bonus_status(user_id):
    record = await bonus_db.find_one({"user_id": user_id})
    bonus = record.get("bonus", {"daily": None, "weekly": None}) if record else {"daily": None, "weekly": None}
    bonus["daily"] = parse_datetime(bonus.get("daily"))
    bonus["weekly"] = parse_datetime(bonus.get("weekly"))
    return bonus

async def update_bonus_status(user_id, bonus_type):
    bonus_status = await get_bonus_status(user_id)
    if bonus_type == "daily":
        bonus_status["daily"] = get_next_day().isoformat()
    elif bonus_type == "weekly":
        bonus_status["weekly"] = get_next_week().isoformat()
    await bonus_db.update_one(
        {"user_id": user_id},
        {"$set": {"bonus": bonus_status}},
        upsert=True
    )

@app.on_message(filters.command("bonus"))
@block_dec
async def bonus_handler(_, message):
    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    today = datetime.now()
    bonus_status = await get_bonus_status(user_id)

    daily_status = "❖ ᴄʟᴀɪᴍᴇᴅ ✓" if bonus_status["daily"] and bonus_status["daily"] > today else "⚘ ᴅᴀɪʟʏ ʙᴏɴᴜs ~"
    weekly_status = "❖ ᴄʟᴀɪᴍᴇᴅ ✓" if bonus_status["weekly"] and bonus_status["weekly"] > today else "● ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs ✨"

    caption = f"""
**⋆✧˚₊‧ ʜᴇʏᴀ {message.from_user.first_name}-ᴄʜᴀɴ! ‧₊˚✧⋆**

━━━━━━━━━━━━━━━━
⚡ **ᴛᴏᴅᴀʏ's ᴅᴀᴛᴇ:** `{today.strftime('%A, %d %B %Y')}`
🌸 **ᴡᴇᴇᴋ ɴᴜᴍʙᴇʀ:** `#{today.strftime('%U')}`
━━━━━━━━━━━━━━━━

✧･ﾟ: *✧･ﾟ:* ʏᴏᴜʀ ʙᴏɴᴜs ʀᴇᴡᴀʀᴅs ᴀᴡᴀɪᴛ! *:･ﾟ✧*:･ﾟ✧

ᴘʟᴇᴀsᴇ ᴄʜᴏᴏsᴇ ғʀᴏᴍ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴄʟᴀɪᴍ ʏᴏᴜʀ ʀᴇᴡᴀʀᴅs~
"""

    markup = IKM([
        [IKB(f" {daily_status} ", callback_data=f"bonus_daily_{user_id}")],
        [IKB(f" {weekly_status} ", callback_data=f"bonus_weekly_{user_id}")],
        [IKB("✧･ﾟ: ᴄʟᴏsᴇ ᴍᴇɴᴜ ✧･ﾟ", callback_data=f"bo_close_{user_id}")]
    ])

    try:
        await message.reply_photo(BONUS_IMAGE, caption=caption, reply_markup=markup)
    except:
        await message.reply_text(caption, reply_markup=markup)

@app.on_callback_query(filters.regex(r"^bonus_"))
@block_cbq
async def bonus_claim_handler(_, query):
    _, bonus_type, user_id = query.data.split("_")
    user_id = int(user_id)

    if user_id != query.from_user.id:
        return await query.answer("✧･ﾟ: ɴᴏᴏᴏ! ᴛʜɪs ɪsɴ'ᴛ ʏᴏᴜʀ ʙᴏɴᴜs! :･ﾟ✧", show_alert=True)

    today = datetime.now()
    bonus_status = await get_bonus_status(user_id)

    if bonus_type == "daily":
        if bonus_status["daily"] and bonus_status["daily"] > today:
            return await query.answer("⚘ ᴀʀᴇɴ'ᴛ ʏᴏᴜ ᴇᴀɢᴇʀ~ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ɢᴏᴛ ᴛᴏᴅᴀʏ's ʙᴏɴᴜs!", show_alert=True)
        await add(user_id, DAILY_BONUS)
        await update_bonus_status(user_id, "daily")
        await query.answer(f"⋆✧˚₊‧ ʏᴀʏ! {DAILY_BONUS:,} ᴄᴏɪɴs ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴡᴀʟʟᴇᴛ! ‧₊˚✧⋆", show_alert=True)

    elif bonus_type == "weekly":
        if bonus_status["weekly"] and bonus_status["weekly"] > today:
            return await query.answer("● sᴜɢᴏɪ! ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ ᴛʜɪs ᴡᴇᴇᴋ's ʙᴏɴᴜs!", show_alert=True)
        await add(user_id, WEEKLY_BONUS)
        await update_bonus_status(user_id, "weekly")
        await query.answer(f"✧･ﾟ: {WEEKLY_BONUS:,} ᴄᴏɪɴs ʙʟᴇssɪɴɢs ғᴏʀ ʏᴏᴜ! ヽ(>∀<☆)ノ :･ﾟ✧", show_alert=True)

    updated_status = await get_bonus_status(user_id)
    daily_status = "❖ ᴄʟᴀɪᴍᴇᴅ ✓" if updated_status["daily"] and updated_status["daily"] > today else "⚘ ᴅᴀɪʟʏ ʙᴏɴᴜs ~"
    weekly_status = "❖ ᴄʟᴀɪᴍᴇᴅ ✓" if updated_status["weekly"] and updated_status["weekly"] > today else "● ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs ✨"

    caption = f"""
**⋆✧˚₊‧ ʜᴇʏᴀ {query.from_user.first_name}-ᴄʜᴀɴ! ‧₊˚✧⋆**

━━━━━━━━━━━━━━━━
⚡ **ᴛᴏᴅᴀʏ's ᴅᴀᴛᴇ:** `{today.strftime('%A, %d %B %Y')}`
🌸 **ᴡᴇᴇᴋ ɴᴜᴍʙᴇʀ:** `#{today.strftime('%U')}`
━━━━━━━━━━━━━━━━

✧･ﾟ: *✧･ﾟ:* ʙᴏɴᴜs sᴛᴀᴛᴜs ᴜᴘᴅᴀᴛᴇᴅ! *:･ﾟ✧*:･ﾟ✧
"""

    markup = IKM([
        [IKB(f" {daily_status} ", callback_data=f"bonus_daily_{user_id}")],
        [IKB(f" {weekly_status} ", callback_data=f"bonus_weekly_{user_id}")],
        [IKB("✧･ﾟ: ᴄʟᴏsᴇ ᴍᴇɴᴜ ✧･ﾟ", callback_data=f"bo_close_{user_id}")]
    ])

    try:
        await query.edit_message_caption(caption, reply_markup=markup)
    except:
        try:
            await query.edit_message_text(caption, reply_markup=markup)
        except:
            pass

@app.on_callback_query(filters.regex(r"^bo_close_"))
@block_cbq
async def close_bonus_handler(_, query):
    try:
        _, _, user_id = query.data.split("_")
        user_id = int(user_id)
    except ValueError:
        return

    if user_id != query.from_user.id:
        return await query.answer("✧･ﾟ: sᴏʀʀʏ ᴏɴɪɪ-ᴄʜᴀɴ! ɴᴏᴛ ʏᴏᴜʀ ᴍᴇɴᴜ! :･ﾟ✧", show_alert=True)

    await query.message.delete()
    await query.answer("⋆✧˚₊‧ ʙᴏɴᴜs ᴍᴇɴᴜ ᴄʟᴏsᴇᴅ! ᴍᴀᴛᴀ ɴᴇ~ ‧₊˚✧⋆")
