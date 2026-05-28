from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.types import InputMediaPhoto, InputMediaVideo  # Add this import at top

import random
import humanize
from Grabber import user_collection, collection, app

# Constants
MIN_SALE_PRICE = 10000
MAX_SALE_PRICE = 500000
MAX_SALES_SLOT = 10
ITEMS_PER_PAGE = 5

# Tiny caps format with bold support
TINY_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ', ' ': ' '
}

# Emoji variations
RARITY_EMOJIS = {
    'Common': '⚫', 
    'Limited Edition': '🔮', 
    'Premium': '🫧', 
    'Mythic': '💮',
    'Godly': '🔱', 
    'Legendary': '🟡', 
    'Epic': '🟣', 
    'Rare': '🟠', 
    'Uncommon': '🟤',
    'Exotic': '🏵️', 
    'Unique': '⚜️', 
    'Eternal': '⚡', 
    'Radiant': '🌸',
    'Divine': '💠', 
    'Celestial': '🎐', 
    'Electra': '🌩️', 
    'Galaxia': '🧿',
    'Summer[Su]': '☀️', 
    'Animation': '🧬'
}

def format_text(text: str) -> str:
    """Convert text to tiny caps with optional bold formatting"""
    result = []
    bold = False
    for char in text:
        if char == '*':
            bold = not bold
            result.append('**' if bold else '**')
        else:
            if bold:
                result.append(f'**{TINY_CAPS.get(char.lower(), char)}**')
            else:
                result.append(TINY_CAPS.get(char.lower(), char))
    return ''.join(result)

async def get_rarity_emoji(rarity: str) -> str:
    """Get emoji for rarity"""
    return RARITY_EMOJIS.get(rarity.lower(), "▪️")

async def get_user_currency(user_id: int):
    """Get user's currency with formatting"""
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        return 0, "💎"
    
    rubies = user_data.get('rubies', 0)
    try:
        rubies = float(str(rubies).replace(',', '')) if isinstance(rubies, str) else float(rubies)
    except (ValueError, TypeError):
        rubies = 0.0
        
    return humanize.intcomma(rubies), "💎"

# Helper function to send media with fallback
async def send_media(message, character_data, caption, reply_markup):
    try:
        # Try video first if available
        if character_data.get('video_url'):
            try:
                await message.reply_video(
                    video=character_data['video_url'],
                    caption=caption,
                    reply_markup=reply_markup
                )
                return True
            except Exception as video_error:
                print(f"Video send failed, trying image: {video_error}")
                # Fall through to image if video fails
        
        # Try image if available (either as fallback or primary)
        if character_data.get('img_url'):
            try:
                await message.reply_photo(
                    photo=character_data['img_url'],
                    caption=caption,
                    reply_markup=reply_markup
                )
                return True
            except Exception as photo_error:
                print(f"Image send failed: {photo_error}")
                # Fall through to text
        
        # If both fail, send as text
        await message.reply(
            text=caption,
            reply_markup=reply_markup
        )
        return True
        
    except Exception as e:
        print(f"Complete media send failure: {e}")
        return False

