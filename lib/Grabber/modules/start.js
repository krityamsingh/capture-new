/**
 * modules/start.js — mirrors start.py
 * /start, /help, /ping, /stats, /id, /botstats
 */
const { OWNER_IDS, BOT_USERNAME } = require('../__init__');

async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return await res.json();
}

async function startCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { first_name: firstName } = message.from;
  const webAppUrl = `https://${ctx.host}`;

  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `🌸 *Welcome, ${firstName}!* 🌸\n\nPlay **Captrue** entirely within our Next-generation Web App! Tap the button below to open the app, watch ads to get random anime characters, and manage your harem!`,
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [{ text: '🎮 Open WebApp', web_app: { url: webAppUrl } }]
      ]
    }
  }, botToken);
}

async function helpCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const webAppUrl = `https://${ctx.host}`;
  
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `🤖 *Captrue Help*\n\nAll gameplay features (including collection viewer, daily bonuses, and shop) have moved exclusively to the Web App.\n\nTap the button below to play!`,
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [{ text: '🎮 Open WebApp', web_app: { url: webAppUrl } }]
      ]
    }
  }, botToken);
}

module.exports = {
  commands: {
    start: startCmd,
    help: helpCmd,
  },
};
