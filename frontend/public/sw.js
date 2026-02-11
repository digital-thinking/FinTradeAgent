/**
 * Service Worker for FinTradeAgent - Optimized caching and performance
 */

const CACHE_NAME = 'fintrade-v1.0.0'
const STATIC_CACHE = 'fintrade-static-v1'
const DYNAMIC_CACHE = 'fintrade-dynamic-v1'
const API_CACHE = 'fintrade-api-v1'

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/assets/css/style.css',
  '/assets/js/main.js',
  '/assets/images/logo.png',
  // Add other critical assets
]

// API endpoints to cache with specific strategies
const API_CACHE_STRATEGIES = {
  '/api/portfolios': { strategy: 'stale-while-revalidate', maxAge: 300000 }, // 5 minutes
  '/api/analytics/dashboard': { strategy: 'cache-first', maxAge: 60000 }, // 1 minute
  '/api/system/health': { strategy: 'network-first', maxAge: 30000 }, // 30 seconds
  '/api/trades/pending': { strategy: 'network-first', maxAge: 10000 }, // 10 seconds
}

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker: Install event')
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Service Worker: Caching static assets')
        return cache.addAll(STATIC_ASSETS)
      })
      .then(() => {
        console.log('Service Worker: Static assets cached')
        return self.skipWaiting()
      })
      .catch(err => console.error('Service Worker: Install failed', err))
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activate event')
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE && 
                cacheName !== DYNAMIC_CACHE && 
                cacheName !== API_CACHE) {
              console.log('Service Worker: Deleting old cache', cacheName)
              return caches.delete(cacheName)
            }
          })
        )
      })
      .then(() => {
        console.log('Service Worker: Cache cleanup complete')
        return self.clients.claim()
      })
  )
})

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const { request } = event
  const url = new URL(request.url)
  
  // Skip non-HTTP requests
  if (!request.url.startsWith('http')) return
  
  // Skip WebSocket requests
  if (request.url.includes('ws://') || request.url.includes('wss://')) return

  event.respondWith(
    handleRequest(request, url)
  )
})

/**
 * Main request handler with different strategies
 */
async function handleRequest(request, url) {
  // API requests
  if (url.pathname.startsWith('/api')) {
    return handleApiRequest(request, url)
  }
  
  // Static assets (JS, CSS, images)
  if (isStaticAsset(url.pathname)) {
    return handleStaticAsset(request)
  }
  
  // HTML documents
  if (request.mode === 'navigate' || 
      (request.method === 'GET' && request.headers.get('accept').includes('text/html'))) {
    return handleNavigation(request)
  }
  
  // Default: try cache first, then network
  return handleDefault(request)
}

/**
 * Handle API requests with specific caching strategies
 */
async function handleApiRequest(request, url) {
  const cacheKey = findApiCacheStrategy(url.pathname)
  const strategy = API_CACHE_STRATEGIES[cacheKey]
  
  if (!strategy) {
    // No caching strategy defined, go to network
    return fetch(request)
  }
  
  switch (strategy.strategy) {
    case 'cache-first':
      return cacheFirst(request, API_CACHE, strategy.maxAge)
      
    case 'network-first':
      return networkFirst(request, API_CACHE, strategy.maxAge)
      
    case 'stale-while-revalidate':
      return staleWhileRevalidate(request, API_CACHE, strategy.maxAge)
      
    default:
      return fetch(request)
  }
}

/**
 * Handle static assets (CSS, JS, images, fonts)
 */
async function handleStaticAsset(request) {
  return cacheFirst(request, STATIC_CACHE)
}

/**
 * Handle navigation requests (HTML documents)
 */
async function handleNavigation(request) {
  try {
    // Try network first for navigation
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      // Cache the response for offline access
      const cache = await caches.open(DYNAMIC_CACHE)
      cache.put(request, networkResponse.clone())
      return networkResponse
    }
  } catch (error) {
    console.log('Service Worker: Network failed, trying cache', error)
  }
  
  // Fallback to cache or offline page
  const cachedResponse = await caches.match(request)
  if (cachedResponse) {
    return cachedResponse
  }
  
  // Return offline page if available
  const offlinePage = await caches.match('/offline.html')
  if (offlinePage) {
    return offlinePage
  }
  
  // Last resort: return basic offline response
  return new Response(
    '<html><body><h1>Offline</h1><p>You are currently offline. Please check your connection.</p></body></html>',
    { 
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/html' }
    }
  )
}

/**
 * Default handler for other requests
 */
