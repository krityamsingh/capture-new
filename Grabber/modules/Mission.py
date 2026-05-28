import asyncio
import random
import string
from datetime import datetime, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputMediaPhoto, 
    InputMediaVideo, 
    CallbackQuery
)
from . import app, collection, user_collection, mission_collection, ac
from Grabber import SUPPORT_GROUP, OWNER_IDS, BOT_USERNAME

# ==== OWNER IDS NORMALIZATION (ONLY ADJUSTMENT) ====
# Make OWNER_ID safe for use in filters.user()
if isinstance(OWNER_IDS, (set, list)):
    OWNER_ID = tuple(OWNER_IDS)
else:
    OWNER_ID = OWNER_IDS
# ===================================================

# ========================
# CONSTANTS (Upgraded)
# ========================

BATTLE_GIFS = [
    "https://files.catbox.moe/lknesv.mp4",
    "https://files.catbox.moe/az1n51.mp4",
    "https://files.catbox.moe/umq03m.mp4"
]

WIN_MESSAGES = [
    "🔥 {winner} ᴅᴏᴍɪɴᴀᴛᴇᴅ ᴛʜᴇ ʙᴀᴛᴛʟᴇғɪᴇʟᴅ!",
    "🎯 {winner} sᴄᴏʀᴇᴅ ᴀ ᴘᴇʀғᴇᴄᴛ ᴠɪᴄᴛᴏʀʏ!",
    "💥 {winner} ᴄʀᴜsʜᴇᴅ ᴛʜᴇ ᴄᴏᴍᴘᴇᴛɪᴛɪᴏɴ!",
    "⚡ {winner} ᴇᴍᴇʀɢᴇᴅ ᴠɪᴄᴛᴏʀɪᴏᴜs ᴡɪᴛʜ ʟɪɢʜᴛɴɪɴɢ sᴘᴇᴇᴅ!"
]

LOSE_MESSAGES = [
    "😢 {loser} ᴘᴜᴛ ᴜᴘ ᴀ ɢᴏᴏᴅ ғɪɢʜᴛ ʙᴜᴛ ғᴇʟʟ sʜᴏʀᴛ...",
    "💔 {loser} ғᴏᴜɢʜᴛ ʙʀᴀᴠᴇʟʏ ʙᴜᴛ ᴡᴀs ᴅᴇғᴇᴀᴛᴇᴅ",
    "🌪️ {loser} ɢᴏᴛ sᴡᴇᴘᴛ ᴀᴡᴀʏ ʙʏ ᴛʜᴇ ᴏᴘᴘᴏɴᴇɴᴛ's ᴘᴏᴡᴇʀ",
    "🌑 {loser} ᴡᴀs ᴏᴠᴇʀᴡʜᴇʟᴍᴇᴅ ʙʏ ᴅᴀʀᴋɴᴇss"
]

AFIGHT_GIFS = [
    "https://files.catbox.moe/az1n51.mp4",
    "https://files.catbox.moe/qsuzc3.mp4",
    "https://files.catbox.moe/umq03m.mp4"
]

AFIGHT_CHARACTERS = [
    {"name": "Naruto Uzumaki", "image": "https://files.catbox.moe/akubnl.jpg", "power": 90},
    {"name": "Goku", "image": "https://files.catbox.moe/0yw1vt.jpg", "power": 95},
    {"name": "Luffy", "image": "https://files.catbox.moe/nz3ndr.jpg", "power": 85},
    {"name": "Levi Ackerman", "image": "https://files.catbox.moe/5m6g1x.jpg", "power": 80},
    {"name": "Sasuke Uchiha", "image": "https://files.catbox.moe/qrf2v0.jpg", "power": 88},
    {"name": "Zoro Roronoa", "image": "https://files.catbox.moe/l98diz.jpg", "power": 82}
]

DIAMOND_IMAGES = [
    "https://files.catbox.moe/hd69ii.jpg",
    "https://files.catbox.moe/xvg9gk.jpg",
    "https://files.catbox.moe/hu35ky.jpg"
]

MISSION_VIDEOS = [
    "https://files.catbox.moe/7i30nq.mp4",
    "https://files.catbox.moe/pczcz5.mp4",
    "https://files.catbox.moe/1lgo71.mp4"
]

SUPPORT_GROUP_TASKS = {
    "required_bio": f"@{BOT_USERNAME}"
}

# ========================
# UTILITY FUNCTIONS (Upgraded)
# ========================

def bold(text): 
    return f"**{text}**"

def generate_battle_id(): 
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_diamond_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_mission_progress(missions):
    progress = []
    for name, mission in missions.items():
        status = "✅" if mission.get("completed", False) else "❌"
        mission_name = mission.get('name', 'Unknown Mission')
        details = f"{status} {bold(mission_name)}"
        
        # Add specific details for each mission type
        if name == "mbattle" and not mission.get("completed", False):
            wins = mission.get("wins", 0)
            required = mission.get("required_wins", 3)
            details += f" ({wins}/{required} ᴡɪɴs)"
        elif name == "playgame" and not mission.get("completed", False):
            wins = mission.get("wins", 0)
            required = mission.get("required_wins", 2)
            details += f" ({wins}/{required} ᴡɪɴs)"
        elif name == "afight" and not mission.get("completed", False):
            wins = mission.get("wins", 0)
            required = mission.get("required_wins", 3)
            power = mission.get("power_level", 50)
            details += f" ({wins}/{required} ᴡɪɴs) | 💪ᴘᴏᴡᴇʀ: {power}"
        elif name == "diamond" and not mission.get("completed", False):
            attempts = mission.get("attempts_used", 0)
            details += f" ({3 - attempts}/3 ᴀᴛᴛᴇᴍᴘᴛs ʟᴇғᴛ)"
            
        progress.append(details)
    return progress

# ========================
# MISSION SYSTEM (Upgraded)
# ========================

