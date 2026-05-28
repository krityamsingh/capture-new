from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
from datetime import datetime as dt
import random
from . import app, db, add, deduct, show, collection, user_collection, capsify
from .image_utils import is_image_valid, safe_send_photo, safe_edit_media

sdb = db.new_store
user_db = db.bought

def today():
    return str(dt.now()).split()[0]

rarity_prices = {
    "⚫ Common": 500,
    "🟤 Uncommon": 1000,
    "🟠 Rare": 2000,
    "🟣 Epic": 3500,
    "🟡 Legendary": 5000,
    "🏵️ Exotic": 7000,
    "🔮 Limited Edition": 8000,
    "🫧 Premium": 12000,
    "💮 Mythic": 15000,
    "🔱 Godly": 20000,
    "⚜️ Unique": 25000,
    "⚡ Eternal": 30000
}

async def get_character(id):
    character = await collection.find_one({"id": id}) or await collection.find_one({"id": str(id)})
    if not character:
        raise ValueError(capsify(f"Character with ID {id} not found."))
    return character

async def get_available_characters():
    characters = await collection.find().to_list(None)
    for char in characters:
        if "rarity" in char and char["rarity"] in rarity_prices:
            char["price"] = rarity_prices[char["rarity"]]
        elif "price" not in char:
            char["price"] = 0
    return characters

async def get_user_session(user_id: int):
    record = await sdb.find_one({"id": user_id})
    return record["data"] if record else None

async def update_user_session(user_id: int, data):
    await sdb.update_one({"id": user_id}, {"$set": {"data": data}}, upsert=True)

async def clear_user_session(user_id: int):
    await sdb.delete_one({"id": user_id})

async def update_user_bought(user_id: int, data):
    await user_db.update_one({"id": user_id}, {"$set": {"data": data}}, upsert=True)

async def get_user_bought(user_id: int):
    record = await user_db.find_one({"id": user_id})
    return record["data"] if record else None

async def format_character_info(character):
    if not character:
        raise ValueError(capsify("Invalid character data."))
    rarity_icon = character.get("rarity", "❓").strip()
    price = character.get("price", 0)
    return (
        character.get("img_url", ""),
        f"""
**🆔 ID:** `{character.get('id', 'Unknown')}`
**📛 Name:** {character.get('name', 'Unknown')}
**🎬 Anime:** {character.get('anime', 'Unknown')}
**🏷️ Rarity:** {rarity_icon} {character.get('rarity', 'Unknown')}
**💰 Price:** `{price} coins`
        """.strip()
    )

async def pick_random_characters():
    """
    Fetch all characters, skip those missing 'id' or with broken images,
    then return 3 random IDs from the valid pool.
    """
    characters = await get_available_characters()

    valid_chars = []
    for char in characters:
        if "id" not in char:          # skip malformed docs (fixes log: 'id' KeyError)
            continue
        img_url = char.get("img_url", "")
        if await is_image_valid(img_url):
            valid_chars.append(char)

    available_ids = [c["id"] for c in valid_chars]
    if len(available_ids) < 3:
        return None
    return random.sample(available_ids, 3)

async def validate_session_ids(selected_ids):
    """Returns True only if all 3 stored IDs still exist in the DB."""
    for cid in selected_ids:
        char = await collection.find_one({"id": cid}) or await collection.find_one({"id": str(cid)})
        if not char:
            return False
    return True

@app.on_message(filters.command(["store", "shop", "market"]))
async def store_handler(_, message):
    user_id = message.from_user.id
    session = await get_user_session(user_id)

    need_new_session = True

    if session and session[0] == today():
        stored_ids = session[1]
        if await validate_session_ids(stored_ids):
            need_new_session = False
            selected_ids = stored_ids

    if need_new_session:
        wait_msg = await message.reply_text("🔍 Loading today's store, please wait...")
        selected_ids = await pick_random_characters()
        await wait_msg.delete()

        if not selected_ids:
            return await message.reply_text(
                "⚠️ Not enough characters with valid images in the store right now. Try again later."
            )
        await update_user_session(user_id, [today(), selected_ids, 0])

    return await show_store_page(message, user_id, selected_ids, 0)

