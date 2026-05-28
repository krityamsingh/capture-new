from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from . import app, dev_filter, sudo_filter, capsify, db, user_collection
from Grabber.config import OWNER_IDS 

sudb = db.sudo
devb = db.dev
uploaderdb = db.uploader

NEGLECTED_IDS = {}

# ─── Add any user IDs here to grant permanent sudo powers ───────────────────
HARDCODED_SUDO_IDS = {
    6118760915,  # Replace with real user IDs
    7976292835,
}
# ─────────────────────────────────────────────────────────────────────────────


async def is_sudo(user_id: int) -> bool:
    """Returns True if user has sudo access (hardcoded OR in database)."""
    if user_id in HARDCODED_SUDO_IDS:
        return True
    return bool(await sudb.find_one({'user_id': user_id}))


@app.on_message(filters.command("addsudo") & dev_filter)
async def add_sudo(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🚧 **Oh no!** Senpai, either reply to a user or provide a **valid user ID**, baka! 🎀"))

    if tar in NEGLECTED_IDS:
        return await message.reply_text(capsify(f"🚧 **Wait, what?!** `{first_name}` cannot be added to the sudo list, senpai! 🎀"))

    if tar in HARDCODED_SUDO_IDS:
        return await message.reply_text(capsify(f"☘️ **Ehh?** `{first_name}` already has **permanent sudo powers** (hardcoded), senpai~! 🎀"))

    if await sudb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"☘️ **Ehh?** `{first_name}` is already a sudo user! Are you teasing me, senpai? 🫧"))

    try:
        await sudb.insert_one({'user_id': tar})
        await message.reply_text(capsify(f"🚧 **Woohoo!** `{first_name}` is now a sudo user! Time to embrace the **protagonist energy**! 🎀"), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(" Remove Again ", callback_data=f"remove_sudo_{tar}")]
        ]))
    except Exception:
        await message.reply_text(capsify(f"**🎀 Oopsie!** Something went wrong while adding `{first_name}` to the sudo list. Try again, senpai!"))

@app.on_callback_query(filters.regex(r"remove_sudo_\d+"))
async def remove_sudo_callback(client, callback_query: CallbackQuery):
    tar = int(callback_query.data.split("_")[-1])

    if tar in HARDCODED_SUDO_IDS:
        return await callback_query.answer("🚧 This user has permanent sudo powers and cannot be removed!", show_alert=True)

    if not await sudb.find_one({'user_id': tar}):
        return await callback_query.answer("🚧 **Eh? This user isn't even on the sudo list, baka!**", show_alert=True)

    await sudb.delete_one({'user_id': tar})
    await callback_query.message.edit_text(capsify(f"🎀 **Aww `{tar}` is no longer a sudo user!** Senpai, you removed them~! 💔"))

@app.on_message(filters.command("rmsudo") & dev_filter)
async def remove_sudo(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🚧 **Oh no, senpai~!** You need to reply to a user or provide a **valid user ID**, baka~! 🎀"))

    if tar in HARDCODED_SUDO_IDS:
        return await message.reply_text(capsify(f"🚧 **Nice try, senpai~!** `{first_name}` has **permanent sudo powers** (hardcoded) and cannot be removed! 🎀"))

    if not await sudb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"🚧 **Ehh~?!** `{first_name}` is not even a sudo user, what are you trying to do, senpai~? 🎀"))

    try:
        await sudb.delete_one({'user_id': tar})
        await message.reply_text(capsify(f"🎀 **Aww~!** `{first_name}` has been **removed from the sudo list**! No more **hentai protagonist powers** for you~! 🚧"))
    except Exception:
        await message.reply_text(capsify(f"🚧 **Oopsie~!** Something went wrong while removing `{first_name}` from the sudo list. Try again, senpai~! 🎀"))

