import { useEffect, useState } from 'react'

const BUY_PRESETS = [0.005, 0.01, 0.02, 0.05]
const SELL_PRESETS = [25, 50, 100]

/**
 * Confirm-trade modal.
 * mode="buy"  → prompts for BNB amount (preset chips + custom input, clamped min/max).
 * mode="sell" → prompts for percentage of holdings (25 / 50 / 100 presets + custom %).
 *
 * onConfirm receives:
 *   buy  → { amount_bnb: number }
 *   sell → { sell_fraction: number }  (0 < f <= 1)
 */
export default function ConfirmTradeModal({
  open,
  mode,
  label,
  defaultAmountBnb = 0.01,
  minBnb = 0.002,
  maxBnb = 0.05,
  onConfirm,
  onCancel,
}) {
  const [amount, setAmount] = useState(String(defaultAmountBnb))
  const [pct, setPct] = useState(100)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      setAmount(String(defaultAmountBnb))
      setPct(100)
      setSubmitting(false)
    }
  }, [open, defaultAmountBnb])

  if (!open) return null

  const isBuy = mode === 'buy'
  const amountNum = parseFloat(amount)
  const amountValid = !isNaN(amountNum) && amountNum >= minBnb && amountNum <= maxBnb
  const pctValid = pct > 0 && pct <= 100

  const handleConfirm = async () => {
    setSubmitting(true)
    try {
      if (isBuy) {
        await onConfirm({ amount_bnb: parseFloat(amountNum.toFixed(6)) })
      } else {
        await onConfirm({ sell_fraction: Math.min(1, pct / 100) })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 w-full max-w-md"
      >
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">
          {isBuy ? 'Confirm Buy' : 'Confirm Sell'}
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mb-5 truncate">{label}</p>

        {isBuy ? (
          <>
            <div className="text-xs text-[var(--text-secondary)] mb-2">Amount (BNB)</div>
            <div className="flex gap-2 mb-3 flex-wrap">
              {BUY_PRESETS.filter((p) => p >= minBnb && p <= maxBnb).map((p) => (
                <button
                  key={p}
                  onClick={() => setAmount(String(p))}
                  className={`px-3 py-1.5 text-sm rounded cursor-pointer border ${
                    parseFloat(amount) === p
                      ? 'bg-[var(--accent-gold)] text-black border-[var(--accent-gold)]'
                      : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] border-[var(--border)] hover:border-[var(--accent-gold)]'
                  }`}
                >
                  {p} BNB
                </button>
              ))}
            </div>
            <input
              type="number"
              step="0.001"
              min={minBnb}
              max={maxBnb}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent-gold)]"
            />
            <div className="text-xs text-[var(--text-secondary)] mt-2">
              Between {minBnb} and {maxBnb} BNB
            </div>
          </>
        ) : (
          <>
            <div className="text-xs text-[var(--text-secondary)] mb-2">Sell percentage</div>
            <div className="flex gap-2 mb-3">
              {SELL_PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPct(p)}
                  className={`flex-1 px-3 py-1.5 text-sm rounded cursor-pointer border ${
                    pct === p
                      ? 'bg-[#F6465D] text-white border-[#F6465D]'
                      : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] border-[var(--border)] hover:border-[#F6465D]'
                  }`}
                >
                  {p}%
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="1"
                min="1"
                max="100"
                value={pct}
                onChange={(e) => setPct(parseFloat(e.target.value) || 0)}
                className="flex-1 px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-[var(--text-primary)] text-sm focus:outline-none focus:border-[#F6465D]"
              />
              <span className="text-sm text-[var(--text-secondary)]">%</span>
            </div>
            <div className="text-xs text-[var(--text-secondary)] mt-2">
              Between 1 and 100% of your current holdings
            </div>
          </>
        )}

        <div className="flex gap-2 justify-end mt-6">
          <button
            onClick={onCancel}
            disabled={submitting}
            className="px-4 py-2 text-sm rounded cursor-pointer bg-[var(--bg-secondary)] text-[var(--text-secondary)] border border-[var(--border)] hover:text-[var(--text-primary)] disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={submitting || (isBuy ? !amountValid : !pctValid)}
            className={`px-4 py-2 text-sm font-semibold rounded cursor-pointer disabled:opacity-50 ${
              isBuy ? 'bg-[#0ECB81] text-black' : 'bg-[#F6465D] text-white'
            }`}
          >
            {submitting ? 'Submitting...' : isBuy ? 'Buy' : 'Sell'}
          </button>
        </div>
      </div>
    </div>
  )
}
