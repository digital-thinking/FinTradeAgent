import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ToastNotification from '../ToastNotification.vue'

describe('ToastNotification', () => {
  const defaultProps = {
    message: 'Test notification message',
    type: 'info'
  }

  it('renders notification message', () => {
    const wrapper = mount(ToastNotification, {
      props: defaultProps
    })
    
    expect(wrapper.text()).toContain('Test notification message')
  })

  it('applies correct styling for info type', () => {
    const wrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'info' }
    })
    
    expect(wrapper.classes()).toContain('bg-blue-50')
    expect(wrapper.find('.text-blue-600').exists()).toBe(true)
  })

  it('applies correct styling for success type', () => {
    const wrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'success' }
    })
    
    expect(wrapper.classes()).toContain('bg-green-50')
    expect(wrapper.find('.text-green-600').exists()).toBe(true)
  })

  it('applies correct styling for warning type', () => {
    const wrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'warning' }
    })
    
    expect(wrapper.classes()).toContain('bg-yellow-50')
    expect(wrapper.find('.text-yellow-600').exists()).toBe(true)
  })

  it('applies correct styling for error type', () => {
    const wrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'error' }
    })
    
    expect(wrapper.classes()).toContain('bg-red-50')
    expect(wrapper.find('.text-red-600').exists()).toBe(true)
  })

  it('shows close button by default', () => {
    const wrapper = mount(ToastNotification, {
      props: defaultProps
    })
    
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('hides close button when dismissible is false', () => {
    const wrapper = mount(ToastNotification, {
      props: { ...defaultProps, dismissible: false }
    })
    
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('emits dismiss event when close button clicked', async () => {
    const wrapper = mount(ToastNotification, {
      props: defaultProps
    })
    
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('dismiss')).toHaveLength(1)
  })

  it('displays title when provided', () => {
    const wrapper = mount(ToastNotification, {
      props: { 
        ...defaultProps,
        title: 'Notification Title'
      }
    })
    
    expect(wrapper.text()).toContain('Notification Title')
  })

  it('renders appropriate icon for each type', () => {
    // Info icon
    const infoWrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'info' }
    })
    expect(infoWrapper.find('svg').exists()).toBe(true)

    // Success icon  
    const successWrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'success' }
    })
    expect(successWrapper.find('svg').exists()).toBe(true)

    // Warning icon
    const warningWrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'warning' }
    })
    expect(warningWrapper.find('svg').exists()).toBe(true)

    // Error icon
    const errorWrapper = mount(ToastNotification, {
      props: { ...defaultProps, type: 'error' }
    })
    expect(errorWrapper.find('svg').exists()).toBe(true)
  })

  it('auto-dismisses after timeout when duration is set', async () => {
    vi.useFakeTimers()
    
    const wrapper = mount(ToastNotification, {
      props: { 
        ...defaultProps,
        duration: 1000
      }
    })

    expect(wrapper.emitted('dismiss')).toBeFalsy()
    
    // Fast-forward time
    vi.advanceTimersByTime(1000)
    
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('dismiss')).toHaveLength(1)
    
    vi.useRealTimers()
  })

  it('does not auto-dismiss when duration is 0', async () => {
    vi.useFakeTimers()
    
    const wrapper = mount(ToastNotification, {
      props: { 
        ...defaultProps,
        duration: 0
      }
    })

    // Fast-forward time significantly
    vi.advanceTimersByTime(5000)
    
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('dismiss')).toBeFalsy()
    
    vi.useRealTimers()
  })

  it('applies correct positioning classes', () => {
    const wrapper = mount(ToastNotification, {
      props: defaultProps
    })
    
    expect(wrapper.classes()).toContain('fixed')
    expect(wrapper.classes()).toContain('top-4')
    expect(wrapper.classes()).toContain('right-4')
    expect(wrapper.classes()).toContain('z-50')
  })

  it('handles action button when provided', async () => {
    const wrapper = mount(ToastNotification, {
      props: { 
        ...defaultProps,
        actionText: 'Undo',
        actionHandler: vi.fn()
      }
    })
    
    expect(wrapper.text()).toContain('Undo')
    
    const actionButton = wrapper.find('button[class*="underline"]')
    await actionButton.trigger('click')
    
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('applies dark mode styling', () => {
    const wrapper = mount(ToastNotification, {
      props: defaultProps
    })
    
    expect(wrapper.classes()).toContain('dark:bg-gray-700')
  })
})