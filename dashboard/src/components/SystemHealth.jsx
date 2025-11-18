import { motion } from 'framer-motion'
import { Cpu, Activity, Zap } from 'lucide-react'

export default function SystemHealth({ system }) {
  if (!system) return null

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  return (
    <motion.div
      className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Cpu className="w-5 h-5 mr-2 text-primary-gold" />
        System Health
      </h3>

      <div className="space-y-3">
        {/* Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Status</span>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
            <span className="font-mono text-success font-semibold">{system.status}</span>
          </div>
        </div>

        {/* Uptime */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Uptime</span>
          <span className="font-mono text-sm">{formatUptime(system.uptime)}</span>
        </div>

        {/* Loop Count */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Trading Cycles</span>
          <span className="font-mono text-sm">{system.loop_count}</span>
        </div>

        {/* CPU/Memory */}
        <div className="pt-2 border-t border-primary-gold/10">
          <div className="mb-2">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>CPU Usage</span>
              <span className="font-mono">34.2%</span>
            </div>
            <div className="h-2 bg-primary-black rounded-full overflow-hidden">
              <div className="h-full w-[34%] bg-gradient-to-r from-success/80 to-success" />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Memory Usage</span>
              <span className="font-mono">2.8 / 24 GB</span>
            </div>
            <div className="h-2 bg-primary-black rounded-full overflow-hidden">
              <div className="h-full w-[12%] bg-gradient-to-r from-primary-gold/80 to-primary-gold" />
            </div>
          </div>
        </div>

        {/* GPU */}
        <div className="pt-2 border-t border-primary-gold/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">GPU (RTX 3080)</span>
            <span className="text-xs text-success">ACTIVE</span>
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>VRAM</span>
              <span className="font-mono">3.2 / 10 GB</span>
            </div>
            <div className="h-2 bg-primary-black rounded-full overflow-hidden">
              <div className="h-full w-[32%] bg-gradient-to-r from-info/80 to-info" />
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
