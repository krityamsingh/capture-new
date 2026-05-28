from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from . import app, user_collection, collection, auction
import asyncio
from itertools import zip_longest

OWNER_IDS = [8496760733, 7878477646]  # change this to your Telegram ID
SUPPORT_GROUP = -1002313549356
SUPPORT_CHANNEL = -1003430763556

RARITIES = [
    "🟡 Legendary",
    "💮 Mythic",
    "🔮 Limited Edition",
    "🫧 Premium",
    "🔱 Godly",
    "🏵️ Exotic",
    "⚜️ Unique",
    "⚡ Eternal",
    "🌸 Radiant",
    "💠 Divine",
    "🎐 Celestial",
    "🌩️ Electra",
    "🧿 Galaxia",
    "☀️ Summer[Su]",
    "🧬 Animation"
]

auction_state = {}
user_bid_counts = {}  # Track bid counts per user per auction

# /startauction (owner only)
@app.on_message(filters.command("startauction") & filters.user(OWNER_IDS))
async def start_auction(client: Client, message: Message):
    def chunk_buttons(data, n):
        args = [iter(data)] * n
        return list(filter(None, [list(filter(None, group)) for group in zip_longest(*args)]))

    buttons = [
        InlineKeyboardButton(text=rarity, callback_data=f"auction_rarity_{rarity}")
        for rarity in RARITIES
    ]
    keyboard = chunk_buttons(buttons, 3)

    await message.reply(
        "**Konichiwa, Master!**\nSelect a rarity to begin the auction.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# /selectauction (owner only)
@app.on_message(filters.command("selectauction") & filters.user(OWNER_IDS))
async def select_auction(client: Client, message: Message):
    try:
        char_id = message.text.split()[1].strip()
    except IndexError:
        return await message.reply("Usage: /selectauction [character_id]")

    # Try both ObjectId and direct ID matching
    char = None
    try:
        # First try as MongoDB ObjectId
        char = await collection.find_one({"_id": ObjectId(char_id)})
    except:
        # If that fails, try as direct string/numeric ID
        char = await collection.find_one({"id": char_id})
    
    if not char:
        # One more try with character's name
        char = await collection.find_one({"name": char_id})
        if not char:
            return await message.reply("Character not found! Please check the ID/name.")

    # Standardize the character data
    char["_id"] = str(char.get("_id"))
    if "id" not in char:
        char["id"] = str(char["_id"])

    auction_data = {
        "char": char,
        "start_time": datetime.utcnow(),
        "highest_bid": 0,
        "highest_user": None,
        "bidders": [],
        "pin_msg_id": None,
        "last_bid_time": datetime.utcnow()
    }

    await auction.delete_many({})
    result = await auction.insert_one(auction_data)

    # Reset bid counts for new auction
    global user_bid_counts
    user_bid_counts = {}

    caption = (
        f"**⏳ AUCTION HAS BEGUN!**\n\n"
        f"🏷️ **Name:** `{char['name']}`\n"
        f"🧬 **Anime:** `{char['anime']}`\n"
        f"✨ **Rarity:** {char['rarity']}\n\n"
    )

    # Special rules for Summer[Su]
    if char['rarity'] == "☀️ Summer[Su]":
        caption += (
            f"💰 **Starting Bid:** `100,000,000` coins\n"
            f"⚠️ **Special Rules:**\n"
            f"- Max 3 bids per user\n"
            f"- If no bid in 1 minute, character will be removed\n\n"
        )
    else:
        caption += "To participate, use the command: `/bid [amount]`\n"

    # Post and pin in SUPPORT_GROUP
    if char.get("video_url"):
        msg = await client.send_video(SUPPORT_GROUP, char["video_url"], caption=caption)
    else:
        msg = await client.send_photo(SUPPORT_GROUP, char["img_url"], caption=caption)

    await msg.pin(disable_notification=True)

    # Save pin message ID
    await auction.update_one({"_id": result.inserted_id}, {"$set": {"pin_msg_id": msg.id}})

    # Send to SUPPORT_CHANNEL
    if char.get("video_url"):
        await client.send_video(SUPPORT_CHANNEL, char["video_url"], caption=caption)
    else:
        await client.send_photo(SUPPORT_CHANNEL, char["img_url"], caption=caption)

    await message.reply(f"Auction started for character: {char['name']} (ID: {char['id']})")

# Rarity Callback
@app.on_callback_query(filters.regex(r"^auction_rarity_(.+)$"))
async def select_rarity(client: Client, query: CallbackQuery):
    rarity = query.matches[0].group(1)

    # Get a random character with selected rarity
    char = await collection.aggregate([
        {"$match": {"rarity": rarity}},
        {"$sample": {"size": 1}}
    ]).to_list(1)

    if not char:
        return await query.answer("No character found for this rarity!", show_alert=True)

    char = char[0]
    char["_id"] = str(char["_id"])
    auction_data = {
        "char": char,
        "start_time": datetime.utcnow(),
        "highest_bid": 0,
        "highest_user": None,
        "bidders": [],
        "pin_msg_id": None,
        "last_bid_time": datetime.utcnow()
    }

    await auction.delete_many({})
    result = await auction.insert_one(auction_data)

    # Reset bid counts for new auction
    global user_bid_counts
    user_bid_counts = {}

    caption = (
        f"**⏳ AUCTION HAS BEGUN!**\n\n"
        f"🏷️ **Name:** `{char['name']}`\n"
        f"🧬 **Anime:** `{char['anime']}`\n"
        f"✨ **Rarity:** {char['rarity']}\n\n"
    )

    # Special rules for Summer[Su]
    if char['rarity'] == "☀️ Summer[Su]":
        caption += (
            f"💰 **Starting Bid:** `100,000,000` coins\n"
            f"⚠️ **Special Rules:**\n"
            f"- Max 3 bids per user\n"
            f"- If no bid in 1 minute, character will be removed\n\n"
        )
    else:
        caption += "To participate, use the command: `/bid [amount]`\n"

    # Post and pin in SUPPORT_GROUP
    if char.get("video_url"):
        msg = await client.send_video(SUPPORT_GROUP, char["video_url"], caption=caption)
    else:
        msg = await client.send_photo(SUPPORT_GROUP, char["img_url"], caption=caption)

    await msg.pin(disable_notification=True)

    # Save pin message ID
    await auction.update_one({"_id": result.inserted_id}, {"$set": {"pin_msg_id": msg.id}})

    # Send to SUPPORT_CHANNEL
    if char.get("video_url"):
        await client.send_video(SUPPORT_CHANNEL, char["video_url"], caption=caption)
    else:
        await client.send_photo(SUPPORT_CHANNEL, char["img_url"], caption=caption)

    await query.answer("Auction has begun! Let the battle begin!")

# /bid command
@app.on_message(filters.command("bid"))
async def bid_command(client: Client, message: Message):
    user = message.from_user
    try:
        amount = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply("Usage: /bid [amount]")

    auction_data = await auction.find_one()
    if not auction_data:
        return await message.reply("No auction is currently running.")

    char = auction_data["char"]
    char_rarity = char["rarity"]

    # Enforce minimum 100,000,000 bid for ☀️ Summer[Su]
    if char_rarity == "☀️ Summer[Su]":
        if amount < 10000000000:
            return await message.reply("☀️ Summer[Su] characters require a minimum bid of 100,000,000 coins!")
        
        # Track bid counts
        user_bid_counts[user.id] = user_bid_counts.get(user.id, 0) + 1
        if user_bid_counts[user.id] > 3:
            return await message.reply("You've reached your maximum bid limit (3) for this ☀️ Summer[Su] character!")

    if amount <= auction_data["highest_bid"]:
        return await message.reply("Bid must be higher than the current highest bid!")

    user_data = await user_collection.find_one({"id": user.id})
    if not user_data:
        return await message.reply("You don't have an account. Please create one first.")

    # Fix user's balance if corrupted
    raw_balance = user_data.get("balance", 0)
    try:
        balance = int(raw_balance)
    except:
        balance = 0
        await user_collection.update_one({"id": user.id}, {"$set": {"balance": balance}})

    if balance < amount:
        return await message.reply("You don't have enough coins!")

    # Refund previous highest bidder
    prev_highest_user_id = auction_data.get("highest_user")
    prev_bid_amount = auction_data.get("highest_bid", 0)

    if prev_highest_user_id and prev_highest_user_id != user.id:
        prev_user_data = await user_collection.find_one({"id": prev_highest_user_id})
        if prev_user_data:
            prev_raw_balance = prev_user_data.get("balance", 0)
            try:
                prev_balance = int(prev_raw_balance)
            except:
                prev_balance = 0
            await user_collection.update_one(
                {"id": prev_highest_user_id},
                {"$set": {"balance": prev_balance + prev_bid_amount}}
            )
            try:
                await client.send_message(
                    prev_highest_user_id,
                    f"❌ You've been outbid by {user.mention}.\nYour `{prev_bid_amount}` coins have been refunded."
                )
            except:
                pass

    # Deduct coins from current user
    await user_collection.update_one({"id": user.id}, {"$set": {"balance": balance - amount}})

    # Update auction data
    await auction.update_one({}, {
        "$set": {
            "highest_bid": amount,
            "highest_user": user.id,
            "last_bid_time": datetime.utcnow()
        },
        "$push": {
            "bidders": {
                "user_id": user.id,
                "amount": amount,
                "time": datetime.utcnow()
            }
        }
    })

    msg = (
        f"🧨 **New Bid Placed!**\n\n"
        f"👤 {user.mention} placed a bid of `{amount}` coins for `{char['name']}`!"
    )

    await client.send_message(SUPPORT_GROUP, msg)
    await client.send_message(SUPPORT_CHANNEL, msg)

    auction_state["last_bid_time"] = datetime.utcnow()
    auction_state["last_bid_user"] = user.id

# Background task: Auto-close auction
async def monitor_auction():
    while True:
        auction_data = await auction.find_one()
        if auction_data:
            char = auction_data["char"]
            last_bid_time = auction_data.get("last_bid_time", auction_data["start_time"])
            time_since_last_bid = datetime.utcnow() - last_bid_time
            
            # Special case for Summer[Su] - 1 minute timeout if no bids
            if char["rarity"] == "☀️ Summer[Su]":
                if datetime.utcnow() - auction_data["start_time"] >= timedelta(minutes=1) and auction_data["highest_bid"] == 0:
                    # No bids within 1 minute - cancel auction
                    await auction.delete_many({})
                    
                    # Try to unpin message
                    pin_msg_id = auction_data.get("pin_msg_id")
                    if pin_msg_id:
                        try:
                            await app.unpin_chat_message(SUPPORT_GROUP, pin_msg_id)
                        except Exception as e:
                            print("Unpin failed:", e)
                    
                    caption = (
                        f"**❌ Auction Canceled!**\n\n"
                        f"🏷️ **Name:** `{char['name']}`\n"
                        f"🧬 **Anime:** `{char['anime']}`\n"
                        f"✨ **Rarity:** {char['rarity']}\n\n"
                        f"No bids were placed within 1 minute, so the character has been removed from auction."
                    )
                    
                    if char.get("video_url"):
                        await app.send_video(SUPPORT_GROUP, char["video_url"], caption=caption)
                        await app.send_video(SUPPORT_CHANNEL, char["video_url"], caption=caption)
                    else:
                        await app.send_photo(SUPPORT_GROUP, char["img_url"], caption=caption)
                        await app.send_photo(SUPPORT_CHANNEL, char["img_url"], caption=caption)
                    
                    continue
            
            # Normal case - 2 minutes since last bid
            if auction_data.get("highest_user") and time_since_last_bid >= timedelta(minutes=2):
                winner_id = auction_data["highest_user"]

                # Add character to user's collection
                await user_collection.update_one(
                    {"id": winner_id},
                    {"$push": {"characters": char}},
                    upsert=True
                )

                # Try getting user mention
                try:
                    user = await app.get_users(winner_id)
                    mention = user.mention
                except:
                    mention = f"[{winner_id}](tg://user?id={winner_id})"

                # Try to unpin message
                pin_msg_id = auction_data.get("pin_msg_id")
                if pin_msg_id:
                    try:
                        await app.unpin_chat_message(SUPPORT_GROUP, pin_msg_id)
                    except Exception as e:
                        print("Unpin failed:", e)

                # Clean up auction
                await auction.delete_many({})

                # Caption for win
                caption = (
                    f"**✅ Auction Ended!**\n\n"
                    f"🏆 **Character:** `{char['name']}`\n"
                    f"🧬 **Anime:** `{char['anime']}`\n"
                    f"✨ **Rarity:** {char['rarity']}\n"
                    f"💰 **Winning Bid:** `{auction_data['highest_bid']}`\n"
                    f"👑 **Won by:** {mention}\n\n"
                    f"Character has been added to their collection!"
                )

                # Send result message to both channels
                if char.get("video_url"):
                    await app.send_video(SUPPORT_GROUP, char["video_url"], caption=caption)
                    await app.send_video(SUPPORT_CHANNEL, char["video_url"], caption=caption)
                else:
                    await app.send_photo(SUPPORT_GROUP, char["img_url"], caption=caption)
                    await app.send_photo(SUPPORT_CHANNEL, char["img_url"], caption=caption)

                # DM winner (if bot started)
                try:
                    await app.send_message(winner_id,
                        f"🎉 **Congratulations!**\n"
                        f"You won `{char['name']}` in the auction for `{auction_data['highest_bid']}` coins!\n"
                        f"They have been added to your harem!"
                    )
                except:
                    pass  # Ignore if user hasn't started bot

        await asyncio.sleep(30)

# This launches the monitor on startup
async def startup():
    await asyncio.sleep(3)
    asyncio.create_task(monitor_auction())

asyncio.get_event_loop().create_task(startup())

# /viewauction
@app.on_message(filters.command("viewauction"))
async def view_auction(client: Client, message: Message):
    data = await auction.find_one()
    if not data:
        return await message.reply("⚠️ No auction is currently running.")

    char = data["char"]
    highest_bid = data.get("highest_bid", "No bids yet")
    highest_user_id = data.get("highest_user")

    # Handle highest bidder
    if highest_user_id:
        try:
            user = await client.get_users(highest_user_id)
            bidder_name = user.first_name
            button_text = f"👑 {bidder_name}'s Profile"
        except:
            button_text = "👑 Highest Bidder"
        mention_button = InlineKeyboardMarkup([[
            InlineKeyboardButton(button_text, url=f"https://t.me/{user.username}" if user.username else f"tg://user?id={highest_user_id}")
        ]])
    else:
        mention_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ No bids yet", callback_data="no_bidder")
        ]])

    # Special info for Summer[Su]
    extra_info = ""
    if char['rarity'] == "☀️ Summer[Su]":
        time_since_start = datetime.utcnow() - data["start_time"]
        if highest_bid == 0 and time_since_start >= timedelta(minutes=1):
            extra_info = "\n\n⚠️ **Auction will end soon if no bids are placed!**"
        elif highest_bid == 0:
            remaining = timedelta(minutes=1) - time_since_start
            extra_info = f"\n\n⏳ **Time remaining for first bid:** {remaining.seconds//60}m {remaining.seconds%60}s"

    # Caption
    caption = (
        f"**🎯 Current Auction**\n\n"
        f"🏷️ **Name:** `{char['name']}`\n"
        f"🧬 **Anime:** `{char['anime']}`\n"
        f"✨ **Rarity:** {char['rarity']}\n"
        f"💰 **Highest Bid:** `{highest_bid}`"
        f"{extra_info}"
    )

    # Send media with inline button
    if char.get("video_url"):
        await message.reply_video(char["video_url"], caption=caption, reply_markup=mention_button)
    else:
        await message.reply_photo(char["img_url"], caption=caption, reply_markup=mention_button)

