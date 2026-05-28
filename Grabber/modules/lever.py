from pyrogram import filters, types as t
import random
import time
import asyncio
from pyrogram import Client
from Grabber import user_collection
from . import add, deduct, show, app
from .block import block_dec, temp_block

cooldown_duration = 600
last_usage_time = {}

SLOT_ICONS = ["🍒", "🍇", "🔔", "⭐", "💎", "🎰"]  # Slot machine symbols

@app.on_message(filters.command(["lever"]))
@block_dec
async def slot_machine(client: Client, message: t.Message):
    user_id = message.from_user.id
    if temp_block(user_id):
        return

    current_time = time.time()

    if not await user_collection.find_one({'id': user_id}):
        await message.reply(
            "🎰 **Welcome to the Ultimate Slot Machine!**\n\n"
            "⚠️ You need to own a character to play!\n"
            "✨ Use `/grab` to get started and join the fun!"
        )
        return

    command_parts = message.text.split()
    if len(command_parts) != 2:
        return await message.reply_text(
            "❌ **Invalid Command Format!**\n\n"
            "🎯 **Usage:** `/lever <bet amount>`\n"
            "📌 Example: `/lever 1000`"
        )

    try:
        bet_amount = int(command_parts[1])
    except ValueError:
        return await message.reply_text(
            "❌ **Invalid Bet Amount!**\n\n"
            "💰 Please enter a numeric value for your bet.\n"
            "📌 Example: `/lever 500`"
        )

    balance = await show(user_id)
    if balance is None:
        return await message.reply_text(
            "💸 **You're out of cash!**\n\n"
            "💡 Earn more before trying your luck at the slots!"
        )

    if bet_amount > balance:
        return await message.reply_text(
            f"❌ **Not Enough Funds!**\n\n"
            f"🪙 Your current balance: **₳{balance}**\n"
            f"📉 Bet amount: **₳{bet_amount}**\n"
            "💡 You can't bet more than you have!"
        )

    min_bet = int(balance * 0.07)
    max_bet = int(balance * 0.4)
    
    if bet_amount < min_bet:
        return await message.reply_text(
            f"⚠️ **Minimum Bet Required!**\n\n"
            f"💰 You must bet **at least 7%** of your balance.\n"
            f"📌 Minimum allowed: **₳{min_bet}**"
        )

    if bet_amount > max_bet:
        return await message.reply_text(
            f"🚨 **Maximum Bet Limit!**\n\n"
            f"📈 You can't bet more than **40%** of your balance.\n"
            f"📌 Maximum allowed: **₳{max_bet}**"
        )

    if user_id in last_usage_time:
        elapsed_time = current_time - last_usage_time[user_id]
        remaining_time = max(0, cooldown_duration - elapsed_time)
        if remaining_time > 0:
            return await message.reply_text(
                f"⏳ **Hold On!**\n\n"
                f"🎰 You can play again in **{int(remaining_time)} seconds**.\n"
                "💡 Patience pays off – maybe luck will be on your side next round!"
            )

    last_usage_time[user_id] = current_time

    # 🎰 Slot Machine Simulation
    slot_result = await client.send_dice(chat_id=message.chat.id, emoji="🎰")
    await asyncio.sleep(random.uniform(1, 4))  # Random suspense effect
    slot_value = slot_result.dice.value

    # Slot-based winning mechanics
    jackpot_multiplier = 3  # Triple winnings for jackpot
    double_match_multiplier = 1.5  # 1.5x for two matched symbols

    # Random slot icons for the visual effect
    slots_display = [random.choice(SLOT_ICONS) for _ in range(3)]
    slots_str = f"{slots_display[0]} | {slots_display[1]} | {slots_display[2]}"

    if slot_value == 1:  # 🎰 Jackpot Win
        winnings = jackpot_multiplier * bet_amount
        await add(user_id, winnings)
        await message.reply_text(
            f"🎉 **JACKPOT WINNER!** 🎉\n\n"
            f"🎰 **{slots_str}** 🎰\n"
            f"🔥 You hit the jackpot and won **₳{winnings}**!\n"
            "💎 You're the luckiest player today!"
        )
        await add_xp(user_id, 10)

    elif slot_value == 2:  # ⭐⭐ Two Matches - Small Win
        winnings = int(double_match_multiplier * bet_amount)
        await add(user_id, winnings)
        await message.reply_text(
            f"✨ **Nice Spin!** ✨\n\n"
            f"🎰 **{slots_str}** 🎰\n"
            f"🔔 You matched **two symbols** and won **₳{winnings}**!\n"
            "💪 Keep going, maybe the jackpot is next!"
        )
        await add_xp(user_id, 5)

    elif slot_value == 3:  # 🍒🍇🔔 - Almost There!
        await deduct(user_id, bet_amount)
        await message.reply_text(
            f"💔 **So Close!** 💔\n\n"
            f"🎰 **{slots_str}** 🎰\n"
            f"🔹 You lost **₳{bet_amount}**.\n"
            "😢 Better luck next time!"
        )
        await deduct_xp(user_id, 3)

    else:  # 🎲 Random Loss
        await deduct(user_id, bet_amount)
        await message.reply_text(
            f"😞 **Better Luck Next Time!** 😞\n\n"
            f"🎰 **{slots_str}** 🎰\n"
            f"💔 You lost **₳{bet_amount}**.\n"
            "🎯 Keep spinning – your luck might turn soon!"
        )
        await deduct_xp(user_id, 2)

async def add_xp(user_id, xp_amount):
    await user_collection.update_one({'id': user_id}, {'$inc': {'xp': xp_amount}}, upsert=True)

async def deduct_xp(user_id, xp_amount):
    await user_collection.update_one({'id': user_id}, {'$inc': {'xp': -xp_amount}}, upsert=True)
