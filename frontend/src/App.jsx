import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { wagmiConfig } from './hooks/useWallet'
import { useWebSocket } from './hooks/useWebSocket'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import OpportunityDetail from './pages/OpportunityDetail'
import Positions from './pages/Positions'
import Avoided from './pages/Avoided'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import ChatPanel from './components/ChatPanel'
import { NotificationProvider } from './components/ToastNotifications'
import './index.css'

const queryClient = new QueryClient()

function AppContent() {
  const { messages: wsMessages, isConnected } = useWebSocket()

  return (
    <NotificationProvider wsMessages={wsMessages}>
      <div className="min-h-screen bg-[var(--bg-primary)]">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/token/:address" element={<OpportunityDetail />} />
            <Route path="/positions" element={<Positions />} />
            <Route path="/avoided" element={<Avoided />} />
            <Route path="/activity" element={<Activity />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
        <ChatPanel />
      </div>
    </NotificationProvider>
  )
}

function App() {
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </QueryClientProvider>
    </WagmiProvider>
  )
}

export default App