# /bidlist
@app.on_message(filters.command("bidlist"))
async def bid_list(client: Client, message: Message):
    data = await auction.find_one()
    if not data or not data.get("bidders"):
        return await message.reply("No bids placed yet.")

    bidders = data["bidders"]
    sorted_bidders = sorted(bidders, key=lambda x: x["amount"], reverse=True)

    text = "**🏆 Top 10 Bidders:**\n\n"
    count = 1

    for b in sorted_bidders[:10]:
        try:
            user = await client.get_users(b["user_id"])
            name = user.first_name if not user.last_name else f"{user.first_name} {user.last_name}"
            mention = f"[{name}](tg://user?id={user.id})"
        except Exception:
            mention = f"[User](tg://user?id={b['user_id']})"

        text += f"**{count}.** {mention} → 💰 `{b['amount']}` coins\n"
        count += 1

    await message.reply(text)

# /endauction (owner only) - Manually end the current auction
@app.on_message(filters.command("endauction") & filters.user(OWNER_IDS))
async def end_auction(client: Client, message: Message):
    auction_data = await auction.find_one()
    if not auction_data:
        return await message.reply("No auction is currently running.")

    char = auction_data["char"]
    highest_bid = auction_data.get("highest_bid", 0)
    highest_user_id = auction_data.get("highest_user")

    # Try to unpin message
    pin_msg_id = auction_data.get("pin_msg_id")
    if pin_msg_id:
        try:
            await client.unpin_chat_message(SUPPORT_GROUP, pin_msg_id)
        except Exception as e:
            print("Unpin failed:", e)

    if highest_user_id:
        # There was a winning bid - process the winner
        # Add character to user's collection
        await user_collection.update_one(
            {"id": highest_user_id},
            {"$push": {"characters": char}},
            upsert=True
        )

        # Try getting user mention
        try:
            user = await client.get_users(highest_user_id)
            mention = user.mention
        except:
            mention = f"[{highest_user_id}](tg://user?id={highest_user_id})"

        caption = (
            f"**🏁 Auction Ended by Owner!**\n\n"
            f"🏆 **Character:** `{char['name']}`\n"
            f"🧬 **Anime:** `{char['anime']}`\n"
            f"✨ **Rarity:** {char['rarity']}\n"
            f"💰 **Winning Bid:** `{highest_bid}`\n"
            f"👑 **Won by:** {mention}\n\n"
            f"Character has been added to their collection!"
        )

        # DM winner (if bot started)
        try:
            await client.send_message(highest_user_id,
                f"🎉 **Congratulations!**\n"
                f"You won `{char['name']}` in the auction for `{highest_bid}` coins!\n"
                f"They have been added to your harem!"
            )
        except:
            pass  # Ignore if user hasn't started bot
    else:
        # No bids were placed
        caption = (
            f"**❌ Auction Ended by Owner!**\n\n"
            f"🏷️ **Name:** `{char['name']}`\n"
            f"🧬 **Anime:** `{char['anime']}`\n"
            f"✨ **Rarity:** {char['rarity']}\n\n"
            f"No bids were placed, so the character has been removed from auction."
        )

        # Refund any pending bids (shouldn't happen but just in case)
        for bid in auction_data.get("bidders", []):
            bidder_id = bid["user_id"]
            bid_amount = bid["amount"]
            user_data = await user_collection.find_one({"id": bidder_id})
            if user_data:
                raw_balance = user_data.get("balance", 0)
                try:
                    balance = int(raw_balance)
                except:
                    balance = 0
                await user_collection.update_one(
                    {"id": bidder_id},
                    {"$set": {"balance": balance + bid_amount}}
                )

    # Send result message to both channels
    if char.get("video_url"):
        await client.send_video(SUPPORT_GROUP, char["video_url"], caption=caption)
        await client.send_video(SUPPORT_CHANNEL, char["video_url"], caption=caption)
    else:
        await client.send_photo(SUPPORT_GROUP, char["img_url"], caption=caption)
        await client.send_photo(SUPPORT_CHANNEL, char["img_url"], caption=caption)

    # Clean up auction
    await auction.delete_many({})

    await message.reply("Auction ended successfully!")