MISSION_TEMPLATE = {
    "start": {
        "name": "🌟 Mission Start",
        "description": "ʙᴇɢɪɴ ʏᴏᴜʀ ᴀᴅᴠᴇɴᴛᴜʀᴇ",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False
    },
    "mbattle": {
        "name": "⚔️ Multi Battle",
        "description": "ᴡɪɴ PvP ʙᴀᴛᴛʟᴇs ᴀɢᴀɪɴsᴛ ᴏᴛʜᴇʀ ᴜsᴇʀs",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False,
        "wins": 0,
        "losses": 0,
        "required_wins": 3,
        "current_streak": 0,
        "best_streak": 0
    },
    "playgame": {
        "name": "🎮 Tic Tac Toe",
        "description": "ᴡɪɴ ɢᴀᴍᴇs ᴏғ ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False,
        "wins": 0,
        "losses": 0,
        "required_wins": 2
    },
    "mtask": {
        "name": "📌 Support Task",
        "description": f"ᴀᴅᴅ @{BOT_USERNAME} ᴛᴏ ʏᴏᴜʀ ʙɪᴏ",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False,
        "bio_updated": False
    },
    "afight": {
        "name": "🔥 Alone Fight",
        "description": "ᴡɪɴ sᴏʟᴏ ʙᴀᴛᴛʟᴇs ᴀɢᴀɪɴsᴛ ᴘᴏᴡᴇʀғᴜʟ AI ᴏᴘᴘᴏɴᴇɴᴛs",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False,
        "wins": 0,
        "losses": 0,
        "required_wins": 3,
        "loss_streak": 0,
        "power_level": 50,
        "power_boosts_used": 0,
        "max_power_boosts": 3
    },
    "diamond": {
        "name": "💎 Diamond Hunt",
        "description": "ғɪɴᴅ ᴛʜᴇ ʜɪᴅᴅᴇɴ ᴅɪᴀᴍᴏɴᴅ ɪɴ 12 ʙᴜᴛᴛᴏɴs",
        "completed": False,
        "completed_at": None,
        "reward_claimed": False,
        "attempts_used": 0,
        "max_attempts": 3,
        "diamonds_found": 0,
        "required_diamonds": 1,
        "last_attempt": None
    }
}

async def init_user_missions(user_id):
    user_data = await user_collection.find_one({"user_id": user_id})
    
    if user_data and "missions" in user_data:
        missions = user_data["missions"]
        # Ensure all mission types exist
        for mission_key, template in MISSION_TEMPLATE.items():
            if mission_key not in missions:
                missions[mission_key] = template.copy()
        
        # Reset diamond attempts if it's a new day
        if "diamond" in missions:
            diamond_mission = missions["diamond"]
            if diamond_mission.get("last_attempt"):
                last_attempt = diamond_mission["last_attempt"]
                if isinstance(last_attempt, str):
                    last_attempt = datetime.fromisoformat(last_attempt)
                
                if datetime.now().date() > last_attempt.date():
                    diamond_mission["attempts_used"] = 0
                    diamond_mission["last_attempt"] = datetime.now()
        
        return missions
    
    # Create new missions for the user
    missions = {key: value.copy() for key, value in MISSION_TEMPLATE.items()}
    missions["start"]["completed"] = True
    missions["start"]["completed_at"] = datetime.now()
    
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {"missions": missions, "created_at": datetime.now(), "missions_claimed": False}},
        upsert=True
    )
    
    return missions

async def save_user_missions(user_id, missions):
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {"missions": missions, "updated_at": datetime.now()}}
    )

# ========================
# GAME SYSTEMS (Upgraded)
# ========================

class BattleSystem:
    def __init__(self):
        self.active_battles = {}
        self.battle_requests = {}
    
    async def send_battle_request(self, client, message):
        if not message.reply_to_message:
            await message.reply(bold("⚠️ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ʙᴀᴛᴛʟᴇ!"))
            return
            
        challenger = message.from_user
        opponent = message.reply_to_message.from_user
        
        if challenger.id == opponent.id:
            await message.reply(bold("❌ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ʙᴀᴛᴛʟᴇ ʏᴏᴜʀsᴇʟғ!"))
            return
            
        if opponent.is_bot:
            await message.reply(bold("❌ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ʙᴀᴛᴛʟᴇ ʙᴏᴛs!"))
            return
            
        battle_id = generate_battle_id()
        self.battle_requests[battle_id] = {
            "challenger": challenger.id,
            "opponent": opponent.id,
            "message_id": message.id,
            "created_at": datetime.now()
        }
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ᴀᴄᴄᴇᴘᴛ ʙᴀᴛᴛʟᴇ", callback_data=f"accept_battle_{battle_id}")],
            [InlineKeyboardButton("❌ ʀᴇᴊᴇᴄᴛ ʙᴀᴛᴛʟᴇ", callback_data=f"reject_battle_{battle_id}")]
        ])
        
        await message.reply_animation(
            random.choice(BATTLE_GIFS),
            caption=bold(f"⚔️ {challenger.first_name} ᴄʜᴀʟʟᴇɴɢᴇᴅ {opponent.first_name} ᴛᴏ ᴀ ʙᴀᴛᴛʟᴇ!\n\nᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇᴘᴛ ᴏʀ ʀᴇᴊᴇᴄᴛ."),
            reply_markup=keyboard
        )
    
    async def start_battle(self, client, callback, battle_id):
        if battle_id not in self.battle_requests:
            await callback.answer("ʙᴀᴛᴛʟᴇ ʀᴇǫᴜᴇsᴛ ᴇxᴘɪʀᴇᴅ!", show_alert=True)
            return
            
        battle = self.battle_requests[battle_id]
        challenger_id = battle["challenger"]
        opponent_id = battle["opponent"]
        
        if callback.from_user.id != opponent_id:
            await callback.answer("ᴛʜɪs ʙᴀᴛᴛʟᴇ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ғᴏʀ ʏᴏᴜ!", show_alert=True)
            return
            
        # Get user missions
        challenger_missions = await init_user_missions(challenger_id)
        opponent_missions = await init_user_missions(opponent_id)
        
        # Determine winner (random for now)
        winner_id = random.choice([challenger_id, opponent_id])
        loser_id = challenger_id if winner_id == opponent_id else opponent_id
        
        # Get user info
        winner_user = await client.get_users(winner_id)
        loser_user = await client.get_users(loser_id)
        
        # Update missions
        if "mbattle" in challenger_missions:
            if winner_id == challenger_id:
                challenger_missions["mbattle"]["wins"] += 1
                challenger_missions["mbattle"]["current_streak"] += 1
                if challenger_missions["mbattle"]["current_streak"] > challenger_missions["mbattle"]["best_streak"]:
                    challenger_missions["mbattle"]["best_streak"] = challenger_missions["mbattle"]["current_streak"]
            else:
                challenger_missions["mbattle"]["losses"] += 1
                challenger_missions["mbattle"]["current_streak"] = 0
                
            # Check if mission completed
            if challenger_missions["mbattle"]["wins"] >= challenger_missions["mbattle"]["required_wins"]:
                challenger_missions["mbattle"]["completed"] = True
                challenger_missions["mbattle"]["completed_at"] = datetime.now()
        
        if "mbattle" in opponent_missions:
            if winner_id == opponent_id:
                opponent_missions["mbattle"]["wins"] += 1
                opponent_missions["mbattle"]["current_streak"] += 1
                if opponent_missions["mbattle"]["current_streak"] > opponent_missions["mbattle"]["best_streak"]:
                    opponent_missions["mbattle"]["best_streak"] = opponent_missions["mbattle"]["current_streak"]
            else:
                opponent_missions["mbattle"]["losses"] += 1
                opponent_missions["mbattle"]["current_streak"] = 0
                
            # Check if mission completed
            if opponent_missions["mbattle"]["wins"] >= opponent_missions["mbattle"]["required_wins"]:
                opponent_missions["mbattle"]["completed"] = True
                opponent_missions["mbattle"]["completed_at"] = datetime.now()
        
        # Save missions
        await save_user_missions(challenger_id, challenger_missions)
        await save_user_missions(opponent_id, opponent_missions)
        
        # Send battle result
        win_message = random.choice(WIN_MESSAGES).format(winner=winner_user.first_name)
        lose_message = random.choice(LOSE_MESSAGES).format(loser=loser_user.first_name)
        
        result_text = f"<blockquote>{win_message}</blockquote>\n\n{lose_message}\n\n"
        result_text += f"🏆 {winner_user.first_name} ᴡᴏɴ ᴛʜᴇ ʙᴀᴛᴛʟᴇ!\n\n"
        result_text += f"ᴄʜᴇᴄᴋ /mymission ғᴏʀ ᴘʀᴏɢʀᴇss"
        
        await callback.message.edit_caption(bold(result_text))
        await callback.answer("ʙᴀᴛᴛʟᴇ ᴄᴏᴍᴘʟᴇᴛᴇ!", show_alert=True)
        
        # Remove battle request
        del self.battle_requests[battle_id]

