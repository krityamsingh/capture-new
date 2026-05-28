from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from Grabber import app, user_collection
from .block import block_dec, block_cbq
import random

# Random abuse messages (for unauthorized users)
abuse = random.choice([
    "🎁 This gift isn’t yours to touch!",
    "⚠️ Only the sender can confirm this gift.",
    "❌ You’re not allowed to do that.",
    "🚫 Hands off! This isn’t your gift.",
    "😤 Stop pressing random buttons!"
])

# --- /gift COMMAND HANDLER ---
@app.on_message(filters.command("gift"))
@block_dec
async def gift_handler(client, message):
    if not message.reply_to_message:
        return await message.reply("🎁 Reply to someone and type `/gift <id>` to send a character.")

    if len(message.command) < 2:
        return await message.reply("❗ Please specify the character ID — example: `/gift 1023`")

    sender = message.from_user
    receiver = message.reply_to_message.from_user
    char_id = message.command[1]

    if sender.id == receiver.id:
        return await message.reply("💀 You can’t gift a character to yourself.")

    # Get sender's collection
    sender_data = await user_collection.find_one({"id": sender.id})
    if not sender_data or "characters" not in sender_data:
        return await message.reply("⚠️ You don’t have any characters to gift.")

    char = next((c for c in sender_data["characters"] if c.get("id") == char_id), None)
    if not char:
        return await message.reply(f"❌ Character with ID `{char_id}` not found in your collection.")

    # Prevent duplicate ongoing gifts
    if char.get("locked"):
        return await message.reply(
            f"⚠️ You already started gifting `{char['name']}`.\nComplete or cancel it first.",
            reply_markup=IKM([[IKB("❌ Cancel Gift", callback_data=f"cancel_gift:{sender.id}:{char_id}")]])
        )

    # Lock this character for gifting
    await user_collection.update_one(
        {"id": sender.id, "characters.id": char_id},
        {"$set": {"characters.$.locked": True, "characters.$.gift_temp_lock": True}}
    )

    # Caption with mentions and clean style
    caption = (
        f"🎁 Gift Confirmation\n\n"
        f"{sender.mention} wants to gift a character to {receiver.mention}.\n"
        f"<blockquote>\n"
        f"• Name: {char['name']}\n"
        f"• Anime: {char['anime']}\n"
        f"• Rarity: {char.get('rarity', 'Unknown')}\n"
        f"• ID: {char_id}\n"
        f"</blockquote>\n"
        f"Do you want to continue with this transfer?"
    )

    keyboard = IKM([
        [IKB("✅ Confirm", callback_data=f"send_gift:{sender.id}:{receiver.id}:{char_id}")],
        [IKB("❌ Cancel", callback_data=f"cancel_gift:{sender.id}:{char_id}")]
    ])

    media = char.get("video_url") or char.get("img_url")
    if not media:
        await user_collection.update_one(
            {"id": sender.id, "characters.id": char_id},
            {"$unset": {"characters.$.locked": "", "characters.$.gift_temp_lock": ""}}
        )
        return await message.reply("⚠️ This character doesn’t have any media attached.")

    try:
        if char.get("video_url"):
            await message.reply_video(video=media, caption=caption, reply_markup=keyboard)
        else:
            await message.reply_photo(photo=media, caption=caption, reply_markup=keyboard)
    except Exception as e:
        await user_collection.update_one(
            {"id": sender.id, "characters.id": char_id},
            {"$unset": {"characters.$.locked": "", "characters.$.gift_temp_lock": ""}}
        )
        print(f"Gift send error: {e}")
        return await message.reply("❌ Couldn’t send confirmation message. Try again later.")

# --- CALLBACK HANDLER ---
@app.on_callback_query(filters.regex("^(send_gift|cancel_gift):"))
@block_cbq
async def gift_callback(client, cb):
    parts = cb.data.split(":")
    action = parts[0]
    sender_id = int(parts[1])
    char_id = parts[2] if action == "cancel_gift" else parts[3]

    # Unauthorized tap check
    if cb.from_user.id != sender_id:
        return await cb.answer(abuse, show_alert=True)

    # Cancel gift flow
    if action == "cancel_gift":
        await user_collection.update_one(
            {"id": sender_id, "characters.id": char_id},
            {"$unset": {"characters.$.locked": "", "characters.$.gift_temp_lock": ""}}
        )
        return await cb.message.edit("❌ Gift cancelled successfully.")

    # Confirm gift flow
    receiver_id = int(parts[2])

    # Anti-spam: prevent multiple transfers
    lock_check = await user_collection.find_one(
        {"id": sender_id, "characters.id": char_id, "characters.gift_temp_lock": True}
    )
    if not lock_check:
        return await cb.answer("⚠️ This gift was already processed.", show_alert=True)

    # Remove temporary flag right away to avoid re-taps
    await user_collection.update_one(
        {"id": sender_id, "characters.id": char_id},
        {"$unset": {"characters.$.gift_temp_lock": ""}}
    )

    sender_data = await user_collection.find_one({"id": sender_id})
    if not sender_data or "characters" not in sender_data:
        return await cb.message.edit("⚠️ Sender data not found.")

    characters = sender_data["characters"]
    char_index = next((i for i, c in enumerate(characters) if c.get("id") == char_id and c.get("locked")), None)

    if char_index is None:
        return await cb.message.edit("⚠️ This character is no longer available or already gifted.")

    char = characters.pop(char_index)

    # Update sender and receiver
    await user_collection.update_one({"id": sender_id}, {"$set": {"characters": characters}})
    await user_collection.update_one({"id": receiver_id}, {"$push": {"characters": char}}, upsert=True)

    receiver = await client.get_users(receiver_id)
    sender = await client.get_users(sender_id)

    await cb.message.edit(
        f"✅ Transfer Complete!\n\n"
        f"{sender.mention} successfully gifted {char['name']} to {receiver.mention}."
    )

    notify_caption = (
        f"✨ You received a new character from {sender.mention}!\n\n"
        f"<blockquote>\n"
        f"• Name: {char['name']}\n"
        f"• Anime: {char['anime']}\n"
        f"• Rarity: {char.get('rarity', 'Unknown')}\n"
        f"</blockquote>\n"
        f"Enjoy your new gift 🎁"
    )

    try:
        media_url = char.get("video_url") or char.get("img_url")
        if char.get("video_url"):
            await client.send_video(chat_id=receiver_id, video=media_url, caption=notify_caption)
        else:
            await client.send_photo(chat_id=receiver_id, photo=media_url, caption=notify_caption)
    except Exception as e:
        print(f"Notification failed: {e}")
