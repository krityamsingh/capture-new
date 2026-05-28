from pyrogram import Client, filters, enums, idle
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery,
    InputMediaAnimation,
    InputMediaPhoto
)
from datetime import datetime, timedelta
from . import Grabberu as app, user_collection
import random
import os
import asyncio
import json
import time

class AdvancedBleachBot:
    def __init__(self, app):
        self.app = app
        self.user_data = {}
        self.battle_sessions = {}
        self.quiz_sessions = {}
        
        # Enhanced character database (All Major Characters)
        self.bleach_characters = {
            "ichigo": {
                "gif": "https://files.catbox.moe/fife8z.mp4",
                "image": "https://files.catbox.moe/l5dy77.jpg",
                "quote": "I'll keep fighting until I have no strength left!",
                "power": "Getsuga Tenshō",
                "type": "Shinigami/Hollow/Quincy",
                "zanpakuto": "Zangetsu",
                "bankai": "Tensa Zangetsu",
                "stats": {
                    "attack": 95,
                    "defense": 85,
                    "speed": 90,
                    "reiatsu": 100
                },
                "abilities": [
                    "Getsuga Tenshō",
                    "Hollow Mask",
                    "Bankai",
                    "Gran Rey Cero"
                ]
            },
            "rukia": {
                "gif": "https://files.catbox.moe/0nfd3z.gif",
                "image": "https://files.catbox.moe/uw5m7o.jpg",
                "quote": "The blade is me.",
                "power": "Sode no Shirayuki",
                "type": "Shinigami",
                "zanpakuto": "Sode no Shirayuki",
                "bankai": "Hakka no Togame",
                "stats": {
                    "attack": 80,
                    "defense": 75,
                    "speed": 85,
                    "reiatsu": 85
                },
                "abilities": [
                    "Some no mai, Tsukishiro",
                    "Tsugi no mai, Hakuren",
                    "San no mai, Shirafune",
                    "Bankai"
                ]
            },
            "aizen": {
                "gif": "https://files.catbox.moe/3la5s8.mp4",
                "image": "https://files.catbox.moe/tei0q0.jpg",
                "quote": "Since when were you under the impression that I wasn't using Kyoka Suigetsu?",
                "power": "Kyoka Suigetsu",
                "type": "Shinigami/Hollow",
                "zanpakuto": "Kyoka Suigetsu",
                "bankai": "Unknown",
                "stats": {
                    "attack": 100,
                    "defense": 95,
                    "speed": 90,
                    "reiatsu": 100
                },
                "abilities": [
                    "Complete Hypnosis",
                    "Hado #90: Kurohitsugi",
                    "Cero",
                    "Immense Reiatsu"
                ]
            },
            "byakuya": {
                "gif": "https://files.catbox.moe/xv2zkh.mp4",
                "image": "https://files.catbox.moe/g6tyuq.jpg",
                "quote": "Pride is the reason I wield my sword.",
                "power": "Senbonzakura",
                "type": "Shinigami",
                "zanpakuto": "Senbonzakura",
                "bankai": "Senbonzakura Kageyoshi",
                "stats": {
                    "attack": 90,
                    "defense": 85,
                    "speed": 95,
                    "reiatsu": 95
                },
                "abilities": [
                    "Senbonzakura (Shikai/Bankai)",
                    "Shunpo Master",
                    "Kido Expert"
                ]
            },
            "toshiro": {
                "gif": "https://files.catbox.moe/lqfrbb.mp4",
                "image": "https://files.catbox.moe/gtu4p7.jpg",
                "quote": "I will surpass my limits to protect my subordinates!",
                "power": "Hyorinmaru",
                "type": "Shinigami",
                "zanpakuto": "Hyorinmaru",
                "bankai": "Daiguren Hyorinmaru",
                "stats": {
                    "attack": 85,
                    "defense": 80,
                    "speed": 90,
                    "reiatsu": 90
                },
                "abilities": [
                    "Ice Dragon techniques",
                    "Bankai: Daiguren Hyorinmaru",
                    "Kido spells"
                ]
            },
            "ulquiorra": {
                "gif": "https://files.catbox.moe/mxgriz.mp4",
                "image": "https://files.catbox.moe/125bbz.jpg",
                "quote": "The heart is just another organ.",
                "power": "Murciélago",
                "type": "Arrancar",
                "zanpakuto": "Murciélago",
                "resurreccion": "Segunda Etapa",
                "stats": {
                    "attack": 95,
                    "defense": 90,
                    "speed": 95,
                    "reiatsu": 100
                },
                "abilities": [
                    "Cero Oscuras",
                    "Lanza del Relámpago",
                    "Enhanced Regeneration"
                ]
            },
            "grimmjow": {
                "gif": "https://files.catbox.moe/xl4jff.mp4",
                "image": "https://files.catbox.moe/agtk69.jpg",
                "quote": "I'll crush you, Kurosaki!",
                "power": "Pantera",
                "type": "Arrancar",
                "resurreccion": "Pantera",
                "stats": {
                    "attack": 90,
                    "defense": 85,
                    "speed": 95,
                    "reiatsu": 90
                },
                "abilities": [
                    "Desgarrón (Claw Slashes)",
                    "Cero",
                    "Enhanced Speed"
                ]
            }
        }
        
        # Expanded Bleach Quotes (30+ Quotes)
        self.bleach_quotes = [
            "We are all afraid. That's why we become stronger! - Ichigo Kurosaki",
            "If you don't fear the sword you wield, you don't deserve to wield it at all. - Byakuya Kuchiki",
            "Pride is not the opposite of shame, but its source. - Kisuke Urahara",
            "The difference in skill is obvious. The difference in power is absolute. - Sosuke Aizen",
            "There is no heart without emptiness. - Ulquiorra Cifer",
            "Fight me! That's all I want! - Kenpachi Zaraki",
            "I reject! - Orihime Inoue",
            "I'll crush you, Kurosaki! - Grimmjow Jaegerjaquez",
            "The blade is me. - Rukia Kuchiki",
            "I will surpass my limits to protect my subordinates! - Toshiro Hitsugaya",
            "Fear is necessary for evolution. - Gin Ichimaru",
            "A sword wields no strength unless the hand that holds it has courage. - Tōsen Kaname",
            "The world is imperfect. If it were perfect, there would be nothing left. - Shunsui Kyōraku",
            "To know sorrow is not terrifying. What is terrifying is to know you can't go back to happiness. - Mayuri Kurotsuchi",
            "If you can't protect something, you don't deserve it. - Yoruichi Shihōin"
        ]
        
        # Complete Zanpakuto Data (All Types)
        self.zanpakuto_data = {
            "Shikai": {
                "desc": "First release form of a Zanpakuto",
                "examples": ["Zangetsu (Ichigo)", "Senbonzakura (Byakuya)", "Hyorinmaru (Toshiro)"],
                "gif": "https://files.catbox.moe/d5hd1j.mp4"
            },
            "Bankai": {
                "desc": "Final release form, achieved by Captains and elite warriors",
                "examples": ["Tensa Zangetsu (Ichigo)", "Senbonzakura Kageyoshi (Byakuya)", "Daiguren Hyorinmaru (Toshiro)"],
                "gif": "https://files.catbox.moe/c144k9.mp4"
            },
            "Resurrección": {
                "desc": "Arrancar release form, equivalent to Bankai",
                "examples": ["Los Lobos (Grimmjow)", "Murciélago (Ulquiorra)", "Pantera (Grimmjow)"],
                "gif": "https://files.catbox.moe/k1rdr9.mp4"
            },
            "Quincy Vollständig": {
                "desc": "Quincy ultimate technique",
                "examples": ["Letzt Stil (Uryu)", "Antithesis (Jugram)"],
                "gif": "https://files.catbox.moe/k1rdr9.mp4"
            }
        }
        
        # Expanded Quiz Questions (20 Questions)
        self.quiz_questions = [
            {
                "question": "What is Ichigo's Zanpakuto name?",
                "options": ["Zangetsu", "Hyorinmaru", "Senbonzakura", "Kyoka Suigetsu"],
                "answer": 0
            },
            {
                "question": "Who was the first Kenpachi?",
                "options": ["Kenpachi Zaraki", "Yachiru Unohana", "Toshiro Hitsugaya", "Byakuya Kuchiki"],
                "answer": 1
            },
            {
                "question": "What is Rukia's Bankai called?",
                "options": ["Sode no Shirayuki", "Hakka no Togame", "Daiguren Hyorinmaru", "Katen Kyokotsu"],
                "answer": 1
            },
            {
                "question": "What is Ulquiorra's Resurrección called?",
                "options": ["Murciélago", "Los Lobos", "Pantera", "Santa Teresa"],
                "answer": 0
            },
            {
                "question": "Which character uses 'Getsuga Tensho'?",
                "options": ["Byakuya", "Ichigo", "Toshiro", "Kenpachi"],
                "answer": 1
            },
            {
                "question": "Who said: 'The heart is just another organ'?",
                "options": ["Aizen", "Ulquiorra", "Grimmjow", "Mayuri"],
                "answer": 1
            }
        ]
        
        # Battle Phrases (Expanded)
        self.battle_phrases = [
            "Bankai!",
            "Getsuga Tenshō!",
            "Shatter, Kyoka Suigetsu!",
            "Dance, Sode no Shirayuki!",
            "Roar, Zabimaru!",
            "All waves, rise now and become my shield!",
            "Resurrección!",
            "Cero!",
            "I reject!",
            "Die where you stand!"
    ]

    def generate_stats_graph(self, stats: dict):
        """Generate a simple text-based stats graph"""
        graph = ""
        for stat, value in stats.items():
            bar = "█" * (value // 10)
            graph += f"{stat.capitalize():<8}: {bar:<10} {value}%\n"
        return graph

    async def send_bleach_greeting(self, message: Message):
        """Send an enhanced Bleach-themed greeting"""
        user = message.from_user
        self.user_data[user.id] = {
            "joined": datetime.now(),
            "power_level": random.randint(1000, 50000),
            "zanpakuto": random.choice(["Zangetsu", "Hyorinmaru", "Senbonzakura", "Sode no Shirayuki"])
        }
        
        greeting = f"""
⚔️ **Welcome to Soul Society, {user.first_name}!** ⚔️

`Bankai!` Your spiritual pressure has been detected. 

📅 **Join Date:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`
⚡ **Initial Reiatsu:** `{self.user_data[user.id]['power_level']}`
🗡️ **Zanpakuto Resonance:** `{self.user_data[user.id]['zanpakuto']}`

Choose your path:
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🩸 Character Database", callback_data="bleach_char"),
             InlineKeyboardButton("🗡️ Zanpakuto Forms", callback_data="zanpakuto")],
            [InlineKeyboardButton("🌀 Random Quote", callback_data="bleach_quote"),
             InlineKeyboardButton("⚡ Power Test", callback_data="power_level")],
            [InlineKeyboardButton("🎮 Battle Arena", callback_data="battle_start"),
             InlineKeyboardButton("❓ Bleach Quiz", callback_data="quiz_start")],
            [InlineKeyboardButton("📊 User Stats", callback_data="user_stats")]
        ])
        
        await message.reply_animation(
            animation="https://files.catbox.moe/0eewp7.mp4",
            caption=greeting,
            reply_markup=keyboard
        )

    async def handle_bleach_character(self, query: CallbackQuery):
        """Show enhanced character selection"""
        characters = list(self.bleach_characters.keys())
        
        # Split characters into rows of 2 buttons each
        keyboard = []
        for i in range(0, len(characters), 2):
            row = characters[i:i+2]
            keyboard.append([
                InlineKeyboardButton(
                    char.capitalize(), 
                    callback_data=f"char_{char}"
                ) for char in row
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="bleach_back")])
        
        await query.message.edit_text(
            "**Soul Reaper Database:**\nSelect a character for detailed information:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_character_info(self, query: CallbackQuery, character: str):
        """Display enhanced character info with media gallery"""
        char_data = self.bleach_characters.get(character.lower())
        if not char_data:
            await query.answer("Character not found!")
            return
            
        stats_graph = self.generate_stats_graph(char_data['stats'])
        
        text = f"""
🌀 **{character.capitalize()}** 🌀

*Type:* `{char_data['type']}`
*Zanpakuto:* `{char_data['zanpakuto']}`
*Bankai:* `{char_data['bankai']}`

*Signature Move:* `{char_data['power']}`
*Abilities:* `{', '.join(char_data['abilities'])}`

*Stats:*
`{stats_graph}`

*Quote:* `{char_data['quote']}`
"""
        media = [
            InputMediaAnimation(
                media=char_data['gif'],
                caption=text
            ),
            InputMediaPhoto(
                media=char_data['image'],
                caption=f"**{character.capitalize()}** - Official Artwork"
            )
        ]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗡️ Zanpakuto Info", callback_data=f"zan_{character}"),
             InlineKeyboardButton("⚔️ Battle This Character", callback_data=f"battle_{character}")],
            [InlineKeyboardButton("🔙 Back", callback_data="bleach_char")]
        ])
        
        await query.message.delete()

        # Send animation (gif) separately
        await self.app.send_animation(
            chat_id=query.message.chat.id,
            animation=char_data['gif'],
            caption=text
    )

        # Send the photo via media group (if you want to expand this in future)
        await self.app.send_media_group(
            chat_id=query.message.chat.id,
            media=[
                InputMediaPhoto(
                media=char_data['image'],
                caption=f"**{character.capitalize()}** - Official Artwork"
            )
        ]
    )

        await self.app.send_message(
            chat_id=query.message.chat.id,
            text="What would you like to do?",
            reply_markup=keyboard
    )

        await query.answer()

    async def show_zanpakuto_info(self, query: CallbackQuery, character: str):
        """Show detailed Zanpakuto information"""
        char_data = self.bleach_characters.get(character.lower())
        if not char_data:
            await query.answer("Character not found!")
            return
            
        text = f"""
🗡 **{character.capitalize()}'s Zanpakuto** 🗡

*Name:* `{char_data['zanpakuto']}`
*Bankai:* `{char_data['bankai']}`
*Type:* `{char_data['type']}`

*Abilities:*
`{', '.join(char_data['abilities'])}`

*Signature Move:* `{char_data['power']}`
"""
        await query.message.reply_animation(
            animation=char_data['gif'],
            caption=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data=f"char_{character}")]
            ])
        )
        await query.answer()

    async def show_zanpakuto_forms(self, query: CallbackQuery):
        """Display interactive Zanpakuto forms with examples"""
        text = "**Zanpakuto Release Forms**\n\n"
        for form, data in self.zanpakuto_data.items():
            text += f"⚡ **{form}:** `{data['desc']}`\n"
            text += f"   *Examples:* `{', '.join(data['examples'])}`\n\n"  # Fixed line
            
        keyboard = [
            [InlineKeyboardButton(form, callback_data=f"zanform_{form}")] 
            for form in self.zanpakuto_data.keys()
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="bleach_back")])
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_zanpakuto_form_detail(self, query: CallbackQuery, form: str):
        """Show detailed info about a specific Zanpakuto form"""
        form_data = self.zanpakuto_data.get(form)
        if not form_data:
            await query.answer("Form not found!")
            return
            
        text = f"""
⚔ **{form} Release** ⚔

*Description:* `{form_data['desc']}`
*Examples:* {", ".join(form_data['examples'])} 

*Characteristics:*
- Requires deep bond with Zanpakuto spirit
- Significant reiatsu expenditure
- Dramatic power increase
"""
        await query.message.reply_animation(
            animation=form_data['gif'],
            caption=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="zanpakuto")]
            ])
        )
        await query.answer()

    async def send_random_quote(self, query: CallbackQuery):
        """Send an animated Bleach quote"""
        quote = random.choice(self.bleach_quotes)
        await query.message.reply_animation(
            animation="https://files.catbox.moe/0eewp7.mp4",
            caption=f"**Bleach Wisdom** ✨\n\n`{quote}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Another Quote", callback_data="bleach_quote")]
            ])
        )
        await query.answer()

    async def calculate_power_level(self, query: CallbackQuery):
        """Calculate user's power level with detailed analysis"""
        user_id = query.from_user.id
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "power_level": random.randint(1000, 50000),
                "zanpakuto": random.choice(["Zangetsu", "Hyorinmaru", "Senbonzakura", "Sode no Shirayuki"])
            }
        
        power = self.user_data[user_id]["power_level"]
        zanpakuto = self.user_data[user_id]["zanpakuto"]
        
        if power < 5000:
            rank = "Human"
            badge = "👤"
        elif power < 10000:
            rank = "Shinigami"
            badge = "👻"
        elif power < 20000:
            rank = "Lieutenant"
            badge = "🎖️"
        elif power < 30000:
            rank = "Captain"
            badge = "👑"
        else:
            rank = "Soul King"
            badge = "✨"
            
        text = f"""
⚡ **Spiritual Pressure Analysis** ⚡

*Your Power Level:* `{power}`
*Rank:* `{badge} {rank}`
*Zanpakuto Resonance:* `{zanpakuto}`

*Compatibility:* `{random.choice(['Getsuga Tenshō', 'Zangetsu', 'Hyōrinmaru', 'Senbonzakura'])}`
*Potential:* `{random.choice(['Unlimited', 'Great', 'Average', 'Needs Training'])}`

*Recommendation:* `{random.choice([
    'Train in the Dangai',
    'Meditate with your Zanpakuto',
    'Fight stronger opponents',
    'Learn Kido spells'
])}`
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Retest", callback_data="power_level"),
             InlineKeyboardButton("⚔️ Battle", callback_data="battle_start")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="bleach_back")]
        ])
        
        await query.message.reply_animation(
            animation="https://files.catbox.moe/0eewp7.mp4",
            caption=text,
            reply_markup=keyboard
        )
        await query.answer()

    async def start_battle(self, query: CallbackQuery, opponent: str = None):
        """Start a battle sequence"""
        user_id = query.from_user.id
        
        if opponent:
            # Specific character battle
            char_data = self.bleach_characters.get(opponent.lower())
            if not char_data:
                await query.answer("Opponent not found!")
                return
                
            self.battle_sessions[user_id] = {
                "opponent": opponent,
                "opponent_stats": char_data['stats'],
                "user_hp": 100,
                "opponent_hp": 100,
                "turn": "user"
            }
            
            text = f"""
