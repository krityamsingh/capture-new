import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import app  # Importing from main bot file

# ✅ IDs
SUPPORT_GROUP_ID = -1002313549356  # Your Support Group ID
SUGGEST_CHANNEL_ID = -1003430763556  # Your Suggestion Channel ID

# ⏳ Cooldown Dictionary
suggestion_cooldown = {}

# 📌 Suggest Command
@app.on_message(filters.command("suggest") & filters.reply)
async def suggest_character(bot, message: Message):
    user_id = message.from_user.id

    if message.chat.id != SUPPORT_GROUP_ID:  
        return await message.reply("❌ This command can only be used in the support group!")  

    if not (message.reply_to_message.photo or message.reply_to_message.video):  
        return await message.reply("❌ Please reply to an **image or video** to suggest a character!")  

    # Cooldown Check (30 sec)
    if user_id in suggestion_cooldown:  
        remaining_time = round(30 - (asyncio.get_event_loop().time() - suggestion_cooldown[user_id]))  
        if remaining_time > 0:  
            return await message.reply(f"⏳ Please wait **{remaining_time} seconds** before suggesting again!")  

    # 📝 Description Handling  
    description = message.text.replace("/suggest", "").strip() or "No description"  

    # 🔹 User Mention  
    user_mention = message.from_user.mention(style="md")  

    # ✅ Send Suggestion Directly
    if message.reply_to_message.photo:
        sent_suggestion = await bot.send_photo(
            SUGGEST_CHANNEL_ID,
            photo=message.reply_to_message.photo.file_id,
            caption=f"**New Suggestion!**\n\n🔹 **Suggested by:** {user_mention}\n🔹 **Description:** {description}"
        )
    elif message.reply_to_message.video:
        sent_suggestion = await bot.send_video(
            SUGGEST_CHANNEL_ID,
            video=message.reply_to_message.video.file_id,
            caption=f"**New Suggestion!**\n\n🔹 **Suggested by:** {user_mention}\n🔹 **Description:** {description}"
        )

    # 🔔 Notify User with View Button
    await message.reply(
        "✅ **Your character suggestion has been sent successfully!**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 View Character", url=f"https://t.me/c/{str(SUGGEST_CHANNEL_ID)[4:]}/{sent_suggestion.id}")]
        ])
    )

    # ⏳ Store Cooldown Time
    suggestion_cooldown[user_id] = asyncio.get_event_loop().time()
