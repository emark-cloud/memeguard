import { Link, useLocation } from 'react-router-dom'
import { useWallet } from '../hooks/useWallet'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/positions', label: 'Positions' },
  { path: '/avoided', label: 'Avoided' },
  { path: '/activity', label: 'Activity' },
  { path: '/settings', label: 'Settings' },
]

export default function Navbar() {
  const { address, isConnected, connect, disconnect } = useWallet()
  const location = useLocation()

  return (
    <nav className="bg-[var(--bg-secondary)] border-b border-[var(--border)] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 no-underline">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-gold)] flex items-center justify-center text-black font-bold text-sm">
            FS
          </div>
          <span className="text-[var(--text-primary)] font-semibold text-lg hidden sm:inline">
            FourScout
          </span>
        </Link>

        {/* Nav Links */}
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={`px-3 py-1.5 rounded text-sm no-underline transition-colors ${
                location.pathname === path
                  ? 'bg-[var(--bg-card)] text-[var(--accent-gold)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Wallet */}
        {isConnected && address ? (
          <button
            onClick={disconnect}
            className="bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm cursor-pointer hover:bg-[var(--bg-hover)] transition-colors"
          >
            {address.slice(0, 6)}...{address.slice(-4)}
          </button>
        ) : (
          <button
            onClick={connect}
            className="bg-[var(--accent-gold)] text-black font-semibold rounded-lg px-4 py-1.5 text-sm cursor-pointer hover:opacity-90 transition-opacity"
          >
            Connect Wallet
          </button>
        )}
      </div>
    </nav>
  )
}
