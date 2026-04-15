import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import RiskBadge from '../components/RiskBadge'
import ChatPanel from '../components/ChatPanel'
import { getToken, approveAction, rejectAction } from '../services/api'

export default function OpportunityDetail() {
  const { address } = useParams()
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await getToken(address)
        setToken(data)
      } catch (e) {
        console.error('Token load error:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [address])

  const handleApprove = async () => {
    if (!token?.pending_action) return
    setActionLoading(true)
    setActionError(null)
    try {
      await approveAction(token.pending_action.id)
      const data = await getToken(address)
      setToken(data)
    } catch (e) {
      console.error('Approve error:', e)
      setActionError('Failed to approve action. Please try again.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async () => {
    if (!token?.pending_action) return
    setActionLoading(true)
    setActionError(null)
    try {
      await rejectAction(token.pending_action.id)
      const data = await getToken(address)
      setToken(data)
    } catch (e) {
      console.error('Reject error:', e)
      setActionError('Failed to reject action. Please try again.')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-[var(--text-secondary)]">Loading...</div>
  }

  if (!token || token.error) {
    return (
      <div className="text-center py-12">
        <p className="text-[var(--text-secondary)]">Token not found</p>
        <Link to="/" className="text-[var(--accent-gold)] text-sm">Back to Dashboard</Link>
      </div>
    )
  }

  let riskDetail = {}
  try {
    riskDetail = token.risk_detail ? JSON.parse(token.risk_detail) : {}
  } catch { /* ignore */ }

  const progress = token.bonding_curve_progress || 0

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back link */}
      <Link to="/" className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-4 inline-block no-underline">
        &larr; Back to Dashboard
      </Link>

      {/* Header */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              {token.name} <span className="text-[var(--text-secondary)] font-normal">${token.symbol}</span>
            </h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1 font-mono">{token.address}</p>
          </div>
          <RiskBadge score={token.risk_score} size="lg" />
        </div>

        {/* Bonding curve */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-[var(--text-secondary)] mb-1">
            <span>Bonding Curve Progress</span>
            <span>{(progress * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(progress * 100, 100)}%`,
                backgroundColor: progress >= 1 ? '#0ECB81' : '#F0B90B',
              }}
            />
          </div>
          {token.graduated ? (
            <span className="text-xs text-[#0ECB81] mt-1 inline-block">Graduated to PancakeSwap</span>
          ) : null}
        </div>

        {/* Creator */}
        {token.creator_address && (
          <div className="text-sm text-[var(--text-secondary)]">
            Creator: <span className="font-mono text-[var(--text-primary)]">{token.creator_address}</span>
          </div>
        )}
      </div>

      {/* Risk breakdown */}
      <div className="bg-[var(--bg-card)] rounded-xl p-6 mb-4">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Risk Breakdown</h2>
        {Object.keys(riskDetail).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(riskDetail).map(([signal, data]) => (
              <div key={signal}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-[var(--text-secondary)] capitalize">
                    {signal.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[var(--text-primary)]">{data.score}/10</span>
                </div>
                <div className="h-1.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(data.score / 10) * 100}%`,
                      backgroundColor: data.score >= 7 ? '#0ECB81' : data.score >= 4 ? '#F0B90B' : '#F6465D',
                    }}
                  />
                </div>
                {data.detail && (
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">{data.detail}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[var(--text-secondary)] text-sm">Risk scoring in progress...</p>
        )}
      </div>

      {/* LLM Rationale */}
      {token.risk_rationale && (
        <div className="bg-[var(--bg-card)] rounded-xl p-6 mb-4">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">AI Analysis</h2>
          <p className="text-[var(--text-secondary)] text-sm leading-relaxed">{token.risk_rationale}</p>
        </div>
      )}

      {/* Approval section */}
      {token.pending_action && token.pending_action.status === 'pending' && (() => {
        let txPreview = null
        try {
          txPreview = token.pending_action.tx_preview ? JSON.parse(token.pending_action.tx_preview) : null
        } catch { /* ignore */ }

        return (
          <div className="bg-[var(--bg-card)] rounded-xl p-6 border-2 border-[var(--accent-gold)] mb-4">
            <h2 className="text-lg font-semibold text-[var(--accent-gold)] mb-2">
              Proposed: {token.pending_action.action_type.toUpperCase()}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
              <div>
                <span className="text-[var(--text-secondary)]">Amount</span>
                <p className="text-[var(--text-primary)] font-medium">{token.pending_action.amount_bnb} BNB</p>
              </div>
              <div>
                <span className="text-[var(--text-secondary)]">Slippage</span>
                <p className="text-[var(--text-primary)] font-medium">{token.pending_action.slippage || 5}%</p>
              </div>
              {txPreview?.estimated_tokens > 0 && (
                <div>
                  <span className="text-[var(--text-secondary)]">Est. Tokens</span>
                  <p className="text-[var(--text-primary)] font-medium">
                    {Number(txPreview.estimated_tokens).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </div>
              )}
              {txPreview?.min_tokens > 0 && (
                <div>
                  <span className="text-[var(--text-secondary)]">Min Tokens</span>
                  <p className="text-[var(--text-primary)] font-medium">
                    {Number(txPreview.min_tokens).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </div>
              )}
            </div>
            {token.pending_action.rationale && (
              <p className="text-[var(--text-secondary)] text-sm mb-4">{token.pending_action.rationale}</p>
            )}
            {actionError && (
              <p className="text-[#F6465D] text-sm mb-3">{actionError}</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="flex-1 bg-[#0ECB81] text-black font-semibold py-2.5 rounded-lg cursor-pointer hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {actionLoading ? 'Executing...' : 'Approve'}
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="flex-1 bg-[var(--bg-secondary)] text-[var(--text-primary)] font-semibold py-2.5 rounded-lg cursor-pointer border border-[var(--border)] hover:bg-[var(--bg-hover)] disabled:opacity-50 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        )
      })()}

      {/* Token-scoped AI chat */}
      <ChatPanel tokenAddress={token.address} tokenName={`${token.name} ($${token.symbol})`} />
    </div>
  )
}
