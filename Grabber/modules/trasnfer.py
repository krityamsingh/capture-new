from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from . import app, user_collection, sudo_filter
import humanize
import random
import time

# Rarity emojis for character summary
RARITY_EMOJIS = {
    'Common': '⚫', 'Limited Edition': '🔮', 'Premium': '🫧', 'Mythic': '💮',
    'Godly': '🔱', 'Legendary': '🟡', 'Epic': '🟣', 'Rare': '🟠', 'Uncommon': '🟤',
    'Exotic': '🏵️', 'Unique': '⚜️', 'Eternal': '⚡', 'Radiant': '🌸',
    'Divine': '💠', 'Celestial': '🎐', 'Electra': '🌩️', 'Galaxia': '🧿', 'Animation': '🧬'
}

# Gold and Ruby emoji variations
GOLD_EMOJIS = ["🪙", "💰", "🏆", "💎", "👑", "✨", "🔱", "🤑", "💸", "🫅"]
RUBY_EMOJIS = ["💎", "🔮", "🧿", "💠", "🪬", "💜", "💗", "🌌", "🔷", "✨"]

async def get_random_gold_emoji():
    return random.choice(GOLD_EMOJIS)

async def get_random_ruby_emoji():
    return random.choice(RUBY_EMOJIS)

def get_rarity_summary(characters):
    """Generate a summary of character rarities"""
    rarity_count = {}
    for char in characters:
        rarity = char.get("rarity", "Common")
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    lines = [f"{RARITY_EMOJIS.get(k, '')} **{k}**: `{v}`" for k, v in sorted(rarity_count.items())]
    return "\n".join(lines)

def format_large_number(number):
    """Format large numbers in a readable way"""
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    return str(number)

@app.on_message(sudo_filter & filters.command("transfer"))
async def transfer_command(client: Client, message: Message):
    """Direct transfer between users - NO confirmation needed"""
    args = message.text.split()[1:]
    if len(args) != 2:
        await message.reply_text(
            "**Usage**: `/transfer <sender_id> <receiver_id>`\n"
            "**Example**: `/transfer 123456789 987654321`"
        )
        return

    try:
        sender_id = int(args[0])
        receiver_id = int(args[1])
    except ValueError:
        await message.reply_text("**Invalid User IDs**. Please enter numeric IDs.")
        return

    if sender_id == receiver_id:
        await message.reply_text("**You can't transfer to yourself**.")
        return

    # Get sender and receiver data
    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})

    if not sender:
        await message.reply_text(f"**User with ID** `{sender_id}` **not found**.")
        return
    if not receiver:
        await message.reply_text(f"**User with ID** `{receiver_id}` **not found**.")
        return

    # Get real names or fallback to IDs
    sender_name = sender.get("first_name", f"User {sender_id}")
    receiver_name = receiver.get("first_name", f"User {receiver_id}")

    # Get all transferable assets
    sender_characters = sender.get("characters", [])
    sender_gold = float(sender.get("gold", 0))
    sender_rubies = float(sender.get("rubies", 0))
    sender_balance = float(sender.get("balance", 0))
    sender_saved = float(sender.get("saved_amount", 0))

    # Check if there's anything to transfer
    total_assets = (
        len(sender_characters) + sender_gold + sender_rubies + 
        sender_balance + sender_saved
    )
    
    if total_assets == 0:
        await message.reply_text(f"**{sender_name}** has no assets to transfer.")
        return

    status = await message.reply_text("⚡ **Transferring assets...**")

    # Get current receiver data
    receiver_data = await user_collection.find_one({'id': receiver_id})
    
    # Prepare updates
    receiver_update = {}
    sender_update = {}
    
    # Transfer characters
    if sender_characters:
        receiver_characters = receiver_data.get("characters", []) if receiver_data else []
        receiver_characters.extend(sender_characters)
        receiver_update["characters"] = receiver_characters
        sender_update["characters"] = []
    
    # Transfer gold
    if sender_gold > 0:
        receiver_gold = float(receiver_data.get("gold", 0)) if receiver_data else 0
        receiver_update["gold"] = receiver_gold + sender_gold
        sender_update["gold"] = 0
    
    # Transfer rubies
    if sender_rubies > 0:
        receiver_rubies = float(receiver_data.get("rubies", 0)) if receiver_data else 0
        receiver_update["rubies"] = receiver_rubies + sender_rubies
        sender_update["rubies"] = 0
    
    # Transfer balance
    if sender_balance > 0:
        receiver_balance = float(receiver_data.get("balance", 0)) if receiver_data else 0
        receiver_update["balance"] = receiver_balance + sender_balance
        sender_update["balance"] = 0
    
    # Transfer saved amount
    if sender_saved > 0:
        receiver_saved = float(receiver_data.get("saved_amount", 0)) if receiver_data else 0
        receiver_update["saved_amount"] = receiver_saved + sender_saved
        sender_update["saved_amount"] = 0

    # Update database
    try:
        # Update receiver
        if receiver_update:
            await user_collection.update_one(
                {'id': receiver_id},
                {'$set': receiver_update},
                upsert=True
            )
        
        # Update sender
        if sender_update:
            await user_collection.update_one(
                {'id': sender_id},
                {'$set': sender_update}
            )
        
        # Generate success message
        success_message = (
            f"**✅ Transfer Completed Instantly!**\n\n"
            f"**From**: {sender_name} (`{sender_id}`)\n"
            f"**To**: {receiver_name} (`{receiver_id}`)\n\n"
            f"**Transferred Assets**:\n"
        )
        
        if sender_characters:
            success_message += f"**Characters**: `{len(sender_characters)}` 👥\n"
            if len(sender_characters) > 1:
                success_message += f"{get_rarity_summary(sender_characters)}\n"
        if sender_gold > 0:
            success_message += f"**Gold**: `{format_large_number(sender_gold)}` {await get_random_gold_emoji()}\n"
        if sender_rubies > 0:
            success_message += f"**Rubies**: `{format_large_number(sender_rubies)}` {await get_random_ruby_emoji()}\n"
        if sender_balance > 0:
            success_message += f"**Balance**: `{format_large_number(sender_balance)}` 🪙\n"
        if sender_saved > 0:
            success_message += f"**Saved Amount**: `{format_large_number(sender_saved)}` 💰\n"
        
        success_message += f"\n**Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        
        await status.edit_text(success_message, parse_mode="markdown")
        
    except Exception as e:
        await status.edit_text(
            f"**❌ Transfer Failed**\n\n"
            f"Error: `{str(e)}`\n"
            f"Please try again."
    )
    
