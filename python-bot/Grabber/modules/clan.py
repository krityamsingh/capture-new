from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto,
    InputMediaVideo
)
from asyncio import sleep
import random
import string
from datetime import datetime, timedelta
from . import app, collection, user_collection, ac, clan_war_collection, clan_collection
import re

# Tiny caps font style with anime touch (for consistency)
tiny_font = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    ' ': ' '
}

def convert_to_tiny(text):
    return ''.join(tiny_font.get(c.lower(), c) for c in text)

# Generate random clan ID
def generate_clan_id(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Clan roles
CLAN_ROLES = {
    "hokage": "🔥 Hokage",
    "chunin": "⚔️ Chunin",
    "genin": "🌀 Genin",
    "low_ninja": "🌱 Low Ninja"
}

# Clan ranks based on level
CLAN_RANKS = {
    1: "🌱 Rookie",
    2: "🌿 Apprentice",
    3: "🌀 Genin Clan",
    4: "⚔️ Chunin Clan",
    5: "🔥 Elite Clan",
    6: "✨ Master Clan",
    7: "🌟 Supreme Clan",
    8: "💫 Legendary Clan",
    9: "👑 Imperial Clan",
    10: "🌌 Divine Clan"
}

# Create Clan Command
@app.on_message(filters.command("createclan"))
async def create_clan(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_mention = message.from_user.mention
    
    # Check if user already has a clan
    existing_clan = await clan_collection.find_one({"owner_id": user_id})
    if existing_clan:
        return await message.reply_text(
            f"**⚠️ You already own a clan!**\n"
            f"**Clan Name:** {existing_clan['name']}\n"
            f"**Clan ID:** `{existing_clan['clan_id']}`\n\n"
            f"Use /myclan to view your clan details."
        )
    
    # Check if user is in any clan
    user_in_clan = await clan_collection.find_one({"members": {"$elemMatch": {"user_id": user_id}}})
    if user_in_clan:
        return await message.reply_text(
            f"**⚠️ You are already a member of a clan!**\n"
            f"**Clan Name:** {user_in_clan['name']}\n"
            f"**Clan ID:** `{user_in_clan['clan_id']}`\n\n"
            f"You must leave your current clan first to create a new one."
        )
    
    # Get clan name from command
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "**⚠️ Please provide a clan name!**\n"
            "**Usage:** /createclan <clan_name>"
        )
    
    clan_name = " ".join(args[1:])
    
    # Validate clan name length
    if len(clan_name) > 32:
        return await message.reply_text(
            "**⚠️ Clan name is too long!**\n"
            "Maximum 32 characters allowed."
        )
    
    # Check if clan name already exists
    existing_name = await clan_collection.find_one({"name": clan_name})
    if existing_name:
        return await message.reply_text(
            "**⚠️ Clan name already taken!**\n"
            "Please choose a different name."
        )
    
    # Generate unique clan ID
    clan_id = generate_clan_id()
    while await clan_collection.find_one({"clan_id": clan_id}):
        clan_id = generate_clan_id()
    
    # Create clan document
    clan_data = {
        "clan_id": clan_id,
        "name": clan_name,
        "owner_id": user_id,
        "owner_name": user_name,
        "owner_mention": user_mention,
        "members": [
            {
                "user_id": user_id,
                "user_name": user_name,
                "user_mention": user_mention,
                "role": "🔥 Hokage",
                "joined_at": datetime.now()
            }
        ],
        "member_count": 1,
        "max_members": 20,
        "level": 1,
        "rank": CLAN_RANKS[1],
        "wins": 0,
        "losses": 0,
        "clan_pfp": None,
        "created_at": datetime.now()
    }
    
    # Insert clan into database
    await clan_collection.insert_one(clan_data)
    
    await message.reply_text(
        f"**🎉 Clan Created Successfully!**\n\n"
        f"**🏮 Clan Name:** {clan_name}\n"
        f"**🆔 Clan ID:** `{clan_id}`\n"
        f"**👑 Owner:** {user_mention}\n"
        f"**👥 Members:** 1/20\n"
        f"**✨ Level:** 1\n"
        f"**🏆 Rank:** {CLAN_RANKS[1]}\n\n"
        f"Share your clan ID with others to let them join!\n"
        f"Use /myclan to view your clan details."
    )

# Join Clan Command
@app.on_message(filters.command("joinclan"))
async def join_clan(client: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_mention = message.from_user.mention
    
    # Check if user already owns a clan
    existing_clan = await clan_collection.find_one({"owner_id": user_id})
    if existing_clan:
        return await message.reply_text(
            f"**⚠️ You already own a clan!**\n"
            f"**Clan Name:** {existing_clan['name']}\n"
            f"**Clan ID:** `{existing_clan['clan_id']}`\n\n"
            f"You cannot join another clan while owning one."
        )
    
    # Check if user is already in a clan
    user_in_clan = await clan_collection.find_one({"members": {"$elemMatch": {"user_id": user_id}}})
    if user_in_clan:
        return await message.reply_text(
            f"**⚠️ You are already in a clan!**\n"
            f"**Clan Name:** {user_in_clan['name']}\n"
            f"**Clan ID:** `{user_in_clan['clan_id']}`\n\n"
            f"You must leave your current clan first to join a new one."
        )
    
    # Get clan ID from command
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "**⚠️ Please provide a clan ID!**\n"
            "**Usage:** /joinclan <clan_id>"
        )
    
    clan_id = args[1].upper()
    
    # Find clan by ID
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        return await message.reply_text(
            "**⚠️ Clan not found!**\n"
            "Please check the clan ID and try again."
        )
    
    # Check if clan is full
    if clan["member_count"] >= clan["max_members"]:
        return await message.reply_text(
            f"**⚠️ Clan is full!**\n"
            f"**Clan Name:** {clan['name']}\n"
            f"**Members:** {clan['member_count']}/{clan['max_members']}\n\n"
            f"This clan has reached its maximum member limit."
        )
    
    # Send join request to clan owner
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept_join:{user_id}:{clan_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_join:{user_id}:{clan_id}")
        ]
    ])
    
    try:
        await client.send_message(
            clan["owner_id"],
            f"**📨 New Clan Join Request!**\n\n"
            f"**👤 User:** {user_mention}\n"
            f"**🆔 User ID:** `{user_id}`\n"
            f"**🏮 Clan:** {clan['name']}\n"
            f"**🆔 Clan ID:** `{clan_id}`\n\n"
            f"Do you want to accept this user into your clan?",
            reply_markup=keyboard
        )
        
        await message.reply_text(
            f"**✅ Join request sent!**\n\n"
            f"**🏮 Clan:** {clan['name']}\n"
            f"**👑 Owner:** {clan['owner_mention']}\n\n"
            f"The clan owner will review your request shortly."
        )
    except Exception as e:
        await message.reply_text(
            "**⚠️ Could not send join request!**\n"
            "The clan owner might have privacy settings that prevent messages."
        )

