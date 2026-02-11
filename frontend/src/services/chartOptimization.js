/**
 * Chart.js performance optimization configuration and utilities
 */

import { Chart } from 'chart.js'

/**
 * Optimized Chart.js configuration for better performance
 */
export const optimizedChartDefaults = {
  // Animation optimizations
  animation: {
    duration: 300, // Reduced from default 1000ms
    easing: 'easeOutQuart'
  },
  
  // Disable animations for large datasets
  animations: {
    colors: false,
    x: false,
    y: false
  },
  
  // Performance optimizations
  responsive: true,
  maintainAspectRatio: false,
  
  // Interaction optimizations
  interaction: {
    mode: 'nearest',
    intersect: false,
    axis: 'x'
  },
  
  // Scale optimizations
  scales: {
    x: {
      type: 'time',
      time: {
        displayFormats: {
          hour: 'MMM DD',
          day: 'MMM DD',
          week: 'MMM DD',
          month: 'MMM YYYY'
        }
      },
      // Performance optimizations for large datasets
      ticks: {
        maxTicksLimit: 10,
        autoSkip: true,
        autoSkipPadding: 10
      }
    },
    y: {
      ticks: {
        maxTicksLimit: 8,
        callback: function(value) {
          // Format numbers for better readability
          if (Math.abs(value) >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M'
          } else if (Math.abs(value) >= 1000) {
            return (value / 1000).toFixed(1) + 'K'
          }
          return value.toFixed(2)
        }
      }
    }
  },
  
  // Plugin optimizations
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        pointStyle: 'circle',
        padding: 10
      }
    },
    tooltip: {
      enabled: true,
      mode: 'nearest',
      intersect: false,
      animation: {
        duration: 100
      },
      callbacks: {
        label: function(context) {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          
          // Format tooltip values
          if (Math.abs(value) >= 1000000) {
            return `${label}: $${(value / 1000000).toFixed(2)}M`
          } else if (Math.abs(value) >= 1000) {
            return `${label}: $${(value / 1000).toFixed(2)}K`
          }
          return `${label}: $${value.toFixed(2)}`
        }
      }
    }
  },
  
  // Element optimizations
  elements: {
    point: {
      radius: 0, // Hide points for better performance
      hoverRadius: 4
    },
    line: {
      borderWidth: 2,
      tension: 0.1 // Smooth curves with minimal performance impact
    }
  }
}

/**
 * Chart optimization utilities
 */
export class ChartOptimizer {
  constructor() {
    this.chartInstances = new Map()
    this.dataCache = new Map()
    this.updateThrottle = new Map()
  }

  /**
   * Create optimized chart with performance monitoring
   */
  createChart(canvasId, config) {
    const canvas = document.getElementById(canvasId)
    if (!canvas) {
      console.error(`Canvas element with id '${canvasId}' not found`)
      return null
    }

    // Merge with optimized defaults
    const optimizedConfig = this.mergeConfig(config, optimizedChartDefaults)
    
    // Add performance monitoring
    optimizedConfig.plugins = optimizedConfig.plugins || {}
    optimizedConfig.plugins.beforeRender = (chart) => {
      chart._renderStart = performance.now()
    }
    optimizedConfig.plugins.afterRender = (chart) => {
      const renderTime = performance.now() - chart._renderStart
      if (renderTime > 50) { // Log slow renders
        console.warn(`Chart ${canvasId} render took ${renderTime.toFixed(2)}ms`)
      }
    }

    const chart = new Chart(canvas, optimizedConfig)
    this.chartInstances.set(canvasId, chart)
    
    return chart
  }

  /**
   * Update chart data with throttling and caching
   */
  updateChartData(canvasId, newData, throttleMs = 100) {
    const chart = this.chartInstances.get(canvasId)
    if (!chart) return

    // Throttle rapid updates
    if (this.updateThrottle.has(canvasId)) {
      clearTimeout(this.updateThrottle.get(canvasId))
    }

    this.updateThrottle.set(canvasId, setTimeout(() => {
      // Check if data actually changed (avoid unnecessary re-renders)
      const cachedData = this.dataCache.get(canvasId)
      const dataString = JSON.stringify(newData)
      
      if (cachedData === dataString) return
      
      this.dataCache.set(canvasId, dataString)
      
      // Update chart data
      chart.data = newData
      chart.update('none') // Skip animations for performance
    }, throttleMs))
  }

  /**
   * Optimized data sampling for large datasets
   */
  sampleData(data, maxPoints = 100) {
    if (data.length <= maxPoints) return data

    const step = Math.ceil(data.length / maxPoints)
    const sampled = []
    
    for (let i = 0; i < data.length; i += step) {
      sampled.push(data[i])
    }
    
    // Always include the last point
    if (sampled[sampled.length - 1] !== data[data.length - 1]) {
      sampled.push(data[data.length - 1])
    }
    
    return sampled
  }

  /**
   * Merge configuration objects deeply
   */
  mergeConfig(target, source) {
    const result = { ...target }
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.mergeConfig(result[key] || {}, source[key])
      } else {
        result[key] = source[key]
      }
    }
    
    return result
  }

  /**
   * Clean up chart resources
   */
  destroyChart(canvasId) {
    const chart = this.chartInstances.get(canvasId)
    if (chart) {
      chart.destroy()
      this.chartInstances.delete(canvasId)
      this.dataCache.delete(canvasId)
      
      if (this.updateThrottle.has(canvasId)) {
        clearTimeout(this.updateThrottle.get(canvasId))
        this.updateThrottle.delete(canvasId)
      }
    }
  }

  /**
   * Clean up all charts
   */
  destroyAllCharts() {
    for (const canvasId of this.chartInstances.keys()) {
      this.destroyChart(canvasId)
    }
  }

  /**
   * Get performance statistics
   */
  getStats() {
    return {
      activeCharts: this.chartInstances.size,
      cachedDataSets: this.dataCache.size,
      pendingUpdates: this.updateThrottle.size
    }
  }

  /**
   * Configure responsive behavior for mobile performance
   */
  configureResponsive(config) {
    const isMobile = window.innerWidth < 768
    
    if (isMobile) {
      // Mobile optimizations
      config.animation = { duration: 0 } // Disable animations
      config.elements = config.elements || {}
      config.elements.point = { radius: 0, hoverRadius: 2 }
      config.plugins = config.plugins || {}
      config.plugins.legend = { display: false } // Hide legend on mobile
    }
    
    return config
  }
}

// Singleton instance
export const chartOptimizer = new ChartOptimizer()

// Auto-cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    chartOptimizer.destroyAllCharts()
  })
}

/**
 * Theme-aware chart colors with performance considerations
 */
export const getOptimizedChartColors = (isDark = false) => {
  const colors = isDark ? {
    primary: '#3B82F6',
    secondary: '#10B981',
    accent: '#F59E0B',
    danger: '#EF4444',
    text: '#F3F4F6',
    grid: '#374151'
  } : {
    primary: '#2563EB',
    secondary: '#059669',
    accent: '#D97706',
    danger: '#DC2626',
    text: '#1F2937',
    grid: '#E5E7EB'
  }

  return {
    ...colors,
    // Pre-calculated alpha variants for performance
    primaryAlpha: colors.primary + '80',
    secondaryAlpha: colors.secondary + '80',
    accentAlpha: colors.accent + '80'
  }
}

export default chartOptimizer