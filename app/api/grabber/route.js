/**
 * app/api/grabber/route.js
 * =========================
 * The Vercel-side "Grabber scraper" webhook endpoint.
 *
 * This is the JS equivalent of the Python bot running in server mode:
 *   start.py → __main__.py:main() → Grabber.modules.* → PTB event loop
 *
 * Vercel hits this on every Telegram webhook event. It:
 *   1. Calls Grabber.boot() → init_clients() + load all modules
 *   2. Calls Grabber.handleUpdate() → routes update to the correct module
 *
 * URL: POST /api/grabber
 */
import { NextResponse } from 'next/server';
import { handleUpdate } from '../../../lib/Grabber/start';

export const dynamic   = 'force-dynamic';
export const maxDuration = 60; // Vercel pro: max 60s per invocation

export async function GET(req) {
  const modules = [];
  try {
    // On GET: return module manifest (shows Vercel the bot is alive)
    const { loadAllModules } = await import('../../../lib/Grabber/module_init');
    const loaded = loadAllModules();
    return NextResponse.json({
      status: 'online',
      bot:    'CaptureCharacterBot (Grabber JS)',
      note:   'JS mirror of Python Grabber bot — Vercel serverless edition',
      modules_loaded: loaded.length,
      modules: loaded,
    });
  } catch (e) {
    return NextResponse.json({ status: 'error', error: e.message }, { status: 500 });
  }
}

export async function POST(req) {
  const BOT_TOKEN = process.env.BOT_TOKEN || '7686672468:AAFhqx5FomKltXmGGv-5K056v9jQx1psLe4';
  const host = req.headers.get('host') || 'localhost';

  let update;
  try {
    update = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!update || typeof update !== 'object') {
    return NextResponse.json({ error: 'Invalid update' }, { status: 400 });
  }

  try {
    await handleUpdate(update, BOT_TOKEN, host);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[Grabber API] Error handling update:', err);
    return NextResponse.json({ ok: false, error: err.message }, { status: 500 });
  }
}
