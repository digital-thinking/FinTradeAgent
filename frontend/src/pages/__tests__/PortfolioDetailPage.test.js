import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import PortfolioDetailPage from '../PortfolioDetailPage.vue'
import { mountComponent, mockApiResponses, MockWebSocket, flushPromises } from '../../test/utils.js'

// Mock API and WebSocket
vi.mock('../../services/api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('../../composables/useWebSocket.js', () => ({
  useWebSocket: vi.fn()
}))

describe('PortfolioDetailPage', () => {
  let api, mockWebSocket, useWebSocketMock

  beforeEach(() => {
    setActivePinia(createPinia())
    api = require('../../services/api.js').default
    
    // Mock WebSocket composable
    mockWebSocket = {
      status: { value: 'disconnected' },
      data: { value: null },
      error: { value: null },
      isConnected: { value: false },
      send: vi.fn(),
      close: vi.fn(),
      reconnect: vi.fn()
    }
    
    useWebSocketMock = require('../../composables/useWebSocket.js').useWebSocket
    useWebSocketMock.mockReturnValue(mockWebSocket)
    
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders portfolio detail layout', () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: {
            params: { name: 'test-portfolio' }
          }
        }
      }
    })
    
    expect(wrapper.find('h1').text()).toContain('Portfolio Details')
    expect(wrapper.find('[data-testid="portfolio-overview"]').exists()).toBe(true)
  })

  it('loads portfolio data based on route parameter', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: {
            params: { name: 'test-portfolio' }
          }
        }
      }
    })
    
    await flushPromises()
    
    expect(api.get).toHaveBeenCalledWith('/api/portfolios/test-portfolio')
  })

  it('displays portfolio information correctly', async () => {
    const portfolioData = {
      name: 'growth-strategy',
      strategy: 'growth',
      cash_balance: 15000,
      total_value: 85000,
      positions: {
        'AAPL': { shares: 100, price: 180, value: 18000 },
        'GOOGL': { shares: 20, price: 150, value: 3000 }
      },
      performance: {
        daily_pnl: 850,
        daily_pnl_percent: 1.2,
        total_return: 12500,
        total_return_percent: 17.2
      }
    }
    
    api.get.mockResolvedValue({ data: portfolioData })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'growth-strategy' } }
        }
      }
    })
    await flushPromises()
    
    expect(wrapper.text()).toContain('growth-strategy')
    expect(wrapper.text()).toContain('$85,000')
    expect(wrapper.text()).toContain('Growth')
    expect(wrapper.text()).toContain('+$850')
    expect(wrapper.text()).toContain('+1.2%')
  })

  it('displays portfolio positions table', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.portfolios[0],
      positions: {
        'AAPL': { shares: 100, price: 180, value: 18000 },
        'GOOGL': { shares: 50, price: 150, value: 7500 },
        'MSFT': { shares: 25, price: 300, value: 7500 }
      }
    }})
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    expect(wrapper.text()).toContain('AAPL')
    expect(wrapper.text()).toContain('GOOGL')
    expect(wrapper.text()).toContain('MSFT')
    expect(wrapper.text()).toContain('100 shares')
    expect(wrapper.text()).toContain('$180.00')
  })

  it('connects to WebSocket for live updates', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    expect(useWebSocketMock).toHaveBeenCalledWith(
      'ws://localhost:8000/ws/agents/test-portfolio',
      expect.any(Object)
    )
  })

  it('displays WebSocket connection status', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    mockWebSocket.status.value = 'connected'
    mockWebSocket.isConnected.value = true
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    expect(wrapper.findComponent({ name: 'ConnectionStatus' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'ConnectionStatus' }).props('status')).toBe('connected')
  })

  it('starts agent execution when execute button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    api.post.mockResolvedValue({ data: { execution_id: 'exec-123', status: 'started' } })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    const executeButton = wrapper.find('[data-testid="execute-agent-button"]')
    await executeButton.trigger('click')
    
    expect(api.post).toHaveBeenCalledWith('/api/agents/test-portfolio/execute')
  })

  it('displays execution progress when agent is running', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Simulate WebSocket execution update
    mockWebSocket.data.value = {
      type: 'execution_progress',
      status: 'running',
      current_step: 2,
      total_steps: 5,
      message: 'Analyzing market data...'
    }
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.findComponent({ name: 'ExecutionProgress' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('Analyzing market data...')
  })

  it('handles WebSocket execution messages', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Simulate different WebSocket messages
    const messages = [
      {
        type: 'execution_started',
        execution_id: 'exec-123',
        timestamp: '2026-02-11T10:00:00Z'
      },
      {
        type: 'execution_progress',
        status: 'running',
        current_step: 1,
        total_steps: 4,
        message: 'Loading market data...'
      },
      {
        type: 'execution_completed',
        status: 'completed',
        recommendations: [
          {
            symbol: 'AAPL',
            action: 'BUY',
            quantity: 10,
            reason: 'Strong momentum signals'
          }
        ]
      }
    ]
    
    for (const message of messages) {
      mockWebSocket.data.value = message
      await wrapper.vm.$nextTick()
    }
    
    expect(wrapper.text()).toContain('AAPL')
    expect(wrapper.text()).toContain('BUY')
    expect(wrapper.text()).toContain('Strong momentum signals')
  })

  it('displays execution history in separate tab', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    api.get.mockResolvedValue({ 
      data: [
        {
          id: 'exec-1',
          status: 'completed',
          start_time: '2026-02-11T09:00:00Z',
          end_time: '2026-02-11T09:05:00Z',
          recommendations_count: 3
        }
      ]
    })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Click execution history tab
    const historyTab = wrapper.find('[data-testid="execution-history-tab"]')
    await historyTab.trigger('click')
    
    expect(wrapper.text()).toContain('Execution History')
    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('3 recommendations')
  })

  it('shows trade recommendations when execution completes', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Simulate execution completion with recommendations
    mockWebSocket.data.value = {
      type: 'execution_completed',
      status: 'completed',
      recommendations: [
        {
          id: 'trade-1',
          symbol: 'AAPL',
          action: 'BUY',
          quantity: 50,
          price: 180.50,
          reason: 'Technical breakout pattern detected'
        },
        {
          id: 'trade-2',
          symbol: 'GOOGL',
          action: 'SELL',
          quantity: 20,
          price: 150.25,
          reason: 'Overvalued based on fundamentals'
        }
      ]
    }
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('Trade Recommendations')
    expect(wrapper.text()).toContain('AAPL')
    expect(wrapper.text()).toContain('BUY 50 shares')
    expect(wrapper.text()).toContain('Technical breakout pattern detected')
  })

  it('applies trade recommendations when approved', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    api.post.mockResolvedValue({ data: { success: true } })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Set up recommendations
    mockWebSocket.data.value = {
      type: 'execution_completed',
      recommendations: [
        { id: 'trade-1', symbol: 'AAPL', action: 'BUY', quantity: 50 }
      ]
    }
    await wrapper.vm.$nextTick()
    
    // Apply trade
    const applyButton = wrapper.find('[data-testid="apply-trade-trade-1"]')
    await applyButton.trigger('click')
    
    expect(api.post).toHaveBeenCalledWith('/api/trades/trade-1/apply')
  })

  it('handles execution errors gracefully', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Simulate execution error
    mockWebSocket.data.value = {
      type: 'execution_error',
      status: 'failed',
      error: 'Market data connection failed',
      timestamp: '2026-02-11T10:00:00Z'
    }
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('Execution Failed')
    expect(wrapper.text()).toContain('Market data connection failed')
    expect(wrapper.find('[data-testid="retry-execution-button"]').exists()).toBe(true)
  })

  it('cancels running execution when stop button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    api.post.mockResolvedValue({ data: { success: true } })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Simulate running execution
    mockWebSocket.data.value = {
      type: 'execution_progress',
      status: 'running',
      execution_id: 'exec-123'
    }
    await wrapper.vm.$nextTick()
    
    const stopButton = wrapper.find('[data-testid="stop-execution-button"]')
    await stopButton.trigger('click')
    
    expect(api.post).toHaveBeenCalledWith('/api/agents/test-portfolio/stop')
  })

  it('displays portfolio performance chart', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.portfolios[0],
      performance_history: [
        { date: '2026-02-10', value: 48000 },
        { date: '2026-02-11', value: 50000 }
      ]
    }})
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    expect(wrapper.findComponent({ name: 'LineChart' }).exists()).toBe(true)
  })

  it('handles WebSocket reconnection', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    mockWebSocket.status.value = 'disconnected'
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    const reconnectButton = wrapper.find('[data-testid="reconnect-websocket"]')
    await reconnectButton.trigger('click')
    
    expect(mockWebSocket.reconnect).toHaveBeenCalled()
  })

  it('cleans up WebSocket connection on component unmount', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    wrapper.unmount()
    
    expect(mockWebSocket.close).toHaveBeenCalled()
  })

  it('shows scheduling controls for automated execution', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.portfolios[0],
      schedule: {
        enabled: true,
        frequency: 'daily',
        time: '09:30'
      }
    }})
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    expect(wrapper.find('[data-testid="schedule-section"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Automated Execution')
    expect(wrapper.text()).toContain('Daily at 09:30')
  })

  it('updates schedule when configuration changed', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios[0] })
    api.put.mockResolvedValue({ data: { success: true } })
    
    const wrapper = mountComponent(PortfolioDetailPage, {
      global: {
        mocks: {
          $route: { params: { name: 'test-portfolio' } }
        }
      }
    })
    await flushPromises()
    
    // Open schedule modal
    const scheduleButton = wrapper.find('[data-testid="configure-schedule-button"]')
    await scheduleButton.trigger('click')
    
    // Update schedule
    const frequencySelect = wrapper.find('[data-testid="schedule-frequency"]')
    const timeInput = wrapper.find('[data-testid="schedule-time"]')
    
    await frequencySelect.setValue('weekly')
    await timeInput.setValue('10:00')
    
    const saveButton = wrapper.find('[data-testid="save-schedule-button"]')
    await saveButton.trigger('click')
    
    expect(api.put).toHaveBeenCalledWith('/api/portfolios/test-portfolio/schedule', {
      enabled: true,
      frequency: 'weekly',
      time: '10:00'
    })
  })
})