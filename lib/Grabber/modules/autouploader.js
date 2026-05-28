/**
 * modules/autouploader.js — mirrors autouploader.py + upload.py
 * /upload, /il, /uchar, /findchar, /charinfo, /replace
 * /adduploader, /rmuploader, /uploaderlist
 */
const {
  OWNER_IDS, UPLOAD_CHANNEL_ID, UPLOAD_GC_ID,
  RARITY_MAP, ANIMATED_RARITY,
  extractIL, parseUploadArgs,
  downloadTelegramMedia, uploadToCatbox,
  getNextId, buildChannelCaption, clean,
} = require('../../bot-modules/uploader');

async function tgApi(method, body, token) {
  const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return await res.json();
}

async function isUploader(userId, db) {
  if (OWNER_IDS.includes(userId)) return true;
  const u = await db.collection('uploader').findOne({ user_id: userId });
  return !!u;
}

async function editChannelPost(db, botToken, charId) {
  const char = await db.collection('anime_characters').findOne({ id: charId });
  if (!char || !char.message_id) return 'No message_id stored';
  const caption = buildChannelCaption(char.name, char.anime, char.rarity, char.price || 0, char.id, char.mention || 'unknown');
  let err = null;
  for (const chatId of [UPLOAD_CHANNEL_ID, UPLOAD_GC_ID]) {
    const r = await tgApi('editMessageCaption', { chat_id: chatId, message_id: char.message_id, caption, parse_mode: 'Markdown' }, botToken);
    if (!r.ok) err = r.description;
  }
  return err;
}

function getMediaInfo(msg) {
  if (msg.photo?.length)   return { fileId: msg.photo[msg.photo.length - 1].file_id, isVideo: false, fileName: 'character.jpg' };
  if (msg.video)           return { fileId: msg.video.file_id, isVideo: true, fileName: 'character.mp4' };
  if (msg.document) {
    const m = msg.document.mime_type || '';
    return { fileId: msg.document.file_id, isVideo: m.startsWith('video/'), fileName: m.startsWith('video/') ? 'character.mp4' : 'character.jpg' };
  }
  return null;
}

async function doUpload(db, botToken, chatId, userId, firstName, fileInfo, charName, anime, rarity) {
  const { fileId, isVideo, fileName } = fileInfo;
  const buf    = await downloadTelegramMedia(fileId, botToken);
  const imgUrl = await uploadToCatbox(buf, fileName);
  const charId = await getNextId(db);
  const price  = Math.floor(Math.random() * 20001) + 60000;
  const mention = `[${firstName}](tg://user?id=${userId})`;
  const doc = { id: charId, name: charName, anime, rarity, price, img_url: imgUrl, mention };
  const caption = buildChannelCaption(charName, anime, rarity, price, charId, mention);

  const method = isVideo ? 'sendVideo' : 'sendPhoto';
  const key    = isVideo ? 'video'     : 'photo';
  const sent   = await tgApi(method, { chat_id: UPLOAD_CHANNEL_ID, [key]: imgUrl, caption, parse_mode: 'Markdown' }, botToken);
  if (sent.result?.message_id) doc.message_id = sent.result.message_id;
  try { await tgApi(method, { chat_id: UPLOAD_GC_ID, [key]: imgUrl, caption, parse_mode: 'Markdown' }, botToken); } catch {}
  await db.collection('anime_characters').insertOne(doc);
  return { charId, price, imgUrl };
}

