from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    Message,
    InputMediaPhoto
)
from Grabber import db, user_collection
from Grabber import Grabberu as app
from . import sudo_filter, dev_filter
import time
import random
import asyncio
from datetime import datetime
from bson import ObjectId  # For MongoDB document IDs

# Collections
backup_collection = db["backup_collection"]
reputation_collection = db["reputation_collection"]
bank_backup_collection = db["bank_backup_collection"]

# Rarity Map with new emojis
rarity_map = {
    "🔴 Common": "🔴",
    "🔮 Limited Edition": "🔮",
    "🫧 Premium": "🫧",
    "🟡 Legendary": "🟡",
    "⚪ Epic": "⚪",
    "🟠 Rare": "🟠",
    "🔵 Uncommon": "🔵",
    "🏵️ Exotic": "🏵️",
    "⚜️ Animated": "⚜️",
    "🌼 Celebrity": "🌼",
    "🎐 Crystal": "🎐",
    "🍹 Neon": "🍹",
    "🧿 Supreme": "🧿",
    "⚡ Thundra": "⚡",
    "🛸 Galvoria": "🛸",
    "🔮 Arcane Verse": "🔮",
    "🫧 Aether Verse": "🫧",
    "🟡 Solar Verse": "🟡"
}

# Animation messages for different actions
ANIMATION_MESSAGES = {
    "delete": [
        "💥 Poof! All waifus vanished into the void!",
        "🗑️ Successfully trashed the collection!",
        "🔥 Burned all waifus to ashes!",
        "🌀 Sent all waifus to the shadow realm!"
    ],
    "bank_reset": [
        "💸 Bank account evaporated!",
        "🏦 Financial records wiped clean!",
        "💰 Money go brrrr... and then disappear!",
        "🧹 Swept all funds into oblivion!"
    ],
    "cancel": [
        "🛑 Operation aborted!",
        "🚫 Crisis averted!",
        "❌ Nothing was deleted!",
        "🔙 Returning to safety!"
    ],
    "destroy": [
        "💣 Nuclear option activated! Everything gone!",
        "☢️ Complete annihilation successful!",
        "🌋 Total destruction achieved!",
        "⚛️ Matter disintegrated at atomic level!"
    ],
    "restore": [
        "🔄 Time reversed! Everything restored!",
        "♻️ Recovery complete!",
        "✨ Magic restoration successful!",
        "⏳ Turned back time to undo changes!"
    ]
}

async def safe_message_operation(message, operation="delete"):
    """Safely perform message operations without raising errors"""
    try:
        if not message:
            return False
            
        if operation == "delete":
            # Only delete if we sent the message
            if message.from_user and message.from_user.id == (await app.get_me()).id:
                await message.delete()
                return True
            else:
                return False
        elif operation == "edit":
            await message.edit_text("Operation completed.")
            return True
    except Exception as e:
        print(f"Safe message operation failed: {e}")
        return False

async def get_animation_message(action):
    return random.choice(ANIMATION_MESSAGES.get(action, ["Action completed!"]))

async def get_user_info(user_id):
    """Fetch comprehensive user profile with waifus, bank details, and reputation."""
    user = await user_collection.find_one({'id': user_id})
    tg_user = await app.get_users(user_id)

    if not user:
        return "❌ <b>User not found in the database.</b>", None, None, None

    # Count waifus per rarity
    waifu_count = {rarity: 0 for rarity in rarity_map}
    for waifu in user.get("characters", []):
        rarity = waifu.get("rarity", "🔴 Common")
        waifu_count[rarity] += 1

    # Get bank details
    balance = user.get("balance", 0)
    rubies = user.get("rubies", 0)
    gold = user.get("gold", 0)

    # Get reputation
    rep_data = await reputation_collection.find_one({'user_id': user_id})
    reputation = rep_data.get("reputation", 0) if rep_data else 0

    # Format numbers
    def format_num(num):
        try:
            return "{:,}".format(int(num))
        except (ValueError, TypeError):
            return "0"

    # Get profile photo
    profile_photo = None
    async for photo in app.get_chat_photos(user_id, limit=1):
        profile_photo = photo.file_id
        break

    username = f"@{tg_user.username}" if tg_user.username else "N/A"
    total_waifus = sum(waifu_count.values())

    # Final formatted message
    user_info = (
        f"🔰 <b>{tg_user.first_name} Info</b>\n\n"
        f"👤 <b>Name:</b> {tg_user.mention}\n"
        f"🧪 <b>Username:</b> {username}\n"
        f"🔩 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🌋 <b>Reputation:</b> {reputation}\n"
        f"👒 <b>Waifu Count:</b> {total_waifus}\n\n"
        f"☁️ <b>Seize currency:</b>\n"
        f"╭───────────────────\n"
        f"├─➩ 🧃 <b>Balance:</b> {format_num(balance)}\n"
        f"├─➩ 🍡 <b>Rubies:</b> {format_num(rubies)}\n"
        f"├─➩ ⚓ <b>Gold:</b> {format_num(gold)}\n"
        f"╰───────────────────\n\n"
        f"✳️ <b>Rarity Counts:</b>\n"
        f"╭───────────────────\n"
    )

    for rarity, count in waifu_count.items():
        if count > 0:
            user_info += f"├─➩ {rarity} {count}\n"

    user_info += f"╰───────────────────\n"
    user_info += f"\n<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"

    return user_info, user, profile_photo, total_waifus

