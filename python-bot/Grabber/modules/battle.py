import asyncio
import random
import time
from pyrogram import filters, Client, types as t
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Grabber import Grabberu as bot
from . import ac, app, user_collection, collection, capsify
from datetime import datetime, timedelta

# Constants
WIN_REWARD_CHARACTER_COUNT = 1
COOLDOWN_DURATION = 300
BATTLE_DURATION = 60
MAX_BATTLE_LEVEL = 100
CRITICAL_HIT_CHANCE = 0.15
SPECIAL_MOVE_CHANCE = 0.25

# Cooldown and stats trackers
user_cooldowns = {}
user_stats = {}
active_battles = {}

# Premium anime characters with enhanced stats
CHARACTERS = {
    "Saitama": {
        "move": "Serious Punch",
        "desc": "A punch with unimaginable power that defies all logic",
        "video_url": "https://files.catbox.moe/rw2yuz.mp4",
        "power": 9999,
        "defense": 500,
        "speed": 800,
        "special": "One Punch (30% instant win chance)",
        "element": "physical"
    },
    "Goku": {
        "move": "Ultra Instinct Kamehameha",
        "desc": "Perfect defense and offense combined into one technique",
        "video_url": "https://files.catbox.moe/90bga6.mp4",
        "power": 9500,
        "defense": 900,
        "speed": 950,
        "special": "UI Dodge (evades next 2 attacks)",
        "element": "energy"
    },
    "Naruto": {
        "move": "Baryon Mode Rasengan",
        "desc": "Life energy converted into devastating spinning force",
        "video_url": "https://files.catbox.moe/d2iygy.mp4",
        "power": 9200,
        "defense": 850,
        "speed": 920,
        "special": "Kurama Heal (restores 30% HP)",
        "element": "chakra"
    },
    "Luffy": {
        "move": "Gear 5: Dawn Gatling",
        "desc": "Reality bending attacks that turn environment into rubber",
        "video_url": "https://files.catbox.moe/wmc671.gif",
        "power": 9100,
        "defense": 800,
        "speed": 990,
        "special": "Toon Force (50% damage negation)",
        "element": "physical"
    },
    "Ichigo": {
        "move": "Final Getsuga Tenshou",
        "desc": "Becoming the attack itself through ultimate sacrifice",
        "video_url": "https://files.catbox.moe/ky17sr.mp4",
        "power": 9400,
        "defense": 750,
        "speed": 980,
        "special": "Bankai Boost (+25% damage for 3 turns)",
        "element": "spiritual"
    }
}

BATTLE_STAGES = [
    {"name": "Mountain Summit", "effect": "Thin air reduces defense by 10%", "element": "wind"},
    {"name": "Volcanic Core", "effect": "Magma flows boost fire attacks by 20%", "element": "fire"},
    {"name": "Abyssal Trench", "effect": "Water pressure slows all movements by 15%", "element": "water"},
    {"name": "Celestial Arena", "effect": "Zero gravity increases speed but reduces accuracy", "element": "cosmic"},
]

BATTLE_QUOTES = [
    "The clash of destinies begins now!",
    "Our spirits shall determine the victor!",
    "Witness the pinnacle of combat!",
    "This moment will echo through eternity!",
    "Let our battle be legendary!",
]

async def get_random_characters():
    try:
        pipeline = [{"$match": {"rarity": {"$in": ["🟡 Legendary"]}}}, {"$sample": {"size": WIN_REWARD_CHARACTER_COUNT}}]
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        return characters
    except Exception as e:
        print(f"Database error: {e}")
        return []

async def update_user_stats(user_id, won=False):
    if user_id not in user_stats:
        user_stats[user_id] = {"wins": 0, "losses": 0, "streak": 0, "highest_streak": 0}
    
    if won:
        user_stats[user_id]["wins"] += 1
        user_stats[user_id]["streak"] += 1
        if user_stats[user_id]["streak"] > user_stats[user_id]["highest_streak"]:
            user_stats[user_id]["highest_streak"] = user_stats[user_id]["streak"]
    else:
        user_stats[user_id]["losses"] += 1
        user_stats[user_id]["streak"] = 0

