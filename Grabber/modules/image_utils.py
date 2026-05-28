import aiohttp
from pyrogram.errors import BadRequest

FALLBACK_IMG = "https://telegra.ph/file/lost-character-placeholder.jpg"
# Replace the above with any real fallback image URL you want shown
# when a character's image is broken.

async def is_image_valid(url: str) -> bool:
    """
    Return True only if the URL is reachable and returns HTTP 200.
    Uses HEAD first; falls back to GET if server rejects HEAD.
    Times out after 5 seconds.
    """
    if not url or not url.startswith("http"):
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status in (405, 403):
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as gresp:
                        return gresp.status == 200
                return False
    except Exception:
        return False


async def safe_send_photo(send_func, img_url: str, **kwargs):
    """
    Wrapper around any Pyrogram send_photo / reply_photo call.
    If Telegram raises WEBPAGE_CURL_FAILED (dead image), it retries
    with FALLBACK_IMG so the message still sends.

    Usage:
        await safe_send_photo(message.reply_photo, char["img_url"],
                              caption="...", reply_markup=markup)
    """
    try:
        return await send_func(img_url, **kwargs)
    except BadRequest as e:
        if "WEBPAGE_CURL_FAILED" in str(e) or "PHOTO_INVALID_DIMENSIONS" in str(e):
            return await send_func(FALLBACK_IMG, **kwargs)
        raise


async def safe_edit_media(message, img_url: str, reply_markup=None):
    """
    Wrapper around edit_message_media that falls back gracefully
    when the new image URL is broken.
    """
    from pyrogram.types import InputMediaPhoto
    try:
        return await message.edit_media(
            media=InputMediaPhoto(img_url),
            reply_markup=reply_markup
        )
    except BadRequest as e:
        if "WEBPAGE_CURL_FAILED" in str(e) or "PHOTO_INVALID_DIMENSIONS" in str(e):
            return await message.edit_media(
                media=InputMediaPhoto(FALLBACK_IMG),
                reply_markup=reply_markup
            )
        raise
