from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from pyrogram.enums import ChatType
import random
import asyncio
from Grabber import user_collection, app

# Marketplace channel and support group IDs
MARKETPLACE_CHANNEL = -1003430763556  # Replace with your channel ID
SUPPORT_GROUP = -1002313549356  # Replace with your group ID

# Rarity emojis
RARITY_EMOJIS = {
    "Common": "⚪",
    "Uncommon": "🟢",
    "Rare": "🔵",
    "Epic": "🟣",
    "Legendary": "🟡",
    "Mythical": "🟠",
    "Special": "🔴"
}

# Dictionary to store secret keys (in production, use a database)
marketplace_data = {}

@app.on_message(filters.command("send"))
async def send_to_marketplace(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if user is in required channels
    try:
        member = await app.get_chat_member(MARKETPLACE_CHANNEL, user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
            raise UserNotParticipant
    except UserNotParticipant:
        await message.reply_text(
            f"**Please join our [Marketplace Channel](https://t.me/CaptureMarketplace) to use this feature.**",
            disable_web_page_preview=True
        )
        return
    
    try:
        member = await app.get_chat_member(SUPPORT_GROUP, user_id)
        if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
            raise UserNotParticipant
    except UserNotParticipant:
        await message.reply_text(
            f"**Please join our [Support Group](https://t.me/TheNightTalks) to use this feature.**",
            disable_web_page_preview=True
        )
        return

    if len(message.command) < 3:
        await message.reply_text("**Usage**: /send character_id price")
        return

    char_id = message.command[1]
    try:
        price = int(message.command[2])
        if price < 100:
            await message.reply_text("Minimum price is 100 gold!")
            return
    except ValueError:
        await message.reply_text("Please enter a valid price!")
        return

    # Get user data
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await message.reply_text("You don't have any characters!")
        return

    # Find character
    chars = user.get("characters", [])
    matched = [char for char in chars if str(char.get("id")) == str(char_id)]
    
    if not matched:
        await message.reply_text("You don't own this character!")
        return

    char = matched[0]
    
    # Generate secret key
    secret_key = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))
    
    # Store marketplace data
    marketplace_data[secret_key] = {
        "owner_id": user_id,
        "char_id": char_id,
        "price": price,
        "char_data": char,
        "message_id": None  # Will be set when posted to channel
    }
    
    # Create marketplace post
    rarity_emoji = RARITY_EMOJIS.get(char['rarity'], "⚪")
    post_text = (
        f"**OwO! Check out {message.from_user.mention}'s New Marketplace Listing!**\n\n"
        f"**Anime:** {char['anime']}\n"
        f"**Character ID:** {char['id']}\n"
        f"**Character:** {char['name']}\n"
        f"**Rarity:** {char['rarity']}\n\n"
        f"**Price:** {price} gold\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{secret_key}")]
    ])
    
    # Send to marketplace channel
    try:
        if "video_url" in char:
            msg = await client.send_video(
                MARKETPLACE_CHANNEL,
                char["video_url"],
                caption=post_text,
                reply_markup=keyboard
            )
        else:
            msg = await client.send_photo(
                MARKETPLACE_CHANNEL,
                char["img_url"],
                caption=post_text,
                reply_markup=keyboard
            )
        
        # Update message ID in marketplace data
        marketplace_data[secret_key]["message_id"] = msg.id
        
        # Send confirmation to user
        confirm_text = (
            f"**Your character has been listed in the marketplace!**\n\n"
            f"**Character:** {char['name']}\n"
            f"**Price:** {price} gold\n\n"
            f"**Secret Key:** Check Ur Dm \n"
            f"_(Keep this safe to manage your listing)_"
        )
        
        view_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 View Listing", url=f"https://t.me/c/{str(MARKETPLACE_CHANNEL)[4:]}/{msg.id}")]
        ])
        
        if "video_url" in char:
            await message.reply_video(
                char["video_url"],
                caption=confirm_text,
                reply_markup=view_button
            )
        else:
            await message.reply_photo(
                char["img_url"],
                caption=confirm_text,
                reply_markup=view_button
            )
            
        # Send secret key to user's DM
        try:
            manage_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✏️ Edit Price", callback_data=f"edit_{secret_key}"),
                    InlineKeyboardButton("❌ Delete Listing", callback_data=f"delete_{secret_key}")
                ]
            ])
            
            await client.send_message(
                user_id,
                f"**Marketplace Management Key**\n\n"
                f"**Character:** {char['name']}\n"
                f"**Secret Key:** `{secret_key}`\n\n"
                f"**Use this key with /change command to manage your listing.**",
                reply_markup=manage_keyboard
            )
        except Exception as e:
            print(f"Error sending DM: {e}")
            
    except Exception as e:
        await message.reply_text(f"**Error listing character:** {str(e)}")

