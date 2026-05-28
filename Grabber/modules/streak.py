from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta
from . import Grabberu as app, user_collection

# Daily Streak Command
@app.on_message(filters.command("streak"))
async def daily_streak(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'streak': 1, 'last_claimed': 1, 'balance': 1})
    
    # Default values
    streak = user_data.get('streak', 0)
    last_claimed = user_data.get('last_claimed', None)
    balance = int(user_data.get('balance', 0))  # Convert balance to integer
    
    today = datetime.utcnow().date()

    if last_claimed:
        last_claimed_date = datetime.strptime(last_claimed, "%Y-%m-%d").date()
        if last_claimed_date == today:
            return await message.reply_text("⚠️ You have already claimed today's streak reward!")
        elif last_claimed_date < today - timedelta(days=1):
            streak = 0  # Streak resets if a day is missed

    # Increase streak
    streak += 1
    base_reward = 100  # Base reward for first streak
    streak_bonus = (streak * 20)  # Reward increases with streak count
    reward = base_reward + streak_bonus

    # Extra bonuses at milestones
    if streak in [3, 7, 14, 30]:
        reward += 500  # Extra coins for milestones

    # Update user data
    new_balance = balance + reward
    await user_collection.update_one(
        {'id': user_id},
        {"$set": {"streak": streak, "last_claimed": today.strftime("%Y-%m-%d"), "balance": new_balance}}
    )

    # Reply with streak status
    streak_message = (
        "🔥 **Daily Streak Reward** 🔥\n\n"
        f"🌟 Streak: `{streak} days`\n"
        f"💰 Reward: `{reward:,} coins`\n"
        f"📊 Total Balance: `{new_balance:,} coins`\n"
    )

    if streak in [3, 7, 14, 30]:
        streak_message += f"\n🎉 **Bonus Milestone Reached!** `{streak} Days Streak` 🎁"

    await message.reply_text(streak_message)
