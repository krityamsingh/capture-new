/**
 * Grabber/module_init.js
 * =======================
 * JavaScript mirror of Python's Grabber/module_init.py
 *
 * This is the Grabber module loader. It:
 *  1. Scans lib/Grabber/modules/*.js for all handler files
 *  2. Dynamically requires each one (like Python's importlib.import_module)
 *  3. Registers each module's handlers into the global Grabber app context
 *  4. Exposes ALL_MODULES list for introspection (mirrors Python's __all__)
 *
 * Boot sequence mirrors Python:
 *   start.py → __main__.py:main() → init_clients() → importlib.import_module(modules)
 *                                                    ↑ this file does that in JS
 */

const path = require('path');
const fs   = require('fs');
const Grabber = require('./__init__');

// ─── Module Registry (mirrors Python's importlib module map) ─────────────────
// Each module registers command handlers, callback handlers, and spawn hooks
const _registry = {
  commands:   {},  // cmd_name → async handler(update, ctx)
  callbacks:  {},  // prefix   → async handler(callbackQuery, ctx)
  spawnHooks: [],  // [async fn(update, ctx)] — called on every group message
};

// ─── Capsify helper (mirrors module_init.py capsify) ─────────────────────────
const ALPHABETS = 'abcdefghijklmnopqrstuvwxyz';
const ALL_CAPS  = 'ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ';

function capsify(text) {
  return text.split('').map(c => {
    if (c === '\n' || c === ' ') return c;
    const idx = ALPHABETS.indexOf(c.toLowerCase());
    return idx >= 0 ? ALL_CAPS[idx] : c;
  }).join('');
}

// ─── Module registration API — used by every module file ─────────────────────
function registerCommand(name, handler) {
  // name can be string or array (aliases)
  const names = Array.isArray(name) ? name : [name];
  for (const n of names) {
    _registry.commands[n.toLowerCase().replace(/^\//, '')] = handler;
    console.log(`[Grabber] Registered command: /${n}`);
  }
}

function registerCallback(prefix, handler) {
  _registry.callbacks[prefix] = handler;
  console.log(`[Grabber] Registered callback: ${prefix}:`);
}

function registerSpawnHook(handler) {
  _registry.spawnHooks.push(handler);
}

// ─── Module scanner (statically defined for Vercel bundler compatibility) ─────
const modulesMap = {
  start: require('./modules/start'),
};

function listAllModules() {
  return Object.keys(modulesMap);
}

// ─── Boot: load all modules (mirrors Python's importlib.import_module loop) ──
let _loaded = false;
const ALL_MODULES = [];

function loadAllModules() {
  if (_loaded) return ALL_MODULES;

  const moduleNames = listAllModules();
  console.log(`[Grabber] Modules to load: ${moduleNames.join(', ')}`);

  for (const name of moduleNames) {
    try {
      const mod = modulesMap[name];
      // Each module exports { commands, callbacks, spawnHooks }
      if (mod.commands) {
        for (const [cmd, fn] of Object.entries(mod.commands)) {
          registerCommand(cmd, fn);
        }
      }
      if (mod.callbacks) {
        for (const [prefix, fn] of Object.entries(mod.callbacks)) {
          registerCallback(prefix, fn);
        }
      }
      if (mod.spawnHooks) {
        for (const fn of mod.spawnHooks) {
          registerSpawnHook(fn);
        }
      }
      ALL_MODULES.push(name);
      console.log(`[Grabber] ✅ Loaded module: ${name}`);
    } catch (err) {
      console.error(`[Grabber] ❌ Failed to load module '${name}':`, err.message);
    }
  }

  _loaded = true;
  return ALL_MODULES;
}

// ─── Dispatch: routes update → correct registered module handler ─────────────
async function dispatch(update, db, botToken, host) {
  // Ensure modules are loaded (lazy init on first request)
  loadAllModules();

  const collections = await Grabber.getCollections();
  const ctx = { db, botToken, host, collections, ...collections };

  // 1. Handle callback queries → route to registered callback handlers
  if (update.callback_query) {
    const data = update.callback_query.data || '';
    for (const [prefix, handler] of Object.entries(_registry.callbacks)) {
      if (data.startsWith(prefix)) {
        return await handler(update.callback_query, ctx);
      }
    }
    return;
  }

  const message = update.message;
  if (!message) return;

  // 2. Run spawn hooks (every message in group triggers spawn check)
  if (message.chat && (message.chat.type === 'group' || message.chat.type === 'supergroup')) {
    for (const hook of _registry.spawnHooks) {
      try { await hook(update, ctx); } catch (e) { /* non-fatal */ }
    }
  }

  // 3. Route text commands → registered command handlers
  const text = message.text || message.caption || '';
  if (!text.startsWith('/')) return;

  const parts   = text.trim().split(/\s+/);
  const rawCmd  = parts[0].toLowerCase().split('@')[0].replace(/^\//, '');
  const handler = _registry.commands[rawCmd];

  if (handler) {
    return await handler(update, ctx);
  }
}

module.exports = {
  ALL_MODULES,
  loadAllModules,
  listAllModules,
  dispatch,
  registerCommand,
  registerCallback,
  registerSpawnHook,
  capsify,
};
