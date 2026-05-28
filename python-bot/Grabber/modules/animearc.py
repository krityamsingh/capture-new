import asyncio
import random
import time
from pyrogram import filters, Client, types as t
from . import Grabberu as app
from Grabber import user_collection

# Configuration
win_rate_percentage = 50  # Probability of winning
cooldown_duration = 600  # Cooldown time in seconds
user_cooldowns = {}
ban_user_ids = {1234567890}

# Fixed Battle Image for All Arcs
battle_image_url = "https://files.catbox.moe/mbksxd.jpg"

# Anime Arc Data (Only Names, No Different Images)
anime_arcs = [
    "Naruto - Pain's Assault",
    "One Piece - Marineford War",
    "Attack on Titan - Final Showdown",
    "Demon Slayer - Mugen Train Battle",
    "Jujutsu Kaisen - Shibuya Incident",
    "Dragon Ball Z - Goku vs Frieza (Namek Arc)",
    "My Hero Academia - Paranormal Liberation War",
    "Bleach - Thousand-Year Blood War",
    "Tokyo Revengers - Bloody Halloween",
    "Black Clover - Spade Kingdom Raid",
    "Hunter x Hunter - Chimera Ant Arc",
    "Fairy Tail - Grand Magic Games",
    "Sword Art Online - Aincrad Final Battle",
    "Fullmetal Alchemist - Promised Day Battle",
    "Vinland Saga - Battle of London Bridge",
    "Chainsaw Man - Gun Devil Rampage",
]

rarities = ['🟡 Legendary']

# XP & Reward System
def get_rewards():
    xp = random.randint(10, 30)
    coins = random.randint(50, 200)
    return xp, coins

def human_readable_time(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{mins}m {secs}s" if mins else f"{secs}s"

def get_random_event():
    events = [
        "⚡ A sudden lightning strike changes the battlefield!",
        "🔥 The villains launch a powerful attack!",
        "🌀 A mysterious force shifts the battle!",
        "💪 Heroes receive unexpected reinforcements!",
        "🌊 A storm approaches, affecting both sides!",
        "🗡️ A legendary warrior joins the fight!",
    ]
    return random.choice(events)

@app.on_message(filters.command(["animearc"]))
async def anime_arc_battle(_, message: t.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    mention = message.from_user.mention

    # Check if user is banned
    if user_id in ban_user_ids:
        return await message.reply_text("🚫 You are banned from using this command.")

    # Check cooldown
    if user_id in user_cooldowns and time.time() - user_cooldowns[user_id] < cooldown_duration:
        remaining_time = cooldown_duration - int(time.time() - user_cooldowns[user_id])
        return await message.reply_text(f"⏳ Wait {human_readable_time(remaining_time)} before starting another battle!")

    # Select a random arc (only name changes, image remains same)
    selected_arc = random.choice(anime_arcs)
    user_cooldowns[user_id] = time.time()

    try:
        # Start battle
        start_message = (
            f"⚔️ **Anime Arc Battle Begins!** ⚔️\n\n"
            f"🌍 **Arc:** {selected_arc}\n\n"
            f"🔥 The war has started, {mention}! What will you do?"
        )
        await app.send_photo(chat_id, photo=battle_image_url, caption=start_message)

        await asyncio.sleep(3)

        # Interactive Phase
        for i in range(2):  
            event = get_random_event()
            action_msg = await message.reply_text(
                f"🌀 **Phase {i + 1}:** {event}\n\n"
                f"🔘 Choose Your Action:\n"
                f"1️⃣ Attack ⚔️\n"
                f"2️⃣ Defend 🛡️"
            )
            await asyncio.sleep(2)

            # Simulate user choice (for now, random)
            user_choice = random.choice(["Attack", "Defend"])

            if user_choice == "Attack":
                await message.reply_text(f"⚔️ {mention} launched a powerful attack!")
            else:
                await message.reply_text(f"🛡️ {mention} defended against the incoming strike!")

            await asyncio.sleep(2)

        # Determine outcome
        if random.random() < (win_rate_percentage / 100):
            # Victory
            selected_rarity = random.choice(rarities)
            xp, coins = get_rewards()
            
            victory_message = (
                f"🎉 **Victory!**\n\n"
                f"🏆 {mention}, you emerged victorious in the **{selected_arc}** battle!\n\n"
                f"💠 **XP Gained:** {xp}\n"
                f"💰 **Coins Rewarded:** {coins}\n\n"
                f"📜 **Your battle record has been updated!**"
            )
            await app.send_photo(chat_id, photo=battle_image_url, caption=victory_message)

            # Update User Stats
            await user_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"xp": xp, "coins": coins}},
                upsert=True
            )
        else:
            # Defeat
            defeat_message = (
                f"💀 **Defeat!**\n\n"
                f"Villains dominated the battle of **{selected_arc}**.\n\n"
                f"💥 **Try again later, {mention}!**"
            )
            await app.send_photo(chat_id, photo=battle_image_url, caption=defeat_message)

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("❗ An error occurred during the battle. Please try again later.")
