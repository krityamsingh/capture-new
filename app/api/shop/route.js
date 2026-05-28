import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { normalizeRarity, RARITY_PRICES } from '@/lib/shop-helpers'



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
