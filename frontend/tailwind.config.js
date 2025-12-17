export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'apple-bg': '#F5F7F4',
        'apple-card': '#FAFBF9',
        'apple-subtle': '#EEF1EC',
        'apple-border': 'rgba(59,77,67,0.08)',
        'apple-text': '#3D4A44',
        'apple-text-secondary': '#7A8580',
        'apple-purple': '#5B8A72',
        'apple-pink': '#7BA594',
        'apple-violet': '#6B9A84',
        'apple-highlight': '#4A7A62',
        'apple-success': '#5B9A6E',
        'apple-warning': '#C4956B',
        'apple-error': '#C47068',
        'apple-info': '#5A8A9A',
        'signal-red': '#C47068',
        'void-black': '#2A3530',
        'surface-black': '#3D4A44',
        'tech-grey': '#7A8580',
        'border-grey': '#5A6660',
      },
      boxShadow: {
        'apple-card': '0px 4px 12px rgba(59,77,67,0.06)',
        'apple-button': '0px 1px 3px rgba(59,77,67,0.05)',
        'apple-nav': '0px 1px 0px rgba(59,77,67,0.04)',
        'red-glow': '0 0 15px rgba(196, 112, 104, 0.3)',
        'red-glow-intense': '0 0 25px rgba(196, 112, 104, 0.5)',
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