// ── /upload ──────────────────────────────────────────────────────────────────
async function uploadCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;

  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);

  const reply = message.reply_to_message;
  const mediaMsg = reply || message;
  const fi = getMediaInfo(mediaMsg);
  if (!fi) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Reply to a photo or video.\n\n`/upload <anime> | <char> | <rarity_no>`', parse_mode: 'Markdown' }, botToken);

  const raw = ((message.text || '') + ' ' + (message.caption || '')).trim();
  const afterCmd = raw.replace(/^\/upload\S*/, '').trim();
  const parsed = parseUploadArgs(afterCmd);
  if (!parsed) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Format: `/upload <anime> | <char> | <rarity_no>`', parse_mode: 'Markdown' }, botToken);

  const { anime, charName, rarityNo } = parsed;
  const rNum = parseInt(rarityNo, 10);
  if (!RARITY_MAP[rNum]) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Rarity must be 1–16.', parse_mode: 'Markdown' }, botToken);
  const rarity = fi.isVideo ? ANIMATED_RARITY : RARITY_MAP[rNum];

  const st = await tgApi('sendMessage', { chat_id: chatId, text: `⏳ Uploading \`${charName}\`…` }, botToken);
  try {
    const { charId, price, imgUrl } = await doUpload(db, botToken, chatId, userId, firstName, fi, charName, anime, rarity);
    await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id,
      text: `✅ *Character Saved!*\n\n🆔 \`${charId}\`\n🎭 *${charName}*\n📺 *${anime}*\n⭐ *${rarity}*\n💰 \`${price.toLocaleString()} coins\`\n🖼️ [View](${imgUrl})`,
      parse_mode: 'Markdown' }, botToken);
  } catch (e) {
    await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id, text: `❌ Upload failed: \`${e.message}\`` }, botToken);
  }
}

// ── /il ──────────────────────────────────────────────────────────────────────
async function ilCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);

  const reply = message.reply_to_message;
  if (!reply) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Reply to a spawn message with `/il <rarity_no>`', parse_mode: 'Markdown' }, botToken);

  const rNum = parseInt(args[0], 10);
  if (!RARITY_MAP[rNum]) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Rarity must be 1–16.', parse_mode: 'Markdown' }, botToken);

  const fi = getMediaInfo(reply);
  if (!fi) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Replied message has no photo or video!' }, botToken);

  const caption = (reply.caption || reply.text || '').trim();
  const { charName, anime } = extractIL(caption);
  if (!charName || !anime) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Could not detect name & anime. Use `/upload` manually.', parse_mode: 'Markdown' }, botToken);

  const rarity = fi.isVideo ? ANIMATED_RARITY : RARITY_MAP[rNum];
  const st = await tgApi('sendMessage', { chat_id: chatId, text: `⏳ Auto-uploading \`${charName}\` from \`${anime}\`…` }, botToken);
  try {
    const { charId, price, imgUrl } = await doUpload(db, botToken, chatId, userId, firstName, fi, charName, anime, rarity);
    await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id,
      text: `✅ *Auto-Scraped & Saved!*\n\n🆔 \`${charId}\`\n🎭 *${charName}*\n📺 *${anime}*\n⭐ *${rarity}*\n💰 \`${price.toLocaleString()} coins\`\n🖼️ [View](${imgUrl})`,
      parse_mode: 'Markdown' }, botToken);
  } catch (e) {
    await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id, text: `❌ Auto-upload failed: \`${e.message}\`` }, botToken);
  }
}

