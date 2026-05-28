from pyrogram import Client, filters
import random
import time
from datetime import datetime
from . import collection, user_collection, sudo_filter, app, dev_filter, log_channel

async def log_action(action_type, details):
    """Logs actions to channel and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
🕒 **Timestamp:** `{timestamp}`
📝 **Action:** `{action_type}`
{details}
"""
    try:
        await app.send_message(log_channel, log_entry)
    except Exception as e:
        print(f"Failed to log to channel: {e}")
    print(log_entry)

async def give_characters(receiver_id, num_characters, giver_id=None):
    """Gives exact number of random characters (up to 5000) with duplicates if needed"""
    if num_characters <= 0:
        raise ValueError("Number of characters must be positive")
    if num_characters > 5000:
        raise ValueError("Maximum 5000 characters at once")

    # Get all available characters
    characters_list = await collection.find().to_list(length=None)
    if not characters_list:
        raise ValueError("❌ The character database is currently empty.")

    # Select characters (with duplicates if needed)
    selected = []
    if len(characters_list) < num_characters:
        # Not enough unique characters - allow duplicates
        for _ in range(num_characters):
            selected.append(random.choice(characters_list).copy())
    else:
        # Enough unique characters available
        selected = random.sample(characters_list, num_characters)

    # Add metadata
    timestamp = int(time.time())
    for char in selected:
        char['obtained_at'] = timestamp
        if giver_id:
            char['giver_id'] = giver_id

    # Batch insert in chunks of 500 for better performance
    batch_size = 500
    inserted_count = 0
    for i in range(0, len(selected), batch_size):
        batch = selected[i:i + batch_size]
        await user_collection.update_one(
            {'id': receiver_id},
            {'$push': {'characters': {'$each': batch}}},
            upsert=True
        )
        inserted_count += len(batch)

    # Log the transaction
    receiver = await app.get_users(receiver_id)
    log_details = f"""
👤 **Receiver:** [{receiver.first_name}](tg://user?id={receiver.id}) (`{receiver.id}`)
🎁 **Characters Given:** `{inserted_count}`
📊 **Unique Characters in DB:** `{len(characters_list)}`
"""
    if giver_id:
        giver = await app.get_users(giver_id)
        log_details += f"🎩 **Given by:** [{giver.first_name}](tg://user?id={giver.id})"

    await log_action("MASS_CHARACTERS_GIVEN", log_details)

    return {
        'count': inserted_count,
        'receiver': receiver,
        'had_duplicates': len(characters_list) < num_characters
    }

@app.on_message(filters.command(["give"]) & sudo_filter)
async def give_character_command(client, message):
    """Mass give command with progress updates"""
    if not message.reply_to_message:
        return await message.reply("⚠️ Please reply to the target user.\nUsage: `/give 3000`")

    try:
        # Parse arguments
        try:
            num_characters = int(message.command[1]) if len(message.command) > 1 else 1
        except (IndexError, ValueError):
            return await message.reply("⚠️ Invalid number format.\nUsage: `/give 3000`")

        if num_characters <= 0:
            return await message.reply("⚠️ Number must be positive!")
        if num_characters > 5000:
            return await message.reply("⚠️ Maximum 5000 characters at once!")

        # Send initial processing message
        processing_msg = await message.reply(f"⚡ Processing mass gift of {num_characters} characters...")

        # Process the give action
        result = await give_characters(
            receiver_id=message.reply_to_message.from_user.id,
            num_characters=num_characters,
            giver_id=message.from_user.id
        )

        # Prepare success response
        receiver = result['receiver']
        response_msg = f"""
🎉 **Mass Character Transfer Complete!**

• **Recipient:** [{receiver.first_name}](tg://user?id={receiver.id})
• **Total Characters Sent:** `{result['count']}`
"""

        if result['had_duplicates']:
            response_msg += "• **Note:** Some duplicates were included to reach the requested amount\n"

        response_msg += f"""
⚡ **Transfer Speed:** Instant bulk transfer

_Action performed by admin: {message.from_user.mention}_
"""

        await processing_msg.delete()
        await message.reply(response_msg, disable_web_page_preview=True)

    except ValueError as e:
        await message.reply(f"❌ {str(e)}")
    except Exception as e:
        error_msg = f"⚠️ **System Error**\n\n`{type(e).__name__}: {str(e)}`"
        await message.reply(error_msg)
        await log_action("MASS_GIVE_ERROR", f"Error in /give:\n\n{error_msg}")

