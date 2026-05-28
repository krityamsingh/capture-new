from pyrogram import Client, filters
from datetime import datetime
import asyncio
from . import collection, user_collection, sudo_filter, app, dev_filter

# Advanced Character Management System
# Super Fast Mass Removal Commands

@app.on_message(filters.command(["massremove"]) & sudo_filter)
async def mass_remove_characters(client, message):
    """
    🚀 ADVANCED MASS CHARACTER REMOVAL
    Remove characters by ID or rarity from ALL users simultaneously
    Super fast bulk operations - No progress bars, instant execution
    """
    try:
        if len(message.command) < 2:
            return await message.reply("""
⚡ **Advanced Mass Removal System**

**Usage:**
`/massremove rarity:RARITY` - Remove by rarity from all users
`/massremove id:CHAR_ID` - Remove specific character ID from all users
`/massremove user:USER_ID` - Remove all characters from specific user

**Examples:**
`/massremove rarity:⚜️ Animated`
`/massremove id:char_abc123`
`/massremove user:123456789`
""")

        command_text = " ".join(message.command[1:])
        processing_msg = await message.reply("⚡ **Initializing Quantum Removal Protocol...**")

        # Parse command parameters
        if command_text.startswith("rarity:"):
            rarity = command_text.replace("rarity:", "").strip()
            result = await remove_by_rarity_all_users(rarity)
            
        elif command_text.startswith("id:"):
            char_id = command_text.replace("id:", "").strip()
            result = await remove_by_id_all_users(char_id)
            
        elif command_text.startswith("user:"):
            user_id = int(command_text.replace("user:", "").strip())
            result = await remove_all_user_characters(user_id)
            
        else:
            return await processing_msg.edit("❌ **Invalid parameter!** Use: rarity:, id:, or user:")

        await processing_msg.edit(result)

    except Exception as e:
        error_msg = f"""
❌ **Quantum Removal Failed**

**Error Type:** `{type(e).__name__}`
**Details:** `{str(e)}`

💡 **Quick Fix Tips:**
- Check rarity spelling exactly
- Ensure character ID exists
- Verify user ID is correct
"""
        await message.reply(error_msg)

async def remove_by_rarity_all_users(rarity):
    """Remove all characters of specific rarity from EVERY user instantly"""
    start_time = datetime.now()
    
    # Get all users with characters
    all_users = user_collection.find({'characters': {'$exists': True, '$ne': []}})
    
    removal_count = 0
    affected_users = 0
    
    async for user in all_users:
        original_count = len(user.get('characters', []))
        
        # Filter out characters with target rarity
        new_characters = [
            char for char in user['characters'] 
            if char.get('rarity') != rarity
        ]
        
        removed_count = original_count - len(new_characters)
        
        if removed_count > 0:
            # Bulk update user collection
            await user_collection.update_one(
                {'id': user['id']},
                {'$set': {'characters': new_characters}}
            )
            removal_count += removed_count
            affected_users += 1

    execution_time = (datetime.now() - start_time).total_seconds()
    
    return f"""
🎯 **Rarity Purge Complete**

⚡ **Execution Speed:** `{execution_time:.3f}s`
🎯 **Target Rarity:** `{rarity}`
🗑️ **Characters Removed:** `{removal_count}`
👥 **Affected Users:** `{affected_users}`
⏰ **Timestamp:** `{datetime.now().strftime("%H:%M:%S")}`

✅ **Operation Status:** Quantum Removal Successful
"""

async def remove_by_id_all_users(char_id):
    """Remove specific character ID from ALL users instantly"""
    start_time = datetime.now()
    
    # Verify character exists in main collection first
    char_exists = await collection.find_one({'char_id': char_id})
    if not char_exists:
        return f"❌ Character ID `{char_id}` not found in database!"
    
    # Bulk remove from all users
    result = await user_collection.update_many(
        {'characters.char_id': char_id},
        {'$pull': {'characters': {'char_id': char_id}}}
    )
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return f"""
🎯 **Targeted Character Elimination**

⚡ **Execution Speed:** `{execution_time:.3f}s`
🎯 **Target ID:** `{char_id}`
🗑️ **Removed From:** `{result.modified_count} users`
📊 **Character Name:** `{char_exists.get('name', 'Unknown')}`
⏰ **Timestamp:** `{datetime.now().strftime("%H:%M:%S")}`

✅ **Operation Status:** Surgical Strike Successful
"""

