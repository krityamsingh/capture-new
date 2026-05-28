from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import random
from . import Grabberu as app, user_collection

# Dictionary to store user coins
user_coins = {}

# List of hard anime quiz questions
QUIZ_QUESTIONS = [
    {
        "question": "🔍 *From* **Death Note**: Who was the first Kira suspect after Light?",
        "correct": "Raye Penber",
        "options": ["L", "Naomi Misora", "Raye Penber", "Matsuda"],
        "coins": 10,
        "image": "https://files.catbox.moe/h8ogd8.jpg"
    },
    {
        "question": "🔍 *From* **Attack on Titan**: Who is the first person to discover Eren's titan form?",
        "correct": "Hange Zoe",
        "options": ["Levi", "Hange Zoe", "Mikasa", "Jean"],
        "coins": 15,
        "image": "https://files.catbox.moe/y5pirw.jpg"
    },
    {
        "question": "🔍 *From* **Steins;Gate**: Who is the real 'John Titor'?",
        "correct": "Suzuha Amane",
        "options": ["Kurisu Makise", "Rintarou Okabe", "Suzuha Amane", "Mayuri Shiina"],
        "coins": 20,
        "image": "https://files.catbox.moe/at6ffi.jpg"
    },
    {
        "question": "🔍 *From* **Tokyo Ghoul**: Who was the first person to call Kaneki 'Eyepatch'?",
        "correct": "Kotaro Amon",
        "options": ["Touka Kirishima", "Kotaro Amon", "Yamori", "Shuu Tsukiyama"],
        "coins": 12,
        "image": "https://files.catbox.moe/y4p6ak.jpg"
    },
    {
        "question": "🔍 *From* **Hunter x Hunter**: Who gave Gon his Hunter Exam badge back?",
        "correct": "Killua Zoldyck",
        "options": ["Hisoka", "Killua Zoldyck", "Leorio", "Kurapika"],
        "coins": 18,
        "image": "https://files.catbox.moe/olfxym.jpg"
    },
    {
        "question": "🔍 *From* **One Piece**: What was the name of Gol D. Roger's ship?",
        "correct": "Oro Jackson",
        "options": ["Thousand Sunny", "Oro Jackson", "Red Force", "Moby Dick"],
        "coins": 22,
        "image": "https://files.catbox.moe/akc8mc.jpg"
    },
    {
        "question": "🔍 *From* **Naruto**: What was Itachi Uchiha’s final words to Sasuke?",
        "correct": "Sorry, Sasuke… There won’t be a next time.",
        "options": [
            "You lack hatred.",
            "Sorry, Sasuke… There won’t be a next time.",
            "Stay strong, little brother.",
            "This is my reality."
        ],
        "coins": 25,
        "image": "https://files.catbox.moe/rs1nkj.jpg"
    },
    {
        "question": "🔍 *From* **Fullmetal Alchemist**: What is Edward Elric’s biggest regret?",
        "correct": "Trying to bring his mother back to life",
        "options": [
            "Not protecting Alphonse",
            "Losing his automail arm",
            "Trying to bring his mother back to life",
            "Fighting Scar"
        ],
        "coins": 17,
        "image": "https://files.catbox.moe/uy0uo5.jpg"
    },
    {
        "question": "🔍 *From* **Re:Zero**: What was Subaru's first loop death caused by?",
        "correct": "Elsa’s Knife",
        "options": ["Beatrice's Magic", "Rem’s Mace", "Elsa’s Knife", "Witch's Curse"],
        "coins": 20,
        "image": "https://files.catbox.moe/kn1tr4.jpg"
    },
    {
        "question": "🔍 *From* **Jujutsu Kaisen**: What is Gojo Satoru’s signature technique?",
        "correct": "Hollow Purple",
        "options": ["Domain Expansion", "Hollow Purple", "Cursed Speech", "Black Flash"],
        "coins": 18,
        "image": "https://files.catbox.moe/ttb0e8.jpg"
    },
    {
        "question": "🔍 *From* **Demon Slayer**: What was the last thing Rengoku said to Tanjiro before dying?",
        "correct": "Set your heart ablaze.",
        "options": [
            "Never give up.",
            "Set your heart ablaze.",
            "Protect Nezuko.",
            "Believe in yourself."
        ],
        "coins": 21,
        "image": "https://files.catbox.moe/gc7j6d.jpg"
    },
    {
        "question": "🔍 *From* **Code Geass**: What was Lelouch’s final wish?",
        "correct": "A peaceful world for Nunnally",
        "options": [
            "His own death",
            "A peaceful world for Nunnally",
            "Zero Requiem’s success",
            "The end of Britannia"
        ],
        "coins": 30,
        "image": "https://files.catbox.moe/uxcxoj.jpg"
    },
    {
        "question": "🔍 *From* **One Punch Man**: What is Saitama’s hero name?",
        "correct": "Caped Baldy",
        "options": ["One Punch Hero", "Caped Baldy", "Bald Reaper", "The Invincible"],
        "coins": 15,
        "image": "https://files.catbox.moe/kyg0qd.jpg"
    },
    {
        "question": "🔍 *From* **Bleach**: What is the name of Ichigo’s Bankai?",
        "correct": "Tensa Zangetsu",
        "options": ["Senbonzakura", "Kyoka Suigetsu", "Tensa Zangetsu", "Zabimaru"],
        "coins": 20,
        "image": "https://files.catbox.moe/ckl90b.jpg"
    },
    {
        "question": "🔍 *From* **Black Clover**: What type of magic does Asta use?",
        "correct": "Anti-Magic",
        "options": ["Wind Magic", "Demon Magic", "Dark Magic", "Anti-Magic"],
        "coins": 18,
        "image": "https://files.catbox.moe/ezaoj3.jpg"
    },
    {
        "question": "🔍 *From* **Dragon Ball Z**: Who was Goku’s first opponent in the Tournament of Power?",
        "correct": "Basil",
        "options": ["Jiren", "Hit", "Basil", "Cabba"],
        "coins": 22,
        "image": "https://files.catbox.moe/qg5nc7.jpg"
    },
    {
        "question": "🔍 *From* **Hunter x Hunter**: What is the name of Killua’s family’s assassination technique?",
        "correct": "Godspeed",
        "options": ["Silent Step", "Godspeed", "Phantom Strike", "Shadow Walk"],
        "coins": 19,
        "image": "https://files.catbox.moe/olfxym.jpg"
    },
    {
        "question": "🔍 *From* **Naruto**: Who was the first jinchuriki of Kurama?",
        "correct": "Mito Uzumaki",
        "options": ["Hashirama Senju", "Kushina Uzumaki", "Mito Uzumaki", "Madara Uchiha"],
        "coins": 25,
        "image": "https://files.catbox.moe/rs1nkj.jpg"
    },
    {
        "question": "🔍 *From* **Attack on Titan**: What was Eren’s final wish?",
        "correct": "For his friends to live in peace",
        "options": [
            "To kill all Titans",
            "To take revenge on Marley",
            "For his friends to live in peace",
            "To become the king of Eldia"
        ],
        "coins": 23,
        "image": "https://files.catbox.moe/y5pirw.jpg"
    },
    {
        "question": "🔍 *From* **Tokyo Revengers**: Who founded the Tokyo Manji Gang?",
        "correct": "Mikey",
        "options": ["Takemichi", "Mikey", "Draken", "Baji"],
        "coins": 16,
        "image": "https://files.catbox.moe/b5iqoq.jpg"
    },
    {
        "question": "🔍 *From* **Demon Slayer**: Who was the first Upper Moon Demon that Tanjiro fought?",
        "correct": "Gyutaro",
        "options": ["Akaza", "Gyutaro", "Daki", "Kokushibo"],
        "coins": 21,
        "image": "https://files.catbox.moe/gc7j6d.jpg"
    },
    {
        "question": "🔍 *From* **My Hero Academia**: What is the name of Bakugo’s quirk?",
        "correct": "Explosion",
        "options": ["Blast", "Nitro Charge", "Explosion", "Boom"],
        "coins": 17,
        "image": "https://files.catbox.moe/v5l0wn.jpg"
    },
    {
        "question": "🔍 *From* **Code Geass**: Who was the first person Lelouch used his Geass on?",
        "correct": "Clovis",
        "options": ["Suzaku", "Clovis", "Cornelia", "Charles"],
        "coins": 26,
        "image": "https://files.catbox.moe/uxcxoj.jpg"
    },
    {
        "question": "🔍 *From* **Re:Zero**: What is the name of Subaru’s curse?",
        "correct": "Return by Death",
        "options": ["Curse of Time", "Return by Death", "Death Loop", "Resurrection Curse"],
        "coins": 20,
        "image": "https://files.catbox.moe/kn1tr4.jpg"
    },
    {
        "question": "🔍 *From* **Jujutsu Kaisen**: Who was the first person to die in Shibuya Arc?",
        "correct": "Kento Nanami",
        "options": ["Jogo", "Kento Nanami", "Mai Zenin", "Suguru Geto"],
        "coins": 24,
        "image": "https://files.catbox.moe/ttb0e8.jpg"
    },
]
# Dictionary to track active quiz sessions
active_quiz = {}

