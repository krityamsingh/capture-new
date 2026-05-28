from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random, time
from . import app, user_collection

# Tiny caps formatter
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ', ' ': ' ', '!': '!', '?': '?', '.': '.', ',': ','
}
def to_tiny_caps(text: str) -> str:
    return ''.join(TINY_CAPS.get(c.lower(), c) for c in text)

LUCKY_GAMES = {}
PLAY_TRACKER = {}
COOLDOWN_TIME = 120
LUCKYBOX_IMG = "https://files.catbox.moe/hpogb7.jpg"

async def ensure_numeric_rubies(user_id):
    user_data = await user_collection.find_one({"id": user_id})
    if user_data and isinstance(user_data.get("rubies"), str):
        try:
            rubies = int(user_data["rubies"])
        except ValueError:
            rubies = 0
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"rubies": rubies}}
        )

@app.on_message(filters.command("luckybox"))
async def luckybox_game(client: Client, message: Message):
    user = message.from_user
    if not user:
        return await message.reply_text(to_tiny_caps("⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇᴛ ᴜꜱᴇʀ ɪɴꜰᴏ."))

    user_id = user.id
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text(to_tiny_caps("❗ ᴜꜱᴀɢᴇ:\n/luckybox <ᴀᴍᴏᴜɴᴛ>"))

    amount = int(args[1])
    if amount <= 0:
        return await message.reply_text(to_tiny_caps("⚠️ ᴇɴᴛᴇʀ ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ."))

    now = time.time()
    times = PLAY_TRACKER.get(user_id, [])
    times = [t for t in times if now - t < COOLDOWN_TIME]
    if len(times) >= 2:
        wait = int(COOLDOWN_TIME - (now - times[0]))
        return await message.reply_text(to_tiny_caps(f"⏳ ᴡᴀɪᴛ {wait}s ʙᴇꜰᴏʀᴇ ᴘʟᴀʏɪɴɢ ᴀɢᴀɪɴ."))

    await ensure_numeric_rubies(user_id)
    user_data = await user_collection.find_one({"id": user_id})
    user_rubies = user_data.get("rubies", 0) if user_data else 0

    if user_rubies < amount:
        return await message.reply_text(to_tiny_caps("❌ ɴᴏᴛ ᴇɴᴏᴜɢʜ ʀᴜʙɪᴇꜱ ᴛᴏ ᴘʟᴀʏ."))

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"rubies": -amount},
            "$set": {"first_name": user.first_name}
        }
    )
    await user_collection.update_one(
        {"id": user_id},
        {"$setOnInsert": {"rubies": 0}},
        upsert=True
    )

    times.append(now)
    PLAY_TRACKER[user_id] = times

    grid = [False] * 9
    for _ in range(3):
        while True:
            i = random.randint(0, 8)
            if not grid[i]:
                grid[i] = True
                break

    LUCKY_GAMES[user_id] = {
        "grid": grid,
        "revealed": [False]*9,
        "found": 0,
        "chances": 3,
        "amount": amount
    }

    keyboard = build_luckybox_keyboard(user_id)
    await message.reply_photo(
        photo=LUCKYBOX_IMG,
        caption=to_tiny_caps(f"🎲 ᴘɪᴄᴋ ᴀ ʙᴏx ᴛᴏ ғɪɴᴅ 💎\nᴇɴᴛʀʏ ғᴇᴇ: {amount} ʀᴜʙɪᴇꜱ\nᴄᴏʟʟᴇᴄᴛ 3 ᴛᴏ ᴡɪɴ (2x-10x ʀᴇᴡᴀʀᴅ)"),
        reply_markup=keyboard
    )

def build_luckybox_keyboard(user_id):
    buttons = []
    game = LUCKY_GAMES.get(user_id)
    for row in range(3):
        row_buttons = []
        for col in range(3):
            idx = row * 3 + col
            label = "❔" if not game["revealed"][idx] else ("💎" if game["grid"][idx] else "❌")
            row_buttons.append(InlineKeyboardButton(label, callback_data=f"luckybox_{user_id}_{idx}"))
        buttons.append(row_buttons)
    return InlineKeyboardMarkup(buttons)

@app.on_callback_query(filters.regex(r"^luckybox_(\d+)_(\d+)$"))
async def luckybox_click(client: Client, query: CallbackQuery):
    uid, index = int(query.matches[0].group(1)), int(query.matches[0].group(2))
    user = query.from_user

    if uid != user.id or uid not in LUCKY_GAMES:
        return await query.answer("Not your game!", show_alert=True)

    game = LUCKY_GAMES[uid]
    if game["revealed"][index]:
        return await query.answer("Already picked!", show_alert=True)

    game["revealed"][index] = True
    is_diamond = game["grid"][index]

    if is_diamond:
        game["found"] += 1
        await query.answer("You got a 💎!", show_alert=True)
    else:
        game["chances"] -= 1
        await query.answer("❌ No diamond!", show_alert=True)

    if game["found"] >= 3:
        base_amount = game["amount"]
        multiplier = random.randint(2, 10)
        reward = base_amount * multiplier

        del LUCKY_GAMES[uid]
        await query.message.edit_caption(
            to_tiny_caps(f"🎉 ᴄᴏɴɢʀᴀᴛꜱ! ʏᴏᴜ ғᴏᴜɴᴅ 3 💎!\nʀᴇᴡᴀʀᴅ: {reward} ʀᴜʙɪᴇꜱ ({multiplier}x)"),
            reply_markup=None
        )
        await user_collection.update_one(
            {"id": uid},
            {
                "$inc": {"rubies": reward},
                "$set": {"first_name": user.first_name}
            }
        )
    elif game["chances"] <= 0:
        del LUCKY_GAMES[uid]
        await query.message.edit_caption(
            to_tiny_caps("😢 ᴀʟʟ ᴄʜᴀɴᴄᴇꜱ ᴜꜱᴇᴅ.\nʏᴏᴜ ᴄᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ 3 💎!"),
            reply_markup=None
        )
    else:
        await query.message.edit_reply_markup(build_luckybox_keyboard(uid))