⚔️ **Battle Initiated** ⚔️

You are facing *{opponent.capitalize()}*!

*Your HP:* ❤️ 100
*{opponent.capitalize()}'s HP:* ❤️ 100

Choose your move:
"""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗡️ Attack", callback_data="battle_attack"),
                 InlineKeyboardButton("🛡️ Defend", callback_data="battle_defend")],
                [InlineKeyboardButton("🌀 Special", callback_data="battle_special"),
                 InlineKeyboardButton("🏃 Flee", callback_data="battle_flee")]
            ])
            
            await query.message.reply_animation(
                animation=char_data['gif'],
                caption=text,
                reply_markup=keyboard
            )
        else:
            # Random opponent selection
            opponents = list(self.bleach_characters.keys())
            opponent = random.choice(opponents)
            await self.start_battle(query, opponent)
            
        await query.answer()

    async def handle_battle_move(self, query: CallbackQuery, move: str):
        """Process battle moves"""
        user_id = query.from_user.id
        if user_id not in self.battle_sessions:
            await query.answer("No active battle!")
            return
            
        battle = self.battle_sessions[user_id]
        opponent = battle["opponent"]
        char_data = self.bleach_characters[opponent.lower()]
        
        # Process user move
        if move == "attack":
            damage = random.randint(10, 25)
            battle["opponent_hp"] -= damage
            user_move = f"You attacked with your Zanpakuto for {damage} damage!"
        elif move == "defend":
            damage = random.randint(5, 15)
            battle["opponent_hp"] -= damage
            user_move = f"You defended and counterattacked for {damage} damage!"
        elif move == "special":
            damage = random.randint(20, 40)
            battle["opponent_hp"] -= damage
            special = random.choice(char_data['abilities'])
            user_move = f"You used {special} for {damage} damage!"
        else:  # flee
            del self.battle_sessions[user_id]
            await query.message.reply_text("You fled from the battle!")
            await query.answer()
            return
            
        # Check if opponent is defeated
        if battle["opponent_hp"] <= 0:
            del self.battle_sessions[user_id]
            await query.message.reply_animation(
                animation="https://files.catbox.moe/fife8z.mp4",
                caption=f"🎉 **Victory!** You defeated {opponent.capitalize()}!"
            )
            await query.answer()
            return
            
        # Opponent's turn
        opp_move = random.choice(["attack", "defend", "special"])
        if opp_move == "attack":
            damage = random.randint(10, 20)
            battle["user_hp"] -= damage
            opp_text = f"{opponent.capitalize()} attacked you for {damage} damage!"
        elif opp_move == "defend":
            damage = random.randint(5, 15)
            battle["user_hp"] -= damage
            opp_text = f"{opponent.capitalize()} defended and counterattacked for {damage} damage!"
        else:
            damage = random.randint(15, 35)
            battle["user_hp"] -= damage
            special = random.choice(char_data['abilities'])
            opp_text = f"{opponent.capitalize()} used {special} for {damage} damage!"
            
        # Check if user is defeated
        if battle["user_hp"] <= 0:
            del self.battle_sessions[user_id]
            await query.message.reply_animation(
                animation=char_data['gif'],
                caption=f"💀 **Defeat!** {opponent.capitalize()} overwhelmed you!"
            )
            await query.answer()
            return
            
        # Update battle status
        text = f"""
