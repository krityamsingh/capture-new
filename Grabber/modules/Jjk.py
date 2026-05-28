import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from . import Grabberu as app, user_collection

# 𝗝𝘂𝗷𝘂𝘁𝘀𝘂 𝗞𝗮𝗶𝘀𝗲𝗻 𝗚𝗮𝗺𝗲 𝗖𝗼𝗻𝘀𝘁𝗮𝗻𝘁𝘀
JJK_CHARACTERS = {
    "ʏᴜᴊɪ ɪᴛᴀᴅᴏʀɪ": {
        "health": 100,
        "cursed_energy": 80,
        "attack": 15,
        "defense": 10,
        "techniques": ["ᴅɪᴠᴇʀɢᴇɴᴛ ғɪsᴛ", "ʙʟᴀᴄᴋ ғʟᴀsʜ"],
        "special": "sᴜᴋᴜɴᴀ's ᴘᴏᴡᴇʀ",
        "image": "yuji_image_id",
        "quote": "I'ᴍ ɢᴏɴɴᴀ ᴋɪʟʟ ʏᴏᴜ ᴀɴᴅ ᴛʜᴇɴ ᴋɪʟʟ ᴄᴜʀsᴇs!"
    },
    "ᴍᴇɢᴜᴍɪ ғᴜsʜɪɢᴜʀᴏ": {
        "health": 90,
        "cursed_energy": 100,
        "attack": 12,
        "defense": 12,
        "techniques": ["ᴛᴇɴ sʜᴀᴅᴏᴡs ᴛᴇᴄʜɴɪϙᴜᴇ", "ᴅᴏᴍᴀɪɴ ᴇxᴘᴀɴsɪᴏɴ"],
        "special": "ᴍᴀʜᴏʀᴀɢᴀ sᴜᴍᴍᴏɴ",
        "image": "megumi_image_id",
        "quote": "I'ᴍ ɴᴏᴛ ᴅʏɪɴɢ ᴡʜᴇɴ I'ᴍ ʟᴏsᴛ. I'ᴍ ᴅʏɪɴɢ ᴡʜᴇɴ I'ᴍ ᴅᴇғᴇᴀᴛᴇᴅ."
    },
    "ɴᴏʙᴀʀᴀ ᴋᴜɢɪsᴀᴋɪ": {
        "health": 85,
        "cursed_energy": 70,
        "attack": 18,
        "defense": 8,
        "techniques": ["sᴛʀᴀᴡ ᴅᴏʟʟ ᴛᴇᴄʜɴɪϙᴜᴇ", "ʀᴇsᴏɴᴀɴᴄᴇ"],
        "special": "ʜᴀɪʀᴘɪɴ ᴀᴛᴛᴀᴄᴋ",
        "image": "nobara_image_id",
        "quote": "I'ᴍ ɴᴏᴛ ɪɴᴛᴇʀᴇsᴛᴇᴅ ɪɴ ᴡᴏᴍᴇɴ ᴡʜᴏ ᴄᴀɴ'ᴛ sᴀʏ ɴᴏ!"
    },
    "sᴀᴛᴏʀᴜ ɢᴏᴊᴏ": {
        "health": 150,
        "cursed_energy": 200,
        "attack": 25,
        "defense": 20,
        "techniques": ["ʟɪᴍɪᴛʟᴇss", "ʜᴏʟʟᴏᴡ ᴘᴜʀᴘʟᴇ"],
        "special": "ᴅᴏᴍᴀɪɴ ᴇxᴘᴀɴsɪᴏɴ: �ᴜɴʟɪᴍɪᴛᴇᴅ ᴠᴏɪᴅ",
        "image": "gojo_image_id",
        "quote": "ᴛʜʀᴏᴜɢʜᴏᴜᴛ ʜᴇᴀᴠᴇɴ ᴀɴᴅ ᴇᴀʀᴛʜ, I ᴀʟᴏɴᴇ ᴀᴍ ᴛʜᴇ ʜᴏɴᴏʀᴇᴅ ᴏɴᴇ."
    }
}

