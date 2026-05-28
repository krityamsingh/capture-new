import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Grabber import collection, user_collection
from . import app

# Cooldown system and state tracking
cooldowns = {}
attempts = {}
active_proposals = {}

# Time settings
PROPOSAL_COOLDOWN = timedelta(minutes=5)
EXCLUDED_RARITIES = ['🏵️ Exotic', '🌼 Celebrity', '🎐 Crystal', '🍹 Neon', '🧿 Supreme', '🛸 Galvoria', '⚡ Thundra', '⚜️ Animated', '🟡 Solar Verse', '🫧 Aether Verse', '🔮 Arcane Verse']

# Stylized responses
LOVE_SUCCESS = [
    "✨ **The stars aligned as {name} blushed deeply...** *\"I've been waiting for you\"* ❤️",
    "💫 **{name}'s eyes sparkled as they took your hand...** *\"I accept your heart\"* 💞",
    "🌸 **Petals swirled around you both as {name} whispered...** *\"Yes, forever\"* 💍",
    "🌠 **A shooting star crossed the sky as {name} kissed your cheek...** *\"My answer is yes\"* 💘",
    "💖 **The world seemed to pause when {name} embraced you...** *\"I'm yours\"* 💕"
]

LOVE_REJECTION = [
    "🍂 **{name} sighed and looked away...** *\"My heart belongs to another\"* 💔",
    "🌧️ **Rain began to fall as {name} shook their head...** *\"Not this time\"* ☔",
    "🌑 **The light faded from {name}'s eyes...** *\"I cannot accept\"* 🖤",
    "🌀 **{name} vanished like the wind... leaving only silence** 🌪️",
    "❄️ **\"You deserve someone better\"** {name} said before disappearing into the snow... 🌨️"
]

async def get_eligible_character():
    """Get a random character with ID ≤ 2000, valid image, and not in excluded rarities"""
    pipeline = [
        {
            "$match": {
                "rarity": {"$nin": EXCLUDED_RARITIES},
                "id": {"$lte": "2000"},
                "img_url": {"$exists": True, "$ne": ""}
            }
        },
        {"$sample": {"size": 1}}
    ]
    result = await collection.aggregate(pipeline).to_list(1)
    return result[0] if result else None

@app.on_message(filters.command("propose"))
async def propose_cmd(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    now = datetime.now()

    if user_id in active_proposals:
        return await message.reply_text("🌹 **Your heart is already racing from another encounter... finish that first!**")

    # Cooldown check
    if user_id in cooldowns and (now - cooldowns[user_id]) < PROPOSAL_COOLDOWN:
        remaining = PROPOSAL_COOLDOWN - (now - cooldowns[user_id])
        return await message.reply_text(
            f"⏳ **Your heart needs rest...** Come back in `{remaining.seconds // 60}m {remaining.seconds % 60}s`"
        )

    # Get eligible character
    char = await get_eligible_character()
    if not char:
        return await message.reply_text("🌌 **No worthy candidates appear...** Try again later when the stars align!")

    # Validate and sanitize fields
    name = char.get("name", "Mysterious Stranger")
    anime = char.get("anime", "Unknown Origin")
    rarity = char.get("rarity", "?")
    img_url = char["img_url"]

    active_proposals[user_id] = char

    attempts.setdefault(user_id, {"date": now.date(), "count": 0})
    if attempts[user_id]["date"] != now.date():
        attempts[user_id] = {"date": now.date(), "count": 0}

    caption = (
        f"🌠 **A Fateful Encounter...**\n\n"
        f"💖 **{name}** stands before you\n"
        f"**Will you confess your deepest feelings?**"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💌 Pour Your Heart Out", callback_data=f"accept_{user_id}")],
        [InlineKeyboardButton("🌌 Walk Away", callback_data=f"reject_{user_id}")]
    ])

    await message.reply_photo(
        photo=img_url,
        caption=caption,
        reply_markup=buttons
    )

@app.on_callback_query(filters.regex(r"^(accept|reject)_\d+"))
async def handle_response(client: Client, query):
    action, uid = query.data.split("_")
    uid = int(uid)

    if query.from_user.id != uid:
        return await query.answer("🔞 This romantic moment isn't yours to interfere with!", show_alert=True)

    char = active_proposals.pop(uid, None)
    if not char:
        return await query.message.edit_caption("⏳ The moment has passed like a fleeting dream...")

    # Additional ID check
    if int(char.get("id", 0)) > 2000:
        return await query.message.edit_caption("⚠️ The universe rejects this unnatural pairing!")

    cooldowns[uid] = datetime.now()

    if action == "reject":
        await query.message.delete()
        return await query.message.reply_text("🌫️ You turned away, leaving your confession unsaid...")

    attempts[uid]["count"] += 1
    guaranteed = attempts[uid]["count"] >= 3
    outcome = "success" if guaranteed else random.choices(["success", "fail"], weights=[65, 35])[0]

    name = char.get("name", "The Mysterious One")

    if outcome == "success":
        await user_collection.update_one({'id': uid}, {'$push': {'characters': char}}, upsert=True)
        attempts[uid]["count"] = 0
        response = random.choice(LOVE_SUCCESS).format(name=name)
        response += f"\n\n💞 **{name} has been added to your harem!**"
    else:
        response = random.choice(LOVE_REJECTION).format(name=name)
        response += "\n\n💫 *The third time's the charm... Keep trying!*"

    await query.message.edit_caption(response, reply_markup=None)

@app.on_message(filters.command("epropose"))
async def cancel_propose(client: Client, message: Message):
    if active_proposals.pop(message.from_user.id, None):
        await message.reply_text("🌪️ Your confession was carried away by the wind...")
    else:
        await message.reply_text("🌌 You have no pending romantic encounters to cancel.")
