import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

const MAP_RARITY = {
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
  'mythic': '💮 Mythic'
}

function normalizeRarity(rarity) {
  if (!rarity) return '🔴 Common'
  const clean = rarity.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim()
  if (MAP_RARITY[clean]) return MAP_RARITY[clean]
  for (const key in MAP_RARITY) {
    if (clean.includes(key)) return MAP_RARITY[key]
  }
  return rarity
}

const RARITY_PRICES = {
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

export async function GET() {
  try {
    const client = await clientPromise
    if (!client) {
      return NextResponse.json({ error: 'Database connection configuration missing' }, { status: 500 })
    }
    const db = client.db('Character_catcher')
    const charColl = db.collection('anime_characters')

    // Sample 12 random characters with images
    const rawChars = await charColl.aggregate([
      { $match: { img_url: { $exists: true, $ne: "" }, deleted: { $ne: true } } },
      { $sample: { size: 12 } }
    ]).toArray()

    const formattedChars = rawChars.map(c => {
      const normRarity = normalizeRarity(c.rarity)
      const price = RARITY_PRICES[normRarity] || 500
      return {
        id: c.id,
        name: c.name,
        anime: c.anime,
        rarity: normRarity,
        price: price,
        img_url: c.img_url
      }
    })

    return NextResponse.json({ characters: formattedChars })
  } catch (error) {
    console.error('API Shop Error:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
export { normalizeRarity, RARITY_PRICES }