CURSES = {
    "ɢʀᴀᴅᴇ 4": {
        "health": 30, 
        "attack": 5, 
        "defense": 3, 
        "reward": 10,
        "description": "ᴡᴇᴀᴋ ᴄᴜʀsᴇs ᴛʜᴀᴛ ᴇᴠᴇɴ ɴᴏʀᴍᴀʟ ᴘᴇᴏᴘʟᴇ ᴄᴀɴ sᴇᴇ"
    },
    "ɢʀᴀᴅᴇ 3": {
        "health": 50, 
        "attack": 8, 
        "defense": 5, 
        "reward": 25,
        "description": "ʟᴏᴡ-ʟᴇᴠᴇʟ ᴄᴜʀsᴇs ᴛʜᴀᴛ ʀᴇϙᴜɪʀᴇ sᴏʀᴄᴇʀᴇʀ ɪɴᴛᴇʀᴠᴇɴᴛɪᴏɴ"
    },
    "ɢʀᴀᴅᴇ 2": {
        "health": 80, 
        "attack": 12, 
        "defense": 8, 
        "reward": 50,
        "description": "ᴅᴀɴɢᴇʀᴏᴜs ᴄᴜʀsᴇs ᴛʜᴀᴛ ᴄᴀɴ ᴋɪʟʟ ɴᴏʀᴍᴀʟ ᴘᴇᴏᴘʟᴇ"
    },
    "ɢʀᴀᴅᴇ 1": {
        "health": 120, 
        "attack": 18, 
        "defense": 12, 
        "reward": 100,
        "description": "ᴘᴏᴡᴇʀғᴜʟ ᴄᴜʀsᴇs ᴛʜᴀᴛ ʀᴇϙᴜɪʀᴇ ᴍᴜʟᴛɪᴘʟᴇ sᴏʀᴄᴇʀᴇʀs"
    },
    "sᴘᴇᴄɪᴀʟ ɢʀᴀᴅᴇ": {
        "health": 200, 
        "attack": 25, 
        "defense": 15, 
        "reward": 250,
        "description": "ɴɪɢʜᴛᴍᴀʀᴇ ᴇɴᴛɪᴛɪᴇs ᴛʜᴀᴛ ᴄᴀɴ ᴡɪᴘᴇ ᴏᴜᴛ ᴄɪᴛɪᴇs"
    }
}

# 𝗚𝗮𝗺𝗲 𝗦𝘁𝗮𝘁𝗲 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁
user_games = {}