@app.on_message(filters.command("sale"))
async def sale_command(client, message):
    user_id = message.from_user.id
        
    if len(message.command) != 3:
        await message.reply(format_text("*ᴜsᴀɢᴇ:* `/sale (ᴄʜᴀʀᴀᴄᴛᴇʀ_ɪᴅ) (ᴀᴍᴏᴜɴᴛ)`"))
        return

    character_id = message.command[1]
    try:
        sale_price = int(message.command[2])
    except ValueError:
        await message.reply(format_text("*ᴛʜᴇ sᴀʟᴇ ᴘʀɪᴄᴇ ᴍᴜsᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ!*"))
        return

    if not (MIN_SALE_PRICE <= sale_price <= MAX_SALE_PRICE):
        await message.reply(
            format_text(f"*ᴛʜᴇ sᴀʟᴇ ᴘʀɪᴄᴇ ᴍᴜsᴛ ʙᴇ ʙᴇᴛᴡᴇᴇɴ {MIN_SALE_PRICE} ᴀɴᴅ {MAX_SALE_PRICE} ᴛᴏᴋᴇɴs!*")
        )
        return

    user = await user_collection.find_one({'id': user_id})
    if not user:
        await message.reply(format_text("*ʏᴏᴜ ʜᴀᴠᴇ ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀs ɪɴ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!*"))
        return

    character = next(
        (char for char in user.get('characters', []) if char['id'] == character_id), None
    )
    if not character:
        await message.reply(format_text(f"*ᴄʜᴀʀᴀᴄᴛᴇʀ ᴡɪᴛʜ ɪᴅ {character_id} ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!*"))
        return

    sales_slot = user.get('sales_slot', [])
    if len(sales_slot) >= MAX_SALES_SLOT:
        await message.reply(format_text("*ʏᴏᴜʀ sᴀʟᴇs sʟᴏᴛ ɪs ғᴜʟʟ! ʀᴇᴍᴏᴠᴇ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴛᴏ ᴀᴅᴅ ᴀ ɴᴇᴡ ᴏɴᴇ.*"))
        return

    # Add sale details
    character['sprice'] = sale_price
    sales_slot.append(character)

    await user_collection.update_one(
        {'id': user_id}, {'$set': {'sales_slot': sales_slot}}
    )

    # Get full character data
    char_data = await collection.find_one({'id': character_id}) or {}
    
    # Prepare caption with proper rarity display
    rarity_name = character.get('rarity', 'Common')
    rarity_emoji = RARITY_EMOJIS.get(rarity_name, '▪️')
    
    caption = format_text(
        f"**🥂 ᴏᴡᴏ! ᴀᴅᴅᴇᴅ ᴛᴏ sᴀʟᴇ**\n\n"
        f"**📛 ɴᴀᴍᴇ:** {character['name']}\n"
        f"**📺 ᴀɴɪᴍᴇ:** {character['anime']}\n"
        f"**🎗 ʀᴀʀɪᴛʏ:** {rarity_emoji} {rarity_name.title()}\n"
        f"**🆔 ɪᴅ:** `{character_id}`\n"
        f"**💰 ᴘʀɪᴄᴇ:** {humanize.intcomma(sale_price)} ᴛᴏᴋᴇɴs"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(format_text("ᴠɪᴇᴡ ᴍʏ sᴛᴏʀᴇ"), callback_data=f"mystore_{user_id}_1")]
    ])
    
    # Send media with proper fallback handling
    success = False
    if char_data.get('video_url'):
        try:
            await message.reply_video(
                video=char_data['video_url'],
                caption=caption,
                reply_markup=buttons
            )
            success = True
        except Exception as e:
            print(f"Failed to send video: {e}")
    
    if not success and char_data.get('img_url'):
        try:
            await message.reply_photo(
                photo=char_data['img_url'],
                caption=caption,
                reply_markup=buttons
            )
            success = True
        except Exception as e:
            print(f"Failed to send image: {e}")
    
    if not success:
        await message.reply(
            text=caption,
            reply_markup=buttons
        )

@app.on_message(filters.command("mystore"))
async def my_store_command(client, message):
    user_id = message.from_user.id
    page = 1
    
    if len(message.command) > 1:
        try:
            page = int(message.command[1])
        except ValueError:
            pass
            
    await show_store_page(client, message, user_id, user_id, page)

