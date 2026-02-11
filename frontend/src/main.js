import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import App from './App.vue'
import routes from './router'
import './assets/main.css'

// Performance optimizations
import { imageOptimizer } from '@/utils/imageOptimization'
import { chartOptimizer } from '@/services/chartOptimization'

const pinia = createPinia()
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Performance monitoring
const performanceObserver = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.entryType === 'navigation') {
      console.log('Navigation Performance:', {
        loadComplete: entry.loadEventEnd - entry.fetchStart,
        domContentLoaded: entry.domContentLoadedEventEnd - entry.fetchStart,
        firstPaint: entry.responseEnd - entry.fetchStart
      })
    } else if (entry.entryType === 'largest-contentful-paint') {
      console.log('Largest Contentful Paint:', entry.startTime)
    } else if (entry.entryType === 'first-input') {
      console.log('First Input Delay:', entry.processingStart - entry.startTime)
    }
  }
})

// Observe performance metrics
if ('PerformanceObserver' in window) {
  try {
    performanceObserver.observe({ entryTypes: ['navigation', 'largest-contentful-paint', 'first-input'] })
  } catch (error) {
    console.warn('Performance monitoring not fully supported:', error)
  }
}

// Register service worker
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register('/sw.js')
    .then((registration) => {
      console.log('Service Worker registered:', registration.scope)
      
      // Check for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New content available, notify user
            console.log('New content available! Refresh to update.')
            // You could show a toast notification here
          }
        })
      })
    })
    .catch((error) => {
      console.error('Service Worker registration failed:', error)
    })
}

// Initialize image optimization
document.addEventListener('DOMContentLoaded', () => {
  imageOptimizer.setupLazyLoading()
})

// Router performance monitoring
router.beforeEach((to, from, next) => {
  const start = performance.now()
  
  // Store navigation start time
  to.meta = to.meta || {}
  to.meta.navigationStart = start
  
  next()
})

router.afterEach((to) => {
  // Log route navigation performance
  if (to.meta && to.meta.navigationStart) {
    const navigationTime = performance.now() - to.meta.navigationStart
    console.log(`Route navigation to ${to.path}:`, navigationTime.toFixed(2) + 'ms')
  }
})

// Create and mount app
const app = createApp(App)
app.use(pinia)
app.use(router)

// Global error handler for performance monitoring
app.config.errorHandler = (error, vm, info) => {
  console.error('Vue Error:', error, info)
  
  // Log performance impact of errors
  if (window.performance && window.performance.mark) {
    window.performance.mark('vue-error-' + Date.now())
  }
}

// Mount app with performance timing
const mountStart = performance.now()
app.mount('#app')
const mountTime = performance.now() - mountStart
console.log('App mount time:', mountTime.toFixed(2) + 'ms')

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  performanceObserver.disconnect()
  chartOptimizer.destroyAllCharts()
  imageOptimizer.clearCache()
})
