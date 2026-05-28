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
  const isGroup = message.chat.type !== 'private';

  if (isGroup) {
    return tgApi('sendMessage', {
      chat_id: chatId,
      text: `⚔️ *CaptureCharacter* is ready!\nUse \`/help\` to see all commands.`,
      parse_mode: 'Markdown',
    }, botToken);
  }

  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `
🌸 *ᴡᴇʟᴄᴏᴍᴇ, ${firstName}!* 🌸

ɪ ᴀᴍ *CaptureCharacter* — ᴛʜᴇ ᴜʟᴛɪᴍᴀᴛᴇ ᴀɴɪᴍᴇ ᴄᴀᴘᴛᴜʀᴇ ʙᴏᴛ!

📌 *Hᴏᴡ ᴛᴏ Pʟᴀʏ:*
• Add me to a group
• Anime characters spawn every 15 messages
• Use \`/capture [name]\` or \`/smash\` to catch them!
• Collect, trade & build your harem

📋 *Use /help for full command list!*
    `.trim(),
    parse_mode: 'Markdown',
    reply_markup: { inline_keyboard: [[
      { text: '➕ Add me to Group', url: `https://t.me/${BOT_USERNAME}?startgroup=true` },
    ]]},
  }, botToken);
}

async function helpCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `
🤖 *Command Help*

⚔️ *Combat:*
• /smash — Combat a spawned character
• /capture [name] — Capture by name
• /exit — Exit active combat

💰 *Economy:*
• /bal — Check balance
• /pay [id] [amount] — Transfer gold
• /mine or /work — Earn gold
• /streak or /bonus — Daily reward
• /rob [id] — Rob a user

📦 *Collection:*
• /harem — View your collection
• /fav [name] — Set favorite character
• /marry [id] — Propose marriage

🖼️ *Uploader (staff only):*
• /upload — Upload a character
• /il [rarity] — Auto-scrape from reply
• /uchar — Update a character
• /findchar — Search characters
• /charinfo [id] — Show char details
• /replace — Replace character data

ℹ️ *Info:*
• /ping — Latency check
• /id — Your Telegram ID
• /stats — Bot statistics
    `.trim(),
    parse_mode: 'Markdown',
  }, botToken);
}

async function pingCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const start = Date.now();
  const sent = await tgApi('sendMessage', { chat_id: chatId, text: '🏓 Pong!' }, botToken);
  const ms = Date.now() - start;
  return tgApi('editMessageText', { chat_id: chatId, message_id: sent.result?.message_id, text: `🏓 Pong! \`${ms}ms\`` }, botToken);
}

async function idCmd(update, ctx) {
  const { botToken } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `👤 *Your Info:*\n• *Name:* ${firstName}\n• *ID:* \`${userId}\`\n• *Chat ID:* \`${chatId}\``,
    parse_mode: 'Markdown',
  }, botToken);
}

async function statsCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const charCount = await db.collection('anime_characters').countDocuments();
  const userCount = await db.collection('user_collection').countDocuments();
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `📊 *Bot Stats:*\n\n🎭 Characters: \`${charCount.toLocaleString()}\`\n👥 Users: \`${userCount.toLocaleString()}\`\n⚙️ Status: \`Online\``,
    parse_mode: 'Markdown',
  }, botToken);
}

module.exports = {
  commands: {
    start: startCmd,
    help: helpCmd,
    ping: pingCmd,
    id: idCmd, myid: idCmd,
    stats: statsCmd, botstats: statsCmd,
  },
};
