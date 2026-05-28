from Grabber import app, monster_collection, db
from . import sudo_filter
from pymongo import ReturnDocument
from pyrogram import filters

# Constants
MONSTER_CHANNEL_ID = -1002500900726  # Replace with your Monster Channel ID

# Error text
WRONG_FORMAT_MONSTER = "Wrong format! Use:\n/monadd <url> <monster-name-with-dashes>"

# Category mapper based on emoji
CATEGORY_MAP = {
    '': '',  # fallback
    '': '',
    '⚔️': '⚔️ ʙᴀᴛᴛʟᴇʀ',
    '': '',
    '': '',
    '': '',
}

def get_category(monster_name):
    for emoji in CATEGORY_MAP:
        if emoji in monster_name:
            return CATEGORY_MAP[emoji]
    return ""

async def get_next_monster_id():
    sequence = await db.sequences.find_one_and_update(
        {"_id": "monster_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return str(sequence["sequence_value"]).zfill(3)

async def send_media(client, chat_id, media_url, caption):
    try:
        if media_url.endswith((".mp4", ".webm")):
            return await client.send_video(chat_id, media=media_url, caption=caption)
        return await client.send_photo(chat_id, photo=media_url, caption=caption)
    except Exception as e:
        print(f"Failed to send media: {e}")

# Add monster command
@app.on_message(filters.command("monadd") & sudo_filter)
async def add_monster(client, message):
    try:
        args = message.text.split()
        if len(args) < 3:
            return await message.reply_text(WRONG_FORMAT_MONSTER)

        media_url = args[1]
        monster_name = " ".join(args[2:]).replace("-", " ").title()

        if not media_url.startswith("http"):
            return await message.reply_text("Please provide a valid media URL.")

        monster_id = await get_next_monster_id()
        category = get_category(monster_name)

        monster_doc = {
            "id": monster_id,
            "name": monster_name,
            "media_url": media_url,
            "category": category
        }

        caption = f"**New Monster Added!**\n\n🆔 ID: `{monster_id}`\n👾 Name: {monster_name}"
        if category:
            caption += f"\n🏷 Category: {category}"

        sent = await send_media(client, MONSTER_CHANNEL_ID, media_url, caption)
        if sent:
            monster_doc["message_id"] = sent.id

        await monster_collection.insert_one(monster_doc)
        await message.reply_text("✅ Monster added successfully!")

    except Exception as e:
        await message.reply_text(f"Error while adding monster:\n{e}")

# Update monster command
@app.on_message(filters.command("monupdate") & sudo_filter)
async def update_monster(client, message):
    try:
        if "|" not in message.text:
            return await message.reply_text("Use format:\n/monupdate id|new-name|new-media-url")

        _, data = message.text.split(" ", 1)
        mon_id, new_name, new_url = map(str.strip, data.split("|"))

        new_name = new_name.replace("-", " ").title()
        category = get_category(new_name)

        monster = await monster_collection.find_one({"id": mon_id})
        if not monster:
            return await message.reply_text("Monster not found.")

        update_data = {
            "name": new_name,
            "media_url": new_url,
            "category": category
        }

        await monster_collection.update_one({"id": mon_id}, {"$set": update_data})

        caption = f"**Monster Updated!**\n\n🆔 ID: `{mon_id}`\n👾 Name: {new_name}"
        if category:
            caption += f"\n🏷 Category: {category}"

        await send_media(client, MONSTER_CHANNEL_ID, new_url, caption)
        await message.reply_text("✅ Monster updated successfully!")

    except Exception as e:
        await message.reply_text(f"Error while updating monster:\n{e}")

# Delete monster command
@app.on_message(filters.command("mondelete") & sudo_filter)
async def delete_monster(client, message):
    try:
        args = message.text.split()
        if len(args) != 2:
            return await message.reply_text("Use format:\n/mondelete <monster-id>")

        mon_id = args[1]
        monster = await monster_collection.find_one({"id": mon_id})

        if not monster:
            return await message.reply_text("Monster not found.")

        await monster_collection.delete_one({"id": mon_id})

        caption = f"❌ Monster Deleted!\n\n🆔 ID: `{mon_id}`\n👾 Name: {monster['name']}"
        await send_media(client, MONSTER_CHANNEL_ID, monster["media_url"], caption)

        await message.reply_text("✅ Monster deleted successfully!")

    except Exception as e:
        await message.reply_text(f"Error while deleting monster:\n{e}")