async def send_loading_animation(chat_id, message_id=None):
    """Send loading animation before showing info"""
    loading_messages = [
        "⚡ Scanning user profile...",
        "🔍 Gathering destruction data...",
        "🛰️ Accessing user database...",
        "💻 Crunching the numbers..."
    ]
    
    loading_msg = await app.send_message(
        chat_id,
        random.choice(loading_messages)
    )
    
    # Simulate loading time
    await asyncio.sleep(1.5)
    
    if message_id:
        await app.delete_messages(chat_id, message_id)
    
    return loading_msg

async def backup_bank_data(user_id, bank_data, action_by=None):
    """Backup bank data before resetting"""
    backup_data = {
        'user_id': user_id,
        'data': bank_data,
        'backup_time': time.time(),
        'backup_type': 'bank_reset'
    }
    if action_by:
        backup_data['action_by'] = action_by
    await bank_backup_collection.insert_one(backup_data)

async def reset_user_bank(user_id, resetter_id):
    """Reset all bank-related fields to zero"""
    user = await user_collection.find_one({'id': user_id})
    if not user:
        return False

    # Backup current bank data
    bank_data = {
        'balance': user.get('balance', 0),
        'rubies': user.get('rubies', 0),
        'gold': user.get('gold', 0),
        'saved_amount': user.get('saved_amount', 0),
        'loan_amount': user.get('loan_amount', 0)
    }
    await backup_bank_data(user_id, bank_data, resetter_id)

    # Reset all values
    await user_collection.update_one(
        {'id': user_id},
        {'$set': {
            'balance': 0,
            'rubies': 0,
            'gold': 0,
            'saved_amount': 0,
            'loan_amount': 0
        }}
    )

    # Notify user
    await notify_user(
        user_id,
        f"⚠️ <b>Bank Account Reset</b> ⚠️\n\n"
        f"All your bank balances have been reset to zero by an admin.\n"
        f"If this was a mistake, please contact support."
    )

    return True

async def create_action_buttons(user_id):
    """Create main action buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Collection", callback_data=f"ask_delete_{user_id}")],
        [
            InlineKeyboardButton("½ Half Delete", callback_data=f"ask_half_delete_{user_id}"),
            InlineKeyboardButton("🔮 By Rarity", callback_data=f"delete_by_rarity_{user_id}")
        ],
        [InlineKeyboardButton("🏦 Manage Bank", callback_data=f"manage_bank_{user_id}")],
        [InlineKeyboardButton("💣 Overall Destroy", callback_data=f"ask_destroy_{user_id}")]
    ])

async def create_confirmation_buttons(user_id, action_type, item_type=None):
    """Create confirmation buttons based on action type"""
    if action_type == "delete":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_delete_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_action_{user_id}")
            ]
        ])
    elif action_type == "reset_bank":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💰 Confirm Reset", callback_data=f"confirm_reset_{item_type}_{user_id}"),
                InlineKeyboardButton("🏦 Cancel", callback_data=f"cancel_action_{user_id}")
            ]
        ])
    elif action_type == "destroy":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💣 NUKE IT ALL", callback_data=f"confirm_destroy_{user_id}"),
                InlineKeyboardButton("🚫 ABORT", callback_data=f"cancel_action_{user_id}")
            ]
        ])

async def create_bank_buttons(user_id):
    """Create bank management buttons"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Reset Balance", callback_data=f"ask_reset_balance_{user_id}"),
            InlineKeyboardButton("💎 Reset Rubies", callback_data=f"ask_reset_rubies_{user_id}")
        ],
        [
            InlineKeyboardButton("🟡 Reset Gold", callback_data=f"ask_reset_gold_{user_id}"),
            InlineKeyboardButton("💸 Reset All", callback_data=f"ask_reset_all_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=f"back_to_info_{user_id}")
        ]
    ])

async def get_backup_info(user_id):
    """Get the most recent backup information for a user"""
    # Get collection backups
    collection_backup = await backup_collection.find_one(
        {'user_id': user_id, 'backup_type': 'collection_delete'},
        sort=[('backup_time', -1)]
    )
    
    # Get bank backups
    bank_backup = await bank_backup_collection.find_one(
        {'user_id': user_id},
        sort=[('backup_time', -1)]
    )
    
    return collection_backup, bank_backup

