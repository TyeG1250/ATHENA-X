import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  Activity, TrendingUp, TrendingDown, DollarSign,
  Database, Cpu, Zap, AlertCircle, CheckCircle,
  BarChart3, Brain, Eye, Shield
} from 'lucide-react'
import TradingChart from './components/TradingChart'
import AgentPanel from './components/AgentPanel'
import PortfolioPanel from './components/PortfolioPanel'
import SystemHealth from './components/SystemHealth'
import OrderFlow from './components/OrderFlow'
import QuestDBMonitor from './components/QuestDBMonitor'
import './index.css'

function App() {
  const [connected, setConnected] = useState(false)
  const [state, setState] = useState(null)
  const [selectedSymbol, setSelectedSymbol] = useState('EUR_USD')
  const wsRef = useRef(null)

  useEffect(() => {
    // Connect to WebSocket server
    const ws = new WebSocket('ws://localhost:8765/ws')
    wsRef.current = ws

    ws.onopen = () => {
      console.log('🟢 Connected to ATHENA-X')
      setConnected(true)

      // Subscribe to symbol data
      ws.send(JSON.stringify({
        type: 'subscribe_symbol',
        symbol: selectedSymbol
      }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'state_update') {
        setState(data)
      } else if (data.type === 'historical_data') {
        // Handle historical chart data
        console.log(`📊 Received ${data.candles.length} candles for ${data.symbol}`)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnected(false)
    }

    ws.onclose = () => {
      console.log('🔴 Disconnected from ATHENA-X')
      setConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [selectedSymbol])

  const symbols = [
    'EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF',
    'AUD_USD', 'NZD_USD', 'USD_CAD', 'XAU_USD'
  ]

  return (
    <div className="min-h-screen bg-primary-black text-white font-sans">
      {/* Header */}
      <header className="bg-primary-black-light border-b border-primary-gold/20">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Zap className="w-8 h-8 text-primary-gold" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-gold to-primary-gold-light bg-clip-text text-transparent">
                ATHENA-X
              </h1>
            </div>
            <div className="h-6 w-px bg-primary-gold/30" />
            <span className="text-sm text-gray-400">Institutional Trading System</span>
          </div>

          {/* Connection Status */}
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              {connected ? (
                <>
                  <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
                  <span className="text-sm text-success">LIVE</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-danger rounded-full" />
                  <span className="text-sm text-danger">DISCONNECTED</span>
                </>
              )}
            </div>

            {state && (
              <div className="text-sm font-mono text-gray-400">
                {new Date(state.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Dashboard Grid */}
      <div className="p-4 grid grid-cols-12 gap-4">
        {/* Left Sidebar - Portfolio & Positions */}
        <div className="col-span-3 space-y-4">
          <PortfolioPanel portfolio={state?.portfolio} />

          {/* Positions */}
          <motion.div
            className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-primary-gold" />
              Open Positions
            </h3>
            <div className="space-y-2">
              {state?.positions?.map((pos, idx) => (
                <div key={idx} className="bg-primary-black-lighter border border-primary-gold/10 rounded p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono font-semibold">{pos.symbol}</span>
                    <span className={`text-sm font-semibold ${pos.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toFixed(2)} USD
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <div>Side: <span className="text-white">{pos.side.toUpperCase()}</span></div>
                    <div>Units: <span className="text-white">{pos.units.toLocaleString()}</span></div>
                    <div>Entry: <span className="text-white">{pos.entry_price}</span></div>
                    <div>Current: <span className="text-white">{pos.current_price}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Agent Panel */}
          <AgentPanel agents={state?.agents} />
        </div>

        {/* Center - Main Chart */}
        <div className="col-span-6 space-y-4">
          {/* Symbol Selector */}
          <div className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-2">
            <div className="flex space-x-2 overflow-x-auto">
              {symbols.map(symbol => (
                <button
                  key={symbol}
                  onClick={() => setSelectedSymbol(symbol)}
                  className={`px-4 py-2 rounded font-mono text-sm transition-all ${
                    selectedSymbol === symbol
                      ? 'bg-primary-gold text-primary-black font-semibold'
                      : 'bg-primary-black-lighter text-gray-400 hover:text-white'
                  }`}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>

          {/* Main Trading Chart */}
          <TradingChart symbol={selectedSymbol} agents={state?.agents} />

          {/* Order Flow */}
          <OrderFlow symbol={selectedSymbol} />
        </div>

        {/* Right Sidebar - System Monitoring */}
        <div className="col-span-3 space-y-4">
          <SystemHealth system={state?.system} />
          <QuestDBMonitor />

          {/* Redis Monitor */}
          <motion.div
            className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <Database className="w-5 h-5 mr-2 text-primary-gold" />
              Redis Cache
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Hit Rate</span>
                <span className="font-mono text-success">94.2%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Keys</span>
                <span className="font-mono">1,247</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Memory</span>
                <span className="font-mono">45.2 MB</span>
              </div>
            </div>
          </motion.div>

          {/* Data Pipeline Status */}
          <motion.div
            className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-primary-gold" />
              Data Pipeline
            </h3>
            <div className="space-y-3">
              {[
                { name: 'OANDA', status: 'healthy', latency: '12ms' },
                { name: 'TradingView', status: 'healthy', latency: '45ms' },
                { name: 'News API', status: 'degraded', latency: '230ms' },
                { name: 'Reddit', status: 'offline', latency: '-' },
              ].map((source, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-2">
                    {source.status === 'healthy' ? (
                      <CheckCircle className="w-4 h-4 text-success" />
                    ) : source.status === 'degraded' ? (
                      <AlertCircle className="w-4 h-4 text-warning" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-danger" />
                    )}
                    <span>{source.name}</span>
                  </div>
                  <span className="font-mono text-gray-400">{source.latency}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

export default App
