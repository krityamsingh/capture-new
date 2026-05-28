const OWNER_IDS = [6228788487, 8496760733, 7878477646, 7976292835, 6118760915];
const UPLOAD_CHANNEL_ID = -1002672414862;
const UPLOAD_GC_ID = -1002313549356;
const CATBOX_USERHASH = "de47eb51da1e8bc98c5ca9cf3";

const RARITY_MAP = {
  1:  "🔴 Common",
  2:  "🔵 Uncommon",
  3:  "🟠 Rare",
  4:  "🟡 Legendary",
  5:  "⚪ Epic",
  6:  "🔮 Limited Edition",
  7:  "🫧 Premium",
  8:  "🏵️ Exotic",
  9:  "⚜️ Animated",
  10: "🌼 Celebrity",
  11: "🎐 Crystal",
  12: "🍹 Neon",
  13: "🧿 Supreme",
  14: "⚡ Thundra",
  15: "🛸 Galvoria",
  16: "🌟 Solar Verse",
};

const ANIMATED_RARITY = "⚜️ Animated";

function looksLikeAnime(t) {
  if (!t) return false;
  const tl = t.toLowerCase().trim();
  const POPULAR_ANIME = [
    "naruto", "one piece", "bleach", "dragon ball", "my hero academia",
    "attack on titan", "demon slayer", "jujutsu kaisen", "one punch man",
    "tokyo ghoul", "sword art online", "fate", "code geass", "steins gate",
    "mob psycho", "vinland saga", "chainsaw man", "spy x family", "wind breaker",
    "black clover", "fairy tail", "hunter x hunter", "fullmetal alchemist",
    "re zero", "overlord", "konosuba", "danmachi", "fire force", "blue lock",
    "haikyuu", "kuroko no basket", "death note", "evangelion", "cowboy bebop",
    "trigun", "inuyasha", "soul eater", "noragami", "the promised neverland",
    "your lie in april", "anohana", "clannad", "toradora",
    "rising of the shield hero", "that time i got reincarnated", "tensura",
    "black butler", "ouran", "fruits basket", "vampire knight"
  ];
  if (POPULAR_ANIME.some(a => tl.includes(a))) {
    return true;
  }
  const ANIME_KEYWORDS = new Set([
    "saga", "season", "arc", "legend", "chronicle", "story", "tale",
    "adventure", "quest", "journey", "war", "battle", "part", "zero",
    "online", "force", "hero", "king", "world", "no", "academy",
    "shippuden", "kai", "super", "ultimate", "returns", "reborn"
  ]);
  const words = tl.match(/\w+/g) || [];
  return words.some(w => ANIME_KEYWORDS.has(w));
}

