import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ConnectionStatus from '../ConnectionStatus.vue'

describe('ConnectionStatus', () => {
  it('shows connected status correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected'
      }
    })
    
    expect(wrapper.text()).toContain('Connected')
    expect(wrapper.find('.bg-green-100').exists()).toBe(true)
    expect(wrapper.find('.text-green-800').exists()).toBe(true)
  })

  it('shows disconnected status correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'disconnected'
      }
    })
    
    expect(wrapper.text()).toContain('Disconnected')
    expect(wrapper.find('.bg-red-100').exists()).toBe(true)
    expect(wrapper.find('.text-red-800').exists()).toBe(true)
  })

  it('shows connecting status correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connecting'
      }
    })
    
    expect(wrapper.text()).toContain('Connecting')
    expect(wrapper.find('.bg-yellow-100').exists()).toBe(true)
    expect(wrapper.find('.text-yellow-800').exists()).toBe(true)
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
  })

  it('shows reconnecting status correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'reconnecting'
      }
    })
    
    expect(wrapper.text()).toContain('Reconnecting')
    expect(wrapper.find('.bg-blue-100').exists()).toBe(true)
    expect(wrapper.find('.text-blue-800').exists()).toBe(true)
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
  })

  it('shows error status correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'error'
      }
    })
    
    expect(wrapper.text()).toContain('Error')
    expect(wrapper.find('.bg-red-100').exists()).toBe(true)
    expect(wrapper.find('.text-red-800').exists()).toBe(true)
  })

  it('displays custom message when provided', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        message: 'WebSocket connection active'
      }
    })
    
    expect(wrapper.text()).toContain('WebSocket connection active')
  })

  it('shows last connected time when provided', () => {
    const lastConnected = new Date('2026-02-11T10:30:00Z')
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'disconnected',
        lastConnected: lastConnected
      }
    })
    
    expect(wrapper.text()).toContain('Last connected')
  })

  it('shows retry count when provided', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'reconnecting',
        retryCount: 3
      }
    })
    
    expect(wrapper.text()).toContain('Attempt 3')
  })

  it('shows connection type when provided', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        connectionType: 'WebSocket'
      }
    })
    
    expect(wrapper.text()).toContain('WebSocket')
  })

  it('renders with icon by default', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected'
      }
    })
    
    expect(wrapper.find('svg').exists()).toBe(true)
  })

  it('hides icon when showIcon is false', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        showIcon: false
      }
    })
    
    expect(wrapper.find('svg').exists()).toBe(false)
  })

  it('shows retry button when status is error or disconnected', () => {
    const errorWrapper = mount(ConnectionStatus, {
      props: {
        status: 'error',
        showRetryButton: true
      }
    })
    
    expect(errorWrapper.find('button').exists()).toBe(true)
    expect(errorWrapper.text()).toContain('Retry')

    const disconnectedWrapper = mount(ConnectionStatus, {
      props: {
        status: 'disconnected',
        showRetryButton: true
      }
    })
    
    expect(disconnectedWrapper.find('button').exists()).toBe(true)
  })

  it('does not show retry button when connected', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        showRetryButton: true
      }
    })
    
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('emits retry event when retry button clicked', async () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'error',
        showRetryButton: true
      }
    })
    
    const retryButton = wrapper.find('button')
    await retryButton.trigger('click')
    
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('applies compact styling when compact prop is true', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        compact: true
      }
    })
    
    expect(wrapper.classes()).toContain('text-sm')
    expect(wrapper.classes()).toContain('px-2')
  })

  it('applies full styling by default', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected'
      }
    })
    
    expect(wrapper.classes()).toContain('px-3')
    expect(wrapper.classes()).toContain('py-1')
  })

  it('updates status color and icon correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected'
      }
    })
    
    // Check connected state
    expect(wrapper.find('.bg-green-100').exists()).toBe(true)
    
    // Update to disconnected
    wrapper.setProps({ status: 'disconnected' })
    
    expect(wrapper.find('.bg-red-100').exists()).toBe(true)
  })

  it('shows connection latency when provided', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected',
        latency: 45
      }
    })
    
    expect(wrapper.text()).toContain('45ms')
  })

  it('applies dark mode classes correctly', () => {
    const wrapper = mount(ConnectionStatus, {
      props: {
        status: 'connected'
      }
    })
    
    expect(wrapper.classes()).toContain('dark:bg-green-900')
    expect(wrapper.classes()).toContain('dark:text-green-200')
  })
})