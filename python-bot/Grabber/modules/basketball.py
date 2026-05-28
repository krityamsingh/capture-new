from pyrogram import Client, filters, types as t
from Grabber import user_collection, app
from . import add, deduct, show
from .block import block_dec
import time

COOLDOWN_DURATION = 30
last_usage_time = {}

@app.on_message(filters.command(["basket"]))
@block_dec
async def basket_bet(client: Client, message: t.Message):
    user_id = message.from_user.id
    current_time = time.time()

    # ⚡ ᴄᴏᴏʟᴅᴏᴡɴ ʜᴀɴᴅʟɪɴɢ
    last_used = last_usage_time.get(user_id)
    if last_used and current_time - last_used < COOLDOWN_DURATION:
        wait_time = int(COOLDOWN_DURATION - (current_time - last_used))
        return await message.reply(f"⏳ **ᴛᴏᴏ ғᴀsᴛ, sʜᴏɴᴇɴ!** ᴡᴀɪᴛ `{wait_time}s` ʙᴇғᴏʀᴇ ʀᴇᴛʀʏɪɴɢ・ᴏ・")

    # 🎯 ʙᴇᴛ ᴠᴀʟɪᴅᴀᴛɪᴏɴ
    try:
        bet = int(message.text.split()[1])
    except:
        return await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ʙᴇᴛ!** ᴜsᴇ: `/basket ᴀᴍᴏᴜɴᴛ`")

    # 💰 ʙᴀʟᴀɴᴄᴇ ᴄʜᴇᴄᴋ
    balance = await show(user_id)
    if balance is None:
        return await message.reply("⚠️ **ɴᴏ ᴄᴏᴍᴘᴀɴɪᴏɴ ғᴏᴜɴᴅ!** ᴜsᴇ /start ғɪʀsᴛ・ᴏ・")
    
    min_bet = max(50, int(balance * 0.07))  # 7% ᴏʀ 50 ᴄᴏɪɴs (ᴡʜɪᴄʜᴇᴠᴇʀ ɪs ʜɪɢʜᴇʀ)
    if bet < min_bet:
        return await message.reply(f"💢 **ʙᴇᴛ ᴛᴏᴏ ʟᴏᴡ!** ᴍɪɴɪᴍᴜᴍ: `{min_bet}` ᴄᴏɪɴs")
    if bet > balance:
        return await message.reply("💸 **ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴs!** ʏᴏᴜ'ʀᴇ ʙʀᴏᴋᴇ ʟᴏʟ・ᴏ・")

    # 🏀 ʀᴏʟʟ ᴛʜᴇ ᴅɪᴄᴇ
    dice = await client.send_dice(message.chat.id, "🏀")
    value = dice.dice.value
    last_usage_time[user_id] = current_time  # 📅 ᴜᴘᴅᴀᴛᴇ ᴄᴏᴏʟᴅᴏᴡɴ

    # ✨ ᴀɴɪᴍᴇ-sᴛʏʟᴇ ʀᴇsᴜʟᴛs
    if value == 6:
        win = bet * 2
        await add(user_id, win)
        await change_xp(user_id, 5)
        await message.reply(
            f"✨ **sᴜᴘᴇʀ sʟᴀᴍ ᴅᴜɴᴋ!!** ✨\n"
            f"╰┈➤ 🏆 +`{win}` ᴄᴏɪɴs\n"
            f"╰┈➤ 🌟 +5 xᴘ\n\n"
            f"ᴛʜᴀᴛ's ʜᴏᴋᴀɢᴇ-ʟᴇᴠᴇʟ sᴋɪʟʟs! (•̀ᴗ•́)و"
        )
    elif value in [4, 5]:
        win = int(bet * 1.5)
        await add(user_id, win)
        await change_xp(user_id, 3)
        await message.reply(
            f"🎯 **ɴᴏᴛʜɪɴɢ ʙᴜᴛ ɴᴇᴛ!**\n"
            f"╰┈➤ 💰 +`{win}` ᴄᴏɪɴs\n"
            f"╰┈➤ ✨ +3 xᴘ\n\n"
            f"ᴋᴇᴇᴘ ɢᴏɪɴɢ, sᴇɴᴘᴀɪ! ٩(◕‿◕｡)۶"
        )
    elif value in [2, 3]:
        loss = int(bet * 0.5)
        await deduct(user_id, loss)
        await change_xp(user_id, -2)
        await message.reply(
            f"💢 **ᴄʟᴏsᴇ ᴍɪss!**\n"
            f"╰┈➤ 🩹 -`{loss}` ᴄᴏɪɴs\n"
            f"╰┈➤ 📉 -2 xᴘ\n\n"
            f"ᴅᴏɴ'ᴛ ᴡᴏʀʀʏ, ɴᴇxᴛ �ᴛɪᴍᴇ ғᴏʀ sᴜʀᴇ! (╥﹏╥)"
        )
    else:
        await deduct(user_id, bet)
        await change_xp(user_id, -3)
        await message.reply(
            f"💀 **ᴀɪʀʙᴀʟʟ ᴅɪsᴀsᴛᴇʀ!**\n"
            f"╰┈➤ ☠️ -`{bet}` ᴄᴏɪɴs\n"
            f"╰┈➤ ❌ -3 xᴘ\n\n"
            f"ᴇᴠᴇɴ sᴀᴋᴜʀᴀ ᴄᴏᴜʟᴅɴ'ᴛ ᴍɪss ᴛʜɪs ʙᴀᴅ (≧﹏≦)"
        )

async def change_xp(user_id, amount):
    await user_collection.update_one(
        {'id': user_id}, 
        {'$inc': {'xp': amount}}, 
        upsert=True
    )
