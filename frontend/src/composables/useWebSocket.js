import { ref, onUnmounted, nextTick } from 'vue'

export const WEBSOCKET_STATES = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error'
}

export function useWebSocket(url, options = {}) {
  const {
    autoConnect = true,
    reconnect: shouldReconnect = true,
    maxReconnectAttempts = 5,
    reconnectInterval = 1000,
    heartbeat = false,
    heartbeatInterval = 30000
  } = options

  // State
  const ws = ref(null)
  const state = ref(WEBSOCKET_STATES.DISCONNECTED)
  const lastMessage = ref(null)
  const error = ref(null)
  const reconnectAttempts = ref(0)
  
  // Local mutable reconnect flag
  let reconnect = shouldReconnect

  // Internal refs
  let reconnectTimer = null
  let heartbeatTimer = null
  let messageCallbacks = new Map()
  let eventCallbacks = new Map()

  // Connection management
  const connect = () => {
    if (ws.value?.readyState === WebSocket.OPEN) return

    state.value = WEBSOCKET_STATES.CONNECTING
    error.value = null

    try {
      ws.value = new WebSocket(url)
      
      ws.value.onopen = () => {
        state.value = WEBSOCKET_STATES.CONNECTED
        reconnectAttempts.value = 0
        
        // Start heartbeat if enabled
        if (heartbeat) {
          startHeartbeat()
        }
        
        // Call connection callbacks
        eventCallbacks.get('open')?.forEach(callback => callback())
      }
      
      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data
          
          // Call message type callbacks
          const typeCallbacks = messageCallbacks.get(data.type) || []
          typeCallbacks.forEach(callback => callback(data))
          
          // Call general message callbacks
          const generalCallbacks = messageCallbacks.get('message') || []
          generalCallbacks.forEach(callback => callback(data))
          
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }
      
      ws.value.onerror = (event) => {
        state.value = WEBSOCKET_STATES.ERROR
        error.value = new Error('WebSocket connection error')
        
        // Call error callbacks
        eventCallbacks.get('error')?.forEach(callback => callback(event))
      }
      
      ws.value.onclose = (event) => {
        state.value = WEBSOCKET_STATES.DISCONNECTED
        stopHeartbeat()
        
        // Call close callbacks
        eventCallbacks.get('close')?.forEach(callback => callback(event))
        
        // Attempt reconnection
        if (reconnect && reconnectAttempts.value < maxReconnectAttempts) {
          attemptReconnect()
        }
      }
      
    } catch (err) {
      state.value = WEBSOCKET_STATES.ERROR
      error.value = err
    }
  }

  const disconnect = () => {
    reconnect = false
    clearTimeout(reconnectTimer)
    stopHeartbeat()
    
    if (ws.value) {
      ws.value.close(1000, 'Manual disconnect')
    }
  }

  const send = (data) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      ws.value.send(message)
      return true
    }
    return false
  }

  // Reconnection logic
  const attemptReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      error.value = new Error('Max reconnection attempts reached')
      return
    }

    reconnectAttempts.value++
    const delay = Math.min(reconnectInterval * Math.pow(2, reconnectAttempts.value - 1), 30000)
    
    reconnectTimer = setTimeout(() => {
      if (state.value !== WEBSOCKET_STATES.CONNECTED) {
        connect()
      }
    }, delay)
  }

  // Heartbeat functionality
  const startHeartbeat = () => {
    heartbeatTimer = setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        send({ type: 'ping' })
      }
    }, heartbeatInterval)
  }

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // Event subscription
  const on = (eventType, callback) => {
    if (['open', 'close', 'error'].includes(eventType)) {
      if (!eventCallbacks.has(eventType)) {
        eventCallbacks.set(eventType, [])
      }
      eventCallbacks.get(eventType).push(callback)
    } else {
      // Message type subscription
      if (!messageCallbacks.has(eventType)) {
        messageCallbacks.set(eventType, [])
      }
      messageCallbacks.get(eventType).push(callback)
    }

    // Return unsubscribe function
    return () => {
      if (['open', 'close', 'error'].includes(eventType)) {
        const callbacks = eventCallbacks.get(eventType) || []
        const index = callbacks.indexOf(callback)
        if (index > -1) callbacks.splice(index, 1)
      } else {
        const callbacks = messageCallbacks.get(eventType) || []
        const index = callbacks.indexOf(callback)
        if (index > -1) callbacks.splice(index, 1)
      }
    }
  }

  // Cleanup
  onUnmounted(() => {
    disconnect()
    messageCallbacks.clear()
    eventCallbacks.clear()
  })

  // Auto-connect if enabled
  if (autoConnect) {
    nextTick(() => connect())
  }

  return {
    // State
    state,
    error,
    lastMessage,
    reconnectAttempts,
    
    // Connection methods
    connect,
    disconnect,
    send,
    
    // Event subscription
    on,
    
    // Computed helpers
    isConnecting: () => state.value === WEBSOCKET_STATES.CONNECTING,
    isConnected: () => state.value === WEBSOCKET_STATES.CONNECTED,
    isDisconnected: () => state.value === WEBSOCKET_STATES.DISCONNECTED,
    hasError: () => state.value === WEBSOCKET_STATES.ERROR
  }
}

// Portfolio-specific WebSocket composable
export function usePortfolioWebSocket(portfolioName, options = {}) {
  const wsUrl = `ws://localhost:8000/api/agents/ws/${portfolioName}`
  return useWebSocket(wsUrl, {
    reconnect: true,
    heartbeat: true,
    ...options
  })
}

// System WebSocket composable
export function useSystemWebSocket(options = {}) {
  const wsUrl = 'ws://localhost:8000/api/agents/ws/system'
  return useWebSocket(wsUrl, {
    reconnect: true,
    heartbeat: true,
    ...options
  })
}

// Trades WebSocket composable
export function useTradesWebSocket(options = {}) {
  const wsUrl = 'ws://localhost:8000/api/agents/ws/trades'
  return useWebSocket(wsUrl, {
    reconnect: true,
    heartbeat: true,
    ...options
  })
}