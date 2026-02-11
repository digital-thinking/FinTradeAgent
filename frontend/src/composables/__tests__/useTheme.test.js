import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useTheme } from '../useTheme.js'

describe('useTheme', () => {
  let mockLocalStorage

  beforeEach(() => {
    // Mock localStorage
    mockLocalStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn()
    }
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true
    })

    // Mock matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    // Mock document.documentElement
    Object.defineProperty(document, 'documentElement', {
      value: {
        classList: {
          add: vi.fn(),
          remove: vi.fn(),
          contains: vi.fn(() => false)
        }
      },
      writable: true
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with light theme by default', () => {
    mockLocalStorage.getItem.mockReturnValue(null)
    
    const { theme, isDark } = useTheme()
    
    expect(theme.value).toBe('light')
    expect(isDark.value).toBe(false)
  })

  it('loads saved theme from localStorage', () => {
    mockLocalStorage.getItem.mockReturnValue('dark')
    
    const { theme, isDark } = useTheme()
    
    expect(theme.value).toBe('dark')
    expect(isDark.value).toBe(true)
    expect(mockLocalStorage.getItem).toHaveBeenCalledWith('theme')
  })

  it('detects system dark mode preference when no saved theme', () => {
    mockLocalStorage.getItem.mockReturnValue(null)
    window.matchMedia.mockImplementation(query => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }))

    const { theme, isDark } = useTheme()
    
    expect(theme.value).toBe('dark')
    expect(isDark.value).toBe(true)
  })

  it('toggles theme from light to dark', () => {
    mockLocalStorage.getItem.mockReturnValue('light')
    
    const { theme, isDark, toggleTheme } = useTheme()
    
    expect(theme.value).toBe('light')
    expect(isDark.value).toBe(false)
    
    toggleTheme()
    
    expect(theme.value).toBe('dark')
    expect(isDark.value).toBe(true)
  })

  it('toggles theme from dark to light', () => {
    mockLocalStorage.getItem.mockReturnValue('dark')
    
    const { theme, isDark, toggleTheme } = useTheme()
    
    expect(theme.value).toBe('dark')
    expect(isDark.value).toBe(true)
    
    toggleTheme()
    
    expect(theme.value).toBe('light')
    expect(isDark.value).toBe(false)
  })

  it('sets theme to specific value', () => {
    const { theme, setTheme } = useTheme()
    
    setTheme('dark')
    
    expect(theme.value).toBe('dark')
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('theme', 'dark')
  })

  it('persists theme changes to localStorage', () => {
    const { toggleTheme } = useTheme()
    
    toggleTheme()
    
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('theme', 'dark')
  })

  it('applies dark class to document element when dark theme', () => {
    const { setTheme } = useTheme()
    
    setTheme('dark')
    
    expect(document.documentElement.classList.add).toHaveBeenCalledWith('dark')
  })

  it('removes dark class from document element when light theme', () => {
    const { setTheme } = useTheme()
    
    setTheme('light')
    
    expect(document.documentElement.classList.remove).toHaveBeenCalledWith('dark')
  })

  it('listens for system theme changes', () => {
    mockLocalStorage.getItem.mockReturnValue(null) // No saved preference
    
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }
    window.matchMedia.mockReturnValue(mockMediaQuery)
    
    useTheme()
    
    expect(mockMediaQuery.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('updates theme when system preference changes', () => {
    mockLocalStorage.getItem.mockReturnValue(null)
    
    let mediaQueryCallback
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn((event, callback) => {
        mediaQueryCallback = callback
      }),
      removeEventListener: vi.fn()
    }
    window.matchMedia.mockReturnValue(mockMediaQuery)
    
    const { theme } = useTheme()
    
    // Simulate system theme change to dark
    mockMediaQuery.matches = true
    mediaQueryCallback({ matches: true })
    
    expect(theme.value).toBe('dark')
  })

  it('ignores system changes when user has saved preference', () => {
    mockLocalStorage.getItem.mockReturnValue('light') // User prefers light
    
    let mediaQueryCallback
    const mockMediaQuery = {
      matches: true, // System prefers dark
      addEventListener: vi.fn((event, callback) => {
        mediaQueryCallback = callback
      }),
      removeEventListener: vi.fn()
    }
    window.matchMedia.mockReturnValue(mockMediaQuery)
    
    const { theme } = useTheme()
    
    expect(theme.value).toBe('light') // Should stick with user preference
    
    // Simulate system theme change
    mediaQueryCallback({ matches: false })
    
    expect(theme.value).toBe('light') // Should still be user preference
  })

  it('provides reactive theme values', async () => {
    const { theme, isDark, toggleTheme } = useTheme()
    
    expect(theme.value).toBe('light')
    expect(isDark.value).toBe(false)
    
    toggleTheme()
    
    // Values should update immediately
    expect(theme.value).toBe('dark')
    expect(isDark.value).toBe(true)
  })

  it('handles invalid localStorage values gracefully', () => {
    mockLocalStorage.getItem.mockReturnValue('invalid-theme')
    
    const { theme } = useTheme()
    
    expect(theme.value).toBe('light') // Should fallback to light
  })

  it('cleans up event listeners on unmount', () => {
    const mockMediaQuery = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }
    window.matchMedia.mockReturnValue(mockMediaQuery)
    
    const { cleanup } = useTheme()
    
    if (cleanup) {
      cleanup()
      expect(mockMediaQuery.removeEventListener).toHaveBeenCalled()
    }
  })

  it('returns consistent theme state across multiple calls', () => {
    mockLocalStorage.getItem.mockReturnValue('dark')
    
    const theme1 = useTheme()
    const theme2 = useTheme()
    
    expect(theme1.theme.value).toBe(theme2.theme.value)
    expect(theme1.isDark.value).toBe(theme2.isDark.value)
  })

  it('handles localStorage errors gracefully', () => {
    mockLocalStorage.getItem.mockImplementation(() => {
      throw new Error('localStorage not available')
    })
    
    expect(() => {
      useTheme()
    }).not.toThrow()
  })
})