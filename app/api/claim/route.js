import { NextResponse } from 'next/server'
import { getDB } from '@/lib/Grabber/__init__'
import { normalizeRarity } from '@/lib/shop-helpers'

const SECRET = process.env.NEXT_PUBLIC_ADREWARD_SECRET || 'change_this_secret_key_abc123'

// Weighted rarity selector
function rollRarity() {
  const roll = Math.random() * 100
  if (roll < 45) return { display: '🔴 Common', query: 'Common' }
  if (roll < 70) return { display: '🔵 Uncommon', query: 'Uncommon' }
  if (roll < 85) return { display: '🟠 Rare', query: 'Rare' }
  if (roll < 93) return { display: '🟡 Legendary', query: 'Legendary' }
  if (roll < 97) return { display: '🫧 Premium', query: 'Premium' }
  if (roll < 99) return { display: '🔮 Limited Edition', query: 'Limited' }
  return { display: '⚜️ Animated', query: 'Animated' }
}

export async function POST(request) {
  try {
    const { user_id, secret } = await request.json()

    // 1. Verify Secret Key
    if (secret !== SECRET) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Secret Key' }, { status: 403 })
    }

    const userId = parseInt(user_id, 10)
    if (isNaN(userId)) {
      return NextResponse.json({ ok: false, message: '❌ Invalid User ID' }, { status: 400 })
    }

    const db = await getDB()
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

    // 2. Cooldown Validation (300 seconds)
    if (user.last_ad_watch) {
      const lastAdWatchTime = new Date(user.last_ad_watch).getTime()
      const diffSeconds = Math.floor((Date.now() - lastAdWatchTime) / 1000)
      if (diffSeconds < 300) {
        return NextResponse.json({
          ok: false,
          cooldown: 300 - diffSeconds,
          message: `⏳ Next ad reward available in ${Math.floor((300 - diffSeconds) / 60)}m ${String((300 - diffSeconds) % 60).padStart(2, '0')}s`
        })
      }
    }

    // 3. Roll Rarity & Fetch Character
    const rolled = rollRarity()
    let rawCharList = await charColl.aggregate([
      {
        $match: {
          rarity: { $regex: rolled.query, $options: 'i' },
          img_url: { $exists: true, $ne: "" },
          deleted: { $ne: true }
        }
      },
      { $sample: { size: 1 } }
    ]).toArray()

    let char = rawCharList[0]

    // Fallback: If no character matches rolled rarity, query any character
    if (!char) {
      rawCharList = await charColl.aggregate([
        { $match: { img_url: { $exists: true, $ne: "" }, deleted: { $ne: true } } },
        { $sample: { size: 1 } }
      ]).toArray()
      char = rawCharList[0]
    }

    if (!char) {
      return NextResponse.json({ ok: false, message: '🚫 No characters found in database' }, { status: 500 })
    }

    // 4. Update Database
    const goldEarned = Math.floor(Math.random() * 196) + 5 // +5 to +200 gold
    const newGold = (user.gold || 0) + goldEarned

    // Append full character object, including MongoDB _id, to match Python bot's exact layout
    await userColl.updateOne(
      { id: userId },
      {
        $set: {
          gold: newGold,
          last_ad_watch: new Date()
        },
        $push: {
          characters: char
        }
      }
    )

    return NextResponse.json({
      ok: true,
      character: {
        id: char.id,
        name: char.name,
        anime: char.anime,
        rarity: normalizeRarity(char.rarity),
        img_url: char.img_url
      },
      gold_earned: goldEarned
    })
  } catch (error) {
    console.error('API Claim Error:', error)
    return NextResponse.json({ ok: false, message: '❌ Internal Server Error' }, { status: 500 })
  }
}
