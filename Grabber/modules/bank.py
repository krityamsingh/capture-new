from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import math
import time
import random
from . import add, deduct, show, abank, dbank, sbank, user_collection, app
from .block import block_dec, temp_block

# Stylish text formatter
def sᴛʏʟɪsʜ(text):
    return text.upper().translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    ))

# Custom Error Handler with stylish messages
async def handle_error(client: Client, message: Message, error: Exception, command: str = None):
    error_messages = {
        "IndexError": ("ᴘʟᴇᴀsᴇ sᴘᴇᴄɪꜰʏ ᴀɴ ᴀᴍᴏᴜɴᴛ.\nᴇxᴀᴍᴘʟᴇ: `/{} 100`"),
        "ValueError": ("ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ. ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ."),
        "default": ("❌ ᴏᴏᴘs! sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ.\nᴇʀʀᴏʀ: {}")
    }
    
    if isinstance(error, IndexError) and command:
        msg = error_messages["IndexError"].format(command)
    else:
        msg = error_messages.get(type(error).__name__, error_messages["default"]).format(str(error))
    
    await message.reply_text(msg)
    print(f"[ERROR] {error}")

# Transaction animation function
async def show_transaction_animation(client: Client, message: Message, transaction_type: str):
    animation_chars = {
        "deposit": ["💸", "💰", "🏦"],
        "withdraw": ["💳", "💵", "🤑"],
        "loan": ["📝", "🏛", "💲"],
        "repay": ["🔙", "💱", "✅"]
    }
    
    msg = await message.reply_text(("ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ..."))
    for emoji in animation_chars.get(transaction_type, ["⏳"]*3):
        await msg.edit_text(f"{emoji} {('ᴘʀᴏᴄᴇssɪɴɢ...')}")
        time.sleep(0.5)
    return msg

# Generate a fake transaction ID
def generate_transaction_id():
    return f"TXN{random.randint(1000000000, 9999999999)}"

# /save command with stylish messages
@block_dec
async def save(client: Client, message: Message):
    try:
        amount = int(message.command[1])
        if amount <= 0:
            raise ValueError()
    except (IndexError, ValueError) as e:
        await handle_error(client, message, e, "save")
        return

    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    processing_msg = await show_transaction_animation(client, message, "deposit")
    
    user_data = await user_collection.find_one({'id': user_id}, projection={'balance': 1})
    if user_data:
        balance = int(user_data.get('balance', 0))
        if amount > balance:
            await processing_msg.delete()
            await message.reply_text(
                f"**{('⚠️ ɪɴsᴜꜰꜰɪᴄɪᴇɴᴛ ꜰᴜɴᴅs')}**\n\n"
                f"**ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ʙᴀʟᴀɴᴄᴇ:** `Ŧ{balance:,}`\n"
                f"**ʏᴏᴜ ᴛʀɪᴇᴅ ᴛᴏ ᴅᴇᴘᴏsɪᴛ:** `Ŧ{amount:,}`\n\n"
                f"**{('ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.')}**"
            )
            return

        await deduct(user_id, amount)
        await abank(user_id, amount)
        
        transaction_id = generate_transaction_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await processing_msg.delete()
        await message.reply_text(
            f"**{('🏦 ᴅᴇᴘᴏsɪᴛ sᴜᴄᴄᴇssꜰᴜʟ!')}**\n\n"
            f"**▸ ᴀᴍᴏᴜɴᴛ:** `Ŧ{amount:,}`\n"
            f"**▸ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ:** `{transaction_id}`\n"
            f"**▸ ᴅᴀᴛᴇ:** `{timestamp}`\n\n"
            f"**{('ʏᴏᴜʀ ꜰᴜɴᴅs ᴀʀᴇ ɴᴏᴡ sᴇᴄᴜʀᴇʟʏ sᴛᴏʀᴇᴅ ɪɴ ʏᴏᴜʀ ʙᴀɴᴋ ᴀᴄᴄᴏᴜɴᴛ.')}**"
        )
    else:
        await processing_msg.delete()
        await message.reply_text(f"**{('🔍 ᴀᴄᴄᴏᴜɴᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ')}**\n\n{('ᴡᴇ ᴄᴏᴜʟᴅɴᴛ ʟᴏᴄᴀᴛᴇ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.')}")