async def create_restore_buttons(user_id, latest_backup=None):
    """Create buttons for restoration options (now supports specific backups)"""
    buttons = []
    
    # Check available backups
    collection_backup = await backup_collection.find_one(
        {'user_id': user_id},
        sort=[('backup_time', -1)]
    )
    bank_backup = await bank_backup_collection.find_one(
        {'user_id': user_id},
        sort=[('backup_time', -1)]
    )

    # Add specific backup restore (for half/rarity deletes)
    if latest_backup:
        backup_type = latest_backup.get('backup_type', '')
        if 'half_delete' in backup_type:
            buttons.append([
                InlineKeyboardButton(
                    "½ Restore Half Deleted", 
                    callback_data=f"restore_backup_{latest_backup['_id']}"
                )
            ])
        elif 'rarity_delete' in backup_type:
            rarity = backup_type.split('_')[-1]
            buttons.append([
                InlineKeyboardButton(
                    f"🔮 Restore {rarity} Waifus", 
                    callback_data=f"restore_backup_{latest_backup['_id']}"
                )
            ])

    # Standard restore options
    if collection_backup:
        buttons.append(
            [InlineKeyboardButton("🔄 Restore Full Collection", callback_data=f"restore_collection_{user_id}")]
        )
    
    if bank_backup:
        buttons.append(
            [InlineKeyboardButton("🏦 Restore Bank", callback_data=f"restore_bank_{user_id}")]
        )
    
    if collection_backup and bank_backup:
        buttons.append(
            [InlineKeyboardButton("💯 Restore Everything", callback_data=f"restore_all_{user_id}")]
        )
    
    buttons.append(
        [InlineKeyboardButton("❌ Close", callback_data=f"close_restore_{user_id}")]
    )
    
    return InlineKeyboardMarkup(buttons)

async def notify_dev_about_action(action_type, user_id, target_user_id, action_details):
    """Notify dev about destructive actions with restore options - FIXED VERSION"""
    dev_id = 7861332030  # Replace with actual dev ID
    
    # Get user info
    target_user = await app.get_users(target_user_id)
    actor_user = await app.get_users(user_id)
    
    # Get backup info (latest backup)
    backup_data = await backup_collection.find_one(
        {'user_id': target_user_id},
        sort=[('backup_time', -1)]
    )
    
    # Prepare message
    message = (
        f"⚠️ <b>ADMIN ACTION NOTIFICATION</b> ⚠️\n\n"
        f"<b>Action Type:</b> {action_type}\n"
        f"<b>Performed by:</b> {actor_user.mention} (ID: {user_id})\n"
        f"<b>Target User:</b> {target_user.mention} (ID: {target_user_id})\n\n"
        f"<b>Action Details:</b>\n{action_details}\n\n"
        f"<b>Backup Available:</b> {'✅' if backup_data else '❌'}\n"
        f"<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"
    )
    
    # Send to dev with restore options if backup exists
    try:
        if backup_data:
            buttons = await create_restore_buttons(target_user_id, latest_backup=backup_data)
            await app.send_message(dev_id, message, reply_markup=buttons)
        else:
            await app.send_message(dev_id, message)
    except Exception as e:
        print(f"Failed to notify dev: {e}")

