import asyncio
import random
import time
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Grabber import Grabberu as bot
from Grabber import user_collection, collection

# 🌌 BATTLE SYSTEM CONFIGURATION
FIGHT_COOLDOWN = 60  # 1 minute cooldown
MAX_STREAK = 15      # Maximum win streak bonus
JUTSU_COST = 20      # Chakra cost for special jutsu
CHAKRA_REGEN = 30    # Chakra regenerated per battle

# ⚡ Dynamic Variables
fight_cooldowns = {}
fight_streaks = {}
user_chakra = {}
user_stats = {}  # Tracks wins/losses per user

# 🎬 BATTLE MEDIA (All URLs utilized)
BATTLE_MEDIA = {
    "intro": {
        "naruto": "https://files.catbox.moe/bziv8y.mp4",
        "sasuke": "https://files.catbox.moe/yc4jbh.mp4"
    },
    "clash": [
        "https://files.catbox.moe/hfpx0m.mp4",
        "https://files.catbox.moe/pjv1qx.mp4"
    ],
    "victory": {
        "naruto": [
            "https://files.catbox.moe/tsgfmc.mp4",
            "https://files.catbox.moe/tsgfmc.mp4"
        ],
        "sasuke": [
            "https://files.catbox.moe/yc4jbh.mp4",
            "https://files.catbox.moe/r2eo6f.mp4"
        ]
    },
    "special": {
        "naruto": {
            "rasengan": "https://files.catbox.moe/ut1f40.mp4",
            "kurama": "https://files.catbox.moe/t5cret.mp4",
            "shadow_clone": "https://files.catbox.moe/1aadct.mp4"
        },
        "sasuke": {
            "chidori": "https://files.catbox.moe/jy4h32.mp4",
            "susanoo": "https://files.catbox.moe/c5ccw7.mp4",
            "amaterasu": "https://files.catbox.moe/9o5rh6.mp4"
        }
    },
    "defeat": "https://files.catbox.moe/jr2x9r.mp4"
}

# 💬 BATTLE DIALOGUE (Enhanced)
BATTLE_QUOTES = {
    "naruto": [
        "Believe it!",
        "I never go back on my word!",
        "I'm gonna be Hokage!",
        "Dattebayo!"
    ],
    "sasuke": [
        "I will restore my clan... and destroy a certain someone.",
        "You're annoying.",
        "This is the power of the Uchiha.",
        "I walk the path of darkness."
    ]
}

BATTLE_DIALOGUE = {
    "start": [
        "🌪️ **{user}** stands at the Valley of the End! The wind howls as destiny calls...",
        "⚡ Lightning cracks as **{user}** prepares for battle! Which legend will you fight alongside?",
        "🌀 Chakra swirls violently around **{user}**! The ultimate showdown begins!"
    ],
    "side_select": {
        "naruto": [
            "🐺 Orange flashes across the battlefield! You've chosen to fight with Naruto Uzumaki!",
            "🦊 Kurama's chakra engulfs you! Naruto stands by your side!",
            "🍥 Ramen power! You're now fighting alongside the Number One Hyperactive Knucklehead Ninja!"
        ],
        "sasuke": [
            "🦅 Dark chakra erupts! You've aligned with Sasuke Uchiha!",
            "👁️ The Sharingan gleams! Sasuke acknowledges you as an ally!",
            "⚡ Lightning crackles around you! The Last Uchiha joins your cause!"
        ]
    },
    "jutsu": {
        "naruto": {
            "rasengan": "🌀 **Rasengan** spirals violently toward the enemy!",
            "kurama": "🦊 **Kurama Mode** activated! The Nine-Tails' power is overwhelming!",
            "shadow_clone": "👥 **Multi Shadow Clone Jutsu**! The battlefield is flooded with clones!"
        },
        "sasuke": {
            "chidori": "⚡ **Chidori** screams through the air! 1000 birds cry out!",
            "susanoo": "💀 **Perfect Susano'o** manifests! The ultimate defense and offense!",
            "amaterasu": "🔥 **Amaterasu**! Black flames that never extinguish!"
        }
    },
    "victory": {
        "naruto": [
            "🌟 **Talk no Jutsu** succeeds! {user} and Naruto achieve victory through understanding!",
            "🌪️ **Tailed Beast Bomb** obliterates the opposition! {user} stands victorious!",
            "🦊 With Kurama's power, {user} and Naruto crush their enemies!"
        ],
        "sasuke": [
            "👁️ **Rinnegan** power overwhelms! {user} and Sasuke claim victory!",
            "⚡ **Chidori Sharp Spear** pierces all defenses! {user} triumphs!",
            "💀 **Susano'o Arrow** finds its mark! {user} and Sasuke emerge victorious!"
        ]
    },
    "defeat": [
        "💔 The battle is lost... but the war isn't over!",
        "☠️ Defeat tastes bitter... will you seek revenge?",
        "🌑 Darkness falls... but the Will of Fire still burns within you!"
    ],
    "streak": [
        "🔥 **{user}** is unstoppable! {streak} consecutive victories!",
        "⚡ The legend grows! {streak}-win streak for **{user}**!",
        "🌀 {streak} battles won! **{user}** is becoming a living legend!"
    ],
    "cooldown": "⏳ **Chakra replenishing...** You can battle again in {time} seconds!",
    "low_chakra": "💢 Not enough chakra! (Current: {chakra}/100)",
    "stats": """
🗡️ **Battle Stats for {user}**
🏆 Wins: {wins} | 💀 Losses: {losses}
🔥 Current Streak: {streak}
🌀 Max Streak: {max_streak}
💫 Chakra: {chakra}/100
"""
}

