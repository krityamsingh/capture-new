import requests
from pyrogram import filters
from Grabber import app

# List of APIs to use (fallback if one fails)
API_SOURCES = {
    "waifu.pics": "https://api.waifu.pics/sfw/{action}",
    "nekos.best": "https://nekos.best/api/v2/{action}",
    "shikimori": "https://shikimori.one/api/{action}"
}

# Commands & Corresponding API Endpoints
sfw_actions = {
    "waifus": "waifu",
    "neko": "neko",
    "shinobu": "shinobu",
    "megumin": "megumin",
    "bully": "bully",
    "cuddle": "cuddle",
    "cry": "cry",
    "hug": "hug",
    "awoo": "awoo",
    "kiss": "kiss",
    "lick": "lick",
    "pat": "pat",
    "smug": "smug",
    "bonk": "bonk",
    "yeet": "yeet",
    "blush": "blush",
    "smile": "smile",
    "wave": "wave",
    "highfive": "highfive",
    "handhold": "handhold",
    "nom": "nom",
    "bite": "bite",
    "glomp": "glomp",
    "slap": "slap",
    "kill": "kill",
    "kick": "kick",
    "happy": "happy",
    "wink": "wink",
    "poke": "poke",
    "dance": "dance",
    "cringe": "cringe",
}

# Custom Messages for Each Action
custom_messages = {
    "hug": "**{user1} wraps {user2} in a warm and loving hug! 🤗❤️**",
    "kiss": "**{user1} gives {user2} a sweet kiss! 💋**",
    "pat": "**{user1} gently pats {user2} on the head! So adorable! 🥰**",
    "slap": "**{user1} slaps {user2} hard! Ouch! 😱**",
    "cuddle": "**{user1} snuggles up with {user2}! So warm and cozy! 🛏️**",
    "bite": "**{user1} playfully bites {user2}! Hope it wasn't too hard! 😆**",
    "kick": "**{user1} kicks {user2} away! 🚀**",
    "wink": "**{user1} winks at {user2} with a teasing smile! 😉**",
    "poke": "**{user1} pokes {user2} gently! Poke poke! 👆**",
    "bonk": "**{user1} bonks {user2} on the head! Bonk! 🔨**",
    "blush": "**{user1} turns red, blushing shyly! 🥺**",
    "smug": "**{user1} smirks smugly! Feeling superior, huh? 😏**",
    "wave": "**{user1} waves cheerfully at {user2}! Hello there! 👋**",
    "highfive": "**{user1} and {user2} exchange a high-five! 🖐️**",
    "handhold": "**{user1} gently holds {user2}'s hand! Such romance! 💞**",
    "dance": "**{user1} starts dancing gracefully! Join the rhythm! 💃🕺**",
    "cry": "**{user1} starts crying! Someone give them a hug! 😭**",
    "yeet": "**{user1} yeets {user2} far away! 🚀**",
    "glomp": "**{user1} glomps {user2} with a super big hug! 🤗**",
    "kill": "**{user1} eliminates {user2}! It's over... 😈**",
    "cringe": "**{user1} cringes so hard… That was awkward! 😬**",
}

def fetch_image(action):
    """Tries fetching an image from multiple APIs."""
    for name, url in API_SOURCES.items():
        try:
            response = requests.get(url.format(action=action), timeout=5)
            response.raise_for_status()
            data = response.json()

            # Different APIs return different structures
            if "url" in data:
                return data["url"]
            elif "results" in data and data["results"]:
                return data["results"][0]["url"]
            elif "image" in data:
                return data["image"]
        except (requests.RequestException, KeyError):
            continue  # Try next API if this one fails

    return None  # If all fail

# Register Commands for Each Action
def create_handler(command, action):
    @app.on_message(filters.command(command))
    async def send_action_image(client, message):
        image_url = fetch_image(action)

        if image_url:
            file_extension = image_url.split(".")[-1].lower()

            # Mention handling
            user1 = message.from_user.mention if message.from_user else "Someone"
            if message.reply_to_message:
                user2 = message.reply_to_message.from_user.mention if message.reply_to_message.from_user else "Someone else"
                caption = custom_messages.get(action, "**{user1} did {action} to {user2}!**").format(user1=user1, user2=user2)
            else:
                caption = custom_messages.get(action, "**{user1} did {action}!**").format(user1=user1, user2="themselves")

            # Send Image/GIF with caption
            try:
                if file_extension == "gif":
                    await client.send_animation(
                        chat_id=message.chat.id,
                        animation=image_url,
                        caption=caption
                    )
                else:
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=image_url,
                        caption=caption
                    )
            except Exception as e:
                await message.reply(f"⚠️ Error sending media: {e}")
        else:
            await message.reply("⚠️ Sorry, couldn't fetch an image. Try again later!")

    return send_action_image

# Bind each command separately
for command, action in sfw_actions.items():
    handler = create_handler(command, action)
    app.add_handler(handler)
