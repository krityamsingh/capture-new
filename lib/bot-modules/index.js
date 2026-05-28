const MONGODB_URI = process.env.MONGODB_URI || "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0";

const {
  looksLikeAnime,
  clean,
  stripNoise,
  extractIL,
  parseUploadArgs,
  downloadTelegramMedia,
  uploadToCatbox,
  getNextId,
  buildChannelCaption,
  OWNER_IDS,
  UPLOAD_CHANNEL_ID,
  UPLOAD_GC_ID,
  RARITY_MAP,
  ANIMATED_RARITY
} = require('./uploader');

async function isUploader(userId, db) {
  if (OWNER_IDS.includes(userId)) return true;
  const uploader = await db.collection('uploader').findOne({ user_id: userId });
  if (uploader) return true;
  const uploaders = await db.collection('uploaders').findOne({ user_id: userId });
  if (uploaders) return true;
  const sudo = await db.collection('sudo').findOne({ user_id: userId });
  if (sudo) return true;
  return false;
}

async function editChannelPost(db, botToken, charId) {
  const charColl = db.collection('anime_characters');
  const char = await charColl.findOne({ id: charId });
  if (!char) return "Character not found";
  
  const msgId = char.message_id;
  if (!msgId) return "No message_id stored";
  
  const caption = buildChannelCaption(
    char.name,
    char.anime,
    char.rarity,
    char.price || 0,
    char.id,
    char.mention || "unknown"
  );
  
  const chats = [UPLOAD_CHANNEL_ID, UPLOAD_GC_ID];
  let lastErr = null;
  for (const chatId of chats) {
    const res = await tgApi('editMessageCaption', {
      chat_id: chatId,
      message_id: msgId,
      caption: caption,
      parse_mode: 'Markdown'
    }, botToken);
    if (!res.ok) {
      lastErr = res.description;
    }
  }
  return lastErr;
}