@app.on_callback_query(filters.regex(r"^buy_"))
async def buy_character(client: Client, callback: CallbackQuery):
    secret_key = callback.data.split("_")[1]
    listing = marketplace_data.get(secret_key)
    
    if not listing:
        await callback.answer("❌ Listing no longer available!", show_alert=True)
        return
    
    buyer_id = callback.from_user.id
    owner_id = listing["owner_id"]
    char_id = listing["char_id"]
    price = listing["price"]
    char_data = listing["char_data"]
    
    if buyer_id == owner_id:
        await callback.answer("🤨 You can't buy your own character!", show_alert=True)
        return
    
    # Get buyer data
    buyer = await user_collection.find_one({"id": buyer_id})
    if not buyer or buyer.get("gold", 0) < price:
        await callback.answer("❌ You don't have enough gold!", show_alert=True)
        return
    
    # Get owner data
    owner = await user_collection.find_one({"id": owner_id})
    if not owner:
        await callback.answer("❌ Owner not found!", show_alert=True)
        return
    
    # Check if character still exists with owner
    owner_chars = owner.get("characters", [])
    char_exists = any(str(c.get("id")) == str(char_id) for c in owner_chars)
    
    if not char_exists:
        await callback.answer("❌ Character no longer available!", show_alert=True)
        return
    
    # Start transaction
    try:
        # Remove character from owner
        await user_collection.update_one(
            {"id": owner_id},
            {"$pull": {"characters": {"id": char_id}}}
        )
        
        # Add character to buyer
        await user_collection.update_one(
            {"id": buyer_id},
            {"$push": {"characters": char_data}},
            upsert=True
        )
        
        # Transfer gold
        await user_collection.update_one(
            {"id": owner_id},
            {"$inc": {"gold": price}}
        )
        
        await user_collection.update_one(
            {"id": buyer_id},
            {"$inc": {"gold": -price}}
        )
        
        # Update marketplace post
        sold_text = (
            f"**SOLD!** {callback.from_user.mention} has purchased this character!\n\n"
            f"**Character:** {char_data['name']}\n"
            f"**Price:** {price} gold\n"
            f"**Transaction completed!**"
        )
        
        try:
            await client.edit_message_caption(
                MARKETPLACE_CHANNEL,
                listing["message_id"],
                caption=sold_text
            )
        except Exception as e:
            print(f"Error editing message: {e}")
        
        # Notify owner
        try:
            notify_text = (
                f"**🎉 Your character has been sold!**\n\n"
                f"**Character:** {char_data['name']}\n"
                f"**Buyer:** {callback.from_user.mention}\n"
                f"**Price:** {price} gold\n\n"
                f"**{price} gold has been added to your balance!**"
            )
            
            if "video_url" in char_data:
                await client.send_video(
                    owner_id,
                    char_data["video_url"],
                    caption=notify_text
                )
            else:
                await client.send_photo(
                    owner_id,
                    char_data["img_url"],
                    caption=notify_text
                )
        except Exception as e:
            print(f"Error notifying owner: {e}")
        
        # Notify buyer
        try:
            notify_text = (
                f"**🎉 You've acquired a new character!**\n\n"
                f"**Character:** {char_data['name']}\n"
                f"**From:** {(await client.get_users(owner_id)).mention}\n"
                f"**Price:** {price} gold\n\n"
                f"**Enjoy your new character!**"
            )
            
            if "video_url" in char_data:
                await client.send_video(
                    buyer_id,
                    char_data["video_url"],
                    caption=notify_text
                )
            else:
                await client.send_photo(
                    buyer_id,
                    char_data["img_url"],
                    caption=notify_text
                )
        except Exception as e:
            print(f"Error notifying buyer: {e}")
        
        # Remove from marketplace
        if secret_key in marketplace_data:
            del marketplace_data[secret_key]
        
        await callback.answer("✅ Purchase successful!", show_alert=True)
        
    except Exception as e:
        await callback.answer("❌ Transaction failed! Please try again.", show_alert=True)
        print(f"Transaction error: {e}")

