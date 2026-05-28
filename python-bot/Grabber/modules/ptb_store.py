import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from Grabber import collection, user_collection, app

LOG_CHANNEL_ID = -1003248939428
store_rarities = ["🟡 Legendary", "🟠 Rare", "🔮 Limited Edition"]
DAILY_LIMIT = 15  # Daily purchase limit

rarity_prices = {
    "🟡 Legendary": random.randint(50000, 89900),
    "🟠 Rare": random.randint(50000, 89900),
    "🔮 Limited Edition": random.randint(50000, 89900)
}

store_cache = {}
store_action_locks = {}
user_purchase_data = {}  # To track daily purchases

async def normalize_balance(user_id):
    user = await user_collection.find_one({"id": user_id})
    balance = user.get("balance", 0)
    if isinstance(balance, str):
        try:
            numeric = int(balance.replace(",", "").split()[0])
            await user_collection.update_one({"id": user_id}, {"$set": {"balance": numeric}})
        except:
            await user_collection.update_one({"id": user_id}, {"$set": {"balance": 0}})

async def check_daily_limit(user_id):
    now = datetime.now()
    user_data = user_purchase_data.get(user_id, {"count": 0, "reset_time": now + timedelta(hours=24)})
    
    if now >= user_data["reset_time"]:
        user_data = {"count": 0, "reset_time": now + timedelta(hours=24)}
        user_purchase_data[user_id] = user_data
    
    return user_data["count"] >= DAILY_LIMIT, user_data

async def increment_purchase_count(user_id):
    limit_reached, user_data = await check_daily_limit(user_id)
    user_data["count"] += 1
    user_purchase_data[user_id] = user_data
    return user_data["count"]

@app.on_message(filters.command("store"))
async def open_store(client, message):
    user_id = message.from_user.id
    chars = await get_store_characters()
    store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": None}
    await send_store_waifu(client, message, user_id, edit=False)

async def get_store_characters():
    chars = await collection.aggregate([
        {"$match": {"rarity": {"$in": store_rarities}}},
        {"$sample": {"size": 30}}  # Show more options in store
    ]).to_list(length=30)
    for char in chars:
        char["price"] = rarity_prices.get(char.get("rarity", ""), random.randint(50000, 89900))
    return chars

def get_store_keyboard(user_id, limit_reached=False):
    if limit_reached:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➡ ɴᴇxᴛ", callback_data="store_next")
            ]
        ])
    else:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛒 ʙᴜʏ", callback_data="store_buy"),
                InlineKeyboardButton("➡ ɴᴇxᴛ", callback_data="store_next")
            ]
        ])

async def send_store_waifu(client, msg_or_query, user_id, edit=True):
    data = store_cache.get(user_id)
    if not data or not data["waifus"]:
        chars = await get_store_characters()
        store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": None}
        data = store_cache.get(user_id)
        
    index = data["index"]
    waifus = data["waifus"]

    if not waifus or index >= len(waifus):
        store_cache[user_id]["index"] = 0
        index = 0
        if not waifus:
            chars = await get_store_characters()
            store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": None}
            data = store_cache.get(user_id)
            waifus = data["waifus"]

    waifu = waifus[index]
    limit_reached, _ = await check_daily_limit(user_id)
    
    caption = (
        f"🐠 Ohayou! Check out {waifu['name']}\n\n"
        f"{waifu['anime']}\n"
        f"id: {waifu.get('id', 'N/A')}\n"
        f"𝙍𝘼𝙍𝙄𝙏𝙔: {waifu['rarity']}\n"
        f"Prize: {waifu['price']} tokens\n\n"
    )
    
    if limit_reached:
        caption += f"⚠️ You've reached your daily limit of {DAILY_LIMIT} purchases!\n"
        caption += "Come back tomorrow to buy more characters."
    else:
        purchases_today = user_purchase_data.get(user_id, {}).get("count", 0)
        caption += f"Purchases today: {purchases_today}/{DAILY_LIMIT}"

    try:
        if edit:
            message = await client.edit_message_media(
                chat_id=msg_or_query.message.chat.id,
                message_id=msg_or_query.message.id,
                media=InputMediaPhoto(waifu["img_url"], caption=caption),
                reply_markup=get_store_keyboard(user_id, limit_reached)
            )
        else:
            message = await msg_or_query.reply_photo(
                photo=waifu["img_url"],
                caption=caption,
                reply_markup=get_store_keyboard(user_id, limit_reached)
            )
            store_cache[user_id]["message_id"] = message.id
    except Exception as e:
        print(f"Error in send_store_waifu: {e}")

