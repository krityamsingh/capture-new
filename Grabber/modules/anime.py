import base64
import string
from math import ceil
from . import uploader_filter, dev_filter, app
from Grabber import collection
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

ANIME_PER_PAGE = 6
LETTERS = list(string.ascii_uppercase)

# Replace these with actual IDs
support_channel_id = -1002313549356  # example: -100xxxxxxxxxx
dev_filter_id = 8496760733  # example: your Telegram user ID

deleted_anime_backup = {}

# Safe encode (max 43 chars to stay under 64-byte callback_data limit)
def encode_anime(anime: str) -> str:
    return base64.urlsafe_b64encode(anime.encode()).decode()[:43]

# Safe decode
def decode_anime(encoded: str) -> str:
    try:
        return base64.urlsafe_b64decode(encoded.encode()).decode()
    except Exception:
        return None

@app.on_message(uploader_filter & filters.command("editanime"))
async def edit_anime_command(client, message: Message):
    keyboard = []
    row = []
    for i, letter in enumerate(LETTERS, 1):
        row.append(InlineKeyboardButton(letter, callback_data=f"ea_l_{letter}"))
        if i % 6 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await message.reply_text(
        "✍️ Choose a letter to filter anime by name:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex("^ea_l_"))
async def anime_letter_page(client, query: CallbackQuery):
    letter = query.data.split("_")[-1]
    await send_anime_page(query.message, letter, 1)

@app.on_callback_query(filters.regex("^apg_"))
async def anime_pagination(client, query: CallbackQuery):
    try:
        _, letter, page = query.data.split("_")
        await send_anime_page(query.message, letter, int(page))
    except Exception:
        await query.answer("Invalid pagination data!", show_alert=True)

async def send_anime_page(msg: Message, letter: str, page: int):
    regex = f"^{letter}"
    anime_docs = await collection.find({"anime": {"$regex": regex, "$options": "i"}}).to_list(length=1000)
    anime_names = sorted(set(doc["anime"] for doc in anime_docs if "anime" in doc))

    total_pages = max(1, ceil(len(anime_names) / ANIME_PER_PAGE))
    start, end = (page - 1) * ANIME_PER_PAGE, page * ANIME_PER_PAGE
    page_animes = anime_names[start:end]

    keyboard = []
    row = []
    for i, anime in enumerate(page_animes, 1):
        encoded = encode_anime(anime)
        if not encoded:
            continue
        btn_text = anime[:20]
        row.append(InlineKeyboardButton(btn_text, callback_data=f"ainfo_{encoded}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"apg_{letter}_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"apg_{letter}_{page+1}"))
    if nav:
        keyboard.append(nav)

    await msg.edit_text(
        f"🔤 Showing anime starting with: **{letter}**\n📄 Page: {page}/{total_pages}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex("^ainfo_"))
async def anime_info_callback(client, query: CallbackQuery):
    encoded = query.data.split("_", 1)[-1]
    anime = decode_anime(encoded)
    if not anime:
        return await query.answer("Invalid data.", show_alert=True)

    count = await collection.count_documents({"anime": anime})

    text = f"📺 Anime Title: `{anime}`\n👧 Total Characters: `{count}`\n\n🔹 You can add, rename, remove, or view characters from this anime."
    back_letter = anime[0].upper() if anime else "A"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"e_delete_{encoded}")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"ea_l_{back_letter}")]
    ])
    await query.message.edit_text(text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("^e_rename_"))
async def start_rename_anime(client, query: CallbackQuery):
    encoded = query.data.split("_", 2)[-1]
    anime = decode_anime(encoded)
    if not anime:
        return await query.answer("Invalid rename request!", show_alert=True)

    user_id = query.from_user.id
    global user_states
    if "user_states" not in globals():
        user_states = {}
    user_states[user_id] = {"state": "renaming_anime", "anime": anime}

    await query.message.edit_text(f"✏️ Send me the new name for the anime:\n\n`{anime}`")

@app.on_message(uploader_filter & filters.command("renameanime"))
async def manual_rename_anime(client, message: Message):
    if "|" not in message.text:
        return await message.reply("Usage:\n`/renameanime Old Name | New Name`", quote=True)

    try:
        old_name, new_name = map(str.strip, message.text.split(" ", 1)[1].split("|", 1))
    except Exception:
        return await message.reply("Invalid format. Use:\n`/renameanime Old Name | New Name`")

    result = await collection.update_many({"anime": old_name}, {"$set": {"anime": new_name}})
    if result.modified_count > 0:
        text = f"✅ Renamed `{old_name}` to `{new_name}` ({result.modified_count} entries updated)."
        await client.send_message(support_channel_id, f"✏️ Anime renamed by uploader:\n`{old_name}` → `{new_name}`")
        await client.send_message(dev_filter_id, f"✏️ Rename Log:\nFrom: `{old_name}`\nTo: `{new_name}`\nCount: {result.modified_count}")
        await message.reply(text)
    else:
        await message.reply(f"⚠️ No entries found for `{old_name}`.")

@app.on_callback_query(filters.regex("^e_delete_"))
async def delete_anime(client, query: CallbackQuery):
    encoded = query.data.split("_", 2)[-1]
    anime = decode_anime(encoded)
    if not anime:
        return await query.answer("Invalid delete request!", show_alert=True)

    docs = await collection.find({"anime": anime}).to_list(length=1000)
    deleted_anime_backup[anime] = docs
    result = await collection.delete_many({"anime": anime})

    await query.message.edit_text(
        f"🗑️ Deleted anime `{anime}` and `{result.deleted_count}` waifus."
    )

    if result.deleted_count > 0:
        text = f"⚠️ Anime Deleted: `{anime}`\nTotal Waifus: `{result.deleted_count}`"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("♻️ Return", callback_data=f"returnanime_{encode_anime(anime)}")]
        ])
        await client.send_message(dev_filter_id, text, reply_markup=keyboard)

@app.on_callback_query(filters.regex("^returnanime_"))
async def restore_deleted_anime(client, query: CallbackQuery):
    encoded = query.data.split("_", 1)[-1]
    anime = decode_anime(encoded)
    if not anime or anime not in deleted_anime_backup:
        return await query.answer("No backup found!", show_alert=True)

    docs = deleted_anime_backup.pop(anime)
    if docs:
        await collection.insert_many(docs)
        await query.message.edit_text(f"✅ Restored anime `{anime}` with `{len(docs)}` waifus.")
    else:
        await query.message.edit_text(f"❌ No waifus to restore for `{anime}`.")
