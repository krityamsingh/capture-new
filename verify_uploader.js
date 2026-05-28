const {
  looksLikeAnime,
  clean,
  extractIL,
  parseUploadArgs,
  uploadToCatbox
} = require('./lib/bot-modules/uploader');

// 1. Test looksLikeAnime
console.log("=== Testing looksLikeAnime ===");
const testAnime = ["Naruto Shippuden", "One Piece Red", "Vinland Saga Season 2", "Not Anime String", "Mob Psycho"];
testAnime.forEach(item => {
  console.log(`- '${item}': ${looksLikeAnime(item) ? '✅ YES' : '❌ NO'}`);
});

// 2. Test clean
console.log("\n=== Testing clean ===");
const dirtyNames = ["**Kakashi Hatake**", "Saitama - Hero", "Fubuki (OPM)"];
dirtyNames.forEach(item => {
  console.log(`- '${item}' -> '${clean(item)}'`);
});

// 3. Test parseUploadArgs
console.log("\n=== Testing parseUploadArgs ===");
const testArgs = [
  "One Punch Man | Saitama | 4",
  "Naruto - Kakashi - 3",
  "Invalid format string here"
];
testArgs.forEach(args => {
  const res = parseUploadArgs(args);
  console.log(`- '${args}':`, res ? `✅ Parsed (Anime: ${res.anime}, Char: ${res.charName}, Rarity: ${res.rarityNo})` : '❌ Failed');
});

// 4. Test extractIL (10 Regex Patterns)
console.log("\n=== Testing extractIL (Auto-Scraper Regexes) ===");
const testSpawns = [
  // Pattern 1: OwO style
  "OwO Look at this!\nNaruto\n123: Kakashi Hatake",
  // Pattern 2: Name/Anime keys
  "Name: Monkey D. Luffy\nAnime: One Piece",
  // Pattern 3: Anime/Name keys
  "Anime: Demon Slayer\nName: Nezuko Kamado",
  // Pattern 7: Parenthesis style
  "Fubuki (One Punch Man)",
  // Pattern 9: Dash style
  "Goku — Dragon Ball Super"
];

testSpawns.forEach((spawn, idx) => {
  const { charName, anime } = extractIL(spawn);
  console.log(`Pattern Test ${idx + 1}:`);
  console.log(`  Source:\n${spawn.replace(/^/gm, '    ')}`);
  console.log(`  Result: Name: '${charName}', Anime: '${anime}' -> ${charName && anime ? '✅ SUCCESS' : '❌ FAILED'}\n`);
});

// 5. Test Catbox Upload
async function testCatbox() {
  console.log("=== Testing Catbox API Upload ===");
  const dummyBuffer = Buffer.from("Hello from Captrue Upgraded automated verification script!");
  try {
    const url = await uploadToCatbox(dummyBuffer, "test_verify.txt");
    console.log(`✅ Catbox Upload SUCCESS: ${url}`);
  } catch (err) {
    console.error(`❌ Catbox Upload FAILED: ${err.message}`);
  }
}

testCatbox();
