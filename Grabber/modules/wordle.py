import asyncio
import random
import logging
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


_EMOJI = {"green": "🟩", "yellow": "🟨", "gray": "⬛"}
_LETTER_EMOJI = {
    c: chr(0x1F1E6 + ord(c) - ord('A')) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
}


def _render_game(game: dict, reveal_word: bool = False) -> str:
    word    = game["word"]
    guesses = game["guesses"]
    lines   = []

    # Title
    left = MAX_GUESSES - len(guesses)
    lines.append(f"**🔤 WORDLE** — {len(guesses)}/{MAX_GUESSES} guesses")
    lines.append("")

    # All guesses so far
    for g in guesses:
        scores = _score_guess(g, word)
        emoji_row  = "".join(_EMOJI[s] for s in scores)
        letter_row = "  ".join(_LETTER_EMOJI[c] for c in g)
        lines.append(emoji_row)
        lines.append(letter_row)
        lines.append("")

    # Empty rows
    for _ in range(MAX_GUESSES - len(guesses)):
        lines.append("⬜⬜⬜⬜⬜")
        lines.append("\u2003\u2003\u2003\u2003\u2003")  # em spaces placeholder
        lines.append("")

    # Keyboard tracker
    used_green  = set()
    used_yellow = set()
    used_gray   = set()
    for g in guesses:
        scores = _score_guess(g, word)
        for ch, sc in zip(g, scores):
            if sc == "green":  used_green.add(ch)
            elif sc == "yellow": used_yellow.add(ch)
            else: used_gray.add(ch)

    rows_kb = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
    kb_lines = []
    for row in rows_kb:
        r = []
        for ch in row:
            if ch in used_green:   r.append("🟩")
            elif ch in used_yellow: r.append("🟨")
            elif ch in used_gray:   r.append("⬛")
            else:                   r.append("⬜")
        kb_lines.append("".join(r))
    lines.append("**Keyboard:**")
    lines += kb_lines

    if reveal_word:
        lines.append(f"\n🔑 The word was: **{word}**")

    return "\n".join(lines)


# ── /wordle ───────────────────────────────────────────────────────────────────
@app.on_message(filters.command("wordle"))
async def wordle_cmd(client, m: Message):
    chat_id = m.chat.id
    if chat_id in _wordle_games:
        # Already running — show current board
        game = _wordle_games[chat_id]
        await m.reply(_render_game(game) + "\n\n_Type a 5-letter word to guess!_")
        return

    word = random.choice(WORD_LIST)
    _wordle_games[chat_id] = {
        "word":        word,
        "guesses":     [],
        "started_by":  m.from_user.id if m.from_user else 0,
        "chat_id":     chat_id,
    }
    game = _wordle_games[chat_id]
    await m.reply(
        _render_game(game)
        + "\n\n🎮 **Game started!** Type any 5-letter word to guess."
        + "\n💡 🟩 correct · 🟨 wrong spot · ⬛ not in word"
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
        board = _render_game(game)
        await m.reply(
            board
            + f"\n\n🎉 **{name}** solved it in {guesses_used} guess{'es' if guesses_used > 1 else ''}!"
            + f"\n🔑 Word: **{word}**"
            + f"\n💎 +{ruby:,} Ruby"
            + "\n\n▶️ Type /wordle to play again!"
        )
    elif lost:
        del _wordle_games[chat_id]
        board = _render_game(game, reveal_word=True)
        await m.reply(
            board
            + f"\n\n😔 No one guessed it! The word was **{word}**."
            + "\n▶️ Type /wordle to play again!"
        )
    else:
        board = _render_game(game)
        remaining = MAX_GUESSES - len(game["guesses"])
        await m.reply(
            board
            + f"\n\n🎯 {remaining} guess{'es' if remaining > 1 else ''} remaining — keep going!"
        )


# ── /wordlestop ───────────────────────────────────────────────────────────────
@app.on_message(filters.command("wordlestop") & sudo_filter)
async def wordle_stop_cmd(_, m: Message):
    chat_id = m.chat.id
    game = _wordle_games.pop(chat_id, None)
    if game:
        await m.reply(f"🛑 Wordle stopped. The word was **{game['word']}**.")
    else:
        await m.reply("No active Wordle game here.")