class AFightSystem:
    async def start_afight(self, client, message):
        user = message.from_user
        missions = await init_user_missions(user.id)
        afight_mission = missions["afight"]
        
        if afight_mission["completed"]:
            await message.reply(bold("🎉 ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀଡʏ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴀʟᴏɴᴇ ғɪɢʜᴛ ᴍɪssɪᴏɴ!\n\nᴜsᴇ /rmission ᴛᴏ ʀᴇsᴇᴛ ʏᴏᴜʀ ᴍɪssɪᴏɴs."))
            return
        
        # Select random opponent
        opponent = random.choice(AFIGHT_CHARACTERS)
        user_power = afight_mission["power_level"]
        
        # Calculate win chance (user power vs opponent power)
        win_chance = max(10, min(90, (user_power / opponent["power"]) * 50))
        is_win = random.randint(1, 100) <= win_chance
        
        # Update mission progress
        if is_win:
            afight_mission["wins"] += 1
            afight_mission["loss_streak"] = 0
            win_message = f"🎉 **{user.first_name}** ᴅᴇғᴇᴀᴛᴇᴅ **{opponent['name']}** (ᴘᴏᴡᴇʀ: {opponent['power']})!"
            
            # Check if mission completed
            if afight_mission["wins"] >= afight_mission["required_wins"]:
                afight_mission["completed"] = True
                afight_mission["completed_at"] = datetime.now()
                win_message += "\n\n<blockquote>🎊 ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜ'ᴠᴇ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴀʟᴏɴᴇ ғɪɢʜᴛ ᴍɪssɪᴏɴ!</blockquote>"
        else:
            afight_mission["losses"] += 1
            afight_mission["loss_streak"] += 1
            win_message = f"💔 **{user.first_name}** ᴡᴀs ᴅᴇғᴇᴀᴛᴇᴅ ʙʏ **{opponent['name']}** (ᴘᴏᴡᴇʀ: {opponent['power']})!"
        
        # Save mission progress
        await save_user_missions(user.id, missions)
        
        # Prepare result message
        result_text = f"{win_message}\n\n"
        result_text += f"😔ʟᴏss sᴛʀᴇᴀᴋ: {afight_mission['loss_streak']}\n"
        result_text += f"💪ʏᴏᴜʀ ᴘᴏᴡᴇʀ: {user_power}\n\n"
        result_text += f"ᴜsᴇ /power ᴛᴏ ʙᴏᴏsᴛ ʏᴏᴜʀ ᴘᴏᴡᴇʀ ({afight_mission['max_power_boosts'] - afight_mission['power_boosts_used']} ʙᴏᴏsᴛs ʟᴇғᴛ)\n\n"
        result_text += f"ᴄʜᴇᴄᴋ /mymission ғᴏʀ ᴘʀᴏɢʀᴇss"
        
        # Send result with GIF
        await message.reply_animation(
            random.choice(AFIGHT_GIFS),
            caption=bold(result_text)
        )

