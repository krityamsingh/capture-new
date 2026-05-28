import { NextResponse } from 'next/server'

const BOT_TOKEN = process.env.BOT_TOKEN || '8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk'

export async function GET(request) {
  try {
    // Determine the absolute WebApp domain URL dynamically from request headers
    const host = request.headers.get('x-forwarded-host') || request.headers.get('host') || 'captrue-upgraded.vercel.app'
    const protocol = host.includes('localhost') ? 'http' : 'https'
    const targetUrl = `${protocol}://${host}/api/bot`

    const tgApiUrl = `https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${encodeURIComponent(targetUrl)}`
    
    console.log('Registering Webhook URL:', targetUrl)
    const tgRes = await fetch(tgApiUrl)
    const tgData = await tgRes.json()

    return NextResponse.json({
      success: tgData.ok,
      webhook_url: targetUrl,
      telegram_response: tgData
    })
  } catch (error) {
    console.error('Webhook Setup Error:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