class JujutsuGame:
    def __init__(self, user_id):
        self.user_id = user_id
        self.character = None
        self.current_health = 0
        self.current_cursed_energy = 0
        self.current_mission = None
        self.battle_wins = 0
        self.balance_reward = 0
        self.battle_log = []
        self.domain_expansion = False
    
    async def start_game(self, character_name):
        if character_name not in JJK_CHARACTERS:
            return False
        
        self.character = JJK_CHARACTERS[character_name]
        self.current_health = self.character["health"]
        self.current_cursed_energy = self.character["cursed_energy"]
        self.battle_wins = 0
        self.balance_reward = 0
        self.battle_log = []
        self.domain_expansion = False
        return True
    
    async def start_mission(self, difficulty):
        if difficulty not in CURSES:
            return None
        
        self.current_mission = {
            "curse": difficulty,
            "curse_health": CURSES[difficulty]["health"],
            "reward": CURSES[difficulty]["reward"],
            "description": CURSES[difficulty]["description"]
        }
        return self.current_mission
    
    async def attack(self, technique_index):
        if not self.current_mission or technique_index >= len(self.character["techniques"]):
            return None
        
        # 𝗣𝗹𝗮𝘆𝗲𝗿 𝗮𝘁𝘁𝗮𝗰𝗸
        technique = self.character["techniques"][technique_index]
        attack_power = self.character["attack"] + random.randint(1, 10)
        
        # 𝗖𝗿𝗶𝘁𝗶𝗰𝗮𝗹 𝗵𝗶𝘁 𝗰𝗵𝗮𝗻𝗰𝗲 (𝗕𝗹𝗮𝗰𝗸 𝗙𝗹𝗮𝘀𝗵)
        is_critical = random.random() < 0.05
        if is_critical:
            attack_power *= 2.5
            self.battle_log.append(f"⚡ ʙʟᴀᴄᴋ ғʟᴀsʜ! ᴄʀɪᴛɪᴄᴀʟ ʜɪᴛ ᴡɪᴛʜ {technique}! ⚡")
        
        damage = max(1, attack_power - CURSES[self.current_mission["curse"]]["defense"] // 2)
        self.current_mission["curse_health"] -= damage
        self.current_cursed_energy -= 10
        
        log_entry = f"➤ ᴜsᴇᴅ {technique} ᴅᴇᴀʟɪɴɢ {damage} ᴅᴀᴍᴀɢᴇ!"
        if is_critical:
            log_entry = f"🌟 {log_entry} (ᴄʀɪᴛɪᴄᴀʟ!)"
        self.battle_log.append(log_entry)
        
        # 𝗖𝗵𝗲𝗰𝗸 𝗶𝗳 𝗰𝘂𝗿𝘀𝗲 𝗶𝘀 𝗱𝗲𝗳𝗲𝗮𝘁𝗲𝗱
        if self.current_mission["curse_health"] <= 0:
            reward = self.current_mission["reward"]
            self.balance_reward += reward
            self.battle_wins += 1
            self.battle_log.append(f"\n🎉 ʏᴏᴜ ᴅᴇғᴇᴀᴛᴇᴅ ᴛʜᴇ {self.current_mission['curse']} ᴄᴜʀsᴇ!")
            self.battle_log.append(f"💰 ɢᴀɪɴᴇᴅ {reward} ᴄᴏɪɴs!")
            return {"outcome": "win", "reward": reward}
        
        # 𝗖𝘂𝗿𝘀𝗲 𝗰𝗼𝘂𝗻𝘁𝗲𝗿𝗮𝘁𝘁𝗮𝗰𝗸
        curse_damage = max(1, CURSES[self.current_mission["curse"]]["attack"] - self.character["defense"] // 2)
        self.current_health -= curse_damage
        self.battle_log.append(f"\n☠ ᴛʜᴇ ᴄᴜʀsᴇ ᴀᴛᴛᴀᴄᴋs ʙᴀᴄᴋ ғᴏʀ {curse_damage} ᴅᴀᴍᴀɢᴇ!")
        
        # 𝗖𝗵𝗲𝗰𝗸 𝗶𝗳 𝗽𝗹𝗮𝘆𝗲𝗿 𝗶𝘀 𝗱𝗲𝗳𝗲𝗮𝘁𝗲𝗱
        if self.current_health <= 0:
            self.battle_log.append("\n💀 ʏᴏᴜ ᴡᴇʀᴇ ᴅᴇғᴇᴀᴛᴇᴅ ʙʏ ᴛʜᴇ ᴄᴜʀsᴇ!")
            return {"outcome": "lose"}
        
        return {"outcome": "continue", "player_health": self.current_health, "curse_health": self.current_mission["curse_health"]}
    
    async def use_special(self):
        if self.current_cursed_energy < 50:
            return {"error": "ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴜʀsᴇᴅ ᴇɴᴇʀɢʏ!"}
        
        special_power = self.character["special"]
        damage = self.character["attack"] * 3
        
        # 𝗗𝗼𝗺𝗮𝗶𝗻 𝗘𝘅𝗽𝗮𝗻𝘀𝗶𝗼𝗻 𝗰𝗵𝗮𝗻𝗰𝗲 (𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗰𝗲𝗿𝘁𝗮𝗶𝗻 𝗰𝗵𝗮𝗿𝗮𝗰𝘁𝗲𝗿𝘀)
        if "domain expansion" in special_power.lower() and random.random() < 0.3:
            damage *= 2
            self.domain_expansion = True
            self.battle_log.append(f"🌀 ᴅᴏᴍᴀɪɴ ᴇxᴘᴀɴsɪᴏɴ: {special_power.upper()}! ᴅᴏᴜʙʟᴇ ᴅᴀᴍᴀɢᴇ! 🌀")
        else:
            self.battle_log.append(f"💥 ᴜsᴇᴅ sᴘᴇᴄɪᴀʟ ᴛᴇᴄʜɴɪϙᴜᴇ: {special_power}!")
        
        self.current_mission["curse_health"] -= damage
        self.current_cursed_energy -= 50
        
        if self.domain_expansion:
            self.battle_log.append(f"☄ ᴅᴇᴀʟᴛ {damage} ɪɴsᴛᴀɴᴛ ᴅᴀᴍᴀɢᴇ ɪɴ ᴛʜᴇ ᴅᴏᴍᴀɪɴ!")
            self.domain_expansion = False
        
        if self.current_mission["curse_health"] <= 0:
            reward = self.current_mission["reward"]
            self.balance_reward += reward
            self.battle_wins += 1
            self.battle_log.append(f"\n🎉 ʏᴏᴜ ᴅᴇғᴇᴀᴛᴇᴅ ᴛʜᴇ ᴄᴜʀsᴇ ᴡɪᴛʜ ʏᴏᴜʀ sᴘᴇᴄɪᴀʟ ᴛᴇᴄʜɴɪϙᴜᴇ!")
            self.battle_log.append(f"💰 ɢᴀɪɴᴇᴅ {reward} ᴄᴏɪɴs!")
            return {"outcome": "win", "reward": reward}
        
        return {"outcome": "continue", "player_health": self.current_health, "curse_health": self.current_mission["curse_health"]}
    
    async def heal(self):
        heal_amount = min(30, self.character["health"] - self.current_health)
        self.current_health += heal_amount
        self.current_cursed_energy = min(self.current_cursed_energy + 20, self.character["cursed_energy"])
        self.battle_log.append(f"💚 ʜᴇᴀʟᴇᴅ ғᴏʀ {heal_amount} ʜᴘ ᴀɴᴅ ʀᴇᴄᴏᴠᴇʀᴇᴅ 20 ᴄᴜʀsᴇᴅ ᴇɴᴇʀɢʏ!")
        return {"health": self.current_health, "cursed_energy": self.current_cursed_energy}

async def update_balance(user_id, amount):
    """sᴀғᴇ ʙᴀʟᴀɴᴄᴇ ᴜᴘᴅᴀᴛᴇ ᴛʜᴀᴛ ʜᴀɴᴅʟᴇs ʙᴏᴛʜ sᴛʀɪɴɢ ᴀɴᴅ ɴᴜᴍᴇʀɪᴄ ʙᴀʟᴀɴᴄᴇs"""
    user_data = await user_collection.find_one({'id': user_id})
    
    if not user_data:
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'balance': amount}},
            upsert=True
        )
        return
    
    current_balance = user_data.get('balance', 0)
    
    # ᴄᴏɴᴠᴇʀᴛ sᴛʀɪɴɢ ʙᴀʟᴀɴᴄᴇ ᴛᴏ ɪɴᴛᴇɢᴇʀ ɪғ ɴᴇᴇᴅᴇᴅ
    if isinstance(current_balance, str):
        try:
            current_balance = int(current_balance)
        except ValueError:
            current_balance = 0
    
    new_balance = current_balance + amount
    
    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'balance': new_balance}},
        upsert=True
    )