class DiamondHuntSystem:
    def __init__(self):
        self.active_games = {}
        
    async def start_diamond_hunt(self, client, message):
        user = message.from_user
        user_id = user.id
        user_name = user.first_name
        
        # Generate game ID
        game_id = generate_diamond_id()
        
        # Select diamond position (1-12)
        diamond_position = random.randint(1, 12)
        
        # Create game state with exactly 3 attempts for this command
        self.active_games[game_id] = {
            "user_id": user_id,
            "diamond_position": diamond_position,
            "buttons_clicked": [],
            "game_message_id": None,
            "attempts_remaining": 3,  # Exactly 3 attempts per /diamond command
            "session_diamonds_found": 0
        }
        
        # Create button grid (3x4)
        keyboard = []
        button_count = 1
        for i in range(3):
            row = []
            for j in range(4):
                row.append(InlineKeyboardButton("🔳", callback_data=f"diamond_{game_id}_{button_count}"))
                button_count += 1
            keyboard.append(row)
        
        # Add a cancel button
        keyboard.append([InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"diamond_cancel_{game_id}")])
        
        # Send game message
        random_diamond_image = random.choice(DIAMOND_IMAGES)
        game_message = await message.reply_photo(
            photo=random_diamond_image,
            caption=bold(f"💎 {user_name}, ғɪɴᴅ ᴛʜᴇ ʜɪᴅᴅᴇɴ ᴅɪᴀᴍᴏɴᴛ!\n\n"
                       f"📦 ʙᴜᴛᴛᴏɴs: 12 | 🔍 ᴀᴛᴛᴇᴍᴘᴛs: 3"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Store message ID
        self.active_games[game_id]["game_message_id"] = game_message.id
    
    async def handle_diamond_click(self, client, callback, game_id, button_num):
        user_id = callback.from_user.id
        
        # Check if game exists
        if game_id not in self.active_games:
            await callback.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ!", show_alert=True)
            return
        
        # Check if user owns this game
        if self.active_games[game_id]["user_id"] != user_id:
            await callback.answer("❌ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)
            return
        
        # Check if button already clicked
        if button_num in self.active_games[game_id]["buttons_clicked"]:
            await callback.answer("❌ ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄʟɪᴄᴋᴇᴅ ᴛʜɪs ʙᴜᴛᴛᴏɴ!", show_alert=True)
            return
        
        # Check if user has attempts remaining for this session
        if self.active_games[game_id]["attempts_remaining"] <= 0:
            await callback.answer("❌ ɴᴏ ᴀᴛᴛᴇᴍᴘᴛs ʀᴇᴍᴀɪɴɪɴɢ ɪɴ ᴛʜɪs sᴇssɪᴏɴ!", show_alert=True)
            return
        
        # Use one attempt
        self.active_games[game_id]["attempts_remaining"] -= 1
        self.active_games[game_id]["buttons_clicked"].append(button_num)
        
        # Get user missions
        missions = await init_user_missions(user_id)
        diamond_mission = missions["diamond"]
        
        # Check if user found the diamond
        if button_num == self.active_games[game_id]["diamond_position"]:
            # User found the diamond!
            self.active_games[game_id]["session_diamonds_found"] += 1
            diamond_mission["diamonds_found"] += 1
            
            # Update mission completion status
            if diamond_mission["diamonds_found"] >= diamond_mission["required_diamonds"]:
                diamond_mission["completed"] = True
                diamond_mission["completed_at"] = datetime.now()
            
            # Save mission progress
            await save_user_missions(user_id, missions)
            
            # Update button to show diamond
            await self.update_button(client, callback, game_id, button_num, "💎", True)
            
            # Send win message
            win_caption = bold(f"🎉 ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs {callback.from_user.first_name}!\n\n"
                             f"ʏᴏᴜ ғᴏᴜɴᴅ ᴛʜᴇ ʜɪᴅᴅᴇɴ ᴅɪᴀᴍᴏɴᴛ!\n\n"
                             f"💎 ᴅɪᴀᴍᴏɴᴅs ғᴏᴜɴᴅ: {diamond_mission['diamonds_found']}/{diamond_mission['required_diamonds']}")
            
            # Check if mission is completed
            if diamond_mission["completed"]:
                win_caption += "\n\n✅ ᴍɪssɪᴏɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ! ᴜsᴇ /mymission ᴛᴏ ᴄʟᴀɪᴍ ʏᴏᴜʀ ʀᴇᴡᴀʀᴅ."
            
            await callback.message.edit_caption(
                caption=win_caption
            )
            
            # Remove game from active games
            if game_id in self.active_games:
                del self.active_games[game_id]
                
        else:
            # User didn't find the diamond
            await self.update_button(client, callback, game_id, button_num, "❌", False)
            
            # Check if user has attempts remaining in this session
            remaining_attempts = self.active_games[game_id]["attempts_remaining"]
            
            if remaining_attempts <= 0:
                # No attempts left in this session
                await callback.message.edit_caption(
                    caption=bold(f"❌ ɢᴀᴍᴇ ᴏᴠᴇʀ! ʏᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ 3 ᴀᴛᴛᴇᴍᴘᴛs.\n\n"
                               f"💎 ᴅɪᴀᴍᴏɴᴅs ғᴏᴜɴᴅ: {diamond_mission['diamonds_found']}/{diamond_mission['required_diamonds']}\n\n"
                               f"ᴜsᴇ /diamond ᴀɢᴀɪɴ ғᴏʀ ᴍᴏʀᴇ ᴀᴛᴛᴇᴍᴘᴛs!")
                )
                
                # Remove game from active games
                if game_id in self.active_games:
                    del self.active_games[game_id]
            else:
                # Update caption to show remaining attempts
                await callback.message.edit_caption(
                    caption=bold(f"💎 {callback.from_user.first_name}, ғɪɴᴅ ᴛʜᴇ ʜɪᴅᴅᴇɴ ᴅɪᴀᴍᴏɴᴛ!\n\n"
                               f"📦 ʙᴜᴛᴛᴏɴs: 12 | 🔍 ᴀᴛᴛᴇᴍᴘᴛs: {remaining_attempts}")
                )
    
    async def update_button(self, client, callback, game_id, button_num, emoji, is_diamond):
        # Get current keyboard
        current_keyboard = callback.message.reply_markup.inline_keyboard
        
        # Create new keyboard
        new_keyboard = []
        
        for row in current_keyboard:
            new_row = []
            for button in row:
                if button.callback_data and f"diamond_{game_id}_{button_num}" in button.callback_data:
                    # This is the clicked button - update only this one
                    if is_diamond:
                        # Diamond found - disable this button only
                        new_row.append(InlineKeyboardButton(f"{emoji}", callback_data="diamond_found"))
                    else:
                        # Wrong button - mark as wrong but keep it clickable (for visual consistency)
                        new_row.append(InlineKeyboardButton(f"{emoji}", callback_data=f"diamond_{game_id}_{button_num}"))
                elif button.callback_data and "diamond_cancel" in button.callback_data:
                    # Keep the cancel button as is
                    new_row.append(button)
                elif button.callback_data and "diamond_" in button.callback_data:
                    # Other diamond buttons - check if they were already clicked
                    btn_parts = button.callback_data.split("_")
                    if len(btn_parts) >= 3:
                        try:
                            btn_num = int(btn_parts[2])
                            if btn_num in self.active_games.get(game_id, {}).get("buttons_clicked", []):
                                # This button was already clicked - show X
                                new_row.append(InlineKeyboardButton("❌", callback_data=button.callback_data))
                            else:
                                # This button hasn't been clicked yet - show empty box
                                new_row.append(InlineKeyboardButton("🔳", callback_data=button.callback_data))
                        except ValueError:
                            new_row.append(button)
                    else:
                        new_row.append(button)
                else:
                    # Other buttons (like cancel)
                    new_row.append(button)
            
            new_keyboard.append(new_row)
        
        # Edit the message with updated keyboard
        try:
            await callback.message.edit_reply_markup(InlineKeyboardMarkup(new_keyboard))
        except Exception as e:
            print(f"Error updating reply markup: {e}")
    
    async def handle_cancel(self, client, callback, game_id):
        user_id = callback.from_user.id
        
        # Check if game exists
        if game_id not in self.active_games:
            await callback.answer("❌ ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        # Check if user owns this game
        if self.active_games[game_id]["user_id"] != user_id:
            await callback.answer("❌ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)
            return
        
        # Remove game from active games
        del self.active_games[game_id]
        
        # Update message
        await callback.message.edit_caption(
            caption=bold("❌ ᴅɪᴀᴍᴏɴᴅ ʜᴜɴᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ.")
        )
        
        await callback.answer("ɢᴀᴍᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ!", show_alert=False)

# ========================
# COMMAND HANDLERS (Upgraded)
# ========================

@app.on_message(filters.command("startmission"))
async def start_mission(client:Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    missions = await init_user_missions(user_id)
    
    if missions["start"]["completed"]:
        await message.reply_video(
            random.choice(MISSION_VIDEOS),
            caption=bold(f"🎯 {user_name}, ʏᴏᴜʀ ᴍɪssɪᴏɴs ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴇ!\n\nᴜsᴇ /mymission ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴘʀᴏɢʀᴇss.")
        )
        return
    
    missions["start"]["completed"] = True
    missions["start"]["completed_at"] = datetime.now()
    await save_user_missions(user_id, missions)
    
    welcome_text = f"<blockquote>🚀 ᴡᴇʟᴄᴏᴍᴇ {user_name} ᴛᴏ ᴛʜᴇ ᴜʟᴛɪᴍᴀᴛᴇ ᴍɪssɪᴏɴ sʏsᴛᴇᴍ!</blockquote>\n\n"
    welcome_text += "ʏᴏᴜʀ ᴀᴅᴠᴇɴᴛᴜʀᴇ ʜᴀs ʙᴇɢᴜɴ. ᴄᴏᴍᴘʟᴇᴛᴇ ᴍɪssɪᴏɴs ᴛᴏ ᴇᴀʀɴ ʀᴇᴡᴀʀᴅs!\n\n"
    welcome_text += "**ᴀᴠᴀɪʟᴀʙʟᴇ ᴍɪssɪᴏɴs:**\n"
    welcome_text += "• ⚔️ /mbattle - PvP ʙᴀᴛᴛʟᴇs\n"
    welcome_text += "• 🎮 /playgame - ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ\n"
    welcome_text += "• 📌 /mtask - sᴜᴘᴘᴏʀᴛ ᴛᴀsᴋ\n"
    welcome_text += "• 🔥 /afight - sᴏʟᴏ ʙᴀᴛᴛʟᴇs\n"
    welcome_text += "• 💎 /diamond - ᴅɪᴀᴍᴏɴᴅ ʜᴜɴᴛ\n\n"
    welcome_text += "ᴜsᴇ /mymission ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴘʀᴏɢʀᴇss!"
    
    await message.reply_video(
        random.choice(MISSION_VIDEOS),
        caption=bold(welcome_text)
    )

@app.on_message(filters.command("mymission"))
async def show_missions(client:Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    missions = await init_user_missions(user_id)
    
    progress = get_mission_progress(missions)
    
    mission_text = f"<blockquote>📊 {user_name}'s ᴍɪssɪᴏɴ ᴘʀᴏɢʀᴇss</blockquote>\n\n"
    mission_text += "\n".join(progress)
    mission_text += "\n\n**ʀᴇᴡᴀʀᴅs:**\n"
    mission_text += "• 🫧 Pʀᴇᴍɪᴜᴍ ᴄʜᴀʀᴀᴄᴛᴇʀs\n"
    mission_text += "• 💎 Exᴄʟᴜsɪᴠᴇ ɪᴛᴇᴍs\n"
    mission_text += "• ⚡ Sᴘᴇᴄɪᴀʟ ᴀʙɪʟɪᴛɪᴇs\n\n"
    
    # Check if all missions are completed
    all_completed = all(mission.get("completed", False) for mission in missions.values() if mission.get("name") != "Mission Start")
    
    # Get user data to check if rewards were already claimed
    user_data = await user_collection.find_one({"user_id": user_id})
    rewards_claimed = user_data.get("missions_claimed", False) if user_data else False
    
    if all_completed and not rewards_claimed:
        mission_text += "🎉 <blockquote>ᴀʟʟ ᴍɪssɪᴏɴs ᴄᴏᴍᴘʟᴇᴛᴇᴅ!</blockquote>\n\n"
        mission_text += "ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴄʟᴀɪᴍ ʏᴏᴜʀ ʀᴇᴡᴀʀᴅs!"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 ᴄʟᴀɪᴍ ʀᴇᴡᴀʀᴅs", callback_data="claim_rewards")]
        ])
    elif all_completed and rewards_claimed:
        mission_text += "✅ <blockquote>ᴀʟʟ ᴍɪssɪᴏɴs ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴀɴᴅ ʀᴇᴡᴀʀᴅs ᴄʟᴀɪᴍᴇᴅ!</blockquote>\n\n"
        mission_text += "ᴜsᴇ /rmission ᴛᴏ ʀᴇsᴇᴛ ᴍɪssɪᴏɴs"
        keyboard = None
    else:
        mission_text += "ᴋᴇᴇᴘ ɢᴏɪɴɢ! ʏᴏᴜ'ʀᴇ ᴅᴏɪɴɢ ɢʀᴇᴀᴛ! 💪"
        keyboard = None
    
    await message.reply_video(
        random.choice(MISSION_VIDEOS),
        caption=bold(mission_text),
        reply_markup=keyboard
    )

@app.on_message(filters.command("mbattle"))
async def multi_battle(client:Client, message: Message):
    await battle_system.send_battle_request(client, message)

@app.on_callback_query(filters.regex("^accept_battle_"))
async def handle_accept_battle(client, callback):
    battle_id = callback.data.split("_")[2]
    await battle_system.start_battle(client, callback, battle_id)

@app.on_callback_query(filters.regex("^reject_battle_"))
async def handle_reject_battle(client, callback):
    battle_id = callback.data.split("_")[2]
    if battle_id in battle_system.battle_requests:
        del battle_system.battle_requests[battle_id]
    await callback.answer("ʙᴀᴛᴛʟᴇ ʀᴇᴊᴇᴄᴛᴇᴅ!", show_alert=True)
    await callback.message.edit_caption(bold("❌ ʙᴀᴛᴛʟᴇ ʀᴇǫᴜᴇsᴛ ᴡᴀs ʀᴇᴊᴇᴄᴛᴇᴅ."))

@app.on_message(filters.command("playgame"))
async def play_game(client:Client, message: Message):
    if not message.reply_to_message:
        await message.reply(bold("⚠️ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ᴘʟᴀʏ!"))
        return
        
    challenger = message.from_user
    opponent = message.reply_to_message.from_user
    
    if challenger.id == opponent.id:
        await message.reply(bold("❌ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ᴘʟᴀʏ ᴀɢᴀɪɴsᴛ ʏᴏᴜʀsᴇʟғ!"))
        return
        
    if opponent.is_bot:
        await message.reply(bold("❌ ʏᴏᴜ ᴄᴀɴɴᴏᴛ ᴘʟᴀʏ ᴀɢᴀɪɴsᴛ ʙᴏᴛs!"))
        return
        
    game_id = generate_battle_id()
    ttt_games[game_id] = {
        "challenger": challenger.id,
        "opponent": opponent.id,
        "board": [[" " for _ in range(3)] for _ in range(3)],
        "current_player": challenger.id,
        "message_id": message.id,
        "created_at": datetime.now()
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ᴀᴄᴄᴇᴘᴛ ɢᴀᴍᴇ", callback_data=f"accept_ttt_{game_id}")],
        [InlineKeyboardButton("❌ ʀᴇᴊᴇᴄᴛ ɢᴀᴍᴇ", callback_data=f"reject_ttt_{game_id}")]
    ])
    
    await message.reply(
        bold(f"🎮 {challenger.first_name} ᴄʜᴀʟʟᴇɴɢᴇᴅ {opponent.first_name} ᴛᴏ ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ!\n\nᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇᴘᴛ ᴏʀ ʀᴇᴊᴇᴄᴛ."),
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^accept_ttt_"))
async def accept_ttt_game(client:Client, callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    game = ttt_games.get(game_id)
    
    if not game:
        await callback.answer("ɢᴀᴍᴇ ʀᴇǫᴜᴇsᴛ ᴇxᴘɪʀᴇᴅ!", show_alert=True)
        return
        
    if callback.from_user.id != game["opponent"]:
        await callback.answer("ᴛʜɪs ɢᴀᴍᴇ ʀᴇǫᴜᴇsᴛ ɪs ɴᴏᴛ ғᴏʀ ʏᴏᴜ!", show_alert=True)
        return
        
    # Create Tic Tac Toe board
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_0_0"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_0_1"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_0_2")
        ],
        [
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_1_0"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_1_1"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_1_2")
        ],
        [
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_2_0"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_2_1"),
            InlineKeyboardButton("🔲", callback_data=f"ttt_move_{game_id}_2_2")
        ]
    ])
    
    challenger = await client.get_users(game["challenger"])
    opponent = await client.get_users(game["opponent"])
    
    await callback.message.edit_text(
        bold(f"🎮 ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ: {challenger.first_name} vs {opponent.first_name}\n\n{challenger.first_name}'s ᴛᴜʀɴ (❌)"),
        reply_markup=keyboard
    )
    await callback.answer("ɢᴀᴍᴇ sᴛᴀʀᴛᴇᴅ!", show_alert=True)

@app.on_callback_query(filters.regex("^ttt_move_"))
async def ttt_make_move(client:Client, callback: CallbackQuery):
    parts = callback.data.split("_")
    game_id = parts[2]
    row, col = int(parts[3]), int(parts[4])
    game = ttt_games.get(game_id)
    
    if not game:
        await callback.answer("ɢᴀᴍᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
        return
        
    if callback.from_user.id != game["current_player"]:
        await callback.answer("ɴᴏᴛ ʏᴏᴜʀ ᴛᴜʀɴ!", show_alert=True)
        return
        
    if game["board"][row][col] != " ":
        await callback.answer("ᴘᴏsɪᴛɪᴏɴ ᴀʟʀᴇᴀᴅʏ ᴛᴀᴋᴇɴ!", show_alert=True)
        return
        
    # Make move
    symbol = "❌" if game["current_player"] == game["challenger"] else "⭕"
    game["board"][row][col] = symbol
    
    # Check for win
    winner = None
    board = game["board"]
    
    # Check rows
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != " ":
            winner = game["challenger"] if board[i][0] == "❌" else game["opponent"]
    
    # Check columns
    for i in range(3):
        if board[0][i] == board[1][i] == board[2][i] != " ":
            winner = game["challenger"] if board[0][i] == "❌" else game["opponent"]
    
    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] != " ":
        winner = game["challenger"] if board[0][0] == "❌" else game["opponent"]
    if board[0][2] == board[1][1] == board[2][0] != " ":
        winner = game["challenger"] if board[0][2] == "❌" else game["opponent"]
    
    # Check for draw
    is_draw = all(cell != " " for row in board for cell in row) and not winner
    
    # Update mission progress if there's a winner
    if winner:
        missions = await init_user_missions(winner)
        if "playgame" in missions:
            missions["playgame"]["wins"] += 1
            # Check if mission completed
            if missions["playgame"]["wins"] >= missions["playgame"]["required_wins"]:
                missions["playgame"]["completed"] = True
                missions["playgame"]["completed_at"] = datetime.now()
            await save_user_missions(winner, missions)
    
    # Update keyboard
    keyboard = callback.message.reply_markup.inline_keyboard
    new_keyboard = []
    
    for i, row_buttons in enumerate(keyboard):
        new_row = []
        for j, button in enumerate(row_buttons):
            if i == row and j == col:
                new_row.append(InlineKeyboardButton(symbol, callback_data="used"))
            else:
                new_row.append(button)
        new_keyboard.append(new_row)
    
    if winner or is_draw:
        # Game over, disable all buttons
        for i in range(3):
            for j in range(3):
                if new_keyboard[i][j].callback_data != "used":
                    new_keyboard[i][j] = InlineKeyboardButton("🔲", callback_data="used")
    
    # Update message
    challenger = await client.get_users(game["challenger"])
    opponent = await client.get_users(game["opponent"])
    
    if winner:
        winner_user = await client.get_users(winner)
        result_text = f"🎉 {winner_user.first_name} ᴡᴏɴ ᴛʜᴇ ɢᴀᴍᴇ!\n\n"
        result_text += f"ᴄʜᴇᴄᴋ /mymission ғᴏʀ ᴘʀᴏɢʀᴇss"
    elif is_draw:
        result_text = "🤝 ɢᴀᴍᴇ ᴇɴᴅᴇᴅ ɪɴ ᴀ ᴅʀᴀᴡ!\n\n"
        result_text += f"ᴘʟᴀʏ ᴀɢᴀɪɴ ᴡɪᴛʜ /playgame"
    else:
        # Switch player
        game["current_player"] = game["opponent"] if game["current_player"] == game["challenger"] else game["challenger"]
        next_player = await client.get_users(game["current_player"])
        symbol = "❌" if game["current_player"] == game["challenger"] else "⭕"
        result_text = f"{next_player.first_name}'s ᴛᴜʀɴ ({symbol})"
    
    await callback.message.edit_text(
        bold(f"🎮 ᴛɪᴄ ᴛᴀᴄ ᴛᴏᴇ: {challenger.first_name} vs {opponent.first_name}\n\n{result_text}"),
        reply_markup=InlineKeyboardMarkup(new_keyboard)
    )
    
    if winner or is_draw:
        del ttt_games[game_id]
    
    await callback.answer()

@app.on_message(filters.command("afight"))
async def alone_fight(client:Client, message: Message):
    await afight_system.start_afight(client, message)

@app.on_message(filters.command("diamond"))
async def diamond_hunt(client:Client, message: Message):
    await diamond_system.start_diamond_hunt(client, message)

# Update the callback handler to include all diamond actions
@app.on_callback_query(filters.regex("^diamond_"))
async def handle_diamond_click(client, callback):
    parts = callback.data.split("_")
    
    if len(parts) < 2:
        await callback.answer("Invalid callback!", show_alert=True)
        return
    
    if parts[1] == "cancel" and len(parts) == 3:
        # Handle cancel
        game_id = parts[2]
        await diamond_system.handle_cancel(client, callback, game_id)
    elif parts[1] == "play" and parts[2] == "again":
        # Handle play again - delete current message and start new game
        await callback.message.delete()
        await diamond_system.start_diamond_hunt(client, callback.message)
    elif len(parts) == 3:
        # Handle button click - format: diamond_gameId_buttonNumber
        game_id = parts[1]
        button_num = int(parts[2])
        await diamond_system.handle_diamond_click(client, callback, game_id, button_num)
    elif parts[1] == "found":
        # Diamond already found, do nothing
        await callback.answer("You already found the diamond in this game!", show_alert=True)
    else:
        await callback.answer("Invalid callback!", show_alert=True)

# Add handler for my_missions button
@app.on_callback_query(filters.regex("^my_missions$"))
async def handle_my_missions(client, callback):
    await callback.message.delete()
    await show_missions(client, callback.message)

@app.on_message(filters.command("power"))
async def power_boost(client:Client, message: Message):
    user = message.from_user
    missions = await init_user_missions(user.id)
    afight_mission = missions["afight"]
    
    if afight_mission["completed"]:
        await message.reply(bold("🎉 ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ ᴀʟᴏɴᴇ ғɪɢʜᴛ ᴍɪssɪᴏɴ!\n\nᴜsᴇ /rmission ᴛᴏ ʀᴇsᴇᴛ ʏᴏᴜʀ ᴍɪssɪᴏɴs."))
        return
    
    boosts_left = afight_mission["max_power_boosts"] - afight_mission["power_boosts_used"]
    
    if boosts_left <= 0:
        await message.reply(bold("❌ ʏᴏᴜ'ᴠᴇ ᴜsᴇᴅ ᴀʟʟ ʏᴏᴜʀ ᴘᴏᴡᴇʀ ʙᴏᴏsᴛs!\n\nᴜsᴇ /rmission ᴛᴏ ʀᴇsᴇᴛ ʏᴏᴜʀ ᴍɪssɪᴏɴs."))
        return
    
    # Apply power boost
    power_increase = 20
    afight_mission["power_level"] += power_increase
    afight_mission["power_boosts_used"] += 1
    boosts_left -= 1
    
    await save_user_missions(user.id, missions)
    
    result_text = f"⚡ **ᴘᴏᴡᴇʀ ʙᴏᴏsᴛ ᴀᴘᴘʟɪᴇᴅ!**\n\n"
    result_text += f"💪 ʏᴏᴜʀ ᴘᴏᴡᴇʀ ɪɴᴄʀᴇᴀsᴇᴅ ʙʏ {power_increase}\n"
    result_text += f"🔥 ᴄᴜʀʀᴇɴᴛ ᴘᴏᴡᴇʀ: {afight_mission['power_level']}\n"
    result_text += f"🎯 ʙᴏᴏsᴛs ʟᴇғᴛ: {boosts_left}\n\n"
    result_text += f"ᴜsᴇ /afight ᴛᴏ ᴛᴇsᴛ ʏᴏᴜʀ ɴᴇᴡ ᴘᴏᴡᴇʀ!"
    
    await message.reply(bold(result_text))

@app.on_message(filters.command("rmission"))
async def reset_missions_user(client:Client, message: Message):
    user_id = message.from_user.id
    user_data = await user_collection.find_one({"user_id": user_id})
    
    if not user_data or "missions" not in user_data:
        await message.reply(bold("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴʏ ᴍɪssɪᴏɴs ᴛᴏ ʀᴇsᴇᴛ!"))
        return
    
    # Check when the user last reset their missions
    last_reset = user_data.get("last_reset")
    if last_reset:
        # Calculate if a week has passed since the last reset
        last_reset_date = last_reset if isinstance(last_reset, datetime) else datetime.fromisoformat(last_reset)
        next_reset_date = last_reset_date + timedelta(days=7)
        
        if datetime.now() < next_reset_date:
            # User can't reset yet
            time_remaining = next_reset_date - datetime.now()
            days_remaining = time_remaining.days
            hours_remaining = time_remaining.seconds // 3600
            
            await message.reply(
                bold(f"⏰ ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ʀᴇsᴇᴛ ʏᴏᴜʀ ᴍɪssɪᴏɴs ᴏɴᴄᴇ ᴘᴇʀ ᴡᴇᴇᴋ!\n\n"
                     f"🔄 ɴᴇxᴛ ʀᴇsᴇᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ: {days_remaining} ᴅᴀʏs ᴀɴᴅ {hours_remaining} ʜᴏᴜʀs\n\n"
                     f"📅 ʏᴏᴜ ᴄᴀɴ ʀᴇsᴇᴛ ᴀɢᴀɪɴ ᴏɴ: {next_reset_date.strftime('%Y-%m-%d %H:%M')}")
            )
            return
    
    # Create fresh missions
    missions = {key: value.copy() for key, value in MISSION_TEMPLATE.items()}
    missions["start"]["completed"] = True
    missions["start"]["completed_at"] = datetime.now()
    
    # Update user data with reset missions and timestamp
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "missions": missions, 
            "last_reset": datetime.now(),
            "updated_at": datetime.now(),
            "missions_claimed": False  # Reset the claim status
        }}
    )
    
    await message.reply(
        bold("🔄 ʏᴏᴜʀ ᴍɪssɪᴏɴs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇsᴇᴛ!\n\n"
             "📊 ᴜsᴇ /mymission ᴛᴏ ᴠɪᴇᴡ ʏᴏᴜʀ ɴᴇᴡ ᴍɪssɪᴏɴs.\n\n"
             "⏰ ʏᴏᴜ ᴄᴀɴ ʀᴇsᴇᴛ ᴀɢᴀɪɴ ɪɴ 7 ᴅᴀʏs.")
    )

