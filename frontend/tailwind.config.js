/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        focused: '#22c55e',
        partial: '#eab308',
        distracted: '#f97316',
        drowsy: '#ef4444',
      },
      keyframes: {
        'bounce-in': {
          '0%':   { transform: 'scale(0.6) translateY(-20px)', opacity: '0' },
          '60%':  { transform: 'scale(1.08) translateY(4px)',  opacity: '1' },
          '100%': { transform: 'scale(1) translateY(0)',       opacity: '1' },
        },
      },
      animation: {
        'bounce-in': 'bounce-in 0.5s ease-out',
      },
    },
  },
  plugins: [],
}