# /withdraw command with stylish messages
@block_dec
async def withdraw(client: Client, message: Message):
    try:
        amount = int(message.command[1])
        if amount <= 0:
            raise ValueError()
    except (IndexError, ValueError) as e:
        await handle_error(client, message, e, "withdraw")
        return

    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    processing_msg = await show_transaction_animation(client, message, "withdraw")
    
    user_data = await user_collection.find_one({'id': user_id}, projection={'saved_amount': 1})
    if user_data:
        saved = int(user_data.get('saved_amount', 0))
        if amount > saved:
            await processing_msg.delete()
            await message.reply_text(
                f"**{('⚠️ ɪɴsᴜꜰꜰɪᴄɪᴇɴᴛ sᴀᴠɪɴɢs')}**\n\n"
                f"**ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴀᴠɪɴɢs:** `Ŧ{saved:,}`\n"
                f"**ʏᴏᴜ ᴛʀɪᴇᴅ ᴛᴏ ᴡɪᴛʜᴅʀᴀᴡ:** `Ŧ{amount:,}`\n\n"
                f"**{('ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ sᴀᴠɪɴɢs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.')}**"
            )
            return

        # Small chance (10%) to trigger a fake security check
        if random.random() < 0.1:
            await processing_msg.delete()
            security_check = await message.reply_text(
                f"**{('🔒 sᴇᴄᴜʀɪᴛʏ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ʀᴇǫᴜɪʀᴇᴅ')}**\n\n"
                f"**{('ꜰᴏʀ ʏᴏᴜʀ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ, ᴡᴇ ɴᴇᴇᴅ ᴛᴏ ᴠᴇʀɪꜰʏ ᴛʜɪs ᴡɪᴛʜᴅʀᴀᴡᴀʟ.')}**\n"
                f"**{('ᴘʟᴇᴀsᴇ ᴄᴏɴꜰɪʀᴍ ᴛʜɪs ɪs ʀᴇᴀʟʟʏ ʏᴏᴜ ʙʏ ᴛʏᴘɪɴɢ:')}**\n\n"
                f"`/confirm_withdraw {amount}`"
            )
            return

        await add(user_id, amount)
        await dbank(user_id, amount)
        
        transaction_id = generate_transaction_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await processing_msg.delete()
        await message.reply_text(
            f"**{('💳 ᴡɪᴛʜᴅʀᴀᴡᴀʟ ᴄᴏᴍᴘʟᴇᴛᴇ!')}**\n\n"
            f"**▸ ᴀᴍᴏᴜɴᴛ:** `Ŧ{amount:,}`\n"
            f"**▸ ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ:** `{transaction_id}`\n"
            f"**▸ ᴅᴀᴛᴇ:** `{timestamp}`\n\n"
            f"**{('ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ʜᴀs ʙᴇᴇɴ ᴛʀᴀɴsꜰᴇʀʀᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴠᴀɪʟᴀʙʟᴇ ʙᴀʟᴀɴᴄᴇ.')}**"
        )
    else:
        await processing_msg.delete()
        await message.reply_text(f"**{('🔍 ᴀᴄᴄᴏᴜɴᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ')}**\n\n{('ᴡᴇ ᴄᴏᴜʟᴅɴᴛ ʟᴏᴄᴀᴛᴇ ʏᴏᴜʀ ʙᴀɴᴋ ᴀᴄᴄᴏᴜɴᴛ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.')}")

