"""
vuplaod.py — Animated / Video Character Upload Module
======================================================

Commands (sudo only):
  /hvupload <catbox_url> <character-name> <anime-name> <rarity-number>
      Upload a new animated character using a Catbox video URL.

      Rarity numbers:
          1  ⚜️ Animated       7  🟡 Legendary
          2  🔴 Common         8  🫧 Premium
          3  🟠 Rare           9  🌼 Celebrity
          4  🔵 Uncommon      10  🎐 Crystal
          5  ⚪ Epic           11  🍹 Neon
          6  🔮 Limited Ed.   12  🧿 Supreme

  /update <char_id>|<new-name>|<new-anime>|<new-video-url>
      Update name, anime, and video URL of an existing character.

  /delete <char_id>
      Permanently delete a character from the database and notify channels.

  /rglobal <char_id>
      Remove a character from ALL users' collections (with confirmation).
"""

from pymongo import ReturnDocument
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from Grabber import collection, db, user_collection
from . import app, sudo_filter


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

ANIMATION_CHANNEL_ID = -1002672414862   # Upload / animation channel
SUPPORT_GROUP_ID     = -1002313549356   # Support group chat

# ── Rarity map — number typed by uploader → rarity string stored in DB ────────
RARITY_MAP = {
    1:  "⚜️ Animated",
    2:  "🔴 Common",
    3:  "🟠 Rare",
    4:  "🔵 Uncommon",
    5:  "⚪ Epic",
    6:  "🔮 Limited Edition",
    7:  "🟡 Legendary",
    8:  "🫧 Premium",
    9:  "🌼 Celebrity",
    10: "🎐 Crystal",
    11: "🍹 Neon",
    12: "🧿 Supreme",
}

RARITY_HELP = "\n".join(
    f"  {k}  →  {v}" for k, v in RARITY_MAP.items()
)

HVUPLOAD_HELP = (
    "❌ **Wrong format!**\n\n"
    "📌 **Usage:**\n"
    "`/hvupload <catbox_url> <character-name> <anime-name> <rarity-number>`\n\n"
    "**Example:**\n"
    "`/hvupload https://files.catbox.moe/abc123.mp4 Kakashi-Hatake Naruto 1`\n\n"
    "_(Use `-` for spaces in name/anime)_\n\n"
    f"**Rarity numbers:**\n{RARITY_HELP}"
)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def get_next_sequence_number(sequence_name: str = "character_id") -> int:
    """
    Returns the next safe character ID — always greater than:
      • any ID currently stored in the characters collection, AND
      • the stored sequence counter value.
    This prevents ID collisions after resets or manual DB edits.
    """
    # Read max existing numeric ID from the actual collection
    all_chars = await collection.find(
        {"id": {"$exists": True}}, {"id": 1}
    ).to_list(length=None)

    existing_ids = []
    for c in all_chars:
        try:
            existing_ids.append(int(c["id"]))
        except (ValueError, TypeError):
            pass
    db_max = max(existing_ids) if existing_ids else 0

    # Read stored sequence counter
    seq_col = db.sequences
    seq_doc = await seq_col.find_one({"_id": sequence_name})
    seq_val = seq_doc["sequence_value"] if seq_doc else 0

    next_val = max(db_max, seq_val) + 1

    # Persist updated counter
    await seq_col.update_one(
        {"_id": sequence_name},
        {"$set": {"sequence_value": next_val}},
        upsert=True,
    )
    return next_val


async def _download_to_temp(url: str, suffix: str) -> str:
    """
    Download a URL to a named temp file and return its path.
    Raises RuntimeError on non-200 or network failure.
    Caller is responsible for deleting the file.
    """
    import tempfile, aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=120),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} while downloading {url[:80]}")
            data = await resp.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        return tmp.name