# 𝗖𝗼𝗺𝗺𝗮𝗻𝗱 𝗛𝗮𝗻𝗱𝗹𝗲𝗿𝘀
@app.on_message(filters.command("jjkstart"))
async def start_jjk_game(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id in user_games:
        await message.reply_text("ʏᴏᴜ'ʀᴇ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴀ ᴊᴜᴊᴜᴛsᴜ ᴋᴀɪsᴇɴ ʙᴀᴛᴛʟᴇ! ᴜsᴇ /jjkattack ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.")
        return
    
    buttons = []
    for character in JJK_CHARACTERS:
        buttons.append([InlineKeyboardButton(character, callback_data=f"jjk_select_{character}")])
    
    await message.reply_text(
        "**ᴊᴜᴊᴜᴛsᴜ ᴋᴀɪsᴇɴ ʀᴘɢ**\n\n"
        "sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴛᴏ ʙᴇɢɪɴ ʏᴏᴜʀ ᴊᴏᴜʀɴᴇʏ ᴀs ᴀ ᴊᴜᴊᴜᴛsᴜ sᴏʀᴄᴇʀᴇʀ:\n"
        "• ʏᴜᴊɪ ɪᴛᴀᴅᴏʀɪ - ʙᴀʟᴀɴᴄᴇᴅ ᴘʜʏsɪᴄᴀʟ ғɪɢʜᴛᴇʀ\n"
        "• ᴍᴇɢᴜᴍɪ ғᴜsʜɪɢᴜʀᴏ - ᴠᴇʀsᴀᴛɪʟᴇ sʜᴀᴅᴏᴡ ᴛᴇᴄʜɴɪϙᴜᴇs\n"
        "• ɴᴏʙᴀʀᴀ ᴋᴜɢɪsᴀᴋɪ - ʜɪɢʜ ᴅᴀᴍᴀɢᴇ ʀᴀɴɢᴇᴅ ᴀᴛᴛᴀᴄᴋs\n"
        "• sᴀᴛᴏʀᴜ ɢᴏᴊᴏ - ᴏᴠᴇʀᴘᴏᴡᴇʀᴇᴅ ʙᴜᴛ ʀᴀʀᴇ (5% ᴄʜᴀɴᴄᴇ)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^jjk_select_"))