# 🎴 RARITY SYSTEM
def get_rarity_pool(streak):
    if streak >= 10:
        return ["👑 Divine", "💮 Mythic", "🔱 Godly"]
    elif streak >= 7:
        return ["💮 Mythic", "🟡 Legendary", "🟣 Epic"]
    elif streak >= 4:
        return ["🟡 Legendary", "🟣 Epic", "🟠 Rare"]
    return ["🟣 Epic", "🟠 Rare", "⚫ Common"]

# 🌀 JUTSU SYSTEM
async def perform_jutsu(user_id, side):
    if user_chakra.get(user_id, 0) < JUTSU_COST:
        return None
    
    user_chakra[user_id] -= JUTSU_COST
    jutsu_type = random.choice(list(BATTLE_MEDIA["special"][side].keys()))
    jutsu_quote = BATTLE_DIALOGUE["jutsu"][side][jutsu_type]
    jutsu_media = BATTLE_MEDIA["special"][side][jutsu_type]
    
    return jutsu_type, jutsu_quote, jutsu_media

# ⚔️ BATTLE COMMAND
@bot.on_message(filters.command("fight"))
async def ninja_battle(_, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    
    # ⏳ Cooldown Check
    if user_id in fight_cooldowns:
        remaining = int(FIGHT_COOLDOWN - (time.time() - fight_cooldowns[user_id]))
        if remaining > 0:
            return await message.reply_text(
                BATTLE_DIALOGUE["cooldown"].format(time=remaining),
                quote=True
            )
    
    # 🔋 Chakra Initialization
    user_chakra[user_id] = user_chakra.get(user_id, 100)
    
    # 🎞️ Epic Intro
    intro_msg = await message.reply_text(
        random.choice(BATTLE_DIALOGUE["start"]).format(user=mention)
    )
    await asyncio.sleep(2)
    
    # 🎮 Side Selection
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐺 Naruto", callback_data="battle_naruto"),
            InlineKeyboardButton("🦅 Sasuke", callback_data="battle_sasuke")
        ],
        [InlineKeyboardButton("❌ Cancel Battle", callback_data="cancel_battle")]
    ])
    
    await intro_msg.edit_text(
        "**Choose your ally for this epic clash:**\n\n"
        "🐺 Naruto - The Nine-Tails Jinchuriki with unyielding determination\n"
        "🦅 Sasuke - The Last Uchiha with the power of the Sharingan\n\n"
        f"💫 Your current chakra: {user_chakra[user_id]}/100",
        reply_markup=keyboard
    )

