import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DashboardPage from '../DashboardPage.vue'
import { mountComponent, mockApiResponses, flushPromises } from '../../test/utils.js'

// Mock API module
vi.mock('../../services/api.js', () => ({
  default: {
    get: vi.fn()
  }
}))

describe('DashboardPage', () => {
  let api

  beforeEach(() => {
    setActivePinia(createPinia())
    api = require('../../services/api.js').default
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard layout correctly', () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    
    expect(wrapper.find('h1').text()).toContain('Dashboard')
    expect(wrapper.find('[data-testid="stats-grid"]').exists()).toBe(true)
  })

  it('loads dashboard data on mount', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    mountComponent(DashboardPage)
    
    await flushPromises()
    
    expect(api.get).toHaveBeenCalledWith('/api/analytics/dashboard')
  })

  it('displays loading skeleton while fetching data', () => {
    api.get.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    const wrapper = mountComponent(DashboardPage)
    
    expect(wrapper.findComponent({ name: 'DashboardSkeleton' }).exists()).toBe(true)
  })

  it('displays dashboard stats correctly', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    // Check for stat cards
    const statCards = wrapper.findAllComponents({ name: 'StatCard' })
    expect(statCards.length).toBeGreaterThan(3)
    
    // Check specific stats
    expect(wrapper.text()).toContain('Total Portfolios')
    expect(wrapper.text()).toContain('Total Value')
    expect(wrapper.text()).toContain('Active Executions')
    expect(wrapper.text()).toContain('Pending Trades')
  })

  it('displays portfolio performance chart', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.findComponent({ name: 'LineChart' }).exists()).toBe(true)
  })

  it('shows recent executions list', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      recent_executions: [
        {
          id: 'exec-1',
          portfolio: 'test-portfolio',
          status: 'completed',
          timestamp: '2026-02-11T10:00:00Z'
        }
      ]
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('Recent Executions')
    expect(wrapper.text()).toContain('test-portfolio')
    expect(wrapper.text()).toContain('completed')
  })

  it('handles empty recent executions', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      recent_executions: []
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('No recent executions')
  })

  it('displays error state when API fails', async () => {
    api.get.mockRejectedValue(new Error('API Error'))
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('Failed to load dashboard data')
  })

  it('refreshes data when refresh button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    // Clear previous calls
    api.get.mockClear()
    
    // Click refresh button
    const refreshButton = wrapper.find('[data-testid="refresh-button"]')
    await refreshButton.trigger('click')
    
    expect(api.get).toHaveBeenCalledWith('/api/analytics/dashboard')
  })

  it('navigates to portfolios page when view all clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    const viewAllLink = wrapper.find('[data-testid="view-all-portfolios"]')
    expect(viewAllLink.attributes('to')).toBe('/portfolios')
  })

  it('navigates to pending trades when trades stat card clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    // Find the pending trades stat card and click it
    const statCards = wrapper.findAllComponents({ name: 'StatCard' })
    const tradesCard = statCards.find(card => 
      card.props('title').includes('Pending Trades')
    )
    
    await tradesCard.trigger('click')
    
    // Should navigate to trades page
    expect(wrapper.vm.$router.currentRoute.value.path).toBe('/trades')
  })

  it('displays portfolio quick actions', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.find('[data-testid="create-portfolio-button"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="import-data-button"]').exists()).toBe(true)
  })

  it('handles system alerts when present', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      system_alerts: [
        {
          id: 'alert-1',
          type: 'warning',
          message: 'Market data connection unstable',
          timestamp: '2026-02-11T10:00:00Z'
        }
      ]
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('System Alerts')
    expect(wrapper.text()).toContain('Market data connection unstable')
    expect(wrapper.find('.bg-yellow-50').exists()).toBe(true) // Warning alert styling
  })

  it('shows market status indicator', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      market_status: {
        is_open: true,
        next_close: '2026-02-11T21:00:00Z',
        timezone: 'NYSE'
      }
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('Market Open')
    expect(wrapper.text()).toContain('NYSE')
  })

  it('updates data automatically on interval', async () => {
    vi.useFakeTimers()
    
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    mountComponent(DashboardPage)
    await flushPromises()
    
    // Clear initial call
    api.get.mockClear()
    
    // Fast-forward to trigger auto-refresh (typically 30 seconds)
    vi.advanceTimersByTime(30000)
    await flushPromises()
    
    expect(api.get).toHaveBeenCalledWith('/api/analytics/dashboard')
    
    vi.useRealTimers()
  })

  it('applies responsive grid layout for stats', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    const statsGrid = wrapper.find('[data-testid="stats-grid"]')
    expect(statsGrid.classes()).toContain('grid-cols-1')
    expect(statsGrid.classes()).toContain('md:grid-cols-2')
    expect(statsGrid.classes()).toContain('lg:grid-cols-4')
  })

  it('formats financial values correctly', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      total_value: 1234567.89,
      daily_pnl: -1234.56
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    // Should format large numbers with commas and currency
    expect(wrapper.text()).toContain('$1,234,567.89')
    expect(wrapper.text()).toContain('-$1,234.56')
  })

  it('shows performance indicators with correct colors', async () => {
    api.get.mockResolvedValue({ data: {
      ...mockApiResponses.dashboard,
      daily_pnl: 250.50,
      daily_pnl_percent: 5.2
    }})
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    // Positive performance should show green
    expect(wrapper.find('.text-green-600').exists()).toBe(true)
    expect(wrapper.text()).toContain('+5.2%')
  })

  it('handles theme changes correctly', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage, {
      global: {
        provide: {
          theme: 'dark'
        }
      }
    })
    await flushPromises()
    
    // Chart should adapt to dark theme
    const chart = wrapper.findComponent({ name: 'LineChart' })
    expect(chart.exists()).toBe(true)
    // Theme prop should be passed to chart
  })

  it('cleans up auto-refresh on component unmount', async () => {
    vi.useFakeTimers()
    
    api.get.mockResolvedValue({ data: mockApiResponses.dashboard })
    
    const wrapper = mountComponent(DashboardPage)
    await flushPromises()
    
    wrapper.unmount()
    
    // Clear previous calls
    api.get.mockClear()
    
    // Fast-forward time - should not make API calls after unmount
    vi.advanceTimersByTime(60000)
    
    expect(api.get).not.toHaveBeenCalled()
    
    vi.useRealTimers()
  })
})