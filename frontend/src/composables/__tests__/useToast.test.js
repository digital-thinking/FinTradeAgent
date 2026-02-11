import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useToast } from '../useToast.js'

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('initializes with empty toast list', () => {
    const { toasts } = useToast()
    
    expect(toasts.value).toEqual([])
  })

  it('adds info toast', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Info message', { type: 'info' })
    
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].message).toBe('Info message')
    expect(toasts.value[0].type).toBe('info')
    expect(toasts.value[0].id).toBeDefined()
  })

  it('adds success toast', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Success message', { type: 'success' })
    
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].type).toBe('success')
  })

  it('adds warning toast', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Warning message', { type: 'warning' })
    
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].type).toBe('warning')
  })

  it('adds error toast', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Error message', { type: 'error' })
    
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].type).toBe('error')
  })

  it('provides convenience methods for each type', () => {
    const { success, error, warning, info, toasts } = useToast()
    
    success('Success message')
    error('Error message')
    warning('Warning message')
    info('Info message')
    
    expect(toasts.value).toHaveLength(4)
    expect(toasts.value[0].type).toBe('success')
    expect(toasts.value[1].type).toBe('error')
    expect(toasts.value[2].type).toBe('warning')
    expect(toasts.value[3].type).toBe('info')
  })

  it('auto-removes toasts after default duration', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Auto remove message')
    
    expect(toasts.value).toHaveLength(1)
    
    // Fast-forward 4 seconds (default duration is 4000ms)
    vi.advanceTimersByTime(4000)
    
    expect(toasts.value).toHaveLength(0)
  })

  it('respects custom duration', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Custom duration message', { duration: 1000 })
    
    expect(toasts.value).toHaveLength(1)
    
    // Fast-forward 500ms - should still be there
    vi.advanceTimersByTime(500)
    expect(toasts.value).toHaveLength(1)
    
    // Fast-forward 500ms more (total 1000ms) - should be removed
    vi.advanceTimersByTime(500)
    expect(toasts.value).toHaveLength(0)
  })

  it('does not auto-remove when duration is 0', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Persistent message', { duration: 0 })
    
    expect(toasts.value).toHaveLength(1)
    
    // Fast-forward a long time
    vi.advanceTimersByTime(10000)
    
    expect(toasts.value).toHaveLength(1) // Should still be there
  })

  it('removes specific toast by ID', () => {
    const { addToast, removeToast, toasts } = useToast()
    
    addToast('First message')
    addToast('Second message')
    addToast('Third message')
    
    expect(toasts.value).toHaveLength(3)
    
    const secondToastId = toasts.value[1].id
    removeToast(secondToastId)
    
    expect(toasts.value).toHaveLength(2)
    expect(toasts.value[0].message).toBe('First message')
    expect(toasts.value[1].message).toBe('Third message')
  })

  it('clears all toasts', () => {
    const { addToast, clearAll, toasts } = useToast()
    
    addToast('First message')
    addToast('Second message')
    addToast('Third message')
    
    expect(toasts.value).toHaveLength(3)
    
    clearAll()
    
    expect(toasts.value).toHaveLength(0)
  })

  it('includes title when provided', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Message with title', { 
      title: 'Important Notice',
      type: 'warning'
    })
    
    expect(toasts.value[0].title).toBe('Important Notice')
    expect(toasts.value[0].message).toBe('Message with title')
  })

  it('includes action when provided', () => {
    const { addToast, toasts } = useToast()
    const actionHandler = vi.fn()
    
    addToast('Message with action', {
      actionText: 'Undo',
      actionHandler
    })
    
    expect(toasts.value[0].actionText).toBe('Undo')
    expect(toasts.value[0].actionHandler).toBe(actionHandler)
  })

  it('sets dismissible property correctly', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Dismissible message', { dismissible: true })
    addToast('Non-dismissible message', { dismissible: false })
    
    expect(toasts.value[0].dismissible).toBe(true)
    expect(toasts.value[1].dismissible).toBe(false)
  })

  it('handles position configuration', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Positioned message', { position: 'bottom-left' })
    
    expect(toasts.value[0].position).toBe('bottom-left')
  })

  it('generates unique IDs for each toast', () => {
    const { addToast, toasts } = useToast()
    
    addToast('First message')
    addToast('Second message')
    addToast('Third message')
    
    const ids = toasts.value.map(toast => toast.id)
    const uniqueIds = new Set(ids)
    
    expect(uniqueIds.size).toBe(3) // All IDs should be unique
  })

  it('maintains toast order (newest first)', () => {
    const { addToast, toasts } = useToast()
    
    addToast('First message')
    addToast('Second message') 
    addToast('Third message')
    
    expect(toasts.value[0].message).toBe('Third message')
    expect(toasts.value[1].message).toBe('Second message')
    expect(toasts.value[2].message).toBe('First message')
  })

  it('limits total number of toasts when configured', () => {
    const { addToast, toasts } = useToast({ maxToasts: 3 })
    
    for (let i = 1; i <= 5; i++) {
      addToast(`Message ${i}`)
    }
    
    expect(toasts.value).toHaveLength(3)
    expect(toasts.value[0].message).toBe('Message 5')
    expect(toasts.value[1].message).toBe('Message 4')
    expect(toasts.value[2].message).toBe('Message 3')
  })

  it('prevents duplicate messages within time window', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Duplicate message')
    addToast('Duplicate message') // Should be prevented
    addToast('Different message')
    
    expect(toasts.value).toHaveLength(2)
    expect(toasts.value[0].message).toBe('Different message')
    expect(toasts.value[1].message).toBe('Duplicate message')
  })

  it('allows duplicate messages after time window', () => {
    const { addToast, toasts } = useToast()
    
    addToast('Duplicate message')
    
    // Fast-forward past duplicate prevention window (default 2 seconds)
    vi.advanceTimersByTime(3000)
    
    addToast('Duplicate message') // Should be allowed now
    
    expect(toasts.value).toHaveLength(2)
  })

  it('handles toast with HTML content when allowed', () => {
    const { addToast, toasts } = useToast()
    
    addToast('<strong>Bold message</strong>', { 
      allowHtml: true 
    })
    
    expect(toasts.value[0].message).toBe('<strong>Bold message</strong>')
    expect(toasts.value[0].allowHtml).toBe(true)
  })

  it('provides toast count reactive computed', () => {
    const { addToast, toastCount } = useToast()
    
    expect(toastCount.value).toBe(0)
    
    addToast('First message')
    expect(toastCount.value).toBe(1)
    
    addToast('Second message')
    expect(toastCount.value).toBe(2)
  })

  it('provides hasToasts reactive computed', () => {
    const { addToast, hasToasts } = useToast()
    
    expect(hasToasts.value).toBe(false)
    
    addToast('Message')
    expect(hasToasts.value).toBe(true)
  })

  it('cleans up timers when toasts are manually removed', () => {
    const { addToast, removeToast, toasts } = useToast()
    
    addToast('Message with timer')
    const toastId = toasts.value[0].id
    
    removeToast(toastId)
    
    // Fast-forward past original duration - should not cause issues
    vi.advanceTimersByTime(5000)
    
    expect(toasts.value).toHaveLength(0)
  })

  it('handles toast updates', () => {
    const { addToast, updateToast, toasts } = useToast()
    
    addToast('Original message')
    const toastId = toasts.value[0].id
    
    updateToast(toastId, {
      message: 'Updated message',
      type: 'success'
    })
    
    expect(toasts.value[0].message).toBe('Updated message')
    expect(toasts.value[0].type).toBe('success')
  })

  it('groups toasts by type when configured', () => {
    const { addToast, getToastsByType } = useToast()
    
    addToast('Error 1', { type: 'error' })
    addToast('Success message', { type: 'success' })
    addToast('Error 2', { type: 'error' })
    addToast('Warning message', { type: 'warning' })
    
    const errorToasts = getToastsByType('error')
    const successToasts = getToastsByType('success')
    
    expect(errorToasts.value).toHaveLength(2)
    expect(successToasts.value).toHaveLength(1)
  })

  it('handles global toast configuration', () => {
    const globalConfig = {
      duration: 2000,
      position: 'bottom-right',
      dismissible: false
    }
    
    const { addToast, toasts } = useToast(globalConfig)
    
    addToast('Configured message')
    
    expect(toasts.value[0].duration).toBe(2000)
    expect(toasts.value[0].position).toBe('bottom-right')
    expect(toasts.value[0].dismissible).toBe(false)
  })

  it('allows per-toast config to override global config', () => {
    const globalConfig = {
      duration: 2000,
      position: 'bottom-right'
    }
    
    const { addToast, toasts } = useToast(globalConfig)
    
    addToast('Override message', {
      duration: 5000,
      position: 'top-left'
    })
    
    expect(toasts.value[0].duration).toBe(5000)
    expect(toasts.value[0].position).toBe('top-left')
  })
})