# ⚡ BATTLE HANDLER
@bot.on_callback_query(filters.regex("^battle_"))
async def handle_battle(_, query):
    user_id = query.from_user.id
    mention = query.from_user.mention
    side = query.data.split("_")[1]
    
    if side == "cancel":
        await query.message.delete()
        return await query.message.reply_text("🌀 Battle cancelled. Your chakra remains intact.")
    
    # 🌀 Initialize Stats
    streak = fight_streaks.get(user_id, 0)
    current_chakra = user_chakra.get(user_id, 100)
    
    # 🎞️ Side Selection Animation
    side_video = BATTLE_MEDIA["intro"][side]
    await query.message.delete()
    await bot.send_video(
        query.message.chat.id,
        side_video,
        caption=random.choice(BATTLE_DIALOGUE["side_select"][side])
    )
    await asyncio.sleep(3)
    
    # ⚔️ Battle Commence
    battle_msg = await query.message.reply_text(
        f"⚡ **{mention}** vs. **{'Sasuke' if side == 'naruto' else 'Naruto'}**\n\n"
        f"{random.choice(BATTLE_QUOTES[side])}"
    )
    await asyncio.sleep(2)
    
    # 🎞️ Battle Clash
    clash_video = random.choice(BATTLE_MEDIA["clash"])
    await bot.send_video(
        query.message.chat.id,
        clash_video,
        caption="💥 **The titans clash!** 🌪️"
    )
    await asyncio.sleep(4)
    
    # 🌀 Jutsu Attempt
    jutsu_used = None
    if current_chakra >= JUTSU_COST and random.random() < 0.5:
        jutsu_used = await perform_jutsu(user_id, side)
        if jutsu_used:
            jutsu_type, jutsu_quote, jutsu_media = jutsu_used
            await bot.send_video(
                query.message.chat.id,
                jutsu_media,
                caption=f"✨ **{mention}** used {jutsu_quote}"
            )
            await asyncio.sleep(3)
    
    # 🎲 Determine Outcome
    win_chance = 0.5 + (streak * 0.03) + (0.2 if jutsu_used else 0)
    is_winner = random.random() < win_chance
    
    # 🎞️ Victory/Defeat Sequence
    if is_winner:
        # VICTORY
        fight_streaks[user_id] = streak + 1
        user_stats[user_id] = user_stats.get(user_id, {"wins": 0, "losses": 0})
        user_stats[user_id]["wins"] += 1
        
        victory_video = random.choice(BATTLE_MEDIA["victory"][side])
        victory_msg = random.choice(BATTLE_DIALOGUE["victory"][side]).format(user=mention)
        
        # 🏆 Reward
        rarity_pool = get_rarity_pool(streak)
        character = await get_character_by_rarity(user_id, rarity_pool)
        
        if character:
            await user_collection.update_one(
                {"id": user_id},
                {
                    "$push": {"characters": character},
                    "$inc": {"battle_wins": 1, "current_streak": 1},
                    "$set": {"last_battle": time.time()},
                    "$max": {"max_streak": streak + 1}
                },
                upsert=True
            )
            
            await bot.send_video(
                query.message.chat.id,
                victory_video,
                caption=(
                    f"{victory_msg}\n\n"
                    f"🏆 **Reward:** {character['name']} ({character['rarity']})\n"
                    f"🔥 Streak: {streak + 1}"
                )
            )
            
            if streak + 1 >= 3:
                await query.message.reply_text(
                    random.choice(BATTLE_DIALOGUE["streak"]).format(
                        user=mention,
                        streak=streak + 1
                    )
                )
        else:
            await query.message.reply_text("🌀 No characters available at your level!")
    else:
        # DEFEAT
        fight_streaks[user_id] = 0
        user_stats[user_id] = user_stats.get(user_id, {"wins": 0, "losses": 0})
        user_stats[user_id]["losses"] += 1
        
        await bot.send_video(
            query.message.chat.id,
            BATTLE_MEDIA["defeat"],
            caption=(
                f"{random.choice(BATTLE_DIALOGUE['defeat'])}\n\n"
                f"💔 Your {streak}-battle streak has been broken!"
            )
        )
    
    # ⚡ Chakra Regen
    user_chakra[user_id] = min(100, user_chakra.get(user_id, 0) + CHAKRA_REGEN)
    fight_cooldowns[user_id] = time.time()

# 🃏 CHARACTER FETCHING
async def get_character_by_rarity(user_id, rarities):
    try:
        pipeline = [
            {"$match": {"rarity": {"$in": rarities}}},
            {"$sample": {"size": 1}}
        ]
        cursor = collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching character: {e}")
        return None

# 📊 STATS COMMAND
@bot.on_message(filters.command("battlestats"))
async def battle_stats(_, message: Message):
    user_id = message.from_user.id
    mention = message.from_user.mention
    stats = user_stats.get(user_id, {"wins": 0, "losses": 0})
    
    await message.reply_text(
        BATTLE_DIALOGUE["stats"].format(
            user=mention,
            wins=stats["wins"],
            losses=stats["losses"],
            streak=fight_streaks.get(user_id, 0),
            max_streak=await get_max_streak(user_id),
            chakra=user_chakra.get(user_id, 100)
        )
    )

async def get_max_streak(user_id):
    user = await user_collection.find_one({"id": user_id})
    return user.get("max_streak", 0) if user else 0

# 🏆 LEADERBOARD
@bot.on_message(filters.command("ninjalb"))
async def ninja_leaderboard(_, message: Message):
    top_players = await user_collection.find().sort("battle_wins", -1).limit(10).to_list(10)
    
    lb_text = "🏆 **Ninja Battle Legends** 🏆\n\n"
    for idx, player in enumerate(top_players, 1):
        user = await bot.get_users(player["id"])
        wins = player.get("battle_wins", 0)
        streak = player.get("current_streak", 0)
        lb_text += f"{idx}. {user.mention}\n   🗡️ {wins} wins | 🔥 {streak} streak\n"
    
    await message.reply_text(lb_text)

# 🔋 CHAKRA COMMAND
@bot.on_message(filters.command("chakra"))
async def chakra_status(_, message: Message):
    user_id = message.from_user.id
    await message.reply_text(
        f"🌀 **Chakra Status**\n"
        f"💫 Current: {user_chakra.get(user_id, 100)}/100\n"
        f"⚡ Regeneration: {CHAKRA_REGEN} per battle\n"
        f"🌀 Jutsu Cost: {JUTSU_COST} chakra\n\n"
        "Use /battle to test your ninja skills!"
    )
