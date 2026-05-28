from pyrogram import Client, filters
from pyrogram.types import Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from Grabber import user_collection
from . import add, deduct, sudo_filter, app, dev_filter
from typing import Union
import time
from datetime import datetime

async def get_user_info(user_id: int) -> Union[dict, None]:
    return await user_collection.find_one({'id': user_id})

async def update_and_respond(message: Message, user_id: int, amount: int, action: str):
    user = await get_user_info(user_id)
    if not user:
        await message.reply_text("❌ User not found in database!")
        return

    if action == "add":
        await add(user_id, amount)
        action_text = f"✨ Token Gift Received! ✨\n➕ Added {amount} Tokens to"
    elif action == "deduct":
        if user['balance'] < amount:
            await message.reply_text("⚠️ User doesn't have enough tokens to deduct!")
            return
        await deduct(user_id, amount)
        action_text = f"⚠️ Token Deduction Notice ⚠️\n➖ Deducted {amount} Tokens from"
    else:
        return

    updated_user = await get_user_info(user_id)
    updated_balance = updated_user.get("balance", 0)
    
    await message.reply_text(
        f"🎯 Token Transaction Complete 🎯\n"
        f"{action_text} user:\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🆔 User ID: {user_id}\n"
        f"👤 Username: @{user.get('username', 'N/A')}\n"
        f"💎 New Balance: {updated_balance} Tokens\n"
        f"🛠 Processed by: {message.from_user.mention}\n"
        f"⏱ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

@app.on_message(filters.command(["addt", "addtokens"]) & sudo_filter)
async def add_tokens(client: Client, message: Message):
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            amount = int(message.command[1])
        else:
            user_id = int(message.command[1])
            amount = int(message.command[2])
    except (IndexError, ValueError):
        await message.reply_text(
            "🔧 Add Tokens Command 🔧\n\n"
            "💠 Usage:\n"
            "• /addt (user_id) (amount)\n"
            "• Reply to user with /addt (amount)\n\n"
            "🌠 Examples:\n"
            "/addt 123456789 500\n"
            "Reply to user: /addt 1000"
        )
        return

    await update_and_respond(message, user_id, amount, "add")

@app.on_message(filters.command(["removet", "deducttokens"]) & dev_filter)
async def remove_tokens(client: Client, message: Message):
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            amount = int(message.command[1])
        else:
            user_id = int(message.command[1])
            amount = int(message.command[2])
    except (IndexError, ValueError):
        await message.reply_text(
            "🔧 Remove Tokens Command 🔧\n\n"
            "💠 Usage:\n"
            "• /removet (user_id) (amount)\n"
            "• Reply to user with /removet (amount)\n\n"
            "🌠 Examples:\n"
            "/removet 123456789 200\n"
            "Reply to user: /removet 150"
        )
        return

    await update_and_respond(message, user_id, amount, "deduct")

@app.on_message(filters.command(["resetall", "resettokens"]) & dev_filter)
async def reset_all_tokens(client: Client, message: Message):
    try:
        if len(message.command) > 1 and message.command[1].isdigit():
            amount = int(message.command[1])
            confirm_text = (
                f"⚠️ Global Token Deduction Warning ⚠️\n\n"
                f"🔻 This will deduct {amount} tokens from ALL users!\n"
                f"👤 Affected users: {await user_collection.count_documents({})}\n\n"
                f"Are you sure?"
            )
            confirm_key = "deduct_all"
        else:
            confirm_text = (
                "⚠️ Global Reset Warning ⚠️\n\n"
                "♻️ This will reset ALL users' balances (main, saved, and loan) to 0!\n"
                f"👤 Affected users: {await user_collection.count_documents({})}\n\n"
                "Are you sure?"
            )
            confirm_key = "reset_all"
            amount = None

        await message.reply_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"{confirm_key}_{amount or ''}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
                ]
            ])
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@app.on_callback_query(filters.regex(r"^(reset_all|deduct_all)") & dev_filter)
async def confirm_reset(client, callback_query):
    try:
        # Parse the callback data safely
        parts = callback_query.data.rsplit('_', 1)  # Split on last underscore only
        action = parts[0]
        amount = parts[1] if len(parts) > 1 else '0'
        
        admin = callback_query.from_user
        
        if action == "reset_all":
            # FULL RESET - Set all balances to 0
            await user_collection.update_many(
                {},
                {'$set': {
                    'balance': 0,
                    'saved_amount': 0,
                    'loan_amount': 0
                }}
            )
            
            success_msg = (
                f"♻️ Global Reset Complete!\n\n"
                f"• All users' balances reset to 0\n"
                f"• Reset by: {admin.mention}\n"
                f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        else:
            # DEDUCTION - Handle large numbers properly
            amount = int(amount) if amount.isdigit() else 0
            
            # Process in batches to handle large collections
            batch_size = 100
            total_updated = 0
            
            async for user in user_collection.find({}):
                try:
                    # Convert balance to integer safely
                    current_balance = int(user.get('balance', 0))
                    
                    # Calculate new balance (ensure it doesn't go negative)
                    new_balance = max(0, current_balance - amount)
                    
                    # Update the user
                    await user_collection.update_one(
                        {'_id': user['_id']},
                        {'$set': {'balance': new_balance}}
                    )
                    
                    total_updated += 1
                    
                    # Batch commit
                    if total_updated % batch_size == 0:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    print(f"Error processing user {user.get('id')}: {str(e)}")
                    continue
            
            success_msg = (
                f"🔻 Global Deduction Complete!\n\n"
                f"• Deducted {amount} tokens from all users\n"
                f"• Total users updated: {total_updated}\n"
                f"• Processed by: {admin.mention}\n"
                f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        await callback_query.edit_message_text(success_msg)
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n\nPlease check server logs for details."
        await callback_query.edit_message_text(error_msg)
        print(f"Critical error in confirm_reset: {str(e)}")

@app.on_callback_query(filters.regex("^cancel_reset$") & dev_filter)
async def cancel_reset(client, callback_query):
    await callback_query.edit_message_text("❌ Token reset operation cancelled.")

@app.on_message(filters.command(["tgive", "givealltokens"]) & dev_filter)
async def give_all_tokens(client: Client, message: Message):
    try:
        amount = int(message.command[1])
        if amount <= 0:
            await message.reply_text("⚠️ Amount must be positive!")
            return
            
        total_users = await user_collection.count_documents({})
        await message.reply_text(
            f"🎁 Mass Token Distribution 🎁\n\n"
            f"• Amount to give: {amount} tokens\n"
            f"• Total recipients: {total_users}\n\n"
            f"Are you sure?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"tgive_{amount}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_tgive")
                ]
            ])
        )
    except (IndexError, ValueError):
        await message.reply_text(
            "🔧 Mass Token Distribution Command 🔧\n\n"
            "💠 Usage:\n"
            "/tgive (amount)\n\n"
            "🌠 Example:\n"
            "/tgive 10000 - Gives 10,000 tokens to all users"
        )

