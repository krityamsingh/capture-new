from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Grabber import collection, user_collection, app

# Define constants for rarity types (avoid typos)
RARITY_ANIMATION = "🧬 Animation"

# -------------------------------------------------------------------
# /p command – Display waifu info with inline buttons
# -------------------------------------------------------------------
@app.on_message(filters.command("p"))
async def check_waifu(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a waifu ID.\nUsage: `/p 1234`",
            quote=True
        )

    try:
        waifu_id = int(message.command[1])
    except ValueError:
        return await message.reply_text(
            "Invalid ID format. Please enter a numeric waifu ID.",
            quote=True
        )

    # Fetch waifu from database
    waifu = await collection.find_one({"id": waifu_id})
    if not waifu:
        return await message.reply_text("Character not found with this ID!", quote=True)

    # Owner count (total number of owners, not copies)
    owners = waifu.get("owners", 0)
    owners_text = owners if owners else "No Owners"

    # Caption
    caption = (
        f"✨ **{waifu['name']}**\n"
        f"📺 **Anime:** {waifu['anime']}\n"
        f"🎗 **Rarity:** {waifu['rarity']}\n"
        f"🆔 **ID:** {waifu['id']}\n"
        f"👥 **Owners:** {owners_text}"
    )

    # Inline buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏆 Top 10 Seizers", callback_data=f"top10_{waifu_id}"),
            InlineKeyboardButton("📦 How Many I Have", callback_data=f"have_{waifu_id}")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="waifu_close")]
    ])

    # Determine media type and URL
    is_animation = waifu.get("rarity") == RARITY_ANIMATION
    media_url = waifu.get("video_url") if is_animation else waifu.get("img_url")

    if not media_url:
        # Fallback if media URL is missing
        return await message.reply_text(
            f"⚠️ Media URL not found for this waifu.\n\n{caption}",
            reply_markup=buttons
        )

    # Send media with error handling
    try:
        if is_animation:
            await message.reply_video(
                video=media_url,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await message.reply_photo(
                photo=media_url,
                caption=caption,
                reply_markup=buttons
            )
    except Exception as e:
        # If sending fails, send only the text with the buttons
        await message.reply_text(
            f"❌ Failed to send media: {e}\n\n{caption}",
            reply_markup=buttons
        )

# -------------------------------------------------------------------
# Callback: Top 10 Seizers of a waifu
# -------------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^top10_(\d+)$"))
async def show_top10_seizers(client: Client, query: CallbackQuery):
    waifu_id = int(query.matches[0].group(1))
    waifu = await collection.find_one({"id": waifu_id})

    if not waifu:
        await query.answer("Waifu not found!", show_alert=True)
        return

    waifu_id_str = str(waifu_id)
    # Aggregate top 10 users by number of copies owned
    pipeline = [
        {"$match": {"$or": [{"characters.id": waifu_id}, {"characters.id": waifu_id_str}]}},
        {"$unwind": "$characters"},
        {"$match": {"$or": [{"characters.id": waifu_id}, {"characters.id": waifu_id_str}]}},
        {"$group": {
            "_id": "$id",
            "count": {"$sum": 1},
            "first_name": {"$first": "$first_name"},
            "last_name": {"$first": "$last_name"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    cursor = user_collection.aggregate(pipeline)

    text = f"🏆 **Top 10 Seizers of {waifu['name']}**\n\n"
    rank = 1
    async for user_data in cursor:
        user_id = user_data["_id"]
        count = user_data["count"]
        first_name = user_data.get("first_name") or "User"
        last_name = user_data.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            full_name = f"User {user_id}"
        mention = f"[{full_name}](tg://user?id={user_id})"
        text += f"{rank}. {mention} — `{count}` owned\n"
        rank += 1

    if rank == 1:
        text += "No collectors found yet."

    await query.answer()
    await query.message.reply_text(text)

# -------------------------------------------------------------------
# Callback: How many copies the current user owns
# -------------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^have_(\d+)$"))
async def show_user_count(client: Client, query: CallbackQuery):
    waifu_id = int(query.matches[0].group(1))
    user_id = query.from_user.id

    user_data = await user_collection.find_one({"$or": [{"id": user_id}, {"id": str(user_id)}]})
    count = 0
    if user_data:
        characters_list = user_data.get("characters") or user_data.get("waifus") or []
        count = sum(
            1 for c in characters_list
            if str(c.get("id", "")) == str(waifu_id)
        )

    await query.answer()
    await query.message.reply_text(
        f"📦 You own `{count}` copy/copies of this character."
    )

# -------------------------------------------------------------------
# Callback: Close the waifu info message
# -------------------------------------------------------------------
@app.on_callback_query(filters.regex("^waifu_close$"))
async def close_check_message(client: Client, query: CallbackQuery):
    await query.message.delete()
    await query.answer()
