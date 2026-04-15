import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const NotificationContext = createContext()

export function useNotifications() {
  return useContext(NotificationContext)
}

const EVENT_CONFIG = {
  trade_executed: (data) => ({
    type: data.side === 'buy' ? 'success' : 'info',
    title: data.side === 'buy' ? 'Trade Executed' : 'Position Sold',
    message: data.side === 'buy'
      ? `Bought ${data.token_address?.slice(0, 10)}... for ${data.amount_bnb} BNB`
      : `Sold ${data.token_address?.slice(0, 10)}... PnL: ${data.pnl_bnb?.toFixed(6) || '?'} BNB`,
  }),
  action_proposed: (data) => ({
    type: 'warning',
    title: `${data.action_type === 'buy' ? 'Buy' : 'Sell'} Proposed`,
    message: data.rationale?.slice(0, 80) || `${data.token_address?.slice(0, 10)}...`,
  }),
  risk_alert: (data) => ({
    type: data.new_grade === 'red' ? 'error' : 'warning',
    title: 'Risk Grade Changed',
    message: `${data.address?.slice(0, 10)}... ${data.old_grade?.toUpperCase()} → ${data.new_grade?.toUpperCase()}`,
  }),
  position_update: (data) => {
    if (!data.pnl_bnb || !data.entry_amount_bnb) return null
    const pnlPct = (data.pnl_bnb / data.entry_amount_bnb) * 100
    if (pnlPct >= 100) return { type: 'success', title: '2x Profit!', message: `${data.token_address?.slice(0, 10)}... is up ${pnlPct.toFixed(0)}%` }
    if (pnlPct >= 50) return { type: 'info', title: 'Position Up 50%+', message: `${data.token_address?.slice(0, 10)}... PnL: +${pnlPct.toFixed(0)}%` }
    if (pnlPct <= -40) return { type: 'error', title: 'Position Down', message: `${data.token_address?.slice(0, 10)}... PnL: ${pnlPct.toFixed(0)}%` }
    return null
  },
}

export function NotificationProvider({ children, wsMessages }) {
  const [toasts, setToasts] = useState([])
  const processedRef = useRef(0)

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { ...toast, id }].slice(-5))
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 5000)
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  useEffect(() => {
    if (!wsMessages || wsMessages.length === 0) return
    if (wsMessages.length === processedRef.current) return

    // Process new messages (wsMessages is newest-first)
    const newCount = wsMessages.length - processedRef.current
    const newMessages = wsMessages.slice(0, newCount)
    processedRef.current = wsMessages.length

    for (const msg of newMessages) {
      const handler = EVENT_CONFIG[msg.type]
      if (handler) {
        const toast = handler(msg.data)
        if (toast) addToast(toast)
      }
    }
  }, [wsMessages, addToast])

  return (
    <NotificationContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed top-16 right-4 z-[100] space-y-2 w-80 pointer-events-none">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={() => dismissToast(toast.id)} />
        ))}
      </div>
    </NotificationContext.Provider>
  )
}

const COLORS = {
  success: 'border-l-[#0ECB81] bg-[rgba(14,203,129,0.1)]',
  warning: 'border-l-[#F0B90B] bg-[rgba(240,185,11,0.1)]',
  error: 'border-l-[#F6465D] bg-[rgba(246,70,93,0.1)]',
  info: 'border-l-[#848E9C] bg-[rgba(132,142,156,0.1)]',
}

function ToastItem({ toast, onDismiss }) {
  return (
    <div
      className={`pointer-events-auto border-l-4 ${COLORS[toast.type]} bg-[var(--bg-card)] rounded-lg p-3 shadow-xl cursor-pointer border border-[var(--border)] animate-[slideIn_0.3s_ease-out]`}
      onClick={onDismiss}
    >
      <div className="flex justify-between items-start">
        <div className="min-w-0">
          <div className="text-sm font-medium text-[var(--text-primary)]">{toast.title}</div>
          <div className="text-xs text-[var(--text-secondary)] mt-0.5 truncate">{toast.message}</div>
        </div>
        <button className="text-[var(--text-secondary)] text-sm ml-2 flex-shrink-0">&times;</button>
      </div>
    </div>
  )
}
