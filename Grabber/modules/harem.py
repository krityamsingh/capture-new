from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB, InputMediaPhoto, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from PIL import Image, ImageDraw, ImageFont
from itertools import groupby
from html import escape
import asyncio
from io import BytesIO
import math
import time
import random

# Database and App Imports
from . import user_collection, collection, app
from .block import temp_block, block_cbq

# ---------------- Configuration ----------------
ADMIN_IDS = [6118760915]
SUPPORT_GROUP = "divine_catchers"
SUPPORT_CHANNEL = "IndianHelpIine"
ALLOW_CHANNEL_CHECK_FALLBACK = True
DAILY_IMAGE = "https://files.catbox.moe/wjkx61.jpg"

# ---------------- Rarity Map ----------------
RARITY_MAP = {
    '🔴 Common': '🔴', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧',
    '🟡 Legendary': '🟡', '⚪ Epic': '⚪', '🟠 Rare': '🟠', '🔵 Uncommon': '🔵',
    '🏵️ Exotic': '🏵️', '⚜️ Animated': '⚜️', '🌼 Celebrity': '🌼',
    '🎐 Crystal': '🎐', '🍹 Neon': '🍹', '🧿 Supreme': '🧿',
    '⚡ Thundra': '⚡', '🛸 Galvoria': '🛸',
    '🔮 Arcane Verse': '🔮', '🫧 Aether Verse': '🫧', '🟡 Solar Verse': '🟡'
}

# Collection mode filter keys → display names
RARITY_MODES = {
    'common': '🔴 Common', 'uncommon': '🔵 Uncommon', 'rare': '🟠 Rare',
    'legendary': '🟡 Legendary', 'limited edition': '🔮 Limited Edition',
    'premium': '🫧 Premium', 'exotic': '🏵️ Exotic', 'animated': '⚜️ Animated',
    'celebrity': '🌼 Celebrity', 'neon': '🍹 Neon', 'crystal': '🎐 Crystal',
    'supreme': '🧿 Supreme', 'thundra': '⚡ Thundra', 'galvoria': '🛸 Galvoria',
    'all': 'All', 'anime': 'Anime Sorted', 'character': 'Characters Sorted'
}

HAREM_STYLES = {
    1: "**➤ {anime} ﴾{index}/{total}﴿\n**⤷〔{rarity}〕 {id} {name} ×{count}**",
    2: "**⊙ {anime} ⦋{index}/{total}⦌\n⤷〔{rarity}〕 {id} {name} ×{count}**",
    3: "**⦾ {anime} 「{index}/{total}」\n✤ 〔{rarity}〕 {id} {name} ×{count}**",
    4: "**🈴 {anime} 「{index}/{total}」\nID: {id} 〔{rarity}〕 {name} ×{count}**",
    5: "**⌥ {anime} 〔{index}/{total}〕\n❖ ⌠ {rarity} ⌡ {id} {name} ×{count}**",
    6: "**⥱ {anime} {index}/{total}\n➥ {id} | {rarity} | {name} ×{count}**",
    7: "**● {anime} 〔{index}/{total}〕\n𝐈𝐃 : {id} ⌠ {rarity} ⌡ {name} ×{count}**",
    8: "**🍁 Name: {name} (x{count})\n**{rarity} Rarity: {rarity_name}\n🍀 Anime: {anime} ({index}/{total})**",
    9: "**❂ {anime} ❘ {index}/{total}\n**⌲ {rarity} ❘ {id} ❘ {name} ×{count}**",
    10: "**⭑ {anime} ╽ {index}/{total}\n**┊ {rarity} ╽ {id} ╽ {name} ×{count}**"
}

# ---------------- Image assets ----------------
try:
    _title_font = ImageFont.truetype("arial.ttf", 28)
    _font = ImageFont.truetype("arial.ttf", 20)
    _rarity_font = ImageFont.truetype("arial.ttf", 18)
except Exception:
    _title_font = ImageFont.load_default()
    _font = ImageFont.load_default()
    _rarity_font = ImageFont.load_default()

_bg_image = Image.new("RGBA", (900, 380), (25, 25, 25, 255))

# ---------------- Helper Functions ----------------

def get_rarity_emoji(rarity: str) -> str:
    """Return emoji for any rarity string."""
    return RARITY_MAP.get(rarity, '❔')


async def get_user_dp(client, chat_id, user_id):
    """Download user profile photo bytes if available; otherwise return None."""
    try:
        chat_member = await client.get_chat_member(chat_id, user_id)
        if chat_member and getattr(chat_member.user, "photo", None):
            data = await client.download_media(chat_member.user.photo.big_file_id, in_memory=True)
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            elif hasattr(data, "read"):
                return data.read()
    except UserNotParticipant:
        return None
    except Exception as e:
        print(f"[get_user_dp] Error: {e}")
    return None


