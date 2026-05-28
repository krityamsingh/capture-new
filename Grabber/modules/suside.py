import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from . import app, user_collection, collection, backup_collection
from .block import block_dec, temp_block
import pytz
from pyrogram.errors import BadRequest, RPCError
import humanize
import random

# Configurations
TIMEZONE = pytz.timezone('Asia/Kolkata')
# Changed: use a list instead of a set for owner IDs
OWNER_IDS = [8496760733, 6228788487, 6118760915]  # Replace with your owner ID(s)
LOG_CHANNEL = -1003248939428  # Replace with your log channel ID

# Helper function to create backup
async def create_backup(user_id, action_type, data_before):
    backup_data = {
        "user_id": user_id,
        "action_type": action_type,
        "data": data_before,
        "timestamp": datetime.now(TIMEZONE),
        "restored": False
    }
    await backup_collection.insert_one(backup_data)
    return backup_data

# Helper function to notify owner and log channel
async def notify_actions(user_data, action_type, deleted_data=None):
    user_id = user_data["id"]
    user_name = user_data.get("name", "Unknown")
    
    # Prepare notification message
    if action_type == "all":
        action_desc = "FULL ACCOUNT SUICIDE"
        details = f"""
• Characters deleted: {len(deleted_data.get('characters', []))}
• Coins reset: {deleted_data.get('balance', 0):,}
• Gold reset: {deleted_data.get('gold', 0):,}
• Rubies reset: {deleted_data.get('rubies', 0):,}
• Bank reset: {deleted_data.get('saved_amount', 0):,}
• Loan reset: {deleted_data.get('loan_amount', 0):,}"""
    elif action_type == "chars":
        action_desc = "CHARACTER COLLECTION DELETED"
        details = f"• Characters deleted: {len(deleted_data.get('characters', []))}"
    elif action_type == "currency":
        action_desc = "ALL CURRENCY DELETED"
        details = f"""
• Coins reset: {deleted_data.get('balance', 0):,}
• Gold reset: {deleted_data.get('gold', 0):,}
• Rubies reset: {deleted_data.get('rubies', 0):,}
• Bank reset: {deleted_data.get('saved_amount', 0):,}
• Loan reset: {deleted_data.get('loan_amount', 0):,}"""
    
    # Send to log channel
    log_message = f"""
⚠️ **{action_desc}** ⚠️
➖➖➖➖➖➖➖➖➖
👤 User: {user_name} (`{user_id}`)
🕒 Time: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}
➖➖➖➖➖➖➖➖➖
📊 **Details:**
{details}
➖➖➖➖➖➖➖➖➖
#suicide_log #user_{user_id}"""
    
    try:
        await app.send_message(LOG_CHANNEL, log_message)
    except Exception as e:
        print(f"Failed to send log message: {e}")
    
    # Send to owner(s) with restore button
    owner_message = f"""
🔔 **USER SUICIDE ALERT** 🔔
➖➖➖➖➖➖➖➖➖
👤 User: {user_name} (`{user_id}`)
🛑 Action: {action_desc}
🕒 Time: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}
➖➖➖➖➖➖➖➖➖
📊 **Details:**
{details}"""
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"🔄 RESTORE {action_type.upper()}",
            callback_data=f"restore_{action_type}_{user_id}"
        )]
    ])
    
    try:
        # Changed: loop over all owner IDs and send the message to each
        for owner_id in OWNER_IDS:
            await app.send_message(owner_id, owner_message, reply_markup=buttons)
    except Exception as e:
        print(f"Failed to notify owner: {e}")