@app.on_message(filters.command(["anikill"]) & dev_filter)
async def kill_animation_characters(client, message):
    """Directly delete all Animation rarity characters from all collections"""
    try:
        # Immediate execution
        processing_msg = await message.reply("☠️ Executing mass deletion of 🧬 Animation characters...")

        # Get all users who have Animation characters
        users_with_animation = await user_collection.find({
            "characters.rarity": "🧬 Animation"
        }).to_list(length=None)

        total_deleted = 0
        affected_users = 0

        # Process each user
        for user in users_with_animation:
            # Filter out Animation characters
            remaining_chars = [
                char for char in user.get('characters', [])
                if char.get('rarity') != "🧬 Animation"
            ]
            
            # Calculate deletions
            deleted_count = len(user.get('characters', [])) - len(remaining_chars)
            if deleted_count == 0:
                continue
            
            # Update user's collection
            await user_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'characters': remaining_chars}}
            )
            
            total_deleted += deleted_count
            affected_users += 1

        # Result message
        result_msg = f"""
☠️ **Mass Deletion Complete**

• Rarity Purged: 🧬 Animation
• Total Deleted: {total_deleted}
• Affected Users: {affected_users}
• Executed By: {message.from_user.mention}
"""
        await processing_msg.edit(result_msg)

        # Log the action
        await log_action("MASS_DELETION", 
            f"Immediate deletion executed\n"
            f"Deleted {total_deleted} Animation characters\n"
            f"Admin: {message.from_user.id}"
        )

    except Exception as e:
        error_msg = f"⚠️ Immediate Deletion Failed: {str(e)}"
        await message.reply(error_msg)
        await log_action("ANIKILL_FAILED", error_msg)

@app.on_message(filters.command(["giveusers"]) & dev_filter)
async def give_all_users_command(client, message):
    """Gives characters to all users (dev only)"""
    try:
        # Parse arguments
        try:
            num_characters = int(message.command[1]) if len(message.command) > 1 else 1
        except (IndexError, ValueError):
            return await message.reply("⚠️ Invalid number format.\nUsage: `/giveusers 5`")

        if num_characters <= 0:
            return await message.reply("⚠️ Number must be positive!")

        if num_characters > 20:
            return await message.reply("⚠️ For safety, max 20 characters at once!")

        # Get all users
        all_users = await user_collection.distinct("id")
        if not all_users:
            return await message.reply("❌ No users found in the database!")

        total_users = len(all_users)
        processing_msg = await message.reply(f"⏳ Processing {num_characters} characters for {total_users} users...")

        success_count = 0
        failed_users = []

        # Process each user
        for user_id in all_users:
            try:
                await give_characters(
                    receiver_id=user_id,
                    num_characters=num_characters,
                    giver_id=message.from_user.id
                )
                success_count += 1
            except Exception as e:
                failed_users.append((user_id, str(e)))
                continue

        # Prepare report
        report_msg = f"""
📊 **Mass Distribution Complete!**

• **Total Users:** `{total_users}`
• **Successful Distributions:** `{success_count}`
• **Characters Given Per User:** `{num_characters}`
• **Failed Distributions:** `{len(failed_users)}`
"""

        if failed_users:
            report_msg += "\n❌ **Failed Users:**\n"
            for user_id, error in failed_users[:10]:  # Show first 10 failures
                report_msg += f"- `{user_id}`: {error[:50]}\n"
            if len(failed_users) > 10:
                report_msg += f"...and {len(failed_users)-10} more"

        # Send notification to all users
        notification_text = f"""
🎉 **Old Size Bot Harem Recovery**

You have received {num_characters} character(s) in your collection!

All characters have random rarities. Check your collection with /mycollection
"""

        sent_count = 0
        for user_id in all_users:
            try:
                await app.send_message(user_id, notification_text)
                sent_count += 1
            except:
                continue

        report_msg += f"\n📨 **Notifications Sent:** `{sent_count}/{total_users}`"
        report_msg += f"\n\n_Action performed by developer: {message.from_user.mention}_"

        await processing_msg.edit_text(report_msg, disable_web_page_preview=True)

        # Log the action
        log_details = f"""
👨‍💻 **Developer:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})
👥 **Total Users:** `{total_users}`
🎁 **Characters Per User:** `{num_characters}`
✅ **Success Count:** `{success_count}`
❌ **Fail Count:** `{len(failed_users)}`
"""
        await log_action("MASS_CHARACTER_DISTRIBUTION", log_details)

    except Exception as e:
        error_msg = f"⚠️ **System Error**\n\n`{type(e).__name__}: {str(e)}`"
        await message.reply(error_msg)
        await log_action("GIVEUSERS_ERROR", f"Error in /giveusers:\n\n{error_msg}")
        

