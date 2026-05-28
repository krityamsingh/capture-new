from pyrogram import Client, filters
from pyrogram.types import Message
from Grabber import (
    collection,
    user_collection,
    group_user_totals_collection,
)
from . import sudo_filter, app

# Rarity list with emojis
rarity_order = [
    "🔴 Common", "🔵 Uncommon", "🟠 Rare", "⚪ Epic", "🟡 Legendary",
    "🔮 Limited Edition", "🫧 Premium", "🏵️ Exotic",
    "⚜️ Animated", "🌼 Celebrity", "🎐 Crystal", "🍹 Neon", "🧿 Supreme",
    "⚡ Thundra", "🛸 Galvoria"
]

# /db command for sudo users
@app.on_message(filters.command("db") & sudo_filter)
async def db_stats(client: Client, message: Message):
    total_users = await user_collection.count_documents({})
    group_ids = await group_user_totals_collection.distinct("group_id")
    total_groups = len(group_ids)
    total_waifus = await collection.count_documents({})
    total_animes = await collection.distinct("anime")
    total_characters = total_waifus

    # Count each rarity
    rarity_counts = {
        rarity: await collection.count_documents({"rarity": rarity}) for rarity in rarity_order
    }
    highest_rarity = max(rarity_counts, key=rarity_counts.get, default="Unknown")
    lowest_rarity = min(rarity_counts, key=rarity_counts.get, default="Unknown")

    # Format rarity line by line
    rarity_lines = "\n".join(
        [f"{rarity} `{count}`" for rarity, count in rarity_counts.items() if count > 0]
    )

    db_text = (
        "╭━━━〔 ᴅʙ ꜱᴛᴀᴛꜱ 〕━━━╮\n"
        f"┣⪼ ᴜꜱᴇʀꜱ : `{total_users}` \n"
        f"┣⪼ ɢʀᴏᴜᴘꜱ : `{total_groups}`\n"
        f"┣⪼ ᴡᴀɪꜰᴜꜱ : `{total_waifus}`\n"
        f"┣⪼ ᴀɴɪᴍᴇꜱ : `{len(total_animes)}`\n"
        f"┣⪼ ᴄʜᴀʀᴀᴄᴛᴇʀꜱ : `{total_characters}`\n"
        "┣━━━〔 ʀᴀʀɪᴛʏ ꜱᴛᴀᴛꜱ 〕━━━┫\n"
        f"{rarity_lines}\n"
        "┣━━━〔 ᴍɪꜱᴄ 〕━━━┫\n"
        f"┣⪼ ʜɪɢʜᴇꜱᴛ : `{highest_rarity}`\n"
        f"┣⪼ ʟᴏᴡᴇꜱᴛ : `{lowest_rarity}`\n"
        "╰━━━━━━━━━━━━━━━╯"
    )

    await message.reply_text(db_text)
