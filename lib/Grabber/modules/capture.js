/**
 * modules/capture.js — mirrors smash.py + capture logic
 * Handles /capture, /smash, /exit commands
 */
if (!global.grabberCombatState) {
  global.grabberCombatState = { activeSmashes: {} };
}
const combatState = global.grabberCombatState;

async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return await res.json();
}

function isNameMatch(guess, charName) {
  const clean = s => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim().split(/\s+/);
  const g = clean(guess), n = clean(charName);
  if (!g.length || !n.length) return false;
  const fg = g.join(' '), fn = n.join(' ');
  return fg === fn || fg === n[0] || fg === n[n.length - 1];
}

async function captureCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  // Import spawn state lazily
  const spawnState = global.grabberSpawnState || {};
  const character = spawnState.spawnedCharacters?.[chatId];

  if (!character) {
    return tgApi('sendMessage', { chat_id: chatId, text: '🌫️ *No character is active right now.*', parse_mode: 'Markdown' }, botToken);
  }
  if (!args.length) {
    return tgApi('sendMessage', { chat_id: chatId, text: '⚠️ *Usage:* `/capture [name]`', parse_mode: 'Markdown' }, botToken);
  }

  const guess = args.join(' ');
  if (isNameMatch(guess, character.name)) {
    if (spawnState.spawnedCharacters) delete spawnState.spawnedCharacters[chatId];
    const gold = Math.floor(Math.random() * 95) + 5;
    await collections.user_collection.updateOne({ id: userId }, { $push: { characters: character }, $inc: { gold } });
    return tgApi('sendMessage', {
      chat_id: chatId,
      text: `🎉 *Correct!* ${firstName} captured *${character.name}*!\n• *Anime:* \`${character.anime}\`\n• *Rarity:* \`${character.rarity}\`\n• *Reward:* +${gold} 💰 gold!`,
      parse_mode: 'Markdown',
    }, botToken);
  }
  return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Incorrect name!* Try again.', parse_mode: 'Markdown' }, botToken);
}

async function smashCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;

  const spawnState = global.grabberSpawnState || {};
  const character = spawnState.spawnedCharacters?.[chatId];

  if (!character) return tgApi('sendMessage', { chat_id: chatId, text: '🌫️ *No character active to smash.*', parse_mode: 'Markdown' }, botToken);
  if (combatState.activeSmashes[userId]) return tgApi('sendMessage', { chat_id: chatId, text: '⚔️ *Already in combat!* Use /exit first.', parse_mode: 'Markdown' }, botToken);

  combatState.activeSmashes[userId] = character;
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `⚔️ *Combat initiated against ${character.name}!*\n• *Power Level:* \`${character.rarity}\``,
    parse_mode: 'Markdown',
    reply_markup: { inline_keyboard: [[
      { text: '💥 Smash Attack', callback_data: `smash_engage:${character.id}` },
      { text: '🏃 Retreat', callback_data: `smash_retreat:${character.id}` },
    ]]},
  }, botToken);
}

async function exitCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;

  const opponent = combatState.activeSmashes[userId];
  delete combatState.activeSmashes[userId];
  if (opponent) return tgApi('sendMessage', { chat_id: chatId, text: `🚪 *You fled from ${opponent.name}.*`, parse_mode: 'Markdown' }, botToken);
  return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Not in combat.*', parse_mode: 'Markdown' }, botToken);
}

async function smashEngageCallback(callbackQuery, ctx) {
  const { botToken, collections } = ctx;
  const { id: cqId, data, message, from } = callbackQuery;
  const charId  = data.split(':')[1];
  const chatId  = message.chat.id;
  const msgId   = message.message_id;
  const userId  = from.id;
  const firstName = from.first_name;
  const opponent = combatState.activeSmashes[userId];

  if (!opponent || String(opponent.id) !== charId) {
    return tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '❌ Combat session expired!', show_alert: true }, botToken);
  }
  delete combatState.activeSmashes[userId];
  const victory = Math.random() < 0.55;
  if (victory) {
    await collections.user_collection.updateOne({ id: userId }, { $push: { characters: opponent } });
    await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '🎉 Victory!' }, botToken);
    return tgApi('editMessageCaption', {
      chat_id: chatId, message_id: msgId,
      caption: `🎖️ *VICTORY!* *${firstName}* captured *${opponent.name}*!\n• *Anime:* \`${opponent.anime}\`\n• *Rarity:* \`${opponent.rarity}\``,
      parse_mode: 'Markdown',
    }, botToken);
  }
  await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '💀 Defeat!' }, botToken);
  return tgApi('editMessageCaption', {
    chat_id: chatId, message_id: msgId,
    caption: `💀 *DEFEAT!* *${opponent.name}* was too strong. Recruit stronger characters!`,
    parse_mode: 'Markdown',
  }, botToken);
}

async function smashRetreatCallback(callbackQuery, ctx) {
  const { botToken } = ctx;
  const { id: cqId, data, message, from } = callbackQuery;
  const userId = from.id;
  const opponent = combatState.activeSmashes[userId];
  delete combatState.activeSmashes[userId];
  await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '🏃 Retreated safely.' }, botToken);
  return tgApi('editMessageCaption', {
    chat_id: message.chat.id, message_id: message.message_id,
    caption: `🏃 *Tactical Retreat!* You fled from *${opponent?.name || 'the opponent'}*.`,
    parse_mode: 'Markdown',
  }, botToken);
}

module.exports = {
  commands: {
    capture: captureCmd,
    smash:   smashCmd,
    exit:    exitCmd,
  },
  callbacks: {
    'smash_engage:':  smashEngageCallback,
    'smash_retreat:': smashRetreatCallback,
  },
};