# Similar advanced implementations for other commands...

@app.on_message(filters.command(["donate"]) & sudo_filter)
async def donate_character_command(client, message):
    """Character donation system without rarity"""
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to user + provide character ID\nUsage: `/donate char123`")

    try:
        if len(message.command) < 2:
            return await message.reply("⚠️ Missing character ID\nUsage: `/donate char123`")

        char_id = message.command[1].strip()
        receiver_id = message.reply_to_message.from_user.id
        giver_id = message.from_user.id

        # Verify character exists
        character = await collection.find_one({'id': char_id})
        if not character:
            return await message.reply(f"❌ Character `{char_id}` not found in global collection!")

        # Check if user already has this character
        user_has_char = await user_collection.count_documents({
            'id': receiver_id,
            'characters.id': char_id
        })
        if user_has_char:
            return await message.reply("⚠️ User already has this character!")

        # Prepare character data
        character.update({
            'donated_at': int(time.time()),
            'donated_by': giver_id
        })

        # Update user collection
        await user_collection.update_one(
            {'id': receiver_id},
            {'$push': {'characters': character}},
            upsert=True
        )

        # Get user details
        receiver = await app.get_users(receiver_id)
        giver = await app.get_users(giver_id)

        # Prepare response
        response = f"""
🎁 **Character Donated Successfully!**

**To:** [{receiver.first_name}](tg://user?id={receiver.id})
**Character:** `{character['name']}`
**From:** {giver.mention}
**Anime:** `{character.get('anime', 'Unknown')}`
**ID:** `{char_id}`

_Use /collection to view your new character!_
"""
        # Send media if available
        if character.get('video_url'):
            await message.reply_video(
                character['video_url'],
                caption=response
            )
        elif character.get('img_url'):
            await message.reply_photo(
                character['img_url'],
                caption=response
            )
        else:
            await message.reply(response)

        # Log the donation
        log_details = f"""
🎁 **Donation Log**
• **Giver:** [{giver.first_name}](tg://user?id={giver.id})
• **Receiver:** [{receiver.first_name}](tg://user?id={receiver.id})
• **Character:** `{character['name']}`
• **ID:** `{char_id}`
"""
        await log_action("CHARACTER_DONATED", log_details)

    except Exception as e:
        error_msg = f"""
⚠️ **Donation Failed**
Error: `{type(e).__name__}`
Details: `{str(e)}`
"""
        await message.reply(error_msg)
        await log_action("DONATION_ERROR", error_msg)

async def remove_characters(user_id, options):
    """
    Character removal with options:
    - count: number to remove
    - mode: 'random' or 'oldest'
    """
    user = await user_collection.find_one({'id': user_id})
    if not user or not user.get('characters'):
        raise ValueError("User has no characters to remove")

    characters = user['characters']
    
    # Determine which characters to remove
    if options.get('mode') == 'oldest':
        # Sort by obtained_at (oldest first)
        characters.sort(key=lambda x: x.get('obtained_at', 0))
        to_remove = characters[:options['count']]
    else:  # random
        to_remove = random.sample(characters, min(options['count'], len(characters)))
    
    # Remove the characters
    await user_collection.update_one(
        {'id': user_id},
        {'$pull': {'characters': {'$or': [{'id': c['id']} for c in to_remove]}}}
    )
    
    return to_remove