# Suicide command with advanced confirmation flows
@app.on_message(filters.command("suicide"))
@block_dec
async def suicide_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is new (less than 1 day old)
    user_data = await user_collection.find_one({"id": user_id})
    if not user_data:
        await message.reply("❌ You don't have any data to suicide! You need to have something first.")
        return
    
    created_at = user_data.get("created_at", datetime.now())
    
    # Get user stats
    characters = user_data.get("characters", [])
    balance = int(user_data.get("balance", 0))
    gold = float(user_data.get("gold", 0))
    rubies = float(user_data.get("rubies", 0))
    saved_amount = int(user_data.get("saved_amount", 0))
    loan_amount = int(user_data.get("loan_amount", 0))
    
    # Check if user has anything to suicide
    if not characters and balance == 0 and gold == 0 and rubies == 0 and saved_amount == 0 and loan_amount == 0:
        await message.reply("❌ You don't have anything to suicide!")
        return
    
    # Rarity counts
    rarity_counts = {}
    for char in characters:
        rarity = char.get('rarity', '🔵 LOW')
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
    
    # Highest and lowest rarity
    rarities = {
        '⚫ COMMON': 0,
        '🔵 LOW': 1,
        '🟢 MEDIUM': 2,
        '🟣 HIGH': 3,
        '🟡 LEGENDARY': 4,
        '🔴 MYTHICAL': 5,
        '🟤 SPECIAL': 6
    }
    
    if characters:
        sorted_chars = sorted(characters, key=lambda x: rarities.get(x.get('rarity', '⚫ COMMON'), 0))
        lowest_rarity = sorted_chars[0].get('rarity', '⚫ COMMON')
        highest_rarity = sorted_chars[-1].get('rarity', '⚫ COMMON')
    else:
        lowest_rarity = highest_rarity = "None"
    
    # Create suicide options
    suicide_options = InlineKeyboardMarkup([
        [InlineKeyboardButton("💀 SUICIDE ALL", callback_data=f"suicide_all_{user_id}")],
        [
            InlineKeyboardButton("🗑️ DELETE COLLECTION ONLY", callback_data=f"suicide_chars_{user_id}"),
            InlineKeyboardButton("💰 DELETE ALL CURRENCY", callback_data=f"suicide_currency_{user_id}")
        ],
        [InlineKeyboardButton("❌ CANCEL", callback_data=f"suicide_cancel_{user_id}")]
    ])
    
    status_message = f"""
⚠️ **SUICIDE MENU** ⚠️
➖➖➖➖➖➖➖➖➖
👤 User: [{message.from_user.first_name}](tg://user?id={user_id})
🆔 ID: `{user_id}`
➖➖➖➖➖➖➖➖➖
📊 Your current stats:
• Characters: `{len(characters)}`
• Coins: `{balance:,}`
• Gold: `{gold:,}`
• Rubies: `{rubies:,}`
• Bank: `{saved_amount:,}`
• Loan: `{loan_amount:,}`
➖➖➖➖➖➖➖➖➖
🔻 Lowest rarity: `{lowest_rarity}`
🔺 Highest rarity: `{highest_rarity}`
➖➖➖➖➖➖➖➖➖
**WARNING:** This action is irreversible!
"""

    suicide_msg = await message.reply(
        status_message,
        reply_markup=suicide_options,
        disable_web_page_preview=True
    )
    
    # Store message ID for later deletion
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"last_suicide_msg": suicide_msg.id}}
    )

# Callback query handler
@app.on_callback_query(filters.regex(r"^suicide_(all|chars|currency|cancel)_(\d+)$"))
async def suicide_callback_handler(client: Client, query: CallbackQuery):
    action = query.data.split("_")[1]
    target_user_id = int(query.data.split("_")[2])
    query_user_id = query.from_user.id
    
    # Check if the user clicking is the same as the target user
    if query_user_id != target_user_id:
        await query.answer("⚠️ You can't perform this action for someone else!", show_alert=True)
        return
    
    user_data = await user_collection.find_one({"id": target_user_id})
    if not user_data:
        await query.answer("❌ User not found!", show_alert=True)
        return
    
    # Delete the original suicide message
    try:
        last_msg_id = user_data.get("last_suicide_msg")
        if last_msg_id:
            await client.delete_messages(query.message.chat.id, last_msg_id)
    except:
        pass
    
    if action == "cancel":
        await query.answer("Suicide cancelled!", show_alert=True)
        return
    
    characters = user_data.get("characters", [])
    balance = int(user_data.get("balance", 0))
    gold = float(user_data.get("gold", 0))
    rubies = float(user_data.get("rubies", 0))
    saved_amount = int(user_data.get("saved_amount", 0))
    loan_amount = int(user_data.get("loan_amount", 0))
    
    if action == "all":
        confirmation_message = f"""
⚠️ **FINAL CONFIRMATION: SUICIDE ALL** ⚠️
➖➖➖➖➖➖➖➖➖
👤 User: [{query.from_user.first_name}](tg://user?id={target_user_id})
🆔 ID: `{target_user_id}`
➖➖➖➖➖➖➖➖➖
🔥 **This will permanently delete:**
• All characters: `{len(characters)}`
• All coins: `{balance:,}`
• All gold: `{gold:,}`
• All rubies: `{rubies:,}`
• Bank balance: `{saved_amount:,}`
• Loan balance: `{loan_amount:,}`
➖➖➖➖➖➖➖➖➖
**This action is irreversible! Are you sure?**
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ CONFIRM SUICIDE ALL", callback_data=f"confirm_suicide_all_{target_user_id}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_suicide_{target_user_id}")]
        ])
    
    elif action == "chars":
        if not characters:
            await query.answer("You don't have any characters to delete!", show_alert=True)
            return
        
        rarity_counts = {}
        for char in characters:
            rarity = char.get('rarity', '⚫ COMMON')
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        rarity_details = "\n".join([f"• {rarity}: {count}" for rarity, count in rarity_counts.items()])
        
        confirmation_message = f"""