async def select_character(client, callback_query):
    user_id = callback_query.from_user.id
    character_name = callback_query.data.split("_")[-1]
    
    # 𝗚𝗼𝗷𝗼 𝗹𝗼𝗰𝗸 𝗺𝗲𝗰𝗵𝗮𝗻𝗶𝗰
    if character_name == "sᴀᴛᴏʀᴜ ɢᴏᴊᴏ" and random.random() > 0.05:
        await callback_query.answer("sᴏʀʀʏ! ɢᴏᴊᴏ-sᴇɴsᴇɪ ɪs ᴛᴏᴏ ᴘᴏᴡᴇʀғᴜʟ ᴛᴏ ʙᴇ sᴇʟᴇᴄᴛᴇᴅ ɴᴏʀᴍᴀʟʟʏ. ᴛʀʏ ᴀɢᴀɪɴ!", show_alert=True)
        return
    
    user_games[user_id] = JujutsuGame(user_id)
    success = await user_games[user_id].start_game(character_name)
    
    if not success:
        await callback_query.answer("ɪɴᴠᴀʟɪᴅ ᴄʜᴀʀᴀᴄᴛᴇʀ sᴇʟᴇᴄᴛɪᴏɴ!", show_alert=True)
        return
    
    char_quote = JJK_CHARACTERS[character_name]["quote"]
    
    await callback_query.edit_message_text(
        f"🎌 ʏᴏᴜ ʜᴀᴠᴇ sᴇʟᴇᴄᴛᴇᴅ {character_name} ᴀs ʏᴏᴜʀ ᴄʜᴀʀᴀᴄᴛᴇʀ!\n\n"
        f"\"{char_quote}\"\n\n"
        f"❤ ʜᴇᴀʟᴛʜ: {user_games[user_id].current_health}\n"
        f"🔋 ᴄᴜʀsᴇᴅ ᴇɴᴇʀɢʏ: {user_games[user_id].current_cursed_energy}\n\n"
        "ᴜsᴇ /jjkmission ᴛᴏ sᴛᴀʀᴛ ᴀ ʙᴀᴛᴛʟᴇ ᴀɢᴀɪɴsᴛ ᴄᴜʀsᴇs!"
    )

