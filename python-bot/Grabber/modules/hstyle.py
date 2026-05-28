import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
from . import user_collection, capsify, app

# Available Harem Styles
HAREM_STYLES = {
    1: "➤ {anime} ﴾{index}/{total}﴿\n⤷〔{rarity}〕 {id} {name} ×{count}",
    2: "⧉ {anime} ⦋{index}/{total}⦌\n⤷〔{rarity}〕 {id} {name} ×{count}",
    3: ":⧽ {anime} 「{index}/{total}」\n⦿ 〔{rarity}〕 {id} {name} ×{count}",
    4: "🈴 {anime} 「{index}/{total}」\nID: {id} 〔{rarity}〕 {name} ×{count}",
    5: "⌬ {anime} 〔{index}/{total}〕\n◈⌠{rarity}⌡ {id} {name} ×{count}",
    6: "⥱ {anime} {index}/{total}\n➥ {id} | {rarity} | {name} ×{count}",
    7: "⌬ {anime} 〔{index}/{total}〕\n𝐈𝐃 : {id} ⌠ {rarity} ⌡ {name} ×{count}",
    8: "🍁 Name: {name} (x{count})\n{rarity} Rarity: {rarity_name}\n🍀 Anime: {anime} ({index}/{total})",
    9: "❂ {anime} ❘ {index}/{total}\n**⌲ {rarity} ❘ {id} ❘ {name} ×{count}**",
    10: "⭑ {anime} ╽ {index}/{total}\n**┊ {rarity} ╽ {id} ╽ {name} ×{count}**"
}

async def update_hstyle_message(bot_message, page, user_id, confirm=False):
    """Edit bot's message with new harem style selection."""
    total_styles = len(HAREM_STYLES)
    if page < 1 or page > total_styles:
        page = 1  

    if confirm:
        hstyle_message = capsify(f"✅ **Harem Style Set Successfully!**\n\n**Your Selected Style Number: {page}**")
        keyboard = [[IKB("❌ Close", callback_data="hstyle:close")]]
    else:
        # Default rarity name
        rarity_name = "Epic"

        # Format harem style
        try:
            style_preview = HAREM_STYLES[page].format(
                anime="Chainsaw Man",
                index=3,
                total=63,
                rarity="🟣",
                id="2148",
                name="Darkness Devil",
                count=1,
                rarity_name=rarity_name  # ✅ Fix: Added rarity_name
            )
        except KeyError:
            style_preview = "❌ Error: Invalid harem style format!"

        hstyle_message = capsify(f"Your Selected Style Number: {page}\n\n{style_preview}")

        keyboard = [
            [
                IKB("⬅️ Previous", callback_data=f"hstyle:{page - 1}") if page > 1 else IKB(" ", callback_data="noop"),
                IKB(f"{page}/{total_styles}", callback_data="noop"),
                IKB("Next ➡️", callback_data=f"hstyle:{page + 1}") if page < total_styles else IKB(" ", callback_data="noop")
            ],
            [IKB("✅ Set Style", callback_data=f"hstyle:set:{page}:{user_id}")],
            [IKB("❌ Close", callback_data="hstyle:close")]
        ]

    markup = IKM(keyboard)

    # ✅ Fix: Only Edit if Content is Different
    if bot_message.text != hstyle_message:
        await bot_message.edit_text(hstyle_message, reply_markup=markup)

@app.on_message(filters.command("hstyle"))
async def hstyle(client, message):
    """Send initial harem style selection message."""
    user_id = message.from_user.id

    # Send new message first (so bot owns it)
    bot_message = await message.reply_text("Loading harem styles...")

    # Now edit it with actual content
    await update_hstyle_message(bot_message, 1, user_id)

@app.on_callback_query(filters.regex(r"hstyle:"))
async def hstyle_callback(client, callback_query):
    """Handle harem style pagination and setting."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    bot_message = callback_query.message  # Now bot owns this message

    if data == "hstyle:close":
        await bot_message.delete()
        return

    if data.startswith("hstyle:set"):
        _, _, style_num, _ = data.split(":")
        style_num = int(style_num)

        await user_collection.update_one({'id': user_id}, {'$set': {'hstyle': style_num}}, upsert=True)
        await callback_query.answer("✅ Harem style updated!", show_alert=True)

        # ✅ Show Confirmation Message
        await update_hstyle_message(bot_message, style_num, user_id, confirm=True)
        return

    _, page = data.split(":")
    await update_hstyle_message(bot_message, int(page), user_id)
