import random
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    Animation
)
from . import Grabberu as app, user_collection

# ANIMATION LINKS (One Piece themed GIFs)
ANIMATIONS = {
    "success": [
        "https://files.catbox.moe/rfuamr.mp4",  # Luffy punching
        "https://files.catbox.moe/uj9hcc.mp4",  # Zoro slashing
        "https://files.catbox.moe/hgjnqk.mp4"   # Sanji kicking
    ],
    "fail": [
        "https://files.catbox.moe/afsrin.mp4",  # Buggy failing
        "https://files.catbox.moe/rouz3g.mp4"   # Chopper scared
    ],
    "critical": [
        "https://files.catbox.moe/hg2fqy.mp4",  # Shanks conqueror's
        "https://files.catbox.moe/ntlyc5.mp4",  # Luffy gear 5
        "https://files.catbox.moe/5qztlb.mp4"   # Whitebeard quake
    ],
    "jail": [
        "https://files.catbox.moe/kxmtca.mp4"   # Sea stone cuffs
    ]
}

# Cooldown and jail storage
rob_cooldowns = {}
jailed_users = {}

# Devil Fruits with special abilities
DEVIL_FRUITS = {
    "gomu": {
        "name": "Gomu Gomu no Mi",
        "price": 150000,
        "effect": "Increases robbery success by 15% and escape chance by 20%",
        "emoji": "🟠"
    },
    "ope": {
        "name": "Ope Ope no Mi",
        "price": 250000,
        "effect": "Allows stealing 40% more berries but 10% jail risk",
        "emoji": "🌀"
    },
    "mera": {
        "name": "Mera Mera no Mi",
        "price": 200000,
        "effect": "Burns 10% of victim's berries if failed robbery",
        "emoji": "🔥"
    },
    "yami": {
        "name": "Yami Yami no Mi",
        "price": 300000,
        "effect": "Nullifies 30% of victim's Haki power",
        "emoji": "⚫"
    }
}

# Haki types with their power levels and prices
HAKI_TYPES = {
    "observation": {
        "name": "Kenbunshoku Haki",
        "emoji": "👁️",
        "levels": {
            1: {"power": 15, "price": 10000, "desc": "Basic danger sense"},
            2: {"power": 35, "price": 30000, "desc": "Short-term future sight"},
            3: {"power": 70, "price": 80000, "desc": "Advanced future sight"},
            4: {"power": 100, "price": 150000, "desc": "Supreme future sight"}
        }
    },
    "armament": {
        "name": "Busoshoku Haki",
        "emoji": "⚔️",
        "levels": {
            1: {"power": 20, "price": 15000, "desc": "Basic hardening"},
            2: {"power": 45, "price": 40000, "desc": "Advanced hardening"},
            3: {"power": 80, "price": 90000, "desc": "Ryou emission"},
            4: {"power": 120, "price": 180000, "desc": "Internal destruction"}
        }
    },
    "conqueror": {
        "name": "Haoshoku Haki",
        "emoji": "👑",
        "levels": {
            1: {"power": 60, "price": 60000, "desc": "Basic conqueror's"},
            2: {"power": 100, "price": 120000, "desc": "Advanced conqueror's"},
            3: {"power": 150, "price": 250000, "desc": "Supreme conqueror's"},
            4: {"power": 200, "price": 500000, "desc": "Conqueror's infusion"}
        }
    }
}

# One Piece crew ranks
CREW_RANKS = {
    0: {"name": "Deck Swabber", "req": 0},
    1: {"name": "Apprentice", "req": 5000},
    2: {"name": "Cabin Boy/Girl", "req": 20000},
    3: {"name": "Lookout", "req": 50000},
    4: {"name": "Navigator", "req": 100000},
    5: {"name": "Shipwright", "req": 200000},
    6: {"name": "Cook", "req": 350000},
    7: {"name": "Sniper", "req": 500000},
    8: {"name": "Doctor", "req": 750000},
    9: {"name": "Musician", "req": 1000000},
    10: {"name": "Archaeologist", "req": 1500000},
    11: {"name": "Helmsman", "req": 2000000},
    12: {"name": "Combatant", "req": 3000000},
    13: {"name": "First Mate", "req": 5000000},
    14: {"name": "Captain", "req": 10000000},
    15: {"name": "Yonko", "req": 25000000},
    16: {"name": "Pirate King", "req": 50000000}
}