@app.on_callback_query(filters.regex("^claim_rewards$"))
async def claim_rewards_callback(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    
    # Get user data from user_collection
    user_data = await user_collection.find_one({"user_id": user_id})
    
    if not user_data:
        await callback.answer("Start missions first with /startmission", show_alert=True)
        return
    
    missions = user_data.get("missions", {})
    
    # Check if all missions are completed
    if not all(m.get("completed", False) for m in missions.values()):
        await callback.answer("Complete all missions first!", show_alert=True)
        return
    
    # Check if already claimed
    if user_data.get("missions_claimed", False):
        await callback.answer("You already claimed your rewards!", show_alert=True)
        return
    
    # Award characters (add to user_collection)
    rewards = [
        {"rarity": "⚜️ Animated", "count": 2},
        {"rarity": "🟡 Legendary", "count": 3}, 
        {"rarity": "🔮 Limited Edition", "count": 2},
        {"rarity": "🫧 Premium", "count": 1}
    ]
    
    added_chars = []
    for reward in rewards:
        chars = await collection.aggregate([
            {"$match": {"rarity": reward["rarity"]}},
            {"$sample": {"size": reward["count"]}}
        ]).to_list(length=reward["count"])
        
        for char in chars:
            await ac(user_id, char["id"])  # Add to user_collection
            added_chars.append(f"• {char['name']} ({char['rarity']})")
    
    # Update user_collection to mark rewards as claimed
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "missions_claimed": True,
            "last_reward_claim": datetime.now()
        }}
    )
    
    # Edit message with rewards
    await callback.message.edit_media(
        InputMediaPhoto(
            "https://files.catbox.moe/akubnl.jpg",
            caption=bold(
                f"🎁 CONGRATULATIONS {user_name}!\n\n"
                "✨ You've completed all missions and received:\n\n" +
                "\n".join(added_chars) +
                f"\n\nCheck your amazing /collection\n"
                f"Reset missions with /rmission to start again!"
            )
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 View Collection", callback_data="view_collection")]
        ])
    )
    await callback.answer("🎉 Rewards claimed successfully!", show_alert=True)