// ── /uchar ───────────────────────────────────────────────────────────────────
async function ucharCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);

  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);
  if (args.length < 2) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Usage:\n`/uchar media <id>`\n`/uchar rarity <id> <no>`\n`/uchar name <id> <new name>`\n`/uchar anime <id> <new anime>`', parse_mode: 'Markdown' }, botToken);

  const sub    = args[0].toLowerCase();
  const charId = args[1].padStart(2, '0');
  const charColl = db.collection('anime_characters');
  const char   = await charColl.findOne({ id: charId });
  if (!char) return tgApi('sendMessage', { chat_id: chatId, text: `❌ Character \`${charId}\` not found.` }, botToken);

  if (sub === 'media') {
    const fi = getMediaInfo(message.reply_to_message || {});
    if (!fi) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Reply to a photo or video with `/uchar media <id>`', parse_mode: 'Markdown' }, botToken);
    const st = await tgApi('sendMessage', { chat_id: chatId, text: `⏳ Updating media for \`${charId}\`…` }, botToken);
    try {
      const buf = await downloadTelegramMedia(fi.fileId, botToken);
      const newUrl = await uploadToCatbox(buf, fi.fileName);
      const newRarity = fi.isVideo ? ANIMATED_RARITY : char.rarity;
      await charColl.updateOne({ id: charId }, { $set: { img_url: newUrl, ...(fi.isVideo ? { rarity: newRarity } : {}) } });
      await editChannelPost(db, botToken, charId);
      await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id,
        text: `✅ *Media Updated!*\n🆔 \`${charId}\`\n🎭 *${char.name}*\n⭐ *${newRarity}*\n🖼️ [View](${newUrl})\n📡 Channel updated.`,
        parse_mode: 'Markdown' }, botToken);
    } catch (e) {
      await tgApi('editMessageText', { chat_id: chatId, message_id: st.result?.message_id, text: `❌ Failed: \`${e.message}\`` }, botToken);
    }
  } else if (sub === 'rarity') {
    const newR = RARITY_MAP[parseInt(args[2], 10)];
    if (!newR) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Invalid rarity number.' }, botToken);
    await charColl.updateOne({ id: charId }, { $set: { rarity: newR } });
    await editChannelPost(db, botToken, charId);
    return tgApi('sendMessage', { chat_id: chatId, text: `✅ Rarity: \`${char.rarity}\` → \`${newR}\`\n📡 Channel updated.`, parse_mode: 'Markdown' }, botToken);
  } else if (sub === 'name') {
    const newName = args.slice(2).join(' ').trim();
    if (!newName) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Provide a new name.' }, botToken);
    await charColl.updateOne({ id: charId }, { $set: { name: clean(newName) } });
    await editChannelPost(db, botToken, charId);
    return tgApi('sendMessage', { chat_id: chatId, text: `✅ Name: \`${char.name}\` → \`${clean(newName)}\`\n📡 Channel updated.`, parse_mode: 'Markdown' }, botToken);
  } else if (sub === 'anime') {
    const newAnime = args.slice(2).join(' ').trim();
    if (!newAnime) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Provide a new anime.' }, botToken);
    await charColl.updateOne({ id: charId }, { $set: { anime: clean(newAnime) } });
    await editChannelPost(db, botToken, charId);
    return tgApi('sendMessage', { chat_id: chatId, text: `✅ Anime: \`${char.anime}\` → \`${clean(newAnime)}\`\n📡 Channel updated.`, parse_mode: 'Markdown' }, botToken);
  }
}

// ── /findchar, /charinfo, /replace ───────────────────────────────────────────
async function findcharCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);
  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);
  if (!args.length) return tgApi('sendMessage', { chat_id: chatId, text: '❌ `/findchar <query>`', parse_mode: 'Markdown' }, botToken);
  const q = args.join(' ');
  const chars = await db.collection('anime_characters').find({ $or: [{ name: { $regex: q, $options: 'i' } }, { anime: { $regex: q, $options: 'i' } }] }).limit(20).toArray();
  if (!chars.length) return tgApi('sendMessage', { chat_id: chatId, text: `❌ No results for \`${q}\`.`, parse_mode: 'Markdown' }, botToken);
  const lines = chars.map(c => `🆔 \`${c.id}\` | *${c.name}* | _${c.anime}_`);
  return tgApi('sendMessage', { chat_id: chatId, text: `🔍 *Results (${chars.length}):*\n\n${lines.join('\n')}`, parse_mode: 'Markdown' }, botToken);
}

async function charinfoCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);
  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);
  if (!args.length) return tgApi('sendMessage', { chat_id: chatId, text: '❌ `/charinfo <id>`', parse_mode: 'Markdown' }, botToken);
  const charId = args[0].padStart(2, '0');
  const char = await db.collection('anime_characters').findOne({ id: charId });
  if (!char) return tgApi('sendMessage', { chat_id: chatId, text: `❌ ID \`${charId}\` not found.`, parse_mode: 'Markdown' }, botToken);
  let imgStatus = '—';
  try { const r = await fetch(char.img_url, { method: 'HEAD' }); imgStatus = r.ok ? '✅ OK' : `❌ HTTP ${r.status}`; } catch (e) { imgStatus = `❌ ${e.message}`; }
  return tgApi('sendMessage', {
    chat_id: chatId,
    text: `📋 *Character Info*\n\n🆔 \`${char.id}\`\n🎭 *${char.name}*\n📺 *${char.anime}*\n⭐ *${char.rarity}*\n💰 \`${(char.price||0).toLocaleString()} coins\`\n🖼️ Image: ${imgStatus}\n🔗 [View File](${char.img_url})`,
    parse_mode: 'Markdown',
  }, botToken);
}

