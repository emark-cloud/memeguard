/**
 * Backend API client for FourScout.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// Shared-secret auth. Empty = backend has auth disabled (local dev).
const API_KEY = import.meta.env.VITE_API_KEY || ''

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (API_KEY) headers['X-API-Key'] = API_KEY
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export const getApiKey = () => API_KEY

// Tokens
export const getTokens = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return request(`/tokens${qs ? '?' + qs : ''}`)
}

export const getToken = (address) => request(`/tokens/${address}`)

// Config
export const getConfig = () => request('/config')

export const updateConfig = (key, value) =>
  request('/config', {
    method: 'PUT',
    body: JSON.stringify({ key, value }),
  })

export const updateConfigBulk = (updates) =>
  request('/config/bulk', {
    method: 'PUT',
    body: JSON.stringify(updates),
  })

// Positions
export const getPositions = (status = 'active') =>
  request(`/positions?status=${status}`)

export const sellPosition = (positionId, sellFraction = null) =>
  request(`/positions/${positionId}/sell`, {
    method: 'POST',
    body: JSON.stringify(sellFraction != null ? { sell_fraction: sellFraction } : {}),
  })

export const abandonPosition = (positionId) =>
  request(`/positions/${positionId}/abandon`, { method: 'POST' })

// Activity
export const getActivity = (limit = 50) => request(`/activity?limit=${limit}`)

// Actions
export const getPendingActions = () => request('/actions/pending')

export const approveAction = (actionId, overrides = {}) => {
  const body = { action_id: actionId }
  if (overrides.amount_bnb != null) body.amount_bnb = overrides.amount_bnb
  if (overrides.sell_fraction != null) body.sell_fraction = overrides.sell_fraction
  return request('/actions/approve', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export const rejectAction = (actionId, reason = null) =>
  request('/actions/reject', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId, reason }),
  })

export const getRejectionReasons = (days = 7, limit = 3) =>
  request(`/overrides/rejection_reasons?days=${days}&limit=${limit}`)

// Avoided
export const getAvoided = (limit = 50) => request(`/avoided?limit=${limit}`)
export const getAvoidedStats = () => request('/avoided/stats')

// Watchlist
export const getWatchlist = () => request('/watchlist')

export const addWatchlistItem = (item) =>
  request('/watchlist', {
    method: 'POST',
    body: JSON.stringify(item),
  })

export const removeWatchlistItem = (id) =>
  request(`/watchlist/${id}`, { method: 'DELETE' })

// Daily trade stats
export const getDailyTradeStats = () => request('/trades/daily')

// Chat advisor
export const sendChatMessage = (message, tokenAddress = null) =>
  request('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, token_address: tokenAddress }),
  })

export const getChatHistory = (tokenAddress = null) => {
  const qs = tokenAddress ? `?token_address=${encodeURIComponent(tokenAddress)}` : ''
  return request(`/chat/history${qs}`)
}

export const clearChatHistory = (tokenAddress = null, scope = 'current') => {
  const params = new URLSearchParams({ scope })
  if (tokenAddress) params.set('token_address', tokenAddress)
  return request(`/chat/history?${params.toString()}`, { method: 'DELETE' })
}

// Override stats (behavioral nudge)
export const getOverrideStats = () => request('/overrides/stats')

// Agent Identity (ERC-8004)
export const getAgentStatus = () => request('/agent/status')

export const registerAgent = (name, imageUrl = null, description = null) =>
  request('/agent/register', {
    method: 'POST',
    body: JSON.stringify({ name, image_url: imageUrl, description }),
  })

// Health
export const getHealth = () => request('/health')
