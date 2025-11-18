import { motion } from 'framer-motion'
import { DollarSign, TrendingUp, TrendingDown } from 'lucide-react'

export default function PortfolioPanel({ portfolio }) {
  if (!portfolio) return null

  const pnlPositive = portfolio.pnl_today >= 0

  return (
    <motion.div
      className="bg-gradient-to-br from-primary-black-light to-primary-black-lighter border-2 border-primary-gold/30 rounded-lg p-4 shadow-gold-glow"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Total Equity */}
      <div className="mb-4">
        <div className="flex items-center space-x-2 mb-1">
          <DollarSign className="w-5 h-5 text-primary-gold" />
          <span className="text-sm text-gray-400">Total Equity</span>
        </div>
        <div className="text-3xl font-bold font-mono text-white">
          ${portfolio.equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      {/* P&L Today */}
      <div className="mb-4 p-3 bg-primary-black rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">P&L Today</span>
          <div className={`flex items-center space-x-1 ${pnlPositive ? 'text-success' : 'text-danger'}`}>
            {pnlPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            <span className="font-mono font-semibold">
              {pnlPositive ? '+' : ''}${Math.abs(portfolio.pnl_today).toFixed(2)}
            </span>
            <span className="text-xs">
              ({pnlPositive ? '+' : ''}{portfolio.pnl_percent.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-primary-black rounded p-2">
          <div className="text-xs text-gray-400 mb-1">Balance</div>
          <div className="font-mono text-sm font-semibold">
            ${portfolio.balance.toLocaleString()}
          </div>
        </div>

        <div className="bg-primary-black rounded p-2">
          <div className="text-xs text-gray-400 mb-1">Margin Used</div>
          <div className="font-mono text-sm font-semibold">
            ${portfolio.margin_used.toLocaleString()}
          </div>
        </div>

        <div className="bg-primary-black rounded p-2 col-span-2">
          <div className="text-xs text-gray-400 mb-1">Available Margin</div>
          <div className="font-mono text-sm font-semibold">
            ${portfolio.margin_available.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>

      {/* Margin Usage Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Margin Utilization</span>
          <span className="font-mono">
            {((portfolio.margin_used / portfolio.equity) * 100).toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-primary-black rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary-gold-dark to-primary-gold"
            initial={{ width: 0 }}
            animate={{ width: `${(portfolio.margin_used / portfolio.equity) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    </motion.div>
  )
}