function clean(s) {
  if (!s) return "";
  s = s.replace(/\*+/g, "");
  s = s.replace(/[^\w\s'-]/g, " ");
  return s.split(/\s+/).filter(Boolean).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
}

function stripNoise(s) {
  if (!s) return "";
  const parts = s.split(/RARITY|rarity|🔴|🔵|🟠|🟡|⚪|🔮|🫧|🏵️|⚜️|🌼|🎐|🍹|🧿|⚡|🛸|🌟/i);
  let cleaned = parts[0] || "";
  cleaned = cleaned.replace(/^\d+\s*[:.]\s*/, "");
  return cleaned.trim();
}

function extractIL(text) {
  if (!text) return { charName: null, anime: null };
  text = text.trim();
  
  const matchers = [
    {
      regex: /(?:OwO[^\n]*\n+)?([^\n]+)\n\d+\s*:\s*([^\n]+)/i,
      map: (m) => ({ anime: m[1], n: m[2] })
    },
    {
      regex: /name\s*[:=]\s*([^\n]+)\n[\s\S]*?anime\s*[:=]\s*([^\n]+)/i,
      map: (m) => ({ n: m[1], anime: m[2] })
    },
    {
      regex: /anime\s*[:=]\s*([^\n]+)\n[\s\S]*?name\s*[:=]\s*([^\n]+)/i,
      map: (m) => ({ anime: m[1], n: m[2] })
    },
    {
      regex: /char(?:acter)?\s*[:=]\s*([^\n]+)\n[\s\S]*?(?:series|show|source)\s*[:=]\s*([^\n]+)/i,
      map: (m) => ({ n: m[1], anime: m[2] })
    },
    {
      regex: /^([^|\n]{2,40})\s*\|\s*([^|\n]{2,60})$/m,
      map: (m) => ({ a: m[1], b: m[2] })
    },
    {
      regex: /from\s*[:=]\s*([^\n]+)\n[\s\S]*?char(?:acter)?\s*[:=]\s*([^\n]+)/i,
      map: (m) => ({ anime: m[1], n: m[2] })
    },
    {
      regex: /(?:title\s*:\s*)?([^\n(]{2,40})\s*\(([^)]{2,60})\)/i,
      map: (m) => ({ n: m[1], anime: m[2] })
    },
    {
      regex: /\*\*([^*\n]{2,40})\*\*\s*\n\s*\*\*([^*\n]{2,60})\*\*/,
      map: (m) => ({ n: m[1], anime: m[2] })
    },
    {
      regex: /^([^\n—–]{2,40})\s*[—–]\s*([^\n]{2,60})$/m,
      map: (m) => ({ n: m[1], anime: m[2] })
    },
    {
      regex: /^([^\n]{2,40})\n([^\n]{2,60})$/m,
      map: (m) => ({ n: m[1], anime: m[2] })
    }
  ];

  for (const matcher of matchers) {
    const m = text.match(matcher.regex);
    if (!m) continue;
    
    const gd = matcher.map(m);
    
    if (gd.a !== undefined && gd.b !== undefined) {
      const a = stripNoise(gd.a);
      const b = stripNoise(gd.b);
      if (!a || !b) continue;
      if (looksLikeAnime(a)) {
        return { charName: clean(b), anime: clean(a) };
      }
      return { charName: clean(a), anime: clean(b) };
    }
    
    let rawName = stripNoise(gd.n || "");
    let rawAnime = stripNoise(gd.anime || "");
    rawName = rawName.split("\n")[0].trim();
    rawAnime = rawAnime.split("\n")[0].trim();
    
    if (rawName && rawAnime && rawName.length > 1 && rawAnime.length > 1) {
      return { charName: clean(rawName), anime: clean(rawAnime) };
    }
  }

  // Fallback
  const lines = text.split("\n")
    .map(ln => stripNoise(ln.trim()))
    .filter(ln => ln.length > 2 && !ln.startsWith("/"));
  
  if (lines.length >= 2) {
    const a = lines[0];
    const b = lines[1];
    if (looksLikeAnime(a)) {
      return { charName: clean(b), anime: clean(a) };
    }
    return { charName: clean(a), anime: clean(b) };
  }

  return { charName: null, anime: null };
}

function parseUploadArgs(raw) {
  raw = raw.trim();
  if (raw.includes("|")) {
    const parts = raw.split("|").map(p => p.trim());
    if (parts.length === 3) {
      return { anime: parts[0], charName: parts[1], rarityNo: parts[2] };
    }
  }
  if (raw.includes(" - ")) {
    const parts = raw.split(" - ").map(p => p.trim());
    if (parts.length === 3) {
      return { anime: parts[0], charName: parts[1], rarityNo: parts[2] };
    }
  }
  return null;
}

async function downloadTelegramMedia(fileId, botToken) {
  const getFileRes = await fetch(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`);
  const getFileData = await getFileRes.json();
  if (!getFileData.ok || !getFileData.result || !getFileData.result.file_path) {
    throw new Error(getFileData.description || "Failed to get file path from Telegram");
  }
  const filePath = getFileData.result.file_path;
  
  const dlRes = await fetch(`https://api.telegram.org/file/bot${botToken}/${filePath}`);
  if (!dlRes.ok) {
    throw new Error(`Failed to download file: status ${dlRes.status}`);
  }
  
  const arrayBuffer = await dlRes.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

async function uploadToCatbox(fileBuffer, fileName) {
  const formData = new FormData();
  formData.append("reqtype", "fileupload");
  formData.append("userhash", CATBOX_USERHASH);
  
  const blob = new Blob([fileBuffer]);
  formData.append("fileToUpload", blob, fileName);
  
  const res = await fetch("https://catbox.moe/user/api.php", {
    method: "POST",
    body: formData
  });
  
  if (!res.ok) {
    throw new Error(`Catbox HTTP error: ${res.status}`);
  }
  
  const text = await res.text();
  const url = text.trim();
  if (!url.startsWith("https://")) {
    throw new Error(`Invalid Catbox response: ${url.slice(0, 100)}`);
  }
  return url;
}

async function getNextId(db) {
  const collectionRef = db.collection('anime_characters');
  const sequencesDb = db.collection('sequences');
  
  const docs = await collectionRef.find({ id: { $exists: true } }, { projection: { id: 1 } }).toArray();
  const existing = docs
    .map(c => parseInt(c.id, 10))
    .filter(id => !isNaN(id));
  const dbMax = existing.length > 0 ? Math.max(...existing) : 0;
  
  const seq = await sequencesDb.findOne({ _id: "character_id" });
  const seqVal = seq ? seq.sequence_value : 0;
  
  const nxt = Math.max(dbMax, seqVal) + 1;
  await sequencesDb.updateOne(
    { _id: "character_id" },
    { $set: { sequence_value: nxt } },
    { upsert: true }
  );
  
  return String(nxt).padStart(2, '0');
}

function buildChannelCaption(name, anime, rarity, price, charId, mention) {
  return (
    `✨ **New Character Added!**\n\n` +
    `🎭 **Name**   ${name}\n` +
    `📺 **Anime**  ${anime}\n` +
    `⭐ **Rarity** ${rarity}\n` +
    `💰 **Price**  ${price.toLocaleString()} coins\n` +
    `🆔 **ID**     \`${charId}\`\n` +
    `👤 **By**     ${mention}`
  );
}

module.exports = {
  OWNER_IDS,
  UPLOAD_CHANNEL_ID,
  UPLOAD_GC_ID,
  CATBOX_USERHASH,
  RARITY_MAP,
  ANIMATED_RARITY,
  looksLikeAnime,
  clean,
  stripNoise,
  extractIL,
  parseUploadArgs,
  downloadTelegramMedia,
  uploadToCatbox,
  getNextId,
  buildChannelCaption
};
