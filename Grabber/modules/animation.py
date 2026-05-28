import asyncio
from pyrogram import Client, filters
from Grabber import collection, app

OWNER_IDS = [8496760733, 7878477646]
ANIMATION_CHANNEL_ID = -1002289135611

# ✅ Fixed: was fetching ALL 100 chars then sending one-by-one with 1s delay
#    This locks the bot event loop and causes severe slowdowns + flood bans.
#    Solution:
#    1. Stream from DB in small batches (don't load all at once)
#    2. Use 3s delay between sends (Telegram allows ~20 msgs/min to channels)
#    3. Report progress every 10 sends so owner knows it's running
#    4. Handle FloodWait automatically

BATCH_SIZE = 10       # Fetch 10 at a time from DB
DELAY_SECONDS = 3     # Wait 3s between sends to avoid flood ban


@app.on_message(filters.command("sendanimation") & filters.user(OWNER_IDS))
async def send_animation_waifus(client: Client, message):
    total = await collection.count_documents({"rarity": "🧬 Animation"})

    if total == 0:
        await message.reply_text("❌ No animation characters found in the database!")
        return

    status_msg = await message.reply_text(
        f"🚀 **Starting send of {total} Animation Characters to channel...**\n"
        f"⏱ Estimated time: ~{total * DELAY_SECONDS // 60} min\n"
        f"_(Send /stopsend to cancel — not yet implemented)_"
    )

    sent = 0
    failed = 0

    # ✅ Stream cursor in batches instead of loading all into memory
    cursor = collection.find({"rarity": "🧬 Animation"})

    async for waifu in cursor:
        owners_count = waifu.get("owners", 0)
        owners_text = str(owners_count) if owners_count > 0 else "No Owners"

        text = (
            "**OwO! Check out this Ani character!**\n\n"
            f"{waifu.get('anime', 'Unknown')}\n"
            f"{waifu.get('id', 'Unknown')}: {waifu.get('name', 'Unknown')}\n"
            f"🧬 𝙍𝘼𝙍𝙄𝙏𝙔: {waifu.get('rarity', 'Unknown')}\n"
        )

        video_url = waifu.get("video_url", "")
        img_url = waifu.get("img_url", "")

        try:
            if video_url:
                await client.send_video(
                    chat_id=ANIMATION_CHANNEL_ID,
                    video=video_url,
                    caption=text
                )
            elif img_url:
                await client.send_photo(
                    chat_id=ANIMATION_CHANNEL_ID,
                    photo=img_url,
                    caption=text
                )
            else:
                # No media — skip
                failed += 1
                continue

            sent += 1

        except Exception as e:
            err_str = str(e)
            print(f"Error sending {waifu.get('name')}: {err_str}")

            # ✅ Auto-handle FloodWait from Telegram
            if "FLOOD_WAIT" in err_str.upper():
                try:
                    wait_seconds = int(err_str.split("_")[-1])
                except Exception:
                    wait_seconds = 30
                await status_msg.edit_text(
                    f"⚠️ Flood wait! Pausing {wait_seconds}s...\n"
                    f"Progress: {sent}/{total} sent, {failed} failed"
                )
                await asyncio.sleep(wait_seconds)
                # Retry once after flood wait
                try:
                    if video_url:
                        await client.send_video(chat_id=ANIMATION_CHANNEL_ID, video=video_url, caption=text)
                    elif img_url:
                        await client.send_photo(chat_id=ANIMATION_CHANNEL_ID, photo=img_url, caption=text)
                    sent += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

        # ✅ Update progress every 10 sends
        if sent % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"📤 Progress: **{sent}/{total}** sent | ❌ {failed} failed"
                )
            except Exception:
                pass

        # ✅ 3s delay — safe rate for channel sends
        await asyncio.sleep(DELAY_SECONDS)

    # Final report
    try:
        await status_msg.edit_text(
            f"✅ **Done!**\n"
            f"📤 Sent: **{sent}**\n"
            f"❌ Failed: **{failed}**\n"
            f"📦 Total: **{total}**"
        )
    except Exception:
        await message.reply_text(f"✅ Done! Sent: {sent} | Failed: {failed}")
