/**
 * Optimized WebSocket service for efficient real-time communication
 */

class OptimizedWebSocket {
  constructor() {
    this.connections = new Map()
    this.messageQueue = new Map()
    this.reconnectAttempts = new Map()
    this.heartbeatIntervals = new Map()
    
    // Performance optimizations
    this.batchSize = 50 // Batch messages for processing
    this.throttleDelay = 100 // Throttle rapid updates
    this.maxReconnectAttempts = 5
    this.heartbeatInterval = 30000 // 30 seconds
  }

  /**
   * Create optimized WebSocket connection with batching and throttling
   */
  connect(key, url, options = {}) {
    if (this.connections.has(key)) {
      this.disconnect(key)
    }

    const ws = new WebSocket(url)
    const config = {
      onMessage: options.onMessage || (() => {}),
      onError: options.onError || (() => {}),
      onConnect: options.onConnect || (() => {}),
      onDisconnect: options.onDisconnect || (() => {}),
      batchMessages: options.batchMessages !== false,
      throttleUpdates: options.throttleUpdates !== false
    }

    // Message batching for performance
    let messageBatch = []
    let batchTimeout = null

    const processBatch = () => {
      if (messageBatch.length === 0) return
      
      try {
        if (config.batchMessages && messageBatch.length > 1) {
          // Process messages in batch
          config.onMessage(messageBatch)
        } else {
          // Process individual messages
          messageBatch.forEach(msg => config.onMessage(msg))
        }
      } catch (error) {
        console.error(`WebSocket batch processing error for ${key}:`, error)
        config.onError(error)
      }
      
      messageBatch = []
      batchTimeout = null
    }

    // Throttled message processing
    let lastProcessTime = 0
    const throttledProcess = (message) => {
      const now = Date.now()
      if (!config.throttleUpdates || now - lastProcessTime >= this.throttleDelay) {
        lastProcessTime = now
        return processBatch()
      }
      
      // Defer processing
      if (!batchTimeout) {
        batchTimeout = setTimeout(processBatch, this.throttleDelay)
      }
    }

    ws.onopen = () => {
      console.log(`WebSocket connected: ${key}`)
      this.reconnectAttempts.set(key, 0)
      
      // Setup heartbeat
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        }
      }, this.heartbeatInterval)
      
      this.heartbeatIntervals.set(key, heartbeat)
      config.onConnect()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Handle heartbeat responses
        if (data.type === 'pong') {
          return
        }
        
        // Add to batch
        messageBatch.push(data)
        
        // Process batch when it reaches limit or after delay
        if (messageBatch.length >= this.batchSize) {
          processBatch()
        } else {
          throttledProcess(data)
        }
      } catch (error) {
        console.error(`WebSocket message parsing error for ${key}:`, error)
        config.onError(error)
      }
    }

    ws.onclose = () => {
      console.log(`WebSocket disconnected: ${key}`)
      this.cleanup(key)
      config.onDisconnect()
      
      // Auto-reconnect with exponential backoff
      const attempts = this.reconnectAttempts.get(key) || 0
      if (attempts < this.maxReconnectAttempts) {
        const delay = Math.pow(2, attempts) * 1000 // Exponential backoff
        console.log(`Reconnecting WebSocket ${key} in ${delay}ms (attempt ${attempts + 1})`)
        
        setTimeout(() => {
          this.reconnectAttempts.set(key, attempts + 1)
          this.connect(key, url, options)
        }, delay)
      }
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${key}:`, error)
      config.onError(error)
    }

    this.connections.set(key, { ws, config })
    return ws
  }

  /**
   * Send message with queuing for offline scenarios
   */
  send(key, message) {
    const connection = this.connections.get(key)
    if (!connection) {
      console.warn(`WebSocket ${key} not found`)
      return false
    }

    const { ws } = connection
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
      return true
    } else {
      // Queue message for when connection reopens
      if (!this.messageQueue.has(key)) {
        this.messageQueue.set(key, [])
      }
      this.messageQueue.get(key).push(message)
      return false
    }
  }

  /**
   * Send queued messages when connection reopens
   */
  sendQueuedMessages(key) {
    const queue = this.messageQueue.get(key)
    if (queue && queue.length > 0) {
      const connection = this.connections.get(key)
      if (connection && connection.ws.readyState === WebSocket.OPEN) {
        queue.forEach(message => {
          connection.ws.send(JSON.stringify(message))
        })
        this.messageQueue.set(key, [])
      }
    }
  }

  /**
   * Disconnect and clean up WebSocket
   */
  disconnect(key) {
    const connection = this.connections.get(key)
    if (connection) {
      connection.ws.close()
      this.cleanup(key)
    }
  }

  /**
   * Clean up resources for a connection
   */
  cleanup(key) {
    this.connections.delete(key)
    this.messageQueue.delete(key)
    this.reconnectAttempts.delete(key)
    
    const heartbeat = this.heartbeatIntervals.get(key)
    if (heartbeat) {
      clearInterval(heartbeat)
      this.heartbeatIntervals.delete(key)
    }
  }

  /**
   * Disconnect all WebSocket connections
   */
  disconnectAll() {
    for (const key of this.connections.keys()) {
      this.disconnect(key)
    }
  }

  /**
   * Get connection status
   */
  getStatus(key) {
    const connection = this.connections.get(key)
    if (!connection) return 'not_found'
    
    switch (connection.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'open'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'closed'
      default:
        return 'unknown'
    }
  }

  /**
   * Get connection statistics
   */
  getStats() {
    return {
      activeConnections: this.connections.size,
      queuedMessages: Array.from(this.messageQueue.values())
        .reduce((total, queue) => total + queue.length, 0),
      reconnectAttempts: Array.from(this.reconnectAttempts.values())
        .reduce((total, attempts) => total + attempts, 0)
    }
  }
}

// Singleton instance
export const wsService = new OptimizedWebSocket()

// Auto-cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    wsService.disconnectAll()
  })
}

export default wsService