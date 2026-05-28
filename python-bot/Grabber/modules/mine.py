import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from . import Grabberu as app, user_collection

# Mining Items & Rarity
MINING_ITEMS = {
    "Iron Ore": {"rarity": "Common", "value": 50, "emoji": "⛏️"},
    "Gold Nugget": {"rarity": "Rare", "value": 150, "emoji": "🏆"},
    "Sapphire Crystal": {"rarity": "Epic", "value": 400, "emoji": "🔷"},
    "Diamond Shard": {"rarity": "Legendary", "value": 1000, "emoji": "💎"},
}

RARITY_TIME = {"Common": 3, "Rare": 5, "Epic": 8, "Legendary": 12}  # Time taken to mine

# Energy System
MAX_ENERGY = 5
ENERGY_REFILL_TIME = 600  # 10 minutes per energy point

# Function to get user mining data
async def get_user_data(user_id):
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        user_data = {
            "id": user_id, 
            "balance": 0, 
            "inventory": {}, 
            "energy": MAX_ENERGY, 
            "last_mined": 0
        }
        await user_collection.insert_one(user_data)
    elif "energy" not in user_data:
        user_data["energy"] = MAX_ENERGY  # Ensure energy exists
        await user_collection.update_one({'id': user_id}, {"$set": {"energy": MAX_ENERGY}})
    return user_data

@app.on_message(filters.command("mine"))
async def mine_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data["energy"] <= 0:
        await message.reply_text("⚡ **You're out of energy!** Wait for it to refill or buy more.")
        return

    item_name, item_info = random.choice(list(MINING_ITEMS.items()))
    rarity = item_info["rarity"]
    value = item_info["value"]
    emoji = item_info["emoji"]
    mine_time = RARITY_TIME[rarity]

    # Decrease Energy
    await user_collection.update_one({'id': user_id}, {"$inc": {"energy": -1}})

    # Digging Animation
    msg = await message.reply_text("⛏️ Digging...")
    for _ in range(mine_time):
        await msg.edit(f"⛏️ Digging{'.' * (_ % 3 + 1)}")
        await asyncio.sleep(1)

    # Update User Inventory
    user_inventory = user_data.get("inventory", {})
    user_inventory[item_name] = user_inventory.get(item_name, 0) + 1
    await user_collection.update_one({'id': user_id}, {"$set": {"inventory": user_inventory}})

    # Mining Success Message
    await msg.edit(f"🎉 **You found a {emoji} {item_name}!**\n"
                   f"✨ **Rarity:** {rarity}\n💰 **Value:** {value} coins")

    # Refill Energy Over Time
    asyncio.create_task(refill_energy(user_id))

async def refill_energy(user_id):
    await asyncio.sleep(ENERGY_REFILL_TIME)
    await user_collection.update_one({'id': user_id}, {"$inc": {"energy": 1}})

@app.on_message(filters.command("inventory"))
async def inventory_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    inventory = user_data.get("inventory", {})

    if not inventory:
        await message.reply_text("📦 **Your inventory is empty!** Start mining to collect items.")
        return

    inv_msg = "🗃 **Your Inventory:**\n\n"
    for item, count in inventory.items():
        emoji = MINING_ITEMS[item]["emoji"]
        inv_msg += f"{emoji} {item}: **{count}x**\n"

    await message.reply_text(inv_msg)

@app.on_message(filters.command("sell"))
async def sell_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    inventory = user_data.get("inventory", {})

    if not inventory:
        await message.reply_text("❌ **You have nothing to sell!** Mine first.")
        return

    total_earnings = 0
    for item, count in inventory.items():
        value = MINING_ITEMS[item]["value"]
        total_earnings += value * count

    # Clear Inventory and Add Balance
    await user_collection.update_one({'id': user_id}, {"$set": {"inventory": {}}, "$inc": {"balance": total_earnings}})

    await message.reply_text(f"✅ **Sold all items for 💰 {total_earnings} coins!**")
