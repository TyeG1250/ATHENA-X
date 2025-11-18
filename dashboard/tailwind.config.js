/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Black & Gold Theme
        primary: {
          black: '#0a0a0a',
          'black-light': '#1a1a1a',
          'black-lighter': '#2a2a2a',
          gold: '#FFD700',
          'gold-dark': '#DAA520',
          'gold-light': '#FFED4E',
        },
        success: '#10B981',
        danger: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'gold-glow': '0 0 20px rgba(255, 215, 0, 0.3)',
        'gold-glow-lg': '0 0 40px rgba(255, 215, 0, 0.5)',
      },
      animation: {
        'pulse-gold': 'pulse-gold 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up': 'slide-up 0.3s ease-out',
      },
      keyframes: {
        'pulse-gold': {
          '0%, 100%': {
            opacity: 1,
            boxShadow: '0 0 20px rgba(255, 215, 0, 0.3)'
          },
          '50%': {
            opacity: 0.8,
            boxShadow: '0 0 40px rgba(255, 215, 0, 0.6)'
          },
        },
        'slide-up': {
          '0%': {
            transform: 'translateY(20px)',
            opacity: 0
          },
          '100%': {
            transform: 'translateY(0)',
            opacity: 1
          },
        },
      },
    },
  },
  plugins: [],
}