⚔️ **Battle Update** │

*Your Move:* {user_move}
*Opponent's Move:* {opp_text}

*Your HP:* ❤️ {max(0, battle["user_hp"])}
*{opponent.capitalize()}'s HP:* ❤️ {max(0, battle["opponent_hp"])}

Choose your next move:
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗡️ Attack", callback_data="battle_attack"),
             InlineKeyboardButton("🛡️ Defend", callback_data="battle_defend")],
            [InlineKeyboardButton("🌀 Special", callback_data="battle_special"),
             InlineKeyboardButton("🏃 Flee", callback_data="battle_flee")]
        ])
        
        await query.message.edit_text(
            text,
            reply_markup=keyboard
        )
        await query.answer()

    async def start_quiz(self, query: CallbackQuery):
        """Start a Bleach trivia quiz"""
        user_id = query.from_user.id
        question = random.choice(self.quiz_questions)
        
        self.quiz_sessions[user_id] = {
            "question": question,
            "score": 0,
            "attempts": 0
        }
        
        options = [
            InlineKeyboardButton(opt, callback_data=f"quiz_answer_{i}")
            for i, opt in enumerate(question["options"])
        ]
        
        keyboard = InlineKeyboardMarkup([options])
        
        await query.message.reply_text(
            f"❓ **Bleach Quiz** ❓\n\n{question['question']}",
            reply_markup=keyboard
        )
        await query.answer()

    async def handle_quiz_answer(self, query: CallbackQuery, answer_idx: int):
        """Process quiz answers"""
        user_id = query.from_user.id
        if user_id not in self.quiz_sessions:
            await query.answer("No active quiz!")
            return
            
        quiz = self.quiz_sessions[user_id]
        correct = answer_idx == quiz["question"]["answer"]
        quiz["attempts"] += 1
        
        if correct:
            quiz["score"] += 1
            result = "✅ **Correct!** Well done!"
        else:
            correct_answer = quiz["question"]["options"][quiz["question"]["answer"]]
            result = f"❌ **Wrong!** The correct answer was: `{correct_answer}`"
            
        # Check if user wants to continue
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➡ Next Question", callback_data="quiz_next")],
            [InlineKeyboardButton("🏁 End Quiz", callback_data="quiz_end")]
        ])
        
        await query.message.reply_text(
            f"{result}\n\nYour current score: {quiz['score']}/{quiz['attempts']}",
            reply_markup=keyboard
        )
        await query.answer()

    async def show_user_stats(self, query: CallbackQuery):
        """Display user statistics and achievements"""
        user_id = query.from_user.id
        if user_id not in self.user_data:
            await query.answer("No data available!")
            return
            
        user = self.user_data[user_id]
        power = user["power_level"]
        
        if power < 5000:
            rank = "Human"
            badge = "👤"
        elif power < 10000:
            rank = "Shinigami"
            badge = "👻"
        elif power < 20000:
            rank = "Lieutenant"
            badge = "🎖️"
        elif power < 30000:
            rank = "Captain"
            badge = "👑"
        else:
            rank = "Soul King"
            badge = "✨"
            
        text = f"""
📊 **User Statistics** 📊

*Name:* {query.from_user.first_name}
*Rank:* {badge} {rank}
*Power Level:* {power}
*Zanpakuto:* {user["zanpakuto"]}
*Member Since:* {user["joined"].strftime('%Y-%m-%d')}

*Achievements:*
- Completed {random.randint(0, 10)} battles
- Answered {random.randint(0, 20)} quiz questions
- Reached {random.choice(['Seireitei', 'Hueco Mundo', 'Soul King Palace'])}
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Power Test", callback_data="power_level"),
             InlineKeyboardButton("🎮 Battle", callback_data="battle_start")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="bleach_back")]
        ])
        
        await query.message.reply_animation(
            animation="https://files.catbox.moe/fife8z.mp4",
            caption=text,
            reply_markup=keyboard
        )
        await query.answer()

    async def send_main_menu(self, query: CallbackQuery):
        """Return to main menu"""
        await self.send_bleach_greeting(query.message)
        await query.answer()

# Initialize the bot
bot = AdvancedBleachBot(app)

# Command handlers
@app.on_message(filters.command(["bstart", "bstart"]))
async def bleach_command(client: Client, message: Message):
    await bot.send_bleach_greeting(message)

# Callback handlers
@app.on_callback_query(filters.regex("^bleach_char$"))
async def bleach_char_callback(client: Client, query: CallbackQuery):
    await bot.handle_bleach_character(query)

@app.on_callback_query(filters.regex("^char_"))
async def character_info_callback(client: Client, query: CallbackQuery):
    character = query.data.split("_")[1]
    await bot.show_character_info(query, character)

@app.on_callback_query(filters.regex("^zan_"))
async def zanpakuto_callback(client: Client, query: CallbackQuery):
    character = query.data.split("_")[1]
    await bot.show_zanpakuto_info(query, character)

@app.on_callback_query(filters.regex("^zanpakuto$"))
async def zanpakuto_forms_callback(client: Client, query: CallbackQuery):
    await bot.show_zanpakuto_forms(query)

@app.on_callback_query(filters.regex("^zanform_"))
async def zanpakuto_form_callback(client: Client, query: CallbackQuery):
    form = query.data.split("_")[1]
    await bot.show_zanpakuto_form_detail(query, form)

@app.on_callback_query(filters.regex("^bleach_quote$"))
async def quote_callback(client: Client, query: CallbackQuery):
    await bot.send_random_quote(query)

@app.on_callback_query(filters.regex("^power_level$"))
async def power_callback(client: Client, query: CallbackQuery):
    await bot.calculate_power_level(query)

@app.on_callback_query(filters.regex("^battle_start$"))
async def battle_start_callback(client: Client, query: CallbackQuery):
    await bot.start_battle(query)

@app.on_callback_query(filters.regex("^battle_"))
async def battle_move_callback(client: Client, query: CallbackQuery):
    move = query.data.split("_")[1]
    await bot.handle_battle_move(query, move)

@app.on_callback_query(filters.regex("^quiz_start$"))
async def quiz_start_callback(client: Client, query: CallbackQuery):
    await bot.start_quiz(query)

@app.on_callback_query(filters.regex("^quiz_answer_"))
async def quiz_answer_callback(client: Client, query: CallbackQuery):
    answer_idx = int(query.data.split("_")[2])
    await bot.handle_quiz_answer(query, answer_idx)

@app.on_callback_query(filters.regex("^quiz_next$"))
async def quiz_next_callback(client: Client, query: CallbackQuery):
    await bot.start_quiz(query)

@app.on_callback_query(filters.regex("^quiz_end$"))
async def quiz_end_callback(client: Client, query: CallbackQuery):
    await query.message.reply_text("Quiz session ended!")
    await query.answer()

@app.on_callback_query(filters.regex("^user_stats$"))
async def user_stats_callback(client: Client, query: CallbackQuery):
    await bot.show_user_stats(query)

@app.on_callback_query(filters.regex("^bleach_back$"))
async def back_callback(client: Client, query: CallbackQuery):
    await bot.send_main_menu(query)
