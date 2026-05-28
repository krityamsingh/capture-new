import time
from pyrogram import Client, filters
from Grabber import application, user_collection
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import asyncio
from . import add, deduct, show, app
from .block import block_dec, temp_block
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Dictionary to track last payment times
last_payment_times = {}
cheque_requests = {}

# Generate cheque image
async def generate_cheque(sender_name: str, recipient_name: str, amount: int, reason: str = None):
    # Create blank image
    img = Image.new('RGB', (800, 400), color=(240, 240, 240))
    d = ImageDraw.Draw(img)
    
    # Add decorative elements
    d.rectangle([20, 20, 780, 380], outline=(0, 0, 0), width=2)
    d.rectangle([30, 30, 770, 100], fill=(220, 220, 255), outline=(0, 0, 0))
    
    # Add title
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 36)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    d.text((400, 60), "TOKEN CHEQUE", fill=(0, 0, 0), font=font_large, anchor="mm")
    
    # Add details
    d.text((50, 150), f"Pay to: {recipient_name}", fill=(0, 0, 0), font=font_medium)
    d.text((50, 200), f"Amount: Ŧ{amount:,}", fill=(0, 0, 0), font=font_medium)
    d.text((50, 250), f"From: {sender_name}", fill=(0, 0, 0), font=font_medium)
    
    if reason:
        wrapped_reason = textwrap.fill(reason, width=40)
        d.text((50, 300), f"Memo: {wrapped_reason}", fill=(0, 0, 0), font=font_small)
    
    # Add decorative signature line
    d.line([500, 350, 750, 350], fill=(0, 0, 0), width=1)
    d.text((750, 340), "SENDER", fill=(100, 100, 100), font=font_small, anchor="ra")
    
    # Save to bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

@app.on_message(filters.command('pay'))
@block_dec
async def pay_tokens(client: Client, message: Message):
    sender = message.from_user
    sender_id = sender.id

    if sender_id in temp_block and time.time() < temp_block[sender_id]:
        return

    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʀᴇᴘʟʏ ᴛᴏ �ᴛʜᴇ ᴘᴇʀsᴏɴ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇɴᴅ ᴛᴏᴋᴇɴs ᴛᴏ.",
            quote=True
        )
        return

    recipient = message.reply_to_message.from_user
    recipient_id = recipient.id

    if sender_id == recipient_id:
        await message.reply_text(
            "❌ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴘᴀʏ ʏᴏᴜʀsᴇʟғ!",
            quote=True
        )
        return

    try:
        args = message.text.split()
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
        reason = " ".join(args[2:]) if len(args) > 2 else None
    except (IndexError, ValueError):
        await message.reply_text(
            "**ᴜsᴀɢᴇ:** `/pay <ᴀᴍᴏᴜɴᴛ> [ʀᴇᴀsᴏɴ]`\n**ᴇxᴀᴍᴘʟᴇ:** `/pay 100 ᴛʜᴀɴᴋs!`",
            quote=True
        )
        return

    # Check minimum amount
    if amount < 10:
        await message.reply_text(
            f"**ᴍɪɴɪᴍᴜᴍ ᴛʀᴀɴsғᴇʀ ᴀᴍᴏᴜɴᴛ ɪs Ŧ10 ᴛᴏᴋᴇɴs**",
            quote=True
        )
        return

    sender_balance = await show(sender_id)
    if not sender_balance or sender_balance < amount:
        await message.reply_text(
            f"**ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ!** ʏᴏᴜ ᴏɴʟʏ ʜᴀᴠᴇ **Ŧ{sender_balance:,}** ᴛᴏᴋᴇɴs.",
            quote=True
        )
        return

    # Anti-spam check
    last_time = last_payment_times.get(sender_id, 0)
    if time.time() - last_time < 300:  # 5 minutes in seconds
        wait_time = 300 - (time.time() - last_time)
        minutes = int(wait_time // 60)
        seconds = int(wait_time % 60)
        await message.reply_text(
            f"⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ **{minutes}ᴍ {seconds}s** ʙᴇғᴏʀᴇ sᴇɴᴅɪɴɢ ᴀɴᴏᴛʜᴇʀ ᴘᴀʏᴍᴇɴᴛ.",
            quote=True
        )
        return

    # Process payment
    await deduct(sender_id, amount)
    await add(recipient_id, amount)
    last_payment_times[sender_id] = time.time()

    # Create receipt
    sender_mention = f"[{sender.first_name}](tg://user?id={sender_id})"
    recipient_mention = f"[{recipient.first_name}](tg://user?id={recipient_id})"
    
    transaction_id = f"TXN-{random.randint(100000, 999999)}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    msg = (
        f"💸 **ᴘᴀʏᴍᴇɴᴛ sᴜᴄᴄᴇssғᴜʟ** 💸\n\n"
        f"• **ᴀᴍᴏᴜɴᴛ:** Ŧ{amount:,}\n"
        f"• **ғʀᴏᴍ:** {sender_mention}\n"
        f"• **ᴛᴏ:** {recipient_mention}\n"
        f"• **ɪᴅ:** `{transaction_id}`\n"
        f"• **ᴛɪᴍᴇ:** `{timestamp}`\n"
    )
    
    if reason:
        msg += f"• **ɴᴏᴛᴇ:** `{reason}`\n"
    
    msg += (
        f"\n**ʙᴀʟᴀɴᴄᴇs:**\n"
        f"{sender_mention}: **Ŧ{await show(sender_id):,}**\n"
        f"{recipient_mention}: **Ŧ{await show(recipient_id):,}**"
    )

    await message.reply_text(
        msg,
        quote=True,
        disable_web_page_preview=True
    )

