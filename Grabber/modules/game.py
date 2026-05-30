from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from . import app

@app.on_message(filters.command("game"))
async def play_game_command(client: Client, message: Message):
    user_tag = message.from_user.mention

    webapp_url = "https://captrue-miniapp.vercel.app?tab=arcade" 
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Arcade Games", web_app=WebAppInfo(url=webapp_url))]
    ])
    
    await message.reply_text(
        f"🕹️ **Arcade Time, {user_tag}!**\n\n"
        f"Tap the button below to open the Captrue Arcade! Play fun mini-games like Lumberjack, 2048, Flappy Bird, and Whack-a-Waifu to earn gold and rank up on the global leaderboard!",
        reply_markup=keyboard
    )