async function handleDefault(request) {
  return networkFirst(request, DYNAMIC_CACHE)
}

/**
 * Cache-first strategy: Check cache, fallback to network
 */
async function cacheFirst(request, cacheName, maxAge = Infinity) {
  const cachedResponse = await caches.match(request)
  
  if (cachedResponse && !isExpired(cachedResponse, maxAge)) {
    return cachedResponse
  }
  
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, networkResponse.clone())
      return networkResponse
    }
    
    // Return cached response even if expired if network fails
    return cachedResponse || networkResponse
  } catch (error) {
    console.log('Service Worker: Network error in cache-first', error)
    return cachedResponse || new Response('Network Error', { status: 503 })
  }
}

/**
 * Network-first strategy: Try network, fallback to cache
 */
async function networkFirst(request, cacheName, maxAge = Infinity) {
  try {
    const networkResponse = await fetch(request)
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, networkResponse.clone())
      return networkResponse
    }
  } catch (error) {
    console.log('Service Worker: Network error in network-first', error)
  }
  
  const cachedResponse = await caches.match(request)
  if (cachedResponse && !isExpired(cachedResponse, maxAge)) {
    return cachedResponse
  }
  
  return new Response('Network Error', { status: 503 })
}

/**
 * Stale-while-revalidate strategy: Return cache immediately, update in background
 */
async function staleWhileRevalidate(request, cacheName, maxAge = Infinity) {
  const cachedResponse = await caches.match(request)
  
  // Always fetch from network in background
  const networkResponsePromise = fetch(request).then(response => {
    if (response.ok) {
      const cache = caches.open(cacheName)
      cache.then(c => c.put(request, response.clone()))
    }
    return response
  }).catch(error => {
    console.log('Service Worker: Background fetch failed', error)
  })
  
  // Return cached response if available and not expired
  if (cachedResponse && !isExpired(cachedResponse, maxAge)) {
    return cachedResponse
  }
  
  // Wait for network response if no valid cache
  return networkResponsePromise || new Response('Network Error', { status: 503 })
}

/**
 * Check if a cached response is expired
 */
function isExpired(response, maxAge) {
  if (maxAge === Infinity) return false
  
  const cachedTime = response.headers.get('sw-cache-time')
  if (!cachedTime) return false
  
  return Date.now() - parseInt(cachedTime) > maxAge
}

/**
 * Find matching API cache strategy
 */
function findApiCacheStrategy(pathname) {
  for (const pattern in API_CACHE_STRATEGIES) {
    if (pathname.startsWith(pattern)) {
      return pattern
    }
  }
  return null
}

/**
 * Check if URL is for a static asset
 */
function isStaticAsset(pathname) {
  return /\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ttf|eot|ico)$/i.test(pathname) ||
         pathname.startsWith('/assets/') ||
         pathname.startsWith('/static/')
}

/**
 * Background sync for failed API requests
 */
self.addEventListener('sync', event => {
  console.log('Service Worker: Background sync event', event.tag)
  
  if (event.tag === 'api-retry') {
    event.waitUntil(retryFailedApiRequests())
  }
})

/**
 * Retry failed API requests
 */
async function retryFailedApiRequests() {
  // Implementation for retrying failed requests stored in IndexedDB
  console.log('Service Worker: Retrying failed API requests')
  // This would typically read from IndexedDB and retry failed requests
}

/**
 * Handle push notifications
 */
self.addEventListener('push', event => {
  if (!event.data) return
  
  const data = event.data.json()
  const options = {
    body: data.body,
    icon: '/assets/images/icon-192x192.png',
    badge: '/assets/images/badge-72x72.png',
    data: data.data,
    actions: data.actions || []
  }
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'FinTradeAgent', options)
  )
})

/**
 * Handle notification click
 */
self.addEventListener('notificationclick', event => {
  event.notification.close()
  
  const data = event.notification.data
  if (data && data.url) {
    event.waitUntil(
      self.clients.matchAll().then(clients => {
        // Check if the target URL is already open
        for (const client of clients) {
          if (client.url === data.url && 'focus' in client) {
            return client.focus()
          }
        }
        
        // Open new window/tab
        if (self.clients.openWindow) {
          return self.clients.openWindow(data.url)
        }
      })
    )
  }
})

/**
 * Performance monitoring
 */
let performanceMetrics = {
  cacheHits: 0,
  cacheMisses: 0,
  networkRequests: 0,
  errors: 0
}

// Log performance metrics periodically
setInterval(() => {
  console.log('Service Worker Performance Metrics:', performanceMetrics)
}, 60000) // Every minute