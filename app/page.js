'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Script from 'next/script'
import { motion, AnimatePresence } from 'framer-motion'

// ─── Config (replace before deploying) ────────────────────────────────────────
const ADSGRAM_BLOCK_ID = process.env.NEXT_PUBLIC_ADSGRAM_BLOCK_ID || 'YOUR_BLOCK_ID'
const SECRET           = process.env.NEXT_PUBLIC_ADREWARD_SECRET   || 'change_this_secret_key_abc123'
// ──────────────────────────────────────────────────────────────────────────────

const RARITY_COLORS = {
  '🔴 Common':          '#ef4444',
  '🔵 Uncommon':        '#3b82f6',
  '🟠 Rare':            '#f97316',
  '🟡 Legendary':       '#eab308',
  '🫧 Premium':         '#06b6d4',
  '🔮 Limited Edition': '#8b5cf6',
  '🏵️ Exotic':          '#10b981',
  '⚜️ Animated':        '#f59e0b',
  '🌼 Celebrity':       '#ec4899',
  '🎐 Crystal':         '#67e8f9',
  '🍹 Neon':            '#a3e635',
  '🧿 Supreme':         '#e879f9',
  '⚡ Thundra':         '#fbbf24',
  '🛸 Galvoria':        '#818cf8',
}

// ─── Subcomponents ────────────────────────────────────────────────────────────

function CharacterCard({ char, onBuy, userGold }) {
  const color = RARITY_COLORS[char.rarity] || '#a855f7'
  const canAfford = userGold >= char.price

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      whileHover={{ scale: 1.02 }}
      className="rounded-2xl overflow-hidden border transition-all duration-200"
      style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}
    >
      <div className="relative">
        <img
          src={char.img_url || '/placeholder.jpg'}
          alt={char.name}
          className="w-full object-cover"
          style={{ height: '170px' }}
          onError={e => { e.target.src = `https://placehold.co/200x170/1a1a2e/94a3b8?text=${encodeURIComponent(char.name)}` }}
        />
        {/* Rarity badge */}
        <div
          className="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full"
          style={{ background: color + '30', color, border: `1px solid ${color}50` }}
        >
          {char.rarity}
        </div>
      </div>

      <div className="p-3">
        <p className="font-bold text-sm truncate text-white">{char.name}</p>
        <p className="text-xs text-slate-400 truncate mt-0.5">{char.anime}</p>
        <motion.button
          whileTap={{ scale: 0.96 }}
          onClick={() => onBuy(char)}
          disabled={!canAfford}
          className="mt-2.5 w-full py-2 rounded-xl text-sm font-bold transition-all duration-150"
          style={{
            background: canAfford
              ? 'linear-gradient(135deg, #f59e0b, #f97316)'
              : '#2d2d4e',
            color: canAfford ? '#000' : '#64748b',
            cursor: canAfford ? 'pointer' : 'not-allowed',
          }}
        >
          💰 {char.price.toLocaleString()} gold
        </motion.button>
      </div>
    </motion.div>
  )
}

function RewardCard({ character }) {
  if (!character) return null
  const color = RARITY_COLORS[character.rarity] || '#a855f7'

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 15 }}
      className="pop-in rounded-2xl overflow-hidden border-2 mt-4"
      style={{ borderColor: color, background: '#1a1a2e' }}
    >
      <img
        src={character.img_url || ''}
        alt={character.name}
        className="w-full object-cover"
        style={{ maxHeight: '300px' }}
        onError={e => { e.target.src = `https://placehold.co/400x300/1a1a2e/94a3b8?text=${encodeURIComponent(character.name)}` }}
      />
      <div className="p-4">
        <span
          className="text-xs font-bold px-3 py-1 rounded-full inline-block mb-2"
          style={{ background: color + '25', color, border: `1px solid ${color}40` }}
        >
          {character.rarity}
        </span>
        <h3 className="text-xl font-bold text-white">{character.name}</h3>
        <p className="text-slate-400 text-sm mt-1">{character.anime}</p>
        <div className="mt-3 flex items-center gap-2">
          <span className="text-green-400 text-sm font-semibold">✅ Added to your harem!</span>
        </div>
      </div>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl overflow-hidden border" style={{ borderColor: '#2d2d4e', background: '#1a1a2e' }}>
      <div className="shimmer w-full" style={{ height: '170px' }} />
      <div className="p-3 space-y-2">
        <div className="shimmer rounded h-4 w-3/4" />
        <div className="shimmer rounded h-3 w-1/2" />
        <div className="shimmer rounded-xl h-8 w-full mt-1" />
      </div>
    </div>
  )
}

