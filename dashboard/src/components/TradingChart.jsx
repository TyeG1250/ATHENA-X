import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'
import { motion } from 'framer-motion'

export default function TradingChart({ symbol, agents }) {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const candleSeriesRef = useRef(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { color: '#1a1a1a' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2a2a' },
        horzLines: { color: '#2a2a2a' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#FFD700',
      },
      timeScale: {
        borderColor: '#FFD700',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    // Create candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries

    // Generate sample data (will be replaced with real data)
    const data = generateSampleData()
    candleSeries.setData(data)

    // Handle resize
    const handleResize = () => {
      chart.applyOptions({
        width: chartContainerRef.current.clientWidth,
      })
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol])

  // Update agent decision markers
  useEffect(() => {
    if (!chartRef.current || !agents) return

    // Add markers for agent decisions
    const markers = []

    if (agents.technical?.vote === 'BUY') {
      markers.push({
        time: Date.now() / 1000,
        position: 'belowBar',
        color: '#10B981',
        shape: 'arrowUp',
        text: 'Technical BUY',
      })
    } else if (agents.technical?.vote === 'SELL') {
      markers.push({
        time: Date.now() / 1000,
        position: 'aboveBar',
        color: '#EF4444',
        shape: 'arrowDown',
        text: 'Technical SELL',
      })
    }

    candleSeriesRef.current?.setMarkers(markers)
  }, [agents])

  return (
    <motion.div
      className="bg-primary-black-light border border-primary-gold/20 rounded-lg overflow-hidden"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Chart Header */}
      <div className="px-4 py-3 border-b border-primary-gold/20 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold font-mono">{symbol}</h3>
          <p className="text-sm text-gray-400">15 Minute Chart</p>
        </div>

        {/* Agent Signal Badges */}
        {agents && (
          <div className="flex space-x-2">
            {Object.entries(agents).map(([name, data]) => (
              <div
                key={name}
                className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  data.vote === 'BUY'
                    ? 'bg-success/20 text-success border border-success/50'
                    : data.vote === 'SELL'
                    ? 'bg-danger/20 text-danger border border-danger/50'
                    : 'bg-gray-700/50 text-gray-300 border border-gray-600'
                }`}
              >
                {name.toUpperCase()}: {data.vote}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chart Canvas */}
      <div ref={chartContainerRef} className="w-full" />
    </motion.div>
  )
}

function generateSampleData() {
  const data = []
  let basePrice = 1.0850
  const now = Date.now() / 1000

  for (let i = 100; i >= 0; i--) {
    const time = now - i * 15 * 60 // 15-minute candles
    const open = basePrice
    const volatility = 0.0005
    const change = (Math.random() - 0.5) * volatility
    const close = open + change
    const high = Math.max(open, close) + Math.random() * volatility
    const low = Math.min(open, close) - Math.random() * volatility

    data.push({
      time,
      open,
      high,
      low,
      close,
    })

    basePrice = close
  }

  return data
}
