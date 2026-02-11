/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  darkMode: 'class', // Enable dark mode via class strategy
  theme: {
    extend: {
      colors: {
        // Existing colors (for backward compatibility)
        ink: '#0f172a',
        slate: '#1f2937',
        mist: '#e5e7eb',
        accent: '#0ea5e9',
        mint: '#10b981',
        amber: '#f59e0b',
        danger: '#ef4444',
        
        // Theme-aware color system
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9', // Main accent
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        
        // Semantic colors that work with dark mode
        surface: {
          DEFAULT: 'rgb(var(--color-surface) / <alpha-value>)',
          hover: 'rgb(var(--color-surface-hover) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--color-border) / <alpha-value>)',
          light: 'rgb(var(--color-border-light) / <alpha-value>)',
        },
        text: {
          primary: 'rgb(var(--color-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
          tertiary: 'rgb(var(--color-text-tertiary) / <alpha-value>)',
        },
        
        // Status colors
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
      },
      
      // CSS Variables for colors (used by theme system)
      backgroundColor: {
        'theme': 'var(--color-background)',
        'theme-secondary': 'var(--color-background-secondary)',
      },
      
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['"IBM Plex Sans"', 'system-ui', 'sans-serif']
      },
      
      boxShadow: {
        glow: 'var(--shadow-glow)',
        'theme-sm': 'var(--shadow-sm)',
        'theme-md': 'var(--shadow-md)', 
        'theme-lg': 'var(--shadow-lg)',
      },
      
      // Animation for theme transitions
      transitionProperty: {
        'theme': 'background-color, border-color, color, fill, stroke, box-shadow',
      },
    }
  },
  plugins: []
}
