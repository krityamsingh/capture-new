from Grabber import app
from pyrogram import filters
from pyrogram.types import ChatInviteLink

OWNER_ID = 7976292835
CHARA_CHANNEL_ID = -1001234567890

@app.on_message(filters.command("send_chara_invite") & filters.user(OWNER_ID))
async def send_chara_invite(client, message):
    try:
        invite = await client.create_chat_invite_link(
            chat_id=CHARA_CHANNEL_ID,
            member_limit=1
        )

        await client.send_message(
            chat_id=OWNER_ID,
            text=(
                "🔗 Chara Channel Invite Link\n\n"
                f"👉 {invite.invite_link}\n\n"
                "⚠️ Do not share publicly."
            )
        )

        await message.reply_text("✅ Invite link sent successfully.")

    except Exception as e:
        await message.reply_text(f"❌ Error:\n`{e}`")
