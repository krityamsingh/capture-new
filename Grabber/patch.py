import os
import aiohttp
import tempfile
from pyrogram import Client
from pyrogram.errors import WebpageMediaEmpty, WebpageCurlFailed, MediaEmpty, BadRequest
from pyrogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation

FALLBACK_IMG = "https://telegra.ph/file/lost-character-placeholder.jpg"

async def download_to_temp(url: str):
    if not isinstance(url, str) or not url.startswith("http"):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    suffix = ".jpg"
                    if ".mp4" in url or ".mov" in url or ".mkv" in url or ".gif" in url:
                        suffix = ".mp4"
                    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                    tmp.write(data)
                    tmp.close()
                    return tmp.name
    except Exception:
        pass
    return None

def safe_delete(path):
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass

# Patch send_photo
original_send_photo = Client.send_photo
async def patched_send_photo(self, chat_id, photo, *args, **kwargs):
    if isinstance(photo, str) and photo.startswith("http"):
        try:
            return await original_send_photo(self, chat_id, photo, *args, **kwargs)
        except (WebpageMediaEmpty, WebpageCurlFailed, MediaEmpty, BadRequest) as e:
            if isinstance(e, BadRequest) and not any(k in str(e) for k in ("WEBPAGE", "MEDIA", "CURL", "PHOTO_INVALID")):
                raise
            tmp_path = await download_to_temp(photo)
            if tmp_path:
                try:
                    with open(tmp_path, "rb") as fh:
                        return await original_send_photo(self, chat_id, fh, *args, **kwargs)
                except Exception:
                    pass
                finally:
                    safe_delete(tmp_path)
            try:
                return await original_send_photo(self, chat_id, FALLBACK_IMG, *args, **kwargs)
            except Exception:
                raise e
    return await original_send_photo(self, chat_id, photo, *args, **kwargs)

Client.send_photo = patched_send_photo

# Patch send_video
original_send_video = Client.send_video
async def patched_send_video(self, chat_id, video, *args, **kwargs):
    if isinstance(video, str) and video.startswith("http"):
        try:
            return await original_send_video(self, chat_id, video, *args, **kwargs)
        except (WebpageMediaEmpty, WebpageCurlFailed, MediaEmpty, BadRequest) as e:
            if isinstance(e, BadRequest) and not any(k in str(e) for k in ("WEBPAGE", "MEDIA", "CURL", "VIDEO_INVALID")):
                raise
            tmp_path = await download_to_temp(video)
            if tmp_path:
                try:
                    with open(tmp_path, "rb") as fh:
                        return await original_send_video(self, chat_id, fh, *args, **kwargs)
                except Exception:
                    pass
                finally:
                    safe_delete(tmp_path)
            try:
                return await original_send_photo(self, chat_id, FALLBACK_IMG, *args, **kwargs)
            except Exception:
                raise e
    return await original_send_video(self, chat_id, video, *args, **kwargs)

Client.send_video = patched_send_video

# Patch send_animation
original_send_animation = Client.send_animation
async def patched_send_animation(self, chat_id, animation, *args, **kwargs):
    if isinstance(animation, str) and animation.startswith("http"):
        try:
            return await original_send_animation(self, chat_id, animation, *args, **kwargs)
        except (WebpageMediaEmpty, WebpageCurlFailed, MediaEmpty, BadRequest) as e:
            if isinstance(e, BadRequest) and not any(k in str(e) for k in ("WEBPAGE", "MEDIA", "CURL", "ANIMATION_INVALID")):
                raise
            tmp_path = await download_to_temp(animation)
            if tmp_path:
                try:
                    with open(tmp_path, "rb") as fh:
                        return await original_send_animation(self, chat_id, fh, *args, **kwargs)
                except Exception:
                    pass
                finally:
                    safe_delete(tmp_path)
            try:
                return await original_send_photo(self, chat_id, FALLBACK_IMG, *args, **kwargs)
            except Exception:
                raise e
    return await original_send_animation(self, chat_id, animation, *args, **kwargs)

Client.send_animation = patched_send_animation

# Patch send_media_group
original_send_media_group = Client.send_media_group
async def patched_send_media_group(self, chat_id, media, *args, **kwargs):
    tmp_paths = []
    new_media = []
    try:
        for item in media:
            media_val = item.media
            if isinstance(media_val, str) and media_val.startswith("http"):
                tmp_path = await download_to_temp(media_val)
                if tmp_path:
                    tmp_paths.append(tmp_path)
                    fh = open(tmp_path, "rb")
                    item.media = fh
            new_media.append(item)
        return await original_send_media_group(self, chat_id, new_media, *args, **kwargs)
    except Exception as e:
        raise e
    finally:
        for item in new_media:
            if hasattr(item.media, "close"):
                try:
                    item.media.close()
                except Exception:
                    pass
        for path in tmp_paths:
            safe_delete(path)

Client.send_media_group = patched_send_media_group