@app.on_message(filters.command(["kill"]) & sudo_filter)
async def kill_character_command(client, message):
    """Character removal interface"""
    try:
        if not message.reply_to_message:
            return await message.reply("⚠️ Reply to target user\nUsage: `/kill 2`")

        # Parse command arguments
        args = message.command[1:]
        if not args:
            return await message.reply("⚠️ Specify count\nUsage: `/kill 3`")

        options = {'count': int(args[0])}
        
        # Perform removal
        removed_chars = await remove_characters(
            user_id=message.reply_to_message.from_user.id,
            options=options
        )
        
        # Generate report
        report = "🗑️ **Removed Characters**\n\n"
        report += f"Total: `{len(removed_chars)}` characters removed"
        
        await message.reply(report)
        
        # Log the action
        target = await app.get_users(message.reply_to_message.from_user.id)
        admin = message.from_user
        log_msg = f"""
🗑️ **Character Removal**
• **Admin:** [{admin.first_name}](tg://user?id={admin.id})
• **Target:** [{target.first_name}](tg://user?id={target.id})
• **Count:** `{options['count']}`
"""
        await log_action("CHARACTERS_REMOVED", log_msg)

    except ValueError as e:
        await message.reply(f"❌ {str(e)}")
    except Exception as e:
        await message.reply(f"⚠️ Error: {type(e).__name__}\n{str(e)}")
        await log_action("REMOVAL_ERROR", f"Error in /kill:\n\n{str(e)}")

@app.on_message(filters.command(["erase"]) & sudo_filter)
async def erase_character_command(client, message):
    """Precise character removal by ID"""
    try:
        if not message.reply_to_message:
            return await message.reply("⚠️ Reply to user + provide character ID\nUsage: `/erase char123`")

        if len(message.command) < 2:
            return await message.reply("⚠️ Missing character ID")

        char_id = message.command[1]
        user_id = message.reply_to_message.from_user.id
        
        # Verify the character exists
        user = await user_collection.find_one(
            {'id': user_id, 'characters.id': char_id},
            {'characters.$': 1}
        )
        
        if not user:
            return await message.reply("❌ Character not found in user's collection")

        # Remove the character
        result = await user_collection.update_one(
            {'id': user_id},
            {'$pull': {'characters': {'id': char_id}}}
        )
        
        if result.modified_count == 0:
            return await message.reply("⚠️ No changes made - character may not exist")

        # Get details for logging
        char_data = user['characters'][0]
        target_user = await app.get_users(user_id)
        admin = message.from_user
        
        response = f"""
🚫 **Character Erased**

• **Target User:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Character:** `{char_data.get('name', 'Unknown')}`
• **ID:** `{char_id}`

_Action performed by admin: {admin.mention}_
"""
        await message.reply(response)
        
        # Detailed logging
        log_entry = f"""
🚫 **Character Erasure**
• **Admin:** [{admin.first_name}](tg://user?id={admin.id})
• **Target:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Character ID:** `{char_id}`
• **Character Name:** `{char_data.get('name')}`
• **Anime:** `{char_data.get('anime')}`
"""
        await log_action("CHARACTER_ERASED", log_entry)

    except Exception as e:
        error_template = """
⚠️ **Erase Command Failed**

**Error Type:** `{type}`
**Details:** `{error}`

Please check the format: `/erase character_id` (reply to user)
"""
        await message.reply(error_template.format(
            type=type(e).__name__,
            error=str(e)
        ))
        await log_action("ERASE_ERROR", f"Error in /erase:\n\n{str(e)}")

