import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ExecutionProgress from '../ExecutionProgress.vue'

describe('ExecutionProgress', () => {
  const defaultProps = {
    status: 'running',
    currentStep: 2,
    totalSteps: 5,
    message: 'Analyzing market data...'
  }

  it('renders execution progress information', () => {
    const wrapper = mount(ExecutionProgress, {
      props: defaultProps
    })
    
    expect(wrapper.text()).toContain('Analyzing market data...')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('5')
  })

  it('displays correct progress percentage', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        currentStep: 3,
        totalSteps: 10
      }
    })
    
    // Should show 30% progress (3/10 * 100)
    const progressBar = wrapper.find('.bg-blue-600')
    expect(progressBar.attributes('style')).toContain('30%')
  })

  it('shows running status correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: { ...defaultProps, status: 'running' }
    })
    
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
    expect(wrapper.find('.bg-blue-600').exists()).toBe(true)
  })

  it('shows completed status correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: { 
        ...defaultProps, 
        status: 'completed',
        currentStep: 5,
        totalSteps: 5
      }
    })
    
    expect(wrapper.find('.bg-green-600').exists()).toBe(true)
    expect(wrapper.text()).toContain('Completed')
  })

  it('shows failed status correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: { 
        ...defaultProps, 
        status: 'failed'
      }
    })
    
    expect(wrapper.find('.bg-red-600').exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed')
  })

  it('shows paused status correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: { 
        ...defaultProps, 
        status: 'paused'
      }
    })
    
    expect(wrapper.find('.bg-yellow-600').exists()).toBe(true)
    expect(wrapper.text()).toContain('Paused')
  })

  it('displays step information correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        status: 'running',
        currentStep: 1,
        totalSteps: 3,
        message: 'Step 1 message'
      }
    })
    
    expect(wrapper.text()).toContain('Step 1 of 3')
  })

  it('handles steps array when provided', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        status: 'running',
        currentStep: 2,
        totalSteps: 3,
        steps: [
          'Initialize portfolio',
          'Analyze market data',
          'Generate recommendations'
        ]
      }
    })
    
    expect(wrapper.text()).toContain('Initialize portfolio')
    expect(wrapper.text()).toContain('Analyze market data')
    expect(wrapper.text()).toContain('Generate recommendations')
  })

  it('shows elapsed time when provided', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        elapsedTime: 125000 // 2 minutes 5 seconds in milliseconds
      }
    })
    
    expect(wrapper.text()).toContain('2:05')
  })

  it('shows estimated time remaining when provided', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        estimatedTimeRemaining: 90000 // 1 minute 30 seconds
      }
    })
    
    expect(wrapper.text()).toContain('1:30')
  })

  it('emits cancel event when cancel button clicked', async () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        cancellable: true
      }
    })
    
    const cancelButton = wrapper.find('button')
    await cancelButton.trigger('click')
    
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('emits pause event when pause button clicked', async () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        pausable: true
      }
    })
    
    const pauseButton = wrapper.find('button[title*="Pause"]')
    await pauseButton.trigger('click')
    
    expect(wrapper.emitted('pause')).toHaveLength(1)
  })

  it('emits resume event when resume button clicked on paused execution', async () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        ...defaultProps,
        status: 'paused',
        pausable: true
      }
    })
    
    const resumeButton = wrapper.find('button[title*="Resume"]')
    await resumeButton.trigger('click')
    
    expect(wrapper.emitted('resume')).toHaveLength(1)
  })

  it('handles zero progress correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        status: 'running',
        currentStep: 0,
        totalSteps: 5,
        message: 'Starting...'
      }
    })
    
    const progressBar = wrapper.find('.bg-blue-600')
    expect(progressBar.attributes('style')).toContain('0%')
  })

  it('handles 100% progress correctly', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        status: 'completed',
        currentStep: 10,
        totalSteps: 10,
        message: 'Complete!'
      }
    })
    
    const progressBar = wrapper.find('.bg-green-600')
    expect(progressBar.attributes('style')).toContain('100%')
  })

  it('shows error message when execution fails', () => {
    const wrapper = mount(ExecutionProgress, {
      props: {
        status: 'failed',
        currentStep: 3,
        totalSteps: 5,
        message: 'Error: Connection timeout',
        errorMessage: 'Failed to connect to trading API'
      }
    })
    
    expect(wrapper.text()).toContain('Failed to connect to trading API')
    expect(wrapper.find('.text-red-600').exists()).toBe(true)
  })
})