@app.on_message(filters.command('cheque'))
@block_dec
async def cheque_command(client: Client, message: Message):
    sender = message.from_user
    sender_id = sender.id
    
    if not message.reply_to_message:
        await message.reply_text(
            "💳 **ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴀ ᴄʜᴇǫᴜᴇ:**\n\n"
            "ʀᴇᴘʟʏ ᴛᴏ ʀᴇᴄɪᴘɪᴇɴᴛ ᴡɪᴛʜ:\n"
            "`/cheque <ᴀᴍᴏᴜɴᴛ> [ʀᴇᴀsᴏɴ]`\n\n"
            "**ᴇxᴀᴍᴘʟᴇ:** `/cheque 500 ʙɪʀᴛʜᴅᴀʏ ɢɪғᴛ`",
            quote=True
        )
        return
        
    recipient = message.reply_to_message.from_user
    recipient_id = recipient.id
    
    try:
        args = message.text.split()
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
        reason = " ".join(args[2:]) if len(args) > 2 else None
    except (IndexError, ValueError):
        await message.reply_text(
            "**ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ.** ᴜsᴇ: `/cheque <ᴀᴍᴏᴜɴᴛ> [ʀᴇᴀsᴏɴ]`",
            quote=True
        )
        return
    
    # Check balance
    sender_balance = await show(sender_id)
    if not sender_balance or sender_balance < amount:
        await message.reply_text(
            f"**ʏᴏᴜ ɴᴇᴇᴅ Ŧ{amount:,} ᴛᴏᴋᴇɴs ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴛʜɪs ᴄʜᴇǫᴜᴇ.**",
            quote=True
        )
        return
    
    # Generate cheque image
    cheque_img = await generate_cheque(sender.first_name, recipient.first_name, amount, reason)
    
    # Store cheque request
    cheque_id = f"CHEQUE-{random.randint(100000, 999999)}"
    cheque_requests[cheque_id] = {
        'sender_id': sender_id,
        'recipient_id': recipient_id,
        'amount': amount,
        'reason': reason,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=7)
    }
    
    # Send cheque with buttons
    caption = (
        f"🏦 **ᴛᴏᴋᴇɴ ᴄʜᴇǫᴜᴇ** 🏦\n\n"
        f"• **ᴀᴍᴏᴜɴᴛ:** Ŧ{amount:,}\n"
        f"• **ᴛᴏ:** {recipient.first_name}\n"
        f"• **ғʀᴏᴍ:** {sender.first_name}\n"
        f"• **ɪᴅ:** `{cheque_id}`\n"
        f"• **ᴇxᴘɪʀᴇs:** {cheque_requests[cheque_id]['expires_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        f"ᴜsᴇ `/cashcheque {cheque_id}` ᴛᴏ ᴄʟᴀɪᴍ"
    )
    
    await message.reply_photo(
        photo=cheque_img,
        caption=caption,
        quote=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 ᴄᴀsʜ ᴄʜᴇǫᴜᴇ", callback_data=f"cash_{cheque_id}")],
            [InlineKeyboardButton("❌ ᴠᴏɪᴅ ᴄʜᴇǫᴜᴇ", callback_data=f"void_{cheque_id}")]
        ])
    )

