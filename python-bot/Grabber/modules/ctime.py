from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message
from pymongo import ReturnDocument
from . import sudo_filter, app
from Grabber import group_user_totals_collection


@app.on_message(filters.command("changetime"))
async def change_time(client: Client, message: Message):
    try:
        # Fetch the current frequency for the chat
        chat_settings = await group_user_totals_collection.find_one({'chat_id': message.chat.id})
        current_frequency = chat_settings.get('message_frequency', 'not set') if chat_settings else 'not set'

        # Ensure the user is an admin or owner
        user = await app.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text(
                f"**❌ Permission Denied**\n\n"
                f"Only administrators can modify the spawn rate settings.\n\n"
                f"**Current Spawn Rate**: `{current_frequency}` messages\n"
                f"**Group**: {message.chat.title}"
            )
            return

        # Parse arguments
        args = message.text.split(maxsplit=1)[1:]
        if len(args) != 1 or not args[0].isdigit():
            await message.reply_text(
                f"**📝 Usage**: `/changetime <number>`\n\n"
                f"**Example**: `/changetime 150`\n\n"
                f"**Current Spawn Rate**: `{current_frequency}` messages\n"
                f"**Group**: {message.chat.title}"
            )
            return

        # Validate and update the frequency
        new_frequency = int(args[0])
        if new_frequency < 99 or new_frequency > 3000:
            await message.reply_text(
                f"**⚠️ Invalid Range**\n\n"
                f"The spawn rate must be between **99 and 3000** messages.\n\n"
                f"**Current Spawn Rate**: `{current_frequency}` messages\n"
                f"**Group**: {message.chat.title}"
            )
            return

        updated_settings = await group_user_totals_collection.find_one_and_update(
            {'chat_id': message.chat.id},
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await message.reply_text(
            f"**✅ Spawn Rate Updated**\n\n"
            f"**Group**: {message.chat.title}\n"
            f"**New Spawn Rate**: `{new_frequency}` messages\n"
            f"**Previous Rate**: `{current_frequency}` messages\n\n"
            f"Characters will now appear every **{new_frequency}** messages! 🎉"
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Update Failed**\n\n"
            f"An error occurred while updating the spawn rate:\n"
            f"`{str(e)}`\n\n"
            f"Please try again or contact support."
        )


@app.on_message(filters.command("ctime") & sudo_filter)
async def change_time_sudo(client: Client, message: Message):
    try:
        # Fetch the current frequency for the chat
        chat_settings = await group_user_totals_collection.find_one({'chat_id': message.chat.id})
        current_frequency = chat_settings.get('message_frequency', 'not set') if chat_settings else 'not set'

        # Parse arguments
        args = message.text.split(maxsplit=1)[1:]
        if len(args) != 1 or not args[0].isdigit():
            await message.reply_text(
                f"**📝 Sudo Usage**: `/ctime <number>`\n\n"
                f"**Example**: `/ctime 50`\n\n"
                f"**Current Spawn Rate**: `{current_frequency}` messages\n"
                f"**Group**: {message.chat.title}"
            )
            return

        # Validate and update the frequency
        new_frequency = int(args[0])
        if new_frequency < 1 or new_frequency > 10000:
            await message.reply_text(
                f"**⚠️ Invalid Range**\n\n"
                f"The sudo spawn rate must be between **1 and 10,000** messages.\n\n"
                f"**Current Spawn Rate**: `{current_frequency}` messages\n"
                f"**Group**: {message.chat.title}"
            )
            return

        updated_settings = await group_user_totals_collection.find_one_and_update(
            {'chat_id': message.chat.id},
            {'$set': {'message_frequency': new_frequency}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

        await message.reply_text(
            f"**⚡ Sudo Spawn Rate Updated**\n\n"
            f"**Group**: {message.chat.title}\n"
            f"**New Spawn Rate**: `{new_frequency}` messages\n"
            f"**Previous Rate**: `{current_frequency}` messages\n\n"
            f"Characters will now appear every **{new_frequency}** messages! 🌟"
        )
    except Exception as e:
        await message.reply_text(
            f"**❌ Sudo Update Failed**\n\n"
            f"An error occurred while updating the spawn rate:\n"
            f"`{str(e)}`\n\n"
            f"Please check the command format and try again."
        )