// Core Telegram Bot API Call Wrapper
async function tgApi(method, body, botToken) {
  try {
    const res = await fetch(`https://api.telegram.org/bot${botToken}/${method}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return await res.json();
  } catch (err) {
    console.error(`Telegram API Error (${method}):`, err);
    return { ok: false, error: err.message };
  }
}

// In-Memory state for live games (Spawns, Combats, Cooldowns)
if (!global.botState) {
  global.botState = {
    messageCounts: {},
    spawnedCharacters: {},
    lastDespawnedCharacters: {},
    activeSmashes: {},
    lastSmashTimes: {},
    dailyCooldowns: {}
  };
}
const state = global.botState;

// Weighted Rarity Selector for spawns
function rollRarity() {
  const roll = Math.random() * 100;
  if (roll < 40) return { display: '🔴 Common', query: 'Common' };
  if (roll < 65) return { display: '🔵 Uncommon', query: 'Uncommon' };
  if (roll < 80) return { display: '🟠 Rare', query: 'Rare' };
  if (roll < 90) return { display: '🟡 Legendary', query: 'Legendary' };
  if (roll < 95) return { display: '🫧 Premium', query: 'Premium' };
  if (roll < 98) return { display: '🔮 Limited Edition', query: 'Limited' };
  if (roll < 99.5) return { display: '🏵️ Exotic', query: 'Exotic' };
  return { display: '⚜️ Animated', query: 'Animated' };
}

// Normalized name check for guesses
function isNameMatch(guess, charName) {
  const clean = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim().split(/\s+/);
  const guessParts = clean(guess);
  const nameParts = clean(charName);
  
  if (guessParts.length === 0 || nameParts.length === 0) return false;
  
  // Matches full name, first name, or last name
  const fullGuess = guessParts.join(' ');
  const fullName = nameParts.join(' ');
  const firstName = nameParts[0];
  const lastName = nameParts[nameParts.length - 1];

  return fullGuess === fullName || fullGuess === firstName || fullGuess === lastName;
}

// Main Commands Router and Module implementations
async function handleBotCommand(update, db, botToken, host) {
  const message = update.message;
  const chat = message.chat;
  const from = message.from;
  const text = message.text || "";

  const chatId = chat.id;
  const userId = from.id;
  const firstName = from.first_name || "Collector";
  const username = from.username || "";

  const userColl = db.collection('user_collection');
  const charColl = db.collection('anime_characters');
  const groupsColl = db.collection('groups');
  const sudoColl = db.collection('sudo');
  const blockColl = db.collection('block');
  const clansColl = db.collection('clans');

  const webAppUrl = `https://${host}`;

  // Parse command and arguments
  const parts = text.trim().split(/\s+/);
  const rawCmd = parts[0].toLowerCase();
  const cmd = rawCmd.split('@')[0]; // strip bot username
  const args = parts.slice(1);

  // Check if blocked
  const isBlocked = await blockColl.findOne({ user_id: userId });
  if (isBlocked) {
    return tgApi('sendMessage', {
      chat_id: chatId,
      text: "❌ *You are globally blocked from using this bot.*",
      parse_mode: 'Markdown'
    }, botToken);
  }

  // Ensure user profile exists
  let user = await userColl.findOne({ id: userId });
  if (!user) {
    user = {
      id: userId,
      first_name: firstName,
      username: username,
      gold: 100,
      rubies: 0,
      characters: [],
      favorites: [],
      last_ad_watch: null
    };
    await userColl.insertOne(user);
  }

  // 1. Spawning Mechanics on Chat Traffic
  if (chat.type === "group" || chat.type === "supergroup") {
    state.messageCounts[chatId] = (state.messageCounts[chatId] || 0) + 1;
    
    // Retrieve group spawn limits/frequency (default every 15 messages)
    const grp = await groupsColl.findOne({ chat_id: chatId });
    const frequency = grp?.spawn_frequency || 15;

    if (state.messageCounts[chatId] >= frequency && !state.spawnedCharacters[chatId]) {
      state.messageCounts[chatId] = 0;
      
      const rolled = rollRarity();
      const randomChars = await charColl.aggregate([
        {
          $match: {
            rarity: { $regex: rolled.query, $options: 'i' },
            img_url: { $exists: true, $ne: "" },
            deleted: { $ne: true }
          }
        },
        { $sample: { size: 1 } }
      ]).toArray();

      const character = randomChars[0];
      if (character) {
        state.spawnedCharacters[chatId] = character;
        
        const caption = `🌸 *A wild anime character has appeared!* 🌸\n\n` +
                        `• *Rarity:* ${rolled.display}\n` +
                        `• *Status:* ⚔️ Capture them now!\n\n` +
                        `Use \`/capture [name]\` or \`/smash\` to claim this character for your harem!`;

        await tgApi('sendPhoto', {
          chat_id: chatId,
          photo: character.img_url,
          caption: caption,
          parse_mode: 'Markdown'
        }, botToken);

        // Despawn after 2 minutes
        setTimeout(async () => {
          if (state.spawnedCharacters[chatId] === character) {
            state.lastDespawnedCharacters[chatId] = character;
            delete state.spawnedCharacters[chatId];
            await tgApi('sendMessage', {
              chat_id: chatId,
              text: `🌬️ *The character (${character.name}) fled into the shadows...*`
            }, botToken);
          }
        }, 120000);
      }
    }
  }

  // 2. Command Handlers
  switch (cmd) {
    case '/start':
    case '/help':
      const helpMsg = `🌸 *Welcome to Captrue Upgraded, ${firstName}!* 🌸\n\n` +
                      `Here are the available bot commands:\n\n` +
                      `*🎮 Gameplay:* \n` +
                      `• \`/capture [name]\` — Guess the spawned character's name to capture it!\n` +
                      `• \`/smash\` — Initiate interactive combat to win the spawned character!\n` +
                      `• \`/exit\` — Abandon active combat\n` +
                      `• \`/harem\` — View your personal collection of captured characters\n` +
                      `• \`/fav\` — View or set your favorite character\n\n` +
                      `*💰 Economy:* \n` +
                      `• \`/bal\` or \`/balance\` — Check your gold and ruby balances\n` +
                      `• \`/pay [id] [amount]\` — Transfer gold coins to another player\n` +
                      `• \`/mine\` / \`/work\` — Perform cooldown jobs to earn extra coins\n` +
                      `• \`/streak\` / \`/bonus\` — Claim daily login streaks and rewards\n` +
                      `• \`/rob [id]\` — Rob coins from another user (risk of failure!)\n\n` +
                      `*⚙️ Account:* \n` +
                      `• \`/login\` — Generate browser confirmation push notifications\n\n` +
                      `🎮 *Tap the buttons below to open the Web App!*`;

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: helpMsg,
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [{ text: '🎮 Play Captrue WebApp', web_app: { url: webAppUrl } }],
            [
              { text: '🛒 Card Shop', web_app: { url: `${webAppUrl}?tab=shop` } },
              { text: '💝 Harem Catalog', web_app: { url: `${webAppUrl}?tab=harem` } }
            ]
          ]
        }
      }, botToken);

    case '/capture':
      if (!state.spawnedCharacters[chatId]) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🌫️ *No character is active in this chat right now.*"
        }, botToken);
      }
      
      if (args.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚠️ *Please provide your name guess!* Usage: `/capture [name]`"
        }, botToken);
      }

      const activeChar = state.spawnedCharacters[chatId];
      const guess = args.join(' ');

      if (isNameMatch(guess, activeChar.name)) {
        delete state.spawnedCharacters[chatId];
        
        // Add to harem and grant gold
        const goldReward = Math.floor(Math.random() * 95) + 5; // +5 to +100 gold
        await userColl.updateOne(
          { id: userId },
          {
            $push: { characters: activeChar },
            $inc: { gold: goldReward }
          }
        );

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `🎉 *Correct!* ${firstName} successfully captured *${activeChar.name}*!\n` +
                `• *Anime:* \`${activeChar.anime}\`\n` +
                `• *Rarity:* \`${activeChar.rarity}\`\n` +
                `• *Reward:* +${goldReward} 💰 gold coins added to balance!`
        }, botToken);
      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Incorrect name!* Try guessing again."
        }, botToken);
      }

    case '/smash':
      if (!state.spawnedCharacters[chatId]) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🌫️ *No character is active in this chat to smash.*"
        }, botToken);
      }

      if (state.activeSmashes[userId]) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚔️ *You are already in combat!* Finish or /exit your current battle."
        }, botToken);
      }

      const opponent = state.spawnedCharacters[chatId];
      state.activeSmashes[userId] = opponent;

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `⚔️ *Combat initiated against ${opponent.name}!*\n\n` +
              `• *Power Level:* \`${opponent.rarity}\`\n` +
              `• *Rules:* Tap one of the actions below to engage!`,
        reply_markup: {
          inline_keyboard: [
            [
              { text: '💥 Smash Attack', callback_data: `smash_engage:${opponent.id}` },
              { text: '🏃 Tactical Retreat', callback_data: `smash_retreat:${opponent.id}` }
            ]
          ]
        }
      }, botToken);

    case '/exit':
      if (state.activeSmashes[userId]) {
        const fledOpponent = state.activeSmashes[userId];
        delete state.activeSmashes[userId];
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `🚪 *Combat abandoned!* You fled from *${fledOpponent.name}*.`
        }, botToken);
      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *You are not currently in any combat.*"
        }, botToken);
      }

    case '/bal':
    case '/balance':
      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `💰 *Your Balance Stats, ${firstName}:*\n\n` +
              `🪙 *Gold Coins:* \`${(user.gold || 0).toLocaleString()}\` gold\n` +
              `🪬 *Token Balance:* \`${(user.rubies || 0).toLocaleString()}\` rubies`
      }, botToken);

    case '/harem':
      const totalHarem = user.characters || [];
      if (totalHarem.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "😔 *Your harem is empty!* Capture spawned characters or visit the WebApp Shop to collect some!"
        }, botToken);
      }

      // Filter by rarity if specified
      let displayChars = totalHarem;
      const rarityFilter = args.join(' ').toLowerCase();
      if (rarityFilter) {
        displayChars = totalHarem.filter(c => c.rarity.toLowerCase().includes(rarityFilter));
      }

      const listStr = displayChars.slice(0, 10).map((c, i) => `${i + 1}. *${c.name}* (${c.rarity})`).join('\n');
      const countMsg = displayChars.length > 10 ? `\n...and ${displayChars.length - 10} more characters.` : "";

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `💝 *Your Harem Catalog (${displayChars.length} Characters):*\n\n` +
              `${listStr || "_No matching characters found._"}${countMsg}\n\n` +
              `📱 *Open the WebApp to view the full image gallery!*`,
        reply_markup: {
          inline_keyboard: [[{ text: '💝 Open Harem Gallery', web_app: { url: `${webAppUrl}?tab=harem` } }]]
        }
      }, botToken);

    case '/fav':
      const harem = user.characters || [];
      if (harem.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Capture characters first before setting a favorite!*"
        }, botToken);
      }

      if (args.length === 0) {
        const fav = user.favorites && user.favorites[0];
        if (fav) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: `⭐️ *Your Current Favorite Character:* \n\n` +
                  `• *Name:* *${fav.name}*\n` +
                  `• *Anime:* \`${fav.anime}\`\n` +
                  `• *Rarity:* \`${fav.rarity}\``
          }, botToken);
        } else {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "ℹ️ *You haven't set a favorite yet.* Use `/fav [character name]` to set one."
          }, botToken);
        }
      }

      const searchName = args.join(' ').toLowerCase();
      const match = harem.find(c => c.name.toLowerCase().includes(searchName));
      if (!match) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Could not find that character in your harem.*"
        }, botToken);
      }

      await userColl.updateOne({ id: userId }, { $set: { favorites: [match] } });
      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `⭐️ *Favorite set!* *${match.name}* is now your star waifu!`
      }, botToken);

    case '/pay':
    case '/transfer':
      if (args.length < 2) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚠️ *Usage:* `/pay [target_user_id] [amount]`"
        }, botToken);
      }

      const targetId = parseInt(args[0], 10);
      const amount = parseInt(args[1], 10);

      if (isNaN(targetId) || isNaN(amount) || amount <= 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Invalid amount or user ID.*"
        }, botToken);
      }

      if (user.gold < amount) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ *Insufficient funds!* You only have ${user.gold} gold.`
        }, botToken);
      }

      const targetUser = await userColl.findOne({ id: targetId });
      if (!targetUser) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Target user not found in the database.*"
        }, botToken);
      }

      // Perform transaction
      await userColl.updateOne({ id: userId }, { $inc: { gold: -amount } });
      await userColl.updateOne({ id: targetId }, { $inc: { gold: amount } });

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `💸 *Transfer Complete!* Sent \`${amount.toLocaleString()}\` gold coins to *${targetUser.first_name}*.`
      }, botToken);

    case '/mine':
    case '/work':
      const nowCooldown = Date.now();
      const lastWork = state.dailyCooldowns[userId] || 0;
      const cooldownPeriod = 5 * 60 * 1000; // 5 minutes work cooldown

      if (nowCooldown - lastWork < cooldownPeriod) {
        const remSecs = Math.floor((cooldownPeriod - (nowCooldown - lastWork)) / 1000);
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `⏳ *You are exhausted!* Please rest for another \`${remSecs}s\` before working again.`
        }, botToken);
      }

      const pay = Math.floor(Math.random() * 45) + 15; // 15 to 60 gold coins
      state.dailyCooldowns[userId] = nowCooldown;

      await userColl.updateOne({ id: userId }, { $inc: { gold: pay } });
      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `⛏️ *Shift Complete!* You worked hard and earned +${pay} 💰 gold coins.`
      }, botToken);

    case '/streak':
    case '/bonus':
      const lastBonus = user.last_bonus_claim ? new Date(user.last_bonus_claim).getTime() : 0;
      const oneDay = 24 * 60 * 60 * 1000;

      if (Date.now() - lastBonus < oneDay) {
        const hoursLeft = Math.ceil((oneDay - (Date.now() - lastBonus)) / (1000 * 60 * 60));
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `⏳ *Bonus already claimed today!* Check back in \`${hoursLeft} hours\`.`
        }, botToken);
      }

      const dailyReward = 150; // Daily reward gold
      await userColl.updateOne(
        { id: userId },
        {
          $inc: { gold: dailyReward },
          $set: { last_bonus_claim: new Date() }
        }
      );

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `🎁 *Daily Reward Claimed!* +${dailyReward} 💰 gold coins added to your account.`
      }, botToken);

    case '/rob':
      if (args.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚠️ *Usage:* `/rob [target_user_id]`"
        }, botToken);
      }

      const victimId = parseInt(args[0], 10);
      if (isNaN(victimId) || victimId === userId) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Invalid User ID.*"
        }, botToken);
      }

      const victim = await userColl.findOne({ id: victimId });
      if (!victim || (victim.gold || 0) < 50) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *This user doesn't have enough gold worth robbing!* (Min 50 gold)"
        }, botToken);
      }

      const success = Math.random() < 0.4; // 40% chance of success
      if (success) {
        const stolen = Math.floor(Math.random() * 40) + 10; // Steal 10 to 50 gold
        await userColl.updateOne({ id: userId }, { $inc: { gold: stolen } });
        await userColl.updateOne({ id: victimId }, { $inc: { gold: -stolen } });

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `🥷 *Robbery Successful!* You stole +${stolen} 💰 gold coins from *${victim.first_name}*!`
        }, botToken);
      } else {
        const fine = 25; // Fail penalty
        await userColl.updateOne({ id: userId }, { $inc: { gold: -fine } });

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `🚨 *Busted!* You failed the robbery and paid a fine of \`-${fine} gold\` coins to the guards.`
        }, botToken);
      }

    case '/marry':
    case '/propose':
      if (args.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚠️ *Usage:* `/propose [target_user_id]`"
        }, botToken);
      }

      const spouseId = parseInt(args[0], 10);
      if (isNaN(spouseId) || spouseId === userId) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Invalid User ID.*"
        }, botToken);
      }

      const spouse = await userColl.findOne({ id: spouseId });
      if (!spouse) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Could not find target user.*"
        }, botToken);
      }

      // Update marriage status in DB
      await userColl.updateOne({ id: userId }, { $set: { spouse: { id: spouseId, name: spouse.first_name } } });
      await userColl.updateOne({ id: spouseId }, { $set: { spouse: { id: userId, name: firstName } } });

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `🔔 *Wedding Bells!* *${firstName}* successfully married *${spouse.first_name}*! 💍`
      }, botToken);

    // Sudo & Dev Commands
    case '/give':
      const isSudo = await sudoColl.findOne({ user_id: userId }) || userId === 6118760915;
      if (!isSudo) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Sudo privileges required."
        }, botToken);
      }

      if (args.length < 3) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "⚠️ *Usage:* `/give [user_id] [gold/ruby] [amount]`"
        }, botToken);
      }

      const targetGiveId = parseInt(args[0], 10);
      const currency = args[1].toLowerCase();
      const giveAmt = parseInt(args[2], 10);

      if (isNaN(targetGiveId) || isNaN(giveAmt) || giveAmt <= 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Invalid target ID or amount.*"
        }, botToken);
      }

      const giveTarget = await userColl.findOne({ id: targetGiveId });
      if (!giveTarget) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *User not found.*"
        }, botToken);
      }

      if (currency === 'gold') {
        await userColl.updateOne({ id: targetGiveId }, { $inc: { gold: giveAmt } });
      } else if (currency === 'ruby' || currency === 'rubies') {
        await userColl.updateOne({ id: targetGiveId }, { $inc: { rubies: giveAmt } });
      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ *Invalid currency type. Choose 'gold' or 'ruby'.*"
        }, botToken);
      }

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `🎁 *Gift sent by Sudo Admin!* Granted +${giveAmt} ${currency} to *${giveTarget.first_name}*.`
      }, botToken);

    // ─── UPLOADER & SCRAPER COMMANDS ───
    case '/upload': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      let targetMsg = message;
      let reply = message.reply_to_message;
      if (reply) {
        targetMsg = reply;
      }

      let fileId = null;
      let isVideo = false;
      let fileName = "file.jpg";

      if (targetMsg.photo && targetMsg.photo.length > 0) {
        fileId = targetMsg.photo[targetMsg.photo.length - 1].file_id;
        fileName = "character.jpg";
      } else if (targetMsg.video) {
        fileId = targetMsg.video.file_id;
        isVideo = true;
        fileName = "character.mp4";
      } else if (targetMsg.document) {
        const mime = targetMsg.document.mime_type || "";
        if (mime.startsWith("image/") || mime.startsWith("video/")) {
          fileId = targetMsg.document.file_id;
          isVideo = mime.startsWith("video/");
          fileName = isVideo ? "character.mp4" : "character.jpg";
        }
      }

      if (!fileId) {
        const helpUpload = `❌ **Wrong format!**\n\n` +
          `Reply to a **photo or mp4**, then use one of:\n\n` +
          `**Format 1 — Pipe separator:**\n` +
          `\`/upload <anime> | <character> | <rarity_no>\`\n\n` +
          `**Format 2 — Dash separator:**\n` +
          `\`/upload <anime> - <character> - <rarity_no>\`\n\n` +
          `📌 mp4 → rarity auto-set to ⚜️ Animated\n\n` +
          `**Examples:**\n` +
          `\`/upload One Punch Man | Fubuki | 3\`\n` +
          `\`/upload One Punch Man - Fubuki - 3\`\n\n` +
          `Rarity scale: 1 to 16.`;

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: helpUpload,
          parse_mode: 'Markdown'
        }, botToken);
      }

      const rawText = reply ? text : (message.caption || "");
      const cmdParts = rawText.split(/\s+/);
      const afterCmd = rawText.substring(cmdParts[0].length).trim();

      const parsed = parseUploadArgs(afterCmd);
      if (!parsed) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Invalid arguments format!** Use `Anime | Character | Rarity` or `Anime - Character - Rarity`",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const { anime, charName, rarityNo } = parsed;
      const rarityNum = parseInt(rarityNo, 10);
      if (isNaN(rarityNum) || !RARITY_MAP[rarityNum]) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Invalid rarity number!** Rarity must be between 1 and 16.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const rarity = isVideo ? ANIMATED_RARITY : RARITY_MAP[rarityNum];

      const statusRes = await tgApi('sendMessage', {
        chat_id: chatId,
        text: `⏳ **Uploading** \`${charName}\` to Catbox and validating…`
      }, botToken);
      const statusMsgId = statusRes.result?.message_id;

      try {
        const fileBuffer = await downloadTelegramMedia(fileId, botToken);
        const imgUrl = await uploadToCatbox(fileBuffer, fileName);
        
        const charId = await getNextId(db);
        const price = Math.floor(Math.random() * (80000 - 60000 + 1)) + 60000;
        const mention = `[${firstName}](tg://user?id=${userId})`;

        const characterDoc = {
          id: charId,
          name: charName,
          anime: anime,
          rarity: rarity,
          price: price,
          img_url: imgUrl,
          mention: mention
        };

        const pubCaption = buildChannelCaption(charName, anime, rarity, price, charId, mention);
        let sentMsgId = null;

        if (isVideo) {
          const sent = await tgApi('sendVideo', {
            chat_id: UPLOAD_CHANNEL_ID,
            video: imgUrl,
            caption: pubCaption,
            parse_mode: 'Markdown'
          }, botToken);
          sentMsgId = sent.result?.message_id;
          
          try {
            await tgApi('sendVideo', {
              chat_id: UPLOAD_GC_ID,
              video: imgUrl,
              caption: pubCaption,
              parse_mode: 'Markdown'
            }, botToken);
          } catch (e) {}
        } else {
          const sent = await tgApi('sendPhoto', {
            chat_id: UPLOAD_CHANNEL_ID,
            photo: imgUrl,
            caption: pubCaption,
            parse_mode: 'Markdown'
          }, botToken);
          sentMsgId = sent.result?.message_id;

          try {
            await tgApi('sendPhoto', {
              chat_id: UPLOAD_GC_ID,
              photo: imgUrl,
              caption: pubCaption,
              parse_mode: 'Markdown'
            }, botToken);
          } catch (e) {}
        }

        if (sentMsgId) {
          characterDoc.message_id = sentMsgId;
        }

        await db.collection('anime_characters').insertOne(characterDoc);

        const doneText = `✅ **Character Saved!**\n\n` +
          `🆔 **ID:** \`${charId}\`\n` +
          `🎭 **Name:** *${charName}*\n` +
          `📺 **Anime:** *${anime}*\n` +
          `⭐ **Rarity:** *${rarity}*\n` +
          `💰 **Price:** \`${price.toLocaleString()} coins\`\n` +
          `🖼️ **URL:** [View File](${imgUrl})`;

        if (statusMsgId) {
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: statusMsgId,
            text: doneText,
            parse_mode: 'Markdown'
          }, botToken);
        }
      } catch (err) {
        console.error("Upload error:", err);
        if (statusMsgId) {
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: statusMsgId,
            text: `❌ **Upload failed:**\n\`${err.message}\``
          }, botToken);
        }
      }
      break;
    }

    case '/il': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const reply = message.reply_to_message;
      if (!reply) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Reply to a character spawn message** with `/il <rarity_no>`",
          parse_mode: 'Markdown'
        }, botToken);
      }

      if (args.length !== 1) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Wrong format!** Use `/il <rarity_no>`",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const rarityNo = parseInt(args[0], 10);
      if (isNaN(rarityNo) || !RARITY_MAP[rarityNo]) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Invalid rarity number!** Rarity must be between 1 and 16.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      let fileId = null;
      let isVideo = false;
      let fileName = "file.jpg";

      if (reply.photo && reply.photo.length > 0) {
        fileId = reply.photo[reply.photo.length - 1].file_id;
        fileName = "character.jpg";
      } else if (reply.video) {
        fileId = reply.video.file_id;
        isVideo = true;
        fileName = "character.mp4";
      } else if (reply.document) {
        const mime = reply.document.mime_type || "";
        if (mime.startsWith("image/") || mime.startsWith("video/")) {
          fileId = reply.document.file_id;
          isVideo = mime.startsWith("video/");
          fileName = isVideo ? "character.mp4" : "character.jpg";
        }
      }

      if (!fileId) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Replied message does not contain photo or video!**",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const captionText = (reply.caption || reply.text || "").trim();
      const { charName, anime } = extractIL(captionText);

      if (!charName || !anime) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Could not detect character info from caption.**\n\nUse `/upload` to enter manually.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      const rarity = isVideo ? ANIMATED_RARITY : RARITY_MAP[rarityNo];

      const statusRes = await tgApi('sendMessage', {
        chat_id: chatId,
        text: `⏳ **Auto-uploading** \`${charName}\` from \`${anime}\`…`
      }, botToken);
      const statusMsgId = statusRes.result?.message_id;

      try {
        const fileBuffer = await downloadTelegramMedia(fileId, botToken);
        const imgUrl = await uploadToCatbox(fileBuffer, fileName);
        
        const charId = await getNextId(db);
        const price = Math.floor(Math.random() * (80000 - 60000 + 1)) + 60000;
        const mention = `[${firstName}](tg://user?id=${userId})`;

        const characterDoc = {
          id: charId,
          name: charName,
          anime: anime,
          rarity: rarity,
          price: price,
          img_url: imgUrl,
          mention: mention
        };

        const pubCaption = buildChannelCaption(charName, anime, rarity, price, charId, mention);
        let sentMsgId = null;

        if (isVideo) {
          const sent = await tgApi('sendVideo', {
            chat_id: UPLOAD_CHANNEL_ID,
            video: imgUrl,
            caption: pubCaption,
            parse_mode: 'Markdown'
          }, botToken);
          sentMsgId = sent.result?.message_id;
          
          try {
            await tgApi('sendVideo', {
              chat_id: UPLOAD_GC_ID,
              video: imgUrl,
              caption: pubCaption,
              parse_mode: 'Markdown'
            }, botToken);
          } catch (e) {}
        } else {
          const sent = await tgApi('sendPhoto', {
            chat_id: UPLOAD_CHANNEL_ID,
            photo: imgUrl,
            caption: pubCaption,
            parse_mode: 'Markdown'
          }, botToken);
          sentMsgId = sent.result?.message_id;

          try {
            await tgApi('sendPhoto', {
              chat_id: UPLOAD_GC_ID,
              photo: imgUrl,
              caption: pubCaption,
              parse_mode: 'Markdown'
            }, botToken);
          } catch (e) {}
        }

        if (sentMsgId) {
          characterDoc.message_id = sentMsgId;
        }

        await db.collection('anime_characters').insertOne(characterDoc);

        const doneText = `✅ **Character Saved via Auto-Scraper!**\n\n` +
          `🆔 **ID:** \`${charId}\`\n` +
          `🎭 **Name:** *${charName}*\n` +
          `📺 **Anime:** *${anime}*\n` +
          `⭐ **Rarity:** *${rarity}*\n` +
          `💰 **Price:** \`${price.toLocaleString()} coins\`\n` +
          `🖼️ **URL:** [View File](${imgUrl})`;

        if (statusMsgId) {
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: statusMsgId,
            text: doneText,
            parse_mode: 'Markdown'
          }, botToken);
        }
      } catch (err) {
        console.error("Auto-upload error:", err);
        if (statusMsgId) {
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: statusMsgId,
            text: `❌ **Auto-upload failed:**\n\`${err.message}\``
          }, botToken);
        }
      }
      break;
    }

    case '/uchar':
    case '/updatechar': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      if (args.length < 2) {
        const helpUchar = `❌ **Wrong format!**\n\n` +
          `\`/uchar media <id>\` — reply to new photo/mp4\n` +
          `\`/uchar rarity <id> <no>\`\n` +
          `\`/uchar name <id> <new name>\`\n` +
          `\`/uchar anime <id> <new anime>\`\n\n` +
          `All changes also update the channel post automatically.`;

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: helpUchar,
          parse_mode: 'Markdown'
        }, botToken);
      }

      const sub = args[0].toLowerCase();
      const rawCharId = args[1];
      const charId = rawCharId.padStart(2, '0');

      const charColl = db.collection('anime_characters');
      const char = await charColl.findOne({ id: charId });
      if (!char) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ **Character \`${charId}\` not found in database!**`
        }, botToken);
      }

      if (sub === 'media') {
        const reply = message.reply_to_message;
        if (!reply) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Reply to a new photo or video** with `/uchar media <id>`"
          }, botToken);
        }

        let fileId = null;
        let isVideo = false;
        let fileName = "file.jpg";

        if (reply.photo && reply.photo.length > 0) {
          fileId = reply.photo[reply.photo.length - 1].file_id;
          fileName = "character.jpg";
        } else if (reply.video) {
          fileId = reply.video.file_id;
          isVideo = true;
          fileName = "character.mp4";
        } else if (reply.document) {
          const mime = reply.document.mime_type || "";
          if (mime.startsWith("image/") || mime.startsWith("video/")) {
            fileId = reply.document.file_id;
            isVideo = mime.startsWith("video/");
            fileName = isVideo ? "character.mp4" : "character.jpg";
          }
        }

        if (!fileId) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Replied message does not contain photo or video!**"
          }, botToken);
        }

        const statusRes = await tgApi('sendMessage', {
          chat_id: chatId,
          text: `⏳ **Downloading & updating media** for character \`${charId}\`…`
        }, botToken);
        const statusMsgId = statusRes.result?.message_id;

        try {
          const fileBuffer = await downloadTelegramMedia(fileId, botToken);
          const newUrl = await uploadToCatbox(fileBuffer, fileName);

          const newRarity = isVideo ? ANIMATED_RARITY : char.rarity;

          const updateFields = { img_url: newUrl };
          if (isVideo) {
            updateFields.rarity = newRarity;
          }

          await charColl.updateOne({ id: charId }, { $set: updateFields });

          const editErr = await editChannelPost(db, botToken, charId);
          const chStatus = !editErr ? "📡 Channel post updated." : `⚠️ Channel edit error: \`${editErr}\``;

          const doneText = `✅ **Media Updated!**\n\n` +
            `🆔 **ID:** \`${charId}\`\n` +
            `🎭 **Name:** *${char.name}*\n` +
            `⭐ **Rarity:** *${newRarity}*\n` +
            `🖼️ **URL:** [View File](${newUrl})\n\n` +
            `${chStatus}`;

          if (statusMsgId) {
            await tgApi('editMessageText', {
              chat_id: chatId,
              message_id: statusMsgId,
              text: doneText,
              parse_mode: 'Markdown'
            }, botToken);
          }
        } catch (err) {
          console.error("Uchar media error:", err);
          if (statusMsgId) {
            await tgApi('editMessageText', {
              chat_id: chatId,
              message_id: statusMsgId,
              text: `❌ **Failed to update media:**\n\`${err.message}\``
            }, botToken);
          }
        }

      } else if (sub === 'rarity') {
        if (args.length < 3) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Usage:** `/uchar rarity <id> <rarity_no>`"
          }, botToken);
        }
        const rarityNo = parseInt(args[2], 10);
        const newRarity = RARITY_MAP[rarityNo];
        if (!newRarity) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Invalid rarity number!** Must be between 1 and 16."
          }, botToken);
        }

        const oldRarity = char.rarity;
        await charColl.updateOne({ id: charId }, { $set: { rarity: newRarity } });

        const editErr = await editChannelPost(db, botToken, charId);
        const chStatus = !editErr ? "📡 Channel post updated." : `⚠️ Channel edit error: \`${editErr}\``;

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `✅ **Rarity Updated!**\n\n` +
            `🆔 **ID:** \`${charId}\`\n` +
            `🎭 **Name:** *${char.name}*\n` +
            `⭐ **Old:** *${oldRarity}*\n` +
            `⭐ **New:** *${newRarity}*\n\n` +
            `${chStatus}`,
          parse_mode: 'Markdown'
        }, botToken);

      } else if (sub === 'name') {
        const newName = args.slice(2).join(' ').trim();
        if (!newName) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Usage:** `/uchar name <id> <new name>`"
          }, botToken);
        }

        const oldName = char.name;
        await charColl.updateOne({ id: charId }, { $set: { name: clean(newName) } });

        const editErr = await editChannelPost(db, botToken, charId);
        const chStatus = !editErr ? "📡 Channel post updated." : `⚠️ Channel edit error: \`${editErr}\``;

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `✅ **Name Updated!**\n\n` +
            `🆔 **ID:** \`${charId}\`\n` +
            `📝 **Old:** *${oldName}*\n` +
            `📝 **New:** *${clean(newName)}*\n\n` +
            `${chStatus}`,
          parse_mode: 'Markdown'
        }, botToken);

      } else if (sub === 'anime') {
        const newAnime = args.slice(2).join(' ').trim();
        if (!newAnime) {
          return tgApi('sendMessage', {
            chat_id: chatId,
            text: "❌ **Usage:** `/uchar anime <id> <new anime>`"
          }, botToken);
        }

        const oldAnime = char.anime;
        await charColl.updateOne({ id: charId }, { $set: { anime: clean(newAnime) } });

        const editErr = await editChannelPost(db, botToken, charId);
        const chStatus = !editErr ? "📡 Channel post updated." : `⚠️ Channel edit error: \`${editErr}\``;

        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `✅ **Anime Updated!**\n\n` +
            `🆔 **ID:** \`${charId}\`\n` +
            `📺 **Old:** *${oldAnime}*\n` +
            `📺 **New:** *${clean(newAnime)}*\n\n` +
            `${chStatus}`,
          parse_mode: 'Markdown'
        }, botToken);

      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ **Unknown uchar subcommand!** Choose media, rarity, name, or anime.`
        }, botToken);
      }
      break;
    }

    case '/findchar': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      if (args.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Usage:** `/findchar <name or anime>`"
        }, botToken);
      }

      const searchTerm = args.join(' ').trim();
      const chars = await db.collection('anime_characters').find({
        $or: [
          { name: { $regex: searchTerm, $options: 'i' } },
          { anime: { $regex: searchTerm, $options: 'i' } }
        ]
      }).limit(50).toArray();

      if (chars.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ **No results found for \`${searchTerm}\`.**`
        }, botToken);
      }

      const lines = [`🔍 **Results (${chars.length})**\n` + '─'.repeat(30) + '\n'];
      for (const c of chars.slice(0, 20)) {
        lines.push(`🆔 \`${c.id}\` | *${c.name}* | _${c.anime}_`);
      }
      if (chars.length > 20) {
        lines.push(`\n... and ${chars.length - 20} more results.`);
      }

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: lines.join('\n'),
        parse_mode: 'Markdown'
      }, botToken);
    }

    case '/charinfo': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      if (args.length !== 1) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Usage:** `/charinfo <id>`"
        }, botToken);
      }

      const charId = args[0].trim().padStart(2, '0');
      const char = await db.collection('anime_characters').findOne({ id: charId });
      if (!char) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ **ID \`${charId}\` not found.**`
        }, botToken);
      }

      let imgStatus = "—";
      if (char.img_url) {
        try {
          const res = await fetch(char.img_url, { method: 'HEAD' });
          imgStatus = res.ok ? "✅ OK" : `❌ HTTP ${res.status}`;
        } catch (e) {
          imgStatus = `❌ Error: ${e.message}`;
        }
      }

      let infoText = `📋 **Character Info**\n` + '─'.repeat(30) + `\n\n` +
        `🆔 **ID:** \`${char.id}\`\n` +
        `🎭 **Name:** *${char.name}*\n` +
        `📺 **Anime:** *${char.anime}*\n` +
        `⭐ **Rarity:** *${char.rarity}*\n` +
        `💰 **Price:** \`${(char.price || 0).toLocaleString()} coins\`\n\n` +
        `🖼️ **Image Status:** \`${imgStatus}\`\n` +
        `🔗 **URL:** [View File](${char.img_url})`;

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: infoText,
        parse_mode: 'Markdown'
      }, botToken);
    }

    case '/replace': {
      const authorized = await isUploader(userId, db);
      if (!authorized) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Uploader privileges required.",
          parse_mode: 'Markdown'
        }, botToken);
      }

      if (args.length === 0) {
        const usageReplace = `❌ **Usage:** \`/replace <id>-<url>-<anime>-<name>-<rarity>\`\n\n` +
          `Example: \`/replace 42-https://files.catbox.moe/oai7m9.jpg-Naruto-Kakashi-🟠 Rare\``;
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: usageReplace,
          parse_mode: 'Markdown'
        }, botToken);
      }

      const input = args.join(' ');
      const parts = input.split('-');
      if (parts.length < 5) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Need 5 fields separated by dashes:** id-url-anime-name-rarity"
        }, botToken);
      }

      const id = parts[0].trim().padStart(2, '0');
      const url = parts[1].trim();
      const anime = parts[2].trim();
      const name = parts[3].trim();
      const rarityRaw = parts.slice(4).join('-').trim();

      const charColl = db.collection('anime_characters');
      const char = await charColl.findOne({ id: id });
      if (!char) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `❌ **ID \`${id}\` not found.**`
        }, botToken);
      }

      const oldName = char.name;
      const oldAnime = char.anime;
      const oldRarity = char.rarity;

      await charColl.updateOne(
        { id: id },
        {
          $set: {
            img_url: url,
            anime: clean(anime),
            name: clean(name),
            rarity: rarityRaw
          }
        }
      );

      await editChannelPost(db, botToken, id);

      const doneText = `🔄 **Replaced successfully!**\n\n` +
        `🆔 \`${id}\`\n` +
        `👤 *${oldName}* → *${clean(name)}*\n` +
        `📺 *${oldAnime}* → *${clean(anime)}*\n` +
        `⭐ *${oldRarity}* → *${rarityRaw}*\n\n` +
        `✅ By: [${firstName}](tg://user?id=${userId})`;

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: doneText,
        parse_mode: 'Markdown'
      }, botToken);
    }

    case '/adduploader': {
      const isOwner = OWNER_IDS.includes(userId);
      if (!isOwner) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Only bot owners can add uploaders."
        }, botToken);
      }

      let targetId = null;
      let targetName = "User";

      if (message.reply_to_message && message.reply_to_message.from) {
        const u = message.reply_to_message.from;
        targetId = u.id;
        targetName = u.first_name || String(u.id);
      } else if (args.length > 0 && /^\d+$/.test(args[0])) {
        targetId = parseInt(args[0], 10);
        targetName = `User ${targetId}`;
      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Reply to a user or use** `/adduploader <user_id>`"
        }, botToken);
      }

      const uploaderColl = db.collection('uploader');
      const exists = await uploaderColl.findOne({ user_id: targetId });
      if (exists) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `⚠️ **${targetName}** is already an uploader.`
        }, botToken);
      }

      await uploaderColl.insertOne({ user_id: targetId, added_at: new Date() });
      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `✅ **${targetName}** (\`${targetId}\`) added as uploader!\n\nAvailable commands:\n• \`/upload\`\n• \`/il\`\n• \`/uchar\`\n• \`/charinfo\`\n• \`/findchar\`\n• \`/replace\``,
        parse_mode: 'Markdown'
      }, botToken);
    }

    case '/rmuploader': {
      const isOwner = OWNER_IDS.includes(userId);
      if (!isOwner) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Only bot owners can remove uploaders."
        }, botToken);
      }

      let targetId = null;
      let targetName = "User";

      if (message.reply_to_message && message.reply_to_message.from) {
        const u = message.reply_to_message.from;
        targetId = u.id;
        targetName = u.first_name || String(u.id);
      } else if (args.length > 0 && /^\d+$/.test(args[0])) {
        targetId = parseInt(args[0], 10);
        targetName = `User ${targetId}`;
      } else {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "❌ **Reply to a user or use** `/rmuploader <user_id>`"
        }, botToken);
      }

      const uploaderColl = db.collection('uploader');
      const exists = await uploaderColl.findOne({ user_id: targetId });
      if (!exists) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: `⚠️ **${targetName}** is not an uploader.`
        }, botToken);
      }

      await uploaderColl.deleteOne({ user_id: targetId });
      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `🗑️ **Uploader ${targetName}** removed.`
      }, botToken);
    }

    case '/uploaderlist': {
      const isOwner = OWNER_IDS.includes(userId);
      if (!isOwner) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "🚫 *Access Denied!* Only bot owners can view uploaders list."
        }, botToken);
      }

      const uploaders = await db.collection('uploader').find().toArray();
      if (uploaders.length === 0) {
        return tgApi('sendMessage', {
          chat_id: chatId,
          text: "📭 **No uploaders registered yet.**"
        }, botToken);
      }

      const lines = [`👥 **Uploaders (${uploaders.length})**\n` + '─'.repeat(25)];
      uploaders.forEach((doc, idx) => {
        lines.push(`${idx + 1}. User ID: \`${doc.user_id}\``);
      });

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: lines.join('\n'),
        parse_mode: 'Markdown'
      }, botToken);
    }

      return tgApi('sendMessage', {
        chat_id: chatId,
        text: `🎁 *Gift sent by Sudo Admin!* Granted +${giveAmt} ${currency} to *${giveTarget.first_name}*.`
      }, botToken);

    default:
      // Silently ignore other commands or non-commands
      break;
  }
}