# Enhanced One Piece themed messages
ROB_MESSAGES = {
    "intro": (
        "**🏴‍☠️ Welcome to the Grand Line Robbery System!**\n\n"
        "`Steal berries from other pirates in epic Haki battles!`\n"
        "`Risk getting sent to Impel Down if you fail!`\n\n"
        "**How to play:**\n"
        "1. Buy Haki powers from `/hakishop`\n"
        "2. Consider getting a Devil Fruit from `/devilshop`\n"
        "3. Rob others by replying to their message with `/rob`\n"
        "4. Earn berries to increase your crew rank!\n\n"
        "**Current Crew Rank:** {rank}\n"
        "**Next Rank:** {next_rank} (Need {req} more berries)"
    ),
    "success": [
        "**⚡ Haki Clash Victory!** {robber}'s {haki} overwhelmed {victim}'s defenses and stole {amount} Berries!",
        "**🌪️ Torn Defenses!** {robber} used {haki} to create an opening and plundered {amount} Berries from {victim}!",
        "**🔥 Burning Ambition!** The heat of {robber}'s {haki} was too much! {amount} Berries stolen!",
        "**👑 Conqueror's Will!** {victim} couldn't withstand {robber}'s {haki}! Lost {amount} Berries!",
        "**🌀 Future Sight Perfection!** {robber} predicted {victim}'s moves and took {amount} Berries!"
    ],
    "fail": [
        "**🛡️ Iron Defense!** {victim}'s {haki} completely nullified {robber}'s attack!",
        "**💨 Swift Counter!** {victim} dodged with Observation Haki and protected their Berries!",
        "**⚓ Anchor Defense!** {robber}'s {haki} wasn't strong enough to move {victim}!",
        "**🌊 Tide Turned!** {victim}'s Armament Haki repelled the robbery attempt!",
        "**🐉 Dragon's Scales!** {robber}'s attack bounced off {victim}'s powerful Haki!"
    ],
    "critical": {
        "success": [
            "**💥 SUPERNOVA IMPACT!** {robber}'s supreme {haki} created a massive shockwave stealing {amount} Berries!",
            "**🌋 ERUPTION OF POWER!** {robber} unleashed their full {haki} potential! {amount} Berries plundered!",
            "**⚡ THUNDER BAGUA!** {robber} channeled Kaido's technique through {haki}! {amount} Berries gone!"
        ],
        "fail": [
            "**⛓️ IMPEL DOWN!** {robber} was caught by Magellan and jailed for {time} minutes!",
            "**👮 MARINE ADMIRAL INTERVENTION!** {robber} was stopped by Akainu! Jailed for {time} minutes!",
            "**🌊 SEA STONE SMACKDOWN!** {robber}'s powers were nullified by Vice Admiral! {time} minute sentence!"
        ]
    },
    "jail": [
        "**🔒 IMPRISONED!** {robber} is in Impel Down Level {level} for {time} minutes!",
        "**🏰 LOCKED AWAY!** {robber} got sent to {level} for {time} minutes!",
        "**🚨 CAPTURED!** {robber} must wait {time} minutes before next robbery!"
    ],
    "errors": {
        "self_rob": "**🤦‍♂️ You can't rob yourself!** Even Buggy wouldn't be this clownish!",
        "no_haki": "**🛑 No Haki Detected!** You need at least one type of Haki from `/hakishop` to rob others!",
        "victim_poor": "**🏝️ Not Worth It!** {victim} has less than 1,000 Berries to steal!",
        "cooldown": "**⏳ Haki Recharging!** You must wait {time} before attempting another robbery!",
        "bot_protected": "**🤖 Marine Protection!** You can't rob Marine bots - they're protected by Vegapunk's technology!",
        "jailed": "**⛓️ IMPRISONED!** You're in Impel Down for {time} more minutes!\nYour Haki is sealed by Sea Stone cuffs!",
        "on_cooldown": "**🌀 Haki Exhausted!** You need to wait {time} before your next robbery attempt!"
    }
}