async def send_video_safe(
    client: Client,
    chat_id: int,
    video_url: str,
    caption: str,
) -> bool:
    """
    Download the video to a local temp file first, then upload to Telegram.
    NEVER passes the URL directly — Telegram throws WEBPAGE_MEDIA_EMPTY
    for Catbox and most external hosts when the URL is passed directly.
    Retries up to 3 times on failure.
    Returns True on success, False otherwise.
    """
    import os
    for attempt in range(1, 4):
        tmp_path = None
        try:
            tmp_path = await _download_to_temp(video_url, ".mp4")
            await client.send_video(
                chat_id=chat_id,
                video=tmp_path,
                caption=caption,
            )
            return True
        except Exception as e:
            print(f"⚠️ send_video attempt {attempt}/3 failed for {chat_id}: {e}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
    print(f"❌ send_video_safe: all 3 attempts failed | chat={chat_id} | url={video_url[:60]}")
    return False


async def send_photo_safe(
    client: Client,
    chat_id: int,
    photo_url: str,
    caption: str,
) -> bool:
    """
    Download the photo to a local temp file first, then upload to Telegram.
    Same reason as send_video_safe — avoids WEBPAGE_MEDIA_EMPTY errors.
    Retries up to 3 times on failure.
    Returns True on success, False otherwise.
    """
    import os
    for attempt in range(1, 4):
        tmp_path = None
        try:
            tmp_path = await _download_to_temp(photo_url, ".jpg")
            await client.send_photo(
                chat_id=chat_id,
                photo=tmp_path,
                caption=caption,
            )
            return True
        except Exception as e:
            print(f"⚠️ send_photo attempt {attempt}/3 failed for {chat_id}: {e}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
    print(f"❌ send_photo_safe: all 3 attempts failed | chat={chat_id} | url={photo_url[:60]}")
    return False


async def broadcast_character(
    client: Client,
    character: dict,
    caption: str,
) -> None:
    """
    Broadcast a character (video or photo) to both the animation channel
    and the support group. Handles both video_url and img_url gracefully.
    """
    video_url = character.get("video_url", "")
    img_url   = character.get("img_url", "")

    for chat_id in (ANIMATION_CHANNEL_ID, SUPPORT_GROUP_ID):
        if video_url:
            await send_video_safe(client, chat_id, video_url, caption)
        elif img_url:
            await send_photo_safe(client, chat_id, img_url, caption)


# ══════════════════════════════════════════════════════════════════════════════
#  /hvupload — upload animated character by Catbox URL
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("hvupload") & sudo_filter)
async def upload_video(client: Client, message: Message):
    """
    /hvupload <catbox_url> <character-name> <anime-name> <rarity-number>

    • URL must start with https://files.catbox.moe/
    • Name and anime: use hyphens for spaces (e.g. Kakashi-Hatake)
    • Rarity: integer 1–12 (see RARITY_MAP above)
    """
    args = message.text.split()[1:]

    if len(args) != 4:
        return await message.reply_text(HVUPLOAD_HELP)

    video_url, raw_name, raw_anime, raw_rarity = args

    # ── Validate URL ──────────────────────────────────────────────────────────
    if not video_url.startswith("https://files.catbox.moe/"):
        return await message.reply_text(
            "❌ **Invalid URL.**\n\n"
            "Only `https://files.catbox.moe/` links are accepted."
        )

    # ── Validate rarity ───────────────────────────────────────────────────────
    try:
        rarity = RARITY_MAP[int(raw_rarity)]
    except (KeyError, ValueError):
        return await message.reply_text(
            f"❌ **Invalid rarity number:** `{raw_rarity}`\n\n"
            f"**Valid options:**\n{RARITY_HELP}"
        )

    char_name = raw_name.replace("-", " ").title()
    anime     = raw_anime.replace("-", " ").title()

    # ── Assign sequence ID ────────────────────────────────────────────────────
    processing = await message.reply_text("⏳ **Saving character…**")

    try:
        char_id = str(await get_next_sequence_number()).zfill(2)
    except Exception as e:
        return await processing.edit_text(
            f"❌ **Failed to generate character ID:** `{str(e)}`"
        )

    # ── Build document ────────────────────────────────────────────────────────
    character = {
        "video_url": video_url,
        "name":      char_name,
        "anime":     anime,
        "rarity":    rarity,
        "id":        char_id,
    }

    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"

    caption = (
        f"🎬 **New Animated Character Added!**\n\n"
        f"👤 **Name:** {char_name}\n"
        f"📺 **Anime:** {anime}\n"
        f"⭐ **Rarity:** {rarity}\n"
        f"🆔 **ID:** `{char_id}`\n"
        f"➕ **Added by:** {mention}"
    )

    # ── Broadcast to channel + GC ─────────────────────────────────────────────
    ch_ok = await send_video_safe(client, ANIMATION_CHANNEL_ID, video_url, caption)
    gc_ok = await send_video_safe(client, SUPPORT_GROUP_ID,     video_url, caption)

    # ── Insert into DB ────────────────────────────────────────────────────────
    try:
        await collection.insert_one(character)
    except Exception as e:
        return await processing.edit_text(
            f"❌ **DB insert failed:** `{str(e)}`\n\n"
            "Character was NOT saved."
        )

    # ── Reply to uploader ─────────────────────────────────────────────────────
    status_lines = [
        f"✅ **Character saved!**\n",
        f"🆔 **ID:** `{char_id}`",
        f"👤 **Name:** {char_name}",
        f"📺 **Anime:** {anime}",
        f"⭐ **Rarity:** {rarity}",
        f"🎬 **URL:** `{video_url}`\n",
        f"📢 Channel: {'✅' if ch_ok else '❌ Failed'}",
        f"💬 Group:   {'✅' if gc_ok else '❌ Failed'}",
    ]
    await processing.edit_text("\n".join(status_lines))


# ══════════════════════════════════════════════════════════════════════════════
#  /update — update name, anime and video URL of an existing character
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("update") & sudo_filter)
async def update_character(client: Client, message: Message):
    """
    /update <char_id>|<new-name>|<new-anime>|<new-video-url>

    Pipe-separated. Name and anime accept spaces directly.
    """
    raw = message.text.split(None, 1)
    if len(raw) < 2:
        return await message.reply_text(
            "❌ **Wrong format.**\n\n"
            "📌 **Usage:**\n"
            "`/update <char_id>|<new-name>|<new-anime>|<new-video-url>`\n\n"
            "**Example:**\n"
            "`/update 42|Kakashi Hatake|Naruto|https://files.catbox.moe/xyz.mp4`"
        )

    parts = raw[1].split("|")
    if len(parts) != 4:
        return await message.reply_text(
            "❌ **Need exactly 4 fields** separated by `|`.\n"
            "`<char_id>|<new-name>|<new-anime>|<new-video-url>`"
        )

    char_id, new_name, new_anime, new_video = [p.strip() for p in parts]

    if not new_video.startswith("https://files.catbox.moe/"):
        return await message.reply_text(
            "❌ **Invalid video URL.**\n"
            "Only `https://files.catbox.moe/` links are accepted."
        )

    new_name  = new_name.title()
    new_anime = new_anime.title()

    character = await collection.find_one({"id": char_id})
    if not character:
        return await message.reply_text(
            f"❌ **Character ID `{char_id}` not found.**"
        )

    processing = await message.reply_text("⏳ **Updating character…**")

    await collection.update_one(
        {"id": char_id},
        {"$set": {
            "name":      new_name,
            "anime":     new_anime,
            "video_url": new_video,
        }}
    )

    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    caption = (
        f"🔄 **Character Updated!**\n\n"
        f"🆔 **ID:** `{char_id}`\n"
        f"👤 **Name:** {character['name']} → {new_name}\n"
        f"📺 **Anime:** {character['anime']} → {new_anime}\n"
        f"⭐ **Rarity:** {character.get('rarity', '—')}\n"
        f"🎬 **New Video:** `{new_video}`\n\n"
        f"✏️ **Updated by:** {mention}"
    )

    ch_ok = await send_video_safe(client, ANIMATION_CHANNEL_ID, new_video, caption)
    gc_ok = await send_video_safe(client, SUPPORT_GROUP_ID,     new_video, caption)

    await processing.edit_text(
        f"✅ **Character `{char_id}` updated!**\n\n"
        f"👤 {new_name} | 📺 {new_anime}\n"
        f"📢 Channel: {'✅' if ch_ok else '❌'} | 💬 Group: {'✅' if gc_ok else '❌'}"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  /delete — permanently delete a character from the DB
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("delete") & sudo_filter)
async def delete_character(client: Client, message: Message):
    """
    /delete <char_id>

    Removes the character from the main collection and notifies channels.
    Works for both video and image characters.
    """
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/delete <char_id>`\n\n"
            "**Example:** `/delete 042`"
        )

    char_id   = args[1].strip()
    character = await collection.find_one({"id": char_id})

    if not character:
        return await message.reply_text(
            f"❌ **Character ID `{char_id}` not found.**"
        )

    processing = await message.reply_text("⏳ **Deleting character…**")

    await collection.delete_one({"id": char_id})

    mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    caption = (
        f"🗑 **Character Deleted!**\n\n"
        f"🆔 **ID:** `{char_id}`\n"
        f"👤 **Name:** {character.get('name', '—')}\n"
        f"📺 **Anime:** {character.get('anime', '—')}\n"
        f"⭐ **Rarity:** {character.get('rarity', '—')}\n\n"
        f"💀 **Deleted by:** {mention}"
    )

    # Broadcast — handles both video and image characters
    await broadcast_character(client, character, caption)

    await processing.edit_text(
        f"✅ **Character `{char_id}` deleted.**\n\n"
        f"👤 {character.get('name', '—')} | 📺 {character.get('anime', '—')}"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  /rglobal — remove a character from ALL users' collections
# ══════════════════════════════════════════════════════════════════════════════

@app.on_message(filters.command("rglobal") & sudo_filter)
async def reset_global_character(client: Client, message: Message):
    """
    /rglobal <char_id>

    Shows a confirmation prompt before removing the character from every
    user's harem/collection. Does NOT delete from the main characters DB.
    """
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/rglobal <char_id>`\n\n"
            "**Example:** `/rglobal 042`"
        )

    char_id   = args[1].strip()
    character = await collection.find_one({"id": char_id})

    if not character:
        return await message.reply_text(
            f"❌ **Character ID `{char_id}` not found.**"
        )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, Remove Globally", callback_data=f"rg_yes_{char_id}"),
        InlineKeyboardButton("❌ Cancel",               callback_data=f"rg_no_{char_id}"),
    ]])

    confirm_text = (
        f"⚠️ **Global Reset Confirmation**\n\n"
        f"🆔 **ID:** `{char_id}`\n"
        f"👤 **Name:** {character.get('name', '—')}\n"
        f"📺 **Anime:** {character.get('anime', '—')}\n"
        f"⭐ **Rarity:** {character.get('rarity', '—')}\n\n"
        f"🚨 This will remove **{character.get('name', 'this character')}** "
        f"from **ALL users'** collections!\n"
        f"Are you sure?"
    )

    video_url = character.get("video_url", "")
    img_url   = character.get("img_url",   "")

    if video_url:
        await client.send_video(
            chat_id=message.chat.id,
            video=video_url,
            caption=confirm_text,
            reply_markup=keyboard,
        )
    elif img_url:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=img_url,
            caption=confirm_text,
            reply_markup=keyboard,
        )
    else:
        await message.reply_text(confirm_text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(r"^rg_(yes|no)_(.+)$"))
