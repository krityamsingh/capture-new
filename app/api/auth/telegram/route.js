import { NextResponse } from 'next/server'
import crypto from 'crypto'
import clientPromise from '@/lib/mongodb'

const BOT_TOKEN = process.env.BOT_TOKEN || '8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk'

function verifyTelegramWebAppData(initData, botToken) {
  try {
    const params = new URLSearchParams(initData)
    const hash = params.get('hash')
    if (!hash) return false

    params.delete('hash')

    const dataCheckArr = []
    for (const [key, value] of params.entries()) {
      dataCheckArr.push(`${key}=${value}`)
    }
    dataCheckArr.sort()
    const dataCheckString = dataCheckArr.join('\n')

    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest()
    const calculatedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex')

    return calculatedHash === hash
  } catch (err) {
    console.error('Crypto verification error:', err)
    return false
  }
}

export async function POST(request) {
  try {
    const { initData } = await request.json()

    if (!initData) {
      return NextResponse.json({ ok: false, message: '❌ initData required' }, { status: 400 })
    }

    // 1. Verify Hash
    const isValid = verifyTelegramWebAppData(initData, BOT_TOKEN)
    if (!isValid) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Telegram signature' }, { status: 403 })
    }

    // 2. Extract User ID & Details
    const params = new URLSearchParams(initData)
    const userStr = params.get('user')
    if (!userStr) {
      return NextResponse.json({ ok: false, message: '❌ User metadata missing' }, { status: 400 })
    }

    const tgUser = JSON.parse(userStr)
    const userId = parseInt(tgUser.id, 10)

    if (isNaN(userId)) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Telegram User ID' }, { status: 400 })
    }

    const client = await clientPromise
    if (!client) {
      return NextResponse.json({ ok: false, message: '❌ Database connection not available' }, { status: 500 })
    }

    const db = client.db('Character_catcher')
    const userColl = db.collection('user_collection')

    let user = await userColl.findOne({ id: userId })

    // Auto-upsert new users so they can play instantly
    if (!user) {
      user = {
        id: userId,
        first_name: tgUser.first_name || 'Telegram User',
        username: tgUser.username || null,
        gold: 100,
        rubies: 0,
        characters: [],
        favorites: [],
        last_ad_watch: null
      }
      await userColl.insertOne(user)
    }

    // Generate secure session token
    const sessionToken = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)

    // Save token in DB
    await userColl.updateOne(
      { id: userId },
      { $set: { auth_token: sessionToken } }
    )

    return NextResponse.json({
      ok: true,
      auth_token: sessionToken,
      userId: userId
    })
  } catch (error) {
    console.error('API Telegram Auth Error:', error)
    return NextResponse.json({ ok: false, message: '❌ Internal Server Error' }, { status: 500 })
  }
}
