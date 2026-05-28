from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from asyncio import sleep
import random
import time
from datetime import datetime, timedelta
from . import app, collection, user_collection, ac

# Config
SUPPORT_GROUP_ID = "Divine_Catchers"
SUPPORT_CHANNEL_USERNAME = "IndianHelpIine"
ANIME_GROUP_USERNAME = "horny_folks"
CLAIM_COOLDOWN_HOURS = 24

# FIX: OWNER_IDS must be LIST, not set
OWNER_IDS = [7878477646, 8496760733, 6228788487, 6118760915]

# Rarity weights
RARITY_DISTRIBUTION = {
    '🟠 Rare': {'emoji': '🟠', 'weight': 15},
    '🟣 Epic': {'emoji': '🟣', 'weight': 10},
    '🟡 Legendary': {'emoji': '🟡', 'weight': 7},
    '🫧 Premium': {'emoji': '🫧', 'weight': 1},
    '🔮 Limited Edition': {'emoji': '🔮', 'weight': 1}
}

claim_system_enabled = True


def get_weighted_random_rarity():
    rarities = list(RARITY_DISTRIBUTION.keys())
    weights = [RARITY_DISTRIBUTION[r]['weight'] for r in rarities]
    return random.choices(rarities, weights=weights, k=1)[0]


async def check_membership(user_id):
    try:
        # Support group
        member = await app.get_chat_member(SUPPORT_GROUP_ID, user_id)
        if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
            return False

        # Channel
        try:
            member = await app.get_chat_member(SUPPORT_CHANNEL_USERNAME, user_id)
            if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                return False
        except:
            return False

        # Anime group
        try:
            member = await app.get_chat_member(ANIME_GROUP_USERNAME, user_id)
            if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                return False
        except:
            return False

        return True
    
    except Exception as e:
        print(f"Membership error: {e}")
        return False



# ------------------- CLAIM COMMAND -------------------
@app.on_message(filters.command("claim"))
async def claim_character(client: Client, message: Message):
    global claim_system_enabled

    user_id = message.from_user.id
    user_tag = message.from_user.mention

    # System disabled?
    if not claim_system_enabled and user_id not in OWNER_IDS:
        return await message.reply_text("⚠️ Claim system is disabled by admin!")

    # Membership check
    is_member = await check_membership(user_id)
    if not is_member and user_id not in OWNER_IDS:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Support Group", url=f"https://t.me/{SUPPORT_GROUP_ID}"),
             InlineKeyboardButton("News Channel", url=f"https://t.me/{SUPPORT_CHANNEL_USERNAME}")],
            [InlineKeyboardButton("Anime Group", url=f"https://t.me/{ANIME_GROUP_USERNAME}")]
        ])
        return await message.reply_text(
            "⚠️ You must join all groups/channels to claim!",
            reply_markup=buttons
        )

    # Cooldown check
    if user_id not in OWNER_IDS:
        user_data = await user_collection.find_one({"user_id": user_id})
        if user_data and "last_claim_time" in user_data:
            last_claim = user_data["last_claim_time"]
            cooldown_end = last_claim + timedelta(hours=CLAIM_COOLDOWN_HOURS)

            if datetime.now() < cooldown_end:
                time_left = cooldown_end - datetime.now()
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                return await message.reply_text(
                    f"⏳ You can claim again in {hours}h {minutes}m.\n"
                    f"(Cooldown {CLAIM_COOLDOWN_HOURS} hours)"
                )

    # Reveal animation
    reveal = await message.reply("🎁 Preparing your character...")
    for seq in ["🌦️", "🌩️", "🌧️"]:
        await sleep(1.4)
        await reveal.edit_text(seq)

    try:
        # Random rarity
        selected_rarity = get_weighted_random_rarity()

        pipeline = [
            {"$match": {"rarity": selected_rarity}},
            {"$sample": {"size": 1}}
        ]
        chars = await collection.aggregate(pipeline).to_list(1)
        if not chars:
            return await reveal.edit_text("⚠️ No characters left for this rarity!")

        char = chars[0]

        # Add character
        await ac(user_id, char["id"])

        # Update cooldown
        if user_id not in OWNER_IDS:
            await user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_claim_time": datetime.now()}},
                upsert=True
            )

        # Prepare caption
        caption = (
            f"🌸 **Character Claimed!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ **Name:** `{char['name']}`\n"
            f"⛩️ **Anime:** `{char['anime']}`\n"
            f"☁️ **Rarity:** `{char['rarity']}`\n"
            f"🕊️ **Claimed By:** {user_tag}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ **Next Claim:** `{CLAIM_COOLDOWN_HOURS} hours`"
        )

        # Send media
        media = (
            InputMediaVideo(char["video_url"], caption=caption)
            if char.get("video_url")
            else InputMediaPhoto(char["img_url"], caption=caption)
        )

        await message.reply_media_group([media])
        await reveal.delete()

    except Exception as e:
        print(f"Claim Error: {e}")
        await reveal.edit_text("⚠️ Error occurred. Try again.")


# ------------------- OWNER COMMANDS -------------------
@app.on_message(filters.command("startclaim") & filters.user(OWNER_IDS))
async def start_claim_system(_, message: Message):
    global claim_system_enabled
    claim_system_enabled = True
    await message.reply_text("✅ Claim system ENABLED!")


@app.on_message(filters.command("stopclaim") & filters.user(OWNER_IDS))
async def stop_claim_system(_, message: Message):
    global claim_system_enabled
    claim_system_enabled = False
    await message.reply_text("⛔ Claim system DISABLED!")


@app.on_message(filters.command("resetclaims") & filters.user(OWNER_IDS))
async def reset_all_cooldowns(_, message: Message):
    await user_collection.update_many({}, {"$unset": {"last_claim_time": ""}})
    await message.reply_text("♻️ All cooldowns RESET!")