@app.on_message(filters.command(["info", "profile"]) & sudo_filter)
async def advanced_info_command(client, message):
    """Advanced profile info with management options"""
    # Send loading animation first
    loading_msg = await send_loading_animation(message.chat.id)
    
    user_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await loading_msg.delete()
            await message.reply_text("⚠️ Invalid user ID format!")
            return

    if not user_id:
        await loading_msg.delete()
        await message.reply_text("⚠️ Reply to a user or provide a valid user ID!")
        return

    user_info, user, profile_photo, _ = await get_user_info(user_id)
    if not user:
        await loading_msg.delete()
        await message.reply_text("❌ User not found in database!")
        return

    buttons = await create_action_buttons(user_id)

    if profile_photo:
        await message.reply_photo(
            profile_photo,
            caption=user_info,
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            user_info,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    
    await loading_msg.delete()

@app.on_callback_query(filters.regex(r"^ask_delete_(\d+)$") & sudo_filter)
async def ask_delete_collection(client, callback_query):
    """Ask confirmation before deleting collection"""
    user_id = int(callback_query.matches[0].group(1))
    user_info, _, _, char_count = await get_user_info(user_id)
    
    # Edit original message
    await callback_query.message.edit_caption(
        caption=f"⚠️ <b>COLLECTION DELETE REQUEST</b> ⚠️\n\n{user_info}",
        reply_markup=None
    )
    
    # Send confirmation message
    confirm_msg = await callback_query.message.reply_text(
        f"⚠️ <b>DELETE CONFIRMATION</b> ⚠️\n\n"
        f"You are about to delete {char_count} waifus from {callback_query.message.reply_to_message.from_user.mention}'s collection!\n\n"
        f"<b>THIS ACTION CANNOT BE UNDONE!</b>",
        reply_markup=await create_confirmation_buttons(user_id, "delete")
    )
    
    # Store confirmation message ID for later deletion
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^confirm_delete_(\d+)$") & sudo_filter)
async def confirm_delete_collection(client, callback_query):
    """Confirm and delete the waifu collection"""
    user_id = int(callback_query.matches[0].group(1))
    deleter_id = callback_query.from_user.id
    
    # Delete confirmation message
    await callback_query.message.delete()
    
    # Backup before deletion
    user = await user_collection.find_one({'id': user_id})
    char_count = 0
    if user and "characters" in user:
        char_count = len(user['characters'])
        await backup_collection.insert_one({
            'user_id': user_id,
            'characters': user['characters'],
            'backup_time': time.time(),
            'backup_type': 'collection_delete',
            'action_by': deleter_id
        })
    
    # Perform deletion
    result = await user_collection.update_one(
        {'id': user_id},
        {'$set': {'characters': []}}
    )
    
    if result.modified_count > 0:
        # Notify user
        await notify_user(
            user_id,
            f"💢 <b>COLLECTION DELETED</b> 💢\n\n"
            f"Your entire waifu collection ({char_count} waifus) has been deleted by an admin.\n"
            f"Contact support if this was a mistake."
        )
        
        # Send success message
        success_msg = await callback_query.message.reply_to_message.reply_text(
            f"✅ <b>Collection Deleted Successfully</b>\n\n"
            f"Successfully deleted {char_count} waifus from user <code>{user_id}</code>.\n"
            f"{await get_animation_message('delete')}"
        )
        
        # Notify dev
        await notify_dev_about_action(
            "Collection Delete",
            deleter_id,
            user_id,
            f"Deleted {char_count} waifus from collection"
        )
    else:
        await callback_query.message.reply_to_message.reply_text(
            "❌ Failed to delete collection. User may not have any waifus."
        )

@app.on_callback_query(filters.regex(r"^manage_bank_(\d+)$") & sudo_filter)
async def manage_bank_options(client, callback_query):
    """Show bank management options"""
    user_id = int(callback_query.matches[0].group(1))
    user_info, _, _, _ = await get_user_info(user_id)
    
    # Edit original message
    await callback_query.message.edit_caption(
        caption=f"🏦 <b>BANK MANAGEMENT PANEL</b> 🏦\n\n{user_info}",
        reply_markup=await create_bank_buttons(user_id)
    )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^ask_reset_(balance|rubies|gold|all)_(\d+)$") & sudo_filter)
async def ask_reset_bank_item(client, callback_query):
    """Ask confirmation before resetting bank items"""
    item_type = callback_query.matches[0].group(1)
    user_id = int(callback_query.matches[0].group(2))
    user = await user_collection.find_one({'id': user_id})
    
    if not user:
        await callback_query.answer("❌ User not found!")
        return
    
    # Get current value
    if item_type == "all":
        current_value = f"Balance: {user.get('balance', 0)}\nRubies: {user.get('rubies', 0)}\nGold: {user.get('gold', 0)}"
    else:
        current_value = user.get(item_type, 0)
    
    # Delete the button message
    await callback_query.message.delete()
    
    # Send confirmation message
    confirm_msg = await callback_query.message.reply_to_message.reply_text(
        f"⚠️ <b>BANK RESET CONFIRMATION</b> ⚠️\n\n"
        f"You are about to reset {'ALL BANK ITEMS' if item_type == 'all' else item_type.upper()} "
        f"for {callback_query.message.reply_to_message.from_user.mention}!\n\n"
        f"Current value{'s' if item_type == 'all' else ''}:\n"
        f"{current_value}\n\n"
        f"<b>THIS WILL SET THE VALUE TO ZERO!</b>",
        reply_markup=await create_confirmation_buttons(user_id, "reset_bank", item_type)
    )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^confirm_reset_(balance|rubies|gold|all)_(\d+)$") & sudo_filter)
async def confirm_reset_bank_item(client, callback_query):
    """Confirm and reset specific bank item"""
    item_type = callback_query.matches[0].group(1)
    user_id = int(callback_query.matches[0].group(2))
    resetter_id = callback_query.from_user.id
    
    # Delete confirmation message
    await callback_query.message.delete()
    
    # Backup current value
    user = await user_collection.find_one({'id': user_id})
    if user:
        if item_type == "all":
            backup_data = {
                'balance': user.get('balance', 0),
                'rubies': user.get('rubies', 0),
                'gold': user.get('gold', 0)
            }
            await bank_backup_collection.insert_one({
                'user_id': user_id,
                'data': backup_data,
                'backup_time': time.time(),
                'backup_type': 'full_bank_reset',
                'action_by': resetter_id
            })
        else:
            await bank_backup_collection.insert_one({
                'user_id': user_id,
                'item_type': item_type,
                'previous_value': user.get(item_type, 0),
                'backup_time': time.time(),
                'action_by': resetter_id
            })
    
    # Perform reset
    if item_type == "all":
        update_data = {
            'balance': 0,
            'rubies': 0,
            'gold': 0
        }
    else:
        update_data = {item_type: 0}
    
    result = await user_collection.update_one(
        {'id': user_id},
        {'$set': update_data}
    )
    
    if result.modified_count > 0:
        # Notify user
        await notify_user(
            user_id,
            f"💸 <b>BANK RESET COMPLETE</b> 💸\n\n"
            f"Your {'entire bank account' if item_type == 'all' else item_type} "
            f"has been reset to zero by an admin.\n"
            f"Contact support if this was unintended."
        )
        
        # Send success message
        success_msg = await callback_query.message.reply_to_message.reply_text(
            f"✅ <b>Bank Reset Successful</b>\n\n"
            f"Successfully reset {'all bank items' if item_type == 'all' else item_type} "
            f"for user <code>{user_id}</code>.\n"
            f"{await get_animation_message('bank_reset')}"
        )
        
        # Notify dev
        await notify_dev_about_action(
            "Bank Reset",
            resetter_id,
            user_id,
            f"Reset {'all bank items' if item_type == 'all' else item_type}"
        )
    else:
        await callback_query.message.reply_to_message.reply_text(
            f"❌ Failed to reset {'bank items' if item_type == 'all' else item_type}."
        )

@app.on_callback_query(filters.regex(r"^ask_destroy_(\d+)$") & sudo_filter)
async def ask_destroy_all(client, callback_query):
    """Ask confirmation before destroying everything"""
    user_id = int(callback_query.matches[0].group(1))
    user_info, user, _, char_count = await get_user_info(user_id)
    
    if not user:
        await callback_query.answer("❌ User not found!")
        return
    
    # Get current values
    balance = user.get('balance', 0)
    rubies = user.get('rubies', 0)
    gold = user.get('gold', 0)
    
    # Delete the button message
    await callback_query.message.delete()
    
    # Send confirmation message
    confirm_msg = await callback_query.message.reply_to_message.reply_text(
        f"☢️ <b>COMPLETE DESTRUCTION CONFIRMATION</b> ☢️\n\n"
        f"You are about to NUKE EVERYTHING for {callback_query.message.reply_to_message.from_user.mention}!\n\n"
        f"<b>This will delete:</b>\n"
        f"- {char_count} waifus\n"
        f"- Balance: {balance}\n"
        f"- Rubies: {rubies}\n"
        f"- Gold: {gold}\n\n"
        f"<b>THIS IS THE POINT OF NO RETURN!</b>",
        reply_markup=await create_confirmation_buttons(user_id, "destroy")
    )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^confirm_destroy_(\d+)$") & sudo_filter)
async def confirm_destroy_all(client, callback_query):
    """Confirm and destroy everything"""
    user_id = int(callback_query.matches[0].group(1))
    destroyer_id = callback_query.from_user.id
    
    # Delete confirmation message
    await callback_query.message.delete()
    
    # Backup everything first
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await callback_query.answer("❌ User not found!")
        return
    
    char_count = len(user.get('characters', []))
    balance = user.get('balance', 0)
    rubies = user.get('rubies', 0)
    gold = user.get('gold', 0)
    
    # Backup collection
    if char_count > 0:
        await backup_collection.insert_one({
            'user_id': user_id,
            'characters': user['characters'],
            'backup_time': time.time(),
            'backup_type': 'collection_delete',
            'action_by': destroyer_id
        })
    
    # Backup bank
    await bank_backup_collection.insert_one({
        'user_id': user_id,
        'data': {
            'balance': balance,
            'rubies': rubies,
            'gold': gold
        },
        'backup_time': time.time(),
        'backup_type': 'full_destruction',
        'action_by': destroyer_id
    })
    
    # Perform destruction
    result = await user_collection.update_one(
        {'id': user_id},
        {'$set': {
            'characters': [],
            'balance': 0,
            'rubies': 0,
            'gold': 0
        }}
    )
    
    if result.modified_count > 0:
        # Notify user
        await notify_user(
            user_id,
            f"💀 <b>ACCOUNT WIPED</b> 💀\n\n"
            f"Your entire account has been reset by an admin:\n"
            f"- {char_count} waifus deleted\n"
            f"- Balance reset from {balance} to 0\n"
            f"- Rubies reset from {rubies} to 0\n"
            f"- Gold reset from {gold} to 0\n\n"
            f"Contact support if this was a mistake."
        )
        
        # Send success message
        success_msg = await callback_query.message.reply_to_message.reply_text(
            f"💣 <b>DESTRUCTION COMPLETE</b> 💣\n\n"
            f"Successfully nuked everything for user <code>{user_id}</code>:\n"
            f"- Deleted {char_count} waifus\n"
            f"- Reset balance: {balance} → 0\n"
            f"- Reset rubies: {rubies} → 0\n"
            f"- Reset gold: {gold} → 0\n\n"
            f"{await get_animation_message('destroy')}"
        )
        
        # Notify dev
        await notify_dev_about_action(
            "Full Destruction",
            destroyer_id,
            user_id,
            f"Destroyed everything:\n"
            f"- {char_count} waifus\n"
            f"- Balance: {balance}\n"
            f"- Rubies: {rubies}\n"
            f"- Gold: {gold}"
        )
    else:
        await callback_query.message.reply_to_message.reply_text(
            "❌ Failed to destroy account. No changes made."
        )

@app.on_callback_query(filters.regex(r"^cancel_action_(\d+)$"))
async def cancel_action(client, callback_query):
    """Cancel any pending destructive action"""
    user_id = int(callback_query.matches[0].group(1))
    
    # Delete confirmation message
    await callback_query.message.delete()
    
    # Send cancellation message
    await callback_query.message.reply_to_message.reply_text(
        f"🛑 <b>DESTRUCTION ABORTED</b> 🛑\n\n"
        f"No changes were made to user <code>{user_id}</code>.\n"
        f"{await get_animation_message('cancel')}"
    )

@app.on_callback_query(filters.regex(r"^back_to_info_(\d+)$"))
async def back_to_info(client, callback_query):
    """Return to the main info view"""
    user_id = int(callback_query.matches[0].group(1))
    user_info, _, profile_photo, _ = await get_user_info(user_id)
    
    buttons = await create_action_buttons(user_id)
    
    if profile_photo:
        # For media messages, we need to use InputMediaPhoto with caption
        await callback_query.message.edit_media(
            media=InputMediaPhoto(
                media=profile_photo,
                caption=user_info
            ),
            reply_markup=buttons
        )
    else:
        # For text messages, just edit the caption
        await callback_query.message.edit_text(
            text=user_info,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^restore_(collection|bank|all)_(\d+)$") & dev_filter)
async def restore_user_data(client, callback_query):
    """Restore user data from backup (Dev only) - FIXED VERSION"""
    action_type = callback_query.matches[0].group(1)
    user_id = int(callback_query.matches[0].group(2))
    
    # Safely delete the restore message - only if we sent it
    try:
        # Check if the message was sent by the bot
        if callback_query.message and callback_query.message.from_user:
            if callback_query.message.from_user.id == (await client.get_me()).id:
                await callback_query.message.delete()
            else:
                # Just edit the message if we can't delete it
                await callback_query.message.edit_text("🔄 Processing restoration...")
        else:
            # If we can't determine the sender, just proceed without deletion
            pass
    except Exception as e:
        print(f"Message deletion/editing failed: {e}. Continuing with restoration...")
    
    success = False
    details = ""
    restored_items = []
    
    if action_type in ["collection", "all"]:
        # Restore collection
        collection_backup = await backup_collection.find_one(
            {'user_id': user_id, 'backup_type': 'collection_delete'},
            sort=[('backup_time', -1)]
        )
        
        if collection_backup:
            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'characters': collection_backup['characters']}}
            )
            if result.modified_count > 0:
                char_count = len(collection_backup['characters'])
                details += f"✅ Restored {char_count} waifus\n"
                restored_items.append(f"{char_count} waifus")
                success = True
            else:
                details += f"❌ Failed to restore collection\n"
        else:
            details += f"❌ No collection backup found\n"
    
    if action_type in ["bank", "all"]:
        # Restore bank
        bank_backup = await bank_backup_collection.find_one(
            {'user_id': user_id},
            sort=[('backup_time', -1)]
        )
        
        if bank_backup:
            if 'data' in bank_backup:  # Full bank backup
                result = await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {
                        'balance': bank_backup['data'].get('balance', 0),
                        'rubies': bank_backup['data'].get('rubies', 0),
                        'gold': bank_backup['data'].get('gold', 0)
                    }}
                )
                if result.modified_count > 0:
                    bank_details = (
                        f"✅ Restored bank:\n"
                        f"   • Balance: {bank_backup['data'].get('balance', 0)}\n"
                        f"   • Rubies: {bank_backup['data'].get('rubies', 0)}\n"
                        f"   • Gold: {bank_backup['data'].get('gold', 0)}\n"
                    )
                    details += bank_details
                    restored_items.append("bank data")
                    success = True
                else:
                    details += f"❌ Failed to restore bank data\n"
            elif 'item_type' in bank_backup:  # Single item backup
                result = await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {
                        bank_backup['item_type']: bank_backup['previous_value']
                    }}
                )
                if result.modified_count > 0:
                    item_details = f"✅ Restored {bank_backup['item_type']}: {bank_backup['previous_value']}\n"
                    details += item_details
                    restored_items.append(f"{bank_backup['item_type']}")
                    success = True
                else:
                    details += f"❌ Failed to restore {bank_backup['item_type']}\n"
        else:
            details += f"❌ No bank backup found\n"
    
    # Prepare response message
    if success:
        # Notify user
        await notify_user(
            user_id,
            f"✨ <b>ACCOUNT RESTORED</b> ✨\n\n"
            f"Your account data has been restored by a developer:\n\n"
            f"{details}\n"
            f"Contact support if you have any questions."
        )
        
        # Send success message - reply to original command message
        success_message = (
            f"✅ <b>Restoration Complete</b>\n\n"
            f"Successfully restored data for user <code>{user_id}</code>:\n\n"
            f"{details}\n"
            f"{await get_animation_message('restore')}"
        )
        
        # Try to reply to the original message, fallback to current chat
        try:
            if hasattr(callback_query.message, 'reply_to_message') and callback_query.message.reply_to_message:
                await callback_query.message.reply_to_message.reply_text(success_message)
            else:
                await callback_query.message.reply_text(success_message)
        except Exception as e:
            # Final fallback - send to current chat
            await client.send_message(
                callback_query.message.chat.id,
                success_message
            )
    else:
        # Send failure message
        error_message = f"❌ Failed to restore {action_type} for user <code>{user_id}</code>.\n\n{details}"
        try:
            await callback_query.message.reply_text(error_message)
        except Exception as e:
            await client.send_message(
                callback_query.message.chat.id,
                error_message
            )
    
    # Always answer the callback query to remove loading state
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^close_restore_(\d+)$") & dev_filter)
async def close_restore_menu(client, callback_query):
    """Close the restore menu (Dev only)"""
    await callback_query.message.delete()
    await callback_query.answer("Restore menu closed")

