import { ref } from 'vue'
import { useToast } from './useToast'

const { error: showErrorToast, warning: showWarningToast } = useToast()

// Network status
const isOnline = ref(navigator.onLine)
const networkError = ref(false)

// Listen for online/offline events
window.addEventListener('online', () => {
  isOnline.value = true
  networkError.value = false
  showErrorToast('Connection restored', { duration: 3000 })
})

window.addEventListener('offline', () => {
  isOnline.value = false
  networkError.value = true
  showWarningToast('You are offline. Some features may not work.', { persistent: true })
})

export function useErrorHandler() {
  const handleError = (error, context = '') => {
    console.error(`Error ${context}:`, error)
    
    const message = getUserFriendlyMessage(error)
    showErrorToast(message, {
      actions: getErrorActions(error)
    })
  }

  const handleApiError = (error, operation = '') => {
    console.error(`API Error during ${operation}:`, error)
    
    // Check if it's a network error
    if (!navigator.onLine || error.code === 'NETWORK_ERROR') {
      networkError.value = true
      showWarningToast('You are offline. Please check your connection.', {
        persistent: true,
        actions: [
          {
            label: 'Retry',
            handler: () => window.location.reload()
          }
        ]
      })
      return
    }

    const message = getApiErrorMessage(error, operation)
    const actions = getApiErrorActions(error, operation)
    
    showErrorToast(message, { actions })
  }

  const handleValidationError = (field, message) => {
    return {
      [field]: message
    }
  }

  const retry = async (fn, maxAttempts = 3, delay = 1000) => {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await fn()
      } catch (error) {
        if (attempt === maxAttempts) {
          throw error
        }
        
        // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)))
      }
    }
  }

  const withErrorHandling = (fn, context = '') => {
    return async (...args) => {
      try {
        return await fn(...args)
      } catch (error) {
        handleError(error, context)
        throw error
      }
    }
  }

  const getUserFriendlyMessage = (error) => {
    if (typeof error === 'string') {
      return error
    }

    if (error?.response?.data?.message) {
      return error.response.data.message
    }

    if (error?.message) {
      return error.message
    }

    if (error?.code) {
      return ERROR_MESSAGES[error.code] || `Error: ${error.code}`
    }

    return 'An unexpected error occurred. Please try again.'
  }

  const getApiErrorMessage = (error, operation) => {
    const status = error?.response?.status
    const message = error?.response?.data?.message

    if (message) {
      return message
    }

    switch (status) {
      case 400:
        return `Invalid request${operation ? ` for ${operation}` : ''}. Please check your input.`
      case 401:
        return 'Authentication required. Please log in again.'
      case 403:
        return `You don't have permission to ${operation || 'perform this action'}.`
      case 404:
        return `${operation || 'Resource'} not found.`
      case 409:
        return `Conflict occurred while ${operation || 'processing request'}. Please try again.`
      case 422:
        return 'Invalid data provided. Please check your input.'
      case 429:
        return 'Too many requests. Please wait a moment and try again.'
      case 500:
        return 'Server error occurred. Please try again later.'
      case 503:
        return 'Service temporarily unavailable. Please try again later.'
      default:
        return `Failed to ${operation || 'complete request'}. Please try again.`
    }
  }

  const getErrorActions = (error) => {
    const actions = []

    // Always offer a refresh option for serious errors
    if (error?.response?.status >= 500) {
      actions.push({
        label: 'Refresh Page',
        handler: () => window.location.reload()
      })
    }

    return actions
  }

  const getApiErrorActions = (error, operation) => {
    const actions = []
    const status = error?.response?.status

    // Retry option for transient errors
    if ([408, 429, 500, 502, 503, 504].includes(status)) {
      actions.push({
        label: 'Retry',
        handler: () => {
          // This would need to be handled by the calling component
          // by passing a retry function
        }
      })
    }

    // Refresh option for authentication errors
    if ([401, 403].includes(status)) {
      actions.push({
        label: 'Refresh Page',
        handler: () => window.location.reload()
      })
    }

    return actions
  }

  return {
    // State
    isOnline,
    networkError,
    
    // Methods
    handleError,
    handleApiError,
    handleValidationError,
    retry,
    withErrorHandling,
    getUserFriendlyMessage
  }
}

// Common error messages
const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network connection failed. Please check your internet connection.',
  TIMEOUT_ERROR: 'Request timed out. Please try again.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  PERMISSION_ERROR: 'You do not have permission to perform this action.',
  NOT_FOUND_ERROR: 'The requested resource was not found.',
  SERVER_ERROR: 'A server error occurred. Please try again later.',
  UNKNOWN_ERROR: 'An unexpected error occurred. Please try again.'
}