async def show_store_page(client, message, owner_id, viewer_id, page):
    owner = await user_collection.find_one({'id': owner_id})
    if not owner or not owner.get('sales_slot'):
        await message.reply(format_text("*ᴛʜɪs ᴜsᴇʀ ʜᴀs ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀs ғᴏʀ sᴀʟᴇ!*"))
        return

    sales = owner['sales_slot']
    total_pages = max(1, (len(sales) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_sales = sales[start_idx:end_idx]
    
    if not page_sales:
        await message.reply(format_text("*ɴᴏ ɪᴛᴇᴍs ғᴏᴜɴᴅ ғᴏʀ ᴛʜɪs ᴘᴀɢᴇ!*"))
        return

    char_data = await collection.find_one({'id': page_sales[0]['id']}) or {}
    
    rarity_name = page_sales[0].get('rarity', 'Common')
    rarity_emoji = RARITY_EMOJIS.get(rarity_name, '▪️')
    
    caption = format_text(
        f"**🛍 {owner.get('first_name', 'Unknown')}'s sᴛᴏʀᴇ**\n"
        f"**📊 ɪᴛᴇᴍs:** {len(sales)} | **📑 ᴘᴀɢᴇ:** {page}/{total_pages}\n\n"
        f"**📛 ɴᴀᴍᴇ:** {page_sales[0]['name']}\n"
        f"**📺 ᴀɴɪᴍᴇ:** {page_sales[0]['anime']}\n"
        f"**🎗 ʀᴀʀɪᴛʏ:** {rarity_emoji} {rarity_name.title()}\n"
        f"**🆔 ɪᴅ:** `{page_sales[0]['id']}`\n"
        f"**💰 ᴘʀɪᴄᴇ:** {humanize.intcomma(page_sales[0]['sprice'])} ᴛᴏᴋᴇɴs"
    )
    
    # Create buttons list with proper structure
    buttons = []
    
    # Action button (Remove/Buy)
    action_button = []
    if owner_id == viewer_id:
        action_button.append(InlineKeyboardButton(
            format_text("ʀᴇᴍᴏᴠᴇ"), 
            callback_data=f"remove_{page_sales[0]['id']}"
        ))
    else:
        viewer_rubies, currency_emoji = await get_user_currency(viewer_id)
        action_button.append(InlineKeyboardButton(
            format_text(f"ʙᴜʏ ({humanize.intcomma(page_sales[0]['sprice'])} {currency_emoji})"), 
            callback_data=f"buy_{page_sales[0]['id']}_{owner_id}"
        ))
    buttons.append(action_button)
    
    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ ᴘʀᴇᴠ", 
            callback_data=f"store_{owner_id}_{viewer_id}_{page-1}"
        ))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            "ɴᴇxᴛ ➡️", 
            callback_data=f"store_{owner_id}_{viewer_id}_{page+1}"
        ))
    
    if nav_buttons:  # Only add navigation row if there are buttons
        buttons.append(nav_buttons)
    
    # Close button
    buttons.append([InlineKeyboardButton(
        format_text("ᴄʟᴏsᴇ"), 
        callback_data=f"close_{viewer_id}"
    )])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # Try to edit existing message if it's from our bot
    try:
        if hasattr(message, 'from_user') and message.from_user.is_self:
            if char_data.get('video_url'):
                await message.edit_media(
                    InputMediaVideo(char_data['video_url'], caption=caption),
                    reply_markup=reply_markup
                )
                return
            elif char_data.get('img_url'):
                await message.edit_media(
                    InputMediaPhoto(char_data['img_url'], caption=caption),
                    reply_markup=reply_markup
                )
                return
            else:
                await message.edit_text(caption, reply_markup=reply_markup)
                return
    except Exception as e:
        print(f"Edit failed: {e}")

    # Send new message if edit fails or not our message
    try:
        if char_data.get('video_url'):
            await message.reply_video(
                video=char_data['video_url'],
                caption=caption,
                reply_markup=reply_markup
            )
        elif char_data.get('img_url'):
            await message.reply_photo(
                photo=char_data['img_url'],
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await message.reply(
                text=caption,
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Error sending message: {e}")
        await message.reply(
            text=caption,
            reply_markup=reply_markup
    )

@app.on_callback_query(filters.regex(r"store_(\d+)_(\d+)_(\d+)"))
async def store_navigation_callback(client, callback_query):
    owner_id = int(callback_query.matches[0].group(1))
    viewer_id = int(callback_query.matches[0].group(2))
    page = int(callback_query.matches[0].group(3))
    
    if callback_query.from_user.id != viewer_id:
        await callback_query.answer(format_text("ᴛʜɪs ɪs ɴᴏᴛ ғᴏʀ ʏᴏᴜ!"), show_alert=True)
        return
    
    await callback_query.answer()
    await show_store_page(client, callback_query.message, owner_id, viewer_id, page)

@app.on_callback_query(filters.regex(r"buy_(\d+)_(\d+)"))
async def buy_callback(client, callback_query):
    character_id = callback_query.matches[0].group(1)
    seller_id = int(callback_query.matches[0].group(2))
    buyer_id = callback_query.from_user.id
    
    # Get buyer and seller data
    buyer = await user_collection.find_one({'id': buyer_id})
    seller = await user_collection.find_one({'id': seller_id})
    
    if not buyer or not seller:
        await callback_query.answer(format_text("ᴜsᴇʀ ᴅᴀᴛᴀ ɴᴏᴛ ғᴏᴜɴᴅ!"), show_alert=True)
        return

    # Find the sale
    sale = next((s for s in seller.get('sales_slot', []) if s['id'] == character_id), None)
    if not sale:
        await callback_query.answer(format_text("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏ ʟᴏɴɢᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ!"), show_alert=True)
        return

    # Check buyer's balance
    buyer_rubies = buyer.get('rubies', 0)
    if buyer_rubies < sale['sprice']:
        await callback_query.answer(format_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ᴛᴏᴋᴇɴs!"), show_alert=True)
        return

    # Perform transaction
    try:
        # Remove from seller's sales slot and characters
        await user_collection.update_one(
            {'id': seller_id},
            {
                '$pull': {
                    'sales_slot': {'id': character_id},
                    'characters': {'id': character_id}
                },
                '$inc': {'rubies': sale['sprice']}
            }
        )
        
        # Add to buyer's characters and deduct rubies
        sale_copy = sale.copy()
        sale_copy.pop('sprice', None)
        
        await user_collection.update_one(
            {'id': buyer_id},
            {
                '$push': {'characters': sale_copy},
                '$inc': {'rubies': -sale['sprice']}
            }
        )
        
        # Notify both parties
        seller_name = seller.get('first_name', 'Unknown')
        buyer_name = callback_query.from_user.first_name
        
        success_msg = format_text(
            f"**✨ ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟ!**\n\n"
            f"**ʏᴏᴜ ʙᴏᴜɢʜᴛ:** {sale['name']}\n"
            f"**ғʀᴏᴍ:** {seller_name}\n"
            f"**ғᴏʀ:** {humanize.intcomma(sale['sprice'])} ᴛᴏᴋᴇɴs\n"
            f"**ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ:** `{character_id}`"
        )
        
        await callback_query.message.edit_text(
            success_msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(format_text("ᴄʟᴏsᴇ"), callback_data=f"close_{buyer_id}")]
            ])
        )
        
        # Notify seller
        try:
            await client.send_message(
                seller_id,
                format_text(
                    f"**🎉 sᴀʟᴇ ɴᴏᴛɪғɪᴄᴀᴛɪᴏɴ!**\n\n"
                    f"**ʏᴏᴜ sᴏʟᴅ:** {sale['name']}\n"
                    f"**ᴛᴏ:** {buyer_name}\n"
                    f"**ғᴏʀ:** {humanize.intcomma(sale['sprice'])} ᴛᴏᴋᴇɴs\n"
                    f"**ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ:** `{character_id}`"
                )
            )
        except Exception:
            pass
            
    except Exception as e:
        print(f"Error in purchase: {e}")
        await callback_query.answer(format_text("ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ғᴀɪʟᴇᴅ!"), show_alert=True)