⚠️ **FINAL CONFIRMATION: DELETE COLLECTION** ⚠️
➖➖➖➖➖➖➖➖➖
👤 User: [{query.from_user.first_name}](tg://user?id={target_user_id})
🆔 ID: `{target_user_id}`
➖➖➖➖➖➖➖➖➖
🔥 **This will permanently delete:**
• Total characters: `{len(characters)}`
{rarity_details}
➖➖➖➖➖➖➖➖➖
**This action is irreversible! Are you sure?**
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ CONFIRM DELETE COLLECTION", callback_data=f"confirm_suicide_chars_{target_user_id}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_suicide_{target_user_id}")]
        ])
    
    elif action == "currency":
        if balance == 0 and gold == 0 and rubies == 0 and saved_amount == 0 and loan_amount == 0:
            await query.answer("You don't have any currency to delete!", show_alert=True)
            return
        
        confirmation_message = f"""
⚠️ **FINAL CONFIRMATION: DELETE ALL CURRENCY** ⚠️
➖➖➖➖➖➖➖➖➖
👤 User: [{query.from_user.first_name}](tg://user?id={target_user_id})
🆔 ID: `{target_user_id}`
➖➖➖➖➖➖➖➖➖
🔥 **This will permanently delete:**
• Coins: `{balance:,}`
• Gold: `{gold:,}`
• Rubies: `{rubies:,}`
• Bank balance: `{saved_amount:,}`
• Loan balance: `{loan_amount:,}`
➖➖➖➖➖➖➖➖➖
**This action is irreversible! Are you sure?**
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ CONFIRM DELETE CURRENCY", callback_data=f"confirm_suicide_currency_{target_user_id}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_suicide_{target_user_id}")]
        ])
    
    msg = await query.message.reply(
        confirmation_message,
        reply_markup=buttons,
        disable_web_page_preview=True
    )
    await user_collection.update_one(
        {"id": target_user_id},
        {"$set": {"last_suicide_msg": msg.id}}
    )
    await query.answer()

# Final confirmation handlers
@app.on_callback_query(filters.regex(r"^confirm_suicide_(all|chars|currency)_(\d+)$"))
async def confirm_suicide_handler(client: Client, query: CallbackQuery):
    action = query.data.split("_")[2]
    target_user_id = int(query.data.split("_")[3])
    query_user_id = query.from_user.id
    
    if query_user_id != target_user_id:
        await query.answer("⚠️ You can't perform this action for someone else!", show_alert=True)
        return
    
    user_data = await user_collection.find_one({"id": target_user_id})
    if not user_data:
        await query.answer("❌ User not found!", show_alert=True)
        return
    
    # Create backup before deletion
    backup_data = {
        "characters": user_data.get("characters", []),
        "balance": user_data.get("balance", 0),
        "gold": user_data.get("gold", 0),
        "rubies": user_data.get("rubies", 0),
        "saved_amount": user_data.get("saved_amount", 0),
        "loan_amount": user_data.get("loan_amount", 0),
        "daily_streak": user_data.get("daily_streak", 0),
        "last_claim_time": user_data.get("last_claim_time")
    }
    
    await create_backup(target_user_id, action, backup_data)
    
    # Update message with loading
    await query.message.edit_text("🔄 Processing your request...")
    
    if action == "all":
        # Delete everything
        await user_collection.update_one(
            {"id": target_user_id},
            {
                "$set": {
                    "characters": [],
                    "balance": 0,
                    "gold": 0,
                    "rubies": 0,
                    "saved_amount": 0,
                    "loan_amount": 0,
                    "last_claim_time": None,
                    "daily_streak": 0
                }
            }
        )
        result_message = "☠️ **SUICIDE COMPLETE!** Your entire account has been reset. No characters, no currency, nothing left."
    
    elif action == "chars":
        # Delete only characters
        await user_collection.update_one(
            {"id": target_user_id},
            {"$set": {"characters": []}}
        )
        result_message = "🗑️ **COLLECTION DELETED!** All your characters have been permanently removed."
    
    elif action == "currency":
        # Delete all currency
        await user_collection.update_one(
            {"id": target_user_id},
            {
                "$set": {
                    "balance": 0,
                    "gold": 0,
                    "rubies": 0,
                    "saved_amount": 0,
                    "loan_amount": 0
                }
            }
        )
        result_message = "💰 **CURRENCY WIPED!** All your coins, gold, rubies, bank balance and loans have been reset to zero."
    
    # Notify owner and log channel
    await notify_actions(user_data, action, backup_data)
    
    # Edit the message with final result
    await query.message.edit_text(
        f"{result_message}\n\n➖➖➖➖➖➖➖➖➖\n👤 User: [{query.from_user.first_name}](tg://user?id={target_user_id})\n🆔 ID: `{target_user_id}`"
    )
    await query.answer()

# Cancel suicide handler
@app.on_callback_query(filters.regex(r"^cancel_suicide_(\d+)$"))
async def cancel_suicide_handler(client: Client, query: CallbackQuery):
    target_user_id = int(query.data.split("_")[1])
    query_user_id = query.from_user.id
    
    if query_user_id != target_user_id:
        await query.answer("⚠️ You can't cancel someone else's action!", show_alert=True)
        return
    
    await query.message.edit_text(
        f"❌ **SUICIDE CANCELLED!** Nothing has been changed.\n\n➖➖➖➖➖➖➖➖➖\n👤 User: [{query.from_user.first_name}](tg://user?id={target_user_id})\n🆔 ID: `{target_user_id}`"
    )
    await query.answer("Suicide cancelled!", show_alert=True)

# Restore handler (for owner only)
@app.on_callback_query(
    filters.regex(r"^restore_(all|chars|currency)_(\d+)$") & filters.user(OWNER_IDS)
)
async def restore_handler(client: Client, query: CallbackQuery):
    action = query.data.split("_")[1]
    target_user_id = int(query.data.split("_")[2])
    
    # Find the latest backup for this user and action type
    backup = await backup_collection.find_one({
        "user_id": target_user_id,
        "action_type": action,
        "restored": False
    }, sort=[("timestamp", -1)])
    
    if not backup:
        await query.answer("❌ No backup found for this action!", show_alert=True)
        return
    
    # Update user data with backup
    if action == "all":
        update_data = {
            "$set": {
                "characters": backup["data"].get("characters", []),
                "balance": backup["data"].get("balance", 0),
                "gold": backup["data"].get("gold", 0),
                "rubies": backup["data"].get("rubies", 0),
                "saved_amount": backup["data"].get("saved_amount", 0),
                "loan_amount": backup["data"].get("loan_amount", 0),
                "daily_streak": backup["data"].get("daily_streak", 0),
                "last_claim_time": backup["data"].get("last_claim_time")
            }
        }
    elif action == "chars":
        update_data = {
            "$set": {
                "characters": backup["data"].get("characters", [])
            }
        }
    elif action == "currency":
        update_data = {
            "$set": {
                "balance": backup["data"].get("balance", 0),
                "gold": backup["data"].get("gold", 0),
                "rubies": backup["data"].get("rubies", 0),
                "saved_amount": backup["data"].get("saved_amount", 0),
                "loan_amount": backup["data"].get("loan_amount", 0)
            }
        }
    
    await user_collection.update_one({"id": target_user_id}, update_data)
    await backup_collection.update_one({"_id": backup["_id"]}, {"$set": {"restored": True}})
    
    # Get user info for notification
    user_data = await user_collection.find_one({"id": target_user_id})
    user_name = user_data.get("name", "Unknown") if user_data else "Unknown"
    
    # Update the message
    await query.message.edit_text(
        f"✅ **RESTORE COMPLETE!**\n\n"
        f"User: {user_name} (`{target_user_id}`)\n"
        f"Action: {action.upper()} RESTORED\n"
        f"Time: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"All data has been successfully restored."
    )
    
    # Notify the user
    try:
        await client.send_message(
            target_user_id,
            f"♻️ **Your account data has been restored by admin!**\n\n"
            f"All your {action} data has been recovered. "
            f"Please check your account status with /status"
        )
    except:
        pass
    
    await query.answer("Restore completed!", show_alert=True)
