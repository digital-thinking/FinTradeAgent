// API mocking utilities for tests

import { vi } from 'vitest'

// Mock API responses
export const mockApiResponses = {
  portfolios: [
    {
      name: 'test-portfolio',
      strategy: 'momentum',
      cash_balance: 10000,
      total_value: 50000,
      positions: {
        'AAPL': { shares: 10, price: 150, value: 1500 },
        'GOOGL': { shares: 5, price: 200, value: 1000 }
      },
      performance: {
        daily_pnl: 250,
        daily_pnl_percent: 0.5,
        total_return: 5000,
        total_return_percent: 10.0
      },
      last_updated: '2026-02-11T00:00:00Z'
    }
  ],

  dashboard: {
    total_portfolios: 3,
    active_executions: 1,
    pending_trades: 5,
    total_value: 150000,
    daily_pnl: 750,
    daily_pnl_percent: 0.5,
    recent_executions: [
      {
        id: 'exec-1',
        portfolio: 'test-portfolio',
        status: 'completed',
        timestamp: '2026-02-11T09:00:00Z',
        duration: 300
      }
    ],
    performance_history: [
      { date: '2026-02-10', value: 148000 },
      { date: '2026-02-11', value: 150000 }
    ]
  },

  pendingTrades: [
    {
      id: 'trade-1',
      symbol: 'AAPL',
      action: 'BUY',
      quantity: 100,
      price: 150.50,
      portfolio: 'test-portfolio',
      timestamp: '2026-02-11T00:00:00Z',
      reason: 'Technical breakout pattern'
    }
  ],

  systemHealth: {
    status: 'healthy',
    uptime: 86400,
    memory_usage: 0.65,
    cpu_usage: 0.25,
    services: {
      api: 'running',
      scheduler: 'running',
      websocket: 'running',
      database: 'running'
    },
    market_data_status: 'connected',
    last_updated: '2026-02-11T10:00:00Z'
  },

  executionLogs: [
    {
      id: 'exec-1',
      portfolio: 'test-portfolio',
      status: 'completed',
      start_time: '2026-02-11T09:00:00Z',
      end_time: '2026-02-11T09:05:00Z',
      steps_completed: 5,
      total_steps: 5,
      recommendations_generated: 3,
      trades_executed: 2,
      error_message: null
    }
  ]
}

// Create mock API client
export const createMockApi = () => {
  const mockApi = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: {
      baseURL: 'http://localhost:8000'
    }
  }

  // Default successful responses
  mockApi.get.mockImplementation((url) => {
    if (url === '/api/portfolios/') {
      return Promise.resolve({ data: mockApiResponses.portfolios })
    }
    if (url.startsWith('/api/portfolios/')) {
      const name = url.split('/').pop()
      const portfolio = mockApiResponses.portfolios.find(p => p.name === name)
      return Promise.resolve({ data: portfolio || mockApiResponses.portfolios[0] })
    }
    if (url === '/api/analytics/dashboard') {
      return Promise.resolve({ data: mockApiResponses.dashboard })
    }
    if (url === '/api/trades/pending') {
      return Promise.resolve({ data: mockApiResponses.pendingTrades })
    }
    if (url === '/api/system/health') {
      return Promise.resolve({ data: mockApiResponses.systemHealth })
    }
    if (url === '/api/analytics/execution-logs') {
      return Promise.resolve({ data: mockApiResponses.executionLogs })
    }
    
    return Promise.resolve({ data: {} })
  })

  mockApi.post.mockImplementation((url, data) => {
    if (url === '/api/portfolios/') {
      return Promise.resolve({ 
        data: { 
          ...data, 
          id: 'new-portfolio-id',
          created_at: new Date().toISOString()
        }
      })
    }
    if (url.includes('/execute')) {
      return Promise.resolve({ 
        data: { 
          execution_id: 'exec-' + Date.now(),
          status: 'started'
        }
      })
    }
    if (url.includes('/apply')) {
      return Promise.resolve({ data: { success: true } })
    }
    
    return Promise.resolve({ data: { success: true } })
  })

  mockApi.put.mockResolvedValue({ data: { success: true } })
  mockApi.delete.mockResolvedValue({ data: { success: true } })

  return mockApi
}

// API error scenarios
export const createApiErrorScenarios = () => ({
  networkError: () => Promise.reject(new Error('Network Error')),
  
  serverError: () => Promise.reject({
    response: {
      status: 500,
      statusText: 'Internal Server Error',
      data: { error: 'Server encountered an error' }
    }
  }),
  
  notFoundError: () => Promise.reject({
    response: {
      status: 404,
      statusText: 'Not Found',
      data: { error: 'Resource not found' }
    }
  }),
  
  validationError: () => Promise.reject({
    response: {
      status: 400,
      statusText: 'Bad Request',
      data: { 
        error: 'Validation failed',
        details: {
          name: ['Portfolio name is required'],
          cash_balance: ['Must be a positive number']
        }
      }
    }
  }),
  
  authError: () => Promise.reject({
    response: {
      status: 401,
      statusText: 'Unauthorized',
      data: { error: 'Authentication required' }
    }
  })
})

// Helper to simulate API delays
export const withDelay = (response, delay = 100) => {
  return new Promise(resolve => {
    setTimeout(() => resolve(response), delay)
  })
}

// Mock specific API endpoints with custom responses
export const mockApiEndpoint = (mockApi, endpoint, response, method = 'get') => {
  mockApi[method].mockImplementation((url, ...args) => {
    if (url === endpoint || url.includes(endpoint)) {
      return typeof response === 'function' ? response(...args) : Promise.resolve({ data: response })
    }
    return mockApi[method].getMockImplementation()(url, ...args)
  })
}

// Reset all API mocks
export const resetApiMocks = (mockApi) => {
  Object.keys(mockApi).forEach(key => {
    if (typeof mockApi[key] === 'function' && mockApi[key].mockClear) {
      mockApi[key].mockClear()
    }
  })
}