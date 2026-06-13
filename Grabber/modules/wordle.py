import asyncio
import random
import logging
import io
import os
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import Message
from . import app, sudo_filter, user_collection, aruby

log = logging.getLogger("Grabber.wordle")

# ── Word list ─────────────────────────────────────────────────────────────────
WORD_LIST = [
    "ANIME", "MAGIC", "SWORD", "BRAVE", "FLAME", "STORM", "DEMON", "ANGEL",
    "NIGHT", "LIGHT", "DREAM", "BLOOD", "CHASE", "DANCE", "EARTH", "FAITH",
    "GHOST", "HEART", "IDEAL", "JEWEL", "KARMA", "LANCE", "NOBLE", "OCEAN",
    "POWER", "QUEEN", "REALM", "SAINT", "TIGER", "UNITY", "VALOR", "WITCH",
    "YOUTH", "BLAZE", "CHAOS", "DELTA", "ELITE", "FROST", "GRACE", "HONOR",
    "IVORY", "LUNAR", "NEXUS", "OPTIC", "PIXEL", "QUILL", "RAVEN", "SMOKE",
    "THORN", "UMBRA", "VENOM", "WRATH", "ALPHA", "BRISK", "CRISP", "DRIFT",
    "EMBER", "FLARE", "GRAND", "HARSH", "INFER", "KNACK", "MARCH", "NERVE",
    "OUTDO", "PLUCK", "QUIRK", "RISKY", "SWIFT", "TAUNT", "USHER", "VIBES",
    "WALTZ", "YEARN", "BLINK", "CLOAK", "EXULT", "FLAIR", "GLOOM", "HAVEN",
    "IRONY", "JOLLY", "KNOCK", "LEAPT", "MAUVE", "OZONE", "RUPEE", "SHOAL",
    "TROVE", "DRAPE", "PRIVY", "JOUST", "KNEEL", "SCOUT", "RIVAL", "PRANK",
    "FLASH", "CREST", "SHRUB", "CRANE", "BLUFF", "DWARF", "SCORN", "GRIME",
]
WORD_LIST = [w for w in WORD_LIST if len(w) == 5]

# ── State ─────────────────────────────────────────────────────────────────────
_wordle_games: dict[int, dict] = {}
# game = {"word": str, "guesses": list[str], "started_by": int, "chat_id": int}

MAX_GUESSES = 6

# Ruby rewards by guesses used (index 0 = won on guess 1)
_RUBY_REWARDS = [250, 150, 100, 75, 50, 25]

# ── Grid renderer ─────────────────────────────────────────────────────────────
def _score_guess(guess: str, word: str) -> list[str]:
    """Return list of 5 results: 'green', 'yellow', 'gray'."""
    result = ["gray"] * 5
    word_letters = list(word)
    guess_letters = list(guess)

    # First pass: greens
    for i in range(5):
        if guess_letters[i] == word_letters[i]:
            result[i] = "green"
            word_letters[i] = None
            guess_letters[i] = None

    # Second pass: yellows
    for i in range(5):
        if guess_letters[i] is None:
            continue
        if guess_letters[i] in word_letters:
            result[i] = "yellow"
            word_letters[word_letters.index(guess_letters[i])] = None

    return result


async def _send_wordle_board(m: Message, game: dict, extra_text: str = ""):
    word = game["word"]
    guesses = game["guesses"]
    
    # Proportions
    cell_size = 100
    gap = 10
    padding = 15
    cols, rows = 5, 6
    
    width = 2 * padding + cols * cell_size + (cols - 1) * gap
    height = 2 * padding + rows * cell_size + (rows - 1) * gap
    
    # Create image
    img = Image.new("RGB", (width, height), color=(18, 18, 19))
    draw = ImageDraw.Draw(img)
    
    # Load font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf"
    
    try:
        font = ImageFont.truetype(font_path, 55)
    except Exception:
        font = ImageFont.load_default()
        
    for r in range(rows):
        has_guess = r < len(guesses)
        guess = guesses[r] if has_guess else None
        scores = _score_guess(guess, word) if has_guess else None
        
        for c in range(cols):
            x0 = padding + c * (cell_size + gap)
            y0 = padding + r * (cell_size + gap)
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            
            if has_guess:
                score = scores[c]
                if score == "green":
                    fill_color = (108, 169, 101)  # #6ca965
                elif score == "yellow":
                    fill_color = (201, 180, 88)   # #c9b458
                else:
                    fill_color = (120, 124, 126)  # #787c7e
                
                # Draw filled cell
                draw.rectangle([x0, y0, x1, y1], fill=fill_color)
                
                # Draw letter centered
                letter = guess[c]
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                draw.text((cx, cy), letter, fill=(255, 255, 255), font=font, anchor="mm")
            else:
                # Draw empty cell with border
                draw.rectangle([x0, y0, x1, y1], fill=(18, 18, 19), outline=(58, 58, 60), width=2)
                
    # Save to BytesIO
    photo_io = io.BytesIO()
    img.save(photo_io, "PNG")
    photo_io.seek(0)
    photo_io.name = "wordle.png"
    
    # Keyboard tracker
    used_green  = set()
    used_yellow = set()
    used_gray   = set()
    for g in guesses:
        g_scores = _score_guess(g, word)
        for ch, sc in zip(g, g_scores):
            if sc == "green":  used_green.add(ch)
            elif sc == "yellow": used_yellow.add(ch)
            else: used_gray.add(ch)

    rows_kb = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    kb_lines = []
    for row in rows_kb:
        r_kb = []
        for ch in row:
            if ch in used_green:   r_kb.append("🟩")
            elif ch in used_yellow: r_kb.append("🟨")
            elif ch in used_gray:   r_kb.append("⬛")
            else:                   r_kb.append("⬜")
        kb_lines.append("".join(r_kb))
        
    caption = f"**🔤 WORDLE** — {len(guesses)}/{MAX_GUESSES} guesses\n\n"
    caption += "**Keyboard:**\n" + "\n".join(kb_lines)
    if extra_text:
        caption += f"\n\n{extra_text}"
        
    await m.reply_photo(photo=photo_io, caption=caption)


