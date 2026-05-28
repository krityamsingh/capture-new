"""
Grabber/modules/bal.py
──────────────────────
Upgraded /bal command module for Pyrogram bots.

Features:
  • Rich formatted balance card with net worth calculation
  • Leaderboard rank display
  • Admin override (admins can check anyone's balance)
  • Optional membership gate (toggle via REQUIRE_MEMBERSHIP)
  • In-memory TTL cache to reduce DB hits
  • Graceful fallbacks for every failure path
  • Full type hints and docstrings
"""

from __future__ import annotations

import time
from typing import Optional

from pyrogram import filters
from pyrogram.errors import UserNotParticipant, RPCError
from pyrogram.types import (
    Message,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# ── Imports ────────────────────────────────────────────────────────────────── #
# Auto-detect which module holds user_collection (motor/MongoDB collections).
# Tries the most common naming conventions used in Pyrogram bots.
user_collection = None
_DB_CANDIDATES = [
    "Grabber.database",   # Grabber/database.py
    "Grabber.db",         # Grabber/db.py
    "Grabber.mongo",      # Grabber/mongo.py
    "Grabber.utils.db",   # Grabber/utils/db.py
    "Grabber",            # Grabber/__init__.py
]
for _mod_path in _DB_CANDIDATES:
    try:
        import importlib as _il
        _mod = _il.import_module(_mod_path)
        if hasattr(_mod, "user_collection"):
            user_collection = _mod.user_collection
            break
    except ImportError:
        continue

if user_collection is None:
    raise RuntimeError(
        "Could not find 'user_collection' in any of these modules:\n"
        + "\n".join(f"  • {m}" for m in _DB_CANDIDATES)
        + "\nAdd your actual DB module path to _DB_CANDIDATES in bal.py."
    )

# Import the Pyrogram client (app)
app = None
for _app_path, _app_attr in [
    ("Grabber",      "app"),
    ("Grabber.main", "app"),
    ("Grabber.bot",  "app"),
]:
    try:
        import importlib as _il
        _mod = _il.import_module(_app_path)
        if hasattr(_mod, _app_attr):
            app = getattr(_mod, _app_attr)
            break
    except ImportError:
        continue

if app is None:
    raise RuntimeError(
        "Could not find Pyrogram 'app' (Client) in Grabber, Grabber.main, or Grabber.bot.\n"
        "Add the correct module path to the app import block in bal.py."
    )

# ── Configuration ──────────────────────────────────────────────────────────── #
SUPPORT_GROUP    = "divine_catchers"
SUPPORT_CHANNEL  = "IndianHelpIine"
REQUIRE_MEMBERSHIP = True          # Set False to disable the join gate entirely
CACHE_TTL        = 30              # Seconds to cache balance data per user
BOT_ADMINS: set[int] = set()       # Add admin user IDs: {123456789, 987654321}
CURRENCY_SYMBOL  = "🪙"

# ── Simple TTL Cache ───────────────────────────────────────────────────────── #
_cache: dict[int, tuple[float, dict]] = {}

def _cache_get(user_id: int) -> Optional[dict]:
    entry = _cache.get(user_id)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    _cache.pop(user_id, None)
    return None

def _cache_set(user_id: int, data: dict) -> None:
    _cache[user_id] = (time.time(), data)

def _cache_clear(user_id: int) -> None:
    _cache.pop(user_id, None)

# ── Helpers ────────────────────────────────────────────────────────────────── #
def _join_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Support Group",   url=f"https://t.me/{SUPPORT_GROUP}")],
        [InlineKeyboardButton("📢 Update Channel",  url=f"https://t.me/{SUPPORT_CHANNEL}")],
    ])

def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def _fmt(n: int) -> str:
    """Format large numbers with commas, e.g. 1234567 → 1,234,567."""
    return f"{n:,}"

def _net_worth(balance: int, saved: int, loan: int) -> int:
    return balance + saved - loan

def _rank_emoji(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "🏅")

async def _check_membership(user_id: int, client) -> bool:
    """Return True if user is in both support group and channel."""
    if not REQUIRE_MEMBERSHIP:
        return True
    try:
        await client.get_chat_member(SUPPORT_GROUP,   user_id)
        await client.get_chat_member(SUPPORT_CHANNEL, user_id)
        return True
    except (UserNotParticipant, RPCError):
        return False
    except Exception:
        return True   # Don't block user on unexpected errors

async def _get_rank(user_id: int) -> Optional[int]:
    """
    Fetch the user's leaderboard rank based on combined wealth
    (balance + saved_amount). Returns None if rank cannot be determined.
    Handles both 'id' and 'user_id' schema conventions.
    """
    try:
        pipeline = [
            {"$project": {
                "id":      1,
                "user_id": 1,
                "total": {"$add": [
                    {"$ifNull": ["$balance",      0]},
                    {"$ifNull": ["$saved_amount", 0]},
                ]},
            }},
            {"$sort": {"total": -1}},
        ]
        rank = 1
        uid = int(user_id)
        async for doc in user_collection.aggregate(pipeline):
            # Match against whichever field the document uses
            if doc.get("id") == uid or doc.get("user_id") == uid:
                return rank
            rank += 1
    except Exception:
        pass
    return None

