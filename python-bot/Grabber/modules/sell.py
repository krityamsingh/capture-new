from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random
from Grabber import user_collection, app

SELL_LOG_CHANNEL = -1002531257849  # Replace with your log channel ID

@app.on_message(filters.command("sell"))
async def sell_character(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply(
            "❗Please provide character ID.\nUsage: /sell <id>",
            quote=True
        )

    char_id = message.command[1]
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await message.reply("⚠️ You don't have any characters.", quote=True)

    chars = user.get("characters", [])
    matched = [char for char in chars if str(char.get("id")) == str(char_id)]

    if not matched:
        return await message.reply("❌ You don't own this character.", quote=True)

    char = matched[0]
    random_price = random.randint(20000, 30000)

    text = (
        f"**ᴛᴀᴋᴇ ᴀ ʟᴏᴏᴋ ᴀᴛ** {char['name']} **ᴄʜᴀʀᴀᴄᴛᴇʀ**!\n\n"
        f"{char['anime']}\n"
        f"**ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ**: {char['id']}\n"
        f"(𝙍𝘼𝙍𝙄𝙏𝙔: {char['rarity']})\n\n"
        f"⚠️ **ᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇʟʟ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ ғᴏʀ** {random_price} **ᴛᴏᴋᴇɴs**?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ᴄᴏɴғɪʀᴍ", callback_data=f"confirm_sell|{char_id}|{random_price}"),
            InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="cancel_sell")
        ]
    ])

    try:
        if "video_url" in char:
            await message.reply_video(video=char["video_url"], caption=text, reply_markup=keyboard)
        else:
            await message.reply_photo(photo=char["img_url"], caption=text, reply_markup=keyboard)
    except Exception as e:
        await message.reply(f"❌ Error displaying character.\n{e}")

@app.on_callback_query(filters.regex("^confirm_sell\\|"))
async def confirm_sell(client, query: CallbackQuery):
    try:
        _, char_id, price = query.data.split("|")
    except ValueError:
        return await query.answer("Invalid data received!", show_alert=True)

    user_id = query.from_user.id
    price = int(price)

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await query.answer("❌ Character not found!", show_alert=True)

    chars = user.get("characters", [])
    matched = [char for char in chars if str(char.get("id")) == str(char_id)]

    if not matched:
        return await query.answer("❌ You don't own this character anymore!", show_alert=True)

    char = matched[0]
    removed = False
    for i, c in enumerate(chars):
        if str(c.get("id")) == str(char_id) and not removed:
            del chars[i]
            removed = True
            break

    await user_collection.update_one({"id": user_id}, {
        "$set": {"characters": chars},
        "$inc": {"balance": price}
    })

    try:
        await query.message.edit_caption(f"✅ **sᴏʟᴅ** {char['name']} **ғᴏʀ** {price} **ᴛᴏᴋᴇɴs**!")
    except:
        pass

    # DM the user
    try:
        caption = (
            f"🪙 You sold {char['name']}!\n"
            f"📺 {char['anime']}\n"
            f"🎗 Rarity: {char['rarity']}\n"
            f"💰 Earned: {price} coins"
        )
        if "video_url" in char:
            await client.send_video(user_id, char["video_url"], caption=caption)
        else:
            await client.send_photo(user_id, char["img_url"], caption=caption)
    except:
        pass

    # Log the sell
    try:
        await client.send_message(
            SELL_LOG_CHANNEL,
            text=(
                f"🧾 {query.from_user.mention} sold:\n\n"
                f"✨ {char['name']}\n"
                f"📺 {char['anime']}\n"
                f"🎗 {char['rarity']}\n"
                f"💰 Price: {price} coins"
            )
        )
    except:
        pass

@app.on_callback_query(filters.regex("^cancel_sell$"))
async def cancel_sell(client, query: CallbackQuery):
    try:
        await query.message.edit_caption("❌ Sell cancelled.")
    except:
        await query.answer("❌ Cannot cancel.")