@app.on_message(filters.command("change"))
async def change_listing(client: Client, message: Message):
    try:
        # Fix for DM check - use proper ChatType comparison
        if message.chat.type != ChatType.PRIVATE:
            await message.reply("**This command only works in bot's private messages!**", quote=True)
            return
        
        if len(message.command) < 2:
            await message.reply("**Usage:** `/change secret_key`", quote=True)
            return
        
        secret_key = message.command[1]
        listing = marketplace_data.get(secret_key)
        
        if not listing:
            await message.reply("**Invalid secret key or listing expired!**", quote=True)
            return
        
        if listing["owner_id"] != message.from_user.id:
            await message.reply("**This is not your listing!**", quote=True)
            return
        
        char_data = listing["char_data"]
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✏️ Edit Price", callback_data=f"edit_{secret_key}"),
                InlineKeyboardButton("❌ Delete Listing", callback_data=f"delete_{secret_key}")
            ],
            [InlineKeyboardButton("🔍 View Listing", url=f"https://t.me/c/{str(abs(MARKETPLACE_CHANNEL))}/{listing['message_id']}")]
        ])
        
        await message.reply(
            f"**Manage Your Marketplace Listing**\n\n"
            f"**Character:** {char_data['name']}\n"
            f"**Current Price:** {listing['price']} gold\n\n"
            f"**Choose an option below:**",
            reply_markup=keyboard,
            quote=True
        )
    
    except Exception as e:
        await message.reply(f"**An error occurred:** {str(e)}", quote=True)

@app.on_callback_query(filters.regex(r"^edit_"))
async def edit_price(client: Client, callback: CallbackQuery):
    secret_key = callback.data.split("_")[1]
    listing = marketplace_data.get(secret_key)
    
    if not listing:
        await callback.answer("❌ Listing no longer available!", show_alert=True)
        return
    
    if listing["owner_id"] != callback.from_user.id:
        await callback.answer("❌ This is not your listing!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"**Enter new price for {listing['char_data']['name']}:**\n"
        f"(Current price: {listing['price']} gold)\n\n"
        f"**Send just the number (e.g., 50000)**"
    )
    
    # Store state for price change
    user_collection.update_one(
        {"id": callback.from_user.id},
        {"$set": {"marketplace_edit": secret_key}}
    )

@app.on_message(filters.private & filters.regex(r"^\d+$"))
async def process_new_price(client: Client, message: Message):
    user_id = message.from_user.id
    user = await user_collection.find_one({"id": user_id})
    
    if not user or not user.get("marketplace_edit"):
        return
    
    secret_key = user["marketplace_edit"]
    listing = marketplace_data.get(secret_key)
    
    if not listing:
        await message.reply_text("**Listing no longer available!**")
        return
    
    try:
        new_price = int(message.text)
        if new_price < 100:
            await message.reply_text("**Minimum price is 100 gold!**")
            return
    except ValueError:
        await message.reply_text("**Please enter a valid number!**")
        return
    
    # Update price
    marketplace_data[secret_key]["price"] = new_price
    
    # Update marketplace post
    char_data = listing["char_data"]
    rarity_emoji = RARITY_EMOJIS.get(char_data['rarity'], "⚪")
    
    post_text = (
        f"**OwO! Check out {message.from_user.mention}'s New Marketplace Listing!**\n\n"
        f"**Anime:** {char_data['anime']}\n"
        f"**Character ID:** {char_data['id']}\n"
        f"**Character:** {char_data['name']}\n"
        f"**Rarity:** {rarity_emoji} {char_data['rarity']}\n\n"
        f"**Price:** {new_price} gold\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{secret_key}")]
    ])
    
    try:
        await client.edit_message_caption(
            MARKETPLACE_CHANNEL,
            listing["message_id"],
            caption=post_text,
            reply_markup=keyboard
        )
        
        await message.reply_text(
            f"**✅ Price updated successfully!**\n\n"
            f"**New price:** {new_price} gold",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 View Listing", url=f"https://t.me/c/{str(MARKETPLACE_CHANNEL)[4:]}/{listing['message_id']}")]
            ])
        )
    except Exception as e:
        await message.reply_text(f"**Error updating price:** {str(e)}")
    
    # Clear edit state
    await user_collection.update_one(
        {"id": user_id},
        {"$unset": {"marketplace_edit": ""}}
    )

@app.on_callback_query(filters.regex(r"^delete_"))
async def delete_listing(client: Client, callback: CallbackQuery):
    secret_key = callback.data.split("_")[1]
    listing = marketplace_data.get(secret_key)
    
    if not listing:
        await callback.answer("❌ Listing no longer available!", show_alert=True)
        return
    
    if listing["owner_id"] != callback.from_user.id:
        await callback.answer("❌ This is not your listing!", show_alert=True)
        return
    
    # Delete marketplace post
    try:
        await client.delete_messages(
            MARKETPLACE_CHANNEL,
            listing["message_id"]
        )
    except Exception as e:
        print(f"Error deleting message: {e}")
    
    # Remove from marketplace data
    if secret_key in marketplace_data:
        del marketplace_data[secret_key]
    
    await callback.message.edit_text(
        f"**🗑 Listing deleted successfully!**\n\n"
        f"**Character:** {listing['char_data']['name']}\n"
        f"**Your character is no longer listed in the marketplace.**"
    )
    
    await callback.answer("✅ Listing deleted!", show_alert=True)