async def create_cmode_image(full_name, user_id, current_mode, dp_bytes=None):
    """Create a small PNG card for cmode. Returns BytesIO or None."""
    try:
        img = _bg_image.copy()
        d = ImageDraw.Draw(img)
        full_name = full_name or "Unknown User"
        dp_size = (150, 150)
        dp_x, dp_y = 50, 100

        if dp_bytes:
            try:
                user_dp = Image.open(BytesIO(dp_bytes)).convert("RGBA")
                user_dp = user_dp.resize(dp_size, Image.LANCZOS)
                mask = Image.new("L", dp_size, 0)
                dm = ImageDraw.Draw(mask)
                dm.ellipse((0, 0, dp_size[0], dp_size[1]), fill=255)
                img.paste(user_dp, (dp_x, dp_y), mask)
            except Exception as e:
                print(f"[create_cmode_image] DP error: {e}")

        d.text((300, 50), "ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ", fill=(255, 255, 255), font=_title_font)
        d.text((250, 120), f"ᴜsᴇʀ: {full_name}", fill=(255, 255, 255), font=_font)
        d.text((250, 180), f"ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ: {current_mode}", fill=(255, 255, 255), font=_rarity_font)

        bio = BytesIO()
        bio.name = f'cmode_{user_id}.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"[create_cmode_image] Error: {e}")
        return None


