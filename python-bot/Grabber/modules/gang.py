import os
import random
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import app, user_collection, gang_collection
from .block import block_dec, temp_block
import pytz
from bson.objectid import ObjectId
from pyrogram.errors import BadRequest, RPCError

TIMEZONE = pytz.timezone('Asia/Kolkata')

DEV_ID = 6118760915  # Change this to your actual dev ID

# Gang ranks
GANG_RANKS = {
    0: "ᴍᴇᴍʙᴇʀ",
    1: "ᴇʟɪᴛᴇ",
    2: "ᴠɪᴄᴇ-ʟᴇᴀᴅᴇʀ",
    3: "ᴄᴏ-ʟᴇᴀᴅᴇʀ"
}

# Gang XP requirements for levels
XP_REQUIREMENTS = [
    0, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000
]

def to_tiny_caps(text: str) -> str:
    """Convert text to tiny caps style"""
    tiny_map = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
    )
    return text.translate(tiny_map)

def generate_gang_id() -> str:
    """Generate a random 6-digit gang ID"""
    return str(random.randint(100000, 999999))

def get_gang_level(xp: int) -> int:
    """Calculate gang level based on XP"""
    for level, requirement in enumerate(XP_REQUIREMENTS):
        if xp < requirement:
            return level - 1
    return len(XP_REQUIREMENTS) - 1

def progress_bar(percentage: float) -> str:
    """Create a visual progress bar"""
    filled = round(percentage * 10)
    return '█' * filled + '░' * (10 - filled)

async def notify_gang_members(gang_id: str, message: str, exclude_user_id: int = None):
    """Notify all gang members"""
    gang = await gang_collection.find_one({"_id": ObjectId(gang_id)})
    if not gang:
        return
    
    for member in gang["members"]:
        user_id = member["user_id"]
        if exclude_user_id and user_id == exclude_user_id:
            continue
            
        try:
            await app.send_message(user_id, message)
        except:
            continue

