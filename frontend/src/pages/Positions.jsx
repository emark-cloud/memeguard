import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ConfirmTradeModal from '../components/ConfirmTradeModal'
import { getPositions, approveAction, rejectAction, sellPosition, abandonPosition } from '../services/api'

export default function Positions() {
  const [positions, setPositions] = useState([])
  const [filter, setFilter] = useState('active')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  // When set, renders the confirm-sell modal.
  // Shape: { kind: 'manual' | 'pending', pos, actionId? }
  const [sellTarget, setSellTarget] = useState(null)

  const loadPositions = async () => {
    try {
      const data = await getPositions(filter)
      setPositions(data)
    } catch (e) {
      console.error('Positions load error:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPositions()
    const interval = setInterval(loadPositions, 10000)
    return () => clearInterval(interval)
  }, [filter])

  const openPendingSellModal = (pos) => {
    setSellTarget({ kind: 'pending', pos, actionId: pos.pending_sell.id })
  }

  const handleManualSell = (pos) => {
    setSellTarget({ kind: 'manual', pos })
  }

  const handleConfirmSell = async ({ sell_fraction }) => {
    if (!sellTarget) return
    const { kind, pos, actionId } = sellTarget
    const key = kind === 'manual' ? `manual-${pos.id}` : actionId
    setActionLoading(key)
    try {
      if (kind === 'manual') {
        await sellPosition(pos.id, sell_fraction)
      } else {
        await approveAction(actionId, { sell_fraction })
      }
      setSellTarget(null)
      await loadPositions()
    } catch (e) {
      console.error('Sell error:', e)
      window.alert(`Sell failed: ${e.message || e}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async (actionId) => {
    const raw = window.prompt('Why are you rejecting this sell? (optional)')
    const reason = raw ? raw.trim().slice(0, 500) : null
    setActionLoading(actionId)
    try {
      await rejectAction(actionId, reason)
      await loadPositions()
    } catch (e) {
      console.error('Sell reject error:', e)
    } finally {
      setActionLoading(null)
    }
  }

  const handleAbandon = async (pos) => {
    const label = pos.token_name || pos.token_symbol || pos.token_address.slice(0, 10) + '...'
    if (!window.confirm(`Abandon ${label}? The position will be marked closed without an on-chain sell. Use this only when the position is too small to cover Four.meme's minimum fee.`)) return
    const key = `abandon-${pos.id}`
    setActionLoading(key)
    try {
      await abandonPosition(pos.id)
      await loadPositions()
    } catch (e) {
      console.error('Abandon error:', e)
      window.alert(`Abandon failed: ${e.message || e}`)
    } finally {
      setActionLoading(null)
    }
  }

  const pnlColor = (pnl) => {
    if (!pnl) return 'text-[var(--text-secondary)]'
    return pnl > 0 ? 'text-[#0ECB81]' : 'text-[#F6465D]'
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Positions</h1>
        <div className="flex gap-2">
          {['active', 'closed', 'all'].map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setLoading(true) }}
              className={`px-3 py-1 rounded text-sm cursor-pointer capitalize ${
                filter === f
                  ? 'bg-[var(--accent-gold)] text-black'
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">Loading...</div>
      ) : positions.length === 0 ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">
          No {filter} positions yet
        </div>
      ) : (
        <div className="bg-[var(--bg-card)] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[var(--text-secondary)] border-b border-[var(--border)]">
                <th className="text-left px-4 py-3 font-medium">Token</th>
                <th className="text-right px-4 py-3 font-medium">Entry</th>
                <th className="text-right px-4 py-3 font-medium">Current</th>
                <th className="text-right px-4 py-3 font-medium">Amount</th>
                <th className="text-right px-4 py-3 font-medium">PnL</th>
                <th className="text-right px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <React.Fragment key={pos.id}>
                  <tr className="border-b border-[var(--border)] hover:bg-[var(--bg-hover)]">
                    <td className="px-4 py-3">
                      <Link to={`/token/${pos.token_address}`} className="text-[var(--accent-gold)] no-underline text-sm">
                        {pos.token_name || pos.token_symbol || pos.token_address.slice(0, 10) + '...'}
                      </Link>
                    </td>
                    <td className="text-right px-4 py-3 text-[var(--text-primary)]">
                      {pos.entry_price?.toFixed(8) || '-'}
                    </td>
                    <td className="text-right px-4 py-3 text-[var(--text-primary)]">
                      {pos.current_price?.toFixed(8) || '-'}
                    </td>
                    <td className="text-right px-4 py-3 text-[var(--text-primary)]">
                      {pos.entry_amount_bnb?.toFixed(4) || '-'} BNB
                    </td>
                    <td className={`text-right px-4 py-3 font-medium ${pnlColor(pos.pnl_bnb)}`}>
                      {pos.pnl_bnb != null ? `${pos.pnl_bnb > 0 ? '+' : ''}${pos.pnl_bnb.toFixed(4)} BNB` : '-'}
                    </td>
                    <td className="text-right px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                        pos.status === 'active' ? 'bg-[rgba(14,203,129,0.15)] text-[#0ECB81]' : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)]'
                      }`}>
                        {pos.status}
                      </span>
                    </td>
                    <td className="text-right px-4 py-3">
                      {pos.status === 'active' && !pos.pending_sell && (
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => handleManualSell(pos)}
                            disabled={actionLoading === `manual-${pos.id}` || actionLoading === `abandon-${pos.id}`}
                            className="px-3 py-1 bg-[#F6465D] text-white text-xs font-semibold rounded cursor-pointer hover:opacity-90 disabled:opacity-50"
                          >
                            {actionLoading === `manual-${pos.id}` ? 'Selling...' : 'Sell'}
                          </button>
                          <button
                            onClick={() => handleAbandon(pos)}
                            disabled={actionLoading === `manual-${pos.id}` || actionLoading === `abandon-${pos.id}`}
                            title="Mark position closed without on-chain sell (for dust positions below Four.meme's min fee)"
                            className="px-3 py-1 bg-[var(--bg-secondary)] text-[var(--text-secondary)] text-xs rounded cursor-pointer border border-[var(--border)] hover:text-[var(--text-primary)] disabled:opacity-50"
                          >
                            {actionLoading === `abandon-${pos.id}` ? '...' : 'Abandon'}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                  {pos.pending_sell && (
                    <tr className="border-b border-[var(--border)] bg-[rgba(246,70,93,0.05)]">
                      <td colSpan={7} className="px-4 py-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <span className="text-xs font-semibold text-[#F6465D] mr-2">SELL PROPOSED</span>
                            <span className="text-xs text-[var(--text-secondary)] truncate">
                              {pos.pending_sell.rationale?.slice(0, 100)}
                            </span>
                          </div>
                          <div className="flex gap-2 ml-4 flex-shrink-0">
                            <button
                              onClick={() => openPendingSellModal(pos)}
                              disabled={actionLoading === pos.pending_sell.id}
                              className="px-3 py-1 bg-[#F6465D] text-white text-xs font-semibold rounded cursor-pointer hover:opacity-90 disabled:opacity-50"
                            >
                              {actionLoading === pos.pending_sell.id ? '...' : 'Sell'}
                            </button>
                            <button
                              onClick={() => handleReject(pos.pending_sell.id)}
                              disabled={actionLoading === pos.pending_sell.id}
                              className="px-3 py-1 bg-[var(--bg-secondary)] text-[var(--text-secondary)] text-xs rounded cursor-pointer border border-[var(--border)] hover:text-[var(--text-primary)]"
                            >
                              Hold
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmTradeModal
        open={!!sellTarget}
        mode="sell"
        label={
          sellTarget
            ? (sellTarget.pos.token_name || sellTarget.pos.token_symbol || sellTarget.pos.token_address.slice(0, 10) + '...')
            : ''
        }
        onCancel={() => {
          if (!actionLoading) setSellTarget(null)
        }}
        onConfirm={handleConfirmSell}
      />
    </div>
  )
}
