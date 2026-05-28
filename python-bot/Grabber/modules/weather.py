from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
import random
import asyncio
import aiohttp
from . import Grabberu as app

# API Endpoints
QUOTES_API = "https://api.quotable.io/random"
ENGLISH_SHAYARI_API = "https://example.com/api/english-shayari"  # Replace with actual English poetry API
COMPLIMENT_API = "https://complimentr.com/api"  # Actual compliment API
WEATHER_API = "https://api.openweathermap.org/data/2.5/weather"
GIPHY_API = "https://api.giphy.com/v1/gifs/random"
PEXELS_API = "https://api.pexels.com/v1/search"

# Weather emoji mapping
WEATHER_EMOJIS = {
    "sunny": "☀️",
    "rainy": "🌧️",
    "cloudy": "☁️",
    "stormy": "⛈️",
    "snowy": "❄️",
    "windy": "🌬️",
    "foggy": "🌫️"
}

# Active sessions
active_sessions = {}

async def fetch_api(url, params=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            return await response.json()

async def get_random_quote():
    try:
        data = await fetch_api(QUOTES_API)
        return f"\"{data['content']}\" - {data['author']}"
    except:
        return "After every storm, there comes a rainbow of hope."

async def get_english_shayari():
    try:
        data = await fetch_api(ENGLISH_SHAYARI_API)
        return data.get('shayari', "Like sunshine through the clouds,\nYour love brightens my darkest days.")
    except:
        return "The rain whispers secrets,\nThe wind carries my thoughts to you."

async def get_random_compliment():
    try:
        data = await fetch_api(COMPLIMENT_API)
        return data.get('compliment', "Your smile brightens even the cloudiest day!")
    except:
        return "You're more beautiful than a perfect sunny day!"

async def get_weather_gif(weather_type):
    try:
        params = {
            'api_key': "YOUR_GIPHY_KEY",
            'tag': f"{weather_type} weather",
            'rating': 'g'
        }
        data = await fetch_api(GIPHY_API, params=params)
        return data['data']['images']['original']['url']
    except:
        return "https://media.giphy.com/media/3o7TKsQ8gqVrXhq3Hi/giphy.gif"  # Fallback weather GIF

async def get_weather_photo(weather_type):
    try:
        headers = {"Authorization": "YOUR_PEXELS_KEY"}
        params = {'query': f"{weather_type} weather", 'per_page': 1}
        data = await fetch_api(PEXELS_API, params=params, headers=headers)
        return data['photos'][0]['src']['large']
    except:
        return "https://images.pexels.com/photos/125510/pexels-photo-125510.jpeg"  # Fallback weather photo

@app.on_message(filters.command("startmyw"))
async def start_weather_updates(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id in active_sessions:
        await message.reply("Your weather updates are already active! Use /offw to stop them.")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ Sunny", callback_data="weather_sunny")],
        [InlineKeyboardButton("🌧️ Rainy", callback_data="weather_rainy")],
        [InlineKeyboardButton("☁️ Cloudy", callback_data="weather_cloudy")],
        [InlineKeyboardButton("⛈️ Stormy", callback_data="weather_stormy")],
        [InlineKeyboardButton("❄️ Snowy", callback_data="weather_snowy")],
    ])
    
    await message.reply(
        "🌤️ Welcome to Personalized Weather Updates!\n\n"
        "Choose your favorite weather type to begin:",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^weather_"))
async def set_favorite_weather(client: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    weather_type = callback.data.split("_")[1]
    
    active_sessions[user_id] = {
        "chat_id": callback.message.chat.id,
        "favorite_weather": weather_type,
        "last_update": datetime.now(),
        "running": True
    }
    
    await callback.message.edit_text(
        f"✅ You selected {WEATHER_EMOJIS[weather_type]} {weather_type.capitalize()} weather!\n\n"
        "You'll now receive beautiful weather updates in this chat.\n"
        "Use /offw to stop the updates."
    )
    
    asyncio.create_task(send_weather_updates(client, user_id))

async def send_weather_updates(client: Client, user_id: int):
    while user_id in active_sessions and active_sessions[user_id]["running"]:
        try:
            session = active_sessions[user_id]
            chat_id = session["chat_id"]
            await asyncio.sleep(random.randint(45, 180))  # 45 seconds to 3 minutes
            
            if not active_sessions.get(user_id, {}).get("running"):
                break
            
            # Weighted random weather selection
            weather_choices = list(WEATHER_EMOJIS.keys())
            weights = [1] * len(weather_choices)
            fav_index = weather_choices.index(session["favorite_weather"])
            weights[fav_index] = 3  # Favorite weather 3x more likely
            
            weather_type = random.choices(weather_choices, weights=weights)[0]
            emoji = WEATHER_EMOJIS[weather_type]
            
            # Temperature based on weather type
            if weather_type == "sunny":
                temp = f"{random.randint(25, 38)}°C"
                desc = "Perfect day to enjoy the sunshine!"
            elif weather_type == "rainy":
                temp = f"{random.randint(18, 25)}°C"
                desc = "Don't forget your umbrella!"
            elif weather_type == "snowy":
                temp = f"{random.randint(-10, 2)}°C"
                desc = "Bundle up and stay warm!"
            else:
                temp = f"{random.randint(10, 28)}°C"
                desc = "Enjoy the weather!"
            
            # Build personalized message
            user = await client.get_users(user_id)
            message_text = f"🌦️ **Weather Update for {user.first_name}** 🌦️\n\n"
            message_text += f"{emoji} *{weather_type.capitalize()}* {emoji}\n"
            message_text += f"🌡️ Temperature: {temp}\n"
            message_text += f"📝 {desc}\n\n"
            
            # Add random content elements
            content_added = False
            if random.random() < 0.4:  # 40% chance for English poetry
                message_text += f"✍️ *Poetry Corner:*\n{await get_english_shayari()}\n\n"
                content_added = True
            
            if random.random() < 0.3 or not content_added:  # 30% chance for quote (or guaranteed if nothing else)
                message_text += f"💭 *Thought of the Day:*\n{await get_random_quote()}\n\n"
            
            if random.random() < 0.2:  # 20% chance for compliment
                message_text += f"💖 {await get_random_compliment()}\n\n"
            
            message_text += f"⏰ Last updated: {datetime.now().strftime('%I:%M %p')}"
            
            # Send with random media
            rand_val = random.random()
            if rand_val < 0.3:  # GIF
                await client.send_animation(
                    chat_id,
                    animation=await get_weather_gif(weather_type),
                    caption=message_text
                )
            elif rand_val < 0.6:  # Photo
                await client.send_photo(
                    chat_id,
                    photo=await get_weather_photo(weather_type),
                    caption=message_text
                )
            else:  # Text
                await client.send_message(chat_id, message_text)
                
            active_sessions[user_id]["last_update"] = datetime.now()
            
        except Exception as e:
            print(f"Update error: {e}")
            await asyncio.sleep(30)

@app.on_message(filters.command("offw"))
async def stop_weather_updates(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in active_sessions:
        active_sessions[user_id]["running"] = False
        del active_sessions[user_id]
        await message.reply("🌫️ Your weather updates have been stopped. We'll miss you!")
    else:
        await message.reply("You don't have any active weather updates running.")
