import { useState, useEffect } from 'react'
import TokenCard from '../components/TokenCard'
import BudgetBar from '../components/BudgetBar'
import { getTokens, getConfig, getPositions, getAvoidedStats, getDailyTradeStats, getOverrideStats, getRejectionReasons } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'

const PERSONA_LABELS = {
  conservative: { label: 'Conservative', icon: '\u{1F6E1}', color: '#0ECB81' },
  momentum: { label: 'Momentum', icon: '\u{26A1}', color: '#F0B90B' },
  sniper: { label: 'Sniper', icon: '\u{1F3AF}', color: '#F6465D' },
}

export default function Dashboard() {
  const [tokens, setTokens] = useState([])
  const [config, setConfig] = useState({})
  const [stats, setStats] = useState({ trades: 0, positions: 0, avoided: 0, savings: 0, spent: 0 })
  const [overrides, setOverrides] = useState(null)
  const [rejectionReasons, setRejectionReasons] = useState([])
  const [loading, setLoading] = useState(true)
  const { isConnected: wsConnected } = useWebSocket()

  useEffect(() => {
    async function load() {
      try {
        const [tokenData, configData, posData, avoidedData, dailyData, overrideData, reasonsData] = await Promise.all([
          getTokens({ limit: 30 }).catch(() => []),
          getConfig().catch(() => ({})),
          getPositions('active').catch(() => []),
          getAvoidedStats().catch(() => ({ confirmed_rugs: 0, estimated_savings_bnb: 0 })),
          getDailyTradeStats().catch(() => ({ spent_today_bnb: 0, trades_today: 0 })),
          getOverrideStats().catch(() => null),
          getRejectionReasons(7, 3).catch(() => ({ top: [] })),
        ])
        setTokens(tokenData)
        setConfig(configData)
        setStats({
          trades: dailyData.trades_today,
          positions: posData.length,
          avoided: avoidedData.confirmed_rugs,
          savings: avoidedData.estimated_savings_bnb,
          spent: dailyData.spent_today_bnb,
        })
        if (overrideData) setOverrides(overrideData)
        setRejectionReasons(reasonsData?.top || [])
      } catch (e) {
        console.error('Dashboard load error:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  const persona = PERSONA_LABELS[config.persona] || PERSONA_LABELS.momentum

  return (
    <div>
      {/* Header row */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{persona.icon}</span>
          <span className="font-semibold text-lg" style={{ color: persona.color }}>
            {persona.label}
          </span>
        </div>

        {/* Agent status */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-[#0ECB81] animate-pulse-glow' : 'bg-[#F6465D]'}`}
          />
          <span className="text-xs text-[var(--text-secondary)]">
            {wsConnected ? 'Scanning' : 'Disconnected'}
          </span>
        </div>

        {/* Quick stats */}
        <div className="ml-auto flex gap-4 text-sm">
          {stats.avoided > 0 && (
            <span className="text-[#0ECB81]">
              {stats.avoided} rugs avoided ({stats.savings.toFixed(3)} BNB saved)
            </span>
          )}
        </div>
      </div>

      {/* Budget bar */}
      <div className="mb-6">
        <BudgetBar
          used={stats.spent}
          max={parseFloat(config.max_per_day_bnb || 0.3)}
          trades={stats.trades}
          positions={stats.positions}
        />
      </div>

      {/* Behavioral nudge */}
      {((overrides && overrides.total_overrides > 0) || rejectionReasons.length > 0) && (
        <div className="mb-6 bg-[var(--bg-card)] rounded-xl p-4 border border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Override Summary</h3>
          {overrides && overrides.total_overrides > 0 && (
            <div className="flex flex-wrap gap-4 text-sm">
              {overrides.approved_risky > 0 && (
                <span className="text-[#F0B90B]">
                  {overrides.approved_risky} risky trade{overrides.approved_risky !== 1 ? 's' : ''} approved
                </span>
              )}
              {overrides.rejected_safe > 0 && (
                <span className="text-[var(--text-secondary)]">
                  {overrides.rejected_safe} safe trade{overrides.rejected_safe !== 1 ? 's' : ''} rejected
                </span>
              )}
              {overrides.overrides_rugged > 0 && (
                <span className="text-[#F6465D]">
                  {overrides.overrides_rugged} overridden token{overrides.overrides_rugged !== 1 ? 's' : ''} rugged
                </span>
              )}
            </div>
          )}
          {rejectionReasons.length > 0 && (
            <div className="mt-3 pt-3 border-t border-[var(--border)]">
              <p className="text-xs text-[var(--text-secondary)] mb-1.5">
                Top reject reasons (last 7 days):
              </p>
              <ul className="space-y-1 text-sm">
                {rejectionReasons.map((r, i) => (
                  <li key={i} className="text-[var(--text-primary)]">
                    <span className="text-[var(--text-secondary)]">{r.count}x</span> &mdash; {r.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Token feed */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1">
          Live Token Feed
        </h2>
        <p className="text-sm text-[var(--text-secondary)]">
          New Four.meme launches scored by risk
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">
          Loading tokens...
        </div>
      ) : tokens.length === 0 ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">
          No tokens discovered yet. Scanner is running...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tokens.map((token) => (
            <TokenCard key={token.address} token={token} />
          ))}
        </div>
      )}
    </div>
  )
}
