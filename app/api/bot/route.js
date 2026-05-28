import { NextResponse } from 'next/server'
import { handleUpdate as grabberHandleUpdate, boot } from '@/lib/Grabber/start'
import { getDB } from '@/lib/Grabber/__init__'

const BOT_TOKEN = process.env.BOT_TOKEN || '7686672468:AAFhqx5FomKltXmGGv-5K056v9jQx1psLe4'

async function tgApi(method, body) {
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function POST(request) {
  try {
    const update = await request.json()

    // Boot Grabber module system + DB on cold start
    await boot()
    const db = await getDB()

    // Determine host for webapp URL building
    let host = request.headers.get('x-forwarded-host') || request.headers.get('host') || 'captrue-upgraded.vercel.app'
    if (host.includes(',')) host = host.split(',')[0].trim()

    // ── Handle login confirm/reject callbacks ──────────────────────────────
    if (update.callback_query) {
      const data = update.callback_query.data || ''

      if (data.startsWith('login_confirm:') || data.startsWith('login_reject:')) {
        const { id: cqId, message, from } = update.callback_query
        const chatId    = message.chat.id
        const messageId = message.message_id
        const userColl  = db.collection('user_collection')

        if (data.startsWith('login_confirm:')) {
          const requestId = data.split(':')[1]
          const user = await userColl.findOne({ 'web_login_request.request_id': requestId })

          if (!user) {
            await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '❌ Login request expired or invalid!', show_alert: true })
            await tgApi('editMessageText', { chat_id: chatId, message_id: messageId, text: '⚠️ *Login request expired or cancelled.*', parse_mode: 'Markdown' })
            return NextResponse.json({ ok: true })
          }

          // Generate session token and store it
          const sessionToken = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
          await userColl.updateOne(
            { id: user.id },
            {
              $set: {
                auth_token: sessionToken,
                'web_login_request.status': 'confirmed',
                'web_login_request.auth_token': sessionToken
              }
            }
          )

          await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '✅ Login confirmed!' })
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: `✅ *Login Approved!*\n\nYou are now logged in to the Web App. You can close this chat.`,
            parse_mode: 'Markdown'
          })

        } else if (data.startsWith('login_reject:')) {
          const requestId = data.split(':')[1]
          const user = await userColl.findOne({ 'web_login_request.request_id': requestId })
          if (user) {
            await userColl.updateOne({ id: user.id }, { $set: { 'web_login_request.status': 'rejected' } })
          }
          await tgApi('answerCallbackQuery', { callback_query_id: cqId, text: '❌ Login rejected.' })
          await tgApi('editMessageText', {
            chat_id: chatId,
            message_id: messageId,
            text: `❌ *Login Request Rejected!*\n\nYou denied this browser login attempt.`,
            parse_mode: 'Markdown'
          })
        }

        return NextResponse.json({ ok: true })
      }

      // All other callbacks → Grabber module dispatcher
      await grabberHandleUpdate(update, BOT_TOKEN, host)
      return NextResponse.json({ ok: true })
    }

    // ── All message updates → Grabber module dispatcher ────────────────────
    if (update.message) {
      await grabberHandleUpdate(update, BOT_TOKEN, host)
    }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('[/api/bot] Error:', error)
    return NextResponse.json({ ok: true })
  }
}