async def calculate_damage(attacker, defender, move, is_critical=False, stage_element=None):
    base_damage = attacker["power"] * (random.uniform(0.8, 1.2))
    defense = defender["defense"] * (random.uniform(0.7, 1.0))
    
    # Elemental advantage system
    element_advantage = 1.0
    if stage_element and attacker.get("element") == stage_element:
        element_advantage = 1.2
    
    if is_critical:
        base_damage *= 1.5
    
    damage = max(10, (base_damage * element_advantage) - (defense * 0.5))
    return int(damage)

async def send_battle_animation(chat_id, user, character, move, damage=None, is_critical=False):
    caption = f"**{user.first_name} unleashes {character['move']}**\n"
    caption += f"_{character['desc']}_\n"
    
    if damage is not None:
        crit_text = "**Critical Strike!** " if is_critical else ""
        caption += f"{crit_text}**Impact:** `{damage}`"
    
    await bot.send_video(
        chat_id=chat_id,
        video=character["video_url"],
        caption=caption,
    )
    await asyncio.sleep(2)

@bot.on_callback_query(filters.regex(r"battle_confirm\|(\d+)\|(\d+)"))
async def battle_confirmation(client: Client, callback_query: t.CallbackQuery):
    challenger_id, opponent_id = map(int, callback_query.data.split("|")[1:])
    user = callback_query.from_user
    chat_id = callback_query.message.chat.id

    if user.id != opponent_id:
        await callback_query.answer("This challenge is not for you", show_alert=True)
        return

    if challenger_id in active_battles or opponent_id in active_battles:
        await callback_query.answer("Combatants are already engaged in battle", show_alert=True)
        return

    battle_id = f"{challenger_id}_{opponent_id}_{int(time.time())}"
    active_battles[challenger_id] = battle_id
    active_battles[opponent_id] = battle_id

    await callback_query.message.edit_reply_markup(reply_markup=None)

    challenger = await bot.get_users(challenger_id)
    opponent = await bot.get_users(opponent_id)
    battle_stage = random.choice(BATTLE_STAGES)
    
    intro_msg = await bot.send_message(
        chat_id,
        f"**Dimensional Rift Opening**\n\n"
        f"**{challenger.first_name}** versus **{opponent.first_name}**\n"
        f"**Battlefield:** {battle_stage['name']}\n"
        f"**Environment:** {battle_stage['effect']}\n\n"
        f"_{random.choice(BATTLE_QUOTES)}_"
    )
    
    await asyncio.sleep(3)

    challenger_char_name, challenger_char = random.choice(list(CHARACTERS.items()))
    opponent_char_name, opponent_char = random.choice(list(CHARACTERS.items()))
    
    challenger_hp = 1000
    opponent_hp = 1000
    turn = 1
    
    while challenger_hp > 0 and opponent_hp > 0 and turn <= 10:
        turn_msg = await bot.send_message(
            chat_id,
            f"**Turn {turn}**\n"
            f"{challenger.first_name}: `{max(0, challenger_hp)}` HP\n"
            f"{opponent.first_name}: `{max(0, opponent_hp)}` HP"
        )
        
        # Challenger's turn
        is_critical = random.random() < CRITICAL_HIT_CHANCE
        damage = await calculate_damage(
            challenger_char, 
            opponent_char, 
            challenger_char["move"],
            is_critical,
            battle_stage["element"]
        )
        
        await send_battle_animation(
            chat_id, challenger, challenger_char, 
            challenger_char["move"], damage, is_critical
        )
        
        opponent_hp -= damage
        await asyncio.sleep(2)
        
        if opponent_hp <= 0:
            break
            
        # Opponent's turn
        is_critical = random.random() < CRITICAL_HIT_CHANCE
        damage = await calculate_damage(
            opponent_char, 
            challenger_char, 
            opponent_char["move"],
            is_critical,
            battle_stage["element"]
        )
        
        await send_battle_animation(
            chat_id, opponent, opponent_char, 
            opponent_char["move"], damage, is_critical
        )
        
        challenger_hp -= damage
        await asyncio.sleep(2)
        
        turn += 1
    
    if challenger_hp > opponent_hp:
        winner = challenger
        loser = opponent
        winner_char = challenger_char_name
    else:
        winner = opponent
        loser = challenger
        winner_char = opponent_char_name
    
    result_msg = f"**Battle Concluded**\n\n"
    result_msg += f"**Victor:** {winner.first_name}\n"
    result_msg += f"**Champion Character:** {winner_char}\n"
    result_msg += f"**Defeated:** {loser.first_name}\n\n"
    result_msg += f"**Final Status:**\n"
    result_msg += f"{challenger.first_name}: `{max(0, challenger_hp)}` HP\n"
    result_msg += f"{opponent.first_name}: `{max(0, opponent_hp)}` HP\n\n"
    result_msg += f"**Combat Duration:** {turn} turns"
    
    await bot.send_message(chat_id, result_msg)
    
    if winner.id == callback_query.from_user.id or winner.id == challenger_id:
        random_characters = await get_random_characters()
        if random_characters:
            for character in random_characters:
                await user_collection.update_one(
                    {"id": winner.id}, {"$push": {"characters": character}}
                )

            reward_message = (
                f"**{winner.first_name} claims victory rewards**\n\n"
            )
            for character in random_characters:
                reward_message += (
                    f"**Character:** {character['name']}\n"
                    f"**Rarity:** {character['rarity']}\n"
                    f"**Origin:** {character['anime']}\n\n"
                )
            await bot.send_photo(
                chat_id=chat_id,
                photo=random_characters[0]["img_url"],
                caption=reward_message,
            )
        
        await update_user_stats(winner.id, won=True)
        await update_user_stats(loser.id, won=False)
        
        stats_msg = f"**Combat Records Updated**\n"
        stats_msg += f"{winner.first_name}: {user_stats[winner.id]['wins']} victories (Current streak: {user_stats[winner.id]['streak']})\n"
        stats_msg += f"{loser.first_name}: {user_stats[loser.id]['losses']} defeats"
        await bot.send_message(chat_id, stats_msg)
    
    del active_battles[challenger_id]
    del active_battles[opponent_id]

