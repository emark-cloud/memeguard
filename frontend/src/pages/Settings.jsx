import { useState, useEffect } from 'react'
import PersonaSelector from '../components/PersonaSelector'
import { getConfig, updateConfig, updateConfigBulk, getAgentStatus, registerAgent, getWatchlist, addWatchlistItem, removeWatchlistItem } from '../services/api'

const APPROVAL_MODES = [
  { id: 'approve_each', label: 'Approve Each', desc: 'Every trade requires explicit approval' },
  { id: 'approve_per_session', label: 'Per Session', desc: 'First trade approved, rest auto-execute' },
  { id: 'budget_threshold', label: 'Budget Threshold', desc: 'Auto under threshold, approve above' },
  { id: 'monitor_only', label: 'Monitor Only', desc: 'No trades, recommendations only' },
]

export default function Settings() {
  const [config, setConfig] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Agent identity state
  const [agentStatus, setAgentStatus] = useState(null)
  const [registering, setRegistering] = useState(false)
  const [registerError, setRegisterError] = useState(null)
  const [agentName, setAgentName] = useState('FourScout Agent')

  // Watchlist state
  const [watchlist, setWatchlist] = useState([])
  const [watchInput, setWatchInput] = useState('')
  const [watchType, setWatchType] = useState('creator')
  const [watchLabel, setWatchLabel] = useState('')

  useEffect(() => {
    getConfig().then(setConfig).catch(console.error)
    getAgentStatus().then(setAgentStatus).catch(console.error)
    getWatchlist().then(setWatchlist).catch(console.error)
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await updateConfigBulk(config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      console.error('Save error:', e)
      setSaveError('Failed to save settings. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleRegister = async () => {
    setRegistering(true)
    setRegisterError(null)
    try {
      await registerAgent(agentName, null, 'FourScout AI trading agent on Four.meme')
      const status = await getAgentStatus()
      setAgentStatus(status)
    } catch (e) {
      console.error('Register error:', e)
      setRegisterError('Registration failed. Check wallet balance and try again.')
    } finally {
      setRegistering(false)
    }
  }

  const handleAddWatch = async () => {
    if (!watchInput.trim()) return
    try {
      await addWatchlistItem({ item_type: watchType, value: watchInput.trim(), label: watchLabel.trim() })
      setWatchInput('')
      setWatchLabel('')
      const items = await getWatchlist()
      setWatchlist(items)
    } catch (e) {
      console.error('Add watchlist error:', e)
    }
  }

  const handleRemoveWatch = async (id) => {
    try {
      await removeWatchlistItem(id)
      setWatchlist((prev) => prev.filter((item) => item.id !== id))
    } catch (e) {
      console.error('Remove watchlist error:', e)
    }
  }

  const update = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-xl font-bold text-[var(--text-primary)] mb-6">Settings</h1>

      {/* Agent Identity (ERC-8004) */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Agent Identity (ERC-8004)</h2>
        <div className="bg-[var(--bg-card)] rounded-xl p-4 space-y-3">
          {agentStatus ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Wallet</span>
                <span className="text-sm font-mono text-[var(--text-primary)]">
                  {agentStatus.wallet_address
                    ? `${agentStatus.wallet_address.slice(0, 6)}...${agentStatus.wallet_address.slice(-4)}`
                    : 'No key configured'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">BNB Balance</span>
                <span className="text-sm text-[var(--text-primary)]">
                  {agentStatus.bnb_balance ?? '—'} BNB
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Status</span>
                {agentStatus.is_registered ? (
                  <a
                    href={
                      agentStatus.erc8004_token_id != null
                        ? `https://8004scan.io/agents/bsc/${agentStatus.erc8004_token_id}`
                        : `https://8004scan.io/agents?search=${agentStatus.wallet_address}`
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    title="View on 8004scan"
                    className="text-xs px-2 py-0.5 rounded bg-[rgba(14,203,129,0.15)] text-[#0ECB81] font-medium no-underline hover:bg-[rgba(14,203,129,0.25)]"
                  >
                    REGISTERED ↗
                  </a>
                ) : (
                  <span className="text-xs px-2 py-0.5 rounded bg-[rgba(246,70,93,0.15)] text-[#F6465D] font-medium">
                    NOT REGISTERED
                  </span>
                )}
              </div>
              {!agentStatus.is_registered && agentStatus.has_private_key && (
                <div className="pt-2 space-y-2">
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    placeholder="Agent name"
                    className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-gold)]"
                  />
                  {registerError && <p className="text-[#F6465D] text-xs">{registerError}</p>}
                  <button
                    onClick={handleRegister}
                    disabled={registering || !agentName.trim()}
                    className="w-full bg-[var(--accent-gold)] text-black font-semibold py-2 rounded-lg cursor-pointer hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
                  >
                    {registering ? 'Registering on-chain...' : 'Register as AI Agent (ERC-8004)'}
                  </button>
                  <p className="text-xs text-[var(--text-secondary)] opacity-60">
                    Registers your wallet on the BRC-8004 Identity Registry, enabling access to AI Agent Mode token launches.
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-[var(--text-secondary)]">Loading agent status...</div>
          )}
        </div>
      </section>

      {/* Persona */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Trading Persona</h2>
        <PersonaSelector
          selected={config.persona}
          onSelect={(id) => update('persona', id)}
        />
      </section>

      {/* Approval Mode */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Approval Mode</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {APPROVAL_MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => update('approval_mode', mode.id)}
              className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                config.approval_mode === mode.id
                  ? 'border-[var(--accent-gold)] bg-[rgba(240,185,11,0.08)]'
                  : 'border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--bg-hover)]'
              }`}
            >
              <div className="font-medium text-sm text-[var(--text-primary)]">{mode.label}</div>
              <div className="text-xs text-[var(--text-secondary)] mt-0.5">{mode.desc}</div>
            </button>
          ))}
        </div>
      </section>

      {/* Exit Strategy */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Exit Strategy</h2>
        <div className="bg-[var(--bg-card)] rounded-xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm text-[var(--text-secondary)]">Take profit (%)</label>
            <input
              type="number"
              step="10"
              min="10"
              value={config.take_profit_pct || ''}
              onChange={(e) => update('take_profit_pct', e.target.value)}
              className="w-32 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] text-right outline-none focus:border-[var(--accent-gold)]"
            />
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm text-[var(--text-secondary)]">Stop loss (%)</label>
            <input
              type="number"
              step="5"
              min="-100"
              max="0"
              value={config.stop_loss_pct || ''}
              onChange={(e) => update('stop_loss_pct', e.target.value)}
              className="w-32 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] text-right outline-none focus:border-[var(--accent-gold)]"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm text-[var(--text-secondary)]">Auto-sell at thresholds</label>
              <p className="text-xs text-[var(--text-secondary)] opacity-60 mt-0.5">
                Automatically execute sells when take-profit or stop-loss is hit
              </p>
            </div>
            <button
              onClick={() => update('auto_sell_enabled', config.auto_sell_enabled === 'true' ? 'false' : 'true')}
              className={`w-11 h-6 rounded-full relative transition-colors cursor-pointer ${
                config.auto_sell_enabled === 'true' ? 'bg-[#0ECB81]' : 'bg-[var(--bg-secondary)]'
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                  config.auto_sell_enabled === 'true' ? 'translate-x-5' : ''
                }`}
              />
            </button>
          </div>
        </div>
      </section>

      {/* Budget Caps */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Budget Caps</h2>
        <div className="bg-[var(--bg-card)] rounded-xl p-4 space-y-4">
          {[
            { key: 'max_per_trade_bnb', label: 'Max per trade (BNB)', type: 'number', step: '0.01' },
            { key: 'max_per_day_bnb', label: 'Max per day (BNB)', type: 'number', step: '0.1' },
            { key: 'max_active_positions', label: 'Max active positions', type: 'number', step: '1' },
            { key: 'max_slippage_pct', label: 'Max slippage (%)', type: 'number', step: '0.5' },
            { key: 'cooldown_seconds', label: 'Cooldown (seconds)', type: 'number', step: '10' },
            { key: 'min_liquidity_usd', label: 'Min liquidity (USD)', type: 'number', step: '100' },
          ].map(({ key, label, type, step }) => (
            <div key={key} className="flex items-center justify-between">
              <label className="text-sm text-[var(--text-secondary)]">{label}</label>
              <input
                type={type}
                step={step}
                min="0"
                value={config[key] || ''}
                onChange={(e) => update(key, e.target.value)}
                className="w-32 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] text-right outline-none focus:border-[var(--accent-gold)]"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Watchlist */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Watchlist</h2>
        <div className="bg-[var(--bg-card)] rounded-xl p-4 space-y-3">
          <div className="flex gap-2">
            <select
              value={watchType}
              onChange={(e) => setWatchType(e.target.value)}
              className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-2 py-1.5 text-sm text-[var(--text-primary)] outline-none"
            >
              <option value="creator">Creator</option>
              <option value="token">Token</option>
            </select>
            <input
              type="text"
              value={watchInput}
              onChange={(e) => setWatchInput(e.target.value)}
              placeholder={watchType === 'creator' ? '0x... creator address' : '0x... token address'}
              className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-gold)] font-mono"
            />
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={watchLabel}
              onChange={(e) => setWatchLabel(e.target.value)}
              placeholder="Label (optional)"
              className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-gold)]"
            />
            <button
              onClick={handleAddWatch}
              disabled={!watchInput.trim()}
              className="bg-[var(--accent-gold)] text-black font-semibold px-4 py-1.5 rounded text-sm cursor-pointer hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              Add
            </button>
          </div>
          {watchlist.length > 0 ? (
            <div className="space-y-2 pt-1">
              {watchlist.map((item) => (
                <div key={item.id} className="flex items-center justify-between bg-[var(--bg-secondary)] rounded-lg px-3 py-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[rgba(240,185,11,0.15)] text-[var(--accent-gold)] font-medium uppercase">
                        {item.item_type}
                      </span>
                      {item.label && <span className="text-sm text-[var(--text-primary)]">{item.label}</span>}
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] font-mono truncate mt-0.5">{item.value}</p>
                  </div>
                  <button
                    onClick={() => handleRemoveWatch(item.id)}
                    className="text-[var(--text-secondary)] hover:text-[#F6465D] text-lg ml-2 cursor-pointer transition-colors flex-shrink-0"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[var(--text-secondary)] opacity-60">
              No items on watchlist. Add creator or token addresses to prioritize scanning.
            </p>
          )}
        </div>
      </section>

      {/* Error message */}
      {saveError && (
        <p className="text-[#F6465D] text-sm mb-3">{saveError}</p>
      )}

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full bg-[var(--accent-gold)] text-black font-semibold py-3 rounded-xl cursor-pointer hover:opacity-90 disabled:opacity-50 transition-opacity"
      >
        {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
      </button>
    </div>
  )
}
