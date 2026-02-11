import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import LineChart from '../LineChart.vue'

// Mock Chart.js
vi.mock('chart.js', () => ({
  Chart: vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
    update: vi.fn(),
    resize: vi.fn()
  })),
  registerables: [],
  defaults: {
    plugins: {
      legend: {},
      tooltip: {}
    }
  }
}))

describe('LineChart', () => {
  const defaultProps = {
    data: {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
      datasets: [{
        label: 'Portfolio Value',
        data: [10000, 12000, 11500, 13000, 14500],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)'
      }]
    }
  }

  it('renders chart canvas element', () => {
    const wrapper = mount(LineChart, {
      props: defaultProps
    })
    
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('creates Chart instance on mount', () => {
    const { Chart } = require('chart.js')
    
    mount(LineChart, {
      props: defaultProps
    })
    
    expect(Chart).toHaveBeenCalledOnce()
  })

  it('applies custom height when provided', () => {
    const wrapper = mount(LineChart, {
      props: {
        ...defaultProps,
        height: 300
      }
    })
    
    const canvas = wrapper.find('canvas')
    expect(canvas.attributes('height')).toBe('300')
  })

  it('applies custom width when provided', () => {
    const wrapper = mount(LineChart, {
      props: {
        ...defaultProps,
        width: 800
      }
    })
    
    const canvas = wrapper.find('canvas')
    expect(canvas.attributes('width')).toBe('800')
  })

  it('uses responsive sizing by default', () => {
    const wrapper = mount(LineChart, {
      props: defaultProps
    })
    
    expect(wrapper.find('.relative').exists()).toBe(true)
  })

  it('updates chart when data changes', async () => {
    const { Chart } = require('chart.js')
    const mockUpdate = vi.fn()
    Chart.mockImplementation(() => ({
      destroy: vi.fn(),
      update: mockUpdate,
      resize: vi.fn()
    }))

    const wrapper = mount(LineChart, {
      props: defaultProps
    })

    // Change data
    await wrapper.setProps({
      data: {
        ...defaultProps.data,
        datasets: [{
          ...defaultProps.data.datasets[0],
          data: [15000, 16000, 17000, 18000, 19000]
        }]
      }
    })

    expect(mockUpdate).toHaveBeenCalled()
  })

  it('destroys chart instance when component unmounts', () => {
    const mockDestroy = vi.fn()
    const { Chart } = require('chart.js')
    Chart.mockImplementation(() => ({
      destroy: mockDestroy,
      update: vi.fn(),
      resize: vi.fn()
    }))

    const wrapper = mount(LineChart, {
      props: defaultProps
    })

    wrapper.unmount()

    expect(mockDestroy).toHaveBeenCalled()
  })

  it('passes custom options to Chart.js', () => {
    const { Chart } = require('chart.js')
    const customOptions = {
      plugins: {
        legend: {
          display: false
        }
      }
    }

    mount(LineChart, {
      props: {
        ...defaultProps,
        options: customOptions
      }
    })

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    expect(chartCall[1].options).toMatchObject(customOptions)
  })

  it('handles responsive behavior correctly', () => {
    const { Chart } = require('chart.js')
    
    mount(LineChart, {
      props: {
        ...defaultProps,
        responsive: true
      }
    })

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    expect(chartCall[1].options.responsive).toBe(true)
  })

  it('applies theme-aware colors in light mode', () => {
    const wrapper = mount(LineChart, {
      props: defaultProps,
      global: {
        provide: {
          theme: 'light'
        }
      }
    })
    
    const { Chart } = require('chart.js')
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    
    // Should use light theme colors
    expect(chartCall[1].options.scales.x.grid.color).toContain('rgb(229, 231, 235)')
  })

  it('applies theme-aware colors in dark mode', () => {
    const wrapper = mount(LineChart, {
      props: defaultProps,
      global: {
        provide: {
          theme: 'dark'
        }
      }
    })
    
    const { Chart } = require('chart.js')
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    
    // Should use dark theme colors
    expect(chartCall[1].options.scales.x.grid.color).toContain('rgb(55, 65, 81)')
  })

  it('handles loading state correctly', () => {
    const wrapper = mount(LineChart, {
      props: {
        ...defaultProps,
        loading: true
      }
    })
    
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
    expect(wrapper.find('.bg-gray-200').exists()).toBe(true)
  })

  it('shows empty state when no data provided', () => {
    const wrapper = mount(LineChart, {
      props: {
        data: {
          labels: [],
          datasets: []
        }
      }
    })
    
    expect(wrapper.text()).toContain('No data available')
  })

  it('handles error state correctly', () => {
    const wrapper = mount(LineChart, {
      props: {
        ...defaultProps,
        error: 'Failed to load chart data'
      }
    })
    
    expect(wrapper.text()).toContain('Failed to load chart data')
    expect(wrapper.find('.text-red-600').exists()).toBe(true)
  })

  it('resizes chart when container size changes', async () => {
    const mockResize = vi.fn()
    const { Chart } = require('chart.js')
    Chart.mockImplementation(() => ({
      destroy: vi.fn(),
      update: vi.fn(),
      resize: mockResize
    }))

    // Mock ResizeObserver
    const mockObserver = {
      observe: vi.fn(),
      disconnect: vi.fn()
    }
    global.ResizeObserver = vi.fn(() => mockObserver)

    const wrapper = mount(LineChart, {
      props: defaultProps
    })

    // Simulate ResizeObserver callback
    const resizeCallback = global.ResizeObserver.mock.calls[0][0]
    resizeCallback([{ contentRect: { width: 800, height: 400 } }])

    await wrapper.vm.$nextTick()

    expect(mockResize).toHaveBeenCalled()
  })

  it('applies custom CSS classes', () => {
    const wrapper = mount(LineChart, {
      props: {
        ...defaultProps,
        class: 'custom-chart-class'
      }
    })
    
    expect(wrapper.classes()).toContain('custom-chart-class')
  })

  it('handles animation configuration', () => {
    const { Chart } = require('chart.js')
    
    mount(LineChart, {
      props: {
        ...defaultProps,
        animated: false
      }
    })

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    expect(chartCall[1].options.animation).toBe(false)
  })

  it('supports multiple datasets', () => {
    const multiDatasetProps = {
      data: {
        labels: ['Jan', 'Feb', 'Mar'],
        datasets: [
          {
            label: 'Portfolio A',
            data: [10000, 12000, 11500],
            borderColor: 'rgb(59, 130, 246)'
          },
          {
            label: 'Portfolio B',
            data: [8000, 9500, 10200],
            borderColor: 'rgb(16, 185, 129)'
          }
        ]
      }
    }

    const { Chart } = require('chart.js')
    mount(LineChart, {
      props: multiDatasetProps
    })

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1]
    expect(chartCall[1].data.datasets).toHaveLength(2)
  })
})