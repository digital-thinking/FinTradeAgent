import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useWebSocket } from '../useWebSocket.js'
import { nextTick } from 'vue'

// Mock WebSocket
class MockWebSocket {
  constructor(url, protocols) {
    this.url = url
    this.protocols = protocols
    this.readyState = WebSocket.CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    
    // Store instance for testing
    MockWebSocket.instances.push(this)
    
    // Simulate connection after a tick
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      if (this.onopen) this.onopen({ type: 'open' })
    }, 0)
  }
  
  send(data) {
    if (this.readyState === WebSocket.OPEN) {
      this.sentMessages = this.sentMessages || []
      this.sentMessages.push(data)
    }
  }
  
  close(code = 1000, reason = '') {
    this.readyState = WebSocket.CLOSED
    if (this.onclose) {
      this.onclose({ 
        type: 'close', 
        code, 
        reason, 
        wasClean: code === 1000 
      })
    }
  }
  
  // Test helpers
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({
        type: 'message',
        data: typeof data === 'string' ? data : JSON.stringify(data)
      })
    }
  }
  
  simulateError(error = new Error('WebSocket error')) {
    if (this.onerror) {
      this.onerror({ type: 'error', error })
    }
  }
  
  static instances = []
  static clear() {
    this.instances = []
  }
}

// Define WebSocket constants
MockWebSocket.CONNECTING = 0
MockWebSocket.OPEN = 1
MockWebSocket.CLOSING = 2
MockWebSocket.CLOSED = 3

