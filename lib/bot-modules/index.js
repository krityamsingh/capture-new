const MONGODB_URI = process.env.MONGODB_URI || "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0";

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
