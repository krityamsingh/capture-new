/**
 * Grabber/__init__.js
 * ===================
 * JavaScript mirror of Python's Grabber/__init__.py
 * 
 * This is the Grabber core — it holds the DB client, all collection references,
 * bot token, config, and the singleton app context.
 * 
 * Boot sequence mirrors Python:
 *   start.py → Grabber/__init__.py → Grabber/modules/* loaded by module_init.js
 */

const { MongoClient } = require('mongodb');

// ─── Config (mirrors Grabber/config.py) ─────────────────────────────────────
const OWNER_IDS   = [6228788487, 8496760733, 7878477646, 7976292835, 6118760915];
const BOT_TOKEN   = process.env.BOT_TOKEN   || '7686672468:AAFhqx5FomKltXmGGv-5K056v9jQx1psLe4';
const MONGO_URL   = process.env.MONGODB_URI || 'mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0';

const SUPPORT_CHAT      = 'Devince_Support';
const BOT_USERNAME      = 'CaptureCharacterBot';
const CHARA_CHANNEL_ID  = -1002672414862;
const UPLOAD_CHANNEL_ID = -1002672414862;
const UPLOAD_GC_ID      = -1002313549356;
const SUPPORT_GROUP_ID  = -1003695209406;
const CATBOX_USERHASH   = 'de47eb51da1e8bc98c5ca9cf3';

// ─── Singleton DB client (lazy, shared across all modules) ────────────────────
let _mongoClient = null;
let _db          = null;
let _collections = {};

async function initDB() {
  if (_db) return _db;
  _mongoClient = new MongoClient(MONGO_URL, { serverSelectionTimeoutMS: 5000 });
  await _mongoClient.connect();
  _db = _mongoClient.db('Character_catcher');
  _initCollections(_db);
  return _db;
}

function _initCollections(db) {
  // Mirrors every collection from Python's init_clients()
  _collections = {
    collection:                   db.collection('anime_characters'),
    user_totals_collection:       db.collection('user_totals'),
    user_collection:              db.collection('user_collection'),
    joke_collection:              db.collection('joke_collection'),
    safari_cooldown_collection:   db.collection('safari_cooldown_collection'),
    safari_users_collection:      db.collection('safari_users_collection'),
    group_user_totals_collection: db.collection('group_user_total'),
    top_global_groups_collection: db.collection('top_global_groups'),
    guild:                        db.collection('guild_team'),
    gban:                         db.collection('gban'),
    clan_collection:              db.collection('clans'),
    join_requests_collection:     db.collection('join_requests'),
    global_ban_users_collection:  db.collection('global_ban_users'),
    users_collection:             db.collection('user'),
    videos_collection:            db.collection('videos'),
    sales_collection:             db.collection('sales'),
    blocked_users_collection:     db.collection('blocked_users'),
    like_dislike_collection:      db.collection('like_dislike_data'),
    user_votes_collection:        db.collection('user_votes'),
    add_coins:                    db.collection('add_coins'),
    add_character:                db.collection('add_character'),
    store_items:                  db.collection('store_items'),
    auction:                      db.collection('auction'),
    global_mute_users_collection: db.collection('global_mute_users_collection'),
    monster_collection:           db.collection('monster_collection'),
    action_history_collection:    db.collection('action_history_collection'),
    gang_collection:              db.collection('gang_collection'),
    mission_collection:           db.collection('mission_collection'),
    chain_collection:             db.collection('chain_collection'),
    word_collection:              db.collection('words'),
    fsub_collection:              db.collection('fsub_collection'),
    chat_auctions:                db.collection('chat_auctions'),
    active_auctions:              db.collection('active_auctions'),
    backup_collection:            db.collection('backup_collection'),
    clan_war_collection:          db.collection('clan_war_collection'),
    giveaway_collection:          db.collection('giveaway_collection'),
    sequences:                    db.collection('sequences'),
    uploader:                     db.collection('uploader'),
    sudo:                         db.collection('sudo'),
    groups:                       db.collection('groups'),
    block:                        db.collection('block'),
  };
}

// Accessor — modules call getDB() to get the raw db instance
async function getDB() {
  if (!_db) await initDB();
  return _db;
}

// Accessor — modules call getCollection(name) like Pyrogram references
async function getCollection(name) {
  if (!_db) await initDB();
  return _collections[name] || _db.collection(name);
}

// Direct shorthand accessors — mirrors Python: `from Grabber import collection, db`
async function getCollections() {
  if (!_db) await initDB();
  return _collections;
}

module.exports = {
  OWNER_IDS,
  BOT_TOKEN,
  MONGO_URL,
  SUPPORT_CHAT,
  BOT_USERNAME,
  CHARA_CHANNEL_ID,
  UPLOAD_CHANNEL_ID,
  UPLOAD_GC_ID,
  SUPPORT_GROUP_ID,
  CATBOX_USERHASH,
  initDB,
  getDB,
  getCollection,
  getCollections,
};
