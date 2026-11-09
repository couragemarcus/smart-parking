/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      keyframes: {
        'blink-green': {
          '0%, 100%': { boxShadow: '0 0 0 4px #22c55e, 0 0 16px 4px #22c55e' },
          '50%': { boxShadow: '0 0 0 4px transparent, 0 0 0 4px transparent' },
        },
      },
      animation: {
        'blink-green': 'blink-green 1s ease-in-out infinite',
      },
      colors: {
        parking: {
          available: '#22c55e',
          reserved: '#f59e0b',
          occupied: '#ef4444',
          oos: '#6b7280',
        },
      },
    },
  },
  plugins: [],
}