# Handle join request callback
@app.on_callback_query(filters.regex(r"^accept_join:"))
async def accept_join_request(client: Client, callback: CallbackQuery):
    data = callback.data.split(":")
    requester_id = int(data[1])
    clan_id = data[2]
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if callback is from clan owner
    if callback.from_user.id != clan["owner_id"]:
        await callback.answer("Only the clan owner can accept requests!", show_alert=True)
        return
    
    # Check if user is already in a clan
    user_in_clan = await clan_collection.find_one({"members": {"$elemMatch": {"user_id": requester_id}}})
    if user_in_clan:
        await callback.answer("User is already in a clan!", show_alert=True)
        return
    
    # Check if clan is full
    if clan["member_count"] >= clan["max_members"]:
        await callback.answer("Clan is full!", show_alert=True)
        return
    
    # Get user info
    try:
        user = await client.get_users(requester_id)
        user_name = user.first_name
        user_mention = user.mention()
    except:
        user_name = "Unknown"
        user_mention = "Unknown"
    
    # Add user to clan
    new_member = {
        "user_id": requester_id,
        "user_name": user_name,
        "user_mention": user_mention,
        "role": "🌱 Low Ninja",
        "joined_at": datetime.now()
    }
    
    await clan_collection.update_one(
        {"clan_id": clan_id},
        {
            "$push": {"members": new_member},
            "$inc": {"member_count": 1}
        }
    )
    
    # Notify user
    try:
        await client.send_message(
            requester_id,
            f"**🎉 Your join request has been accepted!**\n\n"
            f"**🏮 Clan:** {clan['name']}\n"
            f"**👑 Owner:** {clan['owner_mention']}\n"
            f"**👥 Members:** {clan['member_count'] + 1}/{clan['max_members']}\n\n"
            f"Use /myclan to view your clan details."
        )
    except:
        pass
    
    await callback.edit_message_text(
        f"**✅ User accepted into clan!**\n\n"
        f"**👤 User:** {user_mention}\n"
        f"**🏮 Clan:** {clan['name']}\n"
        f"**👥 Members:** {clan['member_count'] + 1}/{clan['max_members']}"
    )
    
    await callback.answer(f"{user_name} has joined the clan!")