describe('useWebSocket', () => {
  beforeEach(() => {
    global.WebSocket = MockWebSocket
    global.WebSocket.CONNECTING = 0
    global.WebSocket.OPEN = 1
    global.WebSocket.CLOSING = 2
    global.WebSocket.CLOSED = 3
    MockWebSocket.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('initializes with correct default state', () => {
    const { 
      status, 
      data, 
      error, 
      isConnected, 
      isConnecting 
    } = useWebSocket('ws://localhost:8080')
    
    expect(status.value).toBe('connecting')
    expect(data.value).toBe(null)
    expect(error.value).toBe(null)
    expect(isConnected.value).toBe(false)
    expect(isConnecting.value).toBe(true)
  })

  it('creates WebSocket connection with correct URL', () => {
    useWebSocket('ws://localhost:8080/test')
    
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:8080/test')
  })

  it('updates status to connected when WebSocket opens', async () => {
    const { status, isConnected, isConnecting } = useWebSocket('ws://localhost:8080')
    
    // Initially connecting
    expect(status.value).toBe('connecting')
    expect(isConnecting.value).toBe(true)
    expect(isConnected.value).toBe(false)
    
    // Wait for connection to open
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    expect(status.value).toBe('connected')
    expect(isConnected.value).toBe(true)
    expect(isConnecting.value).toBe(false)
  })

  it('receives and parses JSON messages', async () => {
    const { data } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    const testData = { type: 'test', message: 'hello' }
    MockWebSocket.instances[0].simulateMessage(testData)
    await nextTick()
    
    expect(data.value).toEqual(testData)
  })

  it('receives plain text messages', async () => {
    const { data } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    MockWebSocket.instances[0].simulateMessage('plain text message')
    await nextTick()
    
    expect(data.value).toBe('plain text message')
  })

  it('sends messages correctly', async () => {
    const { send } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    const message = { type: 'ping', timestamp: Date.now() }
    send(message)
    
    const ws = MockWebSocket.instances[0]
    expect(ws.sentMessages).toContain(JSON.stringify(message))
  })

  it('sends plain text messages', async () => {
    const { send } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    send('hello world')
    
    const ws = MockWebSocket.instances[0]
    expect(ws.sentMessages).toContain('hello world')
  })

  it('handles connection errors', async () => {
    const { status, error } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    const testError = new Error('Connection failed')
    MockWebSocket.instances[0].simulateError(testError)
    await nextTick()
    
    expect(status.value).toBe('error')
    expect(error.value).toBe(testError)
  })

  it('handles connection close', async () => {
    const { status, isConnected } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    // Should be connected first
    expect(status.value).toBe('connected')
    
    MockWebSocket.instances[0].close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
    expect(isConnected.value).toBe(false)
  })

  it('closes connection when close() is called', async () => {
    const { close, status } = useWebSocket('ws://localhost:8080')
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    expect(status.value).toBe('connected')
    
    close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
  })

  it('attempts to reconnect automatically when enabled', async () => {
    const { status } = useWebSocket('ws://localhost:8080', {
      autoReconnect: true,
      reconnectInterval: 1000
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    // Close connection to trigger reconnect
    MockWebSocket.instances[0].close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
    
    // Advance time to trigger reconnect
    vi.advanceTimersByTime(1000)
    await nextTick()
    
    // Should have created a new WebSocket instance
    expect(MockWebSocket.instances).toHaveLength(2)
    expect(status.value).toBe('connecting')
  })

  it('does not reconnect when autoReconnect is disabled', async () => {
    const { status } = useWebSocket('ws://localhost:8080', {
      autoReconnect: false
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    MockWebSocket.instances[0].close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
    
    // Wait longer than typical reconnect interval
    vi.advanceTimersByTime(5000)
    await nextTick()
    
    // Should still only have one instance
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(status.value).toBe('disconnected')
  })

  it('limits reconnection attempts', async () => {
    const { status } = useWebSocket('ws://localhost:8080', {
      autoReconnect: true,
      reconnectInterval: 100,
      maxReconnectAttempts: 3
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    // Close and let it try to reconnect multiple times
    MockWebSocket.instances[0].close()
    await nextTick()
    
    for (let i = 0; i < 5; i++) {
      vi.advanceTimersByTime(100)
      await nextTick()
      
      // Close each new connection attempt
      const latestWs = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      if (latestWs && latestWs.readyState !== WebSocket.CLOSED) {
        latestWs.close()
        await nextTick()
      }
    }
    
    // Should have attempted 3 reconnections + initial = 4 total
    expect(MockWebSocket.instances).toHaveLength(4)
  })

  it('provides manual reconnect functionality', async () => {
    const { reconnect, status } = useWebSocket('ws://localhost:8080', {
      autoReconnect: false
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    MockWebSocket.instances[0].close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
    expect(MockWebSocket.instances).toHaveLength(1)
    
    reconnect()
    await nextTick()
    
    expect(MockWebSocket.instances).toHaveLength(2)
    expect(status.value).toBe('connecting')
  })

  it('handles message filtering with onMessage callback', async () => {
    let receivedMessages = []
    
    const { data } = useWebSocket('ws://localhost:8080', {
      onMessage: (msg) => {
        receivedMessages.push(msg)
        return msg.type === 'important' // Only process important messages
      }
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    // Send different message types
    MockWebSocket.instances[0].simulateMessage({ type: 'info', data: 'info' })
    MockWebSocket.instances[0].simulateMessage({ type: 'important', data: 'important' })
    MockWebSocket.instances[0].simulateMessage({ type: 'debug', data: 'debug' })
    await nextTick()
    
    expect(receivedMessages).toHaveLength(3)
    expect(data.value).toEqual({ type: 'important', data: 'important' })
  })

  it('handles onOpen callback', async () => {
    const onOpenSpy = vi.fn()
    
    useWebSocket('ws://localhost:8080', {
      onOpen: onOpenSpy
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    expect(onOpenSpy).toHaveBeenCalledOnce()
  })

  it('handles onClose callback', async () => {
    const onCloseSpy = vi.fn()
    
    const { } = useWebSocket('ws://localhost:8080', {
      onClose: onCloseSpy
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    MockWebSocket.instances[0].close(1000, 'Normal closure')
    await nextTick()
    
    expect(onCloseSpy).toHaveBeenCalledWith(expect.objectContaining({
      code: 1000,
      reason: 'Normal closure'
    }))
  })

  it('handles onError callback', async () => {
    const onErrorSpy = vi.fn()
    
    useWebSocket('ws://localhost:8080', {
      onError: onErrorSpy
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    const testError = new Error('Test error')
    MockWebSocket.instances[0].simulateError(testError)
    await nextTick()
    
    expect(onErrorSpy).toHaveBeenCalledWith(expect.objectContaining({
      error: testError
    }))
  })

  it('cleans up connection on component unmount', () => {
    const { cleanup } = useWebSocket('ws://localhost:8080')
    
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].readyState).not.toBe(WebSocket.CLOSED)
    
    cleanup()
    
    expect(MockWebSocket.instances[0].readyState).toBe(WebSocket.CLOSED)
  })

  it('handles connection state correctly during reconnection', async () => {
    const { status, isConnecting, isConnected } = useWebSocket('ws://localhost:8080', {
      autoReconnect: true,
      reconnectInterval: 100
    })
    
    await nextTick()
    vi.runAllTimers()
    await nextTick()
    
    expect(status.value).toBe('connected')
    expect(isConnected.value).toBe(true)
    expect(isConnecting.value).toBe(false)
    
    // Close connection
    MockWebSocket.instances[0].close()
    await nextTick()
    
    expect(status.value).toBe('disconnected')
    expect(isConnected.value).toBe(false)
    
    // Start reconnecting
    vi.advanceTimersByTime(100)
    await nextTick()
    
    expect(status.value).toBe('connecting')
    expect(isConnecting.value).toBe(true)
    expect(isConnected.value).toBe(false)
  })
})