@app.on_message(filters.command("rob"))
async def rob_command(client: Client, message: Message):
    # Check if replying to a user
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply_text(
            "**🏴‍☠️ Grand Line Robbery**\n\n"
            "⚠️ Reply to someone's message to challenge them!\n"
            "Example: `/rob` (reply to user)\n\n"
            "💰 **Risk:** You might get jailed in Impel Down!\n"
            "⚔️ **Haki vs Haki combat determines success!**\n"
            "🍎 **Devil Fruits can give you an edge!**"
        )

    robber = message.from_user
    victim = message.reply_to_message.from_user

    # Can't rob bots
    if victim.is_bot:
        return await message.reply_text(ROB_MESSAGES["errors"]["bot_protected"])

    # Can't rob yourself
    if robber.id == victim.id:
        return await message.reply_text(ROB_MESSAGES["errors"]["self_rob"])

    # Check if user is jailed
    if robber.id in jailed_users:
        jail_time_left = jailed_users[robber.id] - time.time()
        if jail_time_left > 0:
            mins = int(jail_time_left // 60)
            secs = int(jail_time_left % 60)
            return await message.reply_text(
                ROB_MESSAGES["errors"]["jailed"].format(
                    time=f"{mins}m {secs}s"
                )
            )
        del jailed_users[robber.id]

    # Check cooldown
    if robber.id in rob_cooldowns:
        cooldown_left = rob_cooldowns[robber.id] - time.time()
        if cooldown_left > 0:
            mins = int(cooldown_left // 60)
            secs = int(cooldown_left % 60)
            return await message.reply_text(
                ROB_MESSAGES["errors"]["on_cooldown"].format(
                    time=f"{mins}m {secs}s"
                )
            )
        del rob_cooldowns[robber.id]

    # Get user data efficiently in one query
    users_data = await user_collection.find(
        {'id': {'$in': [robber.id, victim.id]}}
    ).to_list(length=2)
    
    robber_data = next((u for u in users_data if u['id'] == robber.id), None)
    victim_data = next((u for u in users_data if u['id'] == victim.id), None)

    # Check if robber has any Haki
    if not robber_data or not robber_data.get("haki"):
        return await message.reply_text(ROB_MESSAGES["errors"]["no_haki"])

    # Get balances safely
    robber_balance = await safe_get_balance(robber.id)
    victim_balance = await safe_get_balance(victim.id)

    # Check if victim has enough to rob
    if victim_balance < 1000:
        return await message.reply_text(
            ROB_MESSAGES["errors"]["victim_poor"].format(victim=victim.first_name)
        )
    
    # Calculate rob amount (10-40% of victim's balance)
    max_rob = min(int(victim_balance * random.uniform(0.1, 0.4)), robber_balance * 10)
    rob_amount = random.randint(1000, max_rob) if max_rob > 1000 else 1000

    # Calculate Haki power
    robber_power = calculate_haki_power(robber_data.get("haki", {}))
    victim_power = calculate_haki_power(victim_data.get("haki", {})) if victim_data else 0

    # Apply Devil Fruit effects if any
    robber_fruit = robber_data.get("devil_fruit")
    victim_fruit = victim_data.get("devil_fruit") if victim_data else None
    
    # Robber fruit effects
    if robber_fruit:
        if robber_fruit == "gomu":
            robber_power = int(robber_power * 1.15)
        elif robber_fruit == "ope":
            rob_amount = int(rob_amount * 1.4)
        elif robber_fruit == "yami":
            victim_power = int(victim_power * 0.7)
    
    # Victim fruit effects
    if victim_fruit == "mera" and random.random() < 0.1:
        burn_amount = int(robber_balance * 0.1)
        if burn_amount > 0:
            await user_collection.update_one(
                {'id': robber.id},
                {"$inc": {"balance": -burn_amount}}
            )

    # Add random factor (10-25% of total power)
    robber_power += int(robber_power * random.uniform(0.1, 0.25))
    victim_power += int(victim_power * random.uniform(0.1, 0.25))

    # Get strongest Haki types
    robber_haki = max(robber_data["haki"].items(), key=lambda x: x[1])[0] if robber_data["haki"] else "no haki"
    victim_haki = max(victim_data["haki"].items(), key=lambda x: x[1])[0] if victim_data and victim_data.get("haki") else "no haki"

    # Calculate success chance
    power_diff = robber_power - victim_power
    success_chance = min(max(15, 50 + (power_diff // 2)), 85)  # Clamped between 15-85%

    # Critical conditions
    is_critical_success = random.randint(1, 100) <= 12 and power_diff > 40
    is_critical_fail = random.randint(1, 100) <= 18 and power_diff < -30

    # Send animation first
    if is_critical_success:
        anim_url = random.choice(ANIMATIONS["critical"])
    elif is_critical_fail:
        anim_url = random.choice(ANIMATIONS["jail"])
    elif random.randint(1, 100) <= success_chance:
        anim_url = random.choice(ANIMATIONS["success"])
    else:
        anim_url = random.choice(ANIMATIONS["fail"])
    
    await message.reply_animation(
        animation=anim_url,
        caption="**⚔️ Haki Clash in Progress!**\n\n"
                "The battle of wills is raging!\n"
                "The sea trembles from the collision of powers..."
    )
    await asyncio.sleep(3)  # Dramatic pause

    if is_critical_success:
        # Critical success - steal 2.5x amount
        stolen_amount = int(rob_amount * 2.5)
        await update_balances(robber.id, victim.id, stolen_amount)
        
        haki_name = f"{HAKI_TYPES.get(robber_haki, {}).get('emoji', '🌀')} {HAKI_TYPES.get(robber_haki, {}).get('name', 'Haki')}"
        
        msg = random.choice(ROB_MESSAGES["critical"]["success"]).format(
            robber=f"**{robber.first_name}**",
            victim=f"**{victim.first_name}**",
            amount=f"`{stolen_amount:,}`",
            haki=haki_name
        )
        
        await message.reply_text(
            f"💥 **CRITICAL HAKI SUCCESS!** 💥\n\n{msg}\n\n"
            f"⚔️ **Haki Power:** `{robber_power:,}` vs `{victim_power:,}`\n"
            f"💰 **Bonus:** Stole 2.5x amount with supreme Haki!\n"
            f"{'🍎 **Devil Fruit Effect:** ' + DEVIL_FRUITS.get(robber_fruit, {}).get('effect', '') if robber_fruit else ''}"
        )
        
    elif is_critical_fail:
        # Critical fail - go to jail
        jail_time = random.randint(0) * 0  # 10-30 minutes
        jailed_users[robber.id] = time.time() + jail_time
        
        jail_level = random.choice([
            "1 (Crimson Hell)", 
            "2 (Wild Beast Hell)", 
            "3 (Starvation Hell)", 
            "4 (Blazing Hell)", 
            "5 (Freezing Hell)", 
            "6 (Eternal Hell)",
            "5.5 (Newkama Land)"
        ])
        
        await message.reply_text(
            random.choice(ROB_MESSAGES["critical"]["fail"]).format(
                robber=f"**{robber.first_name}**",
                time=jail_time//60
            ) + f"\n\n**🔒 Level:** {jail_level}\n**⏳ Sentence:** {jail_time//60} minutes\n"
            f"{'🍎 **Devil Fruit Effect:** ' + DEVIL_FRUITS.get(victim_fruit, {}).get('effect', '') if victim_fruit else ''}"
        )
        
    elif random.randint(1, 100) <= success_chance:
        # Normal success
        await update_balances(robber.id, victim.id, rob_amount)
        
        haki_name = f"{HAKI_TYPES.get(robber_haki, {}).get('emoji', '🌀')} {HAKI_TYPES.get(robber_haki, {}).get('name', 'Haki')}"
        
        await message.reply_text(
            random.choice(ROB_MESSAGES["success"]).format(
                robber=f"**{robber.first_name}**",
                victim=f"**{victim.first_name}**",
                amount=f"`{rob_amount:,}`",
                haki=haki_name
            ) + f"\n\n⚔️ **Haki Power:** `{robber_power:,}` vs `{victim_power:,}`\n"
            f"{'🍎 **Devil Fruit Effect:** ' + DEVIL_FRUITS.get(robber_fruit, {}).get('effect', '') if robber_fruit else ''}"
        )
        
    else:
        # Normal fail
        cooldown = random.randint(0) * 0  # 5-15 minutes
        rob_cooldowns[robber.id] = time.time() + cooldown
        
        haki_name = f"{HAKI_TYPES.get(victim_haki, {}).get('emoji', '🌀')} {HAKI_TYPES.get(victim_haki, {}).get('name', 'Haki')}" if victim_data else "basic willpower"
        
        await message.reply_text(
            random.choice(ROB_MESSAGES["fail"]).format(
                robber=f"**{robber.first_name}**",
                victim=f"**{victim.first_name}**",
                haki=haki_name
            ) + f"\n\n⏳ **Cooldown:** {cooldown//60} minutes\n"
            f"{'🍎 **Devil Fruit Effect:** ' + DEVIL_FRUITS.get(victim_fruit, {}).get('effect', '') if victim_fruit else ''}"
        )

@app.on_message(filters.command("hakishop"))
async def haki_shop(client: Client, message: Message):
    buttons = []
    for haki_type, data in HAKI_TYPES.items():
        buttons.append(
            [InlineKeyboardButton(
                f"{data['emoji']} {data['name']}",
                callback_data=f"haki_store_{haki_type}"
            )]
        )
    
    buttons.append([InlineKeyboardButton("🍎 Devil Fruit Shop", callback_data="devil_fruit_shop")])
    
    await message.reply_text(
        "**🏴‍☠️ Haki Training Dojo**\n\n"
        "Master the three types of Haki to dominate the Grand Line:\n\n"
        "👁️ **Observation Haki:** See into the future and predict movements\n"
        "⚔️ **Armament Haki:** Hardens your attacks to bypass defenses\n"
        "👑 **Conqueror's Haki:** Overwhelm weak-willed foes with sheer willpower\n\n"
        "**Upgrade your Haki to become Pirate King!**\n"
        "Check out Devil Fruits for additional powers!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.command("devilshop"))
async def devil_shop(client: Client, message: Message):
    buttons = []
    for fruit_id, fruit_data in DEVIL_FRUITS.items():
        buttons.append(
            [InlineKeyboardButton(
                f"{fruit_data['emoji']} {fruit_data['name']} - {fruit_data['price']:,} Berries",
                callback_data=f"devil_buy_{fruit_id}"
            )]
        )
    
    buttons.append([InlineKeyboardButton("⚔️ Haki Shop", callback_data="haki_shop_back")])
    
    user_data = await user_collection.find_one({'id': message.from_user.id})
    current_fruit = user_data.get("devil_fruit") if user_data else None
    
    await message.reply_text(
        "**🍎 Devil Fruit Black Market**\n\n"
        "Consume these mysterious fruits for incredible powers!\n"
        "But beware - you'll lose the ability to swim!\n\n"
        f"**Your current fruit:** {DEVIL_FRUITS.get(current_fruit, {}).get('name', 'None')}\n\n"
        "Available fruits:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^haki_store_"))
async def haki_store_callback(client, callback):
    haki_type = callback.data.split("_")[-1]
    if haki_type not in HAKI_TYPES:
        return await callback.answer("Invalid Haki type!", show_alert=True)
    
    user_data = await user_collection.find_one({'id': callback.from_user.id})
    if not user_data:
        return await callback.answer("You need to /start first!", show_alert=True)
    
    buttons = []
    for level, info in HAKI_TYPES[haki_type]["levels"].items():
        disabled = user_data.get("haki", {}).get(haki_type, 0) >= level
        buttons.append(
            [InlineKeyboardButton(
                f"{HAKI_TYPES[haki_type]['emoji']} Level {level} - {info['price']:,} Berries {'✅' if disabled else ''}",
                callback_data=f"buy_haki_{haki_type}_{level}" if not disabled else "already_owned"
            )]
        )
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="haki_store_back")])
    
    current_level = user_data.get("haki", {}).get(haki_type, 0)
    
    await callback.message.edit_text(
        f"**{HAKI_TYPES[haki_type]['emoji']} {HAKI_TYPES[haki_type]['name']}**\n\n"
        f"**Your current level:** {current_level}\n\n"
        "Upgrade levels:\n"
        f"1. {HAKI_TYPES[haki_type]['levels'][1]['desc']}\n"
        f"2. {HAKI_TYPES[haki_type]['levels'][2]['desc']}\n"
        f"3. {HAKI_TYPES[haki_type]['levels'][3]['desc']}\n"
        f"4. {HAKI_TYPES[haki_type]['levels'][4]['desc']}\n\n"
        "Each level significantly increases your power in Haki clashes!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^buy_haki_"))
async def buy_haki_callback(client, callback):
    try:
        _, _, haki_type, level = callback.data.split("_")
        level = int(level)
        
        if haki_type not in HAKI_TYPES or level not in [1, 2, 3, 4]:
            return await callback.answer("Invalid selection!", show_alert=True)
        
        user_data = await user_collection.find_one({'id': callback.from_user.id})
        if not user_data:
            return await callback.answer("You need to /start first!", show_alert=True)
        
        price = HAKI_TYPES[haki_type]["levels"][level]["price"]
        balance = await safe_get_balance(callback.from_user.id)
        
        if balance < price:
            return await callback.answer(
                f"You need {price:,} Berries! You only have {balance:,}",
                show_alert=True
            )
        
        current_level = user_data.get("haki", {}).get(haki_type, 0)
        if current_level >= level:
            return await callback.answer(
                f"You already have level {current_level} or higher!",
                show_alert=True
            )
        
        # Update in single operation
        await user_collection.update_one(
            {'id': callback.from_user.id},
            {
                "$inc": {"balance": -price},
                "$set": {f"haki.{haki_type}": level}
            }
        )
        
        await callback.answer(
            f"🎉 You mastered {HAKI_TYPES[haki_type]['name']} Level {level}!",
            show_alert=True
        )
        
        # Refresh the store view
        await haki_store_callback(client, callback)
        
    except Exception as e:
        await callback.answer("Error processing request", show_alert=True)

@app.on_callback_query(filters.regex("^devil_buy_"))
async def buy_devil_fruit(client, callback):
    fruit_id = callback.data.split("_")[-1]
    if fruit_id not in DEVIL_FRUITS:
        return await callback.answer("Invalid fruit!", show_alert=True)
    
    user_data = await user_collection.find_one({'id': callback.from_user.id})
    if not user_data:
        return await callback.answer("You need to /start first!", show_alert=True)
    
    price = DEVIL_FRUITS[fruit_id]["price"]
    balance = await safe_get_balance(callback.from_user.id)
    
    if balance < price:
        return await callback.answer(
            f"You need {price:,} Berries! You have {balance:,}",
            show_alert=True
        )
    
    current_fruit = user_data.get("devil_fruit")
    if current_fruit == fruit_id:
        return await callback.answer(
            "You already have this Devil Fruit!",
            show_alert=True
        )
    
    # Update user with new fruit
    await user_collection.update_one(
        {'id': callback.from_user.id},
        {
            "$inc": {"balance": -price},
            "$set": {"devil_fruit": fruit_id}
        }
    )
    
    await callback.answer(
        f"🍎 You ate the {DEVIL_FRUITS[fruit_id]['name']}! {DEVIL_FRUITS[fruit_id]['effect']}",
        show_alert=True
    )
    
    # Show animation of eating fruit
    await callback.message.reply_animation(
        animation="https://files.catbox.moe/ubdflh.jpg",  # Eating animation
        caption=f"**🍎 Devil Fruit Consumed!**\n\n"
               f"{callback.from_user.first_name} ate the {DEVIL_FRUITS[fruit_id]['name']}!\n"
               f"**Effect:** {DEVIL_FRUITS[fruit_id]['effect']}\n\n"
               f"But now you can't swim! ⚠️"
    )

@app.on_callback_query(filters.regex("^haki_store_back$"))
async def haki_store_back(client, callback):
    await haki_shop(client, callback.message)

@app.on_callback_query(filters.regex("^devil_fruit_shop$"))
async def devil_fruit_shop_callback(client, callback):
    await devil_shop(client, callback.message)

@app.on_callback_query(filters.regex("^haki_shop_back$"))
async def haki_shop_back_callback(client, callback):
    await haki_shop(client, callback.message)

@app.on_callback_query(filters.regex("^already_owned$"))
async def already_owned(client, callback):
    await callback.answer("You already own this upgrade!", show_alert=True)

@app.on_message(filters.command("crewrank"))
async def crew_rank(client: Client, message: Message):
    user_data = await user_collection.find_one({'id': message.from_user.id})
    if not user_data:
        return await message.reply_text("You need to /start first!")
    
    balance = await safe_get_balance(message.from_user.id)
    current_rank = 0
    next_rank = None
    
    # Find current rank
    for rank, data in sorted(CREW_RANKS.items(), reverse=True):
        if balance >= data["req"]:
            current_rank = rank
            break
    
    # Find next rank
    for rank, data in sorted(CREW_RANKS.items()):
        if balance < data["req"]:
            next_rank = data
            break
    
    rank_progress = balance - CREW_RANKS[current_rank]["req"]
    if next_rank:
        rank_needed = next_rank["req"] - CREW_RANKS[current_rank]["req"]
        progress_percent = (rank_progress / rank_needed) * 100
    else:
        progress_percent = 100
    
    # Create progress bar
    progress_bar = "🟩" * int(progress_percent // 10) + "⬜" * (10 - int(progress_percent // 10))
    
    await message.reply_text(
        f"**🏴‍☠️ Crew Rank Progress**\n\n"
        f"**Current Rank:** {CREW_RANKS[current_rank]['name']}\n"
        f"**Total Berries:** {balance:,}\n\n"
        f"{'**Next Rank:** ' + next_rank['name'] + ' (Need ' + str(next_rank['req'] - balance) + ' more berries)' if next_rank else '**MAX RANK ACHIEVED!** 👑'}\n\n"
        f"**Progress:** {progress_bar} {int(progress_percent)}%\n"
        f"`{rank_progress:,}/{rank_needed:, if next_rank else 'MAX'}`"
    )

@app.on_message(filters.command("oprofile"))
async def profile(client: Client, message: Message):
    user_data = await user_collection.find_one({'id': message.from_user.id})
    if not user_data:
        return await message.reply_text("You need to /start first!")
    
    balance = await safe_get_balance(message.from_user.id)
    
    # Calculate crew rank
    current_rank = 0
    for rank, data in sorted(CREW_RANKS.items(), reverse=True):
        if balance >= data["req"]:
            current_rank = rank
            break
    
    # Format Haki display
    haki_display = []
    if user_data.get("haki"):
        for haki_type, level in user_data["haki"].items():
            if haki_type in HAKI_TYPES:
                haki_display.append(
                    f"{HAKI_TYPES[haki_type]['emoji']} {HAKI_TYPES[haki_type]['name']} - Level {level}"
                )
    
    # Format Devil Fruit display
    fruit_display = "None"
    if user_data.get("devil_fruit"):
        fruit_display = f"{DEVIL_FRUITS[user_data['devil_fruit']]['emoji']} {DEVIL_FRUITS[user_data['devil_fruit']]['name']}"
    
    # Check jail status
    jail_status = ""
    if message.from_user.id in jailed_users:
        jail_time_left = jailed_users[message.from_user.id] - time.time()
        if jail_time_left > 0:
            mins = int(jail_time_left // 60)
            secs = int(jail_time_left % 60)
            jail_status = f"\n\n⛓️ **Impel Down Sentence:** {mins}m {secs}s remaining"
    
    # Check cooldown status
    cooldown_status = ""
    if message.from_user.id in rob_cooldowns:
        cooldown_left = rob_cooldowns[message.from_user.id] - time.time()
        if cooldown_left > 0:
            mins = int(cooldown_left // 60)
            secs = int(cooldown_left % 60)
            cooldown_status = f"\n\n⏳ **Rob Cooldown:** {mins}m {secs}s remaining"
    
    await message.reply_text(
        f"**🏴‍☠️ Pirate Profile**\n\n"
        f"**Name:** {message.from_user.first_name}\n"
        f"**Crew Rank:** {CREW_RANKS[current_rank]['name']}\n"
        f"**Total Berries:** {balance:,}\n\n"
        f"**Haki Powers:**\n" + ("\n".join(haki_display) if haki_display else "None") + "\n\n"
        f"**Devil Fruit:** {fruit_display}\n"
        f"{jail_status}{cooldown_status}"
    )

# Optimized helper functions
async def safe_get_balance(user_id):
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        return 0
    
    balance = user_data.get("balance", 0)
    if isinstance(balance, str):
        try:
            balance = int(balance)
            await user_collection.update_one(
                {'id': user_id},
                {"$set": {"balance": balance}}
            )
        except:
            balance = 0
    
    return balance

def calculate_haki_power(haki_data):
    if not haki_data:
        return 0
    return sum(
        HAKI_TYPES[haki_type]["levels"][level]["power"]
        for haki_type, level in haki_data.items()
        if haki_type in HAKI_TYPES and level in HAKI_TYPES[haki_type]["levels"]
    )

async def update_balances(robber_id, victim_id, amount):
    await asyncio.gather(
        user_collection.update_one(
            {'id': robber_id},
            {"$inc": {"balance": amount}},
            upsert=True
        ),
        user_collection.update_one(
            {'id': victim_id},
            {"$inc": {"balance": -amount}},
            upsert=True
        )
            )
