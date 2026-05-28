/**
 * modules/spawn.js — mirrors spawn.py
 * Handles character spawn mechanics on group message traffic.
 */
const Grabber = require('../__init__');

const RARITY_MAP = {
  1: '🔴 Common', 2: '🔵 Uncommon', 3: '🟠 Rare', 4: '🟡 Legendary',
  5: '⚪ Epic', 6: '🔮 Limited Edition', 7: '🫧 Premium', 8: '🏵️ Exotic',
  9: '⚜️ Animated', 10: '🌼 Celebrity', 11: '🎐 Crystal', 12: '🍹 Neon',
  13: '🧿 Supreme', 14: '⚡ Thundra', 15: '🛸 Galvoria', 16: '🌟 Solar Verse',
};

// In-memory state — shared per serverless instance
if (!global.grabberSpawnState) {
  global.grabberSpawnState = {
    messageCounts: {},
    spawnedCharacters: {},
    lastDespawned: {},
  };
}
const state = global.grabberSpawnState;

function rollRarity() {
  const roll = Math.random() * 100;
  if (roll < 40)   return { display: '🔴 Common',         query: 'Common' };
  if (roll < 65)   return { display: '🔵 Uncommon',       query: 'Uncommon' };
  if (roll < 80)   return { display: '🟠 Rare',           query: 'Rare' };
  if (roll < 90)   return { display: '🟡 Legendary',      query: 'Legendary' };
  if (roll < 95)   return { display: '🫧 Premium',        query: 'Premium' };
  if (roll < 98)   return { display: '🔮 Limited Edition', query: 'Limited' };
  if (roll < 99.5) return { display: '🏵️ Exotic',        query: 'Exotic' };
  return                  { display: '⚜️ Animated',       query: 'Animated' };
}

async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return await res.json();
}

async function spawnHook(update, ctx) {
  const { db, botToken, collections } = ctx;
  const message = update.message;
  const chatId  = message.chat.id;

  state.messageCounts[chatId] = (state.messageCounts[chatId] || 0) + 1;

  const grp = await collections.groups?.findOne({ chat_id: chatId });
  const frequency = grp?.spawn_frequency || 15;

  if (state.messageCounts[chatId] < frequency) return;
  if (state.spawnedCharacters[chatId]) return;

  state.messageCounts[chatId] = 0;

  const rolled = rollRarity();
  const chars  = await collections.collection.aggregate([
    { $match: { rarity: { $regex: rolled.query, $options: 'i' }, img_url: { $exists: true, $ne: '' }, deleted: { $ne: true } } },
    { $sample: { size: 1 } },
  ]).toArray();

  const character = chars[0];
  if (!character) return;

  state.spawnedCharacters[chatId] = character;

  await tgApi('sendPhoto', {
    chat_id: chatId,
    photo: character.img_url,
    caption: `🌸 *A wild anime character has appeared!* 🌸\n\n• *Rarity:* ${rolled.display}\n• *Status:* ⚔️ Capture them now!\n\nUse \`/capture [name]\` or \`/smash\` to claim this character!`,
    parse_mode: 'Markdown',
  }, botToken);

  setTimeout(async () => {
    if (state.spawnedCharacters[chatId] === character) {
      state.lastDespawned[chatId] = character;
      delete state.spawnedCharacters[chatId];
      await tgApi('sendMessage', { chat_id: chatId, text: `🌬️ *The character (${character.name}) fled into the shadows...*`, parse_mode: 'Markdown' }, botToken);
    }
  }, 120000);
}

module.exports = {
  spawnHooks: [spawnHook],
  state,
};