async function replaceCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId, first_name: firstName } = message.from;
  const args = (message.text || '').trim().split(/\s+/).slice(1);
  if (!await isUploader(userId, db)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Uploader access required.' }, botToken);
  const parts = args.join(' ').split('-');
  if (parts.length < 5) return tgApi('sendMessage', { chat_id: chatId, text: '❌ `/replace <id>-<url>-<anime>-<name>-<rarity>`', parse_mode: 'Markdown' }, botToken);
  const [id, url, anime, name, ...rarityParts] = parts;
  const charId = id.trim().padStart(2, '0');
  const char = await db.collection('anime_characters').findOne({ id: charId });
  if (!char) return tgApi('sendMessage', { chat_id: chatId, text: `❌ ID \`${charId}\` not found.` }, botToken);
  await db.collection('anime_characters').updateOne({ id: charId }, { $set: { img_url: url.trim(), anime: clean(anime.trim()), name: clean(name.trim()), rarity: rarityParts.join('-').trim() } });
  await editChannelPost(db, botToken, charId);
  return tgApi('sendMessage', { chat_id: chatId, text: `🔄 *Replaced!* \`${charId}\`\n📡 Channel updated.\n✅ By [${firstName}](tg://user?id=${userId})`, parse_mode: 'Markdown' }, botToken);
}

// ── Uploader management ───────────────────────────────────────────────────────
async function addUploaderCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  if (!OWNER_IDS.includes(userId)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Owner only.' }, botToken);
  const args = (message.text || '').trim().split(/\s+/).slice(1);
  const target = message.reply_to_message?.from || (args[0] ? { id: parseInt(args[0], 10), first_name: `User ${args[0]}` } : null);
  if (!target) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Reply to user or `/adduploader <id>`', parse_mode: 'Markdown' }, botToken);
  const exists = await db.collection('uploader').findOne({ user_id: target.id });
  if (exists) return tgApi('sendMessage', { chat_id: chatId, text: `⚠️ *${target.first_name}* already an uploader.`, parse_mode: 'Markdown' }, botToken);
  await db.collection('uploader').insertOne({ user_id: target.id, added_at: new Date() });
  return tgApi('sendMessage', { chat_id: chatId, text: `✅ *${target.first_name}* (\`${target.id}\`) added as uploader!`, parse_mode: 'Markdown' }, botToken);
}

async function rmUploaderCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  if (!OWNER_IDS.includes(userId)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Owner only.' }, botToken);
  const args = (message.text || '').trim().split(/\s+/).slice(1);
  const target = message.reply_to_message?.from || (args[0] ? { id: parseInt(args[0], 10), first_name: `User ${args[0]}` } : null);
  if (!target) return tgApi('sendMessage', { chat_id: chatId, text: '❌ Reply to user or `/rmuploader <id>`', parse_mode: 'Markdown' }, botToken);
  await db.collection('uploader').deleteOne({ user_id: target.id });
  return tgApi('sendMessage', { chat_id: chatId, text: `🗑️ *${target.first_name}* removed from uploaders.`, parse_mode: 'Markdown' }, botToken);
}

async function uploaderListCmd(update, ctx) {
  const { botToken, db } = ctx;
  const { message } = update;
  const { id: chatId } = message.chat;
  const { id: userId } = message.from;
  if (!OWNER_IDS.includes(userId)) return tgApi('sendMessage', { chat_id: chatId, text: '🚫 Owner only.' }, botToken);
  const docs = await db.collection('uploader').find().toArray();
  if (!docs.length) return tgApi('sendMessage', { chat_id: chatId, text: '📭 No uploaders yet.', parse_mode: 'Markdown' }, botToken);
  const lines = docs.map((d, i) => `${i + 1}. \`${d.user_id}\``);
  return tgApi('sendMessage', { chat_id: chatId, text: `👥 *Uploaders (${docs.length}):*\n\n${lines.join('\n')}`, parse_mode: 'Markdown' }, botToken);
}

module.exports = {
  commands: {
    upload: uploadCmd,
    il: ilCmd,
    uchar: ucharCmd, updatechar: ucharCmd,
    findchar: findcharCmd,
    charinfo: charinfoCmd,
    replace: replaceCmd,
    adduploader: addUploaderCmd,
    rmuploader: rmUploaderCmd,
    uploaderlist: uploaderListCmd,
  },
};
