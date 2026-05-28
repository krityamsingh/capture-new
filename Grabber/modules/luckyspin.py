import random
from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
from . import Grabberu as app, user_collection, check_vip_status

# Define possible rewards
SPIN_REWARDS = [
    {"type": "coins", "amount": 500, "message": "🎉 You won **500 Coins**!"},
    {"type": "coins", "amount": 1000, "message": "💰 You hit the jackpot! **1,000 Coins**!"},
    {"type": "coins", "amount": 200, "message": "⭐ You won **200 Coins**!"},
    {"type": "item", "name": "Golden Ticket", "message": "🎫 You won a **Golden Ticket**!"},
    {"type": "item", "name": "Mystery Box", "message": "📦 You found a **Mystery Box**!"},
    {"type": "nothing", "message": "😢 Oh no! You didn't win anything this time."}
]

@app.on_message(filters.command("luckyspin"))
async def lucky_spin(client: Client, message: Message):
    user_id = message.from_user.id
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Check last spin date
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_spin': 1})
    last_spin = user_data.get("last_spin", None)

    if last_spin == today:
        # Check if user is VIP for extra spin
        is_vip = await check_vip_status(user_id)
        if not is_vip:
            return await message.reply_text("⚠️ **You've already used your daily spin!**\n(VIP users get an extra spin!)")
    
    # Select a random reward
    reward = random.choice(SPIN_REWARDS)

    # Update spin history
    await user_collection.update_one({'id': user_id}, {"$set": {"last_spin": today}})
    
    if reward["type"] == "coins":
        await user_collection.update_one({'id': user_id}, {"$inc": {"balance": reward["amount"]}})
    
    elif reward["type"] == "item":
        await user_collection.update_one({'id': user_id}, {"$push": {"inventory": reward["name"]}})
    
    await message.reply_text(f"🎡 **Spinning the Lucky Wheel...**\n⏳")
    await message.reply_text(reward["message"])
