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
    },
  },
  plugins: [],
}
