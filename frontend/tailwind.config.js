export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'signal-red': '#E62E2E',
        'void-black': '#0a0a0a',
        'surface-black': '#161616',
        'tech-grey': '#888888',
        'border-grey': '#333333',
      },
      boxShadow: {
        'red-glow': '0 0 15px rgba(230, 46, 46, 0.4)',
        'red-glow-intense': '0 0 25px rgba(230, 46, 46, 0.7)',
      },
      fontFamily: {
        'heading': ['Inter', 'sans-serif'],
        'mono': ['Roboto Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