# ========================
# OWNER COMMANDS
# ========================

@app.on_message(filters.command("cmission") & filters.user(OWNER_ID))
async def complete_missions(client:Client, message: Message):
    if not message.reply_to_message:
        await message.reply(bold("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ!"))
        return
        
    target_user = message.reply_to_message.from_user
    missions = await init_user_missions(target_user.id)
    
    # Complete all missions
    for mission_key in missions:
        missions[mission_key]["completed"] = True
        missions[mission_key]["completed_at"] = datetime.now()
    
    await save_user_missions(target_user.id, missions)
    
    await message.reply(bold(f"✅ ᴀʟʟ ᴍɪssɪᴏɴs ᴄᴏᴍᴘʟᴇᴛᴇᴅ ғᴏʀ {target_user.first_name}!"))

@app.on_message(filters.command("delmission") & filters.user(OWNER_ID))
async def delete_user_missions(client:Client, message: Message):
    if not message.reply_to_message:
        await message.reply("ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛʜᴇɪʀ ᴍɪssɪᴏɴs")
        return
        
    target_user = message.reply_to_message.from_user
    
    await user_collection.update_one(
        {"user_id": target_user.id},
        {"$unset": {"missions": "", "missions_claimed": "", "last_reset": ""}}
    )
    
    await message.reply(bold(f"🗑️ ᴍɪssɪᴏɴs ᴅᴇʟᴇᴛᴇᴅ ғᴏʀ {target_user.first_name}!"))