async def _fetch_user_data(user_id: int) -> Optional[dict]:
    """
    Fetch balance data from cache or DB.
    Tries both 'id' and 'user_id' field names to handle different schema styles.
    """
    cached = _cache_get(user_id)
    if cached is not None:
        return cached

    projection = {
        "balance":      1,
        "saved_amount": 1,
        "loan_amount":  1,
        "custom_media": 1,
        "id":           1,
        "user_id":      1,
    }

    # Try 'id' first (common in many Pyrogram bots), then fall back to 'user_id'
    uid = int(user_id)
    data = await user_collection.find_one({"id": uid}, projection)
    if not data:
        data = await user_collection.find_one({"user_id": uid}, projection)

    if data:
        _cache_set(user_id, data)
    return data

def _build_message(target: User, data: dict, rank: Optional[int]) -> str:
    balance  = _to_int(data.get("balance",      0))
    saved    = _to_int(data.get("saved_amount", 0))
    loan     = _to_int(data.get("loan_amount",  0))
    net      = _net_worth(balance, saved, loan)
    mention  = f"[{target.first_name}](tg://user?id={target.id})"

    rank_line = ""
    if rank is not None:
        rank_line = f"\n{_rank_emoji(rank)} **Rank:** `#{rank}`"

    loan_line = f"\n💸 **Loan Pending:** `{_fmt(loan)}`" if loan > 0 else ""

    net_color = "📈" if net >= 0 else "📉"

    return (
        f"╔══════════════════════╗\n"
        f"       {CURRENCY_SYMBOL} **Balance Card** {CURRENCY_SYMBOL}\n"
        f"╚══════════════════════╝\n\n"
        f"👤 **User:** {mention}"
        f"{rank_line}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💰 **Wallet:**  `{_fmt(balance)}`\n"
        f"🏦 **Bank:**    `{_fmt(saved)}`"
        f"{loan_line}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{net_color} **Net Worth:** `{_fmt(net)}`\n"
        f"━━━━━━━━━━━━━━━━━"
    )

async def _send_with_media(message: Message, client, target: User, text: str, custom_media: Optional[dict]):
    """Try custom media → profile photo → plain text (in that order)."""
    # 1. Custom media
    if custom_media:
        mid  = custom_media.get("id")
        mtype = custom_media.get("type")
        try:
            if mtype == "photo":
                return await message.reply_photo(photo=mid, caption=text)
            elif mtype == "video":
                return await message.reply_video(video=mid, caption=text)
            elif mtype == "animation":
                return await message.reply_animation(animation=mid, caption=text)
        except Exception:
            pass  # Fall through to next option

    # 2. Profile photo
    try:
        async for photo in client.get_chat_photos(target.id, limit=1):
            return await message.reply_photo(photo=photo.file_id, caption=text)
    except Exception:
        pass

    # 3. Plain text fallback
    return await message.reply_text(text, disable_web_page_preview=True)

# ── Command Handler ────────────────────────────────────────────────────────── #
@app.on_message(filters.command("bal"))
async def balance(client, message: Message):
    """
    /bal          — Check your own balance
    /bal (reply)  — Check the replied user's balance
    Admins can always check anyone's balance regardless of membership.
    """
    invoker: Optional[User] = message.from_user
    if not invoker:
        return await message.reply_text("⚠️ Unable to identify you. Please try again.")

    is_admin = invoker.id in BOT_ADMINS

    # ── Membership gate (skip for admins) ─────────────────────────────────── #
    if not is_admin and not await _check_membership(invoker.id, client):
        return await message.reply_text(
            "❌ **Access Denied**\n\n"
            "You must join both our support group and update channel to use this command.",
            reply_markup=_join_buttons(),
        )

    # ── Resolve target ─────────────────────────────────────────────────────── #
    replied = message.reply_to_message
    if replied and replied.from_user:
        target: User = replied.from_user
        # Non-admins cannot look up others if membership gate is on
        if not is_admin and REQUIRE_MEMBERSHIP and target.id != invoker.id:
            if not await _check_membership(target.id, client):
                return await message.reply_text(
                    "⚠️ That user hasn't joined the required group/channel yet."
                )
    else:
        target = invoker

    mention = f"[{target.first_name}](tg://user?id={target.id})"

    # ── Fetch data ─────────────────────────────────────────────────────────── #
    user_data = await _fetch_user_data(target.id)
    if not user_data:
        return await message.reply_text(
            f"❌ {mention} doesn't have an account yet.\n"
            "They need to interact with the bot first to register."
        )

    # ── Build & send ───────────────────────────────────────────────────────── #
    rank = await _get_rank(target.id)
    text = _build_message(target, user_data, rank)
    await _send_with_media(message, client, target, text, user_data.get("custom_media"))


# ── Admin: force-refresh cache ─────────────────────────────────────────────── #
@app.on_message(filters.command("balrefresh") & filters.user(list(BOT_ADMINS)))
async def refresh_balance_cache(client, message: Message):
    """Admin command: /balrefresh — clears balance cache for replied user."""
    replied = message.reply_to_message
    if not replied or not replied.from_user:
        return await message.reply_text("⚠️ Reply to a user to refresh their balance cache.")
    uid = replied.from_user.id
    _cache_clear(uid)
    await message.reply_text(f"✅ Balance cache cleared for user `{uid}`.")