async def remove_all_user_characters(user_id):
    """Remove ALL characters from specific user"""
    start_time = datetime.now()
    
    try:
        # Get user info
        user = await app.get_users(user_id)
        username = user.first_name
    except:
        username = f"User_{user_id}"
    
    # Get character count before removal
    user_data = await user_collection.find_one({'id': user_id})
    original_count = len(user_data.get('characters', [])) if user_data else 0
    
    # Wipe all characters
    result = await user_collection.update_one(
        {'id': user_id},
        {'$set': {'characters': []}}
    )
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return f"""
🎯 **User Collection Wipe**

⚡ **Execution Speed:** `{execution_time:.3f}s`
👤 **Target User:** `{username}`
🗑️ **Characters Wiped:** `{original_count}`
📊 **User ID:** `{user_id}`
⏰ **Timestamp:** `{datetime.now().strftime("%H:%M:%S")}`

✅ **Operation Status:** Complete Data Erasure Successful
"""

@app.on_message(filters.command(["purgeanimated"]) & sudo_filter)
async def purge_excess_animated(client, message):
    """
    🧹 AUTOMATED ANIMATED CHARACTER PURGE
    Remove ⚜️ Animated characters from users who have more than 3
    Advanced algorithm with smart distribution detection
    """
    try:
        processing_msg = await message.reply("🔍 **Scanning for Animated Character Hoarders...**")
        
        # Get limit from command or default to 3
        try:
            limit = int(message.command[1]) if len(message.command) > 1 else 3
        except:
            limit = 3
            
        result = await remove_excess_animated_chars(limit)
        await processing_msg.edit(result)
        
    except Exception as e:
        error_msg = f"""
❌ **Purge Protocol Failed**

**Error:** `{type(e).__name__}`
**Details:** `{str(e)}`

💡 **Solution:** Check command format: `/purgeanimated 3`
"""
        await message.reply(error_msg)

async def remove_excess_animated_chars(limit=3):
    """Remove excess ⚜️ Animated characters from all users"""
    start_time = datetime.now()
    ANIMATED_RARITY = "⚜️ Animated"
    
    total_removed = 0
    affected_users = 0
    user_details = []
    
    # Get all users with characters
    all_users = user_collection.find({'characters': {'$exists': True, '$ne': []}})
    
    async for user in all_users:
        user_chars = user.get('characters', [])
        
        # Count animated characters
        animated_chars = [char for char in user_chars if char.get('rarity') == ANIMATED_RARITY]
        animated_count = len(animated_chars)
        
        if animated_count > limit:
            # Keep only the limit, remove excess (remove oldest first)
            chars_to_keep = []
            animated_kept = 0
            
            for char in user_chars:
                if char.get('rarity') == ANIMATED_RARITY:
                    if animated_kept < limit:
                        chars_to_keep.append(char)
                        animated_kept += 1
                    else:
                        # Excess character - skip (will be removed)
                        continue
                else:
                    chars_to_keep.append(char)
            
            # Update user collection
            await user_collection.update_one(
                {'id': user['id']},
                {'$set': {'characters': chars_to_keep}}
            )
            
            removed_count = animated_count - limit
            total_removed += removed_count
            affected_users += 1
            
            user_details.append(f"👤 User {user['id']}: {removed_count} removed")
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    result_msg = f"""
🎯 **Animated Character Purge Complete**

⚡ **Execution Speed:** `{execution_time:.3f}s`
🎯 **Limit Enforced:** `{limit} ⚜️ Animated per user`
🗑️ **Total Excess Removed:** `{total_removed}`
👥 **Affected Users:** `{affected_users}`
⏰ **Timestamp:** `{datetime.now().strftime("%H:%M:%S")}`

📊 **Purge Statistics:**
• Maximum allowed per user: `{limit}`
• Total purged characters: `{total_removed}`
• Users affected: `{affected_users}`

✅ **Purge Status:** Balance Restoration Successful
"""
    
    # Add user details if space allows
    if user_details and len(user_details) <= 10:
        result_msg += "\n**📋 Affected Users Summary:**\n" + "\n".join(user_details[:10])
    elif user_details:
        result_msg += f"\n**📋 Top 10 Affected Users of {affected_users} total**\n" + "\n".join(user_details[:10])
    
    return result_msg