@app.on_callback_query(filters.regex(r"^tgive_(\d+)$") & dev_filter)
async def confirm_tgive(client, callback_query):
    amount = int(callback_query.data.split('_')[1])
    admin = callback_query.from_user
    
    try:
        start_time = time.time()
        
        # Safe balance fixing: use $toLong instead of $toInt
        await user_collection.update_many(
            {"balance": {"$type": "string"}},
            [{"$set": {"balance": {"$convert": {"input": "$balance", "to": "long", "onError": 0, "onNull": 0}}}}]
        )
        
        # Then perform the increment
        result = await user_collection.update_many(
            {},
            {'$inc': {'balance': amount}}
        )
        
        elapsed = time.time() - start_time
        
        await callback_query.edit_message_text(
            f"🎉 Mass Distribution Complete! 🎉\n\n"
            f"• Tokens given: {amount} to each user\n"
            f"• Total recipients: {result.modified_count}\n"
            f"• Processed by: {admin.mention}\n"
            f"• Time taken: {elapsed:.2f} seconds\n"
            f"• Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        await callback_query.edit_message_text(f"❌ Error: {str(e)}")

@app.on_callback_query(filters.regex("^cancel_tgive$") & dev_filter)
async def cancel_tgive(client, callback_query):
    await callback_query.edit_message_text("❌ Token distribution cancelled.")