# ========================
# NEW ALLMISSION COMMAND FOR OWNER
# ========================

@app.on_message(filters.command("allmission") & filters.user(OWNER_ID))
async def reset_all_missions(client:Client, message: Message):
    # Get all users from user_collection
    all_users = user_collection.find({})
    
    reset_count = 0
    async for user in all_users:
        user_id = user["user_id"]
        
        # Create fresh missions for each user
        missions = {key: value.copy() for key, value in MISSION_TEMPLATE.items()}
        missions["start"]["completed"] = True
        missions["start"]["completed_at"] = datetime.now()
        
        # Update user data with reset missions
        await user_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "missions": missions,
                "missions_claimed": False,
                "last_reset": datetime.now(),
                "updated_at": datetime.now()
            }}
        )
        reset_count += 1
    
    await message.reply(bold(f"🔄 ᴀʟʟ ᴍɪssɪᴏɴs ʀᴇsᴇᴛ ғᴏʀ {reset_count} ᴜsᴇʀs!"))

# ========================
# IMPROVED BIO CHECK FUNCTION
# ========================

async def check_bio_status(user_id, client):
    try:
        user = await client.get_chat(user_id)
        if hasattr(user, 'bio'):
            bio_text = user.bio or ""
            required_bio = SUPPORT_GROUP_TASKS["required_bio"].lower().replace("@", "")
            return (f"@{required_bio}" in bio_text) or (required_bio in bio_text.lower())
        return False
    except Exception as e:
        print(f"ᴇʀʀᴏʀ ᴄʜᴇᴄᴋɪɴɢ ʙɪᴏ: {e}")
        return False