@app.on_message(filters.command("quiz"))
async def start_quiz(client: Client, message: Message):
    user_id = message.from_user.id
    question_data = random.choice(QUIZ_QUESTIONS)  # Pick a random question
    question_text = question_data["question"]
    correct_answer = question_data["correct"]
    options = question_data["options"].copy()
    random.shuffle(options)  # Shuffle answer options

    # Generate answer buttons (2 per row)
    buttons = [
        [InlineKeyboardButton(options[0], callback_data=f"quiz:{user_id}:{options[0]}"),
         InlineKeyboardButton(options[1], callback_data=f"quiz:{user_id}:{options[1]}")],
        [InlineKeyboardButton(options[2], callback_data=f"quiz:{user_id}:{options[2]}"),
         InlineKeyboardButton(options[3], callback_data=f"quiz:{user_id}:{options[3]}")]
    ]
    
    # Store correct answer in active_quiz
    active_quiz[user_id] = {
        "answer": correct_answer,
        "coins": question_data["coins"]
    }

    # Send question with image
    await message.reply_photo(
        photo=question_data["image"],
        caption=f"{question_text}\n\n🎖 *Reward:* {question_data['coins']} Coins",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"^quiz:"))
async def answer_quiz(client: Client, query: CallbackQuery):
    data = query.data.split(":")
    user_id = int(data[1])
    user_answer = data[2]
    
    if user_id != query.from_user.id:
        return await query.answer("❌ This is not your quiz!", show_alert=True)

    correct_data = active_quiz.get(user_id)

    if not correct_data:
        return await query.answer("❌ No active quiz found!", show_alert=True)

    correct_answer = correct_data["answer"]
    reward_coins = correct_data["coins"]

    if user_answer == correct_answer:
        user_coins[user_id] = user_coins.get(user_id, 0) + reward_coins
        await query.answer(f"✅ Correct! 🎉 You earned {reward_coins} Coins!", show_alert=True)
    else:
        await query.answer(f"❌ Wrong! The correct answer was: {correct_answer}", show_alert=True)

    # Remove buttons after answering
    await query.message.edit_reply_markup(reply_markup=None)

@app.on_message(filters.command("coins"))
async def check_coins(client: Client, message: Message):
    user_id = message.from_user.id
    coins = user_coins.get(user_id, 0)
    await message.reply_text(f"💰 *Your Coins:* {coins} Coins")
