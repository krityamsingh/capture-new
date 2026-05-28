import { NextResponse } from 'next/server'
import { getDB } from '@/lib/Grabber/__init__'

export async function GET(request, { params }) {
  try {
    const resolvedParams = await params
    const userIdStr = resolvedParams.userId
    const userId = parseInt(userIdStr, 10)

    if (isNaN(userId)) {
      return NextResponse.json({ error: 'Invalid User ID' }, { status: 400 })
    }

    const db = await getDB()
    const userColl = db.collection('user_collection')

    let user = await userColl.findOne({ id: userId })

    if (!user) {
      return NextResponse.json({ error: 'User Not Found' }, { status: 404 })
    }

    // Strict Session validation: Require active auth token that matches
    const authToken = request.headers.get('x-auth-token')
    if (!authToken || !user.auth_token || user.auth_token !== authToken) {
      return NextResponse.json({ error: 'Unauthorized Session' }, { status: 401 })
    }

    // Cooldown logic (5 minutes = 300 seconds)
    let cooldownRemaining = 0
    if (user.last_ad_watch) {
      const lastAdWatchTime = new Date(user.last_ad_watch).getTime()
      const diffSeconds = Math.floor((Date.now() - lastAdWatchTime) / 1000)
      if (diffSeconds < 300) {
        cooldownRemaining = 300 - diffSeconds
      }
    }

    return NextResponse.json({
      gold: user.gold || 0,
      harem_count: (user.characters || []).length,
      balance: user.rubies || 0,
      cooldown_remaining: cooldownRemaining
    })
  } catch (error) {
    console.error('API User Error:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
