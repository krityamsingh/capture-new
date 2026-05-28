/**
 * lib/Grabber/start.js
 * =====================
 * JavaScript mirror of Python's start.py + __main__.py
 *
 * This IS the Grabber entry point — it:
 *  1. Calls initDB()       → mirrors init_clients()
 *  2. Calls loadAllModules() → mirrors the importlib.import_module loop
 *  3. Returns dispatch()   → the main update router
 *
 * On Vercel:  called once per serverless cold start, then cached.
 * On Python:  asyncio.run(main()) runs once at process startup.
 */

const Grabber      = require('./__init__');
const moduleInit   = require('./module_init');

let _booted = false;

async function boot() {
  if (_booted) return;
  console.log('[Grabber] ⟳ Booting up — init_clients() + loadAllModules()…');
  await Grabber.initDB();
  const modules = moduleInit.loadAllModules();
  console.log(`[Grabber] ✅ Boot complete — ${modules.length} modules loaded: [${modules.join(', ')}]`);
  _booted = true;
}

/**
 * handleUpdate — the Vercel/serverless replacement for PTB's update polling
 * Called by /api/grabber/route.js on every incoming Telegram webhook event
 */
async function handleUpdate(update, botToken, host) {
  await boot();
  const db = await Grabber.getDB();
  return moduleInit.dispatch(update, db, botToken, host);
}

module.exports = { boot, handleUpdate };
