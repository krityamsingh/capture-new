from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from . import Grabberu as app, user_collection

# Available Languages
LANGUAGES = {
    "English": "en",
    "हिन्दी": "hi",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "日本語": "ja",
    "中文": "zh",
}

@app.on_message(filters.command("setlang"))
async def set_language(client: Client, message: Message):
    user_id = message.from_user.id
    buttons = [
        [InlineKeyboardButton(lang, callback_data=f"lang_{code}")]
        for lang, code in LANGUAGES.items()
    ]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close")])

    await message.reply_text(
        "🌍 **Select Your Language:**",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

@app.on_callback_query(filters.regex("^lang_"))
async def change_language(client: Client, query):
    user_id = query.from_user.id
    lang_code = query.data.split("_")[1]

    await user_collection.update_one(
        {"id": user_id}, {"$set": {"language": lang_code}}, upsert=True
    )

    await query.answer("✅ Language updated successfully!", show_alert=True)
    await query.message.edit_text(f"🌐 Your language has been set to {lang_code.upper()}!")