@app.on_message(filters.command("jjkmission"))
async def start_mission(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴀ ɢᴀᴍᴇ ғɪʀsᴛ ᴡɪᴛʜ /jjkstart")
        return
    
    buttons = [
        [InlineKeyboardButton("ɢʀᴀᴅᴇ 4 (ᴇᴀsʏ)", callback_data="jjk_mission_ɢʀᴀᴅᴇ 4")],
        [InlineKeyboardButton("ɢʀᴀᴅᴇ 3 (ᴍᴇᴅɪᴜᴍ)", callback_data="jjk_mission_ɢʀᴀᴅᴇ 3")],
        [InlineKeyboardButton("ɢʀᴀᴅᴇ 2 (ʜᴀʀᴅ)", callback_data="jjk_mission_ɢʀᴀᴅᴇ 2")],
        [InlineKeyboardButton("ɢʀᴀᴅᴇ 1 (ᴇxᴘᴇʀᴛ)", callback_data="jjk_mission_ɢʀᴀᴅᴇ 1")],
        [InlineKeyboardButton("sᴘᴇᴄɪᴀʟ ɢʀᴀᴅᴇ (ɪɴsᴀɴᴇ)", callback_data="jjk_mission_sᴘᴇᴄɪᴀʟ ɢʀᴀᴅᴇ")]
    ]
    
    await message.reply_text(
        f"**sᴇʟᴇᴄᴛ ᴍɪssɪᴏɴ ᴅɪғғɪᴄᴜʟᴛʏ**\n\n"
        f"ʜɪɢʜᴇʀ ɢʀᴀᴅᴇs ɢɪᴠᴇ ʙᴇᴛᴛᴇʀ ʀᴇᴡᴀʀᴅs ʙᴜᴛ ᴀʀᴇ ᴍᴏʀᴇ ᴅᴀɴɢᴇʀᴏᴜs!\n"
        f"🔥 ᴄᴜʀʀᴇɴᴛ ᴡɪɴ sᴛʀᴇᴀᴋ: {user_games[user_id].battle_wins}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex("^jjk_mission_"))
async def select_mission(client, callback_query):
    user_id = callback_query.from_user.id
    difficulty = callback_query.data.split("_")[-1]
    
    if user_id not in user_games:
        await callback_query.answer("ɢᴀᴍᴇ ɴᴏᴛ sᴛᴀʀᴛᴇᴅ!", show_alert=True)
        return
    
    mission = await user_games[user_id].start_mission(difficulty)
    
    if not mission:
        await callback_query.answer("ɪɴᴠᴀʟɪᴅ ᴅɪғғɪᴄᴜʟᴛʏ!", show_alert=True)
        return
    
    await callback_query.edit_message_text(
        f"⚡ ᴍɪssɪᴏɴ sᴛᴀʀᴛᴇᴅ: {difficulty} ᴄᴜʀsᴇ ⚡\n\n"
        f"📜 {mission['description']}\n\n"
        f"❤ ʏᴏᴜʀ ʜᴘ: {user_games[user_id].current_health}\n"
        f"☠ ᴄᴜʀsᴇ ʜᴘ: {mission['curse_health']}\n"
        f"💰 ᴘᴏᴛᴇɴᴛɪᴀʟ ʀᴇᴡᴀʀᴅ: {mission['reward']} ᴄᴏɪɴs\n\n"
        "ᴜsᴇ /jjkattack ᴛᴏ ғɪɢʜᴛ ᴛʜᴇ ᴄᴜʀsᴇ!\n"
        "ᴛᴇᴄʜɴɪϙᴜᴇs ᴀᴠᴀɪʟᴀʙʟᴇ:\n" + 
        "\n".join([f"➤ {tech}" for tech in user_games[user_id].character["techniques"]])
    )

@app.on_message(filters.command("jjkattack"))
async def attack_curse(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("sᴛᴀʀᴛ ᴀ ɢᴀᴍᴇ ᴡɪᴛʜ /jjkstart ғɪʀsᴛ!")
        return
    
    if not user_games[user_id].current_mission:
        await message.reply_text("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴀ ᴍɪssɪᴏɴ ғɪʀsᴛ ᴡɪᴛʜ /jjkmission")
        return
    
    args = message.text.split()
    technique_index = 0
    
    if len(args) > 1:
        try:
            technique_index = int(args[1]) - 1
            if technique_index < 0 or technique_index >= len(user_games[user_id].character['techniques']):
                await message.reply_text("ɪɴᴠᴀʟɪᴅ ᴛᴇᴄʜɴɪϙᴜᴇ ɴᴜᴍʙᴇʀ!")
                return
        except ValueError:
            await message.reply_text("ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴛᴇᴄʜɴɪϙᴜᴇ ɴᴜᴍʙᴇʀ!")
            return
    
    result = await user_games[user_id].attack(technique_index)
    
    if result is None:
        await message.reply_text("ɪɴᴠᴀʟɪᴅ ᴀᴛᴛᴀᴄᴋ!")
        return
    
    battle_log = "\n".join(user_games[user_id].battle_log[-3:])
    
    if result["outcome"] == "win":
        # ᴜᴘᴅᴀᴛᴇ ᴜsᴇʀ ʙᴀʟᴀɴᴄᴇ ᴜsɪɴɢ sᴀғᴇ ᴍᴇᴛʜᴏᴅ
        await update_balance(user_id, user_games[user_id].balance_reward)
        
        # ᴄʜᴇᴄᴋ ғᴏʀ ᴡɪɴ sᴛʀᴇᴀᴋ ʙᴏɴᴜs
        streak_bonus = 0
        if user_games[user_id].battle_wins % 5 == 0:
            streak_bonus = user_games[user_id].balance_reward // 2
            await update_balance(user_id, streak_bonus)
            battle_log += f"\n\n✨ 5-ᴡɪɴ sᴛʀᴇᴀᴋ ʙᴏɴᴜs: +{streak_bonus} ᴄᴏɪɴs!"
        
        await message.reply_text(
            f"{battle_log}\n\n"
            f"🏆 ᴛᴏᴛᴀʟ ᴄᴏɪɴs ᴇᴀʀɴᴇᴅ: {user_games[user_id].balance_reward + streak_bonus}\n"
            f"🔥 ᴄᴜʀʀᴇɴᴛ ᴡɪɴ sᴛʀᴇᴀᴋ: {user_games[user_id].battle_wins}\n\n"
            "sᴛᴀʀᴛ ᴀɴᴏᴛʜᴇʀ ᴍɪssɪᴏɴ ᴡɪᴛʜ /jjkmission"
        )
        
        user_games[user_id].current_mission = None
    elif result["outcome"] == "lose":
        await message.reply_text(
            f"{battle_log}\n\n"
            "💀 ʏᴏᴜ ᴡᴇʀᴇ ᴅᴇғᴇᴀᴛᴇᴅ! ʏᴏᴜʀ ᴡɪɴ sᴛʀᴇᴀᴋ ʜᴀs ʙᴇᴇɴ ʀᴇsᴇᴛ.\n"
            "sᴛᴀʀᴛ ᴀ ɴᴇᴡ ᴍɪssɪᴏɴ ᴡɪᴛʜ /jjkmission"
        )
        del user_games[user_id]
    else:
        await message.reply_text(
            f"{battle_log}\n\n"
            f"❤ ʏᴏᴜʀ ʜᴘ: {result['player_health']}\n"
            f"☠ ᴄᴜʀsᴇ ʜᴘ: {result['curse_health']}\n\n"
            "ᴀᴛᴛᴀᴄᴋ ᴀɢᴀɪɴ ᴡɪᴛʜ /jjkattack [ᴛᴇᴄʜɴɪϙᴜᴇ ɴᴜᴍʙᴇʀ]\n"
            "ᴏʀ ᴜsᴇ /jjkspecial ғᴏʀ ʏᴏᴜʀ sᴘᴇᴄɪᴀʟ ᴛᴇᴄʜɴɪϙᴜᴇ\n"
            "ᴏʀ /jjkheal ᴛᴏ ʀᴇᴄᴏᴠᴇʀ ʜᴘ"
        )

@app.on_message(filters.command("jjkspecial"))
async def use_special(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("sᴛᴀʀᴛ ᴀ ɢᴀᴍᴇ ᴡɪᴛʜ /jjkstart ғɪʀsᴛ!")
        return
    
    if not user_games[user_id].current_mission:
        await message.reply_text("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴀ ᴍɪssɪᴏɴ ғɪʀsᴛ ᴡɪᴛʜ /jjkmission")
        return
    
    result = await user_games[user_id].use_special()
    
    if "error" in result:
        await message.reply_text(result["error"])
        return
    
    battle_log = "\n".join(user_games[user_id].battle_log[-3:])
    
    if result["outcome"] == "win":
        await update_balance(user_id, user_games[user_id].balance_reward)
        
        await message.reply_text(
            f"{battle_log}\n\n"
            f"🏆 ᴛᴏᴛᴀʟ ᴄᴏɪɴs ᴇᴀʀɴᴇᴅ: {user_games[user_id].balance_reward}\n"
            f"🔥 ᴄᴜʀʀᴇɴᴛ ᴡɪɴ sᴛʀᴇᴀᴋ: {user_games[user_id].battle_wins}\n\n"
            "sᴛᴀʀᴛ ᴀɴᴏᴛʜᴇʀ ᴍɪssɪᴏɴ ᴡɪᴛʜ /jjkmission"
        )
        
        user_games[user_id].current_mission = None
    elif result["outcome"] == "lose":
        await message.reply_text(
            f"{battle_log}\n\n"
            "💀 ʏᴏᴜ ᴡᴇʀᴇ ᴅᴇғᴇᴀᴛᴇᴅ! ʏᴏᴜʀ ᴡɪɴ sᴛʀᴇᴀᴋ ʜᴀs ʙᴇᴇɴ ʀᴇsᴇᴛ.\n"
            "sᴛᴀʀᴛ ᴀ ɴᴇᴡ �ᴍɪssɪᴏɴ ᴡɪᴛʜ /jjkmission"
        )
        del user_games[user_id]
    else:
        await message.reply_text(
            f"{battle_log}\n\n"
            f"❤ ʏᴏᴜʀ ʜᴘ: {result['player_health']}\n"
            f"☠ ᴄᴜʀsᴇ ʜᴘ: {result['curse_health']}\n\n"
            "ᴄᴏɴᴛɪɴᴜᴇ ғɪɢʜᴛɪɴɢ ᴡɪᴛʜ /jjkattack"
        )

@app.on_message(filters.command("jjkheal"))
async def heal_character(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("sᴛᴀʀᴛ ᴀ ɢᴀᴍᴇ �ᴡɪᴛʜ /jjkstart ғɪʀsᴛ!")
        return
    
    if not user_games[user_id].current_mission:
        await message.reply_text("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ ɪɴ ᴀ ᴍɪssɪᴏɴ ᴛᴏ ʜᴇᴀʟ!")
        return
    
    result = await user_games[user_id].heal()
    
    await message.reply_text(
        f"💚 ʜᴇᴀʟᴇᴅ ᴛᴏ {result['health']} ʜᴘ\n"
        f"🔋 ᴄᴜʀsᴇᴅ ᴇɴᴇʀɢʏ: {result['cursed_energy']}\n\n"
        "ᴄᴏɴᴛɪɴᴜᴇ ʏᴏᴜʀ ᴍɪssɪᴏɴ ᴡɪᴛʜ /jjkattack"
    )

@app.on_message(filters.command("jjkstatus"))
async def game_status(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ. sᴛᴀʀᴛ ᴏɴᴇ ᴡɪᴛʜ /jjkstart")
        return
    
    game = user_games[user_id]
    char_name = next(k for k,v in JJK_CHARACTERS.items() if v == game.character)
    status_msg = (
        f"🎌 ᴄʜᴀʀᴀᴄᴛᴇʀ: {char_name}\n"
        f"❤ ʜᴇᴀʟᴛʜ: {game.current_health}/{game.character['health']}\n"
        f"🔋 ᴄᴜʀsᴇᴅ ᴇɴᴇʀɢʏ: {game.current_cursed_energy}/{game.character['cursed_energy']}\n"
        f"🔥 ᴄᴜʀʀᴇɴᴛ ᴡɪɴ sᴛʀᴇᴀᴋ: {game.battle_wins}\n"
        f"💰 ᴄᴏɪɴs ᴇᴀʀɴᴇᴅ ᴛʜɪs sᴇssɪᴏɴ: {game.balance_reward}\n\n"
        "ᴀᴠᴀɪʟᴀʙʟᴇ ᴛᴇᴄʜɴɪϙᴜᴇs:\n" +
        "\n".join([f"➤ {tech}" for tech in game.character["techniques"]]) + "\n\n"
        f"💫 sᴘᴇᴄɪᴀʟ ᴛᴇᴄʜɴɪϙᴜᴇ: {game.character['special']}"
    )
    
    if game.current_mission:
        status_msg += (
            f"\n\nᴄᴜʀʀᴇɴᴛ ᴍɪssɪᴏɴ:\n"
            f"☠ ғɪɢʜᴛɪɴɢ ᴀ {game.current_mission['curse']} ᴄᴜʀsᴇ\n"
            f"ᴄᴜʀsᴇ ʜᴘ: {game.current_mission['curse_health']}\n"
            f"ᴘᴏᴛᴇɴᴛɪᴀʟ ʀᴇᴡᴀʀᴅ: {game.current_mission['reward']} ᴄᴏɪɴs"
        )
    
    await message.reply_text(status_msg)

@app.on_message(filters.command("jjkquit"))
async def quit_game(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_games:
        await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ ᴛᴏ ϙᴜɪᴛ!")
        return
    
    if user_games[user_id].balance_reward > 0:
        await update_balance(user_id, user_games[user_id].balance_reward)
    
    del user_games[user_id]
    await message.reply_text(
        "ʏᴏᴜ'ᴠᴇ ϙᴜɪᴛ ᴛʜᴇ ᴊᴜᴊᴜᴛsᴜ ᴋᴀɪsᴇɴ ʀᴘɢ.\n"
        "ᴀɴʏ ᴄᴏɪɴs ʏᴏᴜ ᴇᴀʀɴᴇᴅ ʜᴀᴠᴇ ʙᴇᴇɴ sᴀᴠᴇᴅ ᴛᴏ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ.\n"
        "sᴛᴀʀᴛ ᴀ ɴᴇᴡ ɢᴀᴍᴇ ᴀɴʏᴛɪᴍᴇ ᴡɪᴛʜ /jjkstart"
            )