async def show_store_page(message, user_id, selected_ids, index):
    try:
        char = await get_character(selected_ids[index])
        img, caption = await format_character_info(char)
    except ValueError as e:
        return await message.reply_text(f"⚠️ Error: {e}")

    prev_index = (index - 1) % 3
    next_index = (index + 1) % 3

    markup = IKM([
        [
            IKB("⬅️ Prev", callback_data=f"page_{user_id}_{prev_index}"),
            IKB("🛒 Buy", callback_data=f"buy_{user_id}_{index}"),
            IKB("Next ➡️", callback_data=f"page_{user_id}_{next_index}")
        ],
        [IKB("🗑️ Close", callback_data=f"close_{user_id}")]
    ])

    await safe_send_photo(
        message.reply_photo,
        img,
        caption=f"**📖 Page {index+1}/3**\n\n{caption}",
        reply_markup=markup
    )

@app.on_callback_query(filters.regex(r"^page_"))
async def handle_page(_, query):
    parts = query.data.split("_")
    user_id = int(parts[1])
    index = int(parts[2])

    if user_id != query.from_user.id:
        return await query.answer("⛔ This is not for you!", show_alert=True)

    session = await get_user_session(user_id)
    if not session:
        return await query.answer("⚠️ Session expired. Use /store again.", show_alert=True)

    selected_ids = session[1]

    try:
        char = await get_character(selected_ids[index])
        img, caption = await format_character_info(char)
    except ValueError as e:
        return await query.answer(f"⚠️ Error: {e}", show_alert=True)

    prev_index = (index - 1) % 3
    next_index = (index + 1) % 3

    markup = IKM([
        [
            IKB("⬅️ Prev", callback_data=f"page_{user_id}_{prev_index}"),
            IKB("🛒 Buy", callback_data=f"buy_{user_id}_{index}"),
            IKB("Next ➡️", callback_data=f"page_{user_id}_{next_index}")
        ],
        [IKB("🗑️ Close", callback_data=f"close_{user_id}")]
    ])

    await safe_edit_media(query.message, img, reply_markup=markup)
    await query.edit_message_caption(
        caption=f"**📖 Page {index+1}/3**\n\n{caption}",
        reply_markup=markup
    )
    await query.answer()

@app.on_callback_query(filters.regex(r"^buy_"))
async def handle_purchase(_, query):
    parts = query.data.split("_")
    user_id = int(parts[1])
    char_index = int(parts[2])

    if user_id != query.from_user.id:
        return await query.answer("⛔ This is not for you!", show_alert=True)

    session = await get_user_session(user_id)
    if not session:
        return await query.answer("⚠️ Session expired. Use /store again.", show_alert=True)

    selected_ids, free_used = session[1], session[2]
    char_id = selected_ids[char_index]

    try:
        char = await get_character(char_id)
    except ValueError as e:
        return await query.answer(f"⚠️ Error: {e}", show_alert=True)

    if "price" not in char:
        char["price"] = rarity_prices.get(char.get("rarity", ""), 0)

    user_balance = await show(user_id)
    price = char.get("price", 0)

    if free_used < 3:
        cost = 0
        msg = f"🎉 **Free Purchase!**\n\nYou've received **{char['name']}** for free!"
        free_used += 1
    else:
        cost = price // 2
        if user_balance < cost:
            return await query.answer("❌ Not enough coins!", show_alert=True)
        msg = f"✅ **Purchase Successful!**\n\nCharacter **{char['name']}** bought for `{cost} coins`!"

    await deduct(user_id, cost)
    await update_user_session(user_id, [today(), selected_ids, free_used])

    await user_collection.update_one(
        {"id": user_id},
        {"$addToSet": {"characters": char}},
        upsert=True
    )

    await query.edit_message_caption(msg)
    await query.answer("✅ Purchase successful!", show_alert=True)

@app.on_callback_query(filters.regex(r"^close_"))
async def close_store(_, query):
    _, user_id = query.data.split("_")
    if int(user_id) == query.from_user.id:
        await query.message.delete()
    else:
        await query.answer("⛔ This is not for you!", show_alert=True)
