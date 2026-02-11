import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useErrorHandler } from '../useErrorHandler.js'

describe('useErrorHandler', () => {
  let consoleSpy

  beforeEach(() => {
    // Mock console.error to prevent noise in tests
    consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleSpy.mockRestore()
    vi.clearAllMocks()
  })

  it('initializes with no errors', () => {
    const { errors, hasErrors } = useErrorHandler()
    
    expect(errors.value).toEqual([])
    expect(hasErrors.value).toBe(false)
  })

  it('handles basic error objects', () => {
    const { handleError, errors } = useErrorHandler()
    
    const testError = new Error('Test error message')
    handleError(testError)
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Test error message')
    expect(errors.value[0].type).toBe('error')
  })

  it('handles string errors', () => {
    const { handleError, errors } = useErrorHandler()
    
    handleError('String error message')
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('String error message')
    expect(errors.value[0].type).toBe('error')
  })

  it('handles API error responses', () => {
    const { handleError, errors } = useErrorHandler()
    
    const apiError = {
      response: {
        status: 404,
        statusText: 'Not Found',
        data: {
          message: 'Resource not found'
        }
      }
    }
    
    handleError(apiError)
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Resource not found')
    expect(errors.value[0].status).toBe(404)
  })

  it('handles network errors', () => {
    const { handleError, errors } = useErrorHandler()
    
    const networkError = {
      code: 'NETWORK_ERROR',
      message: 'Network request failed'
    }
    
    handleError(networkError)
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Network request failed')
  })

  it('generates unique IDs for errors', () => {
    const { handleError, errors } = useErrorHandler()
    
    handleError(new Error('First error'))
    handleError(new Error('Second error'))
    
    expect(errors.value[0].id).toBeDefined()
    expect(errors.value[1].id).toBeDefined()
    expect(errors.value[0].id).not.toBe(errors.value[1].id)
  })

  it('adds timestamps to errors', () => {
    const { handleError, errors } = useErrorHandler()
    
    const beforeTime = Date.now()
    handleError(new Error('Timestamped error'))
    const afterTime = Date.now()
    
    expect(errors.value[0].timestamp).toBeGreaterThanOrEqual(beforeTime)
    expect(errors.value[0].timestamp).toBeLessThanOrEqual(afterTime)
  })

  it('categorizes errors correctly', () => {
    const { handleError, errors } = useErrorHandler()
    
    // Validation error
    handleError(new Error('Validation failed'), { type: 'validation' })
    
    // Network error
    handleError({ code: 'NETWORK_ERROR' })
    
    // Server error
    handleError({ 
      response: { status: 500, data: { message: 'Server error' } }
    })
    
    expect(errors.value[0].type).toBe('validation')
    expect(errors.value[1].type).toBe('network')
    expect(errors.value[2].type).toBe('server')
  })

  it('clears individual errors', () => {
    const { handleError, clearError, errors } = useErrorHandler()
    
    handleError(new Error('First error'))
    handleError(new Error('Second error'))
    
    expect(errors.value).toHaveLength(2)
    
    const firstErrorId = errors.value[0].id
    clearError(firstErrorId)
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Second error')
  })

  it('clears all errors', () => {
    const { handleError, clearAllErrors, errors, hasErrors } = useErrorHandler()
    
    handleError(new Error('First error'))
    handleError(new Error('Second error'))
    handleError(new Error('Third error'))
    
    expect(errors.value).toHaveLength(3)
    expect(hasErrors.value).toBe(true)
    
    clearAllErrors()
    
    expect(errors.value).toHaveLength(0)
    expect(hasErrors.value).toBe(false)
  })

  it('gets errors by type', () => {
    const { handleError, getErrorsByType } = useErrorHandler()
    
    handleError(new Error('Validation error'), { type: 'validation' })
    handleError(new Error('Network error'), { type: 'network' })
    handleError(new Error('Another validation error'), { type: 'validation' })
    
    const validationErrors = getErrorsByType('validation')
    const networkErrors = getErrorsByType('network')
    const serverErrors = getErrorsByType('server')
    
    expect(validationErrors.value).toHaveLength(2)
    expect(networkErrors.value).toHaveLength(1)
    expect(serverErrors.value).toHaveLength(0)
  })

  it('provides latest error reactive ref', () => {
    const { handleError, latestError } = useErrorHandler()
    
    expect(latestError.value).toBe(null)
    
    handleError(new Error('First error'))
    expect(latestError.value.message).toBe('First error')
    
    handleError(new Error('Second error'))
    expect(latestError.value.message).toBe('Second error')
  })

  it('handles error context information', () => {
    const { handleError, errors } = useErrorHandler()
    
    handleError(new Error('Context error'), {
      context: 'User Profile Update',
      userId: '12345',
      action: 'updateProfile'
    })
    
    expect(errors.value[0].context).toBe('User Profile Update')
    expect(errors.value[0].userId).toBe('12345')
    expect(errors.value[0].action).toBe('updateProfile')
  })

  it('prevents duplicate errors within time window', () => {
    vi.useFakeTimers()
    
    const { handleError, errors } = useErrorHandler()
    
    const errorMessage = 'Duplicate error'
    
    handleError(new Error(errorMessage))
    handleError(new Error(errorMessage)) // Should be deduplicated
    
    expect(errors.value).toHaveLength(1)
    
    // Advance time beyond deduplication window (default 5 seconds)
    vi.advanceTimersByTime(6000)
    
    handleError(new Error(errorMessage)) // Should be added now
    
    expect(errors.value).toHaveLength(2)
    
    vi.useRealTimers()
  })

  it('limits total number of stored errors', () => {
    const { handleError, errors } = useErrorHandler({ maxErrors: 3 })
    
    for (let i = 1; i <= 5; i++) {
      handleError(new Error(`Error ${i}`))
    }
    
    expect(errors.value).toHaveLength(3)
    expect(errors.value[0].message).toBe('Error 3') // Oldest should be removed
    expect(errors.value[1].message).toBe('Error 4')
    expect(errors.value[2].message).toBe('Error 5')
  })

  it('calls custom error handler when provided', () => {
    const customHandler = vi.fn()
    const { handleError } = useErrorHandler({ onError: customHandler })
    
    const testError = new Error('Custom handler test')
    handleError(testError)
    
    expect(customHandler).toHaveBeenCalledWith(expect.objectContaining({
      message: 'Custom handler test',
      type: 'error'
    }))
  })

  it('handles promise rejections', async () => {
    const { handleAsyncError, errors } = useErrorHandler()
    
    const failingPromise = Promise.reject(new Error('Async error'))
    
    await expect(handleAsyncError(failingPromise)).rejects.toThrow('Async error')
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Async error')
  })

  it('wraps functions with error handling', async () => {
    const { withErrorHandling, errors } = useErrorHandler()
    
    const failingFunction = () => {
      throw new Error('Function error')
    }
    
    const wrappedFunction = withErrorHandling(failingFunction)
    
    expect(() => wrappedFunction()).not.toThrow()
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Function error')
  })

  it('wraps async functions with error handling', async () => {
    const { withErrorHandling, errors } = useErrorHandler()
    
    const failingAsyncFunction = async () => {
      throw new Error('Async function error')
    }
    
    const wrappedFunction = withErrorHandling(failingAsyncFunction)
    
    await expect(wrappedFunction()).resolves.toBeUndefined()
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].message).toBe('Async function error')
  })

  it('formats error messages for display', () => {
    const { formatErrorForDisplay } = useErrorHandler()
    
    // Basic error
    const basicError = { message: 'Basic error', type: 'error' }
    expect(formatErrorForDisplay(basicError)).toBe('Basic error')
    
    // Validation error
    const validationError = { message: 'Invalid input', type: 'validation' }
    expect(formatErrorForDisplay(validationError)).toBe('Validation Error: Invalid input')
    
    // Network error
    const networkError = { message: 'Connection failed', type: 'network' }
    expect(formatErrorForDisplay(networkError)).toBe('Network Error: Connection failed')
    
    // Server error with status
    const serverError = { message: 'Server error', type: 'server', status: 500 }
    expect(formatErrorForDisplay(serverError)).toBe('Server Error (500): Server error')
  })

  it('handles error retries', () => {
    const { handleError, retry, errors } = useErrorHandler()
    
    let attempts = 0
    const retryableFunction = () => {
      attempts++
      if (attempts < 3) {
        throw new Error('Temporary error')
      }
      return 'success'
    }
    
    handleError(new Error('Temporary error'), {
      retryable: true,
      retryFunction: retryableFunction
    })
    
    expect(errors.value).toHaveLength(1)
    expect(errors.value[0].retryable).toBe(true)
    
    const result = retry(errors.value[0].id)
    expect(result).toBe('success')
    expect(attempts).toBe(3)
  })

  it('logs errors to console in development', () => {
    const { handleError } = useErrorHandler({ logErrors: true })
    
    handleError(new Error('Logged error'))
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'Error handled:',
      expect.objectContaining({
        message: 'Logged error'
      })
    )
  })
})