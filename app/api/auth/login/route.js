import { NextResponse } from 'next/server'
import { getDB } from '@/lib/Grabber/__init__'

export async function POST(request) {
  try {
    const { user_id, code } = await request.json()

    const userId = parseInt(user_id, 10)
    const codeStr = String(code).trim()

    if (isNaN(userId)) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Telegram User ID' }, { status: 400 })
    }

    if (!codeStr) {
      return NextResponse.json({ ok: false, message: '❌ Verification code required' }, { status: 400 })
    }

    const db = await getDB()
    const userColl = db.collection('user_collection')

    const user = await userColl.findOne({ id: userId })
    if (!user) {
      return NextResponse.json({ ok: false, message: '❌ Account not found. Please launch the bot in Telegram first!' })
    }

    const loginCodeData = user.web_login_code
    if (!loginCodeData || !loginCodeData.code) {
      return NextResponse.json({ ok: false, message: '❌ No active verification code. Please send /login to your bot in Telegram first.' })
    }

    const codeMatches = String(loginCodeData.code).trim() === codeStr
    const isNotExpired = new Date() < new Date(loginCodeData.expires_at)

    if (codeMatches && isNotExpired) {
      // Generate a secure high-entropy session token
      const sessionToken = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)

      // Set session auth token in DB and clear the used OTP code
      await userColl.updateOne(
        { id: userId },
        {
          $set: { auth_token: sessionToken },
          $unset: { web_login_code: "" }
        }
      )

      return NextResponse.json({
        ok: true,
        auth_token: sessionToken
      })
    } else {
      const errMsg = !codeMatches ? '❌ Invalid verification code. Try again.' : '⏳ Code expired. Please generate a new code using /login.'
      return NextResponse.json({ ok: false, message: errMsg })
    }
  } catch (error) {
    console.error('API Auth Login Error:', error)
    return NextResponse.json({ ok: false, message: '❌ Internal Server Error' }, { status: 500 })
  }
}
