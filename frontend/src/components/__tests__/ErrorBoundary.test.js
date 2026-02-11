import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ErrorBoundary from '../ErrorBoundary.vue'
import { ref } from 'vue'

// Mock component that throws an error
const ErrorThrowingComponent = {
  template: '<div>This will throw an error</div>',
  mounted() {
    throw new Error('Test error for error boundary')
  }
}

// Mock component that works normally  
const WorkingComponent = {
  template: '<div>Working component</div>'
}

describe('ErrorBoundary', () => {
  let consoleSpy

  beforeEach(() => {
    // Spy on console.error to prevent noise in test output
    consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleSpy.mockRestore()
  })

  it('renders children when no error occurs', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: '<div>Normal content</div>'
      }
    })
    
    expect(wrapper.text()).toContain('Normal content')
    expect(wrapper.find('[data-testid="error-boundary"]').exists()).toBe(false)
  })

  it('catches and displays error when child component throws', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('[data-testid="error-boundary"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Something went wrong')
  })

  it('displays custom error message when provided', async () => {
    const wrapper = mount(ErrorBoundary, {
      props: {
        fallbackMessage: 'Custom error message'
      },
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('Custom error message')
  })

  it('shows retry button by default', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.text()).toContain('Try again')
  })

  it('hides retry button when showRetry is false', async () => {
    const wrapper = mount(ErrorBoundary, {
      props: {
        showRetry: false
      },
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('resets error state when retry button is clicked', async () => {
    // Create a component that can toggle between error and normal state
    const ToggleComponent = {
      template: '<div>{{ shouldThrow ? throwError() : "Working now" }}</div>',
      data() {
        return {
          shouldThrow: true
        }
      },
      methods: {
        throwError() {
          throw new Error('Conditional error')
        }
      }
    }

    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ToggleComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    // Should show error state
    expect(wrapper.find('[data-testid="error-boundary"]').exists()).toBe(true)
    
    // Change the child component to not throw error
    const childComponent = wrapper.findComponent(ToggleComponent)
    childComponent.vm.shouldThrow = false
    
    // Click retry button
    const retryButton = wrapper.find('button')
    await retryButton.trigger('click')
    await wrapper.vm.$nextTick()
    
    // Should show normal content now
    expect(wrapper.text()).toContain('Working now')
    expect(wrapper.find('[data-testid="error-boundary"]').exists()).toBe(false)
  })

  it('emits error event when error is caught', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.emitted('error')).toHaveLength(1)
    expect(wrapper.emitted('error')[0][0]).toBeInstanceOf(Error)
  })

  it('calls onError callback when provided', async () => {
    const onErrorCallback = vi.fn()
    
    const wrapper = mount(ErrorBoundary, {
      props: {
        onError: onErrorCallback
      },
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(onErrorCallback).toHaveBeenCalledOnce()
    expect(onErrorCallback).toHaveBeenCalledWith(expect.any(Error))
  })

  it('shows error details when showDetails is true', async () => {
    const wrapper = mount(ErrorBoundary, {
      props: {
        showDetails: true
      },
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('Test error for error boundary')
  })

  it('hides error details by default', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).not.toContain('Test error for error boundary')
  })

  it('uses fallback slot when provided', async () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: ErrorThrowingComponent,
        fallback: '<div class="custom-error">Custom error UI</div>'
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.find('.custom-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Custom error UI')
  })

  it('tracks error boundary identifier when provided', async () => {
    const wrapper = mount(ErrorBoundary, {
      props: {
        boundaryId: 'dashboard-section'
      },
      slots: {
        default: ErrorThrowingComponent
      }
    })

    await wrapper.vm.$nextTick()
    
    expect(wrapper.emitted('error')[0][1]).toBe('dashboard-section')
  })
})