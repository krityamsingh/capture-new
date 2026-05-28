from pyrogram import Client, filters
from pyrogram.types import Message
from asyncio import sleep
import random
import string
from datetime import datetime, timedelta
from . import app, collection, user_collection
from Grabber.utils.character import ac  # ✅ Fixed: import ac from correct location

# Tiny caps font style
tiny_font = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    ' ': ' '
}

def convert_to_tiny(text):
    return ''.join(tiny_font.get(c.lower(), c) for c in text)

def generate_code(length=12):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ✅ Fixed: Use MongoDB for persistent code storage instead of in-memory dicts
# (in-memory dicts are wiped every bot restart)
from Grabber import db
codes_collection = db["redeem_codes"]
daily_codes_collection = db["daily_codes"]
user_cooldowns_collection = db["redeem_cooldowns"]


# ─────────────────────────────────────────────────────────────
# Helper: send a single photo or video (NOT reply_media_group)
# ✅ Fixed: reply_media_group is for sending multiple media at once
#           For a single item, use reply_photo / reply_video
# ─────────────────────────────────────────────────────────────
async def send_char_media(message: Message, caption: str, video_url: str, img_url: str):
    try:
        if video_url:
            await message.reply_video(video=video_url, caption=caption)
        elif img_url:
            await message.reply_photo(photo=img_url, caption=caption)
        else:
            await message.reply_text(caption)
    except Exception as e:
        await message.reply_text(f"⚠️ ᴍᴇᴅɪᴀ ᴇʀʀᴏʀ: {e}\n\n{caption}")


# ─────────────────────────────────────────────────────────────
# /gen — Generate character redeem code (Owner only)
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("gen") & filters.user(6118760915))
async def generate_character_code(client: Client, message: Message):
    args = message.text.split()

    if len(args) < 3:
        return await message.reply_text(
            convert_to_tiny("⚠️ ɴᴀɴɪ? ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ ᴅᴇsᴜ~!\nᴜsᴇ: /gen <character_id> <user_limit> (◠‿◠)")
        )

    try:
        char_id = int(args[1])
        user_limit = int(args[2])
    except ValueError:
        return await message.reply_text(
            convert_to_tiny("⚠️ ᴇʜʜʜ? ʙᴏᴛʜ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ ᴀɴᴅ ᴜsᴇʀ ʟɪᴍɪᴛ ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀs ᴅᴇsᴜ! (╥﹏╥)")
        )

    char = await collection.find_one({"$or": [{"id": char_id}, {"id": str(char_id)}]})
    if not char:
        return await message.reply_text(
            convert_to_tiny("⚠️ ᴍᴏᴜ ɪᴋᴇɴᴀɪ~! ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀ ғᴏᴜɴᴅ ᴡɪᴛʜ ᴛʜᴀᴛ ɪᴅ (´；ω；`)")
        )

    if not char.get("img_url") and not char.get("video_url"):
        return await message.reply_text(
            convert_to_tiny("⚠️ ᴏʜ ɴᴏ! ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs ɴᴏ ᴍᴇᴅɪᴀ ᴀᴛᴛᴀᴄʜᴇᴅ! (´･_･`)")
        )

    # Generate unique code (check DB)
    code = generate_code()
    while await codes_collection.find_one({"code": code}):
        code = generate_code()

    # ✅ Save to MongoDB so codes survive bot restarts
    await codes_collection.insert_one({
        "code": code,
        "char_id": char["id"],
        "char_name": char["name"],
        "anime": char["anime"],
        "rarity": char["rarity"],
        "img_url": char.get("img_url", ""),
        "video_url": char.get("video_url", ""),
        "user_limit": user_limit,
        "redeemed_by": [],
        "created_at": datetime.now()
    })

    caption = (
        f"🎟️ **ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ! ᴡᴀᴋᴀᴛᴛᴀ!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ᴄᴏᴅᴇ:** `{code}`\n"
        f"👤 **ᴜsᴇʀ ʟɪᴍɪᴛ:** `{user_limit}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 **ᴄʜᴀʀᴀᴄᴛᴇʀ:** `{char['name']}`\n"
        f"🎬 **ᴀɴɪᴍᴇ:** `{char['anime']}`\n"
        f"✨ **ʀᴀʀɪᴛʏ:** `{char['rarity']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **ᴜsᴇ /redeem {code} ᴛᴏ ᴄʟᴀɪᴍ**\n"
        f"❀.(*´▽`*)❀. sᴜᴘᴇʀ ᴋᴀᴡᴀɪɪ ᴅᴇsᴜ ɴᴇ~!\n"
    )

    await send_char_media(message, caption, char.get("video_url", ""), char.get("img_url", ""))


