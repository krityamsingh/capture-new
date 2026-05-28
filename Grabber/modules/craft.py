from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Message, CallbackQuery
)
from datetime import datetime, timedelta
from . import app, collection, user_collection, ac  # Use your correct import path

DAILY_IMAGE = "https://files.catbox.moe/gdbqe9.jpg"
SUFFIX = "あ"
TOKENS_REWARD = 10000
RARITY_WHITELIST = ["🟡 Legendary", "💮 Mythic", "🔮 Limited Edition", "🟣 Epic"]
COOLDOWN_HOURS = 24

# ✨ /craft Command
@app.on_message(filters.command("craft"))
async def craft_command(client: Client, message: Message):
    user = message.from_user
    name_with_suffix = f"{user.first_name} {SUFFIX}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Change Name", url="tg://settings/editprofile")],
        [InlineKeyboardButton("🎁 Claim Reward", callback_data=f"claim_daily_{user.id}")]
    ])

    text = (
        f"🍁 **ᴅᴀɪʟʏ ʀᴇᴇɴ ᴄʀᴀғᴛ ʀᴇᴡᴀʀᴅ** 🍁\n\n"
        f"ʜᴇʏ {user.mention}, ʀᴇᴀᴅʏ ᴛᴏ ᴄʟᴀɪᴍ ʏᴏᴜʀ ғʀᴇᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀɴᴅ `{TOKENS_REWARD}` ᴛᴏᴋᴇɴs?\n\n"
        f"➤ ᴛᴏ ʙᴇ ᴇʟɪɢɪʙʟᴇ, ʏᴏᴜ **ᴍᴜsᴛ** ᴀᴅᴅ `{SUFFIX}` ᴀᴛ ᴛʜᴇ ᴇɴᴅ ᴏғ ʏᴏᴜʀ ɴᴀᴍᴇ.\n"
        f"➤ ᴜsᴇ ᴛʜᴇ **Change Name** ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴇᴅɪᴛ ʏᴏᴜʀ ɴᴀᴍᴇ.\n\n"
        f"🔗 𝐂𝐨𝐩𝐲 𝐓𝐡𝐢𝐬:\n`{name_with_suffix}`\n\n"
        f"⏳ ᴏɴᴄᴇ ᴅᴏɴᴇ, ᴄʟɪᴄᴋ **ᴄʟᴀɪᴍ ʀᴇᴡᴀʀᴅ** ᴛᴏ ᴜɴʟᴏᴄᴋ ʏᴏᴜʀ ɢɪғᴛ!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *ʀᴇᴇɴ ᴡᴀʀʀɪᴏʀs ɴᴇᴠᴇʀ sᴛᴏᴘ!* ✨"
    )

    await message.reply_photo(DAILY_IMAGE, caption=text, reply_markup=keyboard)

# 🎁 Claim Callback
@app.on_callback_query(filters.regex(r"^claim_daily_(\d+)$"))
async def claim_daily_reward(client: Client, query: CallbackQuery):
    user = query.from_user
    user_id = int(query.matches[0].group(1))
    now = datetime.utcnow()

    if user.id != user_id:
        return await query.answer("❌ This isn’t your reward to claim!", show_alert=True)

    if SUFFIX not in user.first_name + (user.last_name or ""):
        return await query.answer("⚠️ You must add the suffix あ to your name first!", show_alert=True)

    user_data = await user_collection.find_one({"user_id": user.id})
    last_claim = user_data.get("last_claim") if user_data else None
    if last_claim:
        last_claim_time = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
        if now - last_claim_time < timedelta(hours=COOLDOWN_HOURS):
            remaining = timedelta(hours=COOLDOWN_HOURS) - (now - last_claim_time)
            hours, minutes = divmod(remaining.seconds // 60, 60)
            return await query.answer(
                f"⏳ Wait {remaining.days}d {hours}h {minutes}m before claiming again!",
                show_alert=True
            )

    await query.message.delete()

    char = await collection.aggregate([
        {"$match": {"rarity": {"$in": RARITY_WHITELIST}}},
        {"$sample": {"size": 1}}
    ]).to_list(1)

    if not char:
        return await client.send_message(query.message.chat.id, "❌ No eligible characters found for now.")

    char = char[0]
    await ac(user.id, char['id'])

    await user_collection.update_one(
        {"user_id": user.id},
        {"$set": {"last_claim": now.strftime("%Y-%m-%d %H:%M:%S")}, "$inc": {"tokens": TOKENS_REWARD}},
        upsert=True
    )

    caption = (
        f"🎉 **ᴅᴀɪʟʏ ᴄʟᴀɪᴍ sᴜᴄᴄᴇssғᴜʟ!** 🎉\n\n"
        f"🏷️ **Name:** `{char['name']}`\n"
        f"🧬 **Anime:** `{char['anime']}`\n"
        f"✨ **Rarity:** {char['rarity']}\n"
        f"🎈 **Bonus Tokens:** `{TOKENS_REWARD}`\n\n"
        f"⚔️ ᴋᴇᴇᴘ ғɪɢʜᴛɪɴɢ, {user.mention}!"
    )

    if char.get("rarity") == "🧬 Animation" and char.get("video_url"):
        await client.send_video(query.message.chat.id, char['video_url'], caption=caption)
    else:
        await client.send_photo(query.message.chat.id, char['img_url'], caption=caption)
