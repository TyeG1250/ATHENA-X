import { motion } from 'framer-motion'
import { Database, Activity } from 'lucide-react'

export default function QuestDBMonitor() {
  return (
    <motion.div
      className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <Database className="w-5 h-5 mr-2 text-primary-gold" />
        QuestDB
      </h3>

      <div className="space-y-3">
        {/* Row Count */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Total Candles</span>
          <span className="font-mono text-sm font-semibold">2,847,392</span>
        </div>

        {/* Ingest Rate */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Ingest Rate</span>
          <div className="flex items-center space-x-1">
            <Activity className="w-3 h-3 text-success" />
            <span className="font-mono text-sm text-success">145 rows/s</span>
          </div>
        </div>

        {/* Query Performance */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Avg Query Time</span>
          <span className="font-mono text-sm">18ms</span>
        </div>

        {/* Storage */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Disk Usage</span>
          <span className="font-mono text-sm">4.2 GB</span>
        </div>

        {/* Partition Info */}
        <div className="pt-3 border-t border-primary-gold/10">
          <div className="text-xs text-gray-400 mb-2">Active Partitions</div>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="font-mono">2025-11-18</span>
              <span className="text-gray-400">247K rows</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="font-mono">2025-11-17</span>
              <span className="text-gray-400">196K rows</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
