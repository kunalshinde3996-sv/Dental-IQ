/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#effcfb',
          100: '#d6f5f3',
          200: '#b0ebe8',
          300: '#7bdbd8',
          400: '#40c1c1',
          500: '#25a5a7',
          600: '#1f848b',
          700: '#1f6a71',
          800: '#20575d',
          900: '#1f494f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
