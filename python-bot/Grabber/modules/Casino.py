import random
import time
from pyrogram import Client, filters
from . import Grabberu as app, user_collection
import asyncio
from datetime import datetime, timedelta
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Dictionary to track cooldowns and active bets
user_cooldowns = {}
active_bets = {}

# Emoji values that Telegram assigns to each dice type
# Use '🎳', '🏀', '🎯', '🎲', '⚽', '🎰'
# Win values vary depending on emoji. Value range: 1-6.
# We'll define win criteria below.
EMOJI_WIN_VALUES = {
    "🎳": 6,  # Bowl
    "🏀": 6,  # Basket
    "🎯": 6,  # Dart
    "🎲": 6,  # Roll
    "⚽": 6,  # Soccer
    "🎰": 6,  # Slot
}

# Multipliers per game
GAME_CONFIG = {
    "bowl": {
        "emoji": "🎳",
        "multipliers": [1.5, 1.8, 2.0, 2.2, 2.5],
        "cooldown": 10,
        "action": "Bowling strike!"
    },
    "basket": {
        "emoji": "🏀",
        "multipliers": [1.5, 1.7, 2.0, 2.3, 2.5],
        "cooldown": 12,
        "action": "Basket shot!"
    },
    "dart": {
        "emoji": "🎯",
        "multipliers": [1.5, 1.9, 2.1, 2.3, 2.5],
        "cooldown": 15,
        "action": "Dart throw!"
    },
    "roll": {
        "emoji": "🎲",
        "multipliers": [1.5, 1.8, 2.0, 2.2, 2.5],
        "cooldown": 8,
        "action": "Dice roll!"
    },
    "soccer": {
        "emoji": "⚽",
        "multipliers": [1.5, 1.7, 2.0, 2.3, 2.5],
        "cooldown": 10,
        "action": "Penalty kick!"
    },
    "slot": {
        "emoji": "🎰",
        "multipliers": [1.5, 1.8, 2.0, 2.2, 2.5],
        "cooldown": 20,
        "action": "Slot spin!"
    }
}

cooldowns = {}

def to_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

async def update_balance(user_id, amount):
    await user_collection.update_one(
        {'id': user_id},
        {'$setOnInsert': {'balance': 0}},
        upsert=True
    )
    user = await user_collection.find_one({'id': user_id})
    if user and isinstance(user.get('balance'), str):
        current_balance = to_int(user['balance'])
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'balance': current_balance}}
        )
    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': to_int(amount)}}
    )

async def check_balance(user_id, amount):
    user = await user_collection.find_one({'id': user_id})
    if not user:
        return False
    balance = to_int(user.get('balance', 0))
    return balance >= amount

def check_cooldown(user_id, game_type):
    current_time = time.time()
    last_used = cooldowns.get((user_id, game_type), 0)
    cooldown = GAME_CONFIG[game_type]["cooldown"]
    remaining = int(cooldown - (current_time - last_used))
    return remaining if current_time - last_used < cooldown else 0

def format_game_result(user, game_type, amount, win_amount, multiplier, won=True):
    game = GAME_CONFIG[game_type]
    status_emoji = "✨" if won else "💥"
    status_text = "WON" if won else "LOST"
    
    result = (
        f"{game['emoji']} *{game['action']}* {game['emoji']}\n\n"
        f"• **Player**: {user}\n"
        f"• **Bet**: `{amount:,}` coins\n"
        f"• **Multiplier**: `{multiplier}x`\n"
        f"• **Result**: `{win_amount:,}` coins\n\n"
        f"{status_emoji} *{status_text}* {status_emoji}"
    )
    
    if not won:
        result += "\n\n💡 Better luck next time!"
    else:
        result += "\n\n🎉 Congratulations on your win!"
    
    return result

def format_bet_result(user, difficulty, amount, win_amount, multiplier, won=True):
    difficulty_emojis = {
        "easy": "🌸",
        "medium": "🌼",
        "hard": "⚡",
        "vip": "💎"
    }
    status_emoji = "✨" if won else "💥"
    status_text = "WON" if won else "LOST"
    
    result = (
        f"{difficulty_emojis[difficulty]} *{difficulty.upper()} BET RESULT* {difficulty_emojis[difficulty]}\n\n"
        f"• **Player**: {user}\n"
        f"• **Bet**: `{amount:,}` coins\n"
        f"• **Multiplier**: `{multiplier}x`\n"
        f"• **Result**: `{win_amount:,}` coins\n\n"
        f"{status_emoji} *{status_text}* {status_emoji}"
    )
    
    if not won:
        result += "\n\n💡 Try a lower difficulty next time!"
    else:
        result += "\n\n🔥 Great job! Want to try higher stakes?"
    
    return result

