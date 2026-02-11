// WebSocket mocking utilities for tests

import { vi } from 'vitest'
import { ref, computed } from 'vue'

// Mock WebSocket message types
export const mockWebSocketMessages = {
  executionStarted: {
    type: 'execution_started',
    execution_id: 'exec-123',
    portfolio: 'test-portfolio',
    timestamp: '2026-02-11T10:00:00Z'
  },

  executionProgress: {
    type: 'execution_progress',
    execution_id: 'exec-123',
    status: 'running',
    current_step: 2,
    total_steps: 5,
    message: 'Analyzing market data...',
    progress_percent: 40,
    estimated_time_remaining: 180
  },

  executionCompleted: {
    type: 'execution_completed',
    execution_id: 'exec-123',
    status: 'completed',
    duration: 300,
    recommendations: [
      {
        id: 'trade-1',
        symbol: 'AAPL',
        action: 'BUY',
        quantity: 50,
        price: 180.50,
        confidence: 0.85,
        reason: 'Strong momentum breakout above resistance'
      },
      {
        id: 'trade-2',
        symbol: 'GOOGL',
        action: 'SELL',
        quantity: 20,
        price: 150.25,
        confidence: 0.72,
        reason: 'Overvalued based on current fundamentals'
      }
    ],
    summary: {
      total_recommendations: 2,
      high_confidence_count: 1,
      estimated_profit: 2500
    }
  },

  executionFailed: {
    type: 'execution_failed',
    execution_id: 'exec-123',
    status: 'failed',
    error: 'Market data connection timeout',
    error_code: 'MARKET_DATA_ERROR',
    timestamp: '2026-02-11T10:02:30Z',
    retryable: true
  },

  marketDataUpdate: {
    type: 'market_data',
    updates: [
      {
        symbol: 'AAPL',
        price: 181.25,
        change: 2.50,
        change_percent: 1.40,
        volume: 45000000,
        timestamp: '2026-02-11T10:00:00Z'
      }
    ]
  },

  portfolioUpdate: {
    type: 'portfolio_update',
    portfolio: 'test-portfolio',
    total_value: 52500,
    cash_balance: 8500,
    positions: {
      'AAPL': { shares: 60, price: 181.25, value: 10875 },
      'GOOGL': { shares: 5, price: 150.25, value: 751.25 }
    },
    daily_pnl: 375,
    daily_pnl_percent: 0.72
  },

  systemAlert: {
    type: 'system_alert',
    level: 'warning',
    message: 'High market volatility detected',
    category: 'market_conditions',
    timestamp: '2026-02-11T10:00:00Z',
    auto_dismiss: true,
    dismiss_after: 30000
  }
}

// Create mock WebSocket composable
export const createMockWebSocket = (initialStatus = 'disconnected') => {
  const status = ref(initialStatus)
  const data = ref(null)
  const error = ref(null)
  
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  const isDisconnected = computed(() => status.value === 'disconnected')
  
  const send = vi.fn()
  const close = vi.fn()
  const reconnect = vi.fn()
  
  // Helper methods for testing
  const simulateConnection = () => {
    status.value = 'connecting'
    setTimeout(() => {
      status.value = 'connected'
    }, 100)
  }
  
  const simulateDisconnection = () => {
    status.value = 'disconnected'
    error.value = new Error('Connection lost')
  }
  
  const simulateMessage = (message) => {
    if (status.value === 'connected') {
      data.value = message
    }
  }
  
  const simulateError = (errorMessage) => {
    status.value = 'error'
    error.value = new Error(errorMessage)
  }
  
  const cleanup = vi.fn()
  
  return {
    status,
    data,
    error,
    isConnected,
    isConnecting,
    isDisconnected,
    send,
    close,
    reconnect,
    cleanup,
    // Test helpers
    simulateConnection,
    simulateDisconnection,
    simulateMessage,
    simulateError
  }
}

// Mock execution flow scenarios
export const createExecutionFlowScenarios = () => {
  const scenarios = {
    // Successful execution with progress updates
    successfulExecution: [
      mockWebSocketMessages.executionStarted,
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 1,
        message: 'Initializing trading agent...'
      },
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 2,
        message: 'Loading market data...'
      },
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 3,
        message: 'Analyzing price patterns...'
      },
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 4,
        message: 'Generating recommendations...'
      },
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 5,
        message: 'Finalizing results...'
      },
      mockWebSocketMessages.executionCompleted
    ],
    
    // Failed execution
    failedExecution: [
      mockWebSocketMessages.executionStarted,
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 1,
        message: 'Initializing trading agent...'
      },
      {
        ...mockWebSocketMessages.executionProgress,
        current_step: 2,
        message: 'Loading market data...'
      },
      mockWebSocketMessages.executionFailed
    ],
    
    // Execution with no recommendations
    noRecommendationsExecution: [
      mockWebSocketMessages.executionStarted,
      {
        ...mockWebSocketMessages.executionCompleted,
        recommendations: [],
        summary: {
          total_recommendations: 0,
          high_confidence_count: 0,
          estimated_profit: 0
        }
      }
    ]
  }
  
  return scenarios
}

// Helper to simulate execution flow
export const simulateExecutionFlow = async (mockWebSocket, scenario, delay = 500) => {
  for (let i = 0; i < scenario.length; i++) {
    await new Promise(resolve => setTimeout(resolve, delay))
    mockWebSocket.simulateMessage(scenario[i])
  }
}

// Mock WebSocket server for testing
export class MockWebSocketServer {
  constructor() {
    this.clients = new Set()
    this.messageHandlers = new Map()
  }
  
  addClient(client) {
    this.clients.add(client)
  }
  
  removeClient(client) {
    this.clients.delete(client)
  }
  
  broadcast(message) {
    this.clients.forEach(client => {
      client.simulateMessage(message)
    })
  }
  
  sendToClient(clientId, message) {
    const client = Array.from(this.clients)[clientId]
    if (client) {
      client.simulateMessage(message)
    }
  }
  
  onMessage(type, handler) {
    this.messageHandlers.set(type, handler)
  }
  
  handleClientMessage(client, message) {
    const handler = this.messageHandlers.get(message.type)
    if (handler) {
      handler(client, message)
    }
  }
}

// Create mock useWebSocket composable
export const createMockUseWebSocket = () => {
  return vi.fn((url, options = {}) => {
    const mockWs = createMockWebSocket('connecting')
    
    // Simulate connection after a delay
    setTimeout(() => {
      if (mockWs.status.value === 'connecting') {
        mockWs.status.value = 'connected'
      }
    }, 100)
    
    // Call onOpen callback if provided
    if (options.onOpen) {
      setTimeout(() => {
        if (mockWs.status.value === 'connected') {
          options.onOpen()
        }
      }, 150)
    }
    
    return mockWs
  })
}

// Helper to test WebSocket reconnection logic
export const testReconnectionScenario = async (mockWebSocket, reconnectAttempts = 3) => {
  // Simulate initial disconnection
  mockWebSocket.simulateDisconnection()
  
  // Simulate reconnection attempts
  for (let i = 0; i < reconnectAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (i === reconnectAttempts - 1) {
      // Successful reconnection on last attempt
      mockWebSocket.simulateConnection()
    } else {
      // Failed reconnection attempts
      mockWebSocket.simulateError(`Reconnection attempt ${i + 1} failed`)
    }
  }
}

export default {
  mockWebSocketMessages,
  createMockWebSocket,
  createExecutionFlowScenarios,
  simulateExecutionFlow,
  MockWebSocketServer,
  createMockUseWebSocket,
  testReconnectionScenario
}