// Callback queries handler (combat actions, etc.)
async function handleBotCallback(callbackQuery, db, botToken) {
  const { id: callbackQueryId, data, message, from } = callbackQuery;
  if (!data || !message) return;

  const chatId = message.chat.id;
  const messageId = message.message_id;
  const userId = from.id;
  const firstName = from.first_name || "Collector";

  const userColl = db.collection('user_collection');

  if (data.startsWith('smash_engage:')) {
    const charId = data.split(':')[1];
    const opponent = state.activeSmashes[userId];

    if (!opponent || String(opponent.id) !== charId) {
      return tgApi('answerCallbackQuery', {
        callback_query_id: callbackQueryId,
        text: "❌ This combat session is no longer active!",
        show_alert: true
      }, botToken);
    }

    // Resolve Battle
    const victory = Math.random() < 0.55; // 55% chance of success
    delete state.activeSmashes[userId];

    if (victory) {
      // Add to collection
      await userColl.updateOne(
        { id: userId },
        { $push: { characters: opponent } }
      );

      await tgApi('answerCallbackQuery', {
        callback_query_id: callbackQueryId,
        text: "🎉 Combat Victory!"
      }, botToken);

      await tgApi('editMessageCaption', {
        chat_id: chatId,
        message_id: messageId,
        caption: `🎖️ *VICTORY!* \n\n*${firstName}* successfully defeated *${opponent.name}* and captured them into their harem!\n\n• *Anime:* \`${opponent.anime}\`\n• *Rarity:* \`${opponent.rarity}\``,
        parse_mode: 'Markdown'
      }, botToken);
    } else {
      await tgApi('answerCallbackQuery', {
        callback_query_id: callbackQueryId,
        text: "💀 Defeat!"
      }, botToken);

      await tgApi('editMessageCaption', {
        chat_id: chatId,
        message_id: messageId,
        caption: `💀 *DEFEAT!* \n\n*${opponent.name}* was too strong. *${firstName}* was knocked unconscious! Recruit stronger waifus and try again.`,
        parse_mode: 'Markdown'
      }, botToken);
    }
  } else if (data.startsWith('smash_retreat:')) {
    const opponent = state.activeSmashes[userId];
    delete state.activeSmashes[userId];

    await tgApi('answerCallbackQuery', {
      callback_query_id: callbackQueryId,
      text: "🏃 Retreated safely."
    }, botToken);

    await tgApi('editMessageCaption', {
      chat_id: chatId,
      message_id: messageId,
      caption: `🏃 *Tactical Retreat!* \n\nYou successfully fled from *${opponent?.name || 'the opponent'}* back to safety.`,
      parse_mode: 'Markdown'
    }, botToken);
  }
}

module.exports = {
  handleBotCommand,
  handleBotCallback
};