async def handle_rglobal_confirmation(client: Client, callback_query: CallbackQuery):
    """
    Handles Yes / No for /rglobal confirmation.
    Uses correct user_collection (db['user_collection']) to pull characters.
    """
    match   = callback_query.matches[0]
    action  = match.group(1)   # "yes" or "no"
    char_id = match.group(2)   # character ID (may be padded like "042")

    if action == "no":
        try:
            await callback_query.message.edit_caption(
                caption="❌ **Global reset cancelled.** No changes were made."
            )
        except Exception:
            await callback_query.message.edit_text(
                "❌ **Global reset cancelled.** No changes were made."
            )
        return

    # ── Fetch character info ──────────────────────────────────────────────────
    character = await collection.find_one({"id": char_id})
    if not character:
        try:
            await callback_query.message.edit_caption(
                caption=f"❌ Character `{char_id}` not found in DB."
            )
        except Exception:
            await callback_query.message.edit_text(
                f"❌ Character `{char_id}` not found in DB."
            )
        return

    # ── Remove from all users' collections ───────────────────────────────────
    # user_collection = db['user_collection'] (imported at top — NOT overwritten)
    # Characters are stored under "characters" array field in user docs
    result = await user_collection.update_many(
        {"characters.id": char_id},
        {"$pull": {"characters": {"id": char_id}}}
    )

    removed_from = result.modified_count
    by_mention   = callback_query.from_user.mention

    done_text = (
        f"✅ **Global Reset Complete!**\n\n"
        f"🆔 **ID:** `{char_id}`\n"
        f"👤 **Name:** {character.get('name', '—')}\n"
        f"📺 **Anime:** {character.get('anime', '—')}\n"
        f"⭐ **Rarity:** {character.get('rarity', '—')}\n\n"
        f"🗂 Removed from **{removed_from}** user collection(s)\n"
        f"👮 **Reset by:** {by_mention}"
    )

    # Edit the confirmation message
    try:
        await callback_query.message.edit_caption(caption=done_text)
    except Exception:
        try:
            await callback_query.message.edit_text(done_text)
        except Exception:
            pass

    # Notify both channels
    await broadcast_character(client, character, done_text)
