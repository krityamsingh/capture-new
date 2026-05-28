import { NextResponse } from 'next/server'
import { getDB } from '@/lib/Grabber/__init__'

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const requestId = searchParams.get('request_id')

    if (!requestId) {
      return NextResponse.json({ status: 'expired', message: 'Missing Request ID' }, { status: 400 })
    }

    const db = await getDB()
    const userColl = db.collection('user_collection')

    // Find user with this request ID
    const user = await userColl.findOne({ 'web_login_request.request_id': requestId })
    if (!user || !user.web_login_request) {
      return NextResponse.json({ status: 'expired' })
    }

    // Check expiration
    const expiresAt = new Date(user.web_login_request.expires_at)
    if (new Date() > expiresAt) {
      // Clear expired request in database
      await userColl.updateOne(
        { id: user.id },
        { $unset: { web_login_request: '' } }
      )
      return NextResponse.json({ status: 'expired' })
    }

    const status = user.web_login_request.status

    if (status === 'confirmed') {
      const authToken = user.web_login_request.auth_token
      
      // Clean up the verified login request now that session is successfully established
      await userColl.updateOne(
        { id: user.id },
        { $unset: { web_login_request: '' } }
      )

      return NextResponse.json({
        status: 'confirmed',
        auth_token: authToken,
        userId: user.id
      })
    }

    if (status === 'rejected') {
      // Clean up rejected request
      await userColl.updateOne(
        { id: user.id },
        { $unset: { web_login_request: '' } }
      )
      return NextResponse.json({ status: 'rejected' })
    }

    // Otherwise, still pending
    return NextResponse.json({ status: 'pending' })

  } catch (error) {
    console.error('API Auth Poll Error:', error)
    return NextResponse.json({ status: 'expired', error: 'Internal Server Error' }, { status: 500 })
  }
}