async def notify_user(user_id, message):
    """Send a notification to the user"""
    try:
        await app.send_message(user_id, message)
    except Exception as e:
        print(f"Failed to notify user {user_id}: {e}")

@app.on_callback_query(filters.regex(r"^ask_half_delete_(\d+)$") & sudo_filter)
async def ask_half_delete(client, callback_query):
    """Ask confirmation before deleting half collection"""
    user_id = int(callback_query.matches[0].group(1))
    user_info, user, _, char_count = await get_user_info(user_id)
    
    if not user or char_count == 0:
        await callback_query.answer("❌ User has no waifus to delete!")
        return
    
    half_count = char_count // 2
    remaining = char_count - half_count
    
    # Edit original message
    await callback_query.message.edit_caption(
        caption=f"⚠️ <b>HALF DELETE CONFIRMATION</b> ⚠️\n\n{user_info}",
        reply_markup=None
    )
    
    # Send confirmation message
    confirm_msg = await callback_query.message.reply_text(
        f"🔪 <b>HALF DELETE REQUEST</b> 🔪\n\n"
        f"You are about to randomly delete <b>{half_count} waifus</b> from this user's collection!\n"
        f"After deletion, they will have <b>{remaining} waifus</b> remaining.\n\n"
        f"<b>This action cannot be undone!</b>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_half_delete_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_action_{user_id}")
            ]
        ])
    )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^confirm_half_delete_(\d+)$") & sudo_filter)
