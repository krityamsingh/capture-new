import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { normalizeRarity, RARITY_PRICES } from '@/lib/shop-helpers'

const SECRET = process.env.NEXT_PUBLIC_ADREWARD_SECRET || 'change_this_secret_key_abc123'

export async function POST(request) {
  try {
    const { user_id, character_id, secret } = await request.json()

    // 1. Verify Secret Key
    if (secret !== SECRET) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Secret Key' }, { status: 403 })
    }

    const userId = parseInt(user_id, 10)
    if (isNaN(userId)) {
      return NextResponse.json({ ok: false, message: '❌ Invalid User ID' }, { status: 400 })
    }

    const client = await clientPromise
    if (!client) {
      return NextResponse.json({ ok: false, message: '❌ Database connection configuration missing' }, { status: 500 })
    }
    const db = client.db('Character_catcher')
    const userColl = db.collection('user_collection')
    const charColl = db.collection('anime_characters')

    const user = await userColl.findOne({ id: userId })
    if (!user) {
      return NextResponse.json({ ok: false, message: '❌ User not found' }, { status: 404 })
    }

    // Session validation: Strict token check
    const authToken = request.headers.get('x-auth-token')
    if (!authToken || !user.auth_token || user.auth_token !== authToken) {
      return NextResponse.json({ ok: false, message: '❌ Unauthorized Session' }, { status: 401 })
    }

    // 2. Fetch character details (check string and integer types)
    const char = await charColl.findOne({
      $or: [
        { id: character_id },
        { id: String(character_id) }
      ],
      deleted: { $ne: true }
    })

    if (!char) {
      return NextResponse.json({ ok: false, message: '🚫 Character not found' }, { status: 404 })
    }

    // 3. Rarity & Price Calculation
    const normRarity = normalizeRarity(char.rarity)
    const price = RARITY_PRICES[normRarity] || 500

    const userGold = user.gold || 0
    if (userGold < price) {
      return NextResponse.json({ ok: false, message: `❌ Need ${price.toLocaleString()} gold, you have ${userGold.toLocaleString()}` })
    }

    // 4. Update Database
    const newGold = userGold - price
    await userColl.updateOne(
      { id: userId },
      {
        $set: { gold: newGold },
        $push: { characters: char }
      }
    )

    return NextResponse.json({
      ok: true,
      message: `🎉 ${char.name} successfully added to your harem!`,
      character: {
        id: char.id,
        name: char.name,
        anime: char.anime,
        rarity: normRarity,
        img_url: char.img_url
      }
    })
  } catch (error) {
    console.error('API Buy Error:', error)
    return NextResponse.json({ ok: false, message: '❌ Internal Server Error' }, { status: 500 })
  }
}
