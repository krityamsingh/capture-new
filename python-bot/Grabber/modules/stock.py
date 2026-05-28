from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, CallbackQuery
from . import app, user_collection, sruby, aruby, druby, capsify 
from PIL import Image, ImageDraw, ImageFont
import random
import io

FONT_PATH = "Fonts/font.ttf"
BG_IMAGE_PATH = "Images/cmode.jpg"

def capsify(text):
    return text.upper()

def generate_image(levels, current_level, result=None):
    width, height = 400, 100
    dot_radius = 10
    spacing = 70
    bar_height = 15
    bar_width = 30

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    for i in range(5):
        x = spacing * i + 50
        y = height // 2
        color = "black"
        if i < current_level:
            color = "green" if levels[i] == "up" else "red"
        draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius), fill=color)

        if i == current_level:
            bar_color = "green" if result == "correct" else "red" if result == "incorrect" else "black"
            draw.rectangle((x - bar_width // 2, y - 25, x + bar_width // 2, y - 25 + bar_height), fill=bar_color)

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

@app.on_message(filters.command("stock"))
async def start_stock_game(client, message):
    user_id = message.from_user.id
    try:
        amount = int(message.command[1])
        if amount < 1:
            raise ValueError
    except (IndexError, ValueError):
        await message.reply_text(capsify("Use /stock [bet amount]"))
        return

    user_balance = await sruby(user_id)
    if user_balance < amount:
        await message.reply_text(capsify("You don't have enough rubies to place this bet."))
        return

    await druby(user_id, amount)

    levels = [random.choice(["up", "down"]) for _ in range(5)]
    game_data = {
        "amount": amount,
        "current_level": 0,
        "levels": levels,
        "game_active": True
    }
    await user_collection.update_one({"id": user_id}, {"$set": {"game_data": game_data}}, upsert=True)

    image = generate_image(levels, 0)
    buttons = [[IKB(capsify("Higher"), callback_data=f"{user_id}_higher"), IKB(capsify("Lower"), callback_data=f"{user_id}_lower")]]
    reply_markup = IKM(buttons)

    await message.reply_photo(
        photo=image,
        caption=capsify(f"Your current bet amount is {amount} rubies.\nChoose Higher or Lower."),
        reply_markup=reply_markup
    )

@app.on_callback_query(filters.regex(r"^\d+_(higher|lower)$"))
async def handle_stock_guess(client, query: CallbackQuery):
    user_id = int(query.data.split("_")[0])
    guess = query.data.split("_")[1]

    if user_id != query.from_user.id:
        await query.answer(capsify("This is not your game."), show_alert=True)
        return

    user_data = await user_collection.find_one({"id": user_id})
    if not user_data or not user_data.get("game_data", {}).get("game_active"):
        await query.answer(capsify("Game has ended or doesn't exist."), show_alert=True)
        return

    game_data = user_data["game_data"]
    current_level = game_data["current_level"]
    levels = game_data["levels"]
    amount = game_data["amount"]

    if current_level >= 5:
        await query.answer(capsify("Game has already ended."), show_alert=True)
        return

    correct = (levels[current_level] == "up" and guess == "higher") or \
              (levels[current_level] == "down" and guess == "lower")

    if correct:
        reward = amount // 4
        await aruby(user_id, reward)
        result = "correct"
        amount += reward
    else:
        penalty = amount // 4
        await druby(user_id, penalty)
        result = "incorrect"
        amount -= penalty

    game_data["amount"] = amount
    game_data["current_level"] += 1
    if game_data["current_level"] >= 5:
        game_data["game_active"] = False
    await user_collection.update_one({"id": user_id}, {"$set": {"game_data": game_data}})

    image = generate_image(levels, current_level + 1, result)

    if game_data["current_level"] >= 5:
        await query.message.edit_caption(
            caption=capsify(f"Game over! Your final amount is {amount} rubies."),
            reply_markup=None
        )
    else:
        buttons = [[IKB(capsify("Higher"), callback_data=f"{user_id}_higher"), IKB(capsify("Lower"), callback_data=f"{user_id}_lower")]]
        if result == "correct":
            buttons.append([IKB(capsify("Cash Out"), callback_data=f"{user_id}_cash_out")])
        reply_markup = IKM(buttons)

        await query.message.edit_media(
            media=image,
            reply_markup=reply_markup
        )

        await query.message.reply_text(capsify(f"Your current bet amount is {amount} rubies.\nChoose Higher or Lower."))

@app.on_callback_query(filters.regex(r"^\d+_cash_out$"))
async def cash_out(client, query: CallbackQuery):
    user_id = int(query.data.split("_")[0])
    if user_id != query.from_user.id:
        await query.answer(capsify("This is not your game."), show_alert=True)
        return

    user_data = await user_collection.find_one({"id": user_id})
    if not user_data or not user_data.get("game_data", {}).get("game_active"):
        await query.answer(capsify("Game has ended or doesn't exist."), show_alert=True)
        return

    game_data = user_data["game_data"]
    amount = game_data["amount"]
    await aruby(user_id, amount)

    await user_collection.update_one({"id": user_id}, {"$set": {"game_data": None}})
    await query.message.edit_caption(
        caption=capsify(f"You cashed out! Your final amount is {amount} rubies."),
        reply_markup=None
      )
