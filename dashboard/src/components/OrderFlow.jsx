import { motion } from 'framer-motion'
import { BarChart3 } from 'lucide-react'

export default function OrderFlow({ symbol }) {
  // Sample volume profile data
  const volumeData = [
    { price: '1.0900', buyVol: 1200, sellVol: 800 },
    { price: '1.0895', buyVol: 900, sellVol: 1100 },
    { price: '1.0890', buyVol: 1500, sellVol: 700 },
    { price: '1.0885', buyVol: 800, sellVol: 1300 },
    { price: '1.0880', buyVol: 2000, sellVol: 600 },
    { price: '1.0875', buyVol: 1100, sellVol: 900 },
    { price: '1.0870', buyVol: 700, sellVol: 1400 },
    { price: '1.0865', buyVol: 1300, sellVol: 1100 },
  ]

  const maxVolume = Math.max(...volumeData.flatMap(d => [d.buyVol, d.sellVol]))

  return (
    <motion.div
      className="bg-primary-black-light border border-primary-gold/20 rounded-lg p-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <BarChart3 className="w-5 h-5 mr-2 text-primary-gold" />
        Order Flow - {symbol}
      </h3>

      <div className="space-y-1">
        {volumeData.map((row, idx) => (
          <div key={idx} className="flex items-center space-x-2">
            {/* Price */}
            <div className="w-16 text-xs font-mono text-gray-400">
              {row.price}
            </div>

            {/* Buy Volume Bar */}
            <div className="flex-1 flex justify-end">
              <div
                className="h-5 bg-success/30 border border-success/50 rounded-l transition-all"
                style={{ width: `${(row.buyVol / maxVolume) * 100}%` }}
              >
                <span className="text-xs font-mono text-success px-1">
                  {row.buyVol > 1000 ? row.buyVol.toLocaleString() : ''}
                </span>
              </div>
            </div>

            {/* Sell Volume Bar */}
            <div className="flex-1">
              <div
                className="h-5 bg-danger/30 border border-danger/50 rounded-r transition-all"
                style={{ width: `${(row.sellVol / maxVolume) * 100}%` }}
              >
                <span className="text-xs font-mono text-danger px-1">
                  {row.sellVol > 1000 ? row.sellVol.toLocaleString() : ''}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-primary-gold/10 flex items-center justify-center space-x-6 text-xs">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-success/30 border border-success/50 rounded" />
          <span className="text-gray-400">Buy Volume</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-danger/30 border border-danger/50 rounded" />
          <span className="text-gray-400">Sell Volume</span>
        </div>
      </div>
    </motion.div>
  )
}
