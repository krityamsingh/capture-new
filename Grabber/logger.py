"""
Grabber/logger.py
─────────────────────────────────────────────────────────────────────────────
Central logging setup for the entire bot.

Usage (in any module):
    from Grabber.logger import get_logger
    log = get_logger(__name__)

    log.info("Bot started")
    log.warning("Flood wait hit: %s", seconds)
    log.error("DB error for user %s: %s", user_id, exc)
    log.exception("Unexpected crash")   # logs traceback automatically

Telegram log-channel forwarding (uses LOG_CHAT_ID from config):
    from Grabber.logger import send_log
    await send_log("Something critical happened", level="ERROR")

What this replaces / fixes:
  • Every bare print() call scattered across spawn.py, smash.py, info.py, etc.
  • utils/error.py decorator that swallowed tracebacks silently
  • config.py defines LOG_CHAT_ID / JOINLOGS / LEAVELOGS but nothing ever used them
  • No timestamps, no log levels, no rotation — logs were impossible to read on Heroku
"""

import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Read from environment so you can tune verbosity without a redeploy
_LOG_LEVEL_NAME: str = os.environ.get("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL: int      = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)

# Whether to also write logs to a rotating file (useful locally, skip on Heroku)
_ENABLE_FILE_LOG: bool = os.environ.get("LOG_TO_FILE", "false").lower() == "true"
_LOG_FILE: str         = os.environ.get("LOG_FILE", "bot.log")
_LOG_MAX_BYTES: int    = 5 * 1024 * 1024   # 5 MB per file
_LOG_BACKUP_COUNT: int = 3                  # keep 3 rotated files

# Telegram log channel (set in config.py → LOG_CHAT_ID)
# Imported lazily inside send_log() to avoid circular imports at module load time.


# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════

_CONSOLE_FMT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_FILE_FMT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ══════════════════════════════════════════════════════════════════════════════
#  ROOT LOGGER  SETUP  (runs once at import time)
# ══════════════════════════════════════════════════════════════════════════════

def _setup_root_logger() -> None:
    root = logging.getLogger()
    root.setLevel(_LOG_LEVEL)

    # ── Console handler ────────────────────────────────────────────────────────
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(_LOG_LEVEL)
        console_handler.setFormatter(_CONSOLE_FMT)
        root.addHandler(console_handler)

    # ── Rotating file handler (optional) ───────────────────────────────────────
    if _ENABLE_FILE_LOG:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=_LOG_FILE,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(_LOG_LEVEL)
        file_handler.setFormatter(_FILE_FMT)
        root.addHandler(file_handler)

    # ── Silence noisy third-party loggers ─────────────────────────────────────
    for noisy in ("httpx", "httpcore", "aiohttp", "pyrogram", "telegram",
                  "apscheduler", "motor"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_setup_root_logger()


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  Call once at the top of each module:

        log = get_logger(__name__)
    """
    return logging.getLogger(name)


# ── Telegram channel forwarding ───────────────────────────────────────────────

async def send_log(
    text: str,
    level: str = "INFO",
    exc: BaseException | None = None,
) -> None:
    """
    Forward a log message to the Telegram log channel defined in config.py.
    Silently skips if the channel ID is not set or the bot isn't ready yet.

    Args:
        text:  Human-readable message.
        level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
        exc:   Optional exception — its traceback is appended automatically.
    """
    # Lazy imports to avoid circular dependency at startup
    try:
        from Grabber.config import LOG_CHAT_ID
        from Grabber import app
    except ImportError:
        return

    log_chat_id = int(LOG_CHAT_ID) if LOG_CHAT_ID else None
    if not log_chat_id:
        return

    level_emoji = {
        "DEBUG":    "🔍",
        "INFO":     "ℹ️",
        "WARNING":  "⚠️",
        "ERROR":    "❌",
        "CRITICAL": "🚨",
    }.get(level.upper(), "📋")

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    body      = f"{level_emoji} <b>[{level.upper()}]</b>  <code>{timestamp}</code>\n\n{text}"

    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        # Telegram message cap is 4096 chars; truncate if needed
        max_tb = 4096 - len(body) - 50
        if max_tb > 0:
            tb_trimmed = tb[-max_tb:] if len(tb) > max_tb else tb
            body += f"\n\n<pre>{tb_trimmed}</pre>"

    try:
        await app.send_message(
            chat_id=log_chat_id,
            text=body,
            parse_mode="html",
            disable_web_page_preview=True,
        )
    except Exception as send_err:
        # Never let log forwarding crash the bot
        _root_log.warning("Failed to forward log to Telegram: %s", send_err)


# ══════════════════════════════════════════════════════════════════════════════
#  DECORATOR  —  drop-in replacement for utils/error.py
# ══════════════════════════════════════════════════════════════════════════════

def catch_errors(func):
    """
    Decorator for Pyrogram and PTB handlers.
    Catches any unhandled exception, logs it with full traceback,
    optionally forwards it to the Telegram log channel, and replies
    to the user with a friendly error message instead of crashing.

    Usage:
        @app.on_message(filters.command("smash"))
        @catch_errors
        async def smash_command(client, message):
            ...
    """
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            # Always log locally first
            _root_log.exception(
                "Unhandled error in %s: %s", func.__qualname__, exc
            )

            # Forward to Telegram log channel (non-blocking, best-effort)
            try:
                import asyncio
                asyncio.create_task(
                    send_log(
                        f"Unhandled error in <code>{func.__qualname__}</code>",
                        level="ERROR",
                        exc=exc,
                    )
                )
            except Exception:
                pass

            # Try to reply to the user with a friendly message
            # Works for both Pyrogram (message) and PTB (update) style handlers
            message = None
            for arg in args:
                # Pyrogram: second arg is message
                if hasattr(arg, "reply_text"):
                    message = arg
                    break
                # PTB: first arg is Update
                if hasattr(arg, "message") and hasattr(arg.message, "reply_text"):
                    message = arg.message
                    break

            if message:
                try:
                    await message.reply_text(
                        "⚠️ An unexpected error occurred. Please try again.\n"
                        "If this keeps happening, contact support."
                    )
                except Exception:
                    pass

    return wrapper


# Module-level logger for use within this file
_root_log = get_logger(__name__)
_root_log.info(
    "Logger initialised  level=%s  file_log=%s",
    _LOG_LEVEL_NAME,
    _ENABLE_FILE_LOG,
)