@app.on_message(filters.command(["smartpurge"]) & dev_filter)
async def smart_purge_system(client, message):
    """
    🧠 AI-ENHANCED SMART PURGE SYSTEM
    Advanced analytics with multiple purge modes
    Developer-only super advanced commands
    """
    try:
        if len(message.command) < 2:
            return await message.reply("""
🤖 **AI-Powered Smart Purge System**

**Modes Available:**
`/smartpurge duplicates` - Remove duplicate characters
`/smartpurge inactive` - Purge from inactive users  
`/smartpurge analysis` - Show collection analytics
`/smartpurge balance` - Auto-balance rarities

**Examples:**
`/smartpurge duplicates`
`/smartpurge analysis`
""")

        mode = message.command[1].lower()
        processing_msg = await message.reply("🤖 **Initializing AI Purge Protocol...**")
        
        if mode == "duplicates":
            result = await remove_duplicate_characters()
        elif mode == "inactive":
            result = await purge_inactive_users()
        elif mode == "analysis":
            result = await collection_analysis()
        elif mode == "balance":
            result = await auto_balance_rarities()
        else:
            return await processing_msg.edit("❌ **Invalid mode!** Choose: duplicates, inactive, analysis, balance")
            
        await processing_msg.edit(result)
        
    except Exception as e:
        await message.reply(f"❌ **AI Purge Failed:** `{type(e).__name__}` - `{str(e)}`")

async def remove_duplicate_characters():
    """Remove duplicate characters from users (keep only one)"""
    start_time = datetime.now()
    
    all_users = user_collection.find({'characters': {'$exists': True, '$ne': []}})
    total_removed = 0
    affected_users = 0
    
    async for user in all_users:
        unique_chars = []
        char_ids_seen = set()
        duplicates_removed = 0
        
        for char in user['characters']:
            char_id = char.get('char_id')
            if char_id and char_id not in char_ids_seen:
                unique_chars.append(char)
                char_ids_seen.add(char_id)
            else:
                duplicates_removed += 1
        
        if duplicates_removed > 0:
            await user_collection.update_one(
                {'id': user['id']},
                {'$set': {'characters': unique_chars}}
            )
            total_removed += duplicates_removed
            affected_users += 1
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return f"""
🎯 **Duplicate Purge Complete**

⚡ **Execution Speed:** `{execution_time:.3f}s`
🗑️ **Duplicates Removed:** `{total_removed}`
👥 **Users Affected:** `{affected_users}`
📊 **Average per User:** `{total_removed/max(affected_users,1):.1f}`
⏰ **Timestamp:** `{datetime.now().strftime("%H:%M:%S")}`

✅ **Database Optimization:** Successful
"""

async def collection_analysis():
    """Advanced collection analytics"""
    start_time = datetime.now()
    
    # Get overall statistics
    total_users = await user_collection.count_documents({})
    users_with_chars = await user_collection.count_documents({'characters': {'$exists': True, '$ne': []}})
    
    # Rarity distribution
    rarity_stats = {}
    total_chars = 0
    
    async for user in user_collection.find({'characters': {'$exists': True}}):
        for char in user.get('characters', []):
            rarity = char.get('rarity', 'Unknown')
            rarity_stats[rarity] = rarity_stats.get(rarity, 0) + 1
            total_chars += 1
    
    # User collection sizes
    collection_sizes = []
    async for user in user_collection.find({'characters': {'$exists': True}}):
        collection_sizes.append(len(user.get('characters', [])))
    
    avg_collection = sum(collection_sizes) / len(collection_sizes) if collection_sizes else 0
    max_collection = max(collection_sizes) if collection_sizes else 0
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    # Format rarity stats
    rarity_text = "\n".join([f"• {rarity}: {count}" for rarity, count in sorted(rarity_stats.items())])
    
    return f"""
📊 **Advanced Collection Analytics**

⚡ **Analysis Speed:** `{execution_time:.3f}s`
👥 **Total Users:** `{total_users}`
🎯 **Active Collectors:** `{users_with_chars}`
📦 **Total Characters:** `{total_chars}`

📈 **Collection Stats:**
• Average Size: `{avg_collection:.1f}`
• Largest Collection: `{max_collection}`
• Empty Collections: `{total_users - users_with_chars}`

🎭 **Rarity Distribution:**
{rarity_text}

⏰ **Snapshot Time:** `{datetime.now().strftime("%H:%M:%S")}`
"""

# Additional utility functions
async def purge_inactive_users():
    """Purge characters from inactive users (placeholder)"""
    return "🔧 **Feature in Development** - Inactive user detection coming soon!"

async def auto_balance_rarities():
    """Auto-balance rarities across users (placeholder)"""
    return "🔧 **Feature in Development** - Auto-balancing algorithm coming soon!"

@app.on_message(filters.command(["purgestats"]) & sudo_filter)
async def purge_statistics(client, message):
    """
    📊 REAL-TIME PURGE STATISTICS
    Show current database status and purge readiness
    """
    stats_msg = """
📊 **Database Purge Readiness Report**

**Quick Commands:**
`/massremove rarity:⚜️ Animated` - Purge specific rarity
`/purgeanimated 3` - Limit animated characters
`/smartpurge analysis` - Detailed analytics

**Ready for immediate execution!**
"""
    await message.reply(stats_msg)
