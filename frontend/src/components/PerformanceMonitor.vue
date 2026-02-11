<template>
  <div class="performance-monitor" v-if="showMonitor">
    <div class="monitor-header">
      <h3>🚀 Performance Monitor</h3>
      <button @click="toggleMonitor" class="toggle-btn">
        {{ isMinimized ? '📊' : '➖' }}
      </button>
      <button @click="closeMonitor" class="close-btn">✖️</button>
    </div>
    
    <div v-if="!isMinimized" class="monitor-content">
      <!-- Real-time metrics -->
      <div class="metrics-section">
        <h4>Real-time Metrics</h4>
        <div class="metrics-grid">
          <div class="metric">
            <span class="metric-label">FPS</span>
            <span class="metric-value" :class="getFPSClass()">{{ metrics.fps }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Memory</span>
            <span class="metric-value">{{ formatBytes(metrics.memory) }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">DOM Nodes</span>
            <span class="metric-value">{{ metrics.domNodes }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">Event Listeners</span>
            <span class="metric-value">{{ metrics.eventListeners }}</span>
          </div>
        </div>
      </div>

      <!-- Performance timeline -->
      <div class="timeline-section">
        <h4>Response Times (ms)</h4>
        <div class="timeline-chart">
          <div 
            v-for="(time, index) in responseTimes.slice(-20)" 
            :key="index"
            class="timeline-bar"
            :style="{ height: `${Math.min(time / 10, 50)}px` }"
            :class="getTimelineBarClass(time)"
            :title="`${time}ms`"
          ></div>
        </div>
      </div>

      <!-- WebSocket status -->
      <div class="websocket-section" v-if="wsStats">
        <h4>WebSocket Status</h4>
        <div class="ws-stats">
          <div class="ws-stat">
            <span class="ws-label">Connections:</span>
            <span class="ws-value">{{ wsStats.activeConnections }}</span>
          </div>
          <div class="ws-stat">
            <span class="ws-label">Messages Queued:</span>
            <span class="ws-value">{{ wsStats.queuedMessages }}</span>
          </div>
          <div class="ws-stat">
            <span class="ws-label">Reconnect Attempts:</span>
            <span class="ws-value">{{ wsStats.reconnectAttempts }}</span>
          </div>
        </div>
      </div>

      <!-- Resource usage -->
      <div class="resources-section">
        <h4>Resource Usage</h4>
        <div class="resource-bars">
          <div class="resource-bar">
            <span class="resource-label">JavaScript Heap:</span>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: `${(metrics.jsHeap / metrics.jsHeapLimit * 100)}%` }"
                :class="getHeapClass()"
              ></div>
            </div>
            <span class="resource-text">
              {{ formatBytes(metrics.jsHeap) }} / {{ formatBytes(metrics.jsHeapLimit) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Performance warnings -->
      <div class="warnings-section" v-if="warnings.length > 0">
        <h4>⚠️ Performance Warnings</h4>
        <div class="warnings-list">
          <div 
            v-for="warning in warnings.slice(-5)" 
            :key="warning.id"
            class="warning-item"
          >
            <span class="warning-icon">{{ getWarningIcon(warning.type) }}</span>
            <span class="warning-text">{{ warning.message }}</span>
            <span class="warning-time">{{ formatTime(warning.timestamp) }}</span>
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="controls-section">
        <button @click="clearWarnings" class="control-btn">Clear Warnings</button>
        <button @click="exportMetrics" class="control-btn">Export Metrics</button>
        <button @click="triggerGC" class="control-btn">Force GC</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { wsService } from '@/services/websocket'
import { chartOptimizer } from '@/services/chartOptimization'
import { imageOptimizer } from '@/utils/imageOptimization'

export default {
  name: 'PerformanceMonitor',
  setup() {
    const showMonitor = ref(false)
    const isMinimized = ref(false)
    const metrics = ref({
      fps: 0,
      memory: 0,
      jsHeap: 0,
      jsHeapLimit: 0,
      domNodes: 0,
      eventListeners: 0
    })
    const responseTimes = ref([])
    const wsStats = ref(null)
    const warnings = ref([])
    
    let animationFrame = null
    let metricsInterval = null
    let fpsCounter = 0
    let lastTime = 0

    // FPS tracking
    const updateFPS = (currentTime) => {
      if (lastTime === 0) lastTime = currentTime
      
      const delta = currentTime - lastTime
      if (delta >= 1000) {
        metrics.value.fps = Math.round(fpsCounter * 1000 / delta)
        fpsCounter = 0
        lastTime = currentTime
      } else {
        fpsCounter++
      }
      
      animationFrame = requestAnimationFrame(updateFPS)
    }

    // Memory and performance metrics
    const updateMetrics = () => {
      if (!performance.memory) return

      metrics.value.memory = performance.memory.usedJSHeapSize
      metrics.value.jsHeap = performance.memory.usedJSHeapSize
      metrics.value.jsHeapLimit = performance.memory.jsHeapSizeLimit
      metrics.value.domNodes = document.querySelectorAll('*').length
      
      // Estimate event listeners (rough approximation)
      metrics.value.eventListeners = document.querySelectorAll('[onclick], [onload], [onchange]').length + 
                                    Object.keys(window).filter(key => key.startsWith('on')).length

      // Check for performance warnings
      checkPerformanceWarnings()
      
      // Update WebSocket stats
      wsStats.value = wsService.getStats()
    }

    // Performance warnings checker
    const checkPerformanceWarnings = () => {
      const now = Date.now()
      
      // Memory warning
      if (metrics.value.jsHeap > metrics.value.jsHeapLimit * 0.8) {
        addWarning('memory', 'JavaScript heap usage is high (>80%)', now)
      }
      
      // DOM nodes warning
      if (metrics.value.domNodes > 5000) {
        addWarning('dom', `High DOM node count: ${metrics.value.domNodes}`, now)
      }
      
      // FPS warning
      if (metrics.value.fps < 30 && metrics.value.fps > 0) {
        addWarning('fps', `Low FPS detected: ${metrics.value.fps}`, now)
      }
      
      // Response time warning
      const recentTimes = responseTimes.value.slice(-5)
      if (recentTimes.length >= 5) {
        const avgTime = recentTimes.reduce((sum, time) => sum + time, 0) / recentTimes.length
        if (avgTime > 1000) {
          addWarning('response', `Slow response times: ${avgTime.toFixed(0)}ms average`, now)
        }
      }
    }

    const addWarning = (type, message, timestamp) => {
      // Don't add duplicate warnings within 30 seconds
      const recentWarning = warnings.value.find(w => 
        w.type === type && w.message === message && timestamp - w.timestamp < 30000
      )
      
      if (!recentWarning) {
        warnings.value.push({
          id: Date.now() + Math.random(),
          type,
          message,
          timestamp
        })
        
        // Keep only last 20 warnings
        if (warnings.value.length > 20) {
          warnings.value = warnings.value.slice(-20)
        }
      }
    }

    // Track API response times
    const trackResponseTime = (time) => {
      responseTimes.value.push(Math.round(time))
      if (responseTimes.value.length > 50) {
        responseTimes.value = responseTimes.value.slice(-50)
      }
    }

    // Utility functions
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString()
    }

    const getFPSClass = () => {
      const fps = metrics.value.fps
      if (fps >= 50) return 'metric-good'
      if (fps >= 30) return 'metric-warning'
      return 'metric-critical'
    }

    const getTimelineBarClass = (time) => {
      if (time < 200) return 'timeline-good'
      if (time < 500) return 'timeline-warning'
      return 'timeline-critical'
    }

    const getHeapClass = () => {
      const usage = metrics.value.jsHeap / metrics.value.jsHeapLimit
      if (usage < 0.6) return 'heap-good'
      if (usage < 0.8) return 'heap-warning'
      return 'heap-critical'
    }

    const getWarningIcon = (type) => {
      switch (type) {
        case 'memory': return '🧠'
        case 'dom': return '📄'
        case 'fps': return '🎮'
        case 'response': return '⏱️'
        default: return '⚠️'
      }
    }

    // Control functions
    const toggleMonitor = () => {
      isMinimized.value = !isMinimized.value
    }

    const closeMonitor = () => {
      showMonitor.value = false
    }

    const clearWarnings = () => {
      warnings.value = []
    }

    const exportMetrics = () => {
      const exportData = {
        timestamp: new Date().toISOString(),
        metrics: metrics.value,
        responseTimes: responseTimes.value,
        warnings: warnings.value,
        wsStats: wsStats.value,
        chartStats: chartOptimizer.getStats(),
        imageStats: imageOptimizer.getCacheStats()
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `performance-metrics-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    }

    const triggerGC = () => {
      if (window.gc) {
        window.gc()
        addWarning('info', 'Garbage collection triggered manually', Date.now())
      } else {
        addWarning('info', 'Garbage collection not available (requires --expose-gc flag)', Date.now())
      }
    }

    // Lifecycle
    onMounted(() => {
      // Show monitor in development mode or when performance flag is set
      showMonitor.value = import.meta.env.DEV || localStorage.getItem('show-performance-monitor') === 'true'
      
      if (showMonitor.value) {
        animationFrame = requestAnimationFrame(updateFPS)
        metricsInterval = setInterval(updateMetrics, 2000) // Update every 2 seconds
        
        // Intercept fetch requests to track response times
        const originalFetch = window.fetch
        window.fetch = async (...args) => {
          const start = performance.now()
          try {
            const response = await originalFetch(...args)
            const time = performance.now() - start
            trackResponseTime(time)
            return response
          } catch (error) {
            const time = performance.now() - start
            trackResponseTime(time)
            throw error
          }
        }
      }
    })

    onUnmounted(() => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
      if (metricsInterval) {
        clearInterval(metricsInterval)
      }
    })

    // Keyboard shortcut to toggle monitor
    const handleKeyPress = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'P') {
        showMonitor.value = !showMonitor.value
        localStorage.setItem('show-performance-monitor', showMonitor.value.toString())
      }
    }

    onMounted(() => {
      document.addEventListener('keydown', handleKeyPress)
    })

    onUnmounted(() => {
      document.removeEventListener('keydown', handleKeyPress)
    })

    return {
      showMonitor,
      isMinimized,
      metrics,
      responseTimes,
      wsStats,
      warnings,
      formatBytes,
      formatTime,
      getFPSClass,
      getTimelineBarClass,
      getHeapClass,
      getWarningIcon,
      toggleMonitor,
      closeMonitor,
      clearWarnings,
      exportMetrics,
      triggerGC
    }
  }
}
</script>

<style scoped>
.performance-monitor {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 350px;
  background: rgba(0, 0, 0, 0.9);
  color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  font-family: 'Courier New', monospace;
  font-size: 12px;
  z-index: 10000;
  backdrop-filter: blur(10px);
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px 8px 0 0;
}

.monitor-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: bold;
}

.toggle-btn, .close-btn {
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 3px;
  margin-left: 5px;
}

.toggle-btn:hover, .close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.monitor-content {
  padding: 15px;
  max-height: 600px;
  overflow-y: auto;
}

.metrics-section h4,
.timeline-section h4,
.websocket-section h4,
.resources-section h4,
.warnings-section h4 {
  margin: 0 0 10px 0;
  font-size: 12px;
  color: #00ff88;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 5px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 20px;
}

.metric {
  display: flex;
  justify-content: space-between;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.metric-label {
  color: #ccc;
}

.metric-value {
  font-weight: bold;
}

.metric-good { color: #00ff88; }
.metric-warning { color: #ffaa00; }
.metric-critical { color: #ff4444; }

.timeline-chart {
  display: flex;
  align-items: end;
  height: 50px;
  margin-bottom: 20px;
  padding: 5px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.timeline-bar {
  width: 3px;
  margin-right: 1px;
  border-radius: 1px;
  transition: height 0.2s ease;
}

.timeline-good { background: #00ff88; }
.timeline-warning { background: #ffaa00; }
.timeline-critical { background: #ff4444; }

.ws-stats {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 20px;
}

.ws-stat {
  display: flex;
  justify-content: space-between;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.resource-bars {
  margin-bottom: 20px;
}

.resource-bar {
  margin-bottom: 10px;
}

.resource-label {
  display: block;
  margin-bottom: 5px;
  color: #ccc;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 5px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.heap-good { background: #00ff88; }
.heap-warning { background: #ffaa00; }
.heap-critical { background: #ff4444; }

.resource-text {
  font-size: 10px;
  color: #aaa;
}

.warnings-list {
  margin-bottom: 20px;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  margin-bottom: 5px;
  background: rgba(255, 170, 0, 0.1);
  border-left: 3px solid #ffaa00;
  border-radius: 4px;
  font-size: 11px;
}

.warning-text {
  flex: 1;
}

.warning-time {
  font-size: 10px;
  color: #aaa;
}

.controls-section {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.control-btn {
  padding: 5px 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.2s ease;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Dark theme adjustments */
.dark .performance-monitor {
  background: rgba(0, 0, 0, 0.95);
}

.dark .monitor-header {
  background: rgba(255, 255, 255, 0.05);
}
</style>