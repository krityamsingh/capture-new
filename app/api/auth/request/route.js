import { NextResponse } from 'next/server'
import crypto from 'crypto'
import { getDB } from '@/lib/Grabber/__init__'

const BOT_TOKEN = process.env.BOT_TOKEN || '8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk'

function parseUserAgent(ua) {
  if (!ua) return 'Unknown Device'
  
  let os = 'Unknown OS'
  if (ua.includes('Windows NT')) os = 'Windows PC'
  else if (ua.includes('Macintosh')) os = 'macOS Device'
  else if (ua.includes('iPhone')) os = 'iPhone'
  else if (ua.includes('iPad')) os = 'iPad'
  else if (ua.includes('Android')) os = 'Android Device'
  else if (ua.includes('Linux')) os = 'Linux PC'

  let browser = 'Unknown Browser'
  if (ua.includes('Firefox')) browser = 'Firefox'
  else if (ua.includes('Chrome')) browser = 'Chrome'
  else if (ua.includes('Safari') && !ua.includes('Chrome')) browser = 'Safari'
  else if (ua.includes('Edge')) browser = 'Edge'
  else if (ua.includes('Opera')) browser = 'Opera'

  return `${browser} on ${os}`
}

export async function POST(request) {
  try {
    const { user_id, device_id } = await request.json()
    const userId = parseInt(user_id, 10)
    const deviceId = device_id || 'Unknown Device ID'

    if (isNaN(userId)) {
      return NextResponse.json({ ok: false, message: '❌ Invalid Telegram User ID' }, { status: 400 })
    }

    const db = await getDB()
    const userColl = db.collection('user_collection')

    // Find the user first
    const user = await userColl.findOne({ id: userId })
    if (!user) {
      return NextResponse.json({
        ok: false,
        message: '❌ Account not found. Please search for the bot in Telegram and tap /start first!'
      }, { status: 404 })
    }

    // Parse User Agent
    const ua = request.headers.get('user-agent') || ''
    const deviceName = parseUserAgent(ua)

    // Parse Vercel Geolocation headers
    const city = request.headers.get('x-vercel-ip-city')
    const country = request.headers.get('x-vercel-ip-country')
    const region = request.headers.get('x-vercel-ip-country-region')
    
    let locationStr = 'Unknown Location'
    if (city && country) {
      const decodedCity = decodeURIComponent(city)
      locationStr = region ? `${decodedCity}, ${region}, ${country}` : `${decodedCity}, ${country}`
    } else {
      const ip = request.headers.get('x-vercel-forwarded-for') || request.headers.get('x-forwarded-for') || '127.0.0.1'
      if (ip === '127.0.0.1' || ip.includes('::1')) {
        locationStr = 'Localhost (Development)'
      }
    }

    // Generate a secure high-entropy request ID
    const requestId = crypto.randomBytes(16).toString('hex')
    const expiresAt = new Date(Date.now() + 2 * 60 * 1000) // 2 minutes expiration

    // Save pending request to database
    await userColl.updateOne(
      { id: userId },
      {
        $set: {
          web_login_request: {
            request_id: requestId,
            status: 'pending',
            expires_at: expiresAt,
            device_id: deviceId,
            device_name: deviceName,
            location: locationStr
          }
        }
      }
    )

    // Format the Telegram Notification message
    const tgMessage = `🔔 *Captrue WebApp Login Request* 🔔\n\n` +
                      `A browser login attempt was initiated for your account.\n\n` +
                      `• *User ID:* \`${userId}\`\n` +
                      `• *Device ID:* \`${deviceId}\`\n` +
                      `• *Browser/Device:* \`${deviceName}\`\n` +
                      `• *Location:* \`${locationStr}\`\n` +
                      `• *Status:* ⏳ Waiting for approval\n` +
                      `• *Time Limit:* 2 minutes\n\n` +
                      `*Please tap one of the buttons below to confirm or reject this login.*`

    const replyMarkup = {
      inline_keyboard: [
        [
          {
            text: '✅ Confirm Login',
            callback_data: `login_confirm:${requestId}`
          },
          {
            text: '❌ Reject Request',
            callback_data: `login_reject:${requestId}`
          }
        ]
      ]
    }

    // Bypass real Telegram message sending for mock test user ID 888888888
    if (userId === 888888888) {
      console.log('Test Mock User detected. Bypassing Telegram notification send.')
      return NextResponse.json({
        ok: true,
        request_id: requestId
      })
    }

    const tgRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: userId,
        text: tgMessage,
        parse_mode: 'Markdown',
        reply_markup: replyMarkup
      })
    })

    const tgData = await tgRes.json()

    if (!tgData.ok) {
      console.error('Telegram notification error:', tgData)
      return NextResponse.json({
        ok: false,
        message: '⚠️ Telegram could not be notified. Please ensure you have launched the bot first.'
      })
    }

    return NextResponse.json({
      ok: true,
      request_id: requestId
    })

  } catch (error) {
    console.error('API Auth Request Error:', error)
    return NextResponse.json({ ok: false, message: '❌ Internal Server Error' }, { status: 500 })
  }
}