@app.on_message(filters.command('cashcheque'))
@block_dec
async def cash_cheque(client: Client, message: Message):
    try:
        cheque_id = message.text.split()[1]
        cheque = cheque_requests.get(cheque_id)
        
        if not cheque:
            await message.reply_text(
                "**ɪɴᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ ᴄʜᴇǫᴜᴇ ɪᴅ**",
                quote=True
            )
            return
            
        if message.from_user.id != cheque['recipient_id']:
            await message.reply_text(
                "**ᴛʜɪs ᴄʜᴇǫᴜᴇ ɪs ɴᴏᴛ ɪssᴜᴇᴅ ᴛᴏ ʏᴏᴜ**",
                quote=True
            )
            return
            
        if datetime.now() > cheque['expires_at']:
            await message.reply_text(
                "**ᴛʜɪs ᴄʜᴇǫᴜᴇ ʜᴀs ᴇxᴘɪʀᴇᴅ**",
                quote=True
            )
            return
            
        # Check sender balance
        sender_balance = await show(cheque['sender_id'])
        if not sender_balance or sender_balance < cheque['amount']:
            await message.reply_text(
                "**sᴇɴᴅᴇʀ ʜᴀs ɪɴsᴜғғɪᴄɪᴇɴᴛ ғᴜɴᴅs ᴛᴏ ᴄᴏᴠᴇʀ ᴛʜɪs ᴄʜᴇǫᴜᴇ**",
                quote=True
            )
            return
            
        # Process payment
        await deduct(cheque['sender_id'], cheque['amount'])
        await add(cheque['recipient_id'], cheque['amount'])
        
        # Notification to both parties
        sender = await client.get_users(cheque['sender_id'])
        recipient = await client.get_users(cheque['recipient_id'])
        
        msg = (
            f"💵 **ᴄʜᴇǫᴜᴇ ᴄᴀsʜᴇᴅ** 💵\n\n"
            f"• **ᴀᴍᴏᴜɴᴛ:** Ŧ{cheque['amount']:,}\n"
            f"• **ғʀᴏᴍ:** {sender.mention}\n"
            f"• **ᴛᴏ:** {recipient.mention}\n"
            f"• **ɪᴅ:** `{cheque_id}`\n\n"
            f"**ɴᴇᴡ ʙᴀʟᴀɴᴄᴇs:**\n"
            f"{sender.mention}: **Ŧ{await show(cheque['sender_id']):,}**\n"
            f"{recipient.mention}: **Ŧ{await show(cheque['recipient_id']):,}**"
        )
        
        await message.reply_text(msg, quote=True)
        
        # Notify sender
        try:
            await client.send_message(
                cheque['sender_id'],
                f"📤 ʏᴏᴜʀ ᴄʜᴇǫᴜᴇ `{cheque_id}` ғᴏʀ **Ŧ{cheque['amount']:,}** ʜᴀs ʙᴇᴇɴ ᴄᴀsʜᴇᴅ"
            )
        except:
            pass
            
        # Remove cheque from system
        del cheque_requests[cheque_id]
        
    except IndexError:
        await message.reply_text(
            "**ᴜsᴀɢᴇ:** `/cashcheque <ᴄʜᴇǫᴜᴇ_ɪᴅ>`",
            quote=True
        )