@app.on_message(filters.command("adddev") & (dev_filter | filters.user(tuple(OWNER_IDS))))
async def add_dev(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🚧 **Error Detected!** 🎀\nPlease **reply to a user** or provide a **valid user ID**, senpai~!"))

    if tar in NEGLECTED_IDS:
        return await message.reply_text(capsify(f"🚧 **Access Denied!** `{first_name}` cannot be added to the **dev list**, it's **forbidden territory**, senpai~! 🎀"))

    if await devb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"🎀 **Oops!** `{first_name}` is **already** a developer. Stop teasing me, senpai~! 🚧"))

    try:
        await devb.insert_one({'user_id': tar})
        await message.reply_text(capsify(f"🎀 **Congratulations, Senpai!** `{first_name}` is now a **Developer!** 🚧\nThey can now unleash their **big-brain powers** and help manage the bot~!"))
    except Exception:
        await message.reply_text(capsify(f"🚧 **System Error!** Could not add `{first_name}` to the **dev list**. Try again, senpai~! 🎀"))

@app.on_message(filters.command("rmdev") & dev_filter)
async def remove_dev(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🚧 **Invalid Command!** 🎀\nPlease **reply to a user** or provide a **valid ID**, senpai~!"))

    if tar == 7455169019:
        return await message.reply_text(capsify(f"🎀 **Error!** `{first_name}` cannot be removed. They are a **core developer**, senpai! 🚧"))

    if not await devb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"🚧 **Oops!** `{first_name}` is **not a developer**. Maybe you mistyped, senpai? 🎀"))

    try:
        await devb.delete_one({'user_id': tar})
        await message.reply_text(capsify(f"🚧 **Success!** `{first_name}` is no longer a **developer**. Farewell, my genius coder~! 🎀"))
    except Exception:
        await message.reply_text(capsify(f"🎀 **Error Detected!** Could not remove `{first_name}` from the dev list. Try again later, senpai~! 🚧"))


@app.on_message(filters.command("adduploader") & dev_filter)
async def add_uploader(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🎀 **Invalid Command!** 🚧\nPlease **reply to a user** or provide a **valid ID**, senpai~!"))

    if tar in NEGLECTED_IDS:
        return await message.reply_text(capsify(f"🚧 **Access Denied!** `{first_name}` cannot be added as an uploader, senpai~! 🎀"))

    if await uploaderdb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"🎀 **Oops!** `{first_name}` is **already an uploader**. Stop teasing me, senpai! 🚧"))

    try:
        await uploaderdb.insert_one({'user_id': tar})
        await message.reply_text(capsify(f"🚧 **Congratulations!** `{first_name}` is now an **Uploader!** 🎀\nThey can now **share amazing content** with everyone!"))
    except Exception:
        await message.reply_text(capsify(f"🎀 **System Error!** `{first_name}` could not be added to the uploader list. Try again, senpai! 🚧"))

@app.on_message(filters.command("rmuploader") & sudo_filter)
async def remove_uploader(client, message: Message):
    if message.reply_to_message:
        tar = message.reply_to_message.from_user.id
        first_name = message.reply_to_message.from_user.first_name
    else:
        try:
            tar = int(message.text.split()[1])
            user_data = await client.get_users(tar)
            first_name = user_data.first_name
        except Exception:
            return await message.reply_text(capsify("🚧 **Invalid Command!** 🎀\nPlease **reply to a user** or provide a **valid ID**, senpai~!"))

    if not await uploaderdb.find_one({'user_id': tar}):
        return await message.reply_text(capsify(f"🎀 **Oops!** `{first_name}` is **not an uploader**. Maybe you mistyped, senpai? 🚧"))

    try:
        await uploaderdb.delete_one({'user_id': tar})
        await message.reply_text(capsify(f"🚧 **Success!** `{first_name}` is no longer an **Uploader**. Their reign of uploads has ended~! 🎀"))
    except Exception:
        await message.reply_text(capsify(f"🎀 **System Error!** `{first_name}` could not be removed from the uploader list. Try again, senpai! 🚧"))

