import { ref, computed, watch, onMounted } from 'vue'

const STORAGE_KEY = 'fintradeagent-theme'
const THEME_LIGHT = 'light'
const THEME_DARK = 'dark'

// Reactive theme state - shared across all components
const currentTheme = ref(THEME_LIGHT)

// Theme preference detection
const getInitialTheme = () => {
  // Check localStorage first
  const savedTheme = localStorage.getItem(STORAGE_KEY)
  if (savedTheme && [THEME_LIGHT, THEME_DARK].includes(savedTheme)) {
    return savedTheme
  }
  
  // Fall back to system preference
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches 
      ? THEME_DARK 
      : THEME_LIGHT
  }
  
  return THEME_LIGHT
}

// Apply theme to document
const applyTheme = (theme) => {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.remove(THEME_LIGHT, THEME_DARK)
    document.documentElement.classList.add(theme)
    document.documentElement.setAttribute('data-theme', theme)
  }
}

export function useTheme() {
  // Computed properties
  const isDark = computed(() => currentTheme.value === THEME_DARK)
  const isLight = computed(() => currentTheme.value === THEME_LIGHT)
  
  // Theme toggle function
  const toggleTheme = () => {
    const newTheme = currentTheme.value === THEME_LIGHT ? THEME_DARK : THEME_LIGHT
    setTheme(newTheme)
  }
  
  // Set specific theme
  const setTheme = (theme) => {
    if (![THEME_LIGHT, THEME_DARK].includes(theme)) {
      console.warn(`Invalid theme: ${theme}`)
      return
    }
    
    currentTheme.value = theme
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }
  
  // Initialize theme on mount
  const initializeTheme = () => {
    const initialTheme = getInitialTheme()
    currentTheme.value = initialTheme
    applyTheme(initialTheme)
  }
  
  // Watch for system theme changes
  const watchSystemTheme = () => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      const handleChange = (e) => {
        // Only auto-switch if user hasn't manually set a preference
        const savedTheme = localStorage.getItem(STORAGE_KEY)
        if (!savedTheme) {
          const newTheme = e.matches ? THEME_DARK : THEME_LIGHT
          setTheme(newTheme)
        }
      }
      
      mediaQuery.addEventListener('change', handleChange)
      
      // Return cleanup function
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }
  
  // Theme-aware color utilities
  const getThemeColor = (lightColor, darkColor) => {
    return isDark.value ? darkColor : lightColor
  }
  
  // Chart.js theme configuration
  const getChartTheme = () => {
    const colors = isDark.value ? {
      background: '#0f172a',
      surface: '#1e293b',
      border: '#334155',
      text: '#e2e8f0',
      textSecondary: '#94a3b8',
      grid: '#334155',
      accent: '#0ea5e9',
      success: '#10b981',
      warning: '#f59e0b',
      danger: '#ef4444'
    } : {
      background: '#ffffff',
      surface: '#f8fafc',
      border: '#e2e8f0',
      text: '#1e293b',
      textSecondary: '#64748b',
      grid: '#e2e8f0',
      accent: '#0ea5e9',
      success: '#10b981',
      warning: '#f59e0b',
      danger: '#ef4444'
    }
    
    return {
      colors,
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: colors.text,
              usePointStyle: true,
              padding: 20
            }
          },
          tooltip: {
            backgroundColor: colors.surface,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1
          }
        },
        scales: {
          x: {
            ticks: {
              color: colors.textSecondary
            },
            grid: {
              color: colors.grid,
              borderColor: colors.border
            }
          },
          y: {
            ticks: {
              color: colors.textSecondary
            },
            grid: {
              color: colors.grid,
              borderColor: colors.border
            }
          }
        }
      }
    }
  }
  
  // CSS custom properties for dynamic theming
  const updateCSSVariables = () => {
    if (typeof document === 'undefined') return
    
    const root = document.documentElement
    const colors = isDark.value ? {
      // Dark theme colors
      '--color-background': '#0f172a',
      '--color-background-secondary': '#1e293b',
      '--color-surface': '#334155',
      '--color-surface-hover': '#475569',
      '--color-border': '#475569',
      '--color-border-light': '#64748b',
      '--color-text-primary': '#f8fafc',
      '--color-text-secondary': '#e2e8f0',
      '--color-text-tertiary': '#94a3b8',
      '--color-accent': '#0ea5e9',
      '--color-accent-hover': '#0284c7',
      '--color-success': '#10b981',
      '--color-warning': '#f59e0b',
      '--color-danger': '#ef4444',
      '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.2)',
      '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.3)',
      '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.3)',
      '--shadow-glow': '0 0 40px rgba(14, 165, 233, 0.3)'
    } : {
      // Light theme colors
      '--color-background': '#ffffff',
      '--color-background-secondary': '#f8fafc',
      '--color-surface': '#f1f5f9',
      '--color-surface-hover': '#e2e8f0',
      '--color-border': '#e2e8f0',
      '--color-border-light': '#cbd5e1',
      '--color-text-primary': '#1e293b',
      '--color-text-secondary': '#334155',
      '--color-text-tertiary': '#64748b',
      '--color-accent': '#0ea5e9',
      '--color-accent-hover': '#0284c7',
      '--color-success': '#10b981',
      '--color-warning': '#f59e0b',
      '--color-danger': '#ef4444',
      '--shadow-sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      '--shadow-md': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      '--shadow-lg': '0 10px 15px -3px rgb(0 0 0 / 0.1)',
      '--shadow-glow': '0 0 40px rgba(14, 165, 233, 0.15)'
    }
    
    Object.entries(colors).forEach(([property, value]) => {
      root.style.setProperty(property, value)
    })
  }
  
  // Watch theme changes and update CSS variables
  watch(currentTheme, updateCSSVariables, { immediate: true })
  
  return {
    // State
    currentTheme: computed(() => currentTheme.value),
    isDark,
    isLight,
    
    // Actions
    toggleTheme,
    setTheme,
    initializeTheme,
    watchSystemTheme,
    
    // Utilities
    getThemeColor,
    getChartTheme,
    updateCSSVariables,
    
    // Constants
    THEME_LIGHT,
    THEME_DARK
  }
}

// Auto-initialize theme when composable is first imported
if (typeof window !== 'undefined') {
  const { initializeTheme, watchSystemTheme } = useTheme()
  initializeTheme()
  watchSystemTheme()
}