# /loan command with stylish messages
@block_dec
async def loan(client: Client, message: Message):
    try:
        loan_amount = int(message.command[1])
        if not 1 <= loan_amount <= 10_000_000_000_000:
            raise ValueError()
    except (IndexError, ValueError) as e:
        await handle_error(client, message, e, "loan")
        return

    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    processing_msg = await show_transaction_animation(client, message, "loan")
    
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await processing_msg.delete()
        await message.reply_text(f"**{('🔍 ᴀᴄᴄᴏᴜɴᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ')}**\n\n{('ᴡᴇ ᴄᴏᴜʟᴅɴᴛ ʟᴏᴄᴀᴛᴇ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ. �ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.')}")
        return

    now = datetime.utcnow()
    last_loan = user_data.get('last_loan_date')
    existing_loan = user_data.get('loan_amount', 0)

    # Credit score simulation (random for demo purposes)
    credit_score = random.randint(300, 850)
    interest_rate = max(5, min(30, 30 - (credit_score - 300) // 25))  # 5-30% based on "credit score"
    
    if last_loan and (now - last_loan).days < 7:
        days_remaining = 7 - (now - last_loan).days
        await processing_msg.delete()
        await message.reply_text(
            f"**{('⏳ ʟᴏᴀɴ ᴄᴏᴏʟᴅᴏᴡɴ ᴘᴇʀɪᴏᴅ')}**\n\n"
            f"**{('ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ᴛᴀᴋᴇ ᴏɴᴇ ʟᴏᴀɴ ᴇᴠᴇʀʏ 7 ᴅᴀʏs.')}**\n"
            f"**ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ɪɴ:** `{days_remaining} ᴅᴀʏ(s)`\n\n"
            f"**ʏᴏᴜʀ ᴄʀᴇᴅɪᴛ sᴄᴏʀᴇ:** `{credit_score}` **(ɪɴᴛᴇʀᴇsᴛ:** `{interest_rate}%`)"
        )
        return

    if existing_loan > 0:
        due_date = user_data.get('loan_due_date')
        if due_date and now > due_date:
            overdue_days = (now - due_date).days
            penalty = existing_loan * (0.05 * overdue_days)
            await user_collection.update_one(
                {'id': user_id},
                {'$set': {'balance': 0, 'saved_amount': 0, 'loan_amount': 0}}
            )
            await processing_msg.delete()
            await message.reply_text(
                f"**{('⚠️ ʟᴏᴀɴ ᴅᴇꜰᴀᴜʟᴛ')}**\n\n"
                f"**ʏᴏᴜ ᴍɪssᴇᴅ ʏᴏᴜʀ ʀᴇᴘᴀʏᴍᴇɴᴛ ᴅᴇᴀᴅʟɪɴᴇ ʙʏ:** `{overdue_days} ᴅᴀʏs`\n"
                f"**ᴀ ᴘᴇɴᴀʟᴛʏ ᴏꜰ:** `Ŧ{int(penalty):,}` **ᴡᴀs ᴀᴘᴘʟɪᴇᴅ.**\n\n"
                f"**{('ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʜᴀs ʙᴇᴇɴ ʀᴇsᴇᴛ ᴅᴜᴇ ᴛᴏ ɴᴏɴ-ᴘᴀʏᴍᴇɴᴛ.')}**"
            )
            return

    # Loan approval process with random chance of rejection
    approval_chance = min(90, 50 + (credit_score - 300) // 10)  # 50-90% based on credit
    if random.randint(1, 100) > approval_chance:
        await processing_msg.delete()
        await message.reply_text(
            f"**{('❌ ʟᴏᴀɴ ᴀᴘᴘʟɪᴄᴀᴛɪᴏɴ ᴅᴇɴɪᴇᴅ')}**\n\n"
            f"**ᴀꜰᴛᴇʀ ʀᴇᴠɪᴇᴡɪɴɢ ʏᴏᴜʀ ᴀᴘᴘʟɪᴄᴀᴛɪᴏɴ (ᴄʀᴇᴅɪᴛ sᴄᴏʀᴇ:** `{credit_score}`),\n"
            f"**{('ᴡᴇ ʀᴇɢʀᴇᴛ ᴛᴏ ɪɴꜰᴏʀᴍ ʏᴏᴜ ᴛʜᴀᴛ ʏᴏᴜʀ ʟᴏᴀɴ ʀᴇǫᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴅᴇɴɪᴇᴅ.')}**\n\n"
            f"**{('ʀᴇᴀsᴏɴ: ᴅᴏᴇs ɴᴏᴛ ᴍᴇᴇᴛ ᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ʟᴇɴᴅɪɴɢ ᴄʀɪᴛᴇʀɪᴀ.')}**"
        )
        return

    loan_due = now + timedelta(days=10)
    total_repayment = loan_amount + (loan_amount * interest_rate // 100)
    
    await add(user_id, loan_amount)
    await user_collection.update_one(
        {'id': user_id},
        {'$set': {
            'loan_amount': total_repayment,
            'loan_due_date': loan_due,
            'last_loan_date': now,
            'interest_rate': interest_rate
        }}
    )

    await processing_msg.delete()
    await message.reply_text(
        f"**{('✅ ʟᴏᴀɴ ᴀᴘᴘʀᴏᴠᴇᴅ!')}**\n\n"
        f"**▸ ᴀᴍᴏᴜɴᴛ ʀᴇᴄᴇɪᴠᴇᴅ:** `Ŧ{loan_amount:,}`\n"
        f"**▸ ɪɴᴛᴇʀᴇsᴛ ʀᴀᴛᴇ:** `{interest_rate}%`\n"
        f"**▸ ᴛᴏᴛᴀʟ ʀᴇᴘᴀʏᴍᴇɴᴛ ᴅᴜᴇ:** `Ŧ{total_repayment:,}`\n"
        f"**▸ ᴅᴜᴇ ᴅᴀᴛᴇ:** `{loan_due.strftime('%Y-%m-%d')}`\n\n"
        f"**{('ᴘʟᴇᴀsᴇ ᴇɴsᴜʀᴇ ᴛɪᴍᴇʟʏ ʀᴇᴘᴀʏᴍᴇɴᴛ ᴛᴏ ᴍᴀɪɴᴛᴀɪɴ ʏᴏᴜʀ ᴄʀᴇᴅɪᴛ sᴄᴏʀᴇ.')}**"
    )

# /repay command with stylish messages
@block_dec
async def repay(client: Client, message: Message):
    try:
        repay_amt = int(message.command[1])
        if repay_amt <= 0:
            raise ValueError()
    except (IndexError, ValueError) as e:
        await handle_error(client, message, e, "repay")
        return

    user_id = message.from_user.id
    if user_id in temp_block and time.time() < temp_block[user_id]:
        return

    processing_msg = await show_transaction_animation(client, message, "repay")
    
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await processing_msg.delete()
        await message.reply_text("**🔍 ᴀᴄᴄᴏᴜɴᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ**\n\nᴡᴇ ᴄᴏᴜʟᴅɴᴛ ʟᴏᴄᴀᴛᴇ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
        return

    loan_amount = user_data.get('loan_amount', 0)
    if repay_amt > loan_amount:
        await processing_msg.delete()
        await message.reply_text(
            "**⚠️ ᴏᴠᴇʀᴘᴀʏᴍᴇɴᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ**\n\n"
            f"**ʏᴏᴜʀ ʀᴇᴍᴀɪɴɪɴɢ ʟᴏᴀɴ ʙᴀʟᴀɴᴄᴇ:** `Ŧ{loan_amount:,}`\n"
            f"**ʏᴏᴜ ᴛʀɪᴇᴅ ᴛᴏ ʀᴇᴘᴀʏ:** `Ŧ{repay_amt:,}`\n\n"
            "**ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀɴ ᴀᴍᴏᴜɴᴛ ᴇǫᴜᴀʟ ᴛᴏ ᴏʀ ʟᴇss ᴛʜᴀɴ ʏᴏᴜʀ ʀᴇᴍᴀɪɴɪɴɢ ʙᴀʟᴀɴᴄᴇ.**"
        )
        return

    now = datetime.utcnow()
    due = user_data.get('loan_due_date')

    penalty = 0
    if due and now > due:
        overdue_days = (now - due).days
        penalty = loan_amount * (0.05 * overdue_days)
        repay_amt += int(penalty)
        await processing_msg.edit_text(
            "**⚠️ ʟᴀᴛᴇ ʀᴇᴘᴀʏᴍᴇɴᴛ ᴘᴇɴᴀʟᴛʏ**\n\n"
            f"**ʏᴏᴜ'ʀᴇ** `{overdue_days}` **ᴅᴀʏ(s) ʟᴀᴛᴇ ᴏɴ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ.**\n"
            f"**ᴘᴇɴᴀʟᴛʏ ᴀᴘᴘʟɪᴇᴅ:** `Ŧ{int(penalty):,}`\n"
            f"**ɴᴇᴡ ᴛᴏᴛᴀʟ ᴀᴍᴏᴜɴᴛ ᴅᴜᴇ:** `Ŧ{repay_amt:,}`"
        )
        time.sleep(2)

    await deduct(user_id, repay_amt)
    remaining = loan_amount - (repay_amt - int(penalty))
    
    if remaining <= 0:
        # Loan fully paid
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'loan_amount': 0}, '$unset': {'loan_due_date': ""}}
        )
        await processing_msg.delete()
        await message.reply_text(
            "**🎉 ʟᴏᴀɴ ꜰᴜʟʟʏ ʀᴇᴘᴀɪᴅ!**\n\n"
            "**ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜ'ᴠᴇ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴘᴀɪᴅ ᴏꜰꜰ ʏᴏᴜʀ ʟᴏᴀɴ.**\n\n"
            "**ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ʙᴀɴᴋɪɴɢ ᴡɪᴛʜ ᴜs!**"
        )
    else:
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'loan_amount': remaining}}
        )
        await processing_msg.delete()
        await message.reply_text(
            "**✅ ᴘᴀʀᴛɪᴀʟ ʀᴇᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴠᴇᴅ**\n\n"
            f"**ᴀᴍᴏᴜɴᴛ ᴘᴀɪᴅ:** `Ŧ{repay_amt:,}`\n"
            f"**ʀᴇᴍᴀɪɴɪɴɢ ʙᴀʟᴀɴᴄᴇ:** `Ŧ{remaining:,}`\n\n"
            "**ᴘʟᴇᴀsᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ʏᴏᴜʀ ʀᴇᴘᴀʏᴍᴇɴᴛ ʙᴇꜰᴏʀᴇ ᴛʜᴇ ᴅᴜᴇ ᴅᴀᴛᴇ ᴛᴏ ᴀᴠᴏɪᴅ ᴘᴇɴᴀʟᴛɪᴇs.**"
        )

