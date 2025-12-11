export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'apple-bg': '#F7F7F9',
        'apple-card': '#FFFFFF',
        'apple-subtle': '#F2F2F5',
        'apple-border': 'rgba(0,0,0,0.07)',
        'apple-text': '#1D1D1F',
        'apple-text-secondary': '#86868B',
        'apple-purple': '#A020F0',
        'apple-pink': '#E540AC',
        'apple-violet': '#7D7AFF',
        'apple-highlight': '#FF2F71',
        'apple-success': '#34C759',
        'apple-warning': '#FF9500',
        'apple-error': '#FF3B30',
        'apple-info': '#007AFF',
        'signal-red': '#E62E2E',
        'void-black': '#0a0a0a',
        'surface-black': '#161616',
        'tech-grey': '#888888',
        'border-grey': '#333333',
      },
      boxShadow: {
        'apple-card': '0px 4px 12px rgba(0,0,0,0.08)',
        'apple-button': '0px 1px 3px rgba(0,0,0,0.06)',
        'apple-nav': '0px 1px 0px rgba(0,0,0,0.05)',
        'red-glow': '0 0 15px rgba(230, 46, 46, 0.4)',
        'red-glow-intense': '0 0 25px rgba(230, 46, 46, 0.7)',
      },
      fontFamily: {
        'apple': ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'Inter', 'sans-serif'],
        'heading': ['Inter', 'sans-serif'],
        'mono': ['Roboto Mono', 'monospace'],
      },
      borderRadius: {
        'apple': '18px',
        'apple-sm': '12px',
        'apple-pill': '9999px',
      },
      spacing: {
        'apple-sm': '20px',
        'apple-md': '24px',
        'apple-lg': '32px',
      },
    },
  },
  plugins: [],
}