async def confirm_half_delete(client, callback_query):
    """Delete half of the user's waifus randomly"""
    user_id = int(callback_query.matches[0].group(1))
    deleter_id = callback_query.from_user.id
    
    # Delete confirmation message
    await callback_query.message.delete()
    
    # Fetch user data
    user = await user_collection.find_one({'id': user_id})
    if not user or "characters" not in user:
        await callback_query.answer("❌ User has no waifus to delete!")
        return
    
    characters = user["characters"]
    char_count = len(characters)
    half_count = char_count // 2
    
    # Backup before deletion
    await backup_collection.insert_one({
        'user_id': user_id,
        'characters': characters,
        'backup_time': time.time(),
        'backup_type': 'half_delete',
        'action_by': deleter_id
    })
    
    # Randomly select waifus to delete
    deleted_waifus = random.sample(characters, half_count)
    remaining_waifus = [w for w in characters if w not in deleted_waifus]
    
    # Update database
    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'characters': remaining_waifus}}
    )
    
    # Notify user
    await notify_user(
        user_id,
        f"✂️ <b>HALF COLLECTION DELETED</b> ✂️\n\n"
        f"An admin randomly deleted <b>{half_count} waifus</b> from your collection!\n"
        f"You now have <b>{len(remaining_waifus)} waifus</b> remaining.\n\n"
        f"Contact support if this was a mistake."
    )
    
    # Send success message
    await callback_query.message.reply_to_message.reply_text(
        f"✅ <b>Half Delete Successful</b>\n\n"
        f"Deleted <b>{half_count} waifus</b> from <code>{user_id}</code>'s collection.\n"
        f"They now have <b>{len(remaining_waifus)} waifus</b> left."
    )
    
    # Notify dev
    await notify_dev_about_action(
        "Half Collection Delete",
        deleter_id,
        user_id,
        f"Deleted {half_count}/{char_count} waifus randomly"
    )

