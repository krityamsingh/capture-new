from pyrogram import Client, filters
from pyrogram.types import Message
from . import app, user_collection
import random
import humanize

# Constants
CONVERSION_RATE = 100000  # 100,000 coins = 1 gold
MIN_CONVERSION = 100000   # Minimum required

# Emoji sets
GOLD_EMOJIS = ["👑", "💰", "💎", "🌟", "✨", "💫"]
COIN_EMOJIS = ["🪙", "🟡", "🔸", "¢", "₵", "ⓒ"]

def get_random_emoji(emoji_list):
    return random.choice(emoji_list)

@app.on_message(filters.command("convert"))
async def convert_coins(client: Client, message: Message):
    user = message.from_user
    if not user:
        await message.reply("❌ Unable to identify you.")
        return

    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                f"🔁 **Convert Coins to Gold**\n\n"
                f"**Usage:** `/convert <amount>`\n"
                f"🔸 Minimum: `{humanize.intcomma(MIN_CONVERSION)}` coins"
            )
            return

        amount_str = args[1].replace(',', '').strip()
        if not amount_str.isdigit():
            await message.reply("❌ Please enter a valid number.")
            return

        amount = int(amount_str)

        if amount < MIN_CONVERSION:
            await message.reply(
                f"❗ Minimum amount to convert is `{humanize.intcomma(MIN_CONVERSION)}` coins.\n"
                f"💡 You entered: `{humanize.intcomma(amount)}` coins"
            )
            return

        # Get user data
        user_data = await user_collection.find_one({'id': user.id})
        if not user_data:
            await message.reply("❌ You don't have any coins to convert.")
            return

        current_coins = int(user_data.get('balance', 0))
        if current_coins < amount:
            await message.reply(
                f"💸 **Insufficient Coins!**\n"
                f"Your Balance: `{humanize.intcomma(current_coins)}` coins\n"
                f"Required: `{humanize.intcomma(amount)}` coins"
            )
            return

        # Calculate gold earned (no fee)
        gold_earned = amount // CONVERSION_RATE
        if gold_earned == 0:
            await message.reply("❌ Not enough coins to earn even 1 gold.")
            return

        remaining_coins = current_coins - amount
        current_gold = int(user_data.get('gold', 0))
        new_gold_balance = current_gold + gold_earned

        # Update database
        await user_collection.update_one(
            {'id': user.id},
            {'$set': {
                'balance': remaining_coins,
                'gold': new_gold_balance
            }}
        )

        # Prepare final response
        coin_emoji = get_random_emoji(COIN_EMOJIS)
        gold_emoji = get_random_emoji(GOLD_EMOJIS)

        await message.reply(
            f"✅ **Conversion Successful!**\n\n"
            f"{coin_emoji} Coins Used: `{humanize.intcomma(amount)}`\n"
            f"{gold_emoji} Gold Earned: `{humanize.intcomma(gold_earned)}`\n\n"
            f"📦 **Your New Balance:**\n"
            f"{coin_emoji} Coins: `{humanize.intcomma(remaining_coins)}`\n"
            f"{gold_emoji} Gold: `{humanize.intcomma(new_gold_balance)}`"
        )

    except Exception as e:
        await message.reply(f"⚠️ **An error occurred:** `{str(e)}`")
