import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 15000
})

// Request interceptor for adding auth headers, etc.
api.interceptors.request.use(
  (config) => {
    // Add any common headers here
    config.headers['X-Client-Version'] = '1.0.0'
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling errors globally
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Enhanced error object
    const enhancedError = {
      ...error,
      timestamp: new Date().toISOString(),
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data
    }

    // Handle different types of errors
    if (error.response) {
      // Server responded with error status
      enhancedError.type = 'HTTP_ERROR'
      enhancedError.message = getHttpErrorMessage(error.response.status, error.response.data)
    } else if (error.request) {
      // Network error (no response received)
      enhancedError.type = 'NETWORK_ERROR'
      enhancedError.message = 'Network connection failed. Please check your internet connection.'
    } else {
      // Request setup error
      enhancedError.type = 'REQUEST_ERROR'
      enhancedError.message = error.message || 'Request failed to initialize'
    }

    console.error('API Error:', enhancedError)
    return Promise.reject(enhancedError)
  }
)

const getHttpErrorMessage = (status, data) => {
  // Use server-provided message if available
  if (data?.message) {
    return data.message
  }
  
  if (data?.detail) {
    return data.detail
  }

  // Default messages based on status codes
  switch (status) {
    case 400:
      return 'Invalid request. Please check your input.'
    case 401:
      return 'Authentication required. Please log in.'
    case 403:
      return 'You do not have permission to perform this action.'
    case 404:
      return 'The requested resource was not found.'
    case 409:
      return 'Conflict: The resource already exists or is in use.'
    case 422:
      return 'Validation failed. Please check your input.'
    case 429:
      return 'Too many requests. Please wait and try again.'
    case 500:
      return 'Internal server error. Please try again later.'
    case 502:
      return 'Bad gateway. The server is temporarily unavailable.'
    case 503:
      return 'Service unavailable. Please try again later.'
    case 504:
      return 'Gateway timeout. The request took too long to process.'
    default:
      return `Server error (${status}). Please try again.`
  }
}

const unwrap = (response) => response.data

// Enhanced API methods with better error context
const createApiMethod = (method, url, contextName) => {
  return async (...args) => {
    try {
      const response = await api[method](url, ...args)
      return unwrap(response)
    } catch (error) {
      // Add context to error
      error.context = contextName
      error.operation = `${method.toUpperCase()} ${url}`
      throw error
    }
  }
}

export const listPortfolios = () => api.get('/api/portfolios/').then(unwrap)
export const getPortfolio = (name) => api.get(`/api/portfolios/${name}`).then(unwrap)
export const createPortfolio = (payload) => api.post('/api/portfolios/', payload).then(unwrap)
export const updatePortfolio = (name, payload) => api.put(`/api/portfolios/${name}`, payload).then(unwrap)
export const deletePortfolio = (name) => api.delete(`/api/portfolios/${name}`).then(unwrap)

export const executeAgent = (name, payload = {}) =>
  api.post(`/api/agents/${name}/execute`, payload).then(unwrap)

export const cancelExecution = (name, executionId) =>
  api.delete(`/api/agents/${name}/execute/${executionId}`).then(unwrap)

export const getPendingTrades = () => api.get('/api/trades/pending').then(unwrap)
export const applyTrade = (tradeId) => api.post(`/api/trades/${tradeId}/apply`).then(unwrap)
export const cancelTrade = (tradeId) => api.delete(`/api/trades/${tradeId}`).then(unwrap)

export const getDashboard = () => api.get('/api/analytics/dashboard').then(unwrap)
export const getExecutionLogs = (portfolioName = null) => {
  const url = portfolioName ? `/api/analytics/execution-logs?portfolio=${portfolioName}` : '/api/analytics/execution-logs'
  return api.get(url).then(unwrap)
}

export const getSystemHealth = () => api.get('/api/system/health').then(unwrap)

export const getSchedulerStatus = () => api.get('/api/system/scheduler').then(unwrap)

// WebSocket URL helpers
export const getPortfolioWebSocketUrl = (portfolioName) => `ws://localhost:8000/ws/${portfolioName}`
export const getSystemWebSocketUrl = () => 'ws://localhost:8000/ws/system'  
export const getTradesWebSocketUrl = () => 'ws://localhost:8000/ws/trades'

// Notification helpers for WebSocket integration
export const subscribeToPortfolioUpdates = (portfolioName, callback) => {
  // This would be handled by the usePortfolioWebSocket composable
  console.log('Portfolio subscription:', portfolioName)
}

export const subscribeToSystemUpdates = (callback) => {
  // This would be handled by the useSystemWebSocket composable  
  console.log('System subscription active')
}

export const subscribeToTradeUpdates = (callback) => {
  // This would be handled by the useTradesWebSocket composable
  console.log('Trades subscription active')
}

export default api
