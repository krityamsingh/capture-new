import asyncio
import time
from datetime import datetime, timedelta
from Grabber import (
    global_ban_users_collection, 
    top_global_groups_collection,
    global_mute_users_collection
)

# Global Ban Functions
async def add_to_global_ban(user_id: int, reason: str, banned_by: int = None, timestamp: datetime = None):
    await global_ban_users_collection.update_one(
        {'_id': user_id},
        {'$set': {
            'reason': reason,
            'banned_by': banned_by,
            'timestamp': timestamp or datetime.now(),
            'last_updated': datetime.now()
        }},
        upsert=True
    )

async def remove_from_global_ban(user_id: int):
    await global_ban_users_collection.delete_one({"_id": user_id})

async def is_user_globally_banned(user_id: int) -> bool:
    user = await global_ban_users_collection.find_one({"_id": user_id})
    return bool(user)

async def fetch_globally_banned_users() -> list:
    banned_users = []
    async for user in global_ban_users_collection.find({}):
        banned_users.append({
            "user_id": user['_id'],
            "reason": user.get('reason', 'No reason provided'),
            "banned_by": user.get('banned_by', 'Unknown'),
            "timestamp": user.get('timestamp', datetime.now()),
            "last_updated": user.get('last_updated', datetime.now())
        })
    return banned_users

# Chat Utilities
async def get_all_chats() -> list:
    return await top_global_groups_collection.distinct("group_id")

async def ban_user_in_chats(client, user_id: int, all_chats: list) -> dict:
    results = {
        'success': 0,
        'failed': 0,
        'errors': [],
        'start_time': datetime.now(),
        'end_time': None
    }

    for chat_id in all_chats:
        try:
            await client.ban_chat_member(
                chat_id,
                user_id,
                until_date=datetime.now() + timedelta(days=365)
            )
            results['success'] += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'chat_id': chat_id,
                'error': str(e)
            })

    results['end_time'] = datetime.now()
    return results

async def unban_user_in_chats(client, user_id: int, all_chats: list) -> dict:
    results = {
        'success': 0,
        'failed': 0,
        'errors': [],
        'start_time': datetime.now(),
        'end_time': None
    }

    for chat_id in all_chats:
        try:
            await client.unban_chat_member(chat_id, user_id)
            results['success'] += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'chat_id': chat_id,
                'error': str(e)
            })

    results['end_time'] = datetime.now()
    return results

# Global Mute Functions
async def add_to_global_mute(user_id: int, reason: str, muted_by: int = None):
    await global_mute_users_collection.update_one(
        {'_id': user_id},
        {'$set': {
            'reason': reason,
            'muted_by': muted_by,
            'timestamp': datetime.now(),
            'last_updated': datetime.now()
        }},
        upsert=True
    )

async def remove_from_global_mute(user_id: int):
    await global_mute_users_collection.delete_one({"_id": user_id})

async def is_user_globally_muted(user_id: int) -> bool:
    user = await global_mute_users_collection.find_one({"_id": user_id})
    return bool(user)

async def fetch_globally_muted_users() -> list:
    muted_users = []
    async for user in global_mute_users_collection.find({}):
        muted_users.append({
            "user_id": user['_id'],
            "reason": user.get('reason', 'No reason provided'),
            "muted_by": user.get('muted_by', 'Unknown'),
            "timestamp": user.get('timestamp', datetime.now()),
            "last_updated": user.get('last_updated', datetime.now())
        })
    return muted_users

# Stats and Utilities
async def get_ban_stats() -> dict:
    return {
        'total_banned': await global_ban_users_collection.count_documents({}),
        'last_updated': datetime.now()
    }

async def get_mute_stats() -> dict:
    return {
        'total_muted': await global_mute_users_collection.count_documents({}),
        'last_updated': datetime.now()
    }

async def cleanup_old_entries(days: int = 30):
    cutoff_date = datetime.now() - timedelta(days=days)
    await global_ban_users_collection.delete_many({'last_updated': {'$lt': cutoff_date}})
    await global_mute_users_collection.delete_many({'last_updated': {'$lt': cutoff_date}})

async def search_banned_users(query: str) -> list:
    return await global_ban_users_collection.find({
        '$or': [
            {'_id': {'$regex': query, '$options': 'i'}},
            {'reason': {'$regex': query, '$options': 'i'}}
        ]
    }).to_list(None)

async def backup_database():
    return {
        'banned_users': await fetch_globally_banned_users(),
        'muted_users': await fetch_globally_muted_users(),
        'timestamp': datetime.now()
            }
