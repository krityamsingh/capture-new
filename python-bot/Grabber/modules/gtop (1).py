from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Grabber import user_collection, app, group_user_totals_collection, top_global_groups_collection

def style(text):
    table = str.maketrans("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                          "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return text.translate(table)

GTOP_MEDIA = "https://files.catbox.moe/nvu1v6.jpg"
ANITOP_MEDIA = "https://files.catbox.moe/qwaui3.jpg"
CTOP_MEDIA = "https://files.catbox.moe/wov3aa.mp4"
GTOPG_MEDIA = "https://files.catbox.moe/nvu1v6.jpg"

def mention_user(user):
    """Returns a safe mention for a user"""
    if hasattr(user, "mention") and user.mention:
        return user.mention
    if hasattr(user, "first_name") and user.first_name:
        name = user.first_name.replace("[", "").replace("]", "")
        return f"[{name}](tg://user?id={user.id})"
    return f"ᴜꜱᴇʀ {user.id}"

@app.on_message(filters.command("gtop"))
async def gtop_handler(client: Client, message: Message):
    pipeline = [
        {"$addFields": {
            "characters": {
                "$cond": {
                    "if": {"$isArray": "$characters"},
                    "then": "$characters",
                    "else": []
                }
            }
        }},
        {"$project": {"id": 1, "total": {"$size": "$characters"}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]
    
    try:
        top_users = await user_collection.aggregate(pipeline).to_list(length=10)
    except Exception as e:
        print(f"Error in gtop aggregation: {e}")
        return await message.reply_text("❌ An error occurred while processing the global top list.")

    if not top_users:
        return await message.reply_text("❌ ɴᴏ ɢʟᴏʙᴀʟ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ.")

    lines = [f"🌍 {style('**Top 10 Global captures**')}\n"]
    for i, user in enumerate(top_users, 1):
        uid = user.get("id") or user.get("_id")
        try:
            tg_user = await client.get_users(uid)
            name = mention_user(tg_user)
        except:
            name = f"[ᴜꜱᴇʀ {uid}](tg://user?id={uid})"
        lines.append(f"{i}. {name} ➾ {user['total']}")

    await message.reply_photo(
        photo=GTOP_MEDIA,
        caption="\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("ʏᴏᴜʀ ʀᴀɴᴋ", callback_data="gtop_rank"),
                InlineKeyboardButton("🚮", callback_data=f"close:{message.from_user.id}")
            ]
        ])
    )

@app.on_message(filters.command("anitop"))
async def anitop_handler(client: Client, message: Message):
    pipeline = [
        {"$addFields": {
            "characters": {
                "$cond": {
                    "if": {"$isArray": "$characters"},
                    "then": "$characters",
                    "else": []
                }
            }
        }},
        {"$unwind": "$characters"},
        {"$match": {"characters.rarity": "⚜️ Animated"}},
        {"$group": {"_id": "$id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    try:
        top_users = await user_collection.aggregate(pipeline).to_list(length=10)
    except Exception as e:
        print(f"Error in anitop aggregation: {e}")
        return await message.reply_text("❌ An error occurred while processing the animation top list.")

    if not top_users:
        return await message.reply_text("❌ ɴᴏ ᴀɴɪᴍᴀᴛɪᴏɴ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ ꜰᴏᴜɴᴅ.")

    lines = [f"⚜️ {style('**Top 10 Animated Holders**')}\n"]
    for i, user in enumerate(top_users, 1):
        uid = user.get("_id")
        try:
            tg_user = await client.get_users(uid)
            name = mention_user(tg_user)
        except:
            name = f"[ᴜꜱᴇʀ {uid}](tg://user?id={uid})"
        lines.append(f"{i}. {name} ➾ {user['count']}")

    await message.reply_photo(
        photo=ANITOP_MEDIA,
        caption="\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("ʜᴏᴡ ᴍᴀɴʏ ɪ ʜᴀᴠᴇ", callback_data="ani_count"),
                InlineKeyboardButton("🚮", callback_data=f"close:{message.from_user.id}")
            ]
        ])
    )

@app.on_message(filters.command("topgroups"))
async def topgroups_handler(client: Client, message: Message):
    try:
        # First get top groups from top_global_groups_collection
        top_groups = await top_global_groups_collection.find().sort("total_characters", -1).limit(10).to_list(length=10)
        
        # If no data in top_global_groups_collection, fetch from group_user_totals_collection
        if not top_groups:
            # Aggregate total characters per group from group_user_totals_collection
            pipeline = [
                {"$group": {
                    "_id": "$group_id", 
                    "total_characters": {"$sum": "$character_count"},
                    "group_name": {"$first": "$group_name"}
                }},
                {"$sort": {"total_characters": -1}},
                {"$limit": 10}
            ]
            top_groups = await group_user_totals_collection.aggregate(pipeline).to_list(length=10)
        
    except Exception as e:
        print(f"Error fetching top groups: {e}")
        return await message.reply_text("❌ An error occurred while processing the top groups list.")

    if not top_groups:
        return await message.reply_text("❌ ɴᴏ ɢʀᴏᴜᴘ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ.")

    lines = [f"🏆 {style('**Top 10 Groups Ranking**')}\n"]
    
    for i, group in enumerate(top_groups, 1):
        group_name = group.get("group_name", "Unknown Group")
        total_chars = group.get("total_characters", 0)
        
        # Clean group name from any markdown
        group_name_clean = group_name.replace("[", "").replace("]", "").replace("*", "")
        
        lines.append(f"{i}. {group_name_clean} ➾ {total_chars} characters")

    await message.reply_photo(
        photo=GTOPG_MEDIA,
        caption="\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_topgroups"),
                InlineKeyboardButton("🚮", callback_data=f"close:{message.from_user.id}")
            ]
        ])
    )

