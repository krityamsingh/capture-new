import random
import time
from pyrogram import filters
from pyrogram.types import Message
from Grabber import Grabberu as bot
from Grabber import user_collection, collection

# Cooldown & Streak System
cooldowns = {}
marry_streaks = {}

# Anime-style streak rewards
anime_streak_rewards = {
    5: "**Streak Bonus!** You're getting popular in the anime world!",
    10: "**10 Marriages!** You're turning into a romance anime legend!",
    20: "**20 Streak!** Everyone wants to be with you now!"
}

# Success messages
anime_success_messages = [
    "**{mention}** just proposed to **{name}** from *{anime}* — and they said yes under the starry sky!",
    "**{mention}** and **{name}** from *{anime}* are now officially together! True love blooms again!",
    "**{mention}** got a yes from **{name}** from *{anime}*! What a beautiful couple!",
    "**{mention}** and **{name}** from *{anime}* walked into the sunset holding hands. Love wins!"
]

# Failure messages
anime_failure_messages = [
    "**{mention}**, sadly **{name}** from *{anime}* turned you down... Maybe next time!",
    "**{mention}**, your feelings weren't returned. **{name}** from *{anime}* just smiled and walked away.",
    "**{mention}**, it seems **{name}** from *{anime}* sees you more as a friend than a partner."
]

# Cooldown message
def cooldown_msg(seconds):
    return f"⏳ Please wait **{seconds}s** before proposing again!"

# Streak bonus message
def streak_bonus(mention, streak):
    bonus = anime_streak_rewards.get(streak, "You're building something special. Keep going!")
    return f"🔥 **{mention}**, your streak is at **{streak}**! {bonus}"

# Character fetcher
async def get_random_character(user_id, rarities=["⚫ Common", "🟤 Uncommon", "🟠 Rare", "🟡 Legendary"], failure=False):
    try:
        user_chars = await user_collection.find_one({"id": user_id})
        owned_ids = [char["id"] for char in user_chars.get("characters", [])] if user_chars else []

        match_stage = {
            "rarity": {"$in": rarities},
            "id": {"$lte": "2000"}
        }

        if not failure:
            match_stage["id"]["$nin"] = owned_ids

        pipeline = [
            {"$match": match_stage},
            {"$sample": {"size": 1}}
        ]

        result = await collection.aggregate(pipeline).to_list(1)
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching character: {e}")
        return None

# Auto-delete function
async def delete_after_delay(message: Message, delay: int = 600):
    """Delete message after specified delay in seconds"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"Error deleting message: {e}")

# Marry Command
@bot.on_message(filters.command("marry"))
async def marry(_, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention

    # Cooldown check
    now = time.time()
    remaining = 60 - (now - cooldowns.get(user_id, 0))
    if remaining > 0:
        cooldown_message = await message.reply_text(cooldown_msg(int(remaining)), quote=True)
        # Delete both command and cooldown message after 10 minutes
        asyncio.create_task(delete_after_delay(message))
        asyncio.create_task(delete_after_delay(cooldown_message))
        return

    cooldowns[user_id] = now

    # Simulate roll
    roll = random.randint(1, 6)

    if roll in [1, 3, 6]:  # Success
        character = await get_random_character(user_id)
        if character:
            if int(character.get("id", 0)) > 2000:
                marry_streaks[user_id] = 0
                error_msg = await message.reply_text(
                    "⚠️ Invalid character found. Please try again.",
                    quote=True
                )
                # Delete both command and error message after 10 minutes
                asyncio.create_task(delete_after_delay(message))
                asyncio.create_task(delete_after_delay(error_msg))
                return

            img_url = character["img_url"]
            name = character["name"]
            anime = character["anime"]

            await user_collection.update_one(
                {"id": user_id},
                {
                    "$push": {"characters": character},
                    "$inc": {"marriage_count": 1}
                },
                upsert=True
            )

            marry_streaks[user_id] = marry_streaks.get(user_id, 0) + 1
            caption = random.choice(anime_success_messages).format(mention=mention, name=name, anime=anime)
            
            # Send photo and schedule deletion
            photo_msg = await message.reply_photo(img_url, caption=caption, quote=True)
            asyncio.create_task(delete_after_delay(photo_msg))
            
            # Delete original command message
            asyncio.create_task(delete_after_delay(message))

            # Check streak and schedule deletion
            if marry_streaks[user_id] in anime_streak_rewards:
                streak_msg = await message.reply_text(streak_bonus(mention, marry_streaks[user_id]), quote=True)
                asyncio.create_task(delete_after_delay(streak_msg))
        else:
            no_char_msg = await message.reply_text(
                "🌌 No eligible characters left to marry. You've married them all!",
                quote=True
            )
            # Delete both command and no character message after 10 minutes
            asyncio.create_task(delete_after_delay(message))
            asyncio.create_task(delete_after_delay(no_char_msg))
    else:  # Failure
        marry_streaks[user_id] = 0
        character = await get_random_character(user_id, failure=True)

        if character and int(character.get("id", 0)) <= 2000:
            fail_msg = random.choice(anime_failure_messages).format(mention=mention, name=character["name"], anime=character["anime"])
        else:
            fail_msg = f"😢 **{mention}**, no characters found for a rejection scene. Fate took a day off."

        # Send failure message and schedule deletion
        failure_msg = await message.reply_text(fail_msg, quote=True)
        asyncio.create_task(delete_after_delay(failure_msg))
        # Delete original command message
        asyncio.create_task(delete_after_delay(message))

# Import asyncio at the top
import asyncio