@app.on_message(filters.command(["massdonate"]) & sudo_filter)
async def mass_donate_command(client, message):
    """Mass donation of multiple characters by IDs with robust error handling"""
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to user + provide character IDs\nUsage: `/massdonate char123 char456 char789`")

    try:
        if len(message.command) < 2:
            return await message.reply("⚠️ Missing character IDs\nUsage: `/massdonate char123 char456 char789`")

        char_ids = [cid.strip() for cid in message.command[1:] if cid.strip()]
        if not char_ids:
            return await message.reply("⚠️ No valid character IDs provided")

        receiver_id = message.reply_to_message.from_user.id
        giver_id = message.from_user.id

        # Verify characters exist and get their data
        characters = []
        invalid_ids = []
        
        for char_id in char_ids:
            try:
                character = await collection.find_one({'id': char_id})
                if not character:
                    invalid_ids.append(char_id)
                    continue
                    
                # Ensure character has required fields
                if 'id' not in character:
                    invalid_ids.append(char_id)
                    continue
                    
                characters.append(character)
            except Exception as e:
                invalid_ids.append(char_id)
                await log_action("MASS_DONATE_WARNING", f"Error processing ID {char_id}: {str(e)}")

        if invalid_ids:
            await message.reply(f"⚠️ Invalid character IDs: {', '.join(invalid_ids)}\nProceeding with valid IDs...")

        if not characters:
            return await message.reply("❌ No valid characters found to donate!")

        # Check which characters user already has
        existing_chars = await user_collection.find_one(
            {'id': receiver_id},
            {'characters.id': 1}
        )
        
        existing_ids = set()
        if existing_chars and 'characters' in existing_chars:
            for char in existing_chars['characters']:
                if 'id' in char:
                    existing_ids.add(char['id'])

        # Prepare characters for donation with all required fields
        donated_chars = []
        skipped = 0
        duplicate_ids = []
        
        for char in characters:
            if not isinstance(char, dict):
                continue
                
            char_id = char.get('id')
            if not char_id:
                continue
                
            if char_id in existing_ids:
                skipped += 1
                duplicate_ids.append(char_id)
                continue
                
            # Ensure all required fields exist
            char_data = {
                'id': char_id,
                'name': char.get('name', 'Unknown'),
                'anime': char.get('anime', 'Unknown'),
                'rarity': char.get('rarity', get_weighted_rarity()),
                'donated_at': int(time.time()),
                'donated_by': giver_id
            }
            
            # Add optional fields if they exist
            for field in ['img_url', 'video_url', 'description']:
                if field in char:
                    char_data[field] = char[field]
                    
            donated_chars.append(char_data)

        if not donated_chars:
            dup_msg = f"\nDuplicate IDs: {', '.join(duplicate_ids)}" if duplicate_ids else ""
            return await message.reply(f"⚠️ User already has all these characters!{dup_msg}")

        # Update user collection with bulk operation
        update_result = await user_collection.update_one(
            {'id': receiver_id},
            {'$push': {'characters': {'$each': donated_chars}}},
            upsert=True
        )

        # Get user details
        receiver = await app.get_users(receiver_id)
        giver = await app.get_users(giver_id)

        # Prepare response
        response = f"""
🎁 **Mass Donation Complete!**

• **Recipient:** [{receiver.first_name}](tg://user?id={receiver.id})
• **Successfully Donated:** `{len(donated_chars)}`
• **Skipped (invalid/duplicate):** `{len(invalid_ids) + skipped}`
• **Donated by:** {giver.mention}
"""

        # Add character list if not too many
        if len(donated_chars) <= 15:
            response += "\n**Donated Characters:**\n"
            for char in donated_chars:
                response += f"- `{char['id']}`: {char.get('name', 'Unknown')} ({char.get('rarity', 'Unknown')})\n"
        else:
            response += f"\n**First 5 IDs:** {', '.join(c['id'] for c in donated_chars[:5])}..."

        if invalid_ids:
            response += f"\n\n⚠️ **Invalid IDs Ignored:** {', '.join(invalid_ids[:5])}{'...' if len(invalid_ids) > 5 else ''}"

        await message.reply(response)

        # Log the donation
        log_details = f"""
🎁 **Mass Donation Log**
• **Giver:** [{giver.first_name}](tg://user?id={giver.id})
• **Receiver:** [{receiver.first_name}](tg://user?id={receiver.id})
• **Total Requested:** `{len(char_ids)}`
• **Successfully Donated:** `{len(donated_chars)}`
• **Invalid IDs:** `{len(invalid_ids)}`
• **Duplicate IDs:** `{skipped}`
"""
        await log_action("MASS_DONATION_SUCCESS", log_details)

    except Exception as e:
        error_msg = f"""
⚠️ **Mass Donation Failed**
Command: `{" ".join(message.command)}`
Error: `{type(e).__name__}`
Details: `{str(e)}`

Please check:
1. All character IDs exist in database
2. No duplicates in the list
3. Proper spacing between IDs
"""
        await message.reply(error_msg)
        await log_action("MASS_DONATION_FAILED", 
            f"Error: {type(e).__name__}\n"
            f"Traceback: {str(e)}\n"
            f"User: {message.from_user.id}\n"
            f"Input: {message.text}"
                        )

