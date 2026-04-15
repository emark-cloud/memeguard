/**
 * Backend API client for MemeGuard.
 */

const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

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

// Activity
export const getActivity = (limit = 50) => request(`/activity?limit=${limit}`)

// Actions
export const getPendingActions = () => request('/actions/pending')

export const approveAction = (actionId) =>
  request('/actions/approve', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId }),
  })

export const rejectAction = (actionId) =>
  request('/actions/reject', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId }),
  })

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

export const clearChatHistory = () =>
  request('/chat/history', { method: 'DELETE' })

// Health
export const getHealth = () => request('/health')
