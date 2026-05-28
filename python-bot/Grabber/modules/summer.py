from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton
from asyncio import sleep, Lock
from . import app, collection, user_collection, ac

# Owner ID for resetting limits
OWNER_IDS = [6228788487, 8496760733, 7861332030]

# Support group and channel IDs
SUPPORT_GROUP_ID = -1002313549356
SUPPORT_CHANNEL_ID = -1003869604435
SUPPORT_GROUP_LINK = "Divine_Catchers"
SUPPORT_CHANNEL_LINK = "IndianHelpIine"

# Create a lock to prevent concurrent reward claims
reward_lock = Lock()

# Reset reward limits command (owner only)
@app.on_message(filters.command("rrlimit") & filters.user(OWNER_IDS))
async def reset_reward_limits(client: Client, message: Message):
    # Reset all users' reward_claimed status
    await user_collection.update_many(
        {},
        {"$set": {"reward_claimed": False}}
    )
    await message.reply_text("✅ All users' reward limits have been reset!")

# Reward Command
@app.on_message(filters.command("reward"))
async def reward_character(client: Client, message: Message):
    # Check if in support group
    if message.chat.id != SUPPORT_GROUP_ID:
        join_button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Join Support Group", url=f"t.me/{SUPPORT_GROUP_LINK}")]]
        )
        return await message.reply_text(
            "⚠️ This command can only be used in our support group!",
            reply_markup=join_button
        )

    user_id = message.from_user.id
    user_tag = message.from_user.mention

    # Use a lock to prevent concurrent processing
    async with reward_lock:
        # Check if user already claimed reward
        user_data = await user_collection.find_one({"user_id": user_id})
        if user_data and user_data.get("reward_claimed"):
            return await message.reply_text(
                f"🎁 You've already claimed your special reward, {user_tag}!\n\n"
                f"Only one reward per user is allowed!"
            )

        # Mark as claimed immediately to prevent concurrent claims
        await user_collection.update_one(
            {"user_id": user_id},
            {"$set": {"reward_claimed": True}},
            upsert=True
        )

        # Send reward sticker
        sticker_message = await message.reply_sticker("CAACAgIAAyEFAASBaLQkAAEKEP9ol3VdTO_q2ptVwV1Xi5PUgfDOUAACNF0AAnNF2Emgpq9l1WqU6TYE")

        try:
            # Get random Animation rarity character
            pipeline = [
                {"$match": {"rarity": "⚜️ Animated"}},
                {"$sample": {"size": 1}}
            ]
            chars = await collection.aggregate(pipeline).to_list(1)
            if not chars:
                # If no characters available, reset the claim status
                await user_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"reward_claimed": False}}
                )
                await sticker_message.delete()
                return await message.reply_text("⚠️ No 🧬 Animation characters available currently. Contact admin!")

            char = chars[0]

            # Add character to user's collection
            await ac(user_id, char["id"])

            caption = (
                f"🌸 **ʏᴏᴜ'ʀᴇ ʙᴀᴄᴋ, ʏᴀᴛᴛᴀ~!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ **ᴄʜᴀʀᴀᴄᴛᴇʀ:** `{char['name']}`\n"
                f"⛩️ **ᴀɴɪᴍᴇ:** `{char['anime']}`\n"
                f"☁️ **ʀᴀʀɪᴛʏ:** `{char['rarity']}`\n"
                f"🕊️ **ᴄʟᴀɪᴍᴇᴅ ʙʏ:** {user_tag}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if char.get("video_url"):
                media = InputMediaVideo(char["video_url"], caption=caption)
            else:
                media = InputMediaPhoto(char["img_url"], caption=caption)
                
            await message.reply_media_group([media])
            await sticker_message.delete()

        except Exception as e:
            print(f"Error in reward command: {e}")
            # If an error occurs, reset the claim status
            await user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"reward_claimed": False}}
            )
            await message.reply_text("⚠️ An unexpected error occurred. Please try again later.")
            try:
                await sticker_message.delete()
            except:
                pass