@app.on_callback_query(filters.regex(r"^cash_"))
async def cash_cheque_button(client, callback_query):
    cheque_id = callback_query.data.split("_")[1]
    cheque = cheque_requests.get(cheque_id)
    
    if not cheque:
        await callback_query.answer("ᴄʜᴇǫᴜᴇ ɴᴏ ʟᴏɴɢᴇʀ ᴠᴀʟɪᴅ", show_alert=True)
        return
        
    if callback_query.from_user.id != cheque['recipient_id']:
        await callback_query.answer("ᴛʜɪs ᴄʜᴇǫᴜᴇ ɪsɴ'ᴛ ʏᴏᴜʀs ᴛᴏ ᴄᴀsʜ", show_alert=True)
        return
        
    # Check sender balance
    sender_balance = await show(cheque['sender_id'])
    if not sender_balance or sender_balance < cheque['amount']:
        await callback_query.answer("sᴇɴᴅᴇʀ ʜᴀs ɪɴsᴜғғɪᴄɪᴇɴᴛ ғᴜɴᴅs", show_alert=True)
        return
        
    # Process payment
    await deduct(cheque['sender_id'], cheque['amount'])
    await add(cheque['recipient_id'], cheque['amount'])
    
    # Notification
    sender = await client.get_users(cheque['sender_id'])
    recipient = await client.get_users(cheque['recipient_id'])
    
    msg = (
        f"💵 **ᴄʜᴇǫᴜᴇ ᴄᴀsʜᴇᴅ** 💵\n\n"
        f"• **ᴀᴍᴏᴜɴᴛ:** Ŧ{cheque['amount']:,}\n"
        f"• **ғʀᴏᴍ:** {sender.mention}\n"
        f"• **ᴛᴏ:** {recipient.mention}\n"
        f"• **ɪᴅ:** `{cheque_id}`"
    )
    
    await callback_query.message.edit_caption(msg)
    await callback_query.answer("ᴄʜᴇǫᴜᴇ ᴄᴀsʜᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=True)
    
    # Notify sender
    try:
        await client.send_message(
            cheque['sender_id'],
            f"📤 ʏᴏᴜʀ ᴄʜᴇǫᴜᴇ `{cheque_id}` ғᴏʀ **Ŧ{cheque['amount']:,}** ʜᴀs ʙᴇᴇɴ ᴄᴀsʜᴇᴅ"
        )
    except:
        pass
        
    # Remove cheque from system
    del cheque_requests[cheque_id]

@app.on_callback_query(filters.regex(r"^void_"))
async def void_cheque_button(client, callback_query):
    cheque_id = callback_query.data.split("_")[1]
    cheque = cheque_requests.get(cheque_id)
    
    if not cheque:
        await callback_query.answer("ᴄʜᴇǫᴜᴇ ᴀʟʀᴇᴀᴅʏ ᴠᴏɪᴅᴇᴅ", show_alert=True)
        return
        
    if callback_query.from_user.id != cheque['sender_id']:
        await callback_query.answer("ᴏɴʟʏ ᴛʜᴇ sᴇɴᴅᴇʀ ᴄᴀɴ ᴠᴏɪᴅ ᴛʜɪs", show_alert=True)
        return
        
    del cheque_requests[cheque_id]
    await callback_query.answer("ᴄʜᴇǫᴜᴇ ᴠᴏɪᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ", show_alert=True)
    await callback_query.message.edit_caption("❌ **ᴛʜɪs ᴄʜᴇǫᴜᴇ ʜᴀs ʙᴇᴇɴ ᴠᴏɪᴅᴇᴅ ʙʏ ᴛʜᴇ sᴇɴᴅᴇʀ**")