@app.on_callback_query(filters.regex(r"remove_(\d+)"))
async def remove_sale_callback(client, callback_query):
    character_id = callback_query.matches[0].group(1)
    user_id = callback_query.from_user.id
    
    # Remove from sales slot
    result = await user_collection.update_one(
        {'id': user_id},
        {'$pull': {'sales_slot': {'id': character_id}}}
    )
    
    if result.modified_count == 0:
        await callback_query.answer(format_text("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ʏᴏᴜʀ sᴀʟᴇs!"), show_alert=True)
        return
    
    await callback_query.answer(format_text("ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ sᴀʟᴇs!"), show_alert=True)
    await show_store_page(client, callback_query.message, user_id, user_id, 1)

@app.on_callback_query(filters.regex(r"close_(\d+)"))
async def close_callback(client, callback_query):
    user_id = int(callback_query.matches[0].group(1))
    if callback_query.from_user.id != user_id:
        await callback_query.answer(format_text("ᴛʜɪs ɪs ɴᴏᴛ ғᴏʀ ʏᴏᴜ!"), show_alert=True)
        return
    
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer(format_text("ᴍᴇssᴀɢᴇ ᴀʟʀᴇᴀᴅʏ ᴅᴇʟᴇᴛᴇᴅ!"), show_alert=True)

