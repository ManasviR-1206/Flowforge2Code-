/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['var(--font-heading)', 'Helvetica Neue', 'sans-serif'],
        body: ['var(--font-body)', 'Helvetica Neue', 'sans-serif'],
      },
      colors: {
        space: {
          950: '#030712',
          900: '#060d1f',
          800: '#0b162f',
          700: '#112247',
        },
        cyanGlow: '#00f0ff',
        purpleGlow: '#a855f7',
      },
      animation: {
        'float-slow': 'float 6s ease-in-out infinite',
        'float-delayed': 'float 7s ease-in-out 3s infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'dash-flow': 'dashFlow 2s linear infinite',
        'laser-beam': 'laserBeam 3s ease-in-out infinite',
        'orbit': 'orbit 20s linear infinite',
        'cursor-blink': 'blink 0.8s step-end infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-14px)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.4', filter: 'drop-shadow(0 0 15px rgba(6, 182, 212, 0.4))' },
          '50%': { opacity: '0.9', filter: 'drop-shadow(0 0 30px rgba(6, 182, 212, 0.8))' },
        },
        dashFlow: {
          '0%': { strokeDashoffset: '24' },
          '100%': { strokeDashoffset: '0' },
        },
        laserBeam: {
          '0%, 100%': { opacity: '0.2' },
          '50%': { opacity: '1' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        }
      }
    },
  },
  plugins: [],
}