# ── /wordle ───────────────────────────────────────────────────────────────────
@app.on_message(filters.command("wordle"))
async def wordle_cmd(client, m: Message):
    chat_id = m.chat.id
    if chat_id in _wordle_games:
        # Already running — show current board
        game = _wordle_games[chat_id]
        await _send_wordle_board(m, game, "_Type a 5-letter word to guess!_")
        return

    word = random.choice(WORD_LIST)
    _wordle_games[chat_id] = {
        "word":        word,
        "guesses":     [],
        "started_by":  m.from_user.id if m.from_user else 0,
        "chat_id":     chat_id,
    }
    game = _wordle_games[chat_id]
    await _send_wordle_board(
        m, game,
        "🎮 **Game started!** Type any 5-letter word to guess.\n💡 🟩 correct · 🟨 wrong spot · ⬛ not in word"
    )


# ── Guess listener ────────────────────────────────────────────────────────────
_not_cmd = filters.create(lambda _, __, m: bool(m.text and not m.text.strip().startswith("/")))

@app.on_message(filters.text & _not_cmd, group=5)
async def wordle_guess_listener(client, m: Message):
    chat_id = m.chat.id
    if chat_id not in _wordle_games:
        return
    if not m.from_user:
        return

    guess = m.text.strip().upper()
    if len(guess) != 5 or not guess.isalpha():
        return  # ignore non-5-letter messages silently

    from .wordle_words import WORDS
    if guess not in WORDS:
        await m.reply("⚠️ **Not in word list!** Try a valid English 5-letter word.")
        return

    game = _wordle_games[chat_id]
    word = game["word"]

    if guess in game["guesses"]:
        await m.reply(f"⚠️ You already guessed **{guess}**!")
        return

    game["guesses"].append(guess)
    scores = _score_guess(guess, word)
    won   = all(s == "green" for s in scores)
    lost  = not won and len(game["guesses"]) >= MAX_GUESSES

    if won:
        del _wordle_games[chat_id]
        guesses_used = len(game["guesses"])
        ruby = _RUBY_REWARDS[guesses_used - 1]
        uid  = m.from_user.id
        name = m.from_user.first_name or "Player"
        
        # Ensure user exists in Grabber db
        user_doc = await user_collection.find_one({'id': uid})
        if not user_doc:
            await user_collection.insert_one({
                'id': uid,
                'username': m.from_user.username or "",
                'first_name': name,
                'balance': '0',
                'rubies': '0',
                'gold': '0'
            })
            
        await aruby(uid, ruby)
        
        extra_text = (
            f"🎉 **{name}** solved it in {guesses_used} guess{'es' if guesses_used > 1 else ''}!\n"
            f"🔑 Word: **{word}**\n"
            f"💎 +{ruby:,} Ruby\n\n"
            f"▶️ Type /wordle to play again!"
        )
        await _send_wordle_board(m, game, extra_text)
    elif lost:
        del _wordle_games[chat_id]
        extra_text = (
            f"😔 No one guessed it! The word was **{word}**.\n"
            f"▶️ Type /wordle to play again!"
        )
        await _send_wordle_board(m, game, extra_text)
    else:
        remaining = MAX_GUESSES - len(game["guesses"])
        extra_text = f"🎯 {remaining} guess{'es' if remaining > 1 else ''} remaining — keep going!"
        await _send_wordle_board(m, game, extra_text)


# ── /wordlestop ───────────────────────────────────────────────────────────────
@app.on_message(filters.command("wordlestop") & sudo_filter)
async def wordle_stop_cmd(_, m: Message):
    chat_id = m.chat.id
    game = _wordle_games.pop(chat_id, None)
    if game:
        await m.reply(f"🛑 Wordle stopped. The word was **{game['word']}**.")
    else:
        await m.reply("No active Wordle game here.")
