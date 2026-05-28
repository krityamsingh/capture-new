import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message
from . import aruby, sudo_filter, guess_watcher, app, collection
from .block import block_dec

# Active games tracker
active_guesses = {}
GUESS_TIMEOUT = 180  # 3 minutes timeout for each game
COOLDOWN = 3  # 3 seconds cooldown between games

# Support group ID
SUPPORT_GROUP_ID = -1002313549356

def support_group_only(func):
    async def wrapper(client, message: Message):
        if message.chat.id != SUPPORT_GROUP_ID:
            await message.reply("This command only works in the official support group: @thereapersagain")
            return
        return await func(client, message)
    return wrapper

async def get_random_character():
    """Fetch a random character"""
    try:
        character = await collection.aggregate([
            {"$match": {"img_url": {"$exists": True}, "name": {"$exists": True}}},
            {"$sample": {"size": 1}}
        ]).to_list(length=1)
        
        if character:
            return character[0]
        return None
    except Exception as e:
        print(f"Error in get_random_character: {e}")
        return None

def get_random_reward():
    """Get random reward between 1-200 Ruby"""
    return random.randint(1, 200)

@app.on_message(filters.command("guess"))
@block_dec
@support_group_only
async def start_guess_game(client, message: Message):
    chat_id = message.chat.id
    
    # Check if there's already an active game
    if chat_id in active_guesses:
        game = active_guesses[chat_id]
        time_left = (game['start_time'] + timedelta(seconds=GUESS_TIMEOUT) - datetime.now()).seconds
        
        if time_left > 0:
            try:
                await message.reply_photo(
                    photo=game['character']['img_url'],
                    caption=f"Current Guessing Game\nReward: {game['reward']} Ruby\nTime Left: {time_left}s\nReply with character name!"
                )
            except Exception as e:
                print(f"Error showing current game: {e}")
                await message.reply("Error showing current game. Starting new game...")
                await new_guess_game(client, chat_id, message)
            return
    
    # Start new game if no active game or current game expired
    await new_guess_game(client, chat_id, message)

async def new_guess_game(client, chat_id, trigger_message=None):
    try:
        character = await get_random_character()
        if not character:
            if trigger_message:
                await trigger_message.reply("Database error - no characters available")
            else:
                await client.send_message(chat_id, "Database error - no characters available")
            return

        reward = get_random_reward()
        
        if trigger_message:
            # Reply to the user who triggered the command
            msg = await trigger_message.reply_photo(
                photo=character['img_url'],
                caption=f"New Guessing Game\nReward: {reward} Ruby\nTime: {GUESS_TIMEOUT//60} minutes"
            )
        else:
            # Send to group normally
            msg = await client.send_photo(
                chat_id,
                photo=character['img_url'],
                caption=f"New Guessing Game\nReward: {reward} Ruby\nTime: {GUESS_TIMEOUT//60} minutes"
            )

        active_guesses[chat_id] = {
            'character': character,
            'start_time': datetime.now(),
            'message_id': msg.id,
            'reward': reward,
            'answered': False,
            'trigger_user_id': trigger_message.from_user.id if trigger_message else None
        }

        # Start timeout task
        asyncio.create_task(game_timeout(client, chat_id))
        
    except Exception as e:
        print(f"Error in new_guess_game: {e}")
        if trigger_message:
            await trigger_message.reply("Error starting new game")
        else:
            await client.send_message(chat_id, "Error starting new game")

async def game_timeout(client, chat_id):
    await asyncio.sleep(GUESS_TIMEOUT)
    
    try:
        if chat_id in active_guesses and not active_guesses[chat_id]['answered']:
            game = active_guesses[chat_id]
            await client.send_message(
                chat_id,
                f"Time's up! The answer was: {game['character']['name']}\nType /guess to play again!"
            )
            # Clear the game
            if chat_id in active_guesses:
                del active_guesses[chat_id]
    except Exception as e:
        print(f"Error in game_timeout: {e}")

@app.on_message(filters.text & ~filters.me & ~filters.command("guess"), group=guess_watcher)
async def handle_guess(client, message: Message):
    try:
        chat_id = message.chat.id
        if chat_id != SUPPORT_GROUP_ID or chat_id not in active_guesses:
            return

        game = active_guesses[chat_id]
        
        # Check if already answered or game expired
        if game['answered']:
            return
            
        time_elapsed = (datetime.now() - game['start_time']).seconds
        if time_elapsed > GUESS_TIMEOUT:
            return

        user = message.from_user
        if not user:
            return
            
        guess = message.text.strip().lower()
        correct = game['character']['name'].lower()
        
        # Check if guess is correct (partial match)
        if any(part in guess for part in correct.split()) or guess in correct:
            # Mark as answered to prevent multiple winners
            active_guesses[chat_id]['answered'] = True
            
            reward = game['reward']
            
            # Add reward to user
            await aruby(user.id, reward)
            
            # Send congratulatory message as reply to user's guess
            await message.reply(
                f"Correct! {user.first_name} guessed it!\n{game['character']['name']}\nWon: {reward} Ruby\nNext game starting soon..."
            )
            
            # Store current game info
            current_character = game['character']['name']
            
            # Clear current game
            if chat_id in active_guesses:
                del active_guesses[chat_id]
            
            # Start new game after cooldown
            await asyncio.sleep(COOLDOWN)
            
            # Start new game and reply to the user who just guessed correctly
            await new_guess_game(client, chat_id, message)
            
    except Exception as e:
        print(f"Error in handle_guess: {e}")

@app.on_message(filters.command("xguess") & sudo_filter)
@block_dec
async def force_end_game(client, message: Message):
    try:
        chat_id = message.chat.id
        if chat_id in active_guesses:
            game = active_guesses[chat_id]
            await message.reply(
                f"Game ended by admin!\nThe answer was: {game['character']['name']}"
            )
            del active_guesses[chat_id]
        else:
            await message.reply("No active game to end")
    except Exception as e:
        print(f"Error in force_end_game: {e}")