@app.on_message(filters.command("creategang"))
@block_dec
async def create_gang(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is already in a gang
    existing_gang = await gang_collection.find_one({"members.user_id": user_id})
    if existing_gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴀ ɢᴀɴɢ! ᴜꜱᴇ /leavegang ᴛᴏ ʟᴇᴀᴠᴇ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ɢᴀɴɢ ꜰɪʀꜱᴛ.")
        return
    
    if len(message.command) < 2:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɢᴀɴɢ ɴᴀᴍᴇ. ᴜꜱᴀɢᴇ: /creategang <ɢᴀɴɢ ɴᴀᴍᴇ>")
        return
    
    gang_name = " ".join(message.command[1:])
    if len(gang_name) > 32:
        await message.reply("⚠️ ɢᴀɴɢ ɴᴀᴍᴇ ᴄᴀɴɴᴏᴛ ʙᴇ ʟᴏɴɢᴇʀ ᴛʜᴀɴ 32 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ.")
        return
    
    # Create new gang
    gang_data = {
        "name": gang_name,
        "gang_id": generate_gang_id(),
        "owner": user_id,
        "members": [{"user_id": user_id, "rank": 3}],  # Owner has highest rank
        "wins": 0,
        "losses": 0,
        "xp": 0,
        "created_at": datetime.now(TIMEZONE),
        "pfp": None,
        "description": "ᴡʀɪᴛᴇ /editgdesc ᴛᴏ ꜱᴇᴛ ᴀ ɢᴀɴɢ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ."
    }
    
    result = await gang_collection.insert_one(gang_data)
    
    await message.reply(
        f"🎉 **ɴᴇᴡ ɢᴀɴɢ ᴄʀᴇᴀᴛᴇᴅ!**\n\n"
        f"➠ ɴᴀᴍᴇ: `{gang_name}`\n"
        f"➠ ɢᴀɴɢ ɪᴅ: `{gang_data['gang_id']}`\n\n"
        f"ᴜꜱᴇ /mygang ᴛᴏ ᴠɪᴇᴡ ʏᴏᴜʀ ɢᴀɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ.\n"
        f"ꜱʜᴀʀᴇ ʏᴏᴜʀ ɢᴀɴɢ ɪᴅ ᴡɪᴛʜ ᴏᴛʜᴇʀꜱ ᴛᴏ ɪɴᴠɪᴛᴇ ᴛʜᴇᴍ!"
    )

@app.on_message(filters.command("joingang"))
@block_dec
async def join_gang(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is already in a gang
    existing_gang = await gang_collection.find_one({"members.user_id": user_id})
    if existing_gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴀ ɢᴀɴɢ! ᴜꜱᴇ /leavegang ᴛᴏ ʟᴇᴀᴠᴇ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ɢᴀɴɢ ꜰɪʀꜱᴛ.")
        return
    
    if len(message.command) < 2:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɢᴀɴɢ ɪᴅ. ᴜꜱᴀɢᴇ: /joingang <ɢᴀɴɢ ɪᴅ>")
        return
    
    gang_id = message.command[1]
    gang = await gang_collection.find_one({"gang_id": gang_id})
    
    if not gang:
        await message.reply("⚠️ ɴᴏ ɢᴀɴɢ ꜰᴏᴜɴᴅ ᴡɪᴛʜ ᴛʜᴀᴛ ɪᴅ. ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.")
        return
    
    # Add user to gang as a member
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$push": {"members": {"user_id": user_id, "rank": 0}}}
    )
    
    # Notify gang members
    await notify_gang_members(
        gang["_id"],
        f"✨ **ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴊᴏɪɴᴇᴅ!**\n\n"
        f"➠ ɴᴀᴍᴇ: [{message.from_user.first_name}](tg://user?id={user_id})\n"
        f"➠ ɢᴀɴɢ: `{gang['name']}`\n\n"
        f"ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ �ᴛʜᴇ ɢᴀɴɢ!"
    )
    
    await message.reply(
        f"🎉 **ʏᴏᴜ'ᴠᴇ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ɢᴀɴɢ!**\n\n"
        f"➠ ɢᴀɴɢ: `{gang['name']}`\n"
        f"➠ ᴏᴡɴᴇʀ: `{gang['owner']}`\n\n"
        f"ᴜꜱᴇ /mygang ᴛᴏ ᴠɪᴇᴡ ʏᴏᴜʀ ɢᴀɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ."
    )

@app.on_message(filters.command("mygang"))
@block_dec
async def my_gang(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Find user's gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ! ᴜꜱᴇ /creategang ᴏʀ /joingang ᴛᴏ ᴊᴏɪɴ ᴏɴᴇ.")
        return
    
    # Safely get gang fields with defaults
    gang_name = gang.get("name", "ɴᴏ ɴᴀᴍᴇ")
    gang_id = gang.get("gang_id", "ɴᴏ ɪᴅ")
    owner_id = gang.get("owner", 0)
    members = gang.get("members", [])
    xp = gang.get("xp", 0)
    wins = gang.get("wins", 0)
    losses = gang.get("losses", 0)
    description = gang.get("description", "ᴡʀɪᴛᴇ /editgdesc ᴛᴏ ꜱᴇᴛ ᴀ ɢᴀɴɢ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ.")
    
    # Find user's rank in the gang
    user_rank = 0
    for member in members:
        if member.get("user_id") == user_id:
            user_rank = member.get("rank", 0)
            break
    
    # Calculate gang level
    gang_level = get_gang_level(xp)
    next_level_xp = XP_REQUIREMENTS[gang_level + 1] if gang_level + 1 < len(XP_REQUIREMENTS) else XP_REQUIREMENTS[-1]
    xp_progress = (xp - XP_REQUIREMENTS[gang_level]) / (next_level_xp - XP_REQUIREMENTS[gang_level]) * 100 if next_level_xp > XP_REQUIREMENTS[gang_level] else 100
    
    # Get owner info
    try:
        owner = await client.get_users(owner_id)
        owner_name = owner.first_name
    except:
        owner_name = "Unknown"
    
    # Format members list
    members_list = []
    for member in sorted(members, key=lambda x: x.get("rank", 0), reverse=True):
        try:
            user = await client.get_users(member.get("user_id", 0))
            name = user.first_name if user else "Unknown"
        except:
            name = "Unknown"
        
        rank_name = GANG_RANKS.get(member.get("rank", 0), "ᴍᴇᴍʙᴇʀ")
        members_list.append(f"➠ {name} ({rank_name})")
    
    members_text = "\n".join(members_list[:10])  # Show first 10 members
    if len(members) > 10:
        members_text += f"\n\n+ {len(members) - 10} ᴍᴏʀᴇ ᴍᴇᴍʙᴇʀꜱ..."
    
    # Format the gang info message
    gang_info = f"""
  ◆ {to_tiny_caps('gang information')} ◆
༺═──────────────────═༻
   ●  ɴᴀᴍᴇ: `{gang_name}`
   ●  ɪᴅ: `{gang_id}`
   ●  ᴏᴡɴᴇʀ: `{owner_name}`
༺═──────────────────═༻
   ❖  ɢᴀɴɢ ꜱᴛᴀᴛꜱ
   ├─ ʟᴇᴠᴇʟ: `{gang_level}`
   ├─ xᴘ: `{xp}/{next_level_xp}`
   ├─ {progress_bar(xp_progress/100)}
   ├─ ᴡɪɴꜱ: `{wins}`
   └─ ʟᴏꜱꜱᴇꜱ: `{losses}`
   
   ❖  ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ
   {description}
   
   ❖  ᴍᴇᴍʙᴇʀꜱ ({len(members)})
   {members_text}
   
   ❖  ʏᴏᴜʀ ʀᴀɴᴋ
   {GANG_RANKS.get(user_rank, "ᴍᴇᴍʙᴇʀ")}
"""
    
    # Handle both photo and video pfp
    if gang.get("pfp"):
        try:
            # First try to send as photo
            await message.reply_photo(
                photo=gang["pfp"],
                caption=gang_info
            )
        except ValueError:
            # If it's a video, send as video
            try:
                await message.reply_video(
                    video=gang["pfp"],
                    caption=gang_info
                )
            except Exception as e:
                print(f"Error sending gang media: {e}")
                await message.reply(gang_info)
        except Exception as e:
            print(f"Error sending gang pfp: {e}")
            await message.reply(gang_info)
    else:
        await message.reply(gang_info)

@app.on_message(filters.command("setgpfp"))
@block_dec
async def set_gang_pfp(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner
    if gang["owner"] != user_id:
        await message.reply("⚠️ ᴏɴʟʏ ᴛʜᴇ ɢᴀɴɢ ᴏᴡɴᴇʀ ᴄᴀɴ ꜱᴇᴛ ᴛʜᴇ ɢᴀɴɢ ᴘʀᴏꜰɪʟᴇ ᴘɪᴄᴛᴜʀᴇ!")
        return
    
    if not message.reply_to_message or not (message.reply_to_message.photo or message.reply_to_message.video):
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴏʀ ᴠɪᴅᴇᴏ ᴛᴏ ꜱᴇᴛ ᴀꜱ ɢᴀɴɢ ᴘʀᴏꜰɪʟᴇ!")
        return
    
    # Get file_id from either photo or video
    if message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_id
    else:
        file_id = message.reply_to_message.video.file_id
    
    # Update gang pfp
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$set": {"pfp": file_id}}
    )
    
    await message.reply("🎉 ɢᴀɴɢ ᴘʀᴏꜰɪʟᴇ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘᴅᴀᴛᴇᴅ!")

@app.on_message(filters.command("editgname"))
@block_dec
async def edit_gang_name(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner
    if gang["owner"] != user_id:
        await message.reply("⚠️ ᴏɴʟʏ ᴛʜᴇ ɢᴀɴɢ ᴏᴡɴᴇʀ ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴇ ɢᴀɴɢ ɴᴀᴍᴇ!")
        return
    
    if len(message.command) < 2:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ɴᴀᴍᴇ. ᴜꜱᴀɢᴇ: /editgname <ɴᴇᴡ ɴᴀᴍᴇ>")
        return
    
    new_name = " ".join(message.command[1:])
    if len(new_name) > 32:
        await message.reply("⚠️ ɢᴀɴɢ ɴᴀᴍᴇ ᴄᴀɴɴᴏᴛ ʙᴇ ʟᴏɴɢᴇʀ ᴛʜᴀɴ 32 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ.")
        return
    
    # Update gang name
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$set": {"name": new_name}}
    )
    
    # Notify all gang members
    await notify_gang_members(
        gang["_id"],
        f"📢 **ɢᴀɴɢ ɴᴀᴍᴇ ᴄʜᴀɴɢᴇᴅ!**\n\n"
        f"ᴛʜᴇ ɢᴀɴɢ ɴᴀᴍᴇ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ:\n"
        f"➠ `{new_name}`"
    )
    
    await message.reply(f"🎉 ɢᴀɴɢ ɴᴀᴍᴇ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ `{new_name}`!")

@app.on_message(filters.command("editgdesc"))
@block_dec
async def edit_gang_description(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner
    if gang["owner"] != user_id:
        await message.reply("⚠️ ᴏɴʟʏ ᴛʜᴇ ɢᴀɴɢ ᴏᴡɴᴇʀ ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴇ ɢᴀɴɢ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ!")
        return
    
    if len(message.command) < 2:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴇᴡ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ. ᴜꜱᴀɢᴇ: /editgdesc <ɴᴇᴡ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ>")
        return
    
    new_desc = " ".join(message.command[1:])
    if len(new_desc) > 200:
        await message.reply("⚠️ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ʟᴏɴɢᴇʀ ᴛʜᴀɴ 200 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ.")
        return
    
    # Update gang description
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$set": {"description": new_desc}}
    )
    
    await message.reply(f"🎉 ɢᴀɴɢ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ ʜᴀꜱ ʙᴇᴇɴ ᴜᴘᴅᴀᴛᴇᴅ!")

@app.on_message(filters.command("gpromote"))
@block_dec
async def promote_gang_member(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner or co-leader
    user_rank = 0
    for member in gang["members"]:
        if member["user_id"] == user_id:
            user_rank = member["rank"]
            break
    
    if user_rank < 2:  # Only owner (3) and co-leaders (2) can promote
        await message.reply("⚠️ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴘʀᴏᴍᴏᴛᴇ ᴍᴇᴍʙᴇʀꜱ!")
        return
    
    # Check if replying to a message or providing user ID
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_user = int(message.command[1])
        except:
            pass
    
    if not target_user:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴏʀ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇɪʀ ɪᴅ ᴛᴏ ᴘʀᴏᴍᴏᴛᴇ ᴛʜᴇᴍ.")
        return
    
    # Check if target user is in the gang
    target_member = None
    target_index = -1
    for i, member in enumerate(gang["members"]):
        if member["user_id"] == target_user:
            target_member = member
            target_index = i
            break
    
    if not target_member:
        await message.reply("⚠️ ᴛʜᴀᴛ ᴜꜱᴇʀ ɪꜱ ɴᴏᴛ ɪɴ ʏᴏᴜʀ ɢᴀɴɢ!")
        return
    
    # Check if promoting is possible (can't promote to same or higher rank than yourself)
    if target_member["rank"] >= user_rank:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴘʀᴏᴍᴏᴛᴇ ꜱᴏᴍᴇᴏɴᴇ ᴡɪᴛʜ ᴛʜᴇ ꜱᴀᴍᴇ ᴏʀ ʜɪɢʜᴇʀ ʀᴀɴᴋ ᴛʜᴀɴ ʏᴏᴜʀꜱᴇʟꜰ!")
        return
    
    # Promote the member (increase rank by 1)
    new_rank = target_member["rank"] + 1
    
    # Update the member's rank
    gang["members"][target_index]["rank"] = new_rank
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$set": {"members": gang["members"]}}
    )
    
    # Get user names
    try:
        promoter = await client.get_users(user_id)
        promoter_name = promoter.first_name
    except:
        promoter_name = "Unknown"
    
    try:
        promoted = await client.get_users(target_user)
        promoted_name = promoted.first_name
    except:
        promoted_name = "Unknown"
    
    # Notify gang members
    await notify_gang_members(
        gang["_id"],
        f"📢 **ɢᴀɴɢ ᴘʀᴏᴍᴏᴛɪᴏɴ!**\n\n"
        f"➠ ᴘʀᴏᴍᴏᴛᴇᴅ: [{promoted_name}](tg://user?id={target_user})\n"
        f"➠ ɴᴇᴡ ʀᴀɴᴋ: {GANG_RANKS.get(new_rank, 'ᴍᴇᴍʙᴇʀ')}\n"
        f"➠ ᴘʀᴏᴍᴏᴛᴇᴅ ʙʏ: [{promoter_name}](tg://user?id={user_id})"
    )
    
    await message.reply(
        f"🎉 **ᴍᴇᴍʙᴇʀ ᴘʀᴏᴍᴏᴛᴇᴅ!**\n\n"
        f"➠ ᴜꜱᴇʀ: [{promoted_name}](tg://user?id={target_user})\n"
        f"➠ ɴᴇᴡ ʀᴀɴᴋ: {GANG_RANKS.get(new_rank, 'ᴍᴇᴍʙᴇʀ')}"
    )

@app.on_message(filters.command("gdemote"))
@block_dec
async def demote_gang_member(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner or co-leader
    user_rank = 0
    for member in gang["members"]:
        if member["user_id"] == user_id:
            user_rank = member["rank"]
            break
    
    if user_rank < 2:  # Only owner (3) and co-leaders (2) can demote
        await message.reply("⚠️ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴅᴇᴍᴏᴛᴇ ᴍᴇᴍʙᴇʀꜱ!")
        return
    
    # Check if replying to a message or providing user ID
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_user = int(message.command[1])
        except:
            pass
    
    if not target_user:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴏʀ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇɪʀ ɪᴅ ᴛᴏ ᴅᴇᴍᴏᴛᴇ ᴛʜᴇᴍ.")
        return
    
    # Check if target user is in the gang
    target_member = None
    target_index = -1
    for i, member in enumerate(gang["members"]):
        if member["user_id"] == target_user:
            target_member = member
            target_index = i
            break
    
    if not target_member:
        await message.reply("⚠️ ᴛʜᴀᴛ ᴜꜱᴇʀ ɪꜱ ɴᴏᴛ ɪɴ ʏᴏᴜʀ ɢᴀɴɢ!")
        return
    
    # Check if demoting is possible (can't demote yourself, owner can't be demoted)
    if target_user == user_id:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴅᴇᴍᴏᴛᴇ ʏᴏᴜʀꜱᴇʟꜰ!")
        return
    
    if target_user == gang["owner"]:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴅᴇᴍᴏᴛᴇ ᴛʜᴇ ɢᴀɴɢ ᴏᴡɴᴇʀ!")
        return
    
    if target_member["rank"] == 0:
        await message.reply("⚠️ ᴛʜɪꜱ ᴍᴇᴍʙᴇʀ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴀᴛ ᴛʜᴇ ʟᴏᴡᴇꜱᴛ ʀᴀɴᴋ!")
        return
    
    # Demote the member (decrease rank by 1)
    new_rank = target_member["rank"] - 1
    
    # Update the member's rank
    gang["members"][target_index]["rank"] = new_rank
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$set": {"members": gang["members"]}}
    )
    
    # Get user names
    try:
        demoter = await client.get_users(user_id)
        demoter_name = demoter.first_name
    except:
        demoter_name = "Unknown"
    
    try:
        demoted = await client.get_users(target_user)
        demoted_name = demoted.first_name
    except:
        demoted_name = "Unknown"
    
    # Notify gang members
    await notify_gang_members(
        gang["_id"],
        f"📢 **ɢᴀɴɢ ᴅᴇᴍᴏᴛɪᴏɴ!**\n\n"
        f"➠ ᴅᴇᴍᴏᴛᴇᴅ: [{demoted_name}](tg://user?id={target_user})\n"
        f"➠ ɴᴇᴡ ʀᴀɴᴋ: {GANG_RANKS.get(new_rank, 'ᴍᴇᴍʙᴇʀ')}\n"
        f"➠ ᴅᴇᴍᴏᴛᴇᴅ ʙʏ: [{demoter_name}](tg://user?id={user_id})"
    )
    
    await message.reply(
        f"⚠️ **ᴍᴇᴍʙᴇʀ ᴅᴇᴍᴏᴛᴇᴅ!**\n\n"
        f"➠ ᴜꜱᴇʀ: [{demoted_name}](tg://user?id={target_user})\n"
        f"➠ ɴᴇᴡ ʀᴀɴᴋ: {GANG_RANKS.get(new_rank, 'ᴍᴇᴍʙᴇʀ')}"
    )

@app.on_message(filters.command("kickm"))
@block_dec
async def kick_gang_member(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner or co-leader
    user_rank = 0
    for member in gang["members"]:
        if member["user_id"] == user_id:
            user_rank = member["rank"]
            break
    
    if user_rank < 2:  # Only owner (3) and co-leaders (2) can kick
        await message.reply("⚠️ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴋɪᴄᴋ ᴍᴇᴍʙᴇʀꜱ!")
        return
    
    # Check if replying to a message or providing user ID
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_user = int(message.command[1])
        except:
            pass
    
    if not target_user:
        await message.reply("⚠️ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴏʀ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇɪʀ ɪᴅ ᴛᴏ ᴋɪᴄᴋ ᴛʜᴇᴍ.")
        return
    
    # Check if target user is in the gang
    target_member = None
    for member in gang["members"]:
        if member["user_id"] == target_user:
            target_member = member
            break
    
    if not target_member:
        await message.reply("⚠️ ᴛʜᴀᴛ ᴜꜱᴇʀ ɪꜱ ɴᴏᴛ ɪɴ ʏᴏᴜʀ ɢᴀɴɢ!")
        return
    
    # Check if kicking is possible (can't kick yourself, owner can't be kicked)
    if target_user == user_id:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴋɪᴄᴋ ʏᴏᴜʀꜱᴇʟꜰ!")
        return
    
    if target_user == gang["owner"]:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴋɪᴄᴋ ᴛʜᴇ ɢᴀɴɢ ᴏᴡɴᴇʀ!")
        return
    
    # Remove the member from the gang
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$pull": {"members": {"user_id": target_user}}}
    )
    
    # Get user names
    try:
        kicker = await client.get_users(user_id)
        kicker_name = kicker.first_name
    except:
        kicker_name = "Unknown"
    
    try:
        kicked = await client.get_users(target_user)
        kicked_name = kicked.first_name
    except:
        kicked_name = "Unknown"
    
    # Notify gang members
    await notify_gang_members(
        gang["_id"],
        f"📢 **ᴍᴇᴍʙᴇʀ ᴋɪᴄᴋᴇᴅ!**\n\n"
        f"➠ ᴋɪᴄᴋᴇᴅ: [{kicked_name}](tg://user?id={target_user})\n"
        f"➠ ᴋɪᴄᴋᴇᴅ ʙʏ: [{kicker_name}](tg://user?id={user_id})"
    )
    
    # Notify the kicked user
    try:
        await client.send_message(
            target_user,
            f"⚠️ **ʏᴏᴜ'ᴠᴇ ʙᴇᴇɴ ᴋɪᴄᴋᴇᴅ ꜰʀᴏᴍ ᴛʜᴇ ɢᴀɴɢ!**\n\n"
            f"➠ ɢᴀɴɢ: `{gang['name']}`\n"
            f"➠ ʀᴇᴀꜱᴏɴ: ɴᴏᴛ ꜱᴘᴇᴄɪꜰɪᴇᴅ"
        )
    except:
        pass
    
    await message.reply(
        f"⚠️ **ᴍᴇᴍʙᴇʀ ᴋɪᴄᴋᴇᴅ!**\n\n"
        f"➠ ᴜꜱᴇʀ: [{kicked_name}](tg://user?id={target_user})\n"
        f"➠ ʀᴇᴀꜱᴏɴ: ɴᴏᴛ ꜱᴘᴇᴄɪꜰɪᴇᴅ"
    )

@app.on_message(filters.command("leavegang"))
@block_dec
async def leave_gang(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in a gang
    gang = await gang_collection.find_one({"members.user_id": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ɪɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Check if user is the owner
    if gang["owner"] == user_id:
        await message.reply("⚠️ ʏᴏᴜ ᴄᴀɴ'ᴛ ʟᴇᴀᴠᴇ ʏᴏᴜʀ ᴏᴡɴ ɢᴀɴɢ! ᴜꜱᴇ /deletegang ᴛᴏ �ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ɢᴀɴɢ.")
        return
    
    # Remove user from the gang
    await gang_collection.update_one(
        {"_id": gang["_id"]},
        {"$pull": {"members": {"user_id": user_id}}}
    )
    
    # Get user name
    try:
        user = await client.get_users(user_id)
        user_name = user.first_name
    except:
        user_name = "Unknown"
    
    # Notify gang members
    await notify_gang_members(
        gang["_id"],
        f"📢 **ᴍᴇᴍʙᴇʀ ʟᴇꜰᴛ!**\n\n"
        f"➠ ᴜꜱᴇʀ: [{user_name}](tg://user?id={user_id})\n"
        f"➠ ɢᴀɴɢ: `{gang['name']}`"
    )
    
    await message.reply(
        f"⚠️ **ʏᴏᴜ'ᴠᴇ ʟᴇꜰᴛ ᴛʜᴇ ɢᴀɴɢ!**\n\n"
        f"➠ ɢᴀɴɢ: `{gang['name']}`"
    )

@app.on_message(filters.command("deletegang"))
@block_dec
async def delete_gang(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user owns a gang
    gang = await gang_collection.find_one({"owner": user_id})
    if not gang:
        await message.reply("⚠️ ʏᴏᴜ ᴅᴏɴ'ᴛ ᴏᴡɴ ᴀɴʏ ɢᴀɴɢ!")
        return
    
    # Confirm deletion
    if len(message.command) < 2 or message.command[1].lower() != "confirm":
        await message.reply(
            "⚠️ **ᴛʜɪꜱ ᴡɪʟʟ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ᴅᴇʟᴇᴛᴇ ʏᴏᴜʀ ɢᴀɴɢ!**\n\n"
            "ɪꜰ ʏᴏᴜ'ʀᴇ ꜱᴜʀᴇ, ᴘʟᴇᴀꜱᴇ ᴜꜱᴇ:\n"
            f"`/deletegang confirm`"
        )
        return
    
    # Get gang name for notification
    gang_name = gang["name"]
    
    # Notify all gang members
    await notify_gang_members(
        gang["_id"],
        f"⚠️ **ɢᴀɴɢ ᴅᴇʟᴇᴛᴇᴅ!**\n\n"
        f"ᴛʜᴇ ɢᴀɴɢ `{gang_name}` ʜᴀꜱ ʙᴇᴇɴ ᴅɪꜱʙᴀɴᴅᴇᴅ ʙʏ ɪᴛꜱ ᴏᴡɴᴇʀ."
    )
    
    # Delete the gang
    await gang_collection.delete_one({"_id": gang["_id"]})
    
    await message.reply(
        f"⚠️ **ʏᴏᴜʀ ɢᴀɴɢ ʜᴀꜱ ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ!**\n\n"
        f"➠ ɢᴀɴɢ: `{gang_name}`"
    )

@app.on_message(filters.command("gangwar") & filters.group)
@block_dec
async def gang_war(client: Client, message: Message):
    # Only allow bot developer (replace YOUR_DEV_ID with actual ID)
    if message.from_user.id != DEV_ID:
        await message.reply("⚠️ This command is restricted to bot developer only!")
        return

    # Advanced war initialization with multiple checks
    if len(message.command) < 3:
        await message.reply(
            "⚔️ **Advanced Gang War System** ⚔️\n\n"
            "Usage:\n"
            "`/gangwar <gang1_id> <gang2_id> [bet_amount]`\n"
            "`/gangwar random [bet_amount]`\n\n"
            "💰 Betting System: Winner takes 90% of pooled XP\n"
            "⏳ Cooldown: 12 hours between wars\n"
            "📊 Stats: Affects gang leaderboard position"
        )
        return

    # Check if gangs are in cooldown (using database)
    cooldown_check = await gang_cooldowns.find_one({
        "$or": [
            {"gang_id": message.command[1]},
            {"gang_id": message.command[2]}
        ],
        "war_end": {"$gt": datetime.now()}
    })
    if cooldown_check:
        remaining = cooldown_check["war_end"] - datetime.now()
        await message.reply(
            f"⏳ One of these gangs is on cooldown!\n"
            f"Next war possible in: {remaining.seconds//3600}h {(remaining.seconds%3600)//60}m"
        )
        return

    # Betting system
    bet_amount = 0
    if len(message.command) > 3 and message.command[-1].isdigit():
        bet_amount = int(message.command[-1])
        if bet_amount < 100:
            await message.reply("⚠️ Minimum bet amount is 100 XP!")
            return

    # Gang selection logic
    if message.command[1].lower() == "random":
        # Exclude low-level gangs from random selection
        all_gangs = await gang_collection.aggregate([
            {"$match": {"xp": {"$gt": 500}}},
            {"$sample": {"size": 2}}
        ]).to_list(length=2)
        
        if len(all_gangs) < 2:
            await message.reply("⚠️ Not enough eligible gangs for random war!")
            return
        
        gang1, gang2 = all_gangs[0], all_gangs[1]
    else:
        gang1 = await gang_collection.find_one({"gang_id": message.command[1]})
        gang2 = await gang_collection.find_one({"gang_id": message.command[2]})
        
        if not gang1 or not gang2:
            await message.reply("⚠️ Couldn't find both gangs. Check the IDs!")
            return

    # Advanced war simulation with multiple factors
    def calculate_win_chance(gang):
        level = get_gang_level(gang["xp"])
        member_count = len(gang["members"])
        win_ratio = gang["wins"] / max(1, gang["wins"] + gang["losses"])
        return (level * 2) + (member_count * 0.5) + (win_ratio * 20)

    gang1_power = calculate_win_chance(gang1)
    gang2_power = calculate_win_chance(gang2)
    total_power = gang1_power + gang2_power

    # Determine winner with weighted random
    winner = gang1 if random.random() < (gang1_power / total_power) else gang2
    loser = gang2 if winner == gang1 else gang1

    # XP calculations with bonuses
    base_xp = max(100, min(500, abs(gang1_power - gang2_power) * 2))
    xp_gain = base_xp + random.randint(50, 150)
    xp_loss = base_xp // 2 + random.randint(20, 80)

    # Apply betting
    if bet_amount > 0:
        if winner["xp"] < bet_amount or loser["xp"] < bet_amount:
            await message.reply("⚠️ One gang doesn't have enough XP for this bet!")
            return
        
        xp_gain += int(bet_amount * 0.9)
        xp_loss += bet_amount

    # Update database
    updates = [
        # Winner updates
        {
            "$inc": {
                "wins": 1,
                "xp": xp_gain,
                "war_streak": 1,
                "total_earned": xp_gain
            },
            "$set": {
                "last_war": datetime.now(),
                "war_cooldown": datetime.now() + timedelta(hours=12)
            }
        },
        # Loser updates
        {
            "$inc": {
                "losses": 1,
                "xp": -xp_loss,
                "war_streak": -1,
                "total_lost": xp_loss
            },
            "$set": {
                "last_war": datetime.now(),
                "war_cooldown": datetime.now() + timedelta(hours=12)
            }
        }
    ]

    await gang_collection.update_one({"_id": winner["_id"]}, updates[0])
    await gang_collection.update_one({"_id": loser["_id"]}, updates[1])

    # Get updated info
    updated_winner = await gang_collection.find_one({"_id": winner["_id"]})
    updated_loser = await gang_collection.find_one({"_id": loser["_id"]})

    # War result message with advanced stats
    result_msg = (
        f"⚔️ **GANG WAR RESULTS** ⚔️\n\n"
        f"🏆 WINNER: {winner['name']}\n"
        f"   Level: {get_gang_level(updated_winner['xp'])} (+{get_gang_level(updated_winner['xp']) - get_gang_level(winner['xp'])})\n"
        f"   XP Gained: +{xp_gain}\n"
        f"   New Streak: {updated_winner.get('war_streak', 0)}\n\n"
        f"☠ LOSER: {loser['name']}\n"
        f"   Level: {get_gang_level(updated_loser['xp'])} (-{get_gang_level(loser['xp']) - get_gang_level(updated_loser['xp'])})\n"
        f"   XP Lost: -{xp_loss}\n"
        f"   Streak Broken: {loser.get('war_streak', 0)}\n\n"
    )

    # Special bonuses for streaks
    if updated_winner.get('war_streak', 0) >= 3:
        streak_bonus = updated_winner['war_streak'] * 50
        await gang_collection.update_one(
            {"_id": winner["_id"]},
            {"$inc": {"xp": streak_bonus}}
        )
        result_msg += f"🔥 {winner['name']} is on a {updated_winner['war_streak']}-win streak! +{streak_bonus} XP bonus!\n\n"

    await message.reply(result_msg)

    # Notify gang members with different messages based on outcome
    await notify_gang_members(
        winner["_id"],
        f"🎉 **VICTORY NOTICE** 🎉\n\n"
        f"Your gang {winner['name']} has defeated {loser['name']}!\n\n"
        f"🏆 Rewards:\n"
        f"- Gained {xp_gain} XP\n"
        f"- Current streak: {updated_winner.get('war_streak', 0)} wins\n"
        f"- All members receive bonus items!"
    )

    await notify_gang_members(
        loser["_id"],
        f"💀 **DEFEAT NOTICE** 💀\n\n"
        f"Your gang {loser['name']} lost against {winner['name']}!\n\n"
        f"📉 Penalties:\n"
        f"- Lost {xp_loss} XP\n"
        f"- Streak reset to 0\n"
        f"- Cooldown: 12 hours\n\n"
        f"Analyze your strategy and try again later!"
    )

# Dev-only command to delete all gangs (fixed version)
@app.on_message(filters.command("delallgangs") & filters.user(DEV_ID))
@block_dec
async def delete_all_gangs(client: Client, message: Message):
    # Delete all gangs immediately
    result = await gang_collection.delete_many({})
    
    # Also clear cooldowns and related data
    await gang_cooldowns.delete_many({})
    
    await message.reply(f"🗑️ Successfully deleted {result.deleted_count} gangs!")

@app.on_message(filters.command("ganghelp"))
@block_dec
async def gang_help(client: Client, message: Message):
    help_text = f"""
  ◆ {to_tiny_caps('gang commands help')} ◆
༺═────────────────────────────═༻

  ❖  ɢᴀɴɢ ᴄʀᴇᴀᴛɪᴏɴ & ᴊᴏɪɴɪɴɢ
  ├─ /creategang <ɴᴀᴍᴇ> - ᴄʀᴇᴀᴛᴇ ᴀ ɴᴇᴡ ɢᴀɴɢ
  ├─ /joingang <ɪᴅ> - ᴊᴏɪɴ ᴀɴ ᴇxɪꜱᴛɪɴɢ ɢᴀɴɢ
  └─ /leavegang - ʟᴇᴀᴠᴇ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ɢᴀɴɢ

  ❖  ɢᴀɴɢ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ (ᴏᴡɴᴇʀ ᴏɴʟʏ)
  ├─ /editgname <ɴᴇᴡ ɴᴀᴍᴇ> - ᴄʜᴀɴɢᴇ ɢᴀɴɢ ɴᴀᴍᴇ
  ├─ /editgdesc <ᴅᴇꜱᴄ> - ꜱᴇᴛ ɢᴀɴɢ ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ
  ├─ /setgpfp - ꜱᴇᴛ ɢᴀɴɢ ᴘʀᴏꜰɪʟᴇ ᴘɪᴄ (ʀᴇᴘʟʏ ᴛᴏ ᴘɪᴄ/ᴠɪᴅᴇᴏ)
  ├─ /gpromote <ᴜꜱᴇʀ> - ᴘʀᴏᴍᴏᴛᴇ ᴀ ᴍᴇᴍʙᴇʀ
  ├─ /gdemote <ᴜꜱᴇʀ> - ᴅᴇᴍᴏᴛᴇ ᴀ ᴍᴇᴍʙᴇʀ
  ├─ /kickm <ᴜꜱᴇʀ> - ᴋɪᴄᴋ ᴀ ᴍᴇᴍʙᴇʀ ꜰʀᴏᴍ ɢᴀɴɢ
  └─ /deletegang - ᴅᴇʟᴇᴛᴇ ʏᴏᴜʀ ɢᴀɴɢ

  ❖  ɢᴀɴɢ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ
  ├─ /mygang - ᴠɪᴇᴡ ʏᴏᴜʀ ɢᴀɴɢ'ꜱ ɪɴꜰᴏ
  └─ /ganghelp - ꜱʜᴏᴡ ᴛʜɪꜱ ʜᴇʟᴘ ᴍᴇꜱꜱᴀɢᴇ

  ❖  ɢᴀɴɢ ᴡᴀʀ (ᴀᴅᴍɪɴ ᴏɴʟʏ)
  └─ /gangwar <ɢᴀɴɢ1> <ɢᴀɴɢ2> - ꜱᴛᴀʀᴛ ᴀ ɢᴀɴɢ ᴡᴀʀ

༺═────────────────────────────═༻
  ɢᴀɴɢ ꜱʏꜱᴛᴇᴍ ʙʏ @{client.me.username}
"""
    await message.reply(help_text)
