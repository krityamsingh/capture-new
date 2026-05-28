import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    InputMediaPhoto, InputMediaVideo
)
from Grabber import collection, user_collection, app  # Import user_collection also

# Updated rarity order
rarity_order = [
    "🔴 Common", "🔵 Uncommon", "🟠 Rare", "⚪ Epic", "🟡 Legendary", 
    "🔮 Limited Edition", "🫧 Premium", "🏵️ Exotic", 
    "🌼 Celebrity", "🎐 Crystal", "🍹 Neon", "🧿 Supreme",
    "⚡ Thundra", "🛸 Galvoria",
    "⚜️ Animated"
]

# Session data
user_data = {}

# /rarity command
@app.on_message(filters.command("rarity"))
async def show_rarity_menu(client, message):
    keyboard = []
    for i in range(0, len(rarity_order), 3):
        row = [
            InlineKeyboardButton(rarity_order[j], callback_data=f"rarity_menu_{rarity_order[j]}")
            for j in range(i, min(i + 3, len(rarity_order)))
        ]
        keyboard.append(row)
    await message.reply_text(
        "✨ **Select a Rarity to Explore Characters:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# /myrarity command - NEW FEATURE
@app.on_message(filters.command("myrarity"))
async def show_my_rarity_menu(client, message):
    user_id = message.from_user.id
    
    # Check if user has any characters
    user_characters = await user_collection.find({"user_id": user_id}).to_list(length=1)
    if not user_characters:
        await message.reply_text("You don't own any characters yet!")
        return
    
    keyboard = []
    for i in range(0, len(rarity_order), 3):
        row = [
            InlineKeyboardButton(rarity_order[j], callback_data=f"myrarity_menu_{rarity_order[j]}")
            for j in range(i, min(i + 3, len(rarity_order)))
            if await user_collection.count_documents({"user_id": user_id, "rarity": rarity_order[j]}) > 0
        ]
        if row:  # Only add row if there are buttons
            keyboard.append(row)
    
    if not keyboard:
        await message.reply_text("You don't own any characters across rarities!")
        return
    
    await message.reply_text(
        "✨ **Select a Rarity to View Your Characters:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Handle global rarity selection
@app.on_callback_query(filters.regex("^rarity_menu_"))
async def global_rarity_selection(client, query: CallbackQuery):
    rarity = query.data.split("_", 2)[2]
    waifus = await collection.find({"rarity": rarity}).to_list(length=1000)
    if not waifus:
        await query.answer("No characters found in this rarity!", show_alert=True)
        return
    user_data[query.from_user.id] = {
        "index": 0,
        "waifus": waifus,
        "mode": "global",
        "rarity": rarity
    }
    await query.message.delete()
    await send_waifu(client, query.message, query.from_user.id)

# Handle user rarity selection
@app.on_callback_query(filters.regex("^myrarity_menu_"))
async def user_rarity_selection(client, query: CallbackQuery):
    rarity = query.data.split("_", 2)[2]
    user_id = query.from_user.id

    # Fetch user's owned characters
    owned = await user_collection.find({"user_id": user_id, "rarity": rarity}).to_list(length=1000)
    if not owned:
        await query.answer("You don't own any characters of this rarity yet!", show_alert=True)
        return

    # Map to character list (pull details from collection)
    waifu_ids = [x["char_id"] for x in owned]
    waifus = await collection.find({"id": {"$in": waifu_ids}}).to_list(length=1000)

    # Attach owned counts
    char_count_map = {x["char_id"]: x["count"] for x in owned}
    for waifu in waifus:
        waifu["owned_count"] = char_count_map.get(waifu.get("id"), 0)

    user_data[user_id] = {
        "index": 0,
        "waifus": waifus,
        "mode": "user",
        "rarity": rarity
    }
    await query.message.delete()
    await send_waifu(client, query.message, user_id)

# Send waifu card
async def send_waifu(client, message, user_id):
    data = user_data.get(user_id)
    if not data:
        return
    
    waifus = data["waifus"]
    index = data["index"]
    rarity = data["rarity"]
    mode = data["mode"]
    waifu = waifus[index]

    # Global owners count
    owners = waifu.get("owners", 0)
    owners_text = f"{owners} users" if owners else "No Owners"

    # User-owned count
    owned_text = ""
    if mode == "user":
        owned_count = waifu.get("owned_count", 0)
        owned_text = f"\n🗃 **You Own:** {owned_count} copies"

    text = (
        f"✨ **{waifu['name']}**\n"
        f"📺 **Anime:** {waifu.get('anime', 'Unknown')}\n"
        f"🎗 **Rarity:** {rarity}\n"
        f"🆔 **ID:** {waifu.get('id', 'Unknown')}\n"
        f"{owned_text}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅ Previous", callback_data="waifu_prev"),
            InlineKeyboardButton("➡ Next", callback_data="waifu_next")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="waifu_close")]
    ])

    # Check media type
    is_video = rarity == "⚜️ Animated"
    media_url = waifu.get("video_url") if is_video else waifu.get("img_url")
    media_type = InputMediaVideo if is_video else InputMediaPhoto

    try:
        await message.edit_media(
            media=media_type(media=media_url, caption=text),
            reply_markup=keyboard
        )
    except Exception:
        if is_video:
            await message.reply_video(video=media_url, caption=text, reply_markup=keyboard)
        else:
            await message.reply_photo(photo=media_url, caption=text, reply_markup=keyboard)

# Navigation handler
@app.on_callback_query(filters.regex("^waifu_(next|prev)"))
async def navigate_waifus(client, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_data.get(user_id)
    if not data:
        return
    
    if query.data == "waifu_next":
        data["index"] = (data["index"] + 1) % len(data["waifus"])
    else:
        data["index"] = (data["index"] - 1) % len(data["waifus"])
    
    await send_waifu(client, query.message, user_id)

# Close button handler
@app.on_callback_query(filters.regex("^waifu_close"))
async def close_waifu_view(client, query: CallbackQuery):
    await query.message.delete()
    user_data.pop(query.from_user.id, None)