@app.on_callback_query(filters.regex(r"^reject_join:"))
async def reject_join_request(client: Client, callback: CallbackQuery):
    data = callback.data.split(":")
    requester_id = int(data[1])
    clan_id = data[2]
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if callback is from clan owner
    if callback.from_user.id != clan["owner_id"]:
        await callback.answer("Only the clan owner can reject requests!", show_alert=True)
        return
    
    # Get user info
    try:
        user = await client.get_users(requester_id)
        user_name = user.first_name
        user_mention = user.mention()
    except:
        user_name = "Unknown"
        user_mention = "Unknown"
    
    # Notify user
    try:
        await client.send_message(
            requester_id,
            f"**❌ Your join request has been rejected!**\n\n"
            f"**🏮 Clan:** {clan['name']}\n"
            f"**👑 Owner:** {clan['owner_mention']}\n\n"
            f"You can try joining another clan."
        )
    except:
        pass
    
    await callback.edit_message_text(
        f"**❌ Join request rejected!**\n\n"
        f"**👤 User:** {user_mention}\n"
        f"**🏮 Clan:** {clan['name']}"
    )
    
    await callback.answer(f"{user_name}'s request was rejected")

# My Clan Command
@app.on_message(filters.command("myclan"))
async def my_clan(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Find user's clan
    clan = await clan_collection.find_one({
        "$or": [
            {"owner_id": user_id},
            {"members": {"$elemMatch": {"user_id": user_id}}}
        ]
    })
    
    if not clan:
        return await message.reply_text(
            "**⚠️ You are not in any clan!**\n\n"
            "Create your own clan with /createclan or join one with /joinclan"
        )
    
    # Check if user is owner
    is_owner = user_id == clan["owner_id"]
    
    # Prepare buttons
    buttons = []
    if is_owner:
        buttons.append([InlineKeyboardButton("🗑️ Delete Clan", callback_data=f"delete_clan:{clan['clan_id']}")])
    else:
        buttons.append([InlineKeyboardButton("👋 Leave Clan", callback_data=f"leave_clan:{clan['clan_id']}")])
    
    buttons.append([InlineKeyboardButton("👥 View Members", callback_data=f"view_members:{clan['clan_id']}:1")])
    
    # Add clan pfp if exists
    caption = (
        f"**🏮 Clan: {clan['name']}**\n"
        f"**🆔 Clan ID:** `{clan['clan_id']}`\n"
        f"**👑 Owner:** {clan['owner_mention']}\n"
        f"**👥 Members:** {clan['member_count']}/{clan['max_members']}\n"
        f"**✨ Level:** {clan['level']}\n"
        f"**🏆 Rank:** {clan['rank']}\n"
        f"**✅ Wins:** {clan['wins']}\n"
        f"**❌ Losses:** {clan['losses']}\n\n"
        f"**Share your clan ID to invite others!**"
    )
    
    if clan.get("clan_pfp"):
        try:
            await message.reply_photo(
                clan["clan_pfp"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        except:
            pass
    
    await message.reply_text(
        caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Handle myclan callbacks
@app.on_callback_query(filters.regex(r"^view_members:"))
async def view_clan_members(client: Client, callback: CallbackQuery):
    data = callback.data.split(":")
    clan_id = data[1]
    page = int(data[2])
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if user is in this clan
    user_in_clan = any(member["user_id"] == callback.from_user.id for member in clan["members"])
    if not user_in_clan:
        await callback.answer("You are not a member of this clan!", show_alert=True)
        return
    
    # Paginate members (10 per page)
    members_per_page = 10
    total_pages = (len(clan["members"]) + members_per_page - 1) // members_per_page
    
    if page < 1 or page > total_pages:
        await callback.answer("Invalid page!", show_alert=True)
        return
    
    start_idx = (page - 1) * members_per_page
    end_idx = min(start_idx + members_per_page, len(clan["members"]))
    
    # Format members list
    members_text = ""
    for i, member in enumerate(clan["members"][start_idx:end_idx], start=start_idx + 1):
        members_text += f"{i}. {member['user_mention']} - {member['role']}\n"
    
    # Create navigation buttons
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"view_members:{clan_id}:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"view_members:{clan_id}:{page+1}"))
    
    if buttons:
        navigation_row = [buttons[0]]
        if len(buttons) > 1:
            navigation_row.append(buttons[1])
        keyboard = InlineKeyboardMarkup([navigation_row])
    else:
        keyboard = None
    
    await callback.edit_message_text(
        f"**👥 Members of {clan['name']}**\n"
        f"**Page {page}/{total_pages}**\n\n"
        f"{members_text}",
        reply_markup=keyboard
    )
    
    await callback.answer()

@app.on_callback_query(filters.regex(r"^leave_clan:"))
async def leave_clan(client: Client, callback: CallbackQuery):
    clan_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if user is the owner
    if user_id == clan["owner_id"]:
        await callback.answer("Owners cannot leave their clan! Use /deleteclan instead.", show_alert=True)
        return
    
    # Check if user is in this clan
    user_in_clan = any(member["user_id"] == user_id for member in clan["members"])
    if not user_in_clan:
        await callback.answer("You are not a member of this clan!", show_alert=True)
        return
    
    # Remove user from clan
    await clan_collection.update_one(
        {"clan_id": clan_id},
        {
            "$pull": {"members": {"user_id": user_id}},
            "$inc": {"member_count": -1}
        }
    )
    
    await callback.edit_message_text(
        f"**👋 You have left {clan['name']}**\n\n"
        f"You are no longer a member of this clan."
    )
    
    await callback.answer("You have left the clan")

@app.on_callback_query(filters.regex(r"^delete_clan:"))
async def delete_clan(client: Client, callback: CallbackQuery):
    clan_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if user is the owner
    if user_id != clan["owner_id"]:
        await callback.answer("Only the clan owner can delete the clan!", show_alert=True)
        return
    
    # Confirm deletion
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete:{clan_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_delete:{clan_id}")
        ]
    ])
    
    await callback.edit_message_text(
        f"**⚠️ Are you sure you want to delete {clan['name']}?**\n\n"
        f"This action cannot be undone. All clan data will be lost.",
        reply_markup=keyboard
    )
    
    await callback.answer()

@app.on_callback_query(filters.regex(r"^confirm_delete:"))
async def confirm_delete_clan(client: Client, callback: CallbackQuery):
    clan_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if user is the owner
    if user_id != clan["owner_id"]:
        await callback.answer("Only the clan owner can delete the clan!", show_alert=True)
        return
    
    # Delete clan
    await clan_collection.delete_one({"clan_id": clan_id})
    
    await callback.edit_message_text(
        f"**🗑️ Clan {clan['name']} has been deleted**\n\n"
        f"All clan data has been permanently removed."
    )
    
    await callback.answer("Clan deleted successfully")

@app.on_callback_query(filters.regex(r"^cancel_delete:"))
async def cancel_delete_clan(client: Client, callback: CallbackQuery):
    clan_id = callback.data.split(":")[1]
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Return to clan view
    buttons = []
    buttons.append([InlineKeyboardButton("🗑️ Delete Clan", callback_data=f"delete_clan:{clan_id}")])
    buttons.append([InlineKeyboardButton("👥 View Members", callback_data=f"view_members:{clan_id}:1")])
    
    caption = (
        f"**🏮 Clan: {clan['name']}**\n"
        f"**🆔 Clan ID:** `{clan['clan_id']}`\n"
        f"**👑 Owner:** {clan['owner_mention']}\n"
        f"**👥 Members:** {clan['member_count']}/{clan['max_members']}\n"
        f"**✨ Level:** {clan['level']}\n"
        f"**🏆 Rank:** {clan['rank']}\n"
        f"**✅ Wins:** {clan['wins']}\n"
        f"**❌ Losses:** {clan['losses']}\n\n"
        f"**Share your clan ID to invite others!**"
    )
    
    await callback.edit_message_text(
        caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    await callback.answer("Deletion cancelled")

# Set Clan Profile Picture Command
@app.on_message(filters.command("setcpfp") & filters.reply)
async def set_clan_pfp(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user owns a clan
    clan = await clan_collection.find_one({"owner_id": user_id})
    if not clan:
        return await message.reply_text(
            "**⚠️ You don't own a clan!**\n\n"
            "Only clan owners can set clan profile pictures."
        )
    
    # Get the replied message
    replied = message.reply_to_message
    
    # Check if replied message has media
    if not (replied.photo or replied.video or replied.animation or replied.document):
        return await message.reply_text(
            "**⚠️ Please reply to a photo, video, or GIF!**\n\n"
            "The media will be set as your clan's profile picture."
        )
    
    # Get the file ID
    if replied.photo:
        file_id = replied.photo.file_id
    elif replied.video:
        file_id = replied.video.file_id
    elif replied.animation:
        file_id = replied.animation.file_id
    elif replied.document and replied.document.mime_type.startswith('image/'):
        file_id = replied.document.file_id
    else:
        return await message.reply_text(
            "**⚠️ Unsupported media type!**\n\n"
            "Please reply with a photo, video, or GIF."
        )
    
    # Update clan pfp
    await clan_collection.update_one(
        {"clan_id": clan["clan_id"]},
        {"$set": {"clan_pfp": file_id}}
    )
    
    await message.reply_text(
        f"**✅ Clan profile picture updated!**\n\n"
        f"**🏮 Clan:** {clan['name']}\n"
        f"The new profile picture will be shown in clan info."
    )

# Clan Role Management Command
@app.on_message(filters.command("role") & filters.reply)
async def set_member_role(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user owns a clan
    clan = await clan_collection.find_one({"owner_id": user_id})
    if not clan:
        return await message.reply_text(
            "**⚠️ You don't own a clan!**\n\n"
            "Only clan owners can set member roles."
        )
    
    # Get the replied user
    replied = message.reply_to_message
    target_id = replied.from_user.id
    
    # Check if target is in the clan
    target_in_clan = any(member["user_id"] == target_id for member in clan["members"])
    if not target_in_clan:
        return await message.reply_text(
            "**⚠️ This user is not in your clan!**\n\n"
            "You can only set roles for clan members."
        )
    
    # Check if target is the owner
    if target_id == clan["owner_id"]:
        return await message.reply_text(
            "**⚠️ You cannot change the owner's role!**"
        )
    
    # Get role from command
    args = message.text.split()
    if len(args) < 2:
        # Show role selection buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔥 Hokage", callback_data=f"set_role:{target_id}:hokage:{clan['clan_id']}"),
                InlineKeyboardButton("⚔️ Chunin", callback_data=f"set_role:{target_id}:chunin:{clan['clan_id']}")
            ],
            [
                InlineKeyboardButton("🌀 Genin", callback_data=f"set_role:{target_id}:genin:{clan['clan_id']}"),
                InlineKeyboardButton("🌱 Low Ninja", callback_data=f"set_role:{target_id}:low_ninja:{clan['clan_id']}")
            ]
        ])
        
        await message.reply_text(
            f"**Select a role for {replied.from_user.mention}**\n\n"
            f"**Current Clan:** {clan['name']}",
            reply_markup=keyboard
        )
        return
    
    role_key = args[1].lower()
    if role_key not in CLAN_ROLES:
        return await message.reply_text(
            "**⚠️ Invalid role!**\n\n"
            "Available roles: hokage, chunin, genin, low_ninja"
        )
    
    role = CLAN_ROLES[role_key]
    
    # Update member role
    await clan_collection.update_one(
        {"clan_id": clan["clan_id"], "members.user_id": target_id},
        {"$set": {"members.$.role": role}}
    )
    
    await message.reply_text(
        f"**✅ Role updated!**\n\n"
        f"**👤 User:** {replied.from_user.mention}\n"
        f"**🎭 New Role:** {role}\n"
        f"**🏮 Clan:** {clan['name']}"
    )

# Handle role selection callback
@app.on_callback_query(filters.regex(r"^set_role:"))
async def handle_set_role(client: Client, callback: CallbackQuery):
    data = callback.data.split(":")
    target_id = int(data[1])
    role_key = data[2]
    clan_id = data[3]
    
    # Get clan data
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        await callback.answer("Clan not found!", show_alert=True)
        return
    
    # Check if callback is from clan owner
    if callback.from_user.id != clan["owner_id"]:
        await callback.answer("Only the clan owner can set roles!", show_alert=True)
        return
    
    # Check if target is in the clan
    target_in_clan = any(member["user_id"] == target_id for member in clan["members"])
    if not target_in_clan:
        await callback.answer("User is not in your clan!", show_alert=True)
        return
    
    # Check if target is the owner
    if target_id == clan["owner_id"]:
        await callback.answer("You cannot change the owner's role!", show_alert=True)
        return
    
    role = CLAN_ROLES[role_key]
    
    # Update member role
    await clan_collection.update_one(
        {"clan_id": clan_id, "members.user_id": target_id},
        {"$set": {"members.$.role": role}}
    )
    
    # Get target user info
    try:
        target_user = await client.get_users(target_id)
        target_mention = target_user.mention()
    except:
        target_mention = "Unknown User"
    
    await callback.edit_message_text(
        f"**✅ Role updated!**\n\n"
        f"**👤 User:** {target_mention}\n"
        f"**🎭 New Role:** {role}\n"
        f"**🏮 Clan:** {clan['name']}"
    )
    
    await callback.answer(f"Role set to {role}")

# Remove Role Command
@app.on_message(filters.command("unrole") & filters.reply)
async def remove_member_role(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user owns a clan
    clan = await clan_collection.find_one({"owner_id": user_id})
    if not clan:
        return await message.reply_text(
            "**⚠️ You don't own a clan!**\n\n"
            "Only clan owners can remove member roles."
        )
    
    # Get the replied user
    replied = message.reply_to_message
    target_id = replied.from_user.id
    
    # Check if target is in the clan
    target_in_clan = any(member["user_id"] == target_id for member in clan["members"])
    if not target_in_clan:
        return await message.reply_text(
            "**⚠️ This user is not in your clan!**\n\n"
            "You can only remove roles for clan members."
        )
    
    # Check if target is the owner
    if target_id == clan["owner_id"]:
        return await message.reply_text(
            "**⚠️ You cannot remove the owner's role!**"
        )
    
    # Reset role to default
    await clan_collection.update_one(
        {"clan_id": clan["clan_id"], "members.user_id": target_id},
        {"$set": {"members.$.role": "🌱 Low Ninja"}}
    )
    
    await message.reply_text(
        f"**✅ Role removed!**\n\n"
        f"**👤 User:** {replied.from_user.mention}\n"
        f"**🎭 Role Reset To:** 🌱 Low Ninja\n"
        f"**🏮 Clan:** {clan['name']}"
    )

# Clan Info Command
@app.on_message(filters.command("infoclan"))
async def clan_info(client: Client, message: Message):
    # Get clan ID from command
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "**⚠️ Please provide a clan ID!**\n"
            "**Usage:** /infoclan <clan_id>"
        )
    
    clan_id = args[1].upper()
    
    # Find clan by ID
    clan = await clan_collection.find_one({"clan_id": clan_id})
    if not clan:
        return await message.reply_text(
            "**⚠️ Clan not found!**\n"
            "Please check the clan ID and try again."
        )
    
    # Format clan info
    caption = (
        f"**🏮 Clan: {clan['name']}**\n"
        f"**🆔 Clan ID:** `{clan['clan_id']}`\n"
        f"**👑 Owner:** {clan['owner_mention']}\n"
        f"**👥 Members:** {clan['member_count']}/{clan['max_members']}\n"
        f"**✨ Level:** {clan['level']}\n"
        f"**🏆 Rank:** {clan['rank']}\n"
        f"**✅ Wins:** {clan['wins']}\n"
        f"**❌ Losses:** {clan['losses']}\n"
        f"**📅 Created:** {clan['created_at'].strftime('%Y-%m-%d')}\n\n"
        f"Use /joinclan {clan_id} to join this clan!"
    )
    
    if clan.get("clan_pfp"):
        try:
            await message.reply_photo(
                clan["clan_pfp"],
                caption=caption
            )
            return
        except:
            pass
    
    await message.reply_text(caption)

# Clan Rank Command
@app.on_message(filters.command("clanrank"))
async def clan_rankings(client: Client, message: Message):
    # Get top clans by wins
    top_clans = await clan_collection.find().sort("wins", -1).limit(10).to_list(10)
    
    if not top_clans:
        return await message.reply_text(
            "**🏆 Clan Rankings**\n\n"
            "No clans have been created yet!"
        )
    
    # Format rankings
    rankings = "**🏆 Top Clans by Wins**\n\n"
    for i, clan in enumerate(top_clans, 1):
        rankings += f"{i}. **{clan['name']}** - {clan['wins']} wins\n"
        rankings += f"   Level {clan['level']} | {clan['rank']} | Members: {clan['member_count']}\n\n"
    
    await message.reply_text(rankings)

# Clan War Commands (for dev/owner only)
@app.on_message(filters.command("clanwar") & filters.user(7861332030))
async def start_clan_war(client: Client, message: Message):
    # Get two random clans
    all_clans = await clan_collection.find().to_list(100)
    
    if len(all_clans) < 2:
        return await message.reply_text(
            "**⚠️ Not enough clans for a war!**\n\n"
            "At least 2 clans are needed to start a clan war."
        )
    
    # Select two random clans
    clan1, clan2 = random.sample(all_clans, 2)
    
    # Start the war
    await process_clan_war(client, message, clan1, clan2)

@app.on_message(filters.command("sclanwar") & filters.user(7861332030))
async def start_specific_clan_war(client: Client, message: Message):
    # Get clan IDs from command
    args = message.text.split()
    if len(args) < 3:
        return await message.reply_text(
            "**⚠️ Please provide two clan IDs!**\n"
            "**Usage:** /sclanwar <clan_id1> <clan_id2>"
        )
    
    clan_id1 = args[1].upper()
    clan_id2 = args[2].upper()
    
    # Find clans by ID
    clan1 = await clan_collection.find_one({"clan_id": clan_id1})
    clan2 = await clan_collection.find_one({"clan_id": clan_id2})
    
    if not clan1 or not clan2:
        return await message.reply_text(
            "**⚠️ One or both clans not found!**\n"
            "Please check the clan IDs and try again."
        )
    
    if clan1["clan_id"] == clan2["clan_id"]:
        return await message.reply_text(
            "**⚠️ Cannot start a war between the same clan!**"
        )
    
    # Start the war
    await process_clan_war(client, message, clan1, clan2)

async def process_clan_war(client: Client, message: Message, clan1: dict, clan2: dict):
    # Create war record
    war_id = generate_clan_id(12)
    war_data = {
        "war_id": war_id,
        "clan1_id": clan1["clan_id"],
        "clan1_name": clan1["name"],
        "clan2_id": clan2["clan_id"],
        "clan2_name": clan2["name"],
        "started_at": datetime.now(),
        "status": "ongoing"
    }
    
    await clan_war_collection.insert_one(war_data)
    
    # Send war announcement with image
    war_image_url = "https://example.com/clan_war_image.jpg"  # Replace with your image URL
    
    war_message = (
        f"**⚔️ Clan War Started!**\n\n"
        f"**{clan1['name']}** 🆚 **{clan2['name']}**\n\n"
        f"**Clan 1:** {clan1['name']} (ID: `{clan1['clan_id']}`)\n"
        f"**Owner:** {clan1['owner_mention']}\n"
        f"**Members:** {clan1['member_count']}\n\n"
        f"**Clan 2:** {clan2['name']} (ID: `{clan2['clan_id']}`)\n"
        f"**Owner:** {clan2['owner_mention']}\n"
        f"**Members:** {clan2['member_count']}\n\n"
        f"**War ID:** `{war_id}`\n"
        f"Support your clan in this epic battle!"
    )
    
    # Send notification to all clan members
    for clan in [clan1, clan2]:
        for member in clan["members"]:
            try:
                await client.send_message(
                    member["user_id"],
                    f"**⚔️ Your clan is in a war!**\n\n"
                    f"**{clan1['name']}** 🆚 **{clan2['name']}**\n\n"
                    f"Support your clan in this epic battle!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏆 View War", url=f"https://t.me/c/{message.chat.id}/{message.id}")]
                    ])
                )
            except:
                pass
    
    try:
        await message.reply_photo(
            war_image_url,
            caption=war_message
        )
    except:
        await message.reply_text(war_message)
    
    # Simulate war (wait a bit and determine winner)
    await sleep(10)
    
    # Determine winner randomly (could be more complex)
    winner_clan = random.choice([clan1, clan2])
    loser_clan = clan2 if winner_clan["clan_id"] == clan1["clan_id"] else clan1
    
    # Update war record
    await clan_war_collection.update_one(
        {"war_id": war_id},
        {
            "$set": {
                "status": "completed",
                "winner_clan_id": winner_clan["clan_id"],
                "winner_clan_name": winner_clan["name"],
                "ended_at": datetime.now()
            }
        }
    )
    
    # Update clan stats
    await clan_collection.update_one(
        {"clan_id": winner_clan["clan_id"]},
        {
            "$inc": {
                "wins": 1,
                "level": 1
            }
        }
    )
    
    await clan_collection.update_one(
        {"clan_id": loser_clan["clan_id"]},
        {"$inc": {"losses": 1}}
    )
    
    # Update clan rank based on level
    for clan in [winner_clan, loser_clan]:
        updated_clan = await clan_collection.find_one({"clan_id": clan["clan_id"]})
        if updated_clan:
            new_level = updated_clan["level"]
            new_rank = CLAN_RANKS.get(min(new_level, 10), CLAN_RANKS[10])
            
            await clan_collection.update_one(
                {"clan_id": clan["clan_id"]},
                {"$set": {"rank": new_rank}}
            )
    
    # Reward winner clan members
    limited_chars = await collection.find({"rarity": "🔮 Limited Edition"}).limit(2).to_list(2)
    animated_chars = await collection.find({"rarity": "⚜️ Animated"}).limit(2).to_list(2)
    
    reward_chars = limited_chars + animated_chars
    
    for member in winner_clan["members"]:
        for char in reward_chars:
            try:
                await ac(member["user_id"], char["id"])
            except:
                pass
    
    # Send war results
    results_message = (
        f"**🏆 Clan War Results!**\n\n"
        f"**{clan1['name']}** 🆚 **{clan2['name']}**\n\n"
        f"**Winner:** {winner_clan['name']} 🎉\n\n"
        f"**Rewards:**\n"
        f"- All members of {winner_clan['name']} received 4 rare characters!\n"
        f"- Clan level increased by 1\n"
        f"- Clan rank updated\n\n"
        f"Congratulations to the winning clan!"
    )
    
    try:
        await message.reply_photo(
            war_image_url,
            caption=results_message
        )
    except:
        await message.reply_text(results_message)
    
    # Notify all clan members of results
    for clan in [clan1, clan2]:
        is_winner = clan["clan_id"] == winner_clan["clan_id"]
        
        for member in clan["members"]:
            try:
                if is_winner:
                    await client.send_message(
                        member["user_id"],
                        f"**🎉 Your clan won the war!**\n\n"
                        f"**{clan1['name']}** 🆚 **{clan2['name']}**\n\n"
                        f"**Rewards:**\n"
                        f"- 4 rare characters added to your collection\n"
                        f"- Clan level increased by 1\n"
                        f"- Clan rank updated\n\n"
                        f"Check your collection with /mycollection"
                    )
                else:
                    await client.send_message(
                        member["user_id"],
                        f"**💔 Your clan lost the war!**\n\n"
                        f"**{clan1['name']}** 🆚 **{clan2['name']}**\n\n"
                        f"Better luck next time! Train your clan and try again."
                    )
            except:
                pass

