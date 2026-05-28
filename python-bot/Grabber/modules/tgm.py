import os
import asyncio
import aiohttp
from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from . import app

# Constants
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
SUPPORTED_TYPES = ["photo", "video", "animation", "document", "sticker"]

async def upload_to_catbox(file_path):
    """Asynchronously uploads a file to Catbox and returns the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as file:
                data = aiohttp.FormData()
                data.add_field("reqtype", "fileupload")
                data.add_field("fileToUpload", file)
                
                async with session.post(CATBOX_URL, data=data) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
                    raise Exception(f"Upload failed with status {response.status}")
    except Exception as e:
        raise Exception(f"Catbox error: {str(e)}")

def get_file_type(message):
    """Determine the file type from the message."""
    if message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.animation:
        return "animation"
    elif message.document:
        return "document"
    elif message.sticker:
        return "sticker"
    return None

def get_human_size(size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

@app.on_message(filters.command(["tgm", "catbox"]) & filters.reply)
async def upload_handler(client, message):
    reply = message.reply_to_message
    file_type = get_file_type(reply)
    
    if not file_type or file_type not in SUPPORTED_TYPES:
        await message.reply("⚠️ **Unsupported Format**\n\nI can only process photos, videos, GIFs, documents, and stickers.")
        return

    # Initial processing message with cool animation
    status_msg = await message.reply("🚀 **Initializing Upload Process...**")
    
    try:
        # Step 1: Downloading the file
        await status_msg.edit("📥 **Downloading Media...**\n\n⌛ Please wait while I fetch your file...")
        
        file_path = await reply.download()
        if not file_path:
            await status_msg.edit("❌ **Download Failed**\n\nCouldn't retrieve the media file.")
            return

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            await status_msg.edit(f"⚠️ **File Too Large**\n\nMaximum allowed size is 200MB.\nYour file: {get_human_size(file_size)}")
            os.remove(file_path)
            return

        # Step 2: Uploading to Catbox
        progress_msg = "☁️ **Uploading to Catbox...**\n\n"
        progress_msg += "🔄 This might take a while for larger files..."
        await status_msg.edit(progress_msg)
        
        # Simulate progress updates for better UX
        for i in range(1, 4):
            try:
                await status_msg.edit(f"{progress_msg}\n{'▣' * i}{'▢' * (3 - i)}")
                await asyncio.sleep(0.5)
            except MessageNotModified:
                pass

        file_url = await upload_to_catbox(file_path)

        # Step 3: Prepare the response
        caption = "✨ **Upload Successful!**\n\n"
        caption += f"🔗 **Direct Link:** `{file_url}`\n"
        caption += f"📊 **File Size:** {get_human_size(file_size)}\n\n"
        caption += "🗑️ File will be automatically deleted from our servers after 30 days."

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Open in Browser", url=file_url)],
            [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{file_url}")]
        ])

        # Send appropriate media type with preview
        if file_type == "photo":
            await message.reply_photo(
                photo=reply.photo.file_id,
                caption=caption,
                reply_markup=buttons
            )
        elif file_type == "video":
            await message.reply_video(
                video=reply.video.file_id,
                caption=caption,
                reply_markup=buttons
            )
        elif file_type == "animation":
            await message.reply_animation(
                animation=reply.animation.file_id,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await message.reply_document(
                document=file_path,
                caption=caption,
                reply_markup=buttons
            )

        # Cleanup
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        error_msg = "⚠️ **Upload Failed**\n\n"
        error_msg += f"Error: `{str(e)}`\n\n"
        error_msg += "Please try again later or contact support if this persists."
        await status_msg.edit(error_msg)
        
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

@app.on_callback_query(filters.regex("^copy_"))
async def copy_link_callback(client, callback_query):
    url = callback_query.data.split("_", 1)[1]
    await callback_query.answer("Link copied to clipboard!", show_alert=False)
    await callback_query.message.edit_text(
        f"{callback_query.message.text}\n\n✅ **Link copied to clipboard!**"
    )

# Error handler for MessageNotModified
@app.on_message(filters.command(["tgm", "catbox"]))
async def error_handler(_, message):
    try:
        await message.reply("❌ **Invalid Usage**\n\nPlease reply to a media file with /tgm or /catbox")
    except:
        pass
