/**
 * lib/shop-helpers.js
 * Shared rarity constants used by both /api/shop and /api/buy routes.
 * Extracted here so route files don't cross-import each other (which breaks Next.js build).
 */

export const MAP_RARITY = {
  'common': '🔴 Common',
  'uncommon': '🔵 Uncommon',
  'rare': '🟠 Rare',
  'legendary': '🟡 Legendary',
  'premium': '🫧 Premium',
  'limited': '🔮 Limited Edition',
  'limited edition': '🔮 Limited Edition',
  'exotic': '🏵️ Exotic',
  'animated': '⚜️ Animated',
  'celebrity': '🌼 Celebrity',
  'crystal': '🎐 Crystal',
  'neon': '🍹 Neon',
  'supreme': '🧿 Supreme',
  'thundra': '⚡ Thundra',
  'galvoria': '🛸 Galvoria',
  'epic': '⚪ Epic',
  'godly': '🔱 Godly',
  'unique': '⚜️ Unique',
  'mythic': '💮 Mythic',
}

export const RARITY_PRICES = {
  '🔴 Common':          100,
  '🔵 Uncommon':        250,
  '🟠 Rare':            500,
  '🟡 Legendary':       1000,
  '🫧 Premium':         2000,
  '🔮 Limited Edition': 3500,
  '🏵️ Exotic':          5000,
  '⚜️ Animated':        7500,
  '🌼 Celebrity':       10000,
  '🎐 Crystal':         12500,
  '🍹 Neon':            15000,
  '🧿 Supreme':         20000,
  '⚡ Thundra':         25000,
  '🛸 Galvoria':        30000,
}

export function normalizeRarity(rarity) {
  if (!rarity) return '🔴 Common'
  const clean = rarity.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim()
  if (MAP_RARITY[clean]) return MAP_RARITY[clean]
  for (const key in MAP_RARITY) {
    if (clean.includes(key)) return MAP_RARITY[key]
  }
  return rarity
}
