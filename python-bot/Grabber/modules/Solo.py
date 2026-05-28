from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from . import Grabberu as app, user_collection
from datetime import datetime, timedelta
import random
import time
import asyncio
import json
import os

# RPG Game Classes
class Player:
    def __init__(self, user_data):
        self.id = user_data.get('_id')
        self.name = user_data.get('name', "Hunter")
        self.level = user_data.get('level', 1)
        self.exp = user_data.get('exp', 0)
        self.prestige_level = user_data.get('prestige_level', 0)  # Moved above
        self.max_exp = self.calculate_max_exp()  # Depends on prestige_level
        self.hp = user_data.get('hp', 100)
        self.max_hp = user_data.get('max_hp', 100)
        self.mp = user_data.get('mp', 50)
        self.max_mp = user_data.get('max_mp', 50)
        self.strength = user_data.get('strength', 10)
        self.agility = user_data.get('agility', 10)
        self.intelligence = user_data.get('intelligence', 10)
        self.stamina = user_data.get('stamina', 10)
        self.gold = user_data.get('gold', 0)
        self.crystals = user_data.get('crystals', 0)
        self.inventory = user_data.get('inventory', [])
        self.equipped = user_data.get('equipped', {})
        self.dungeons_completed = user_data.get('dungeons_completed', 0)
        self.bosses_defeated = user_data.get('bosses_defeated', 0)
        self.last_daily = user_data.get('last_daily', None)
        self.last_weekly = user_data.get('last_weekly', None)
        self.title = user_data.get('title', "E-Rank Hunter")
        self.skills = user_data.get('skills', [])
        self.rank = user_data.get('rank', "E")
        self.shadow_army = user_data.get('shadow_army', [])
        self.gates_cleared = user_data.get('gates_cleared', 0)
        self.daily_quests_completed = user_data.get('daily_quests_completed', 0)
        self.last_boss_attempt = user_data.get('last_boss_attempt', None)

    def calculate_max_exp(self):
        return 100 * (self.level ** 2) * (1 + self.prestige_level * 0.2)
    
    def add_exp(self, amount):
        bonus_exp = amount * (1 + self.prestige_level * 0.1)
        self.exp += int(bonus_exp)
        while self.exp >= self.max_exp:
            self.exp -= self.max_exp
            self.level_up()
    
    def level_up(self):
        self.level += 1
        self.max_hp += 20 + (self.prestige_level * 5)
        self.hp = self.max_hp
        self.max_mp += 10 + (self.prestige_level * 3)
        self.mp = self.max_mp
        self.strength += 2 + (self.prestige_level // 2)
        self.agility += 2 + (self.prestige_level // 2)
        self.intelligence += 2 + (self.prestige_level // 2)
        self.stamina += 2 + (self.prestige_level // 2)
        self.max_exp = self.calculate_max_exp()
        self.update_rank()
        return True
    
    def update_rank(self):
        ranks = {
            1: "E", 10: "D", 20: "C", 
            30: "B", 40: "A", 50: "S", 
            60: "SS", 70: "SSS", 80: "Monarch", 
            90: "Ruler", 100: "Shadow Monarch",
            120: "Monarch of Shadows", 
            150: "Sovereign of Darkness"
        }
        for lvl, rank in sorted(ranks.items(), reverse=True):
            if self.level >= lvl:
                self.rank = rank
                self.title = f"{rank}-Rank Hunter"
                break
    
    def prestige(self):
        if self.level < 100:
            return False
        
        self.prestige_level += 1
        self.level = 1
        self.exp = 0
        self.max_exp = self.calculate_max_exp()
        self.hp = self.max_hp = 100 + (self.prestige_level * 20)
        self.mp = self.max_mp = 50 + (self.prestige_level * 10)
        self.strength = 10 + (self.prestige_level * 2)
        self.agility = 10 + (self.prestige_level * 2)
        self.intelligence = 10 + (self.prestige_level * 2)
        self.stamina = 10 + (self.prestige_level * 2)
        self.rank = "E"
        self.title = f"E-Rank Hunter (Prestige {self.prestige_level})"
        
        # Keep some progress
        self.crystals += self.prestige_level * 5
        self.gold = int(self.gold * 0.1)  # Keep 10% of gold
        
        return True
    
    def to_dict(self):
        return {
            '_id': self.id,
            'name': self.name,
            'level': self.level,
            'exp': self.exp,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'mp': self.mp,
            'max_mp': self.max_mp,
            'strength': self.strength,
            'agility': self.agility,
            'intelligence': self.intelligence,
            'stamina': self.stamina,
            'gold': self.gold,
            'crystals': self.crystals,
            'inventory': self.inventory,
            'equipped': self.equipped,
            'dungeons_completed': self.dungeons_completed,
            'bosses_defeated': self.bosses_defeated,
            'last_daily': self.last_daily,
            'last_weekly': self.last_weekly,
            'title': self.title,
            'skills': self.skills,
            'rank': self.rank,
            'shadow_army': self.shadow_army,
            'gates_cleared': self.gates_cleared,
            'daily_quests_completed': self.daily_quests_completed,
            'prestige_level': self.prestige_level,
            'last_boss_attempt': self.last_boss_attempt
        }

# Game Items, Dungeons, and Bosses
ITEMS = {
    "health_potion": {
        "name": "ʜᴇᴀʟᴛʜ ᴘᴏᴛɪᴏɴ",
        "description": "ʀᴇsᴛᴏʀᴇs 50 ʜᴘ",
        "price": 50,
        "type": "consumable",
        "emoji": "❤️"
    },
    "mana_potion": {
        "name": "ᴍᴀɴᴀ ᴘᴏᴛɪᴏɴ",
        "description": "ʀᴇsᴛᴏʀᴇs 30 ᴍᴘ",
        "price": 50,
        "type": "consumable",
        "emoji": "🔵"
    },
    "elixir": {
        "name": "ᴇʟɪxɪʀ ᴏғ ʟɪғᴇ",
        "description": "ʀᴇsᴛᴏʀᴇs ғᴜʟʟ ʜᴘ ᴀɴᴅ ᴍᴘ",
        "price": 200,
        "type": "consumable",
        "emoji": "✨"
    },
    "dagger": {
        "name": "ʙᴀsɪᴄ ᴅᴀɢɢᴇʀ",
        "description": "+5 sᴛʀᴇɴɢᴛʜ",
        "price": 100,
        "type": "weapon",
        "stats": {"strength": 5},
        "emoji": "🗡️"
    },
    "shadow_armor": {
        "name": "sʜᴀᴅᴏᴡ ᴀʀᴍᴏʀ",
        "description": "+10 ᴀɢɪʟɪᴛʏ, +5 sᴛᴀᴍɪɴᴀ",
        "price": 300,
        "type": "armor",
        "stats": {"agility": 10, "stamina": 5},
        "emoji": "🛡️"
    },
    "monarch_ring": {
        "name": "ʀɪɴɢ ᴏғ ᴛʜᴇ ᴍᴏɴᴀʀᴄʜ",
        "description": "+15 ᴀʟʟ sᴛᴀᴛs",
        "price": 1000,
        "type": "accessory",
        "stats": {"strength": 15, "agility": 15, "intelligence": 15, "stamina": 15},
        "emoji": "💍",
        "crystal_price": 10
    },
    "gate_key": {
        "name": "ɢᴀᴛᴇ ᴋᴇʏ",
        "description": "ᴀʟʟᴏᴡs ᴇɴᴛʀʏ ᴛᴏ sᴘᴇᴄɪᴀʟ ɢᴀᴛᴇ",
        "price": 500,
        "type": "special",
        "emoji": "🔑"
    },
    "shadow_extract": {
        "name": "sʜᴀᴅᴏᴡ ᴇxᴛʀᴀᴄᴛ",
        "description": "ɪɴsᴛᴀɴᴛʟʏ sᴜᴍᴍᴏɴ 3 sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs",
        "price": 300,
        "type": "consumable",
        "emoji": "👥",
        "crystal_price": 5
    }
}

DUNGEONS = {
    "easy": {
        "name": "ᴇ-ʀᴀɴᴋ ᴅᴜɴɢᴇᴏɴ",
        "min_level": 1,
        "exp_reward": 50,
        "gold_reward": (20, 50),
        "crystal_chance": 0.01,
        "difficulty": "ᴇᴀsʏ",
        "emoji": "🟢"
    },
    "medium": {
        "name": "ᴄ-ʀᴀɴᴋ ᴅᴜɴɢᴇᴏɴ",
        "min_level": 20,
        "exp_reward": 150,
        "gold_reward": (50, 100),
        "crystal_chance": 0.05,
        "difficulty": "ᴍᴇᴅɪᴜᴍ",
        "emoji": "🟡"
    },
    "hard": {
        "name": "ᴀ-ʀᴀɴᴋ ᴅᴜɴɢᴇᴏɴ",
        "min_level": 40,
        "exp_reward": 300,
        "gold_reward": (100, 200),
        "crystal_chance": 0.1,
        "difficulty": "ʜᴀʀᴅ",
        "emoji": "🔴"
    },
    "double_dungeon": {
        "name": "ᴅᴏᴜʙʟᴇ ᴅᴜɴɢᴇᴏɴ",
        "min_level": 60,
        "exp_reward": 600,
        "gold_reward": (200, 400),
        "crystal_chance": 0.2,
        "difficulty": "ᴇxᴛʀᴇᴍᴇ",
        "emoji": "🟣"
    },
    "gate": {
        "name": "ʀᴀɪᴅ ɢᴀᴛᴇ",
        "min_level": 80,
        "exp_reward": 1000,
        "gold_reward": (500, 800),
        "crystal_chance": 0.5,
        "difficulty": "ʙᴏss",
        "emoji": "🚪",
        "requires_key": True
    }
}

BOSSES = {
    "ant_king": {
        "name": "ᴋɪɴɢ ᴏғ ᴀɴᴛs",
        "min_level": 50,
        "hp": 2000,
        "attack": 100,
        "defense": 50,
        "exp_reward": 2000,
        "gold_reward": (1000, 1500),
        "crystal_reward": (5, 10),
        "drop_chance": 0.3,
        "drop_item": "monarch_ring",
        "emoji": "🐜👑"
    },
    "igris": {
        "name": "ɪɢʀɪs ᴛʜᴇ ʟᴏʏᴀʟ",
        "min_level": 70,
        "hp": 5000,
        "attack": 200,
        "defense": 100,
        "exp_reward": 5000,
        "gold_reward": (2000, 3000),
        "crystal_reward": (10, 20),
        "drop_chance": 0.5,
        "drop_item": "shadow_armor",
        "emoji": "🗡️🛡️"
    },
    "sovereign": {
        "name": "sᴏᴠᴇʀᴇɪɢɴ ᴏғ ᴅᴇsᴛʀᴜᴄᴛɪᴏɴ",
        "min_level": 100,
        "hp": 10000,
        "attack": 300,
        "defense": 200,
        "exp_reward": 10000,
        "gold_reward": (5000, 8000),
        "crystal_reward": (20, 50),
        "drop_chance": 1.0,
        "drop_item": "monarch_ring",
        "emoji": "👑💀"
    }
}

DAILY_QUESTS = {
    "dungeon_runner": {
        "name": "ᴅᴜɴɢᴇᴏɴ ʀᴜɴɴᴇʀ",
        "description": "ᴄᴏᴍᴘʟᴇᴛᴇ 3 ᴅᴜɴɢᴇᴏɴs",
        "reward": {"gold": 200, "exp": 300},
        "goal": 3
    },
    "shadow_recruiter": {
        "name": "sʜᴀᴅᴏᴡ ʀᴇᴄʀᴜɪᴛᴇʀ",
        "description": "sᴜᴍᴍᴏɴ 5 sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs",
        "reward": {"gold": 300, "crystals": 2},
        "goal": 5
    },
    "boss_slayer": {
        "name": "ʙᴏss sʟᴀʏᴇʀ",
        "description": "ᴅᴇғᴇᴀᴛ 1 ʙᴏss",
        "reward": {"gold": 500, "exp": 1000, "crystals": 5},
        "goal": 1
    }
}

# GIF Animations (replace with actual GIF URLs)
GIFS = {
    "level_up": "https://files.catbox.moe/30vmnh.mp4",
    "battle": "https://files.catbox.moe/mvhpyj.mp4",
    "dungeon_enter": "https://files.catbox.moe/v6sz8d.mp4",
    "dungeon_complete": "https://files.catbox.moe/6l44ek.mp4",
    "daily_reward": "https://files.catbox.moe/yo9l5m.mp4",
    "weekly_reward": "https://files.catbox.moe/yo9l5m.mp4",
    "shop": "https://files.catbox.moe/f2fmiv.mp4",
    "inventory": "https://files.catbox.moe/p3sq16.mp4",
    "shadow_summon": "https://files.catbox.moe/kqz410.mp4",
    "boss_battle": "https://files.catbox.moe/yvj4bx.mp4",
    "boss_victory": "https://files.catbox.moe/5gy0ei.mp4",
    "prestige": "https://files.catbox.moe/8cxzxn.mp4",
    "gate_enter": "https://files.catbox.moe/0chv7h.mp4",
    "gate_complete": "https://files.catbox.moe/5tfw24.mp4",
    "quest_complete": "https://files.catbox.moe/0chv7h.mp4"
}

# Helper Functions
async def get_player(user_id):
    user_data = await user_collection.find_one({'_id': user_id})
    if not user_data:
        # Create new player
        user_data = {
            '_id': user_id,
            'name': "Hunter",
            'level': 1,
            'exp': 0,
            'hp': 100,
            'max_hp': 100,
            'mp': 50,
            'max_mp': 50,
            'strength': 10,
            'agility': 10,
            'intelligence': 10,
            'stamina': 10,
            'gold': 0,
            'crystals': 0,
            'inventory': [],
            'equipped': {},
            'dungeons_completed': 0,
            'bosses_defeated': 0,
            'last_daily': None,
            'last_weekly': None,
            'title': "E-Rank Hunter",
            'skills': [],
            'rank': "E",
            'shadow_army': [],
            'gates_cleared': 0,
            'daily_quests_completed': 0,
            'prestige_level': 0,
            'last_boss_attempt': None
        }
        await user_collection.insert_one(user_data)
    return Player(user_data)

async def update_player(player):
    await user_collection.update_one(
        {'_id': player.id},
        {'$set': player.to_dict()}
    )

async def send_animated_message(client, message, text, gif_type="battle", reply_markup=None):
    gif_url = GIFS.get(gif_type, GIFS["battle"])
    await message.reply_animation(
        animation=gif_url,
        caption=f"**{text}**",
        parse_mode=enums.ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Create shop buttons
def create_shop_buttons(page=0):
    items_per_page = 6
    item_keys = list(ITEMS.keys())
    total_pages = (len(item_keys) // items_per_page) + 1
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = item_keys[start_idx:end_idx]
    
    buttons = []
    for i in range(0, len(page_items), 2):
        row = []
        for item_key in page_items[i:i+2]:
            item = ITEMS[item_key]
            price = item.get('crystal_price', item['price'])
            currency = "💎" if 'crystal_price' in item else "💰"
            row.append(
                InlineKeyboardButton(
                    f"{item['emoji']} {item['name']} - {price}{currency}",
                    callback_data=f"buy_{item_key}_{page}"
                )
            )
        buttons.append(row)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"shop_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"shop_page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="shop_back")])
    return InlineKeyboardMarkup(buttons)

# Commands
@app.on_message(filters.command("starthunting"))
async def start_game(client, message: Message):
    player = await get_player(message.from_user.id)
    welcome_msg = f"""
✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ sᴏʟᴏ ʟᴇᴠᴇʟɪɴɢ ʀᴘɢ** ✨

ʏᴏᴜ ᴀʀᴇ ᴀ ʜᴜɴᴛᴇʀ ɪɴ ᴀ ᴡᴏʀʟᴅ ғᴜʟʟ ᴏғ ᴅᴜɴɢᴇᴏɴs ᴀɴᴅ ᴍᴏɴsᴛᴇʀs. 
ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛs:

🏷 **ɴᴀᴍᴇ:** {player.name}
📊 **ʟᴇᴠᴇʟ:** {player.level} (Prestige {player.prestige_level})
⭐ **ʀᴀɴᴋ:** {player.rank}
❤ **ʜᴘ:** {player.hp}/{player.max_hp}
🔵 **ᴍᴘ:** {player.mp}/{player.max_mp}
⚔ **sᴛʀᴇɴɢᴛʜ:** {player.strength}
🏃 **ᴀɢɪʟɪᴛʏ:** {player.agility}
🧠 **ɪɴᴛᴇʟʟɪɢᴇɴᴄᴇ:** {player.intelligence}
🛡 **sᴛᴀᴍɪɴᴀ:** {player.stamina}
💰 **ɢᴏʟᴅ:** {player.gold}
💎 **ᴄʀʏsᴛᴀʟs:** {player.crystals}

ᴜsᴇ /help ᴛᴏ sᴇᴇ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs.
"""
    await send_animated_message(client, message, welcome_msg, "battle")

@app.on_message(filters.command("profile"))
async def show_profile(client, message: Message):
    player = await get_player(message.from_user.id)
    
    # Calculate combat power
    combat_power = (player.strength * 2) + (player.agility * 1.5) + \
                  (player.intelligence * 1.2) + (player.stamina * 1.8) + \
                  (len(player.shadow_army) * 10)
    
    # Calculate next daily/weekly reset
    now = datetime.now()
    next_daily = ""
    next_weekly = ""
    
    if player.last_daily:
        next_daily_time = player.last_daily + timedelta(hours=24)
        if now < next_daily_time:
            remaining = next_daily_time - now
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            next_daily = f"\n⏳ **ɴᴇxᴛ ᴅᴀɪʟʏ:** {hours}ʜ {minutes}ᴍ"
    
    if player.last_weekly:
        next_weekly_time = player.last_weekly + timedelta(days=7)
        if now < next_weekly_time:
            remaining = next_weekly_time - now
            days = remaining.days
            hours = (remaining.seconds // 3600) % 24
            next_weekly = f"\n⏳ **ɴᴇxᴛ ᴡᴇᴇᴋʟʏ:** {days}ᴅ {hours}ʜ"
    
    profile_msg = f"""
🎭 **{player.title.upper()} PROFILE** 🎭

🏷 **ɴᴀᴍᴇ:** {player.name}
📊 **ʟᴇᴠᴇʟ:** {player.level} (Prestige {player.prestige_level})
⭐ **ʀᴀɴᴋ:** {player.rank}
⚔ **ᴄᴏᴍʙᴀᴛ ᴘᴏᴡᴇʀ:** {int(combat_power)}
⏳ **ᴇxᴘ:** {player.exp}/{player.max_exp}
❤ **ʜᴘ:** {player.hp}/{player.max_hp}
🔵 **ᴍᴘ:** {player.mp}/{player.max_mp}

⚔ **sᴛʀᴇɴɢᴛʜ:** {player.strength}
🏃 **ᴀɢɪʟɪᴛʏ:** {player.agility}
🧠 **ɪɴᴛᴇʟʟɪɢᴇɴᴄᴇ:** {player.intelligence}
🛡 **sᴛᴀᴍɪɴᴀ:** {player.stamina}

💰 **ɢᴏʟᴅ:** {player.gold}
💎 **ᴄʀʏsᴛᴀʟs:** {player.crystals}

🏆 **ᴅᴜɴɢᴇᴏɴs ᴄᴏᴍᴘʟᴇᴛᴇᴅ:** {player.dungeons_completed}
👑 **ʙᴏssᴇs ᴅᴇғᴇᴀᴛᴇᴅ:** {player.bosses_defeated}
🚪 **ɢᴀᴛᴇs ᴄʟᴇᴀʀᴇᴅ:** {player.gates_cleared}
👥 **sʜᴀᴅᴏᴡ ᴀʀᴍʏ:** {len(player.shadow_army)} ᴍᴇᴍʙᴇʀs
📝 **ᴅᴀɪʟʏ ǫᴜᴇsᴛs:** {player.daily_quests_completed}/3
{next_daily}{next_weekly}
"""
    await send_animated_message(client, message, profile_msg, "inventory")

@app.on_message(filters.command("dungeon"))
async def enter_dungeon(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if player.hp <= 0:
        await send_animated_message(client, message, "ʏᴏᴜʀ ʜᴘ ɪs ᴛᴏᴏ ʟᴏᴡ! ʀᴇsᴛ ᴏʀ ᴜsᴇ ʜᴇᴀʟɪɴɢ ɪᴛᴇᴍs ғɪʀsᴛ.", "battle")
        return
    
    # Determine available dungeons
    available_dungeons = []
    for key, dungeon in DUNGEONS.items():
        if player.level >= dungeon['min_level']:
            # Check for gate key requirement
            if dungeon.get('requires_key'):
                if "gate_key" not in player.inventory:
                    continue
            available_dungeons.append((key, dungeon))
    
    if not available_dungeons:
        await send_animated_message(client, message, "ɴᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴜɴɢᴇᴏɴs. ʟᴇᴠᴇʟ ᴜᴘ ғɪʀsᴛ!", "battle")
        return
    
    # Create buttons for available dungeons
    buttons = []
    for key, dungeon in available_dungeons:
        emoji = dungeon.get('emoji', '🔵')
        buttons.append(
            [InlineKeyboardButton(
                f"{emoji} {dungeon['name']} ({dungeon['difficulty']})",
                callback_data=f"dungeon_{key}"
            )]
        )
    
    # Add special raid gate button if player has key
    if "gate_key" in player.inventory and player.level >= DUNGEONS["gate"]["min_level"]:
        dungeon = DUNGEONS["gate"]
        buttons.append(
            [InlineKeyboardButton(
                f"🚪 {dungeon['name']} (ʙᴏss)",
                callback_data=f"dungeon_gate"
            )]
        )
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="dungeon_back")])
    
    await message.reply_animation(
        animation=GIFS["dungeon_enter"],
        caption="**sᴇʟᴇᴄᴛ ᴀ ᴅᴜɴɢᴇᴏɴ ᴛᴏ ᴇɴᴛᴇʀ:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^dungeon_"))
async def dungeon_callback(client, callback_query):
    data = callback_query.data
    player = await get_player(callback_query.from_user.id)
    
    if data == "dungeon_back":
        await callback_query.message.delete()
        return
    
    dungeon_key = data.split("_")[1]
    dungeon = DUNGEONS.get(dungeon_key)
    
    if not dungeon or player.level < dungeon['min_level']:
        await callback_query.answer("ᴛʜɪs ᴅᴜɴɢᴇᴏɴ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ!", show_alert=True)
        return
    
    # Check for gate key
    if dungeon.get('requires_key') and "gate_key" not in player.inventory:
        await callback_query.answer("ʏᴏᴜ ɴᴇᴇᴅ ᴀ ɢᴀᴛᴇ ᴋᴇʏ ᴛᴏ ᴇɴᴛᴇʀ ᴛʜɪs ɢᴀᴛᴇ!", show_alert=True)
        return
    
    # Use gate key if required
    if dungeon.get('requires_key'):
        player.inventory.remove("gate_key")
        await update_player(player)
    
    # Simulate dungeon battle
    await callback_query.edit_message_caption("**ᴇɴᴛᴇʀɪɴɢ ᴅᴜɴɢᴇᴏɴ...**")
    await asyncio.sleep(2)
    
    # Battle outcome (success chance depends on dungeon difficulty)
    success_chance = {
        "easy": 0.9,
        "medium": 0.75,
        "hard": 0.6,
        "double_dungeon": 0.5,
        "gate": 0.4
    }.get(dungeon_key, 0.8)
    
    if random.random() < success_chance:
        # Player wins
        gold_reward = random.randint(*dungeon['gold_reward'])
        player.gold += gold_reward
        player.add_exp(dungeon['exp_reward'])
        player.dungeons_completed += 1
        
        # Check for crystal reward
        crystal_reward = 0
        if random.random() < dungeon.get('crystal_chance', 0):
            crystal_reward = random.randint(1, 3)
            player.crystals += crystal_reward
        
        # Random item drop chance
        dropped_item = None
        if random.random() < 0.3:
            item_key = random.choice(list(ITEMS.keys()))
            # Don't drop premium items
            while 'crystal_price' in ITEMS[item_key] and random.random() < 0.7:
                item_key = random.choice(list(ITEMS.keys()))
            dropped_item = ITEMS[item_key]
            player.inventory.append(item_key)
        
        # Update player
        await update_player(player)
        
        # Victory message
        victory_msg = f"""
🎉 **ᴅᴜɴɢᴇᴏɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!** 🎉

ʏᴏᴜ sᴜᴄᴄᴇssғᴜʟʟʏ ᴄʟᴇᴀʀᴇᴅ ᴛʜᴇ {dungeon['name']}!

🏆 **ʀᴇᴡᴀʀᴅs:**
💰 +{gold_reward} ɢᴏʟᴅ
✨ +{dungeon['exp_reward']} xᴘ
"""
        if crystal_reward > 0:
            victory_msg += f"💎 +{crystal_reward} ᴄʀʏsᴛᴀʟs\n"
        
        if dropped_item:
            victory_msg += f"\n🎁 **ʏᴏᴜ ғᴏᴜɴᴅ:** {dropped_item['name']} - {dropped_item['description']}"
        
        # Check for gate completion
        if dungeon_key == "gate":
            player.gates_cleared += 1
            await update_player(player)
            victory_msg += "\n\n**ʏᴏᴜ ʜᴀᴠᴇ ᴄʟᴇᴀʀᴇᴅ ᴀ ʀᴀɪᴅ ɢᴀᴛᴇ!**"
            gif_type = "gate_complete"
        else:
            gif_type = "dungeon_complete"
        
        await callback_query.edit_message_caption(victory_msg)
        await send_animated_message(client, callback_query.message, victory_msg, gif_type)
    else:
        # Player loses
        hp_loss = random.randint(dungeon['min_level'] * 2, dungeon['min_level'] * 5)
        player.hp = max(0, player.hp - hp_loss)
        await update_player(player)
        
        defeat_msg = f"""
💀 **ᴅᴇғᴇᴀᴛ ɪɴ ᴅᴜɴɢᴇᴏɴ!** 💀

ʏᴏᴜ ғᴀɪʟᴇᴅ ᴛᴏ ᴄʟᴇᴀʀ ᴛʜᴇ {dungeon['name']}!

❤ **ʜᴘ ʟᴏsᴛ:** -{hp_loss}
"""
        await callback_query.edit_message_caption(defeat_msg)
        await send_animated_message(client, callback_query.message, defeat_msg, "battle")

@app.on_message(filters.command("sdaily"))
async def daily_reward(client, message: Message):
    player = await get_player(message.from_user.id)
    now = datetime.now()
    
    if player.last_daily and (now - player.last_daily) < timedelta(hours=24):
        next_daily = player.last_daily + timedelta(hours=24)
        remaining = next_daily - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        await send_animated_message(client, message, 
            f"ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ ʏᴏᴜʀ ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅ ᴛᴏᴅᴀʏ!\n\n⏳ ɴᴇxᴛ ʀᴇᴡᴀʀᴅ ɪɴ: {hours}ʜ {minutes}ᴍ", 
            "daily_reward")
        return
    
    # Give daily reward
    reward_gold = random.randint(100, 200) * (1 + player.prestige_level)
    reward_exp = random.randint(50, 100) * (1 + player.prestige_level)
    reward_crystals = 1 if random.random() < 0.3 else 0
    
    player.gold += reward_gold
    player.add_exp(reward_exp)
    player.crystals += reward_crystals
    player.last_daily = now
    await update_player(player)
    
    reward_msg = f"""
🎁 **ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅ ᴄʟᴀɪᴍᴇᴅ!** 🎁

💰 **+{reward_gold} ɢᴏʟᴅ**
✨ **+{reward_exp} xᴘ**
"""
    if reward_crystals > 0:
        reward_msg += f"💎 **+{reward_crystals} ᴄʀʏsᴛᴀʟ**\n"
    
    reward_msg += "\nᴄᴏᴍᴇ ʙᴀᴄᴋ ᴛᴏᴍᴏʀʀᴏᴡ ғᴏʀ ᴍᴏʀᴇ ʀᴇᴡᴀʀᴅs!"
    
    await send_animated_message(client, message, reward_msg, "daily_reward")

@app.on_message(filters.command("sweekly"))
async def weekly_reward(client, message: Message):
    player = await get_player(message.from_user.id)
    now = datetime.now()
    
    if player.last_weekly and (now - player.last_weekly) < timedelta(days=7):
        next_weekly = player.last_weekly + timedelta(days=7)
        remaining = next_weekly - now
        days = remaining.days
        hours = (remaining.seconds // 3600) % 24
        await send_animated_message(client, message, 
            f"ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ ʏᴏᴜʀ ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅ ᴛʜɪs ᴡᴇᴇᴋ!\n\n⏳ ɴᴇxᴛ ʀᴇᴡᴀʀᴅ ɪɴ: {days}ᴅ {hours}ʜ", 
            "weekly_reward")
        return
    
    # Give weekly reward
    reward_gold = random.randint(500, 1000) * (1 + player.prestige_level)
    reward_exp = random.randint(300, 600) * (1 + player.prestige_level)
    reward_crystals = random.randint(3, 5)
    
    player.gold += reward_gold
    player.add_exp(reward_exp)
    player.crystals += reward_crystals
    player.last_weekly = now
    await update_player(player)
    
    reward_msg = f"""
🎁 **ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅ ᴄʟᴀɪᴍᴇᴅ!** 🎁

💰 **+{reward_gold} ɢᴏʟᴅ**
✨ **+{reward_exp} xᴘ**
💎 **+{reward_crystals} ᴄʀʏsᴛᴀʟs**

ᴄᴏᴍᴇ ʙᴀᴄᴋ ɴᴇxᴛ ᴡᴇᴇᴋ ғᴏʀ ᴍᴏʀᴇ ʀᴇᴡᴀʀᴅs!
"""
    await send_animated_message(client, message, reward_msg, "weekly_reward")

# Command to show shop
@app.on_message(filters.command("vipshop"))
async def show_shop(client, message: Message):
    shop_msg = (
        "🛒 **sʜᴀᴅᴏᴡ ᴀʀᴍʏ sʜᴏᴘ** 🛒\n\n"
        "💰 **ɢᴏʟᴅ:** ᴘᴜʀᴄʜᴀsᴇ ɪᴛᴇᴍs ᴡɪᴛʜ ɢᴏʟᴅ ᴇᴀʀɴᴇᴅ ғʀᴏᴍ ᴅᴜɴɢᴇᴏɴs\n"
        "💎 **ᴄʀʏsᴛᴀʟs:** ᴘʀᴇᴍɪᴜᴍ ᴄᴜʀʀᴇɴᴄʏ ғʀᴏᴍ ᴅᴀɪʟʏ/ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅs ᴏʀ ʙᴏssᴇs\n\n"
        "ᴜsᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ʙʀᴏᴡsᴇ ᴀɴᴅ ʙᴜʏ ɪᴛᴇᴍs:"
    )
    await message.reply_text(shop_msg, reply_markup=create_shop_buttons())

# Callback for shop
@app.on_callback_query(filters.regex("^shop_"))
async def shop_callback(client, callback_query: CallbackQuery):
    data = callback_query.data
    player = await get_player(callback_query.from_user.id)

    if data == "shop_back":
        await callback_query.message.delete()
        return

    if data.startswith("shop_page_"):
        page = int(data.split("_")[2])
        await callback_query.edit_message_reply_markup(reply_markup=create_shop_buttons(page))
        return

    if data.startswith("buy_"):
        parts = data.split("_")
        item_key = parts[1]
        page = int(parts[2])
        item = ITEMS.get(item_key)

        if not item:
            await callback_query.answer("ɪᴛᴇᴍ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        if 'crystal_price' in item:
            currency = "crystals"
            price = item['crystal_price']
            balance = player.crystals
        else:
            currency = "gold"
            price = item['price']
            balance = player.gold

        if balance < price:
            await callback_query.answer(f"ɴᴏᴛ ᴇɴᴏᴜɢʜ {currency} ғᴏʀ ᴛʜɪs ɪᴛᴇᴍ!", show_alert=True)
            return

        confirm_buttons = [
            [InlineKeyboardButton(f"ʏᴇs - ʙᴜʏ ғᴏʀ {price}{'💎' if currency == 'crystals' else '💰'}", 
                                  callback_data=f"confirmbuy_{item_key}_{page}")],
            [InlineKeyboardButton("ɴᴏ - ᴄᴀɴᴄᴇʟ", callback_data=f"cancelbuy_{page}")]
        ]

        await callback_query.edit_message_text(
            f"**ᴄᴏɴғɪʀᴍ ᴘᴜʀᴄʜᴀsᴇ:**\n\n{item['emoji']} **{item['name']}**\n{item['description']}\n\n"
            f"ᴘʀɪᴄᴇ: {price}{'💎' if currency == 'crystals' else '💰'}",
            reply_markup=InlineKeyboardMarkup(confirm_buttons)
        )
        return

    if data.startswith("confirmbuy_"):
        parts = data.split("_")
        item_key = parts[1]
        page = int(parts[2])
        item = ITEMS.get(item_key)

        if not item:
            await callback_query.answer("ɪᴛᴇᴍ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        if 'crystal_price' in item:
            player.crystals -= item['crystal_price']
        else:
            player.gold -= item['price']

        player.inventory.append(item_key)
        await update_player(player)

        await callback_query.answer(f"ʏᴏᴜ ʙᴏᴜɢʜᴛ {item['name']}!", show_alert=True)
        await callback_query.edit_message_text(
            "✅ **ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟ!**\n\nʏᴏᴜʀ ɪᴛᴇᴍ ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ.",
            reply_markup=create_shop_buttons(page)
        )
        return

    if data.startswith("cancelbuy_"):
        page = int(data.split("_")[1])
        await callback_query.edit_message_text(
            "🛒 **ʙʀᴏᴡsᴇ ᴛʜᴇ sʜᴏᴘ:**",
            reply_markup=create_shop_buttons(page)
        )
        return

@app.on_message(filters.command("soloinventory"))
async def show_inventory(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if not player.inventory:
        await send_animated_message(client, message, "ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ ɪs ᴇᴍᴘᴛʏ!", "inventory")
        return
    
    # Group items by type
    consumables = []
    weapons = []
    armor = []
    special = []
    
    for item_key in player.inventory:
        item = ITEMS.get(item_key, {"name": item_key, "type": "unknown"})
        if item['type'] == "consumable":
            consumables.append(item)
        elif item['type'] == "weapon":
            weapons.append(item)
        elif item['type'] == "armor":
            armor.append(item)
        else:
            special.append(item)
    
    # Split the inventory into multiple messages if too long
    messages = []
    current_msg = "🎒 **ɪɴᴠᴇɴᴛᴏʀʏ** 🎒\n\n"
    
    if consumables:
        current_msg += "❤️ **ᴄᴏɴsᴜᴍᴀʙʟᴇs:**\n"
        for item in consumables:
            item_text = f"{item['emoji']} {item['name']} - {item['description']}\n🔘 /use_{item['name'].replace(' ', '_').lower()}\n\n"
            if len(current_msg) + len(item_text) > 1000:  # Leave some buffer
                messages.append(current_msg)
                current_msg = item_text
            else:
                current_msg += item_text
    
    if weapons or armor:
        section_text = "⚔️ **ᴇǫᴜɪᴘᴍᴇɴᴛ:**\n"
        if len(current_msg) + len(section_text) > 1000:
            messages.append(current_msg)
            current_msg = section_text
        else:
            current_msg += section_text
            
        for item in weapons + armor:
            item_text = f"{item['emoji']} {item['name']} - {item['description']}\n🔘 /equip_{item['name'].replace(' ', '_').lower()}\n\n"
            if len(current_msg) + len(item_text) > 1000:
                messages.append(current_msg)
                current_msg = item_text
            else:
                current_msg += item_text
    
    if special:
        section_text = "✨ **sᴘᴇᴄɪᴀʟ ɪᴛᴇᴍs:**\n"
        if len(current_msg) + len(section_text) > 1000:
            messages.append(current_msg)
            current_msg = section_text
        else:
            current_msg += section_text
            
        for item in special:
            item_text = f"{item['emoji']} {item['name']} - {item['description']}\n\n"
            if len(current_msg) + len(item_text) > 1000:
                messages.append(current_msg)
                current_msg = item_text
            else:
                current_msg += item_text
    
    if current_msg:
        messages.append(current_msg)
    
    # Send first message with animation, others as text
    if messages:
        await send_animated_message(client, message, messages[0], "inventory")
        for msg in messages[1:]:
            await message.reply(msg)

@app.on_message(filters.command("use_"))
async def use_item(client, message: Message):
    item_key = message.command[0].split("_", 1)[1].lower()
    player = await get_player(message.from_user.id)
    
    # Find the item in inventory (case insensitive)
    inventory_item = None
    for inv_item in player.inventory:
        if inv_item.replace('_', ' ').lower() == item_key.replace('_', ' ').lower():
            inventory_item = inv_item
            break
    
    if not inventory_item:
        await send_animated_message(client, message, "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜɪs ɪᴛᴇᴍ ɪɴ ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ!", "inventory")
        return
    
    item = ITEMS.get(inventory_item)
    if not item:
        await send_animated_message(client, message, "ɪᴛᴇᴍ ɴᴏᴛ ғᴏᴜɴᴅ!", "inventory")
        return
    
    # Apply item effects
    if item['type'] == "consumable":
        if "health" in item_key:
            heal_amount = min(50, player.max_hp - player.hp)
            player.hp += heal_amount
            msg = f"ʏᴏᴜ ᴜsᴇᴅ ᴀ {item['name']} ᴀɴᴅ ʀᴇɢᴀɪɴᴇᴅ {heal_amount} ʜᴘ!"
        elif "mana" in item_key:
            restore_amount = min(30, player.max_mp - player.mp)
            player.mp += restore_amount
            msg = f"ʏᴏᴜ ᴜsᴇᴅ ᴀ {item['name']} ᴀɴᴅ ʀᴇɢᴀɪɴᴇᴅ {restore_amount} ᴍᴘ!"
        elif "elixir" in item_key:
            hp_heal = player.max_hp - player.hp
            mp_restore = player.max_mp - player.mp
            player.hp = player.max_hp
            player.mp = player.max_mp
            msg = f"ʏᴏᴜ ᴜsᴇᴅ ᴀɴ {item['name']} ᴀɴᴅ ʀᴇɢᴀɪɴᴇᴅ {hp_heal} ʜᴘ ᴀɴᴅ {mp_restore} ᴍᴘ!"
        elif "shadow_extract" in item_key:
            shadow_types = ["ɪɢʀɪs", "ʙᴇʀᴜ", "ᴛᴀɴᴋ"]
            for _ in range(3):
                player.shadow_army.append(random.choice(shadow_types))
            msg = "ʏᴏᴜ ᴜsᴇᴅ ᴀ sʜᴀᴅᴏᴡ �xᴛʀᴀᴄᴛ ᴀɴᴅ sᴜᴍᴍᴏɴᴇᴅ 3 ɴᴇᴡ sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs!"
        
        # Remove from inventory
        player.inventory.remove(inventory_item)
        await update_player(player)
        await send_animated_message(client, message, msg, "inventory")
    else:
        await send_animated_message(client, message, "ᴛʜɪs ɪᴛᴇᴍ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜsᴇᴅ ʟɪᴋᴇ ᴛʜᴀᴛ!", "inventory")

@app.on_message(filters.command("equip_"))
async def equip_item(client, message: Message):
    item_key = message.command[0].split("_", 1)[1].lower()
    player = await get_player(message.from_user.id)
    
    # Find the item in inventory (case insensitive)
    inventory_item = None
    for inv_item in player.inventory:
        if inv_item.replace('_', ' ').lower() == item_key.replace('_', ' ').lower():
            inventory_item = inv_item
            break
    
    if not inventory_item:
        await send_animated_message(client, message, "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜɪs ɪᴛᴇᴍ ɪɴ ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ!", "inventory")
        return
    
    item = ITEMS.get(inventory_item)
    if not item:
        await send_animated_message(client, message, "ɪᴛᴇᴍ ɴᴏᴛ ғᴏᴜɴᴅ!", "inventory")
        return
    
    # Equip the item
    if item['type'] == "weapon":
        # Unequip current weapon if any
        if "weapon" in player.equipped:
            old_item = ITEMS.get(player.equipped["weapon"])
            if old_item:
                for stat, value in old_item.get('stats', {}).items():
                    setattr(player, stat, getattr(player, stat) - value)
        
        # Equip new weapon
        player.equipped["weapon"] = inventory_item
        for stat, value in item.get('stats', {}).items():
            setattr(player, stat, getattr(player, stat) + value)
        
        msg = f"ʏᴏᴜ ᴇǫᴜɪᴘᴘᴇᴅ {item['name']}!"
    elif item['type'] == "armor":
        # Unequip current armor if any
        if "armor" in player.equipped:
            old_item = ITEMS.get(player.equipped["armor"])
            if old_item:
                for stat, value in old_item.get('stats', {}).items():
                    setattr(player, stat, getattr(player, stat) - value)
        
        # Equip new armor
        player.equipped["armor"] = inventory_item
        for stat, value in item.get('stats', {}).items():
            setattr(player, stat, getattr(player, stat) + value)
        
        msg = f"ʏᴏᴜ ᴇǫᴜɪᴘᴘᴇᴅ {item['name']}!"
    else:
        await send_animated_message(client, message, "ᴛʜɪs ɪᴛᴇᴍ ᴄᴀɴɴᴏᴛ ʙᴇ ᴇǫᴜɪᴘᴘᴇᴅ!", "inventory")
        return
    
    await update_player(player)
    await send_animated_message(client, message, msg, "inventory")

@app.on_message(filters.command("rest"))
async def rest_command(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if player.hp == player.max_hp and player.mp == player.max_mp:
        await send_animated_message(client, message, "ʏᴏᴜ'ʀᴇ ᴀʟʀᴇᴀᴅʏ ғᴜʟʟʏ ʀᴇsᴛᴇᴅ!", "battle")
        return
    
    # Restore HP/MP over time (simulated with delay)
    await message.reply_animation(
        animation=GIFS["battle"],
        caption="**ʏᴏᴜ sᴛᴀʀᴛ ʀᴇsᴛɪɴɢ...**",
        parse_mode=enums.ParseMode.MARKDOWN
    )
    
    restore_per_second = 10
    seconds = 0
    
    while player.hp < player.max_hp or player.mp < player.max_mp:
        seconds += 1
        player.hp = min(player.max_hp, player.hp + restore_per_second)
        player.mp = min(player.max_mp, player.mp + restore_per_second)
        
        if seconds % 3 == 0:  # Update every 3 seconds
            await message.reply_text(
                f"**ʀᴇsᴛɪɴɢ... ({seconds}s)**\n\n"
                f"❤ ʜᴘ: {player.hp}/{player.max_hp}\n"
                f"🔵 ᴍᴘ: {player.mp}/{player.max_mp}",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        
        await asyncio.sleep(1)
    
    await update_player(player)
    await send_animated_message(client, message, 
        f"ʏᴏᴜ ғᴜʟʟʏ ʀᴇsᴛᴇᴅ ᴀғᴛᴇʀ {seconds} sᴇᴄᴏɴᴅs!\n\n❤ ʜᴘ: {player.hp}/{player.max_hp}\n🔵 ᴍᴘ: {player.mp}/{player.max_mp}", 
        "battle")

@app.on_message(filters.command("shadow"))
async def shadow_command(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if player.level < 30:
        await send_animated_message(client, message, 
            "ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴛ ʟᴇᴀsᴛ ʟᴇᴠᴇʟ 30 ᴛᴏ ᴜɴʟᴏᴄᴋ sʜᴀᴅᴏᴡ ᴀʙɪʟɪᴛɪᴇs!", 
            "shadow_summon")
        return
    
    # Calculate shadow army stats
    shadow_stats = {
        "ɪɢʀɪs": {"count": 0, "hp": 500, "attack": 50},
        "ʙᴇʀᴜ": {"count": 0, "hp": 200, "attack": 150},
        "ᴛᴀɴᴋ": {"count": 0, "hp": 300, "attack": 100}
    }
    
    for soldier in player.shadow_army:
        shadow_stats[soldier]["count"] += 1
    
    total_soldiers = len(player.shadow_army)
    total_hp = sum(stats["hp"] * stats["count"] for stats in shadow_stats.values())
    total_attack = sum(stats["attack"] * stats["count"] for stats in shadow_stats.values())
    
    shadow_msg = f"""
👥 **sʜᴀᴅᴏᴡ ᴀʀᴍʏ** 👥

ʏᴏᴜ ᴄᴜʀʀᴇɴᴛʟʏ ʜᴀᴠᴇ {total_soldiers} sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs.

🪖 **ɪɢʀɪs:** {shadow_stats['ɪɢʀɪs']['count']} (ᴛᴀɴᴋ)
🗡 **ʙᴇʀᴜ:** {shadow_stats['ʙᴇʀᴜ']['count']} (ᴀssᴀssɪɴ)
🏹 **ᴛᴀɴᴋ:** {shadow_stats['ᴛᴀɴᴋ']['count']} (ʀᴀɴɢᴇᴅ)

ᴛᴏᴛᴀʟ ᴀʀᴍʏ sᴛʀᴇɴɢᴛʜ:
❤ **ʜᴘ:** {total_hp}
⚔ **ᴀᴛᴛᴀᴄᴋ:** {total_attack}

ᴄᴏᴍᴍᴀɴᴅs:
🔘 /summon_shadow - sᴜᴍᴍᴏɴ ᴀ ɴᴇᴡ sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀ (100 ᴍᴘ)
🔘 /shadow_attack - ᴀᴛᴛᴀᴄᴋ ᴡɪᴛʜ ʏᴏᴜʀ sʜᴀᴅᴏᴡ ᴀʀᴍʏ
🔘 /merge_shadows - ᴍᴇʀɢᴇ sʜᴀᴅᴏᴡs ғᴏʀ ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴇᴠᴏʟᴠᴇᴅ sᴏʟᴅɪᴇʀ
"""
    await send_animated_message(client, message, shadow_msg, "shadow_summon")

@app.on_message(filters.command("summon_shadow"))
async def summon_shadow(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if player.level < 30:
        await send_animated_message(client, message, 
            "ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴛ ʟᴇᴀsᴛ ʟᴇᴠᴇʟ 30 ᴛᴏ ᴜɴʟᴏᴄᴋ sʜᴀᴅᴏᴡ ᴀʙɪʟɪᴛɪᴇs!", 
            "shadow_summon")
        return
    
    if player.mp < 100:
        await send_animated_message(client, message, 
            "ʏᴏᴜ ɴᴇᴇᴅ ᴀᴛ ʟᴇᴀsᴛ 100 ᴍᴘ ᴛᴏ sᴜᴍᴍᴏɴ ᴀ sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀ!", 
            "shadow_summon")
        return
    
    # Deduct MP and summon shadow
    player.mp -= 100
    shadow_types = ["ɪɢʀɪs", "ʙᴇʀᴜ", "ᴛᴀɴᴋ"]
    shadow_type = random.choice(shadow_types)
    player.shadow_army.append(shadow_type)
    await update_player(player)
    
    await send_animated_message(client, message, 
        f"ʏᴏᴜ sᴜᴍᴍᴏɴᴇᴅ ᴀ ɴᴇᴡ {shadow_type} sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀ!\n\n👥 sʜᴀᴅᴏᴡ ᴀʀᴍʏ: {len(player.shadow_army)} ᴍᴇᴍʙᴇʀs\n🔵 ᴍᴘ: {player.mp}/{player.max_mp}", 
        "shadow_summon")

@app.on_message(filters.command("shadow_attack"))
async def shadow_attack(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if len(player.shadow_army) == 0:
        await send_animated_message(client, message, 
            "ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴʏ sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ᴛᴏ ᴀᴛᴛᴀᴄᴋ ᴡɪᴛʜ!", 
            "shadow_summon")
        return
    
    # Calculate shadow army stats
    shadow_stats = {
        "ɪɢʀɪs": {"count": 0, "hp": 500, "attack": 50},
        "ʙᴇʀᴜ": {"count": 0, "hp": 200, "attack": 150},
        "ᴛᴀɴᴋ": {"count": 0, "hp": 300, "attack": 100}
    }
    
    for soldier in player.shadow_army:
        shadow_stats[soldier]["count"] += 1
    
    total_attack = sum(stats["attack"] * stats["count"] for stats in shadow_stats.values())
    
    # Simulate battle against random enemies
    enemy_types = ["ɢᴏʙʟɪɴs", "ᴏʀᴄs", "sᴋᴇʟᴇᴛᴏɴs", "ᴅᴇᴍᴏɴs"]
    enemy_type = random.choice(enemy_types)
    enemy_hp = random.randint(500, 2000) * (1 + player.prestige_level)
    
    battle_msg = f"""
⚔ **sʜᴀᴅᴏᴡ ᴀʀᴍʏ ᴀᴛᴛᴀᴄᴋ!** ⚔

ʏᴏᴜʀ {len(player.shadow_army)} sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ᴀᴛᴛᴀᴄᴋ ᴀ ɢʀᴏᴜᴘ ᴏғ {enemy_type}!

ᴛᴏᴛᴀʟ ᴀᴛᴛᴀᴄᴋ ᴘᴏᴡᴇʀ: {total_attack}
ᴇɴᴇᴍʏ ʜᴇᴀʟᴛʜ: {enemy_hp}
"""
    await send_animated_message(client, message, battle_msg, "shadow_summon")
    await asyncio.sleep(2)
    
    # Determine outcome
    if total_attack >= enemy_hp:
        # Victory
        gold_reward = random.randint(100, 300) * (1 + player.prestige_level)
        exp_reward = random.randint(50, 150) * (1 + player.prestige_level)
        
        player.gold += gold_reward
        player.add_exp(exp_reward)
        
        # Chance to lose a soldier (10%)
        soldiers_lost = 0
        if random.random() < 0.1 and len(player.shadow_army) > 1:
            soldiers_lost = random.randint(1, min(3, len(player.shadow_army) // 2))
            for _ in range(soldiers_lost):
                player.shadow_army.pop(random.randint(0, len(player.shadow_army)-1))
        
        victory_msg = f"""
🎉 **ᴠɪᴄᴛᴏʀʏ!** 🎉

ʏᴏᴜʀ sʜᴀᴅᴏᴡ ᴀʀᴍʏ ᴅᴇғᴇᴀᴛᴇᴅ ᴛʜᴇ {enemy_type}!

🏆 **ʀᴇᴡᴀʀᴅs:**
💰 +{gold_reward} ɢᴏʟᴅ
✨ +{exp_reward} xᴘ
"""
        if soldiers_lost > 0:
            victory_msg += f"\n💀 **ᴄᴀsᴜᴀʟᴛɪᴇs:** {soldiers_lost} sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ʟᴏsᴛ ɪɴ ʙᴀᴛᴛʟᴇ"
        
        await update_player(player)
        await send_animated_message(client, message, victory_msg, "shadow_summon")
    else:
        # Defeat - lose random soldiers
        soldiers_lost = random.randint(1, min(5, len(player.shadow_army)))
        for _ in range(soldiers_lost):
            player.shadow_army.pop(random.randint(0, len(player.shadow_army)-1))
        
        defeat_msg = f"""
💀 **ᴅᴇғᴇᴀᴛ!** 💀

ʏᴏᴜʀ sʜᴀᴅᴏᴡ ᴀʀᴍʏ ᴡᴀs ᴅᴇғᴇᴀᴛᴇᴅ ʙʏ ᴛʜᴇ {enemy_type}!

💀 **ᴄᴀsᴜᴀʟᴛɪᴇs:** {soldiers_lost} sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ᴡᴇʀᴇ ʟᴏsᴛ
"""
        await update_player(player)
        await send_animated_message(client, message, defeat_msg, "shadow_summon")


@app.on_message(filters.command("merge_shadows"))
async def merge_shadows(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if len(player.shadow_army) < 3:
        await send_animated_message(client, message, 
            "ʏᴏᴜ ɴᴇᴇᴅ ᴀᴛ ʟᴇᴀsᴛ 3 sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ᴛᴏ ᴍᴇʀɢᴇ!", 
            "shadow_summon")
        return
    
    # Determine merge result based on soldier types
    shadow_types = {
        "ɪɢʀɪs": 0,
        "ʙᴇʀᴜ": 0,
        "ᴛᴀɴᴋ": 0
    }
    
    for soldier in player.shadow_army[:3]:  # Only use first 3 soldiers
        shadow_types[soldier] += 1
    
    # Remove 3 soldiers
    player.shadow_army = player.shadow_army[3:]
    
    # Determine merged soldier type
    if shadow_types["ɪɢʀɪs"] >= 2:
        new_soldier = "ɪɢʀɪs ᴇʟɪᴛᴇ"
        stats = {"hp": 800, "attack": 100}
    elif shadow_types["ʙᴇʀᴜ"] >= 2:
        new_soldier = "ʙᴇʀᴜ ᴇʟɪᴛᴇ"
        stats = {"hp": 400, "attack": 300}
    elif shadow_types["ᴛᴀɴᴋ"] >= 2:
        new_soldier = "ᴛᴀɴᴋ ᴇʟɪᴛᴇ"
        stats = {"hp": 600, "attack": 200}
    else:  # Mixed merge
        new_soldier = "ʜʏʙʀɪᴅ sʜᴀᴅᴏᴡ"
        stats = {"hp": 500, "attack": 250}
    
    # Add the new elite soldier
    player.shadow_army.append(new_soldier)
    await update_player(player)
    
    result_msg = f"""
✨ **sʜᴀᴅᴏᴡ ᴍᴇʀɢᴇ sᴜᴄᴄᴇssғᴜʟ!** ✨

ʏᴏᴜ ᴍᴇʀɢᴇᴅ 3 sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ɪɴᴛᴏ ᴀ:

**{new_soldier}**
❤ ʜᴘ: {stats['hp']}
⚔ ᴀᴛᴛᴀᴄᴋ: {stats['attack']}

👥 sʜᴀᴅᴏᴡ ᴀʀᴍʏ: {len(player.shadow_army)} ᴍᴇᴍʙᴇʀs
"""
    await send_animated_message(client, message, result_msg, "shadow_summon")

@app.on_message(filters.command("boss"))
async def boss_command(client, message: Message):
    player = await get_player(message.from_user.id)
    now = datetime.now()
    
    # Check boss cooldown
    if player.last_boss_attempt and (now - player.last_boss_attempt) < timedelta(hours=12):
        next_attempt = player.last_boss_attempt + timedelta(hours=12)
        remaining = next_attempt - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        await send_animated_message(client, message, 
            f"ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ᴄʜᴀʟʟᴇɴɢᴇ ᴀ ʙᴏss ᴇᴠᴇʀʏ 12 ʜᴏᴜʀs!\n\n⏳ ɴᴇxᴛ ᴀᴛᴛᴇᴍᴘᴛ ɪɴ: {hours}ʜ {minutes}ᴍ", 
            "boss_battle")
        return
    
    # Determine available bosses
    available_bosses = []
    for key, boss in BOSSES.items():
        if player.level >= boss['min_level']:
            available_bosses.append((key, boss))
    
    if not available_bosses:
        await send_animated_message(client, message, "ɴᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ʙᴏssᴇs. ʟᴇᴠᴇʟ ᴜᴘ ғɪʀsᴛ!", "boss_battle")
        return
    
    # Create buttons for available bosses
    buttons = []
    for key, boss in available_bosses:
        buttons.append(
            [InlineKeyboardButton(
                f"{boss['emoji']} {boss['name']} (ʟᴠʟ {boss['min_level']}+)",
                callback_data=f"boss_{key}"
            )]
        )
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="boss_back")])
    
    await message.reply_animation(
        animation=GIFS["boss_battle"],
        caption="**sᴇʟᴇᴄᴛ ᴀ ʙᴏss ᴛᴏ ᴄʜᴀʟʟᴇɴɢᴇ:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^boss_"))
async def boss_callback(client, callback_query):
    data = callback_query.data
    player = await get_player(callback_query.from_user.id)
    
    if data == "boss_back":
        await callback_query.message.delete()
        return
    
    boss_key = data.split("_")[1]
    boss = BOSSES.get(boss_key)
    
    if not boss or player.level < boss['min_level']:
        await callback_query.answer("ᴛʜɪs ʙᴏss ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ!", show_alert=True)
        return
    
    # Check player HP
    if player.hp <= 0:
        await callback_query.answer("ʏᴏᴜʀ ʜᴘ ɪs ᴛᴏᴏ ʟᴏᴡ! ʀᴇsᴛ ᴏʀ ᴜsᴇ ʜᴇᴀʟɪɴɢ ɪᴛᴇᴍs ғɪʀsᴛ!", show_alert=True)
        return
    
    # Start boss battle
    player.last_boss_attempt = datetime.now()
    await update_player(player)
    
    await callback_query.edit_message_caption(f"**ᴘʀᴇᴘᴀʀɪɴɢ ᴛᴏ ғɪɢʜᴛ {boss['name']}...**")
    await asyncio.sleep(2)
    
    # Calculate player power
    player_power = (player.strength * 2) + (player.agility * 1.5) + \
                  (player.intelligence * 1.2) + (player.stamina * 1.8) + \
                  (len(player.shadow_army) * 10)
    
    # Calculate boss power
    boss_power = boss['attack'] * 2 + boss['defense'] * 1.5
    
    # Determine outcome (scales with player level)
    success_chance = min(0.8, max(0.1, (player_power / boss_power) * 0.5))
    
    if random.random() < success_chance:
        # Player wins
        gold_reward = random.randint(*boss['gold_reward'])
        crystal_reward = random.randint(*boss['crystal_reward'])
        player.gold += gold_reward
        player.crystals += crystal_reward
        player.add_exp(boss['exp_reward'])
        player.bosses_defeated += 1
        
        # Check for item drop
        dropped_item = None
        if random.random() < boss['drop_chance']:
            item_key = boss['drop_item']
            dropped_item = ITEMS[item_key]
            player.inventory.append(item_key)
        
        # Update player
        await update_player(player)
        
        # Victory message
        victory_msg = f"""
🎉 **ʙᴏss ᴅᴇғᴇᴀᴛᴇᴅ!** 🎉

ʏᴏᴜ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇғᴇᴀᴛᴇᴅ {boss['name']}!

🏆 **ʀᴇᴡᴀʀᴅs:**
💰 +{gold_reward} ɢᴏʟᴅ
💎 +{crystal_reward} ᴄʀʏsᴛᴀʟs
✨ +{boss['exp_reward']} xᴘ
"""
        if dropped_item:
            victory_msg += f"\n🎁 **ʏᴏᴜ ғᴏᴜɴᴅ:** {dropped_item['name']} - {dropped_item['description']}"
        
        await callback_query.edit_message_caption(victory_msg)
        await send_animated_message(client, callback_query.message, victory_msg, "boss_victory")
    else:
        # Player loses
        hp_loss = random.randint(boss['min_level'] * 5, boss['min_level'] * 10)
        player.hp = max(0, player.hp - hp_loss)
        
        # Chance to lose shadow soldiers (30%)
        soldiers_lost = 0
        if random.random() < 0.3 and len(player.shadow_army) > 0:
            soldiers_lost = random.randint(1, min(3, len(player.shadow_army)))
            for _ in range(soldiers_lost):
                player.shadow_army.pop(random.randint(0, len(player.shadow_army)-1))
        
        await update_player(player)
        
        defeat_msg = f"""
💀 **ʙᴏss ᴅᴇғᴇᴀᴛ!** 💀

ʏᴏᴜ ғᴀɪʟᴇᴅ ᴛᴏ ᴅᴇғᴇᴀᴛ {boss['name']}!

❤ **ʜᴘ ʟᴏsᴛ:** -{hp_loss}
"""
        if soldiers_lost > 0:
            defeat_msg += f"💀 **sʜᴀᴅᴏᴡ sᴏʟᴅɪᴇʀs ʟᴏsᴛ:** {soldiers_lost}"
        
        await callback_query.edit_message_caption(defeat_msg)
        await send_animated_message(client, callback_query.message, defeat_msg, "boss_battle")

@app.on_message(filters.command("prestige"))
async def prestige_command(client, message: Message):
    player = await get_player(message.from_user.id)
    
    if player.level < 100:
        await send_animated_message(client, message, 
            f"ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ʟᴇᴠᴇʟ 100 ᴛᴏ ᴘʀᴇsᴛɪɢᴇ!\n\nʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ʟᴇᴠᴇʟ: {player.level}", 
            "prestige")
        return
    
    confirm_buttons = [
        [InlineKeyboardButton("✅ ʏᴇs - ᴘʀᴇsᴛɪɢᴇ ɴᴏᴡ", callback_data="prestige_confirm")],
        [InlineKeyboardButton("❌ ɴᴏ - ᴄᴀɴᴄᴇʟ", callback_data="prestige_cancel")]
    ]
    
    prestige_msg = f"""
✨ **ᴘʀᴇsᴛɪɢᴇ sʏsᴛᴇᴍ** ✨

ᴘʀᴇsᴛɪɢɪɴɢ ᴡɪʟʟ:
- ʀᴇsᴇᴛ ʏᴏᴜʀ ʟᴇᴠᴇʟ ᴛᴏ 1
- ʀᴇᴍᴏᴠᴇ 90% ᴏғ ʏᴏᴜʀ ɢᴏʟᴅ
- ɢɪᴠᴇ ʏᴏᴜ ᴀ ᴘᴇʀᴍᴀɴᴇɴᴛ +10% xᴘ ʙᴏɴᴜs
- ɢɪᴠᴇ ʏᴏᴜ {player.prestige_level * 5 + 5} 💎 ᴄʀʏsᴛᴀʟs

**ᴄᴜʀʀᴇɴᴛ ᴘʀᴇsᴛɪɢᴇ ʟᴇᴠᴇʟ:** {player.prestige_level}
**ɴᴇxᴛ ᴘʀᴇsᴛɪɢᴇ ʀᴇᴡᴀʀᴅ:** {player.prestige_level * 5 + 5} 💎

ᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴘʀᴇsᴛɪɢᴇ?
"""
    await send_animated_message(
        client, 
        message, 
        prestige_msg, 
        "prestige",
        reply_markup=InlineKeyboardMarkup(confirm_buttons)
    )

@app.on_callback_query(filters.regex("^prestige_"))
async def prestige_callback(client, callback_query):
    data = callback_query.data
    player = await get_player(callback_query.from_user.id)
    
    if data == "prestige_cancel":
        await callback_query.message.delete()
        return
    
    if player.level < 100:
        await callback_query.answer("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ʟᴇᴠᴇʟ 100 ᴛᴏ ᴘʀᴇsᴛɪɢᴇ!", show_alert=True)
        return
    
    # Perform prestige
    if player.prestige():
        reward_crystals = player.prestige_level * 5 + 5
        player.crystals += reward_crystals
        await update_player(player)
        
        success_msg = f"""
✨ **ᴘʀᴇsᴛɪɢᴇ sᴜᴄᴄᴇssғᴜʟ!** ✨

ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴀᴛ ᴘʀᴇsᴛɪɢᴇ ʟᴇᴠᴇʟ {player.prestige_level}!

💎 **ʀᴇᴡᴀʀᴅ:** +{reward_crystals} ᴄʀʏsᴛᴀʟs
✨ **xᴘ ʙᴏɴᴜs:** +{player.prestige_level * 10}%

ʏᴏᴜʀ ɴᴇᴡ sᴛᴀᴛs:
📊 **ʟᴇᴠᴇʟ:** {player.level}
💰 **ɢᴏʟᴅ:** {player.gold}
💎 **ᴄʀʏsᴛᴀʟs:** {player.crystals}
"""
        await callback_query.edit_message_caption(success_msg)
        await send_animated_message(client, callback_query.message, success_msg, "prestige")
    else:
        await callback_query.answer("ᴘʀᴇsᴛɪɢᴇ ғᴀɪʟᴇᴅ!", show_alert=True)

@app.on_message(filters.command("quests"))
async def quests_command(client, message: Message):
    player = await get_player(message.from_user.id)
    now = datetime.now()
    
    # Check if daily quests need reset (new day)
    if player.last_daily and now.date() > player.last_daily.date():
        player.daily_quests_completed = 0
        await update_player(player)
    
    quests_msg = "📜 **ᴅᴀɪʟʏ ǫᴜᴇsᴛs** 📜\n\n"
    
    for key, quest in DAILY_QUESTS.items():
        progress = min(player.daily_quests_completed, quest['goal'])
        quests_msg += f"🔹 **{quest['name']}**\n{quest['description']}\n"
        quests_msg += f"ᴘʀᴏɢʀᴇss: {progress}/{quest['goal']}\n"
        
        rewards = []
        if 'gold' in quest['reward']:
            rewards.append(f"{quest['reward']['gold']}💰")
        if 'exp' in quest['reward']:
            rewards.append(f"{quest['reward']['exp']}✨")
        if 'crystals' in quest['reward']:
            rewards.append(f"{quest['reward']['crystals']}💎")
        
        quests_msg += f"ʀᴇᴡᴀʀᴅ: {' '.join(rewards)}\n\n"
    
    quests_msg += f"**ᴄᴏᴍᴘʟᴇᴛᴇᴅ ᴛᴏᴅᴀʏ:** {player.daily_quests_completed}/3\n\n"
    quests_msg += "ǫᴜᴇsᴛs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴛʀᴀᴄᴋ ʏᴏᴜʀ ᴘʀᴏɢʀᴇss ᴀɴᴅ ʀᴇᴡᴀʀᴅ ʏᴏᴜ ᴡʜᴇɴ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!"
    
    await send_animated_message(client, message, quests_msg, "quest_complete")

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_msg = """
🎮 **sᴏʟᴏ ʟᴇᴠᴇʟɪɴɢ ʀᴘɢ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs** 🎮

🔹 /starthunting - sᴛᴀʀᴛ ᴛʜᴇ ɢᴀᴍᴇ
🔹 /profile - ᴠɪᴇᴡ ʏᴏᴜʀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴘʀᴏғɪʟᴇ
🔹 /dungeon - ᴇɴᴛᴇʀ ᴀ ᴅᴜɴɢᴇᴏɴ
🔹 /boss - ᴄʜᴀʟʟᴇɴɢᴇ ᴀ ᴘᴏᴡᴇʀғᴜʟ ʙᴏss
🔹 /sdaily - ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅ
🔹 /sweekly - ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅ
🔹 /vipshop - ᴠɪᴇᴡ ᴛʜᴇ ɪᴛᴇᴍ sʜᴏᴘ (ʙᴜᴛᴛᴏɴs)
🔹 /soloinventory - ᴠɪᴇᴡ ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ
🔹 /rest - ʀᴇsᴛ ᴛᴏ ʀᴇɢᴀɪɴ ʜᴘ ᴀɴᴅ ᴍᴘ
🔹 /shadow - ᴠɪᴇᴡ ʏᴏᴜʀ sʜᴀᴅᴏᴡ ᴀʀᴍʏ
🔹 /quests - ᴠɪᴇᴡ ᴅᴀɪʟʏ ǫᴜᴇsᴛs
🔹 /prestige - ʀᴇsᴇᴛ ʏᴏᴜʀ ᴘʀᴏɢʀᴇss ғᴏʀ ʙᴏɴᴜsᴇs (ʟᴠʟ 100+)

ᴇᴍʙᴀʀᴋ ᴏɴ ʏᴏᴜʀ ᴊᴏᴜʀɴᴇʏ ᴛᴏ ʙᴇᴄᴏᴍᴇ ᴛʜᴇ sʜᴀᴅᴏᴡ ᴍᴏɴᴀʀᴄʜ!
"""
    await send_animated_message(client, message, help_msg, "battle")