@app.on_message(filters.command("sales"))
async def sales_command(client, message):
    user_id = message.from_user.id
        
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) == 2:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            await message.reply(format_text("*ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ ᴘʀᴏᴠɪᴅᴇᴅ!*"))
            return
    else:
        await message.reply(format_text("*ᴜsᴀɢᴇ:* `/sales (ᴜsᴇʀ_ɪᴅ) ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴜsᴇʀ's ᴍᴇssᴀɢᴇ*"))
        return

    if target_user_id == user_id:
        await message.reply(format_text("*ᴜsᴇ /mystore ᴛᴏ ᴠɪᴇᴡ ʏᴏᴜʀ ᴏᴡɴ sᴀʟᴇs!*"))
        return

    await show_store_page(client, message, target_user_id, user_id, 1)

@app.on_message(filters.command("randomsales"))
async def random_sales_command(client, message):
    user_id = message.from_user.id

    loading_msg = await message.reply(format_text("**🔍 sᴇᴀʀᴄʜɪɴɢ ғᴏʀ ʀᴀɴᴅᴏᴍ sᴛᴏʀᴇs...**"))
    
    # Get random users with sales
    pipeline = [
        {'$match': {'sales_slot': {'$exists': True, '$ne': []}}},
        {'$sample': {'size': 5}},
        {'$project': {'first_name': 1, 'id': 1, 'sales_count': {'$size': '$sales_slot'}}}
    ]
    
    random_users = await user_collection.aggregate(pipeline).to_list(length=5)
    
    if not random_users:
        await loading_msg.edit(format_text("*ɴᴏ ᴀᴄᴛɪᴠᴇ sᴛᴏʀᴇs ғᴏᴜɴᴅ!*"))
        return

    response = format_text("**🎲 ʀᴀɴᴅᴏᴍ sᴛᴏʀᴇs ᴀᴠᴀɪʟᴀʙʟᴇ:**\n\n")
    buttons = []
    
    for user in random_users:
        response += f"**👤 {user.get('first_name', 'Unknown')}**\n"
        response += f"**🆔** `{user['id']}` | **📦 {user['sales_count']} ɪᴛᴇᴍs**\n\n"
        buttons.append(
            InlineKeyboardButton(
                f"👤 {user.get('first_name', 'Unknown')}",
                callback_data=f"store_{user['id']}_{user_id}_1"
            )
        )

    await loading_msg.edit(
        response,
        reply_markup=InlineKeyboardMarkup([
            buttons,
            [InlineKeyboardButton(format_text("ᴄʟᴏsᴇ"), callback_data=f"close_{user_id}")]
        ])
    )