@app.on_message(filters.command(["bowl", "basket", "dart", "roll", "soccer", "slot"]))
async def casino_game(client: Client, message: Message):
    if not message.from_user:
        return

    try:
        game_type = message.command[0].lower()
        if len(message.command) < 2:
            return await message.reply(f"⚠️ Usage: `/{game_type} <amount>`")
        amount = to_int(message.command[1])
    except ValueError:
        return await message.reply("⚠️ Invalid amount! Please use numbers only.")

    # Cooldown check
    remaining = check_cooldown(message.from_user.id, game_type)
    if remaining > 0:
        return await message.reply(f"⏳ Cooldown: Try again in {remaining} seconds")

    # Balance check
    if not await check_balance(message.from_user.id, amount):
        return await message.reply("❌ Insufficient balance!")

    # Deduct balance and set cooldown
    await update_balance(message.from_user.id, -amount)
    cooldowns[(message.from_user.id, game_type)] = time.time()

    game = GAME_CONFIG[game_type]
    emoji = game["emoji"]
    dice_msg = await app.send_dice(chat_id=message.chat.id, emoji=emoji)
    value = dice_msg.dice.value
    await asyncio.sleep(2)

    user_mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"

    if value == EMOJI_WIN_VALUES[emoji]:
        multiplier = random.choice(game["multipliers"])
        win_amount = int(amount * multiplier)
        await update_balance(message.from_user.id, win_amount)
        result = format_game_result(
            user=user_mention,
            game_type=game_type,
            amount=amount,
            win_amount=win_amount,
            multiplier=multiplier,
            won=True
        )
    else:
        loss_multiplier = round(random.uniform(0.1, 0.9), 1)
        win_amount = int(amount * loss_multiplier)
        if win_amount > 0:
            await update_balance(message.from_user.id, win_amount)
        result = format_game_result(
            user=user_mention,
            game_type=game_type,
            amount=amount,
            win_amount=win_amount,
            multiplier=loss_multiplier,
            won=False
        )

    await message.reply(result)

# Advanced bet command
@app.on_message(filters.command("bet"))
async def bet_game(client: Client, message: Message):
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    # Check cooldown
    current_time = time.time()
    if user_id in user_cooldowns and current_time < user_cooldowns[user_id]:
        remaining = int(user_cooldowns[user_id] - current_time)
        return await message.reply(f"⏰ Please wait {remaining} seconds before using the bet command again.")
    
    try:
        if len(message.command) < 2:
            return await message.reply("⚠️ Usage: `/bet <amount>`")
        amount = to_int(message.command[1])
    except ValueError:
        return await message.reply("⚠️ Invalid amount! Please use numbers only.")

    if amount <= 0:
        return await message.reply("⚠️ Amount must be greater than zero!")

    if not await check_balance(message.from_user.id, amount):
        return await message.reply("❌ Insufficient balance!")

    # Check if user already has an active bet
    if user_id in active_bets:
        try:
            # Try to delete the previous bet message
            prev_msg_id = active_bets[user_id]
            await client.delete_messages(message.chat.id, prev_msg_id)
        except:
            pass
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("EASY (60% win)", callback_data=f"bet_{user_id}_easy_{amount}"),
            InlineKeyboardButton("MEDIUM (45% win)", callback_data=f"bet_{user_id}_medium_{amount}")
        ],
        [
            InlineKeyboardButton("HARD (30% win)", callback_data=f"bet_{user_id}_hard_{amount}"),
            InlineKeyboardButton("VIP (15% win)", callback_data=f"bet_{user_id}_vip_{amount}")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"bet_{user_id}_cancel")
        ]
    ])

    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    bet_message = await message.reply(
        f"🎲 *BET SELECTION* 🎲\n\n"
        f"**Player**: {mention}\n"
        f"**Amount**: `{amount:,}` coins\n\n"
        "**Choose your difficulty level:**\n",
        reply_markup=buttons
    )
    
    # Store the message ID for this user's active bet
    active_bets[user_id] = bet_message.id
    
    # Set cooldown (30 seconds)
    user_cooldowns[user_id] = current_time + 30