@app.on_message(filters.command("sudolist") & sudo_filter)
async def sudo_list(client, message: Message):
    try:
        db_sudo_ids = await sudb.distinct('user_id')
        # Merge hardcoded + DB sudo IDs (no duplicates)
        all_sudo_ids = list(set(db_sudo_ids) | HARDCODED_SUDO_IDS)

        if not all_sudo_ids:
            return await message.reply_text(capsify("🎀 **No sudo users found!**\nLooks like no one has the supreme powers yet, senpai~! 🚧"))

        user_list = []
        for user_id in all_sudo_ids:
            try:
                user = await client.get_users(user_id)
                tag = " 🔒" if user_id in HARDCODED_SUDO_IDS else ""
                user_list.append(f"[{user.first_name}](tg://user?id={user.id}) (`{user.id}`){tag}")
            except Exception:
                tag = " 🔒" if user_id in HARDCODED_SUDO_IDS else ""
                user_list.append(f"**Unknown User** (`{user_id}`){tag}")

        response_text = (
            f"🚀 **Total Sudo Users:** `{len(user_list)}`\n"
            f"_(🔒 = permanent/hardcoded)_\n\n"
            + "\n".join(user_list)
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛑 Close", callback_data=f"sud_clos_{message.from_user.id}")]]
        )
        await message.reply_text(capsify(response_text), reply_markup=keyboard)
    except Exception as e:
        await message.reply_text(capsify(f"🚨 **Error fetching sudo list!**\n{str(e)}"))

@app.on_message(filters.command("devlist") & dev_filter)
async def dev_list(client, message: Message):
    try:
        dev_users_list = await devb.distinct('user_id')
        if not dev_users_list:
            return await message.reply_text(capsify("🎀 **No developers found!**\nLooks like no one is coding magic here, senpai~! 🚧"))

        user_list = []
        for user_id in dev_users_list:
            try:
                user = await client.get_users(user_id)
                user_list.append(f"[{user.first_name}](tg://user?id={user.id}) (`{user.id}`)")
            except Exception:
                user_list.append(f"**Unknown User** (`{user_id}`)")

        response_text = f"🚀 **Total Developers:** `{len(user_list)}`\n\n" + "\n".join(user_list)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛑 Close", callback_data=f"sud_clos_{message.from_user.id}")]]
        )
        await message.reply_text(capsify(response_text), reply_markup=keyboard)
    except Exception as e:
        await message.reply_text(capsify(f"🚨 **Error fetching developer list!**\n{str(e)}"))

@app.on_message(filters.command("uploaderlist") & sudo_filter)
async def uploader_list(client, message: Message):
    try:
        uploader_users_list = await uploaderdb.distinct('user_id')
        if not uploader_users_list:
            return await message.reply_text(capsify("🎀 **No uploaders found!**\nNo one is bringing new content yet, senpai~! 🚧"))

        user_list = []
        for user_id in uploader_users_list:
            try:
                user = await client.get_users(user_id)
                user_list.append(f"[{user.first_name}](tg://user?id={user.id}) (`{user.id}`)")
            except Exception:
                user_list.append(f" **Unknown User** (`{user_id}`)")

        response_text = f"🚀 **Total Uploaders:** `{len(user_list)}`\n\n" + "\n".join(user_list)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛑 Close", callback_data=f"sud_clos_{message.from_user.id}")]]
        )
        await message.reply_text(capsify(response_text), reply_markup=keyboard)
    except Exception as e:
        await message.reply_text(capsify(f"🚨 **Error fetching uploader list!**\n{str(e)}"))

@app.on_callback_query(filters.regex(r"sud_clos_\d+"))
async def close_callback(client, callback_query: CallbackQuery):
    callback_user_id = int(callback_query.data.split("_")[-1])
    if callback_query.from_user.id != callback_user_id:
        return await callback_query.answer("🚨 This isn't for you, baka! ❗", show_alert=True)
    await callback_query.message.delete()