def ensure_owner(func):
    async def wrapper(client, query: CallbackQuery):
        user_id = query.from_user.id
        data = store_cache.get(user_id)
        if not data or data.get("owner_id") != user_id:
            await query.answer("⚠️ This isn't your store!", show_alert=True)
            return
        await func(client, query)
    return wrapper

async def with_lock(user_id, func, *args, **kwargs):
    if store_action_locks.get(user_id):
        return
    store_action_locks[user_id] = True
    try:
        await func(*args, **kwargs)
    finally:
        store_action_locks.pop(user_id, None)

@app.on_callback_query(filters.regex("^store_next$"))
@ensure_owner
async def next_waifu(client, query: CallbackQuery):
    await with_lock(query.from_user.id, _next_waifu, client, query)

async def _next_waifu(client, query):
    user_id = query.from_user.id
    data = store_cache.get(user_id)
    if not data or not data["waifus"]:
        chars = await get_store_characters()
        store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": query.message.id}
        data = store_cache.get(user_id)
    
    data["index"] = (data["index"] + 1) % len(data["waifus"])
    await send_store_waifu(client, query, user_id)

@app.on_callback_query(filters.regex("^store_buy$"))
@ensure_owner
async def buy_waifu(client, query: CallbackQuery):
    await with_lock(query.from_user.id, _buy_waifu, client, query)

async def _buy_waifu(client, query):
    user_id = query.from_user.id
    data = store_cache.get(user_id)
    if not data or not data["waifus"]:
        chars = await get_store_characters()
        store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": query.message.id}
        data = store_cache.get(user_id)
        waifus = data["waifus"]
    else:
        waifus = data["waifus"]

    index = data["index"]
    if index >= len(waifus):
        return await query.answer("⚠️ Invalid selection!", show_alert=True)

    limit_reached, user_data = await check_daily_limit(user_id)
    if limit_reached:
        return await query.answer(
            f"You've reached your daily limit of {DAILY_LIMIT} purchases!",
            show_alert=True
        )

    waifu = waifus[index]
    price = waifu.get("price", random.randint(50000, 89900))
    await normalize_balance(user_id)

    user = await user_collection.find_one({"id": user_id}) or {}
    balance = float(user.get("balance", 0))

    if balance < price:
        await query.answer("❌ Insufficient tokens!", show_alert=True)
        return

    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -price}})
    await user_collection.update_one({"id": user_id}, {"$push": {"characters": waifu}}, upsert=True)
    await increment_purchase_count(user_id)
    await query.answer(f"🎉 You bought {waifu['name']}!", show_alert=False)

    try:
        await client.send_photo(
            chat_id=user_id,
            photo=waifu["img_url"],
            caption=f"✨ Purchase Successful! ✨\n\n"
                   f"🎀 Character: {waifu['name']}\n"
                   f"📺 Anime: {waifu['anime']}\n"
                   f"💎 Rarity: {waifu['rarity']}\n"
                   f"💰 Price Paid: {price} tokens\n\n"
                   f"Purchases today: {user_purchase_data.get(user_id, {}).get('count', 1)}/{DAILY_LIMIT}\n\n"
                   f"Thank you for shopping with us!"
        )
    except Exception as e:
        print(f"Error sending purchase confirmation: {e}")

    try:
        await client.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"🛍️ New Purchase 🛍️\n\n"
                f"👤 Buyer: {query.from_user.mention}\n"
                f"✨ Character: {waifu['name']}\n"
                f"📺 Anime: {waifu['anime']}\n"
                f"💎 Rarity: {waifu['rarity']}\n"
                f"💰 Price: {price} tokens\n"
                f"#️⃣ Purchases today: {user_purchase_data.get(user_id, {}).get('count', 1)}/{DAILY_LIMIT}"
        )
    except Exception as e:
        print(f"Error logging purchase: {e}")

    # Remove purchased waifu and update index
    data["waifus"].pop(index)
    if index >= len(data["waifus"]):
        data["index"] = max(0, len(data["waifus"]) - 1)
    
    if not data["waifus"]:
        chars = await get_store_characters()
        store_cache[user_id] = {"index": 0, "waifus": chars, "owner_id": user_id, "message_id": query.message.id}
        await send_store_waifu(client, query, user_id)
        return

    await send_store_waifu(client, query, user_id)