# Bet callback handler
@app.on_callback_query(filters.regex(r"^bet_(\d+)_(easy|medium|hard|vip)_(\d+)$"))
async def bet_callback(client: Client, query: CallbackQuery):
    data_parts = query.data.split("_")
    target_user_id = int(data_parts[1])
    difficulty = data_parts[2]
    amount = to_int(data_parts[3])
    user_id = query.from_user.id
    
    # Check if the user clicking is the same who initiated the bet
    if user_id != target_user_id:
        await query.answer("⚠️ This is not your bet!", show_alert=True)
        return
    
    # Delete the original message with buttons
    try:
        await query.message.delete()
    except:
        pass
    
    # Remove from active bets
    if user_id in active_bets:
        del active_bets[user_id]

    if not await check_balance(user_id, amount):
        await query.answer("❌ Insufficient balance!", show_alert=True)
        return

    # Deduct amount
    await update_balance(user_id, -amount)

    # Determine outcome based on difficulty
    difficulties = {
        "easy": {"win_prob": 0.6, "range": (1.5, 2.0)},
        "medium": {"win_prob": 0.45, "range": (1.0, 3.0)},
        "hard": {"win_prob": 0.3, "range": (0.5, 5.0)},
        "vip": {"win_prob": 0.15, "range": (0.1, 10.0)}
    }

    config = difficulties[difficulty]
    won = random.random() < config["win_prob"]
    
    if won:
        multiplier = round(random.uniform(*config["range"]), 1)
        win_amount = int(amount * multiplier)
        await update_balance(user_id, win_amount)
    else:
        multiplier = round(random.uniform(0.1, config["range"][0]-0.1), 1)
        win_amount = int(amount * multiplier)
        if win_amount > 0:
            await update_balance(user_id, win_amount)

    mention = f"[{query.from_user.first_name}](tg://user?id={user_id})"
    
    # Generate a unique result message based on outcome
    if won:
        celebration = random.choice(["🎉", "🔥", "💰", "🤑", "🌟"])
        result_message = (
            f"{celebration} *JACKPOT!* {celebration}\n\n"
            f"**Player**: {mention}\n"
            f"**Difficulty**: {difficulty.upper()}\n"
            f"**Bet Amount**: `{amount:,}` coins\n"
            f"**Multiplier**: `{multiplier}x`\n"
            f"**You Won**: `{win_amount:,}` coins!\n\n"
            f"*Balance updated successfully!*"
        )
    else:
        reaction = random.choice(["😢", "😭", "💸", "🤕", "🌧️"])
        result_message = (
            f"{reaction} *BETTER LUCK NEXT TIME!* {reaction}\n\n"
            f"**Player**: {mention}\n"
            f"**Difficulty**: {difficulty.upper()}\n"
            f"**Bet Amount**: `{amount:,}` coins\n"
            f"**Multiplier**: `{multiplier}x`\n"
            f"**You Got Back**: `{win_amount:,}` coins\n\n"
            f"*Balance updated successfully!*"
        )

    # Send spinning animation with unique emojis
    spin_frames = ["🎰", "🎲", "🎯", "🃏", "💰"]
    msg = await client.send_message(query.message.chat.id, f"{spin_frames[0]} Spinning...")
    
    for frame in spin_frames[1:]:
        await asyncio.sleep(0.5)
        await msg.edit_text(f"{frame} Spinning...")
    
    await asyncio.sleep(1)
    
    # Edit with final result
    await msg.edit_text(result_message)
    await query.answer()

# Cancel bet handler
@app.on_callback_query(filters.regex(r"^bet_(\d+)_cancel$"))
async def bet_cancel(client: Client, query: CallbackQuery):
    data_parts = query.data.split("_")
    target_user_id = int(data_parts[1])
    user_id = query.from_user.id
    
    # Check if the user clicking is the same who initiated the bet
    if user_id != target_user_id:
        await query.answer("⚠️ This is not your bet!", show_alert=True)
        return
    
    try:
        await query.message.delete()
    except:
        pass
    
    # Remove from active bets
    if user_id in active_bets:
        del active_bets[user_id]
        
    await query.answer("❌ Bet cancelled!", show_alert=False)