@app.on_callback_query(filters.regex(r"^delete_by_rarity_(\d+)$") & sudo_filter)
async def delete_by_rarity_menu(client, callback_query):
    user_id = int(callback_query.matches[0].group(1))
    
    # Generate buttons for all rarities
    buttons = []
    for rarity, emoji in rarity_map.items():
        safe_rarity = rarity.replace(" ", "_")  # Convert "Limited Edition" → "Limited_Edition"
        buttons.append(
            InlineKeyboardButton(
                f"{emoji} {rarity.split()[0]}",
                callback_data=f"raritydel_ask_{safe_rarity}_{user_id}"
            )
        )
    
    # Split into rows of 3 buttons
    chunked = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    chunked.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_to_info_{user_id}")])
    
    await callback_query.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(chunked)
    )
    await callback_query.answer("Select a rarity to delete")

@app.on_callback_query(filters.regex(r"^raritydel_ask_(.+)_(\d+)$") & sudo_filter)
async def ask_rarity_delete_confirmation(client, callback_query):
    rarity_encoded = callback_query.matches[0].group(1)
    user_id = int(callback_query.matches[0].group(2))
    original_rarity = rarity_encoded.replace("_", " ")  # Convert back to "Limited Edition"
    
    # Count waifus of this rarity
    user = await user_collection.find_one({'id': user_id})
    count = len([w for w in user.get("characters", []) if w.get("rarity") == original_rarity])
    
    await callback_query.message.edit_text(
        f"⚠️ Delete ALL {original_rarity} waifus?\n"
        f"• Quantity: {count}\n"
        f"• User ID: {user_id}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💀 CONFIRM", 
                    callback_data=f"raritydel_confirm_{rarity_encoded}_{user_id}"),
                InlineKeyboardButton("❌ CANCEL", 
                    callback_data=f"raritydel_cancel_{user_id}")
            ]
        ])
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^raritydel_confirm_(.+)_(\d+)$") & sudo_filter)
async def execute_rarity_delete(client, callback_query):
    rarity_encoded = callback_query.matches[0].group(1)
    user_id = int(callback_query.matches[0].group(2))
    original_rarity = rarity_encoded.replace("_", " ")
    
    # Delete all waifus of this rarity
    result = await user_collection.update_one(
        {'id': user_id},
        {'$pull': {'characters': {'rarity': original_rarity}}}
    )
    
    if result.modified_count > 0:
        # Backup deleted waifus
        deleted = [w for w in (await user_collection.find_one({'id': user_id}))["characters"] if w["rarity"] == original_rarity]
        await backup_collection.insert_one({
            'user_id': user_id,
            'characters': deleted,
            'backup_time': time.time(),
            'backup_type': f'rarity_delete_{original_rarity}'
        })
        
        await callback_query.message.edit_text(
            f"✅ Deleted all {original_rarity} waifus!\n"
            f"User ID: {user_id}"
        )
    else:
        await callback_query.message.edit_text("❌ No waifus were deleted")
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^raritydel_cancel_(\d+)$") & sudo_filter)
async def cancel_rarity_delete(client, callback_query):
    user_id = int(callback_query.matches[0].group(1))
    await callback_query.message.delete()
    await callback_query.answer("Cancelled rarity deletion")