@app.on_message(filters.command(["rani"]) & sudo_filter)
async def remove_animated_characters(client, message):
    """Remove animated characters from a user with count"""
    if not message.reply_to_message:
        return await message.reply("⚠️ Please reply to the target user.\nUsage: `/rani 5`")

    try:
        # Parse count argument
        try:
            count = int(message.command[1]) if len(message.command) > 1 else 1
        except (IndexError, ValueError):
            return await message.reply("⚠️ Invalid number format.\nUsage: `/rani 3`")

        if count <= 0:
            return await message.reply("⚠️ Number must be positive!")

        target_user_id = message.reply_to_message.from_user.id
        admin_user_id = message.from_user.id

        # Send processing message
        processing_msg = await message.reply(f"⚡ Removing {count} ⚜️ Animated characters...")

        # Get user's collection
        user_data = await user_collection.find_one({'id': target_user_id})
        if not user_data or not user_data.get('characters'):
            await processing_msg.delete()
            return await message.reply("❌ User has no characters in collection!")

        # Filter animated characters
        animated_chars = [
            char for char in user_data['characters'] 
            if char.get('rarity') == "⚜️ Animated"
        ]

        if not animated_chars:
            await processing_msg.delete()
            return await message.reply("❌ User has no ⚜️ Animated characters!")

        # Limit removal to available animated characters
        actual_remove_count = min(count, len(animated_chars))
        chars_to_remove = animated_chars[:actual_remove_count]

        # Remove characters from user's collection
        char_ids_to_remove = [char['id'] for char in chars_to_remove]
        
        await user_collection.update_one(
            {'id': target_user_id},
            {'$pull': {'characters': {'id': {'$in': char_ids_to_remove}}}}
        )

        # Get user details for response
        target_user = await app.get_users(target_user_id)
        admin_user = message.from_user

        # Prepare response
        response = f"""
🗑️ **Animated Characters Removed**

• **Target User:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Requested Removal:** `{count}`
• **Actual Removed:** `{actual_remove_count}`
• **Remaining Animated:** `{len(animated_chars) - actual_remove_count}`
• **Executed by:** {admin_user.mention}
"""

        if actual_remove_count < count:
            response += f"\n⚠️ Note: Only {actual_remove_count} animated characters were available."

        await processing_msg.edit_text(response)

        # Log the action
        log_details = f"""
🗑️ **Animated Characters Removal**
• **Admin:** [{admin_user.first_name}](tg://user?id={admin_user.id})
• **Target:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Requested:** `{count}`
• **Removed:** `{actual_remove_count}`
• **Character IDs:** {', '.join(char_ids_to_remove[:5])}{'...' if len(char_ids_to_remove) > 5 else ''}
"""
        await log_action("ANIMATED_CHARS_REMOVED", log_details)

    except Exception as e:
        error_msg = f"⚠️ **Removal Failed**\n\nError: `{type(e).__name__}: {str(e)}`"
        try:
            await processing_msg.edit_text(error_msg)
        except:
            await message.reply(error_msg)
        await log_action("RANI_COMMAND_ERROR", f"Error: {str(e)}")

