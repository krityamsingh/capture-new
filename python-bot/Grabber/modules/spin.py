import random
import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from . import Grabberu as app, user_collection

SPIN_COOLDOWN = 60 * 60  # 60 minutes

SPIN_ANIMATIONS = [
    "🔁 Spinning the wheel...",
    "🎯 Aiming for the jackpot...",
    "🎡 Wheel is spinning fast...",
    "✨ Feeling lucky today...",
    "⏳ Hold on tight...",
]

REWARD_TIERS = {
    "🥉 Minor Win": random.randint(100, 300),
    "🥈 Decent Win": random.randint(400, 1000),
    "🥇 Big Win": random.randint(1200, 3000),
    "💎 JACKPOT": random.randint(5000, 15000),
}

PRIZE_WEIGHTS = (
    ["🥉 Minor Win"] * 45 +
    ["🥈 Decent Win"] * 30 +
    ["🥇 Big Win"] * 20 +
    ["💎 JACKPOT"] * 5
)

@app.on_message(filters.command("spin"))
async def spin_command(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    name = user.first_name

    # Fetch or create user
    user_data = await user_collection.find_one({"id": user_id})
    now = datetime.datetime.utcnow()

    if not user_data:
        await user_collection.insert_one({
            "id": user_id,
            "balance": 5000,
            "last_spin": None
        })
        return await message.reply(
            caption=f"✨ **Welcome {name}** ✨\nYou got your **first free spin!**\nUse `/spin` again now!"
        )

    last_spin = user_data.get("last_spin")
    if last_spin:
        try:
            last_spin = datetime.datetime.strptime(last_spin, "%Y-%m-%d %H:%M:%S")
        except:
            last_spin = None

    # Cooldown handling
    if last_spin and (now - last_spin).total_seconds() < SPIN_COOLDOWN:
        remaining = int(SPIN_COOLDOWN - (now - last_spin).total_seconds())
        mins, secs = divmod(remaining, 60)
        return await message.reply_text(
            f"⏳ **Cooldown Active!**\nTry again in **{mins}m {secs}s**."
        )

    # Send spin animation
    animation_msg = await message.reply_text(random.choice(SPIN_ANIMATIONS))

    # Determine reward
    prize = random.choice(PRIZE_WEIGHTS)
    amount = REWARD_TIERS[prize]
    new_balance = user_data["balance"] + amount

    # Update user info
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "last_spin": now.strftime("%Y-%m-%d %H:%M:%S")}}
    )

    await animation_msg.delete()

    # Result Message
    result_text = (
        f"🎉 **{name}'s Lucky Spin Result!** 🎉\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏅 **Prize Tier:** `{prize}`\n"
        f"💰 **Coins Won:** `{amount}`\n"
        f"🏦 **Total Balance:** `{new_balance}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Come back in 1 hour for another spin!"
    )

    await message.reply_text(result_text)