# Handlers
@app.on_message(filters.command("save"))
async def save_handler(client: Client, message: Message):
    await save(client, message)

@app.on_message(filters.command("withdraw"))
async def withdraw_handler(client: Client, message: Message):
    await withdraw(client, message)

@app.on_message(filters.command("loan"))
async def loan_handler(client: Client, message: Message):
    await loan(client, message)

@app.on_message(filters.command("repay"))
async def repay_handler(client: Client, message: Message):
    await repay(client, message)

# Security confirmation handler
@app.on_message(filters.command("confirm_withdraw"))
async def confirm_withdraw_handler(client: Client, message: Message):
    try:
        amount = int(message.command[1])
        user_id = message.from_user.id
        
        # Check if this was actually requested
        user_data = await user_collection.find_one({'id': user_id}, projection={'saved_amount': 1})
        if user_data:
            saved = int(user_data.get('saved_amount', 0))
            if amount > saved:
                await message.reply_text(f"**{('ᴡɪᴛʜᴅʀᴀᴡᴀʟ ʀᴇǫᴜᴇsᴛ ᴇxᴘɪʀᴇᴅ ᴏʀ ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ.')}**")
                return

            await add(user_id, amount)
            await dbank(user_id, amount)
            
            await message.reply_text(
                f"**{('🔓 ᴡɪᴛʜᴅʀᴀᴡᴀʟ ᴠᴇʀɪꜰɪᴇᴅ')}**\n\n"
                f"**`Ŧ{amount:,}` ʜᴀs ʙᴇᴇɴ ᴛʀᴀɴsꜰᴇʀʀᴇᴅ ᴛᴏ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ.**\n\n"
                f"**{('ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴋᴇᴇᴘɪɴɢ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ sᴇᴄᴜʀᴇ!')}**"
            )
    except:
        await message.reply_text(f"**{('ɪɴᴠᴀʟɪᴅ ᴄᴏɴꜰɪʀᴍᴀᴛɪᴏɴ ʀᴇǫᴜᴇsᴛ.')}**")