# Delete All Clans Command (Dev Only)
@app.on_message(filters.command("dclan") & filters.user(7861332030))
async def delete_all_clans(client: Client, message: Message):
    # Confirmation buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Delete All", callback_data="confirm_delete_all_clans"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete_all_clans")
        ]
    ])
    
    # Get total clan count
    total_clans = await clan_collection.count_documents({})
    
    await message.reply_text(
        f"**⚠️ ARE YOU ABSOLUTELY SURE?**\n\n"
        f"This will delete **ALL {total_clans} clans** from the database!\n"
        f"This action is **permanent and cannot be undone**!\n\n"
        f"**Type /confirmdclan to proceed** or use the buttons below.",
        reply_markup=keyboard
    )

# Confirm Delete All Clans Command
@app.on_message(filters.command("confirmdclan") & filters.user(7861332030))
async def confirm_delete_all_clans(client: Client, message: Message):
    # Get total clan count before deletion
    total_clans = await clan_collection.count_documents({})
    
    if total_clans == 0:
        return await message.reply_text(
            "**ℹ️ No clans found in the database!**\n"
            "There are no clans to delete."
        )
    
    # Delete all clans
    result = await clan_collection.delete_many({})
    
    await message.reply_text(
        f"**🗑️ Successfully deleted all clans!**\n\n"
        f"**Deleted:** {result.deleted_count} clans\n"
        f"**Database cleaned:** ✅\n\n"
        f"All clan data has been permanently removed from the system."
    )

