import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { handleBotCommand, handleBotCallback } from '@/lib/bot-modules'
import { handleUpdate as grabberHandleUpdate } from '@/lib/Grabber/start'

const BOT_TOKEN = process.env.BOT_TOKEN || '8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk'

export async function POST(request) {
  try {
    const update = await request.json()

    // 1. Establish MongoDB connection
    const client = await clientPromise
    if (!client) {
      console.error("Database client missing!")
      return NextResponse.json({ ok: true })
    }
    const db = client.db('Character_catcher')

    // Determine the absolute WebApp domain URL dynamically, handling Vercel comma-separated host list
    let host = request.headers.get('x-forwarded-host') || request.headers.get('host') || 'captrue-upgraded.vercel.app'
    if (host.includes(',')) {
      host = host.split(',')[0].trim()
    }

    // 2. Handle interactive Callback Queries (e.g. Combat attack/retreat, browser confirmations)
    if (update.callback_query) {
      const data = update.callback_query.data || ""
      
      // If it's a browser login approval, handle locally
      if (data.startsWith('login_confirm:') || data.startsWith('login_reject:')) {
        const { id: callbackQueryId, message } = update.callback_query
        const chatId = message.chat.id
        const messageId = message.message_id
        const userColl = db.collection('user_collection')
        const isMockTest = chatId === 888888888

        if (data.startsWith('login_confirm:')) {
          const requestId = data.split(':')[1]
          const user = await userColl.findOne({ 'web_login_request.request_id': requestId })
          if (!user) {
            if (!isMockTest) {
              await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ callback_query_id: callbackQueryId, text: '❌ Login request expired or invalid!', show_alert: true })
              })
              await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId, message_id: messageId, text: '⚠️ *Login request expired or cancelled.*', parse_mode: 'Markdown' })
              })
            }
            return NextResponse.json({ ok: true })
          }

          const sessionToken = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
          await userColl.updateOne(
            { id: user.id },
            { $set: { auth_token: sessionToken, 'web_login_request.status': 'confirmed', 'web_login_request.auth_token': sessionToken } }
          )

          if (!isMockTest) {
            await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ callback_query_id: callbackQueryId, text: '✅ Login confirmed successfully!' })
            })
            await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ chat_id: chatId, message_id: messageId, text: `✅ *Login Approved Successfully!*\n\nYou have successfully logged in to the Web App. You can close this chat now!`, parse_mode: 'Markdown' })
            })
          }
        } else if (data.startsWith('login_reject:')) {
          const requestId = data.split(':')[1]
          const user = await userColl.findOne({ 'web_login_request.request_id': requestId })
          if (user) {
            await userColl.updateOne({ id: user.id }, { $set: { 'web_login_request.status': 'rejected' } })
          }
          if (!isMockTest) {
            await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ callback_query_id: callbackQueryId, text: '❌ Login request rejected.' })
            })
            await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ chat_id: chatId, message_id: messageId, text: `❌ *Login Request Cancelled!*\n\nYou rejected this browser authorization request.`, parse_mode: 'Markdown' })
            })
          }
        }
        return NextResponse.json({ ok: true })
      }

      // Route other callback queries to Grabber module system
      await grabberHandleUpdate(update, BOT_TOKEN, host)
      return NextResponse.json({ ok: true })
    }

    // 3. Process incoming Message updates via Grabber module loader
    if (update.message) {
      await grabberHandleUpdate(update, BOT_TOKEN, host)
    }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Webhook Serverless Bot Error:', error)
    return NextResponse.json({ ok: true })
  }
}