@app.on_callback_query(filters.regex(r"^close:(\d+)$"))
async def close_button(client: Client, cq: CallbackQuery):
    owner_id = int(cq.matches[0].group(1))
    if cq.from_user.id != owner_id:
        return await cq.answer("Only the command sender can close this!", show_alert=True)
    await cq.message.delete()

@app.on_callback_query(filters.regex("^refresh_topgroups$"))
async def refresh_topgroups(client: Client, cq: CallbackQuery):
    try:
        # Refresh the top groups data - same logic as command
        top_groups = await top_global_groups_collection.find().sort("total_characters", -1).limit(10).to_list(length=10)
        
        if not top_groups:
            pipeline = [
                {"$group": {
                    "_id": "$group_id", 
                    "total_characters": {"$sum": "$character_count"},
                    "group_name": {"$first": "$group_name"}
                }},
                {"$sort": {"total_characters": -1}},
                {"$limit": 10}
            ]
            top_groups = await group_user_totals_collection.aggregate(pipeline).to_list(length=10)
            
    except Exception as e:
        print(f"Error refreshing top groups: {e}")
        return await cq.answer("❌ Error refreshing top groups list.", show_alert=True)

    if not top_groups:
        return await cq.answer("❌ ɴᴏ ɢʀᴏᴜᴘ ᴅᴀᴛᴀ ᴀᴠᴀɪʟᴀʙʟᴇ.", show_alert=True)

    lines = [f"🏆 {style('**Top 10 Groups Ranking**')}\n"]
    
    for i, group in enumerate(top_groups, 1):
        group_name = group.get("group_name", "Unknown Group")
        total_chars = group.get("total_characters", 0)
        
        group_name_clean = group_name.replace("[", "").replace("]", "").replace("*", "")
        
        lines.append(f"{i}. {group_name_clean} ➾ {total_chars} characters")

    # Update the message with refreshed data
    await cq.message.edit_caption(
        caption="\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_topgroups"),
                InlineKeyboardButton("🚮", callback_data=f"close:{cq.from_user.id}")
            ]
        ])
    )
    await cq.answer("Top groups list refreshed! ✅")

@app.on_callback_query(filters.regex("^ani_count$"))
async def ani_count(client: Client, cq: CallbackQuery):
    uid = cq.from_user.id
    user = await user_collection.find_one({"id": uid})
    if not user:
        return await cq.answer("No characters found in your profile.", show_alert=True)

    # Ensure characters is an array
    characters = user.get("characters", [])
    if not isinstance(characters, list):
        characters = []

    ani_chars = [c for c in characters if isinstance(c, dict) and c.get("rarity") == "⚜️ Animated"]
    count = len(ani_chars)

    pipeline = [
        {"$addFields": {
            "characters": {
                "$cond": {
                    "if": {"$isArray": "$characters"},
                    "then": "$characters",
                    "else": []
                }
            }
        }},
        {"$unwind": "$characters"},
        {"$match": {"characters.rarity": "⚜️ Animated"}},
        {"$group": {"_id": "$id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    try:
        all_users = await user_collection.aggregate(pipeline).to_list(None)
    except Exception as e:
        print(f"Error in ani_count aggregation: {e}")
        return await cq.answer("Error calculating your rank.", show_alert=True)

    rank = next((i+1 for i, u in enumerate(all_users) if u["_id"] == uid), None)

    msg = f"🧬 You have: {count} animation characters.\n✨ Animation Rank: {rank}" if rank else f"⚜️ You have: {count} animation characters.\n✨ You're not ranked yet."
    await cq.answer(msg, show_alert=True)

@app.on_callback_query(filters.regex("^gtop_rank$"))
async def gtop_rank(client: Client, cq: CallbackQuery):
    uid = cq.from_user.id
    user = await user_collection.find_one({"id": uid})
    if not user:
        return await cq.answer("You don't have any characters yet.", show_alert=True)

    # Ensure characters is an array
    characters = user.get("characters", [])
    if not isinstance(characters, list):
        characters = []
    total = len(characters)

    pipeline = [
        {"$addFields": {
            "characters": {
                "$cond": {
                    "if": {"$isArray": "$characters"},
                    "then": "$characters",
                    "else": []
                }
            }
        }},
        {"$project": {"id": 1, "total": {"$size": "$characters"}}},
        {"$sort": {"total": -1}}
    ]
    
    try:
        all_users = await user_collection.aggregate(pipeline).to_list(None)
    except Exception as e:
        print(f"Error in gtop_rank aggregation: {e}")
        return await cq.answer("Error calculating your rank.", show_alert=True)

    rank = next((i+1 for i, u in enumerate(all_users) if (u.get("id") or u.get("_id")) == uid), None)

    msg = f"🌍 You have {total} characters.\n✨ Global Rank: {rank}" if rank else f"🌍 You have {total} characters.\n✨ You're not ranked yet."
    await cq.answer(msg, show_alert=True)