@bot.on_message(filters.command(["battle"]))
async def battle(_, message: t.Message):
    if not message.reply_to_message:
        await message.reply_text("**Please reply to a user to initiate combat**")
        return

    challenger = message.from_user
    opponent = message.reply_to_message.from_user

    if opponent.is_bot:
        await message.reply_text("**Bots cannot participate in battles**")
        return
    if challenger.id == opponent.id:
        await message.reply_text("**Self-combat is not permitted**")
        return

    current_time = time.time()
    if challenger.id in user_cooldowns and current_time - user_cooldowns[challenger.id] < COOLDOWN_DURATION:
        remaining_time = int(COOLDOWN_DURATION - (current_time - user_cooldowns[challenger.id]))
        await message.reply_text(f"**Energy recovering: {remaining_time}s until next challenge**")
        return

    if opponent.id in active_battles:
        await message.reply_text(f"**{opponent.first_name} is currently engaged in combat**")
        return

    user_cooldowns[challenger.id] = current_time

    confirm_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Accept Duel", callback_data=f"battle_confirm|{challenger.id}|{opponent.id}"),
                InlineKeyboardButton("Decline", callback_data="battle_reject"),
            ]
        ]
    )
    
    char1 = random.choice(list(CHARACTERS.items()))
    char2 = random.choice(list(CHARACTERS.items()))
    
    preview_text = (
        f"**Combat Challenge Initiated**\n\n"
        f"**{challenger.first_name}** challenges **{opponent.first_name}**\n\n"
        f"**Potential Combatants:**\n"
        f"• {char1[0]} (Power: {char1[1]['power']} | Defense: {char1[1]['defense']})\n"
        f"• {char2[0]} (Power: {char2[1]['power']} | Defense: {char2[1]['defense']})\n\n"
        f"**Challenge expires in {BATTLE_DURATION//60} minutes**\n"
        f"{opponent.first_name}, your response is required"
    )
    
    challenge_msg = await message.reply_text(
        preview_text,
        reply_markup=confirm_markup,
    )
    
    await asyncio.sleep(BATTLE_DURATION)
    try:
        if opponent.id in active_battles and active_battles[opponent.id].startswith(f"{challenger.id}_{opponent.id}"):
            return
            
        await challenge_msg.edit_text(
            f"**Challenge Expired**\n"
            f"{opponent.first_name} did not respond to the challenge",
            reply_markup=None
        )
    except:
        pass

@bot.on_callback_query(filters.regex(r"battle_reject"))
async def reject_battle(client: Client, callback_query: t.CallbackQuery):
    await callback_query.message.edit_text(
        "**Challenge declined**\nThe battle will not commence",
        reply_markup=None
    )
    await callback_query.answer()