# ========================
# UPDATED MTASK COMMAND
# ========================

@app.on_message(filters.command("mtask"))
async def show_support_tasks(client:Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    try:
        missions = await init_user_missions(user_id)
        mtask_mission = missions["mtask"]
        
        if mtask_mission["completed"]:
            await message.reply(bold(f"🎉 {user_name}, ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ sᴜᴘᴘᴏʀᴛ ᴛᴀsᴋ!\n\nᴜsᴇ /rmission ᴛᴏ ʀᴇsᴇᴛ ʏᴏᴜʀ ᴍɪssɪᴏɴs."))
            return
        
        # Check bio status
        bio_updated = await check_bio_status(user_id, client)
        
        if bio_updated:
            mtask_mission["completed"] = True
            mtask_mission["completed_at"] = datetime.now()
            mtask_mission["bio_updated"] = True
            await save_user_missions(user_id, missions)
            
            await message.reply(bold(f"<blockquote>🎊 ᴛʜᴀɴᴋ ʏᴏᴜ {user_name} ғᴏʀ sᴜᴘᴘᴏʀᴛɪɴɢ ᴜs!</blockquote>\n\nʏᴏᴜ'ᴠᴇ sᴜᴄᴄᴇssғᴜʟʟʏ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛʜᴇ sᴜᴘᴘᴏʀᴛ ᴛᴀsᴋ ᴍɪssɪᴏɴ!"))
        else:
            task_text = f"📌 **sᴜᴘᴘᴏʀᴛ ᴛᴀsᴋ - {user_name}**\n\n"
            task_text += f"ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴛʜɪs ᴍɪssɪᴏɴ, ᴀᴅᴅ @{BOT_USERNAME} ᴛᴏ ʏᴏᴜʀ ʙɪᴏ!\n\n"
            task_text += "**sᴛᴇᴘs:**\n"
            task_text += "1. ɢᴏ ᴛᴏ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ sᴇᴛᴛɪɴɢs\n"
            task_text += "2. ᴇᴅɪᴛ ʏᴏᴜʀ ᴘʀᴏғɪʟᴇ\n"
            task_text += "3. ᴀᴅᴅ @CaptureCharacterBot ᴛᴏ ʏᴏᴜʀ ʙɪᴏ\n"
            task_text += "4. ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴀɴᴅ ᴜsᴇ /mtask ᴀɢᴀɪɴ\n\n"
            task_text += "ᴛʜᴀɴᴋ ʏᴏᴜ ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ! ❤️"
            
            await message.reply(bold(task_text))
    except Exception as e:
        await message.reply(bold(f"❌ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {str(e)}"))

# ========================
# INITIALIZE GAME SYSTEMS
# ========================

battle_system = BattleSystem()
afight_system = AFightSystem()
diamond_system = DiamondHuntSystem()
ttt_games = {}
