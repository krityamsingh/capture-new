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

    user_tag = message.from_user.mention

    # Redirect to WebApp for rewards
    from pyrogram.types import WebAppInfo
    webapp_url = "https://captrue-miniapp.vercel.app" 
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Claim Reward via WebApp", web_app=WebAppInfo(url=webapp_url))]
    ])
    
    await message.reply_text(
        f"🎁 **Reward Time, {user_tag}!**\n\nClick the button below to open the WebApp, watch an ad, and claim your special reward!",
        reply_markup=keyboard
    )
