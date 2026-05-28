import time
import os
import math
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from . import app, user_collection, collection
from .block import block_dec, temp_block
import pytz
from pyrogram.errors import BadRequest, RPCError
import random

TIMEZONE = pytz.timezone('Asia/Kolkata')
MAX_SAFE_INT = 2**63 - 1

# Emoji sets
GOLD_EMOJIS = ["💰", "🏆", "🏅", "🎖️", "🥇", "💎", "🪙", "👑"]
RUBY_EMOJIS = ["💎", "🔴", "♦️", "❤️", "💠", "🛑", "❣️"]

def custom_format_number(num):
    return f"{int(num):,}"

def format_number(num):
    return f"{int(num):,}"

def progress_bar(percent):
    fill = round(percent * 10)
    return '█' * fill + '░' * (10 - fill)

def get_wealth_level(amount):
    levels = [
        (0, "Beginner"),
        (100, "Traveler"),
        (500, "Merchant"),
        (2000, "Guild Master"),
        (5000, "Lord"),
        (10000, "Duke"),
        (50000, "Prince"),
        (100000, "King"),
        (500000, "Emperor"),
        (1000000, "Dragon Lord")
    ]
    for threshold, level in reversed(levels):
        if amount >= threshold:
            return level
    return "Beggar"

async def get_random_gold_emoji():
    return random.choice(GOLD_EMOJIS)

async def get_random_ruby_emoji():
    return random.choice(RUBY_EMOJIS)

@app.on_message(filters.command("status"))
@block_dec
async def status_command(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    try:
        await message.react("⚡")
    except:
        pass

    loading = await message.reply("🔍 Fetching your status...")

    try:
        user_data = await user_collection.find_one({"id": user_id})
        if not user_data:
            await loading.edit("❌ You haven't registered yet! Use /start to begin.")
            return

        # Character stats
        characters = user_data.get("characters", [])
        char_count = len(characters)
        total_chars = await collection.count_documents({}) or 1
        completion_rate = (char_count / total_chars) * 100

        # Balances
        balance = int(user_data.get("balance", 0))
        gold = float(user_data.get("gold", 0))
        rubies = float(user_data.get("rubies", 0))
        bank = int(user_data.get("saved_amount", 0))
        loan = int(user_data.get("loan_amount", 0))

        gold_emoji = user_data.get("last_gold_emoji", await get_random_gold_emoji())
        ruby_emoji = user_data.get("last_ruby_emoji", await get_random_ruby_emoji())

        # Rank
        safe_balance = min(balance, MAX_SAFE_INT)
        global_rank = await user_collection.count_documents({"balance": {"$gt": safe_balance}}) + 1
        total_users = await user_collection.count_documents({})

        # Rarity count
        rarity_counts = {}
        for c in characters:
            rarity = c.get('rarity', '🔵 LOW')
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

        rarity_display = "\n".join([
            f"{rarity.split()[0]} {rarity.split()[1]} → {format_number(count)}"
            for rarity, count in sorted(rarity_counts.items())
        ]) if rarity_counts else "⚫ Common → 0"

        # Account details
        created_at = user_data.get("created_at", datetime.now())
        account_age = (datetime.now(TIMEZONE) - created_at.replace(tzinfo=TIMEZONE)).days
        name_display = f"[{message.from_user.first_name}](tg://user?id={user_id})"

        # Wealth levels
        coin_level = get_wealth_level(balance)
        gold_level = get_wealth_level(gold)
        ruby_level = get_wealth_level(rubies)

        caption = f"""
✨ **Player Status Report** ✨
───────────────────
👤 **Name:** {name_display}
🆔 **User ID:** `{user_id}`
───────────────────
📦 **Collection Stats**
• Characters: `{format_number(char_count)}/{format_number(total_chars)}`
• Progress: `{progress_bar(completion_rate / 100)}`
───────────────────
💰 **Currencies**
• Coins: `{format_number(balance)}` ({coin_level})
• Bank: `{format_number(bank)}`
• Loan: `{format_number(loan)}`
• Gold {gold_emoji}: `{format_number(gold)}` ({gold_level})
• Rubies {ruby_emoji}: `{format_number(rubies)}` ({ruby_level})
───────────────────
🎭 **Rarity Breakdown**
{rarity_display}
───────────────────
"""

        # Try sending with profile pic
        photo_path = None
        try:
            user = await client.get_users(user_id)
            if user.photo:
                photo_path = await client.download_media(user.photo.big_file_id)
        except (BadRequest, RPCError):
            pass

        await loading.delete()

        if photo_path:
            await message.reply_photo(photo=photo_path, caption=caption)
            os.remove(photo_path)
        else:
            await message.reply(caption, disable_web_page_preview=True)

    except Exception as e:
        await loading.delete()
        await message.reply(f"❌ Error: `{str(e)}`")