# ─────────────────────────────────────────────────────────────
# /dailycode — Get a daily character code
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("dailycode"))
async def daily_code(client: Client, message: Message):
    user_id = message.from_user.id
    now = datetime.now()

    # ✅ Check cooldown from DB
    cooldown_doc = await user_cooldowns_collection.find_one({"user_id": user_id})
    if cooldown_doc:
        last_used = cooldown_doc["last_used"]
        if now - last_used < timedelta(hours=24):
            remaining = (last_used + timedelta(hours=24)) - now
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes, seconds = divmod(rem, 60)
            return await message.reply_text(
                convert_to_tiny(
                    f"⚠️ ᴍᴀᴛᴛᴇ ᴋᴜᴅᴀsᴀɪ~! ᴡᴀɪᴛ {hours}ʜ {minutes}ᴍ {seconds}s ʙᴇғᴏʀᴇ ɴᴇxᴛ ᴅᴀɪʟʏ ᴄᴏᴅᴇ!\n"
                    "ᴀʀɪɢᴀᴛᴏᴜ ɢᴏᴢᴀɪᴍᴀsᴜ (◕‿◕✿)"
                )
            )

    rarity_weights = {
        "🟠 Rare": 60,
        "🔮 Limited Edition": 30,
        "🟡 Legendary": 10
    }
    rarity = random.choices(
        list(rarity_weights.keys()),
        weights=list(rarity_weights.values()),
        k=1
    )[0]

    char_list = await collection.aggregate([
        {"$match": {"rarity": rarity}},
        {"$sample": {"size": 1}}
    ]).to_list(1)

    if not char_list:
        return await message.reply_text(
            convert_to_tiny("⚠️ sᴜᴍɪᴍᴀsᴇɴ~! ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀs ғᴏᴜɴᴅ ғᴏʀ ᴛʜɪs ʀᴀʀɪᴛʏ. ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ (´；ω；`)")
        )

    char = char_list[0]
    code = generate_code()
    while await daily_codes_collection.find_one({"code": code}):
        code = generate_code()

    # ✅ Save to DB
    await daily_codes_collection.insert_one({
        "code": code,
        "char_id": char["id"],
        "char_name": char["name"],
        "anime": char["anime"],
        "rarity": char["rarity"],
        "img_url": char.get("img_url", ""),
        "video_url": char.get("video_url", ""),
        "expires_at": now + timedelta(hours=24),
        "redeemed": False
    })

    # ✅ Update cooldown in DB
    await user_cooldowns_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_used": now}},
        upsert=True
    )

    caption = (
        f"🎉 **ᴅᴀɪʟʏ ᴀɴɪᴍᴇ ʀᴇᴡᴀʀᴅ ɢᴇᴛᴛᴏ ᴅᴀ!**\n"
        f"✨ **ʏᴏᴜ ɢᴏᴛ ᴀ {rarity} ᴄʜᴀʀᴀᴄᴛᴇʀ ᴄᴏᴅᴇ!**\n"
        f"🆔 **ᴄᴏᴅᴇ:** `{code}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 **ᴄʜᴀʀᴀᴄᴛᴇʀ:** `{char['name']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **ᴜsᴇ /redeem {code} ᴛᴏ ᴄʟᴀɪᴍ**\n"
        f"❀.(*´▽`*)❀. ɢᴀɴʙᴀᴛᴛᴇ ɴᴇ~!\n"
    )

    await send_char_media(message, caption, char.get("video_url", ""), char.get("img_url", ""))