function Toast({ message, visible }) {
  return (
    <div
      className="fixed bottom-24 left-1/2 z-50 pointer-events-none transition-all duration-300 whitespace-nowrap text-sm px-5 py-3 rounded-full border"
      style={{
        transform: `translateX(-50%) translateY(${visible ? '0' : '16px'})`,
        opacity: visible ? 1 : 0,
        background: '#1e293b',
        borderColor: '#2d2d4e',
        color: '#e2e8f0',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      {message}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CaptrueMiniApp() {
  const [tab, setTab]               = useState('ad')          // 'ad' | 'shop' | 'harem'
  const [userData, setUserData]     = useState(null)
  const [shopChars, setShopChars]   = useState([])
  const [shopLoading, setShopLoading] = useState(true)
  const [adState, setAdState]       = useState('ready')       // 'ready' | 'loading' | 'claiming' | 'cooldown'
  const [rewardChar, setRewardChar] = useState(null)
  const [cdSeconds, setCdSeconds]   = useState(0)
  const [toast, setToast]           = useState({ msg: '', vis: false })
  const [isTelegram, setIsTelegram] = useState(false)
  
  // Auth state
  const [userId, setUserId]         = useState(null)
  const [userIdInput, setUserIdInput] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [authRequestId, setAuthRequestId] = useState(null)
  const [authStatus, setAuthStatus]   = useState('idle') // 'idle' | 'pending' | 'confirmed' | 'rejected' | 'expired'

  const cdRef                       = useRef(null)
  const adControllerRef             = useRef(null)
  const pollTimerRef                = useRef(null)

  // ── Toast helper ──────────────────────────────────────────────────────────
  const showToast = useCallback((msg) => {
    setToast({ msg, vis: true })
    setTimeout(() => setToast(t => ({ ...t, vis: false })), 3000)
  }, [])

  // ── Logout helper ─────────────────────────────────────────────────────────
  const handleLogout = useCallback(() => {
    localStorage.removeItem('captrue_user_id')
    localStorage.removeItem('captrue_auth_token')
    setUserId(null)
    setUserData(null)
    setRewardChar(null)
    setShopChars([])
    setUserIdInput('')
    setAuthRequestId(null)
    setAuthStatus('idle')
  }, [])

  // ── Init Telegram WebApp ──────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return
    const tg = window.Telegram?.WebApp
    
    const initializeAuth = async () => {
      // 1. If running inside Telegram, authenticate cryptographically
      if (tg && tg.initData) {
        tg.ready()
        tg.expand()
        tg.setHeaderColor?.('#0e0e1a')
        tg.setBackgroundColor?.('#0e0e1a')
        setIsTelegram(true)
        
        try {
          const authRes = await fetch('/api/auth/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData })
          })
          const authData = await authRes.json()
          if (authData.ok) {
            localStorage.setItem('captrue_auth_token', authData.auth_token)
            localStorage.setItem('captrue_user_id', authData.userId)
            setUserId(authData.userId)
          } else {
            showToast('❌ Telegram authentication failed.')
          }
        } catch {
          showToast('⚠️ Telegram connection error.')
        }
      } else {
        // 2. If running in a web browser, check localStorage session
        const storedUserId = localStorage.getItem('captrue_user_id')
        const storedToken = localStorage.getItem('captrue_auth_token')
        if (storedUserId && storedToken) {
          setUserId(parseInt(storedUserId, 10))
        }

        // Generate persistent Device ID if missing
        if (!localStorage.getItem('captrue_device_id')) {
          const randId = 'DEV-' + Math.random().toString(36).substring(2, 10).toUpperCase()
          localStorage.setItem('captrue_device_id', randId)
        }
      }
    }

    initializeAuth()

    // Init AdsGram
    if (window.Adsgram) {
      adControllerRef.current = window.Adsgram.init({ blockId: ADSGRAM_BLOCK_ID })
    }

    // Check if URL has ?tab= param
    const params = new URLSearchParams(window.location.search)
    const tabParam = params.get('tab')
    if (['ad','shop','harem'].includes(tabParam)) setTab(tabParam)
  }, [showToast])

  // ── Load user data ────────────────────────────────────────────────────────
  const loadUser = useCallback(async () => {
    if (!userId) return
    const token = localStorage.getItem('captrue_auth_token') || ''
    try {
      const res  = await fetch(`/api/user/${userId}`, {
        headers: { 'x-auth-token': token }
      })
      
      // Auto-logout if session token is rejected (401 Unauthorized)
      if (res.status === 401) {
        showToast('🔒 Session expired. Please log in again.')
        handleLogout()
        return
      }

      const data = await res.json()
      setUserData(data)

      // Resume cooldown if any
      if (data.cooldown_remaining > 0) {
        startCooldown(data.cooldown_remaining)
      }
    } catch { /* silent */ }
  }, [userId, handleLogout, showToast])

  useEffect(() => { loadUser() }, [loadUser, userId])

  // ── Load shop ─────────────────────────────────────────────────────────────
  const loadShop = useCallback(async () => {
    setShopLoading(true)
    try {
      const res  = await fetch('/api/shop')
      const data = await res.json()
      setShopChars(data.characters || [])
    } catch {
      setShopChars([])
    } finally {
      setShopLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === 'shop') loadShop()
  }, [tab, loadShop])

  // ── Cooldown ticker ───────────────────────────────────────────────────────
  const startCooldown = useCallback((seconds) => {
    setAdState('cooldown')
    setCdSeconds(seconds)
    if (cdRef.current) clearInterval(cdRef.current)
    cdRef.current = setInterval(() => {
      setCdSeconds(prev => {
        if (prev <= 1) {
          clearInterval(cdRef.current)
          setAdState('ready')
          showToast('✅ You can watch another ad now!')
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [showToast])

  useEffect(() => () => { if (cdRef.current) clearInterval(cdRef.current) }, [])

  // ── Polling logic for interactive push login ──────────────────────────────
  const startPolling = useCallback((reqId) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/auth/poll?request_id=${reqId}`)
        const data = await res.json()

        if (data.status === 'confirmed') {
          clearInterval(pollTimerRef.current)
          localStorage.setItem('captrue_auth_token', data.auth_token)
          localStorage.setItem('captrue_user_id', data.userId)
          setUserId(data.userId)
          setAuthStatus('confirmed')
          showToast('🔐 Collection synced successfully!')
        } else if (data.status === 'rejected') {
          clearInterval(pollTimerRef.current)
          setAuthStatus('rejected')
          showToast('❌ Login request rejected in Telegram.')
          setTimeout(() => {
            setAuthStatus('idle')
            setAuthRequestId(null)
          }, 3000)
        } else if (data.status === 'expired') {
          clearInterval(pollTimerRef.current)
          setAuthStatus('expired')
          showToast('⏳ Login request expired. Try again.')
          setTimeout(() => {
            setAuthStatus('idle')
            setAuthRequestId(null)
          }, 3000)
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 2000)
  }, [showToast])

  const handleRequestVerification = async () => {
    const id = parseInt(userIdInput, 10)
    if (!id || isNaN(id)) {
      showToast('⚠️ Please enter your numerical Telegram ID.')
      return
    }

    // Ensure a device ID is set
    let deviceId = localStorage.getItem('captrue_device_id')
    if (!deviceId) {
      deviceId = 'DEV-' + Math.random().toString(36).substring(2, 10).toUpperCase()
      localStorage.setItem('captrue_device_id', deviceId)
    }

    setAuthLoading(true)
    try {
      const res = await fetch('/api/auth/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: id, device_id: deviceId })
      })
      const data = await res.json()

      if (data.ok) {
        setAuthRequestId(data.request_id)
        setAuthStatus('pending')
        showToast('🔔 Notification sent to your Telegram bot!')
        startPolling(data.request_id)
      } else {
        showToast(data.message || '⚠️ Failed to initiate login.')
      }
    } catch {
      showToast('❌ Network error starting verification.')
    } finally {
      setAuthLoading(false)
    }
  }

  const handleCancelVerification = () => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    setAuthRequestId(null)
    setAuthStatus('idle')
    setAuthLoading(false)
    showToast('Cancelled login request.')
  }

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  // ── Watch ad ──────────────────────────────────────────────────────────────
  const handleWatchAd = async () => {
    if (!userId) { showToast('⚠️ Connect your Telegram Account first'); return }
    if (adState !== 'ready') return

    const token = localStorage.getItem('captrue_auth_token') || ''

    if (!adControllerRef.current) {
      showToast('📺 Simulating Ad Reward (Web Test Mode)')
    }

    setAdState('loading')

    try {
      if (adControllerRef.current) {
        await adControllerRef.current.show()
      } else {
        await new Promise(resolve => setTimeout(resolve, 1500))
      }

      setAdState('claiming')
      const res  = await fetch('/api/claim', {
        method:  'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-auth-token': token
        },
        body:    JSON.stringify({ user_id: userId, secret: SECRET }),
      })

      if (res.status === 401) {
        showToast('🔒 Session expired. Redirection to login.')
        handleLogout()
        return
      }

      const data = await res.json()

      if (data.ok) {
        setRewardChar(data.character)
        showToast(`🎉 ${data.character.name} added! +${data.gold_earned} 💰`)
        await loadUser()
        startCooldown(300)
        document.getElementById('reward-anchor')?.scrollIntoView({ behavior: 'smooth' })
      } else if (data.cooldown) {
        startCooldown(data.cooldown)
        showToast(data.message)
      } else {
        showToast(data.message || 'Something went wrong')
        setAdState('ready')
      }
    } catch (err) {
      console.error('Ad/claim error:', err)
      showToast('❌ Ad skipped or unavailable.')
      setAdState('ready')
    }
  }

  // ── Buy character ─────────────────────────────────────────────────────────
  const handleBuy = async (char) => {
    if (!userId) { showToast('⚠️ Connect your Telegram Account first'); return }

    const token = localStorage.getItem('captrue_auth_token') || ''
    const goldAvail = userData?.gold || 0
    if (goldAvail < char.price) {
      showToast(`❌ Need ${char.price} 💰, you have ${goldAvail}`)
      return
    }

    try {
      const res  = await fetch('/api/buy', {
        method:  'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-auth-token': token
        },
        body:    JSON.stringify({ user_id: userId, character_id: char.id, secret: SECRET }),
      })

      if (res.status === 401) {
        showToast('🔒 Session expired. Redirection to login.')
        handleLogout()
        return
      }

      const data = await res.json()

      if (data.ok) {
        showToast(data.message)
        await loadUser()
        setRewardChar(data.character)
        setTab('ad')
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } else {
        showToast(data.message || 'Purchase failed')
      }
    } catch {
      showToast('⚠️ Network error')
    }
  }

  // ── Format cooldown mm:ss ─────────────────────────────────────────────────
  const fmtCd = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  // ── Render Login Screen if no User ID / Token ───────────────────────────────
  if (!userId) {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center p-4 text-slate-100" style={{ background: '#0e0e1a' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-2xl p-6 text-center border w-full max-w-sm overflow-hidden relative"
          style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}
        >
          {authStatus === 'idle' ? (
            <>
              <div className="text-6xl mb-4 animate-pulse">🎴</div>
              <h1 className="text-2xl font-black mb-2 grad-text">Captrue Secure Connect</h1>
              <p className="text-slate-400 text-xs leading-relaxed mb-6">
                Connect your account. Enter your Telegram User ID below to send a secure push notification straight to your Telegram chat.
              </p>
              <div className="space-y-4 text-left">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Telegram User ID</label>
                  <input
                    type="number"
                    placeholder="e.g. 5362666067"
                    value={userIdInput}
                    onChange={e => setUserIdInput(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-[#0e0e1a] border border-[#2d2d4e] focus:border-[#e94560] focus:outline-none text-center font-bold text-lg text-white"
                  />
                </div>
                <button
                  onClick={handleRequestVerification}
                  disabled={authLoading}
                  className="w-full py-4 mt-2 rounded-xl font-bold text-white transition-all duration-150 active:scale-95 cursor-pointer flex justify-center items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #e94560, #a855f7)', opacity: authLoading ? 0.7 : 1 }}
                >
                  {authLoading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Requesting...</span>
                    </>
                  ) : (
                    <>
                      <span>🚀 Request Telegram Verification</span>
                    </>
                  )}
                </button>
              </div>
            </>
          ) : (
            <div className="py-6 flex flex-col items-center">
              {/* Radar Scanner Animation */}
              <div className="relative w-28 h-28 flex items-center justify-center mb-6">
                <motion.div
                  animate={{ scale: [1, 2], opacity: [0.5, 0] }}
                  transition={{ repeat: Infinity, duration: 1.8, ease: "easeOut" }}
                  className="absolute inset-0 rounded-full bg-purple-500/20 border border-purple-500/30"
                />
                <motion.div
                  animate={{ scale: [1, 1.6], opacity: [0.6, 0] }}
                  transition={{ repeat: Infinity, duration: 1.8, delay: 0.6, ease: "easeOut" }}
                  className="absolute inset-0 rounded-full bg-pink-500/20 border border-pink-500/30"
                />
                <div className="relative z-10 w-16 h-16 rounded-full bg-gradient-to-tr from-[#e94560] to-[#a855f7] flex items-center justify-center text-3xl shadow-xl shadow-purple-900/50">
                  🔔
                </div>
              </div>

              {authStatus === 'pending' && (
                <>
                  <h2 className="text-xl font-extrabold text-white mb-2 animate-pulse">Waiting for Approval...</h2>
                  <p className="text-slate-300 text-sm px-4 mb-1">
                    We sent a confirmation push message to your Telegram bot.
                  </p>
                  <p className="text-pink-400 font-bold text-xs px-4 mb-6 uppercase tracking-wider animate-bounce">
                    Tap "Confirm Login" in Telegram
                  </p>
                  <button
                    onClick={handleCancelVerification}
                    className="px-6 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white border border-[#2d2d4e] bg-[#0e0e1a]/50 hover:bg-[#0e0e1a] transition-all animate-pulse"
                  >
                    Cancel Request
                  </button>
                </>
              )}

              {authStatus === 'confirmed' && (
                <>
                  <div className="text-5xl mb-3">✅</div>
                  <h2 className="text-xl font-black text-green-400 mb-1">Success Confirmed!</h2>
                  <p className="text-slate-400 text-xs">Logging you in and loading waifus...</p>
                </>
              )}

              {authStatus === 'rejected' && (
                <>
                  <div className="text-5xl mb-3">❌</div>
                  <h2 className="text-xl font-black text-red-400 mb-1">Login Rejected</h2>
                  <p className="text-slate-400 text-xs">The request was rejected in Telegram.</p>
                </>
              )}

              {authStatus === 'expired' && (
                <>
                  <div className="text-5xl mb-3">⏳</div>
                  <h2 className="text-xl font-black text-yellow-500 mb-1">Request Expired</h2>
                  <p className="text-slate-400 text-xs">The 2-minute request window closed.</p>
                </>
              )}
            </div>
          )}
        </motion.div>
        <Toast message={toast.msg} visible={toast.vis} />
      </div>
    )
  }

  // ── Main App Layout ─────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col min-h-screen text-slate-100" style={{ background: '#0e0e1a' }}>
      
      {/* Dynamic AdsGram Script Loading */}
      <Script 
        src="https://sad.adsgram.org/js/sad.min.js" 
        strategy="lazyOnload" 
        onLoad={() => {
          if (window.Adsgram) {
            adControllerRef.current = window.Adsgram.init({ blockId: ADSGRAM_BLOCK_ID })
          }
        }}
      />

      {/* ── HEADER ── */}
      <header
        className="sticky top-0 z-20 flex items-center justify-between px-4 py-3 border-b"
        style={{ background: '#0e0e1a', borderColor: '#2d2d4e' }}
      >
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-black grad-text">🎴 Captrue</h1>
          {!isTelegram && (
            <button
              onClick={handleLogout}
              className="text-[10px] uppercase font-bold text-slate-400 hover:text-white transition-colors border border-[#2d2d4e] bg-[#1a1a2e] px-2 py-0.5 rounded-md cursor-pointer"
            >
              🚪 Exit
            </button>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1 bg-[#1a1a2e] px-2.5 py-1 rounded-full border border-[#2d2d4e]">
            <span className="text-yellow-400">💰</span>
            <span className="font-bold text-yellow-300">{userData?.gold?.toLocaleString() ?? '…'}</span>
          </span>
          <span className="flex items-center gap-1 bg-[#1a1a2e] px-2.5 py-1 rounded-full border border-[#2d2d4e]">
            <span className="text-pink-400">💝</span>
            <span className="font-bold text-pink-300">{userData?.harem_count ?? '…'}</span>
          </span>
        </div>
      </header>

      {/* ── TABS ── */}
      <nav
        className="flex border-b sticky z-10"
        style={{ top: '53px', background: '#1a1a2e', borderColor: '#2d2d4e' }}
      >
        {[
          { id: 'ad',    label: '📺 Watch Ad' },
          { id: 'shop',  label: '🛒 Shop' },
          { id: 'harem', label: '💝 Harem' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex-1 py-3 text-sm font-semibold transition-all duration-150 border-b-2"
            style={{
              color:       tab === t.id ? '#e94560' : '#94a3b8',
              borderColor: tab === t.id ? '#e94560' : 'transparent',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* ── CONTENT ── */}
      <main className="flex-1 overflow-y-auto p-4 pb-24 max-w-lg mx-auto w-full">
        <AnimatePresence mode="wait">
          {tab === 'ad' && (
            <motion.div
              key="ad-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {/* Ad card */}
              <div
                className="rounded-2xl p-6 text-center border mb-4"
                style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}
              >
                <div className="text-6xl mb-4 animate-bounce">📺</div>
                <h2 className="text-xl font-black text-white mb-2">Watch & Win a Waifu!</h2>
                <p className="text-slate-400 text-sm leading-relaxed mb-5">
                  Watch a short ad to receive a <span className="text-white font-semibold">random anime character</span> added straight to your harem.
                </p>

                {/* Rarity table */}
                <div
                  className="rounded-xl p-3 mb-5 text-left grid grid-cols-2 gap-1.5 text-xs"
                  style={{ background: '#0e0e1a', border: '1px solid #2d2d4e' }}
                >
                  {[
                    ['🔴 Common', '22.5%'], ['🔵 Uncommon', '12.5%'],
                    ['🟠 Rare', '7.5%'],   ['🟡 Legendary', '4%'],
                    ['🫧 Premium', '2%'],  ['🔮 Limited Ed.', '1.5%'],
                    ['⚜️ Animated', '50% 🔥', true],
                  ].map(([r, pct, hot]) => (
                    <div key={r} className={`flex justify-between px-2 py-1 rounded-lg ${hot ? 'font-bold' : ''}`}
                      style={{ background: hot ? '#f59e0b18' : 'transparent', color: hot ? '#f59e0b' : '#94a3b8' }}>
                      <span>{r}</span><span>{pct}</span>
                    </div>
                  ))}
                </div>

                {/* Watch button */}
                {adState === 'ready' && (
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    onClick={handleWatchAd}
                    className="w-full py-4 rounded-2xl font-black text-lg text-white transition-all duration-150"
                    style={{ background: 'linear-gradient(135deg, #e94560, #a855f7)', boxShadow: '0 4px 20px rgba(233,69,96,0.35)' }}
                  >
                    ▶ Watch Ad &amp; Get Character
                  </motion.button>
                )}

                {adState === 'loading' && (
                  <button disabled
                    className="w-full py-4 rounded-2xl font-black text-lg text-white shimmer"
                    style={{ background: '#2d2d4e', color: '#64748b' }}>
                    ⏳ Loading ad…
                  </button>
                )}

                {adState === 'claiming' && (
                  <button disabled
                    className="w-full py-4 rounded-2xl font-black text-lg text-white shimmer"
                    style={{ background: '#2d2d4e', color: '#64748b' }}>
                    🎁 Getting your character…
                  </button>
                )}

                {adState === 'cooldown' && (
                  <div>
                    <button disabled
                      className="w-full py-4 rounded-2xl font-black text-lg"
                      style={{ background: '#2d2d4e', color: '#64748b' }}>
                      ⏳ Next ad in {fmtCd(cdSeconds)}
                    </button>
                    {/* Progress bar */}
                    <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ background: '#2d2d4e' }}>
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{
                          width: `${(cdSeconds / 300) * 100}%`,
                          background: 'linear-gradient(90deg, #e94560, #a855f7)',
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Reward card */}
              <div id="reward-anchor" />
              {rewardChar && <RewardCard character={rewardChar} />}

              {/* Non-Telegram notice */}
              {!isTelegram && (
                <div
                  className="mt-4 p-4 rounded-xl text-sm text-center"
                  style={{ background: '#f59e0b18', border: '1px solid #f59e0b40', color: '#f59e0b' }}
                >
                  💡 Secure Web Session active for ID: <strong>{userId}</strong>.
                  <br/>
                  <span className="text-slate-400 text-xs mt-1 block">
                    You can watch simulated ads, refresh the store, and buy cards securely!
                  </span>
                </div>
              )}
            </motion.div>
          )}

          {tab === 'shop' && (
            <motion.div
              key="shop-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-black text-white text-lg">🛒 Character Shop</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Buy with gold earned from watching ads</p>
                </div>
                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={loadShop}
                  className="text-sm px-3 py-1.5 rounded-lg border transition-colors cursor-pointer"
                  style={{ borderColor: '#2d2d4e', color: '#94a3b8', background: '#1a1a2e' }}
                >
                  🔄 Refresh
                </motion.button>
              </div>

              {/* Gold display */}
              <div
                className="rounded-xl p-3 flex items-center gap-3 mb-4"
                style={{ background: '#f59e0b18', border: '1px solid #f59e0b30' }}
              >
                <span className="text-2xl">💰</span>
                <div>
                  <p className="text-xs text-slate-400">Your Gold</p>
                  <p className="font-black text-yellow-300 text-lg">{userData?.gold?.toLocaleString() ?? '…'}</p>
                </div>
                <div className="ml-auto text-xs text-slate-400 text-right">
                  <p>Watch ads to earn more gold</p>
                  <p className="text-yellow-500">+5 to +200 per character</p>
                </div>
              </div>

              {shopLoading ? (
                <div className="grid grid-cols-2 gap-3">
                  {Array(6).fill(0).map((_,i) => <SkeletonCard key={i} />)}
                </div>
              ) : shopChars.length === 0 ? (
                <div className="text-center py-16 text-slate-400">
                  <p className="text-4xl mb-3">😔</p>
                  <p>No characters available</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {shopChars.map(c => (
                    <CharacterCard
                      key={c.id}
                      char={c}
                      onBuy={handleBuy}
                      userGold={userData?.gold || 0}
                    />
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {tab === 'harem' && (
            <motion.div
              key="harem-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {/* Big counter */}
              <div
                className="rounded-2xl p-6 text-center border"
                style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}
              >
                <p
                  className="text-7xl font-black"
                  style={{ background: 'linear-gradient(135deg, #e94560, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
                >
                  {userData?.harem_count ?? '…'}
                </p>
                <p className="text-slate-400 mt-2 font-semibold">characters in your harem</p>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl p-4 border" style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}>
                  <p className="text-xs text-slate-400">Total Gold</p>
                  <p className="text-xl font-black text-yellow-300 mt-1">{userData?.gold?.toLocaleString() ?? '…'} 💰</p>
                </div>
                <div className="rounded-xl p-4 border" style={{ background: '#1a1a2e', borderColor: '#2d2d4e' }}>
                  <p className="text-xs text-slate-400">Token Balance</p>
                  <p className="text-xl font-black text-blue-300 mt-1">{userData?.balance?.toLocaleString() ?? '…'} 🪙</p>
                </div>
              </div>

              {/* Bot instruction */}
              <div
                className="rounded-xl p-4 text-sm"
                style={{ background: '#a855f718', border: '1px solid #a855f730' }}
              >
                <p className="font-bold text-purple-300 mb-2">📱 Browse your harem in the bot</p>
                <div className="space-y-1.5 text-slate-300 text-xs font-mono">
                  {[
                    ['/harem', '— view your full collection'],
                    ['/harem animated', '— filter ⚜️ Animated'],
                    ['/harem legendary', '— filter 🟡 Legendary'],
                    ['/bal', '— check gold & tokens'],
                  ].map(([cmd, desc]) => (
                    <p key={cmd}><span className="text-pink-400">{cmd}</span>{' '}{desc}</p>
                  ))}
                </div>
              </div>

              {/* How to earn */}
              <div
                className="rounded-xl p-4 text-sm"
                style={{ background: '#f59e0b18', border: '1px solid #f59e0b30' }}
              >
                <p className="font-bold text-yellow-300 mb-2">💡 How to earn gold</p>
                <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                  <li>📺 Watch ads — get a character +5–200 gold</li>
                  <li>🎯 Capture spawned characters in group chats</li>
                  <li>🏆 Complete daily missions</li>
                  <li>💰 Trade characters with other users</li>
                </ul>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* ── TOAST ── */}
      <Toast message={toast.msg} visible={toast.vis} />
    </div>
  )
}