@app.on_message(filters.command(["aani"]) & sudo_filter)
async def give_animated_characters(client, message):
    """Give animated characters to a user with count"""
    if not message.reply_to_message:
        return await message.reply("⚠️ Please reply to the target user.\nUsage: `/aani 5`")

    try:
        # Parse count argument
        try:
            count = int(message.command[1]) if len(message.command) > 1 else 1
        except (IndexError, ValueError):
            return await message.reply("⚠️ Invalid number format.\nUsage: `/aani 3`")

        if count <= 0:
            return await message.reply("⚠️ Number must be positive!")
        if count > 100:
            return await message.reply("⚠️ Maximum 100 animated characters at once!")

        target_user_id = message.reply_to_message.from_user.id
        giver_id = message.from_user.id

        # Send processing message
        processing_msg = await message.reply(f"⚡ Giving {count} ⚜️ Animated characters...")

        # Get all animated characters from global collection
        animated_chars = await collection.find({'rarity': '⚜️ Animated'}).to_list(length=None)
        
        if not animated_chars:
            await processing_msg.delete()
            return await message.reply("❌ No ⚜️ Animated characters found in global database!")

        # Check which animated characters user already has
        user_data = await user_collection.find_one(
            {'id': target_user_id},
            {'characters.id': 1}
        )
        
        existing_animated_ids = set()
        if user_data and 'characters' in user_data:
            user_animated_chars = [
                char for char in user_data['characters'] 
                if char.get('rarity') == '⚜️ Animated'
            ]
            existing_animated_ids = {char['id'] for char in user_animated_chars if 'id' in char}

        # Filter out characters user already has
        available_animated_chars = [
            char for char in animated_chars 
            if char.get('id') not in existing_animated_ids
        ]

        if not available_animated_chars:
            await processing_msg.delete()
            return await message.reply("❌ User already has all available animated characters!")

        # Select characters to give (with duplicates if needed)
        selected_chars = []
        if len(available_animated_chars) < count:
            # Not enough unique animated characters - allow duplicates
            for _ in range(count):
                char_copy = random.choice(available_animated_chars).copy()
                # Generate unique ID for duplicate to avoid conflicts
                char_copy['id'] = f"{char_copy['id']}_dup_{int(time.time())}_{random.randint(1000,9999)}"
                selected_chars.append(char_copy)
        else:
            # Enough unique animated characters available
            selected_chars = random.sample(available_animated_chars, count)

        # Add metadata
        timestamp = int(time.time())
        for char in selected_chars:
            char['obtained_at'] = timestamp
            char['giver_id'] = giver_id

        # Add to user's collection
        await user_collection.update_one(
            {'id': target_user_id},
            {'$push': {'characters': {'$each': selected_chars}}},
            upsert=True
        )

        # Get user details
        target_user = await app.get_users(target_user_id)
        giver_user = message.from_user

        # Prepare response
        response = f"""
🎁 **Animated Characters Given**

• **Recipient:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Characters Given:** `{len(selected_chars)}`
• **Available Unique Animated:** `{len(available_animated_chars)}`
• **Total Animated in DB:** `{len(animated_chars)}`
• **Given by:** {giver_user.mention}
"""

        if len(available_animated_chars) < count:
            response += "• **Note:** Duplicates were included to reach requested amount\n"

        # Show first few character names if not too many
        if len(selected_chars) <= 10:
            response += "\n**Given Characters:**\n"
            for char in selected_chars[:5]:
                original_name = char['name'].replace('_dup_', ' (duplicate)').split('_dup_')[0]
                response += f"- {original_name}\n"
            if len(selected_chars) > 5:
                response += f"- ...and {len(selected_chars) - 5} more\n"

        await processing_msg.edit_text(response)

        # Log the action
        log_details = f"""
🎁 **Animated Characters Given**
• **Giver:** [{giver_user.first_name}](tg://user?id={giver_user.id})
• **Receiver:** [{target_user.first_name}](tg://user?id={target_user.id})
• **Count Given:** `{len(selected_chars)}`
• **Had Duplicates:** `{len(available_animated_chars) < count}`
• **Available Unique:** `{len(available_animated_chars)}`
"""
        await log_action("ANIMATED_CHARS_GIVEN", log_details)

    except Exception as e:
        error_msg = f"⚠️ **Give Animated Failed**\n\nError: `{type(e).__name__}: {str(e)}`"
        try:
            await processing_msg.edit_text(error_msg)
        except:
            await message.reply(error_msg)
        await log_action("AANI_COMMAND_ERROR", f"Error: {str(e)}")
