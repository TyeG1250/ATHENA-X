import { motion } from 'framer-motion'
import { Brain, Eye, Shield, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const agentIcons = {
  technical: Brain,
  sentiment: Eye,
  risk: Shield,
}

const voteColors = {
  BUY: 'text-success',
  SELL: 'text-danger',
  HOLD: 'text-gray-400',
  NEUTRAL: 'text-gray-400',
}

const voteIcons = {
  BUY: TrendingUp,
  SELL: TrendingDown,
  HOLD: Minus,
  NEUTRAL: Minus,
}

export default function AgentPanel({ agents }) {
  if (!agents) return null

  return (
    <motion.div
      className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Brain className="w-5 h-5 mr-2 text-primary-gold" />
        Agent Consensus
      </h3>

      <div className="space-y-3">
        {Object.entries(agents).map(([name, data]) => {
          const Icon = agentIcons[name] || Brain
          const VoteIcon = voteIcons[data.vote] || Minus
          const voteColor = voteColors[data.vote] || 'text-gray-400'

          return (
            <div
              key={name}
              className="bg-primary-black-lighter border border-primary-gold/10 rounded-lg p-3"
            >
              {/* Agent Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Icon className="w-4 h-4 text-primary-gold" />
                  <span className="font-semibold capitalize">{name}</span>
                </div>
                <div className={`flex items-center space-x-1 font-mono font-semibold ${voteColor}`}>
                  <VoteIcon className="w-4 h-4" />
                  <span>{data.vote}</span>
                </div>
              </div>

              {/* Confidence Bar */}
              <div className="mb-2">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Confidence</span>
                  <span className="font-mono">{(data.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-primary-black rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-primary-gold-dark to-primary-gold"
                    initial={{ width: 0 }}
                    animate={{ width: `${data.confidence * 100}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                </div>
              </div>

              {/* Additional Data */}
              {data.signals && (
                <div className="flex flex-wrap gap-1">
                  {data.signals.map((signal, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-primary-gold/10 text-primary-gold text-xs rounded-full font-mono"
                    >
                      {signal}
                    </span>
                  ))}
                </div>
              )}

              {data.score !== undefined && (
                <div className="text-xs text-gray-400 mt-2">
                  Sentiment Score: <span className="text-white font-mono">{data.score.toFixed(2)}</span>
                </div>
              )}

              {data.exposure !== undefined && (
                <div className="text-xs text-gray-400 mt-2">
                  Risk Exposure: <span className="text-white font-mono">{(data.exposure * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Consensus Vote */}
      <div className="mt-4 p-3 bg-primary-black-lighter border-2 border-primary-gold/30 rounded-lg">
        <div className="text-center">
          <div className="text-sm text-gray-400 mb-1">Final Decision</div>
          <div className="text-2xl font-bold text-primary-gold font-mono">
            ANALYZING...
          </div>
        </div>
      </div>
    </motion.div>
  )
}
