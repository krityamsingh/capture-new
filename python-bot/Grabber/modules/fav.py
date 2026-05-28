from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import WebpageMediaEmpty, MediaEmpty, BadRequest
from . import app, user_collection


async def send_fav_media(message: Message, caption: str, keyboard: InlineKeyboardMarkup,
                          video_url: str, img_url: str):
    """
    Try video → photo → plain text (with URL appended).
    WEBPAGE_MEDIA_EMPTY means the URL stored in DB is not a direct media file
    (e.g. a Telegram post link or a webpage). We silently fall back
    instead of crashing with an error to the user.
    """

    # 1. Try video
    if video_url:
        try:
            await message.reply_video(
                video=video_url,
                caption=caption,
                reply_markup=keyboard,
                quote=False
            )
            return
        except (WebpageMediaEmpty, MediaEmpty, BadRequest):
            pass  # not a direct video URL — fall through

    # 2. Try photo
    if img_url:
        try:
            await message.reply_photo(
                photo=img_url,
                caption=caption,
                reply_markup=keyboard,
                quote=False
            )
            return
        except (WebpageMediaEmpty, MediaEmpty, BadRequest):
            pass  # not a direct image URL — fall through

    # 3. Final fallback: plain text + URLs as clickable links
    fallback_text = caption
    if video_url:
        fallback_text += f"\n\n🎬 [Video]({video_url})"
    elif img_url:
        fallback_text += f"\n\n🖼 [Image]({img_url})"

    await message.reply_text(
        fallback_text,
        reply_markup=keyboard,
        quote=False,
        disable_web_page_preview=True  # prevent Telegram re-trying to embed broken URL
    )


@app.on_message(filters.command("fav"))
async def fav(client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.reply_text("**Please provide Character ID...**")

    character_id = args[1]

    user = await user_collection.find_one({"id": user_id})

    if not user or "characters" not in user:
        return await message.reply_text("**You do not have any character yet...**")

    character = next(
        (c for c in user["characters"] if isinstance(c, dict) and str(c.get("id")) == character_id),
        None
    )
    if not character:
        return await message.reply_text("**This Character is Not In your Character list**")

    character_name = character.get("name", "Unknown Character")
    anime_name = character.get("anime", "Unknown Anime")
    rarity = character.get("rarity", "Unknown Rarity")
    img_url = character.get("img_url", "").strip()
    video_url = character.get("video_url", "").strip()

    caption = (
        f"» **Do you want to make this character your favorite?**\n\n"
        f"**Name:** {character_name}\n"
        f"**Anime:** {anime_name}\n"
        f"**Rarity:** {rarity}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"fav_yes_{user_id}_{character_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"fav_no_{user_id}_{character_id}")
        ]
    ])

    await send_fav_media(message, caption, keyboard, video_url, img_url)


@app.on_callback_query(filters.regex(r"^fav_(yes|no)_(\d+)_(\d+)$"))
async def fav_callback(client, query):
    parts = query.data.split("_")
    action = parts[1]
    user_id = int(parts[2])
    character_id = parts[3]

    if query.from_user.id != user_id:
        return await query.answer("❌ This is not for you!", show_alert=True)

    user = await user_collection.find_one({"id": user_id})
    if not user or "characters" not in user:
        return await query.answer("You do not have any character yet...", show_alert=True)

    character = next(
        (c for c in user["characters"] if isinstance(c, dict) and str(c.get("id")) == character_id),
        None
    )
    if not character:
        return await query.answer("This character is not in your list", show_alert=True)

    if action == "yes":
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"favorites": [character_id]}}
        )
        new_caption = f"✅ **{character['name']} has been added to your Favorites!**"
    else:
        new_caption = "❌ **Action has been cancelled.**"

    try:
        if query.message.caption is not None:
            await query.message.edit_caption(new_caption, reply_markup=None)
        else:
            await query.message.edit_text(new_caption, reply_markup=None)
        await query.answer()
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
