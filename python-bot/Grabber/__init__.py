import aiohttp
import tempfile
import os
from pyrogram import Client as PyrogramClient
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from resolve_peer import ResolvePeer
from .config import *
from datetime import datetime

bot_start_time = datetime.now()


async def _download_url_to_temp(url: str, suffix: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} fetching {url}")
            data = await resp.read()

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
    finally:
        tmp.close()
    return tmp.name


class Client(PyrogramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def resolve_peer(self, id):
        obj = ResolvePeer(self)
        return await obj.resolve_peer(id)

    async def send_photo(self, chat_id, photo, *args, **kwargs):
        if isinstance(photo, str) and photo.startswith(("http://", "https://")):
            tmp_path = None
            try:
                ext = ".jpg"
                if ".png" in photo.lower():
                    ext = ".png"
                elif ".gif" in photo.lower():
                    ext = ".gif"
                tmp_path = await _download_url_to_temp(photo, ext)
                with open(tmp_path, "rb") as fh:
                    return await super().send_photo(chat_id, fh, *args, **kwargs)
            except Exception as e:
                print(f"[Client.send_photo] URL download failed ({photo}): {e}")
                return await super().send_photo(chat_id, photo, *args, **kwargs)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        else:
            return await super().send_photo(chat_id, photo, *args, **kwargs)

    async def send_video(self, chat_id, video, *args, **kwargs):
        if isinstance(video, str) and video.startswith(("http://", "https://")):
            tmp_path = None
            try:
                ext = ".mp4"
                if ".webm" in video.lower():
                    ext = ".webm"
                tmp_path = await _download_url_to_temp(video, ext)
                with open(tmp_path, "rb") as fh:
                    return await super().send_video(chat_id, fh, *args, **kwargs)
            except Exception as e:
                print(f"[Client.send_video] URL download failed ({video}): {e}")
                return await super().send_video(chat_id, video, *args, **kwargs)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        else:
            return await super().send_video(chat_id, video, *args, **kwargs)

    async def send_animation(self, chat_id, animation, *args, **kwargs):
        if isinstance(animation, str) and animation.startswith(("http://", "https://")):
            tmp_path = None
            try:
                ext = ".gif"
                if ".mp4" in animation.lower():
                    ext = ".mp4"
                tmp_path = await _download_url_to_temp(animation, ext)
                with open(tmp_path, "rb") as fh:
                    return await super().send_animation(chat_id, fh, *args, **kwargs)
            except Exception as e:
                print(f"[Client.send_animation] URL download failed ({animation}): {e}")
                return await super().send_animation(chat_id, animation, *args, **kwargs)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        else:
            return await super().send_animation(chat_id, animation, *args, **kwargs)

    async def edit_message_media(self, chat_id, message_id, media, *args, **kwargs):
        from pyrogram.types import InputMediaVideo, InputMediaPhoto
        
        target_url = None
        if hasattr(media, "media") and isinstance(media.media, str) and media.media.startswith(("http://", "https://")):
            target_url = media.media
            
        if target_url:
            tmp_path = None
            try:
                ext = ".jpg"
                if isinstance(media, InputMediaVideo):
                    ext = ".mp4"
                elif isinstance(media, InputMediaPhoto):
                    if ".png" in target_url.lower():
                        ext = ".png"
                    elif ".gif" in target_url.lower():
                        ext = ".gif"
                
                tmp_path = await _download_url_to_temp(target_url, ext)
                fh = open(tmp_path, "rb")
                media.media = fh
                try:
                    return await super().edit_message_media(chat_id, message_id, media, *args, **kwargs)
                finally:
                    fh.close()
            except Exception as e:
                print(f"[Client.edit_message_media] URL download failed ({target_url}): {e}")
                media.media = target_url
                return await super().edit_message_media(chat_id, message_id, media, *args, **kwargs)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        else:
            return await super().edit_message_media(chat_id, message_id, media, *args, **kwargs)


# --- Clients are built lazily inside main() to share one event loop ---
# __main__.py calls init_clients() before importing modules
application = None
Grabberu = None
app = None

# DB collections — populated by init_clients()
client = None
db = None
collection = None
user_totals_collection = None
user_collection = None
joke_collection = None
safari_cooldown_collection = None
safari_users_collection = None
group_user_totals_collection = None
top_global_groups_collection = None
guild = None
gban = None
clan_collection = None
join_requests_collection = None
global_ban_users_collection = None
users_collection = None
videos_collection = None
sales_collection = None
blocked_users_collection = None
like_dislike_collection = None
user_votes_collection = None
add_coins = None
add_character = None
get_user_data = None
add = None
store_items = None
check_vip_status = None
auction = None
global_mute_users_collection = None
monster_collection = None
action_history_collection = None
gang_collection = None
mission_collection = None
chain_collection = None
word_collection = None
fsub_collection = None
chat_auctions = None
active_auctions = None
backup_collection = None
clan_war_collection = None
giveaway_collection = None


def init_clients():
    """Call this inside asyncio.run() BEFORE importing any modules."""
    import Grabber as _self

    _self.application = Application.builder().token(TOKEN).build()

    _self.Grabberu = Client(
        "Grabber",
        api_id=api_id,
        api_hash=api_hash,
        bot_token=TOKEN,
    )
    _self.app = _self.Grabberu

    _self.client = AsyncIOMotorClient(MONGO_URL)
    _db = _self.client["Character_catcher"]
    _self.db = _db

    _self.collection                  = _db["anime_characters"]
    _self.user_totals_collection      = _db["user_totals"]
    _self.user_collection             = _db["user_collection"]
    _self.joke_collection             = _db["joke_collection"]
    _self.safari_cooldown_collection  = _db["safari_cooldown_collection"]
    _self.safari_users_collection     = _db["safari_users_collection"]
    _self.group_user_totals_collection= _db["group_user_total"]
    _self.top_global_groups_collection= _db["top_global_groups"]
    _self.guild                       = _db["guild_team"]
    _self.gban                        = _db["gban"]
    _self.clan_collection             = _db["clans"]
    _self.join_requests_collection    = _db["join_requests"]
    _self.global_ban_users_collection = _db["global_ban_users"]
    _self.users_collection            = _db["user"]
    _self.videos_collection           = _db["videos"]
    _self.sales_collection            = _db["sales"]
    _self.blocked_users_collection    = _db["blocked_users"]
    _self.like_dislike_collection     = _db["like_dislike_data"]
    _self.user_votes_collection       = _db["user_votes"]
    _self.add_coins                   = _db["add_coins"]
    _self.add_character               = _db["add_character"]
    _self.get_user_data               = _db["get_user_data"]
    _self.add                         = _db["add"]
    _self.store_items                 = _db["store_items"]
    _self.check_vip_status            = _db["check_vip_status"]
    _self.auction                     = _db["auction"]
    _self.global_mute_users_collection= _db["global_mute_users_collection"]
    _self.monster_collection          = _db["monster_collection"]
    _self.action_history_collection   = _db["action_history_collection"]
    _self.gang_collection             = _db["gang_collection"]
    _self.mission_collection          = _db["mission_collection"]
    _self.chain_collection            = _db["chain_collection"]
    _self.word_collection             = _db["words"]
    _self.fsub_collection             = _db["fsub_collection"]
    _self.chat_auctions               = _db["chat_auctions"]
    _self.active_auctions             = _db["active_auctions"]
    _self.backup_collection           = _db["backup_collection"]
    _self.clan_war_collection         = _db["clan_war_collection"]
    _self.giveaway_collection         = _db["giveaway_collection"]