@app.on_callback_query(filters.regex(r"^restore_backup_(.+)$") & dev_filter)
async def restore_waifu_backup(client, callback_query):
    """Restore deleted waifus from backup (Dev only)"""
    backup_id = callback_query.matches[0].group(1)
    
    # Fetch backup data
    backup = await backup_collection.find_one({'_id': ObjectId(backup_id)})
    if not backup:
        await callback_query.answer("❌ Backup not found!")
        return
    
    user_id = backup['user_id']
    deleted_waifus = backup.get('characters', [])
    
    # Fetch current user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await callback_query.answer("❌ User not found!")
        return
    
    # Merge deleted waifus back into collection
    current_waifus = user.get('characters', [])
    restored_waifus = current_waifus + deleted_waifus
    
    # Update database
    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'characters': restored_waifus}}
    )
    
    # Delete backup to prevent duplicate restores
    await backup_collection.delete_one({'_id': ObjectId(backup_id)})
    
    # Notify dev
    await callback_query.message.edit_text(
        f"✅ <b>RESTORE SUCCESSFUL</b>\n\n"
        f"Restored <b>{len(deleted_waifus)} waifus</b> to "
        f"<a href='tg://user?id={user_id}'>{user_id}</a>'s collection.\n"
        f"Total waifus now: <b>{len(restored_waifus)}</b>"
    )
    
    # Notify user
    await notify_user(
        user_id,
        f"✨ <b>WAIFUS RESTORED</b> ✨\n\n"
        f"A developer restored <b>{len(deleted_waifus)} waifus</b> to your collection!\n"
        f"You now have <b>{len(restored_waifus)} waifus</b> in total."
    )
    
    await callback_query.answer()