# ─────────────────────────────────────────────────────────────
# /redeem — Redeem a code
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("redeem"))
async def redeem_character_code(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.reply_text(
            convert_to_tiny("⚠️ ɴᴀɴɪ? ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀ ᴄᴏᴅᴇ ᴅᴇsᴜ~!\nᴜsᴇ: /redeem <code> (◕‿◕)")
        )

    code = args[1].upper()

    # ✅ Look up from MongoDB
    code_data = await codes_collection.find_one({"code": code})
    is_daily = False

    if not code_data:
        code_data = await daily_codes_collection.find_one({"code": code})
        is_daily = True

    if not code_data:
        return await message.reply_text(
            convert_to_tiny("⚠️ ɪᴋᴇɴᴀɪ! ɪɴᴠᴀʟɪᴅ ᴄᴏᴅᴇ ᴅᴇsᴜ~! ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ (´；ω；`)")
        )

    if is_daily:
        if datetime.now() > code_data["expires_at"]:
            await daily_codes_collection.delete_one({"code": code})
            return await message.reply_text(
                convert_to_tiny("⚠️ ᴏʜ ɴᴏ! ᴛʜɪs ᴄᴏᴅᴇ ʜᴀs ᴇxᴘɪʀᴇᴅ ᴅᴇsᴜ~! ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ ᴡɪᴛʜ /dailycode (╥_╥)")
            )
        if code_data["redeemed"]:
            return await message.reply_text(
                convert_to_tiny("⚠️ sᴜᴍɪᴍᴀsᴇɴ~! ᴛʜɪs ᴄᴏᴅᴇ ʜᴀs ᴀʟʀᴇᴀᴅʏ ʙᴇᴇɴ ʀᴇᴅᴇᴇᴍᴇᴅ (´･_･`)")
            )
    else:
        if user_id in code_data.get("redeemed_by", []):
            return await message.reply_text(
                convert_to_tiny("⚠️ ᴀʀᴇ? ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ʀᴇᴅᴇᴇᴍᴇᴅ ᴛʜɪs ᴄᴏᴅᴇ ᴅᴇsᴜ~! (◠‿◠)")
            )
        if len(code_data.get("redeemed_by", [])) >= code_data["user_limit"]:
            return await message.reply_text(
                convert_to_tiny("⚠️ ɢᴏᴍᴇɴ ᴅᴇsᴜ~! ᴛʜɪs ᴄᴏᴅᴇ ʜᴀs ʀᴇᴀᴄʜᴇᴅ ɪᴛs ᴜsᴇʀ ʟɪᴍɪᴛ! (╯︵╰,)")
            )

    # Check if user already owns the character
    user_data = await user_collection.find_one({"id": user_id})
    owned_ids = [str(c.get("id", "")) for c in user_data.get("characters", []) if isinstance(c, dict)] if user_data else []
    if str(code_data["char_id"]) in owned_ids:
        return await message.reply_text(
            convert_to_tiny("⚠️ ᴀʀᴇ ᴍᴏ~? ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴏᴡɴ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ ᴅᴇsᴜ! (＾▽＾)")
        )

    try:
        await ac(user_id, code_data["char_id"])

        # ✅ Mark redeemed in DB
        if is_daily:
            await daily_codes_collection.update_one({"code": code}, {"$set": {"redeemed": True}})
        else:
            await codes_collection.update_one({"code": code}, {"$push": {"redeemed_by": user_id}})

        caption = (
            f"🎉 **sᴜᴘᴇʀ ᴡᴀᴋᴀʀᴜ! ᴄᴏᴅᴇ ʀᴇᴅᴇᴇᴍᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!**\n"
            f"🍀 **ᴄʜᴀʀᴀᴄᴛᴇʀ:** `{code_data['char_name']}`\n"
            f"⛩️ **ᴀɴɪᴍᴇ:** `{code_data['anime']}`\n"
            f"🍁 **ʀᴀʀɪᴛʏ:** `{code_data['rarity']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❀.(*´▽`*)❀. ᴏᴍᴇᴅᴇᴛᴏᴜ ɢᴏᴢᴀɪᴍᴀsᴜ~!\n"
        )

        await send_char_media(
            message, caption,
            code_data.get("video_url", ""),
            code_data.get("img_url", "")
        )

    except Exception as e:
        print(f"Error in redeem_character_code: {e}")
        await message.reply_text(
            convert_to_tiny("⚠️ ʏᴀʙᴀɪ! ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ ᴅᴇsᴜ~! (；一_一)")
        )


# ─────────────────────────────────────────────────────────────
# /checkcode — Check code info
# ─────────────────────────────────────────────────────────────
@app.on_message(filters.command("checkcode"))
async def check_code_info(client: Client, message: Message):
    args = message.text.split()

    if len(args) < 2:
        return await message.reply_text(
            convert_to_tiny("⚠️ ɴᴀɴɪ? ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀ ᴄᴏᴅᴇ ᴅᴇsᴜ~!\nᴜsᴇ: /checkcode <code> (◠‿◠)")
        )

    code = args[1].upper()

    code_data = await codes_collection.find_one({"code": code})
    is_daily = False

    if not code_data:
        code_data = await daily_codes_collection.find_one({"code": code})
        is_daily = True

    if not code_data:
        return await message.reply_text(
            convert_to_tiny("⚠️ ᴍᴏᴜ ɪᴋᴇɴᴀɪ~! ɪɴᴠᴀʟɪᴅ ᴄᴏᴅᴇ ᴅᴇsᴜ! (´･_･`)")
        )

    if is_daily:
        code_type = "ᴅᴀɪʟʏ ᴄᴏᴅᴇ"
        expires_at = code_data.get("expires_at")
        now = datetime.now()
        if expires_at and now < expires_at:
            remaining_s = int((expires_at - now).total_seconds())
            expires_in = f"{remaining_s // 3600}ʜ"
            status = "✅ ᴀᴄᴛɪᴠᴇ"
        else:
            expires_in = "ᴇxᴘɪʀᴇᴅ"
            status = "❌ ᴇxᴘɪʀᴇᴅ"
        redeemed = "ʏᴇs" if code_data.get("redeemed") else "ɴᴏ"
    else:
        code_type = "ᴀᴄᴛɪᴠᴇ ᴄᴏᴅᴇ"
        status = "✅ ᴀᴄᴛɪᴠᴇ"
        redeemed = f"{len(code_data.get('redeemed_by', []))}/{code_data['user_limit']}"
        expires_in = "ɴᴏɴᴇ"

    caption = (
        f"🔍 **ᴀɴɪᴍᴇ ᴄᴏᴅᴇ ɪɴғᴏʀᴍᴀᴛɪᴏɴ**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌸 **ᴄᴏᴅᴇ ᴛʏᴘᴇ:** `{code_type}`\n"
        f"🆔 **ᴄᴏᴅᴇ:** `{code}`\n"
        f"📅 **sᴛᴀᴛᴜs:** `{status}`\n"
        f"⏳ **ᴇxᴘɪʀᴇs ɪɴ:** `{expires_in}`\n"
        f"🔖 **ʀᴇᴅᴇᴇᴍᴇᴅ:** `{redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 **ᴄʜᴀʀᴀᴄᴛᴇʀ:** `{code_data['char_name']}`\n"
        f"🎬 **ᴀɴɪᴍᴇ:** `{code_data['anime']}`\n"
        f"✨ **ʀᴀʀɪᴛʏ:** `{code_data['rarity']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 ᴜsᴇ /redeem {code} ᴛᴏ ᴄʟᴀɪᴍ\n"
        f"❀.(*´▽`*)❀. ɢᴀɴʙᴀᴛᴛᴇ ɴᴇ~!\n"
    )

    await message.reply_text(caption)