def get_join_buttons(user_id, context="harem"):
    """Return join-panel buttons."""
    return IKM([
        [IKB("🥂 ᴊᴏɪɴ ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url=f"https://t.me/{SUPPORT_GROUP}")],
        [IKB("🧃 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{SUPPORT_CHANNEL}")],
        [IKB("✅ I HAVE JOINED", callback_data=f"joined_check:{user_id}:{context}")]
    ])


async def check_membership(user_id, client):
    """Verify membership in group & channel."""
    async def _is_member(chat_identifier, is_channel=False):
        variants = [chat_identifier]
        if not str(chat_identifier).startswith("@"):
            variants.append("@" + str(chat_identifier))

        last_exc = None
        for tid in variants:
            try:
                await client.get_chat_member(tid, user_id)
                return True
            except UserNotParticipant:
                return False
            except Exception as e:
                last_exc = e
                err_txt = str(e).lower()
                chat_admin_required = (
                    "chat_admin_required" in err_txt or
                    "channels.getparticipant" in err_txt or
                    "chat_admin_required" in repr(e).lower()
                )
                if is_channel and chat_admin_required:
                    if ALLOW_CHANNEL_CHECK_FALLBACK:
                        try:
                            await client.get_chat(tid)
                            return True
                        except Exception:
                            return False
                    return False
                continue
        return False

    if not await _is_member(SUPPORT_GROUP, is_channel=False):
        return False
    if not await _is_member(SUPPORT_CHANNEL, is_channel=True):
        return False
    return True


async def fetch_user_characters(user_id):
    """Fetch user characters from DB. Returns (characters, error)."""
    user = await user_collection.find_one({"id": user_id})
    if not user or 'characters' not in user:
        return None, 'You have not guessed any characters yet.'
    characters = [c for c in user['characters'] if 'id' in c]
    if not characters:
        return None, 'No valid characters found in your collection.'
    return characters, None


async def get_user_characters(user_id):
    """Fetch & filter characters based on user's collection_mode. Returns (unique_chars, counts, user)."""
    user = await user_collection.find_one({"id": user_id})
    if not user or not user.get("characters"):
        return None, None, None

    all_chars = [c for c in user["characters"] if "id" in c]
    cmode = (user.get("collection_mode", "All") or "All").lower()

    if cmode in ("all",):
        filtered = all_chars
    elif cmode in ("anime sorted", "anime"):
        filtered = sorted(all_chars, key=lambda x: x.get("anime", "").lower())
    elif cmode in ("characters sorted", "characters"):
        filtered = sorted(all_chars, key=lambda x: x.get("name", "").lower())
    else:
        filtered = [c for c in all_chars if c.get("rarity", "").lower() == cmode]

    if not filtered:
        return None, None, None

    counts = {}
    char_map = {}
    for c in filtered:
        cid = c["id"]
        counts[cid] = counts.get(cid, 0) + 1
        if cid not in char_map:
            char_map[cid] = c

    return list(char_map.values()), counts, user


def format_harem_line(user, index, total, anime, rarity, char_id, name, count):
    """Format a single character line using the user's chosen hstyle."""
    style = HAREM_STYLES.get(user.get("hstyle", 3), HAREM_STYLES[3])
    rarity_emoji = get_rarity_emoji(rarity)
    rarity_name = rarity.split(' ', 1)[-1] if ' ' in rarity else rarity
    return style.format(
        index=index, total=total, anime=anime,
        rarity=rarity_emoji, id=char_id, name=name,
        count=count, rarity_name=rarity_name
    )


async def build_harem_message(unique_chars, counts, user, page, total_pages, user_name, filter_rarity=None):
    """Build paginated harem text. Supports both flat (hstyle) and grouped-by-anime display."""
    chars_per_page = 15
    start_idx = page * chars_per_page
    sliced = unique_chars[start_idx: start_idx + chars_per_page]

    harem_text = (
        f"<b>{escape(user_name)}'s Harem — Page {page + 1}/{total_pages}</b>\n"
    )
    if filter_rarity:
        harem_text += f"<b>Filtered by: {filter_rarity}</b>\n"

    # Group sliced characters by anime for a clean grouped display
    grouped = {}
    for c in sliced:
        anime = c.get("anime", "Unknown")
        grouped.setdefault(anime, []).append(c)

    char_index = start_idx + 1
    for anime, chars in grouped.items():
        # Show anime name with count of user's chars / total chars in DB
        try:
            total_in_db = await collection.count_documents({"anime": anime})
        except Exception:
            total_in_db = "?"
        harem_text += f"\n<b>{escape(anime)} {len(chars)}/{total_in_db}</b>\n"
        for char in chars:
            count = counts.get(char["id"], 1)
            rarity_emoji = get_rarity_emoji(char.get("rarity", ""))
            harem_text += f"◈⌠{rarity_emoji}⌡ {char['id']} {escape(char.get('name', 'Unknown'))} ×{count}\n"
            char_index += 1

    harem_text += f"\n<b>ᴛᴏᴛᴀʟ ᴜɴɪQᴜᴇ:</b> <code>{len(unique_chars)}</code>"
    return harem_text


async def create_navigation_markup(user_id, page, total_pages, cmode, total_chars, filter_rarity=None):
    """Build pagination + filter inline keyboard."""
    cmode_key = (cmode or "All").lower().replace(" ", "_")
    inline_query = f"collection.{user_id}." if cmode_key == "all" else f"collection.{user_id}.{cmode_key}"
    filter_str = filter_rarity or "None"

    nav_buttons = []
    nav_buttons.append(
        IKB("⬅️ ᴘʀᴇᴠ", callback_data=f"harem:{page - 1}:{user_id}:{filter_str}") if page > 0
        else IKB("⬅️", callback_data="noop")
    )
    nav_buttons.append(IKB(f"📖 {page + 1}/{total_pages}", callback_data="noop"))
    nav_buttons.append(
        IKB("ɴᴇxᴛ ➡️", callback_data=f"harem:{page + 1}:{user_id}:{filter_str}") if page < total_pages - 1
        else IKB("➡️", callback_data="noop")
    )

    fast_nav = []
    fast_nav.append(
        IKB("⏪ 2x", callback_data=f"harem:{max(0, page - 2)}:{user_id}:{filter_str}") if page > 1
        else IKB("⏪", callback_data="noop")
    )
    fast_nav.append(
        IKB("2x ⏩", callback_data=f"harem:{min(total_pages - 1, page + 2)}:{user_id}:{filter_str}") if page < total_pages - 2
        else IKB("⏩", callback_data="noop")
    )

    return IKM([
        nav_buttons,
        fast_nav,
        [
            IKB(f"🧃 ({total_chars})", switch_inline_query_current_chat=inline_query),
            IKB("⚜️ Animated", switch_inline_query_current_chat=f"collection.{user_id}.Animated")
        ],
        [IKB("🔎 Filter by Rarity", callback_data=f"filter:{user_id}")]
    ])


async def _get_cover_media(user, characters):
    """Return the best cover character (favorite first, else random)."""
    if not characters:
        return None
    image_character = None
    if user and user.get("favorites"):
        fav_id = user["favorites"][0] if isinstance(user["favorites"], list) else user["favorites"]
        image_character = next((c for c in characters if str(c.get("id")) == str(fav_id)), None)
    if not image_character:
        image_character = random.choice(characters)
    return image_character


async def display_harem(client, source, user_id, page, filter_rarity=None, is_initial=False, callback_query=None):
    """Core display function used by both the command and callbacks."""
    try:
        # Fetch characters (respecting collection_mode)
        unique_chars, counts, user = await get_user_characters(user_id)
        collection_mode = user.get("collection_mode", "All") if user else "All"

        # Apply optional rarity filter on top of collection_mode
        if filter_rarity and unique_chars:
            unique_chars = [c for c in unique_chars if c.get("rarity") == filter_rarity]
            if counts:
                counts = {c["id"]: counts.get(c["id"], 1) for c in unique_chars}

        if not unique_chars:
            msg = (
                f"❌ No characters found with **{filter_rarity}** rarity in your collection!"
                if filter_rarity else
                f"You don't have any characters in your current collection mode ({collection_mode}) yet."
            )
            if callback_query:
                await callback_query.message.edit_text(msg)
            else:
                await source.reply_text(msg)
            return

        chars_per_page = 15
        total_pages = math.ceil(len(unique_chars) / chars_per_page)
        page = max(0, min(page, total_pages - 1))

        user_name = source.from_user.first_name if not callback_query else callback_query.from_user.first_name
        harem_text = await build_harem_message(unique_chars, counts, user, page, total_pages, user_name, filter_rarity)
        markup = await create_navigation_markup(user_id, page, total_pages, collection_mode, len(unique_chars), filter_rarity)

        # Pick cover image
        all_chars_raw = user.get("characters", []) if user else []
        image_character = await _get_cover_media(user, unique_chars)

        if is_initial:
            # New message
            if image_character:
                vid = image_character.get("video_url") or (
                    image_character.get("img_url") if (image_character.get("img_url") or "").endswith((".mp4", ".gif")) else None
                )
                if vid:
                    await source.reply_video(vid, caption=harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                elif image_character.get("img_url"):
                    await source.reply_photo(image_character["img_url"], caption=harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                else:
                    await source.reply_text(harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            else:
                await source.reply_text(harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
        else:
            # Edit existing message
            if image_character:
                vid = image_character.get("video_url") or (
                    image_character.get("img_url") if (image_character.get("img_url") or "").endswith((".mp4", ".gif")) else None
                )
                try:
                    if vid:
                        await callback_query.message.edit_media(
                            InputMediaVideo(vid, caption=harem_text), reply_markup=markup
                        )
                    elif image_character.get("img_url"):
                        await callback_query.message.edit_media(
                            InputMediaPhoto(image_character["img_url"], caption=harem_text), reply_markup=markup
                        )
                    else:
                        await callback_query.message.edit_text(harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    await callback_query.message.edit_text(harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
            else:
                await callback_query.message.edit_text(harem_text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        print(f"[display_harem] Error: {e}")
        err = "An error occurred. Please try again later."
        if callback_query:
            try:
                await callback_query.message.edit_text(err)
            except Exception:
                pass
        else:
            await source.reply_text(err)


# ─────────────────────────────────────────────
# Command Handlers
# ─────────────────────────────────────────────

@app.on_message(filters.command(["harem", "collection"]))
async def harem_command(client, message):
    user_id = message.from_user.id
    if user_id in temp_block and (
        not isinstance(temp_block[user_id], (int, float)) or temp_block[user_id] > time.time()
    ):
        return

    if not await check_membership(user_id, client):
        return await message.reply_text(
            f"**🧃 {message.from_user.first_name}, you must join both our support group and channel to use this command!**\n\n"
            "Please join both and try again~",
            reply_markup=get_join_buttons(user_id, context="harem")
        )

    await display_harem(client, message, user_id, page=0, filter_rarity=None, is_initial=True)


@app.on_callback_query(filters.regex(r"^harem:"))
@block_cbq
async def harem_callback(client, callback_query):
    data = callback_query.data

    # Handle close action
    if "close" in data:
        parts = data.split("_")
        if len(parts) == 2:
            end_user = int(parts[1])
            if callback_query.from_user.id == end_user:
                await callback_query.answer()
                await callback_query.message.delete()
            else:
                await callback_query.answer("This is not your Harem", show_alert=True)
        return

    try:
        _, page_str, user_id_str, filter_rarity_str = data.split(":")
        page = int(page_str)
        user_id = int(user_id_str)
        filter_rarity = None if filter_rarity_str == "None" else filter_rarity_str
    except ValueError:
        await callback_query.answer("Invalid data format.", show_alert=True)
        return

    if callback_query.from_user.id != user_id:
        await callback_query.answer("It's not your Harem!", show_alert=True)
        return

    if not await check_membership(user_id, client):
        await callback_query.answer("Please join our group and channel first!", show_alert=True)
        return

    await callback_query.answer()
    await display_harem(client, callback_query.message, user_id, page, filter_rarity, is_initial=False, callback_query=callback_query)


# ─────────────────────────────────────────────
# Rarity Filter Callbacks
# ─────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^filter:"))
async def filter_callback(client, callback_query):
    try:
        _, user_id_str = callback_query.data.split(":")
        user_id = int(user_id_str)

        if callback_query.from_user.id != user_id:
            await callback_query.answer("It's not your Harem!", show_alert=True)
            return

        all_rarities = list(RARITY_MAP.keys())

        keyboard = []
        row = []
        for i, rarity in enumerate(all_rarities, 1):
            emoji = get_rarity_emoji(rarity)
            row.append(IKB(emoji, callback_data=f"apply_filter:{user_id}:{rarity}"))
            if i % 4 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([IKB("❌ Clear Filter", callback_data=f"apply_filter:{user_id}:None")])

        await callback_query.message.edit_text(
            "**🔎 Select a rarity to filter your collection:**",
            reply_markup=IKM(keyboard)
        )
    except Exception as e:
        print(f"[filter_callback] Error: {e}")
        await callback_query.answer("⚠️ Error opening filter!", show_alert=True)


@app.on_callback_query(filters.regex(r"^apply_filter:"))
async def apply_filter_callback(client, callback_query):
    try:
        _, user_id_str, filter_rarity_str = callback_query.data.split(":", 2)
        user_id = int(user_id_str)
        filter_rarity = None if filter_rarity_str == "None" else filter_rarity_str

        if callback_query.from_user.id != user_id:
            await callback_query.answer("It's not your Harem!", show_alert=True)
            return

        await callback_query.answer()
        await display_harem(client, callback_query.message, user_id, 0, filter_rarity, is_initial=False, callback_query=callback_query)

    except Exception as e:
        print(f"[apply_filter_callback] Error: {e}")
        await callback_query.answer("⚠️ Error applying filter!", show_alert=True)


# ─────────────────────────────────────────────
# Collection Mode (/cmode)
# ─────────────────────────────────────────────

@app.on_message(filters.command(["cmode", "collectionmode"]) & filters.group)
async def cmode(client, message):
    user_id = message.from_user.id
    if user_id in temp_block and (
        not isinstance(temp_block[user_id], (int, float)) or temp_block[user_id] > time.time()
    ):
        return

    if not await check_membership(user_id, client):
        return await message.reply_text(
            f"**ʜᴇʏ {message.from_user.first_name} — please join our support group & channel to use collection mode.**",
            reply_markup=get_join_buttons(user_id, context="cmode")
        )

    full_name = message.from_user.first_name or ""
    if getattr(message.from_user, "last_name", None):
        full_name += " " + message.from_user.last_name

    user_data_task = user_collection.find_one({'id': user_id})
    dp_task = get_user_dp(client, message.chat.id, user_id)
    user_data, dp_bytes = await asyncio.gather(user_data_task, dp_task)
    current_mode = user_data.get('collection_mode', 'All') if user_data else 'All'

    buttons = [
        [IKB("ʀᴀʀɪᴛʏ", callback_data=f"cmode_main:rarity:{user_id}"), IKB("ᴅᴇғᴀᴜʟᴛ (ᴀʟʟ)", callback_data=f"cmode_main:all:{user_id}")],
        [IKB("ᴀɴɪᴍᴇs", callback_data=f"cmode_main:anime:{user_id}"), IKB("ᴄʜᴀʀᴀᴄᴛᴇʀs", callback_data=f"cmode_main:character:{user_id}")],
        [IKB("ᴄᴀɴᴄᴇʟ", callback_data=f"cmode_main:cancel:{user_id}")]
    ]

    caption = (
        f"**ʜᴇʏʏᴀ {full_name}!\n\n"
        "ʏᴏᴜ ᴄᴀɴ ᴄᴜsᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ ʜᴇʀᴇ!**\n\n"
        f"**ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ:** `{current_mode}`"
    )

    try:
        if dp_bytes:
            cmode_img = await create_cmode_image(full_name, user_id, current_mode, dp_bytes)
            if cmode_img:
                await message.reply_photo(photo=cmode_img, caption=caption, reply_markup=IKM(buttons))
                return
    except Exception as e:
        print(f"[cmode] image send failed: {e}")

    await message.reply_photo(photo=DAILY_IMAGE, caption=caption, reply_markup=IKM(buttons))


@app.on_callback_query(filters.regex(r"^cmode_main:"))
async def cmode_main_callback(client, callback_query):
    try:
        _, mode, user_id_str = callback_query.data.split(':')
        user_id = int(user_id_str)

        if callback_query.from_user.id != user_id:
            await callback_query.answer("⚠️ ɴᴏᴛ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!", show_alert=True)
            return

        full_name = callback_query.from_user.first_name or ""
        if getattr(callback_query.from_user, "last_name", None):
            full_name += " " + callback_query.from_user.last_name

        if mode == "cancel":
            await callback_query.message.delete()

        elif mode == "rarity":
            buttons = [
                [IKB("🔴 Common", callback_data=f"cmode:common:{user_id}"), IKB("🔵 Uncommon", callback_data=f"cmode:uncommon:{user_id}"), IKB("🟠 Rare", callback_data=f"cmode:rare:{user_id}")],
                [IKB("🟡 Legendary", callback_data=f"cmode:legendary:{user_id}"), IKB("🔮 Ltd Edition", callback_data=f"cmode:limited edition:{user_id}"), IKB("🫧 Premium", callback_data=f"cmode:premium:{user_id}")],
                [IKB("🏵️ Exotic", callback_data=f"cmode:exotic:{user_id}"), IKB("⚜️ Animated", callback_data=f"cmode:animated:{user_id}"), IKB("⚡ Thundra", callback_data=f"cmode:thundra:{user_id}")],
                [IKB("🛸 Galvoria", callback_data=f"cmode:galvoria:{user_id}"), IKB("🍹 Neon", callback_data=f"cmode:neon:{user_id}"), IKB("🧿 Supreme", callback_data=f"cmode:supreme:{user_id}")],
                [IKB("🎐 Crystal", callback_data=f"cmode:crystal:{user_id}"), IKB("🌼 Celebrity", callback_data=f"cmode:celebrity:{user_id}"), IKB("🔙 ʙᴀᴄᴋ", callback_data=f"cmode_main:back:{user_id}")]
            ]
            await callback_query.edit_message_caption(
                f"**{full_name}, sᴇʟᴇᴄᴛ ʏᴏᴜʀ ʀᴀʀɪᴛʏ ᴍᴏᴅᴇ:**",
                reply_markup=IKM(buttons)
            )

        elif mode == "all":
            await user_collection.update_one({'id': user_id}, {'$set': {'collection_mode': 'All'}}, upsert=True)
            await callback_query.edit_message_caption(
                f"**{full_name}, ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n▸ ɴᴏᴡ sʜᴏᴡɪɴɢ: **ᴀʟʟ ɪᴛᴇᴍs**",
                reply_markup=IKM([[IKB("🔙 ʙᴀᴄᴋ", callback_data=f"cmode_main:back:{user_id}")]])
            )

        elif mode == "anime":
            await user_collection.update_one({'id': user_id}, {'$set': {'collection_mode': 'Anime Sorted'}}, upsert=True)
            await callback_query.edit_message_caption(
                f"**{full_name}, ᴄᴏʟʟᴇᴄᴛɪᴏɴ ꜱᴏʀᴛᴇᴅ!**\n\n▸ ɴᴏᴡ sʜᴏᴡɪɴɢ: **ᴀɴɪᴍᴇ ᴍᴏᴅᴇ** (A-Z)",
                reply_markup=IKM([[IKB("🔙 ʙᴀᴄᴋ", callback_data=f"cmode_main:back:{user_id}")]])
            )

        elif mode == "character":
            await user_collection.update_one({'id': user_id}, {'$set': {'collection_mode': 'Characters Sorted'}}, upsert=True)
            await callback_query.edit_message_caption(
                f"**{full_name}, ᴄᴏʟʟᴇᴄᴛɪᴏɴ ꜱᴏʀᴛᴇᴅ!**\n\n▸ ɴᴏᴡ sʜᴏᴡɪɴɢ: **ᴄʜᴀʀᴀᴄᴛᴇʀ ᴍᴏᴅᴇ** (A-Z)",
                reply_markup=IKM([[IKB("🔙 ʙᴀᴄᴋ", callback_data=f"cmode_main:back:{user_id}")]])
            )

        elif mode == "back":
            buttons = [
                [IKB("ʀᴀʀɪᴛʏ", callback_data=f"cmode_main:rarity:{user_id}"), IKB("ᴅᴇғᴀᴜʟᴛ (ᴀʟʟ)", callback_data=f"cmode_main:all:{user_id}")],
                [IKB("ᴀɴɪᴍᴇs", callback_data=f"cmode_main:anime:{user_id}"), IKB("ᴄʜᴀʀᴀᴄᴛᴇʀs", callback_data=f"cmode_main:character:{user_id}")],
                [IKB("ᴄᴀɴᴄᴇʟ", callback_data=f"cmode_main:cancel:{user_id}")]
            ]
            await callback_query.edit_message_caption(
                f"**ʜᴇʏ {full_name}!\n\nʏᴏᴜ ᴄᴀɴ ᴄᴜsᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ ʜᴇʀᴇ!**",
                reply_markup=IKM(buttons)
            )

    except Exception as e:
        print(f"[cmode_main_callback] Error: {e}")
        await callback_query.answer("⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!", show_alert=True)


@app.on_callback_query(filters.regex(r"^cmode:"))
async def cmode_callback(client, callback_query):
    try:
        _, rarity, user_id_str = callback_query.data.split(':')
        user_id = int(user_id_str)

        if callback_query.from_user.id != user_id:
            await callback_query.answer("⚠️ ɴᴏᴛ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!", show_alert=True)
            return

        collection_mode = RARITY_MODES.get(rarity)
        if not collection_mode:
            await callback_query.answer("⚠️ ɪɴᴠᴀʟɪᴅ ᴍᴏᴅᴇ!", show_alert=True)
            return

        await user_collection.update_one({'id': user_id}, {'$set': {'collection_mode': collection_mode}}, upsert=True)

        full_name = callback_query.from_user.first_name or ""
        if getattr(callback_query.from_user, "last_name", None):
            full_name += " " + callback_query.from_user.last_name

        await callback_query.edit_message_caption(
            f"**{full_name}, ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n▸ ɴᴏᴡ sʜᴏᴡɪɴɢ: **{collection_mode}**",
            reply_markup=IKM([[IKB("🔙 ʙᴀᴄᴋ", callback_data=f"cmode_main:back:{user_id}")]])
        )

    except Exception as e:
        print(f"[cmode_callback] Error: {e}")
        await callback_query.answer("⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!", show_alert=True)


# ─────────────────────────────────────────────
# Joined Check Callback
# ─────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^joined_check:"))
async def joined_check_callback(client, callback_query):
    await callback_query.answer("Checking membership...", show_alert=False)

    try:
        _, user_id_str, context = callback_query.data.split(":", 2)
        user_id = int(user_id_str)
    except Exception:
        await callback_query.answer("Invalid request.", show_alert=True)
        return

    if callback_query.from_user.id != user_id:
        await callback_query.answer("This button isn't for you.", show_alert=True)
        return

    try:
        ok = await check_membership(user_id, client)
    except Exception as e:
        print(f"[joined_check] Error: {e}")
        await callback_query.answer("Error checking membership. Try again later.", show_alert=True)
        return

    if not ok:
        await callback_query.answer("You haven't joined both chats yet. Please join and try again.", show_alert=True)
        return

    # ---- context: harem ----
    if context == "harem":
        await display_harem(client, callback_query.message, user_id, 0, None, is_initial=False, callback_query=callback_query)
        return

    # ---- context: cmode ----
    if context == "cmode":
        full_name = callback_query.from_user.first_name or ""
        if getattr(callback_query.from_user, "last_name", None):
            full_name += " " + callback_query.from_user.last_name

        user_doc = await user_collection.find_one({'id': user_id}) or {}
        current_mode = user_doc.get('collection_mode', 'All')
        dp_bytes = await get_user_dp(client, callback_query.message.chat.id, user_id)

        caption = (
            f"**ʜᴇʏʏᴀ {full_name}!\n\n"
            "ʏᴏᴜ ᴄᴀɴ ᴄᴜsᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ᴍᴏᴅᴇ ʜᴇʀᴇ!**\n\n"
            f"**ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ:** `{current_mode}`"
        )
        buttons = [
            [IKB("ʀᴀʀɪᴛʏ", callback_data=f"cmode_main:rarity:{user_id}"), IKB("ᴅᴇғᴀᴜʟᴛ (ᴀʟʟ)", callback_data=f"cmode_main:all:{user_id}")],
            [IKB("ᴀɴɪᴍᴇs", callback_data=f"cmode_main:anime:{user_id}"), IKB("ᴄʜᴀʀᴀᴄᴛᴇʀs", callback_data=f"cmode_main:character:{user_id}")],
            [IKB("ᴄᴀɴᴄᴇʟ", callback_data=f"cmode_main:cancel:{user_id}")]
        ]

        if dp_bytes:
            try:
                cmode_img = await create_cmode_image(full_name, user_id, current_mode, dp_bytes)
                if cmode_img:
                    await callback_query.message.edit_media(
                        InputMediaPhoto(cmode_img, caption=caption), reply_markup=IKM(buttons)
                    )
                    return
            except Exception as e:
                print(f"[joined_check:cmode] image error: {e}")

        try:
            await callback_query.message.edit_caption(caption, reply_markup=IKM(buttons))
        except Exception:
            await callback_query.message.reply_photo(DAILY_IMAGE, caption=caption, reply_markup=IKM(buttons))
        return

    await callback_query.answer("Membership confirmed — please run the command again.", show_alert=True)


# ─────────────────────────────────────────────
# Owner Commands
# ─────────────────────────────────────────────

OWNER_IDS = [1653814030, 7976292835, 6118760915]


@app.on_message(filters.command("deleteharem"))
async def delete_harem(client, message):
    try:
        if message.from_user.id not in OWNER_IDS:
            await message.reply_text("You don't have permission to perform this action.")
            return

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        elif len(message.command) > 1 and message.command[1].startswith('@'):
            user = await client.get_users(message.command[1])
            target_id = user.id
        elif len(message.command) > 1:
            target_id = int(message.command[1])
        else:
            target_id = message.from_user.id

        await message.reply_text(
            f"⚠️ Delete entire harem for user `{target_id}`? This cannot be undone.",
            reply_markup=IKM([
                [IKB("✅ Yes", callback_data=f"confirm_delete:{target_id}:yes"),
                 IKB("❌ Cancel", callback_data=f"confirm_delete:{target_id}:cancel")]
            ])
        )
    except Exception as e:
        print(f"[delete_harem] Error: {e}")
        await message.reply_text("An error occurred. Please try again.")


@app.on_message(filters.command("dh"))
async def delete_harem_count(client, message):
    """
    /dh <count> — delete first N characters from a user's harem.
    Usage:
      • Reply to user + /dh 10
      • /dh @username 10
      • /dh <user_id> 10
    """
    try:
        if message.from_user.id not in OWNER_IDS:
            await message.reply_text("⛔ You don't have permission to use this command.")
            return

        args = message.command[1:]  # everything after /dh

        # Parse target user and count
        target_id = None
        count = None

        if message.reply_to_message:
            # /dh <count> (reply to user)
            target_id = message.reply_to_message.from_user.id
            if args and args[0].isdigit():
                count = int(args[0])
        elif len(args) >= 2:
            # /dh @username <count>  OR  /dh <user_id> <count>
            if args[0].startswith('@'):
                user = await client.get_users(args[0])
                target_id = user.id
            else:
                target_id = int(args[0])
            if args[1].isdigit():
                count = int(args[1])
        elif len(args) == 1 and args[0].isdigit():
            # /dh <count> with no target — apply to self (rare owner use-case)
            target_id = message.from_user.id
            count = int(args[0])

        if target_id is None or count is None:
            await message.reply_text(
                "❌ **Invalid usage.**\n\n"
                "**Format:**\n"
                "• Reply to a user: `/dh <count>`\n"
                "• By username: `/dh @username <count>`\n"
                "• By user ID: `/dh <user_id> <count>`\n\n"
                "**Example:** `/dh 50` (reply) or `/dh 123456789 50`"
            )
            return

        if count <= 0:
            await message.reply_text("❌ Count must be greater than 0.")
            return

        # Fetch user data
        user_doc = await user_collection.find_one({"id": target_id})
        if not user_doc or not user_doc.get("characters"):
            await message.reply_text(f"❌ User `{target_id}` has no characters to delete.")
            return

        total = len(user_doc["characters"])
        actual_delete = min(count, total)

        await message.reply_text(
            f"⚠️ **Delete {actual_delete} characters** from user `{target_id}`?\n\n"
            f"📦 They currently have **{total}** characters.\n"
            f"🗑 After deletion: **{total - actual_delete}** will remain.\n\n"
            "This **cannot** be undone!",
            reply_markup=IKM([
                [IKB("✅ Confirm", callback_data=f"dh_confirm:{target_id}:{actual_delete}"),
                 IKB("❌ Cancel", callback_data=f"dh_cancel:{target_id}")]
            ])
        )

    except ValueError:
        await message.reply_text("❌ Invalid user ID or count. Both must be numbers.")
    except Exception as e:
        print(f"[delete_harem_count] Error: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")


@app.on_callback_query(filters.regex(r"^dh_confirm:"))
async def dh_confirm_callback(client, callback_query):
    try:
        if callback_query.from_user.id not in OWNER_IDS:
            await callback_query.answer("⛔ No permission.", show_alert=True)
            return

        _, user_id_str, count_str = callback_query.data.split(":")
        target_id = int(user_id_str)
        count = int(count_str)

        user_doc = await user_collection.find_one({"id": target_id})
        if not user_doc or not user_doc.get("characters"):
            await callback_query.message.edit_text(f"❌ User `{target_id}` has no characters.")
            return

        characters = user_doc["characters"]
        total_before = len(characters)
        actual_delete = min(count, total_before)

        # Remove the last N characters
        remaining = characters[:-actual_delete] if actual_delete < total_before else []

        await user_collection.update_one(
            {"id": target_id},
            {"$set": {"characters": remaining}}
        )

        await callback_query.message.edit_text(
            f"✅ **Done!**\n\n"
            f"👤 User: `{target_id}`\n"
            f"🗑 Deleted: **{actual_delete}** characters\n"
            f"📦 Remaining: **{len(remaining)}** characters"
        )

    except Exception as e:
        print(f"[dh_confirm_callback] Error: {e}")
        await callback_query.message.edit_text("❌ An error occurred during deletion.")


@app.on_callback_query(filters.regex(r"^dh_cancel:"))
async def dh_cancel_callback(client, callback_query):
    if callback_query.from_user.id not in OWNER_IDS:
        await callback_query.answer("⛔ No permission.", show_alert=True)
        return
    await callback_query.message.edit_text("🚫 Deletion cancelled. No changes were made.")


@app.on_callback_query(filters.regex(r"^confirm_delete:"))
async def confirm_delete_callback(client, callback_query):
    try:
        _, user_id_str, action = callback_query.data.split(':')
        user_id = int(user_id_str)

        if callback_query.from_user.id not in OWNER_IDS:
            await callback_query.answer("No permission.", show_alert=True)
            return

        if action == 'yes':
            await user_collection.update_one({"id": user_id}, {"$set": {"characters": []}})
            await callback_query.message.edit_text(f"✅ Harem for `{user_id}` has been reset!")
        elif action == 'cancel':
            await callback_query.message.edit_text("🚫 Action canceled.")
    except Exception as e:
        print(f"[confirm_delete_callback] Error: {e}")
        await callback_query.message.edit_text("An error occurred.")


@app.on_message(filters.command("transfer"))
async def transfer_harem(client, message):
    try:
        if message.from_user.id not in OWNER_IDS:
            await message.reply_text("⚠️ Only bot owners can use this command.")
            return

        if len(message.command) < 3:
            await message.reply_text("❌ Usage: `/transfer <from_user_id> <to_user_id>`")
            return

        from_id = int(message.command[1])
        to_id = int(message.command[2])

        if from_id == to_id:
            await message.reply_text("❌ Cannot transfer to the same user!")
            return

        from_user = await user_collection.find_one({"id": from_id})
        if not from_user or not from_user.get('characters'):
            await message.reply_text(f"❌ User `{from_id}` has no collection to transfer!")
            return

        await message.reply_text(
            f"⚠️ **Transfer Request**\n\nFrom: `{from_id}` ({len(from_user['characters'])} chars)\nTo: `{to_id}`\n\n**THIS WILL OVERWRITE THE DESTINATION!**",
            reply_markup=IKM([
                [IKB("✅ CONFIRM", callback_data=f"transfer_confirm:{from_id}:{to_id}"),
                 IKB("❌ CANCEL", callback_data="transfer_cancel")]
            ])
        )
    except ValueError:
        await message.reply_text("❌ Invalid user ID format.")
    except Exception as e:
        print(f"[transfer_harem] Error: {e}")
        await message.reply_text("❌ An error occurred.")


@app.on_callback_query(filters.regex(r"^transfer_confirm:"))
async def transfer_confirm_callback(client, callback_query):
    try:
        if callback_query.from_user.id not in OWNER_IDS:
            await callback_query.answer("⚠️ Owners only!", show_alert=True)
            return

        _, from_id_str, to_id_str = callback_query.data.split(':')
        from_id, to_id = int(from_id_str), int(to_id_str)

        from_user = await user_collection.find_one({"id": from_id})
        if not from_user:
            await callback_query.message.edit_text("❌ Source user no longer exists!")
            return

        await user_collection.update_one(
            {"id": to_id},
            {"$set": {"characters": from_user['characters'], "favorites": from_user.get('favorites', [])}},
            upsert=True
        )
        await user_collection.update_one({"id": from_id}, {"$set": {"characters": [], "favorites": []}})

        await callback_query.message.edit_text(
            f"♻️ **Transfer Complete**\n\n• From: `{from_id}`\n• To: `{to_id}`\n• Moved: {len(from_user['characters'])} characters\n\nSource reset!"
        )
    except Exception as e:
        print(f"[transfer_confirm] Error: {e}")
        await callback_query.message.edit_text("❌ Transfer failed!")


@app.on_callback_query(filters.regex(r"^transfer_cancel$"))
async def transfer_cancel_callback(client, callback_query):
    if callback_query.from_user.id not in OWNER_IDS:
        await callback_query.answer("⚠️ Owners only!", show_alert=True)
        return
    await callback_query.message.edit_text("🚫 Transfer cancelled.")


# ─────────────────────────────────────────────
# Top Collectors
# ─────────────────────────────────────────────

@app.on_message(filters.command("top"))
async def top_users(client, message):
    try:
        all_users = await user_collection.find(
            {"characters": {"$exists": True, "$ne": []}}
        ).to_list(length=100)

        if not all_users:
            await message.reply_text("📊 No users with collections found yet!")
            return

        user_scores = []
        for u in all_users:
            chars = u.get('characters', [])
            total = len(chars)
            unique = len(set(c.get('id') for c in chars))
            user_scores.append({
                'user_id': u['id'],
                'total': total,
                'unique': unique,
                'score': total + unique * 0.5
            })

        user_scores.sort(key=lambda x: x['score'], reverse=True)

        top_text = "🏆 **ᴛᴏᴘ ᴄᴏʟʟᴇᴄᴛᴏʀs** 🏆\n\n"
        for i, ud in enumerate(user_scores[:10], 1):
            try:
                info = await client.get_users(ud['user_id'])
                name = info.first_name
            except Exception:
                name = f"User {ud['user_id']}"
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            top_text += f"{medal} {escape(name)}\n   📦 Total: {ud['total']} | ✨ Unique: {ud['unique']}\n\n"

        await message.reply_text(top_text, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        print(f"[top_users] Error: {e}")
        await message.reply_text("❌ An error occurred while fetching top users.")


# ─────────────────────────────────────────────
# Debug Helper
# ─────────────────────────────────────────────

@app.on_message(filters.command("checkjoin") & filters.user(ADMIN_IDS))
async def checkjoin_cmd(client, message):
    user_id = message.from_user.id
    out = []
    for chat in (SUPPORT_GROUP, SUPPORT_CHANNEL):
        try:
            member = await client.get_chat_member(chat, user_id)
            out.append(f"{chat}: ✅ OK — status={getattr(member, 'status', 'unknown')}")
        except UserNotParticipant:
            out.append(f"{chat}: ❌ NOT A MEMBER")
        except Exception as e:
            out.append(f"{chat}: ⚠️ ERROR — {type(e).__name__}: {e}")
    await message.reply_text("CheckJoin results:\n\n" + "\n".join(out))
