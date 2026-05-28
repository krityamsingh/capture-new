from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta
from . import Grabberu as app, user_collection

VIP_COST = 5000  # Cost to become VIP
VIP_DURATION = 7  # VIP membership duration in days

@app.on_message(filters.command("vip"))
async def buy_vip(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'balance': 1, 'vip_expiry': 1})
    
    # Ensure balance is an integer
    balance = int(user_data.get("balance", 0)) if user_data else 0
    vip_expiry = user_data.get("vip_expiry", None) if user_data else None

    # Check if user already has VIP
    if vip_expiry:
        try:
            expiry_date = datetime.strptime(vip_expiry, "%Y-%m-%d").date()
            if expiry_date > datetime.utcnow().date():
                return await message.reply_text(f"👑 **You are already a VIP!**\n\n🕛 **Expires on:** {vip_expiry}")
        except ValueError:
            pass  # If date parsing fails, treat it as expired.

    # Check if user has enough balance
    if balance < VIP_COST:
        return await message.reply_text(f"❌ **You need {VIP_COST:,} coins to buy VIP!**\n💰 Your Balance: {balance:,} coins.")

    # Deduct cost & set VIP expiry
    new_balance = balance - VIP_COST
    new_expiry = (datetime.utcnow() + timedelta(days=VIP_DURATION)).strftime("%Y-%m-%d")
    
    await user_collection.update_one(
        {'id': user_id},
        {"$set": {"vip_expiry": new_expiry}, "$inc": {"balance": -VIP_COST}}
    )

    await message.reply_text(
        f"🎉 **Congratulations! You are now a VIP Member!**\n\n"
        f"👑 **VIP Benefits Activated**\n"
        f"🕛 **Expires on:** `{new_expiry}`\n"
        f"💰 **Remaining Balance:** `{new_balance:,} coins`"
    )

# Function to check VIP status
async def check_vip_status(user_id):
    user_data = await user_collection.find_one({'id': user_id}, projection={'vip_expiry': 1})
    if user_data and user_data.get("vip_expiry"):
        try:
            expiry_date = datetime.strptime(user_data["vip_expiry"], "%Y-%m-%d").date()
            return expiry_date > datetime.utcnow().date()
        except ValueError:
            return False
    return False
