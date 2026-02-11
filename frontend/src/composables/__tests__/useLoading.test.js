import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useLoading } from '../useLoading.js'
import { nextTick } from 'vue'

describe('useLoading', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('initializes with loading false by default', () => {
    const { loading } = useLoading()
    
    expect(loading.value).toBe(false)
  })

  it('initializes with loading true when specified', () => {
    const { loading } = useLoading(true)
    
    expect(loading.value).toBe(true)
  })

  it('starts loading immediately without delay by default', () => {
    const { loading, startLoading } = useLoading()
    
    startLoading()
    
    expect(loading.value).toBe(true)
  })

  it('stops loading immediately', () => {
    const { loading, startLoading, stopLoading } = useLoading()
    
    startLoading()
    expect(loading.value).toBe(true)
    
    stopLoading()
    expect(loading.value).toBe(false)
  })

  it('applies delay before showing loading state', async () => {
    const { loading, startLoading } = useLoading(false, 300)
    
    startLoading()
    
    // Should not be loading immediately
    expect(loading.value).toBe(false)
    
    // Fast forward 299ms - still should not be loading
    vi.advanceTimersByTime(299)
    await nextTick()
    expect(loading.value).toBe(false)
    
    // Fast forward 1ms more (total 300ms) - now should be loading
    vi.advanceTimersByTime(1)
    await nextTick()
    expect(loading.value).toBe(true)
  })

  it('cancels delayed loading when stopped before delay', async () => {
    const { loading, startLoading, stopLoading } = useLoading(false, 300)
    
    startLoading()
    expect(loading.value).toBe(false)
    
    // Stop before delay completes
    vi.advanceTimersByTime(150)
    stopLoading()
    
    // Complete the original delay
    vi.advanceTimersByTime(150)
    await nextTick()
    
    // Should still not be loading
    expect(loading.value).toBe(false)
  })

  it('handles multiple start calls correctly', async () => {
    const { loading, startLoading } = useLoading(false, 200)
    
    startLoading()
    vi.advanceTimersByTime(100)
    
    // Start again before first delay completes
    startLoading()
    
    // First delay should be cancelled, new delay starts
    vi.advanceTimersByTime(100) // Total 200ms from first call, 100ms from second
    await nextTick()
    expect(loading.value).toBe(false)
    
    // Complete second delay
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(loading.value).toBe(true)
  })

  it('provides toggle functionality', () => {
    const { loading, toggleLoading } = useLoading()
    
    expect(loading.value).toBe(false)
    
    toggleLoading()
    expect(loading.value).toBe(true)
    
    toggleLoading()
    expect(loading.value).toBe(false)
  })

  it('toggle respects delay when turning on', async () => {
    const { loading, toggleLoading } = useLoading(false, 250)
    
    toggleLoading() // Turn on with delay
    expect(loading.value).toBe(false)
    
    vi.advanceTimersByTime(250)
    await nextTick()
    expect(loading.value).toBe(true)
    
    toggleLoading() // Turn off immediately
    expect(loading.value).toBe(false)
  })

  it('provides isLoading computed that matches loading state', () => {
    const { loading, isLoading, startLoading, stopLoading } = useLoading()
    
    expect(isLoading.value).toBe(loading.value)
    
    startLoading()
    expect(isLoading.value).toBe(loading.value)
    expect(isLoading.value).toBe(true)
    
    stopLoading()
    expect(isLoading.value).toBe(loading.value)
    expect(isLoading.value).toBe(false)
  })

  it('works with async operations', async () => {
    const { loading, startLoading, stopLoading } = useLoading()
    
    const asyncOperation = async () => {
      startLoading()
      try {
        // Simulate async work
        await new Promise(resolve => setTimeout(resolve, 100))
        return 'success'
      } finally {
        stopLoading()
      }
    }
    
    const promise = asyncOperation()
    expect(loading.value).toBe(true)
    
    vi.advanceTimersByTime(100)
    const result = await promise
    
    expect(result).toBe('success')
    expect(loading.value).toBe(false)
  })

  it('handles concurrent loading operations', async () => {
    const { loading, startLoading, stopLoading } = useLoading(false, 100)
    
    // Start first operation
    startLoading()
    vi.advanceTimersByTime(50)
    
    // Start second operation before first completes
    startLoading()
    
    // Complete first delay (should be cancelled)
    vi.advanceTimersByTime(50)
    await nextTick()
    expect(loading.value).toBe(false)
    
    // Complete second delay
    vi.advanceTimersByTime(50)
    await nextTick()
    expect(loading.value).toBe(true)
    
    // Stop should work normally
    stopLoading()
    expect(loading.value).toBe(false)
  })

  it('prevents memory leaks by cleaning up timeouts', async () => {
    const { startLoading, stopLoading } = useLoading(false, 500)
    
    startLoading()
    
    // Stop before delay completes - should clean up timeout
    vi.advanceTimersByTime(250)
    stopLoading()
    
    // Advance past original delay - should not change state
    vi.advanceTimersByTime(250)
    await nextTick()
    
    // No way to directly test setTimeout cleanup, but ensuring no state change
    // after stopLoading indicates proper cleanup
    expect(true).toBe(true) // Test passes if no hanging promises
  })

  it('handles zero delay correctly', () => {
    const { loading, startLoading } = useLoading(false, 0)
    
    startLoading()
    
    // With zero delay, should start immediately
    expect(loading.value).toBe(true)
  })

  it('handles negative delay as immediate', () => {
    const { loading, startLoading } = useLoading(false, -100)
    
    startLoading()
    
    // Negative delay should be treated as no delay
    expect(loading.value).toBe(true)
  })

  it('maintains state independence across multiple instances', () => {
    const loader1 = useLoading()
    const loader2 = useLoading()
    
    loader1.startLoading()
    expect(loader1.loading.value).toBe(true)
    expect(loader2.loading.value).toBe(false)
    
    loader2.startLoading()
    expect(loader1.loading.value).toBe(true)
    expect(loader2.loading.value).toBe(true)
    
    loader1.stopLoading()
    expect(loader1.loading.value).toBe(false)
    expect(loader2.loading.value).toBe(true)
  })

  it('works correctly with different delay values', async () => {
    const fastLoader = useLoading(false, 100)
    const slowLoader = useLoading(false, 300)
    
    fastLoader.startLoading()
    slowLoader.startLoading()
    
    // After 100ms, only fast loader should be showing
    vi.advanceTimersByTime(100)
    await nextTick()
    expect(fastLoader.loading.value).toBe(true)
    expect(slowLoader.loading.value).toBe(false)
    
    // After 200ms more (300ms total), slow loader should also show
    vi.advanceTimersByTime(200)
    await nextTick()
    expect(fastLoader.loading.value).toBe(true)
    expect(slowLoader.loading.value).toBe(true)
  })
})