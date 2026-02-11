// Test utilities for Vue components

import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'

// Mock router for testing
export const createMockRouter = (routes = []) => {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/portfolios', component: { template: '<div>Portfolios</div>' } },
      { path: '/portfolio/:name', component: { template: '<div>Portfolio Detail</div>' } },
      { path: '/trades', component: { template: '<div>Trades</div>' } },
      { path: '/comparison', component: { template: '<div>Comparison</div>' } },
      { path: '/system', component: { template: '<div>System</div>' } },
      ...routes
    ]
  })
  return router
}

// Mount component with common providers
export const mountComponent = (component, options = {}) => {
  const pinia = createPinia()
  setActivePinia(pinia)
  
  const router = createMockRouter()
  
  const defaultGlobal = {
    plugins: [pinia, router],
    stubs: {
      'router-link': true,
      'router-view': true
    }
  }
  
  return mount(component, {
    global: {
      ...defaultGlobal,
      ...options.global
    },
    ...options
  })
}

// Mock API responses
export const mockApiResponses = {
  portfolios: [
    {
      name: 'test-portfolio',
      strategy: 'momentum',
      cash_balance: 10000,
      positions: {
        'AAPL': { shares: 10, price: 150 },
        'GOOGL': { shares: 5, price: 200 }
      },
      last_updated: '2026-02-11T00:00:00Z'
    }
  ],
  dashboard: {
    total_portfolios: 3,
    active_executions: 1,
    pending_trades: 5,
    total_value: 50000,
    daily_pnl: 250,
    recent_executions: []
  },
  pendingTrades: [
    {
      id: 'trade-1',
      symbol: 'AAPL',
      action: 'BUY',
      quantity: 100,
      price: 150.50,
      portfolio: 'test-portfolio',
      timestamp: '2026-02-11T00:00:00Z'
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
      websocket: 'running'
    }
  }
}

// Mock WebSocket
export class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    
    // Simulate connection
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      if (this.onopen) this.onopen()
    }, 0)
  }
  
  send(data) {
    // Mock send
  }
  
  close() {
    this.readyState = WebSocket.CLOSED
    if (this.onclose) this.onclose()
  }
  
  // Helper to simulate receiving messages
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) })
    }
  }
}

// Mock axios for API calls
export const mockAxios = {
  get: vi.fn(),
  post: vi.fn(), 
  put: vi.fn(),
  delete: vi.fn(),
  defaults: {
    baseURL: 'http://localhost:8000'
  }
}

// Wait for Vue's nextTick and additional ticks for async operations
export const flushPromises = () => {
  return new Promise(resolve => {
    setTimeout(resolve, 0)
  })
}