# Handle callback for delete all clans
@app.on_callback_query(filters.regex(r"^confirm_delete_all_clans$"))
async def handle_confirm_delete_all_clans(client: Client, callback: CallbackQuery):
    # Check if user is the dev
    if callback.from_user.id != 7861332030:
        await callback.answer("Only the developer can use this command!", show_alert=True)
        return
    
    # Get total clan count before deletion
    total_clans = await clan_collection.count_documents({})
    
    if total_clans == 0:
        await callback.answer("No clans found in the database!", show_alert=True)
        return
    
    # Delete all clans
    result = await clan_collection.delete_many({})
    
    await callback.edit_message_text(
        f"**🗑️ Successfully deleted all clans!**\n\n"
        f"**Deleted:** {result.deleted_count} clans\n"
        f"**Database cleaned:** ✅\n\n"
        f"All clan data has been permanently removed from the system."
    )
    
    await callback.answer("All clans deleted successfully!")

@app.on_callback_query(filters.regex(r"^cancel_delete_all_clans$"))
async def handle_cancel_delete_all_clans(client: Client, callback: CallbackQuery):
    # Check if user is the dev
    if callback.from_user.id != 7861332030:
        await callback.answer("Only the developer can use this command!", show_alert=True)
        return
    
    await callback.edit_message_text(
        "**❌ Operation cancelled!**\n\n"
        "No clans were deleted from the database."
    )
    
    await callback.answer("Operation cancelled")
