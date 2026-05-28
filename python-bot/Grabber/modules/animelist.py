import string
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
import random
from . import app, collection

# Constants
DIGITS = list("123456789")
ALPHABETS = list(string.ascii_uppercase)
BUTTONS_PER_PAGE = 15  # 5 lines * 3 buttons
ANIME_PER_PAGE = 10
CACHE_EXPIRE_MINUTES = 30

# UI Text
UI = {
    "main": "🔎 <b>Explore Animes by Initial Letter</b>",
    "select_anime": "📺 <b>Animes starting with:</b> <code>{}</code>",
    "no_anime": "⚠️ No animes found starting with <code>{}</code>.",
    "inline_tip": "❄️ <b>𝗚𝗢 𝗜𝗡𝗟𝗜𝗡𝗘 𝗔𝗡𝗗 𝗦𝗘𝗘 𝗔𝗟𝗟 𝗪𝗔𝗜𝗙𝗨𝗦 𝗢𝗙</b> <code>{}</code>\n\n<b>Total characters:</b> <code>{}</code>"
}

# Cache class
class AnimeCache:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}

    def get(self, key):
        if key in self.cache and (datetime.now() - self.timestamps[key]).seconds < CACHE_EXPIRE_MINUTES * 60:
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self.timestamps[key] = datetime.now()

anime_cache = AnimeCache()

# Alphabet Keyboard Generator
def get_alphabet_keyboard(page: int = 0):
    full_list = DIGITS + ALPHABETS
    start = page * BUTTONS_PER_PAGE
    end = min(start + BUTTONS_PER_PAGE, len(full_list))
    selected = full_list[start:end]

    buttons = []
    for i in range(0, len(selected), 3):
        row = [
            InlineKeyboardButton(letter, callback_data=f"anime_alpha:{letter}:0")
            for letter in selected[i:i+3]
        ]
        buttons.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("☜", callback_data=f"alpha_page:{page - 1}"))
    if end < len(full_list):
        nav_buttons.append(InlineKeyboardButton("☞", callback_data=f"alpha_page:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(buttons)

# Anime List Keyboard Generator
def get_anime_keyboard(anime_list, page: int, alpha: str):
    start = page * ANIME_PER_PAGE
    end = start + ANIME_PER_PAGE
    current_slice = anime_list[start:end]

    buttons = [
        [InlineKeyboardButton(anime["anime"], callback_data=f"anime_detail:{anime['anime']}")]
        for anime in current_slice
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("☜", callback_data=f"anime_alpha:{alpha}:{page - 1}"))
    if end < len(anime_list):
        nav_buttons.append(InlineKeyboardButton("☞", callback_data=f"anime_alpha:{alpha}:{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="alpha_page:0")])
    return InlineKeyboardMarkup(buttons)

# /animelist command
@app.on_message(filters.command(["animelist", "anime"]))
async def animelist_cmd(_, message: Message):
    await message.reply_text(
        UI["main"],
        reply_markup=get_alphabet_keyboard(0),
        disable_web_page_preview=True
    )

# Callback handler
@app.on_callback_query(filters.regex(r"^(alpha_page|anime_alpha|anime_detail):"))
async def animelist_callback(_, query: CallbackQuery):
    data = query.data
    try:
        if data.startswith("alpha_page:"):
            page = int(data.split(":")[1])
            await query.message.edit_text(
                UI["main"],
                reply_markup=get_alphabet_keyboard(page),
                disable_web_page_preview=True
            )

        elif data.startswith("anime_alpha:"):
            _, alpha, page = data.split(":")
            page = int(page)

            anime_list = anime_cache.get(alpha)
            if anime_list is None:
                anime_cursor = collection.aggregate([
                    {"$match": {"anime": {"$regex": f"^{alpha}", "$options": "i"}}},
                    {"$group": {"_id": "$anime"}},
                    {"$project": {"anime": "$_id", "_id": 0}},
                    {"$sort": {"anime": 1}}
                ])
                anime_list = await anime_cursor.to_list(length=None)
                anime_cache.set(alpha, anime_list)

            if not anime_list:
                await query.message.edit_text(UI["no_anime"].format(alpha))
            else:
                await query.message.edit_text(
                    UI["select_anime"].format(alpha),
                    reply_markup=get_anime_keyboard(anime_list, page, alpha),
                    disable_web_page_preview=True
                )

        elif data.startswith("anime_detail:"):
            anime = data.split(":", 1)[1]
            count = await collection.count_documents({"anime": anime})
            await query.message.edit_text(
                UI["inline_tip"].format(anime, count),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"🔎 𝗖𝗵𝗮𝗿𝗮𝗰𝘁𝗲𝗿 𝗟𝗶𝘀𝘁", switch_inline_query_current_chat=anime)],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"anime_alpha:{anime[0].upper()}:{0}")]
                ]),
                disable_web_page_preview=True
            )

        await query.answer()

    except Exception as e:
        print(f"Error in animelist_callback: {e}")
        await query.answer("⚠️ Something went wrong.", show_alert=True)
