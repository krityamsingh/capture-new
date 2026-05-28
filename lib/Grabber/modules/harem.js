/**
 * modules/harem.js — mirrors harem.py + fav.py + marry.py + profile.py
 */
async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return await res.json();
}

async function haremCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  const user = await collections.user_collection.findOne({ id: userId });
  const chars = user?.characters || [];

  if (!chars.length) return tgApi('sendMessage', {
    chat_id: chatId,
    text: '😔 *Your harem is empty!* Capture spawned characters to fill it.',
    parse_mode: 'Markdown',
  }, botToken);

  let display = chars;
  if (args.length) display = chars.filter(c => c.rarity?.toLowerCase().includes(args.join(' ').toLowerCase()));

  const listStr = display.slice(0, 10).map((c, i) => `${i + 1}. *${c.name}* (${c.rarity})`).join('\n');
  const more    = display.length > 10 ? `\n...and ${display.length - 10} more.` : '';

  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `💝 *${firstName}'s Harem (${display.length} characters):*\n\n${listStr || '_No matches_'}${more}`,
    parse_mode: 'Markdown',
  }, botToken);
}

async function favCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  const user = await collections.user_collection.findOne({ id: userId });
  const chars = user?.characters || [];

  if (!chars.length) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Capture characters first!*', parse_mode: 'Markdown' }, botToken);

  if (!args.length) {
    const fav = user?.favorites?.[0];
    if (fav) return tgApi('sendMessage', {
      chat_id: chatId,
      text: `⭐ *Favorite:* *${fav.name}*\n• *Anime:* \`${fav.anime}\`\n• *Rarity:* \`${fav.rarity}\``,
      parse_mode: 'Markdown',
    }, botToken);
    return tgApi('sendMessage', { chat_id: chatId, text: 'ℹ️ *No favorite set.* Use `/fav [character name]`', parse_mode: 'Markdown' }, botToken);
  }

  const name  = args.join(' ').toLowerCase();
  const match = chars.find(c => c.name?.toLowerCase().includes(name));
  if (!match) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Character not found in harem.*', parse_mode: 'Markdown' }, botToken);

  await collections.user_collection.updateOne({ id: userId }, { $set: { favorites: [match] } });
  return tgApi('sendMessage', { chat_id: chatId, text: `⭐ *Favorite set!* *${match.name}* is now your star!`, parse_mode: 'Markdown' }, botToken);
}

async function marryCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  if (!args.length) return tgApi('sendMessage', { chat_id: chatId, text: '⚠️ *Usage:* `/marry [user_id]`', parse_mode: 'Markdown' }, botToken);
  const spouseId = parseInt(args[0], 10);
  if (isNaN(spouseId) || spouseId === userId) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Invalid user ID.*', parse_mode: 'Markdown' }, botToken);

  const spouse = await collections.user_collection.findOne({ id: spouseId });
  if (!spouse) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *User not found.*', parse_mode: 'Markdown' }, botToken);

  await collections.user_collection.updateOne({ id: userId },   { $set: { spouse: { id: spouseId, name: spouse.first_name } } });
  await collections.user_collection.updateOne({ id: spouseId }, { $set: { spouse: { id: userId, name: firstName } } });
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `🔔 *Wedding Bells!* *${firstName}* married *${spouse.first_name}*! 💍`,
    parse_mode: 'Markdown',
  }, botToken);
}

module.exports = {
  commands: {
    harem: haremCmd,
    fav: favCmd, favorite: favCmd,
    marry: marryCmd, propose: marryCmd,
  },
};
