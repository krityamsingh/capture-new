/**
 * modules/bal.js — mirrors bal.py
 * Handles /bal, /balance, /pay, /transfer, /mine, /work, /streak, /bonus, /rob
 */
async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return await res.json();
}

if (!global.grabberEconomyState) global.grabberEconomyState = { workCooldowns: {} };
const eState = global.grabberEconomyState;

async function balCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const user = await collections.user_collection.findOne({ id: userId });
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `💰 *${firstName}'s Balance:*\n\n🪙 *Gold:* \`${(user?.gold || 0).toLocaleString()}\`\n💎 *Rubies:* \`${(user?.rubies || 0).toLocaleString()}\``,
    parse_mode: 'Markdown',
  }, botToken);
}

async function payCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  if (args.length < 2) return tgApi('sendMessage', { chat_id: chatId, text: '⚠️ *Usage:* `/pay [user_id] [amount]`', parse_mode: 'Markdown' }, botToken);
  const targetId = parseInt(args[0], 10);
  const amount   = parseInt(args[1], 10);
  if (isNaN(targetId) || isNaN(amount) || amount <= 0) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Invalid amount or user ID.*', parse_mode: 'Markdown' }, botToken);

  const user   = await collections.user_collection.findOne({ id: userId });
  const target = await collections.user_collection.findOne({ id: targetId });
  if (!target) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Target user not found.*', parse_mode: 'Markdown' }, botToken);
  if ((user?.gold || 0) < amount) return tgApi('sendMessage', { chat_id: chatId, text: `❌ *Insufficient funds!* You have ${user?.gold || 0} gold.`, parse_mode: 'Markdown' }, botToken);

  await collections.user_collection.updateOne({ id: userId },   { $inc: { gold: -amount } });
  await collections.user_collection.updateOne({ id: targetId }, { $inc: { gold: amount } });
  return tgApi('sendMessage', { chat_id: chatId, text: `💸 *Transfer complete!* Sent \`${amount.toLocaleString()}\` gold to *${target.first_name}*.`, parse_mode: 'Markdown' }, botToken);
}

async function mineCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const now = Date.now();
  const last = eState.workCooldowns[userId] || 0;
  const COOLDOWN = 5 * 60 * 1000;

  if (now - last < COOLDOWN) {
    const rem = Math.ceil((COOLDOWN - (now - last)) / 1000);
    return tgApi('sendMessage', { chat_id: chatId, text: `⏳ *Exhausted!* Rest for \`${rem}s\` before mining again.`, parse_mode: 'Markdown' }, botToken);
  }
  const pay = Math.floor(Math.random() * 45) + 15;
  eState.workCooldowns[userId] = now;
  await collections.user_collection.updateOne({ id: userId }, { $inc: { gold: pay } });
  return tgApi('sendMessage', { chat_id: chatId, text: `⛏️ *Shift Complete!* Earned +${pay} 💰 gold.`, parse_mode: 'Markdown' }, botToken);
}

async function streakCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const user = await collections.user_collection.findOne({ id: userId });
  const last = user?.last_bonus_claim ? new Date(user.last_bonus_claim).getTime() : 0;
  const oneDay = 24 * 60 * 60 * 1000;

  if (Date.now() - last < oneDay) {
    const hrs = Math.ceil((oneDay - (Date.now() - last)) / 3600000);
    return tgApi('sendMessage', { chat_id: chatId, text: `⏳ *Already claimed today!* Come back in \`${hrs} hours\`.`, parse_mode: 'Markdown' }, botToken);
  }
  const reward = 150;
  await collections.user_collection.updateOne({ id: userId }, { $inc: { gold: reward }, $set: { last_bonus_claim: new Date() } });
  return tgApi('sendMessage', { chat_id: chatId, text: `🎁 *Daily Reward!* +${reward} 💰 gold added.`, parse_mode: 'Markdown' }, botToken);
}

async function robCmd(update, ctx) {
  const { botToken, collections } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  if (!args.length) return tgApi('sendMessage', { chat_id: chatId, text: '⚠️ *Usage:* `/rob [user_id]`', parse_mode: 'Markdown' }, botToken);
  const victimId = parseInt(args[0], 10);
  if (isNaN(victimId) || victimId === userId) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Invalid user ID.*', parse_mode: 'Markdown' }, botToken);

  const victim = await collections.user_collection.findOne({ id: victimId });
  if (!victim || (victim.gold || 0) < 50) return tgApi('sendMessage', { chat_id: chatId, text: '❌ *Target has less than 50 gold — not worth robbing!*', parse_mode: 'Markdown' }, botToken);

  if (Math.random() < 0.4) {
    const stolen = Math.floor(Math.random() * 40) + 10;
    await collections.user_collection.updateOne({ id: userId },   { $inc: { gold: stolen } });
    await collections.user_collection.updateOne({ id: victimId }, { $inc: { gold: -stolen } });
    return tgApi('sendMessage', { chat_id: chatId, text: `🥷 *Robbery success!* Stole +${stolen} 💰 from *${victim.first_name}*!`, parse_mode: 'Markdown' }, botToken);
  }
  const fine = 25;
  await collections.user_collection.updateOne({ id: userId }, { $inc: { gold: -fine } });
  return tgApi('sendMessage', { chat_id: chatId, text: `🚨 *Busted!* Paid \`-${fine} gold\` fine.`, parse_mode: 'Markdown' }, botToken);
}

module.exports = {
  commands: {
    bal: balCmd, balance: balCmd,
    pay: payCmd, transfer: payCmd,
    mine: mineCmd, work: mineCmd,
    streak: streakCmd, bonus: streakCmd,
    rob: robCmd,
  },
};
