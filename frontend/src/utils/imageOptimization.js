/**
 * Image optimization utilities for better performance
 */

/**
 * Image compression and optimization utilities
 */
export class ImageOptimizer {
  constructor() {
    this.cache = new Map()
    this.loadingImages = new Map()
  }

  /**
   * Lazy load images with intersection observer
   */
  setupLazyLoading() {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, falling back to immediate loading')
      return this.fallbackLazyLoading()
    }

    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target
          this.loadImage(img)
          observer.unobserve(img)
        }
      })
    }, {
      rootMargin: '50px 0px', // Start loading 50px before image enters viewport
      threshold: 0.01
    })

    // Observe all images with data-src attribute
    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img)
    })

    return imageObserver
  }

  /**
   * Fallback lazy loading for browsers without IntersectionObserver
   */
  fallbackLazyLoading() {
    const images = document.querySelectorAll('img[data-src]')
    
    const checkImages = () => {
      images.forEach(img => {
        if (this.isInViewport(img)) {
          this.loadImage(img)
        }
      })
    }

    // Check on scroll and resize
    window.addEventListener('scroll', this.throttle(checkImages, 100))
    window.addEventListener('resize', this.throttle(checkImages, 100))
    
    // Initial check
    checkImages()
  }

  /**
   * Load image with optimization and caching
   */
  async loadImage(img) {
    const src = img.dataset.src || img.src
    if (!src) return

    // Check cache first
    if (this.cache.has(src)) {
      const cachedBlob = this.cache.get(src)
      img.src = URL.createObjectURL(cachedBlob)
      img.classList.add('loaded')
      return
    }

    // Prevent duplicate loading
    if (this.loadingImages.has(src)) {
      return this.loadingImages.get(src)
    }

    const loadPromise = this.loadAndOptimizeImage(src)
    this.loadingImages.set(src, loadPromise)

    try {
      const optimizedBlob = await loadPromise
      
      // Cache the optimized image
      this.cache.set(src, optimizedBlob)
      
      // Update image source
      img.src = URL.createObjectURL(optimizedBlob)
      img.classList.add('loaded')
      
      // Add fade-in animation
      img.style.opacity = '0'
      img.style.transition = 'opacity 0.3s ease'
      requestAnimationFrame(() => {
        img.style.opacity = '1'
      })
      
    } catch (error) {
      console.error('Failed to load image:', src, error)
      // Fallback to original src
      img.src = src
    } finally {
      this.loadingImages.delete(src)
    }
  }

  /**
   * Load and optimize image
   */
  async loadAndOptimizeImage(src) {
    const response = await fetch(src)
    const blob = await response.blob()
    
    // Skip optimization for small images or unsupported formats
    if (blob.size < 50 * 1024 || !blob.type.startsWith('image/')) {
      return blob
    }

    return this.compressImage(blob)
  }

  /**
   * Compress image using Canvas API
   */
  async compressImage(blob, quality = 0.8, maxWidth = 1200, maxHeight = 800) {
    return new Promise((resolve) => {
      const img = new Image()
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')

      img.onload = () => {
        // Calculate new dimensions
        let { width, height } = img
        
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height)
          width *= ratio
          height *= ratio
        }

        // Set canvas size
        canvas.width = width
        canvas.height = height

        // Draw and compress
        ctx.drawImage(img, 0, 0, width, height)
        
        canvas.toBlob((compressedBlob) => {
          // Use compressed version only if it's actually smaller
          resolve(compressedBlob.size < blob.size ? compressedBlob : blob)
        }, blob.type, quality)
      }

      img.onerror = () => resolve(blob) // Fallback to original
      img.src = URL.createObjectURL(blob)
    })
  }

  /**
   * Create responsive image sources for different screen sizes
   */
  generateResponsiveSources(baseSrc, sizes = [400, 800, 1200]) {
    const extension = baseSrc.split('.').pop()
    const baseName = baseSrc.replace(`.${extension}`, '')
    
    return sizes.map(size => ({
      srcSet: `${baseName}_${size}w.${extension}`,
      media: size === 400 ? '(max-width: 640px)' : 
             size === 800 ? '(max-width: 1024px)' : 
             '(min-width: 1025px)',
      size
    }))
  }

  /**
   * Preload critical images
   */
  preloadImages(urls) {
    urls.forEach(url => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.as = 'image'
      link.href = url
      document.head.appendChild(link)
    })
  }

  /**
   * Check if element is in viewport
   */
  isInViewport(element) {
    const rect = element.getBoundingClientRect()
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    )
  }

  /**
   * Throttle function calls
   */
  throttle(func, limit) {
    let inThrottle
    return function() {
      const args = arguments
      const context = this
      if (!inThrottle) {
        func.apply(context, args)
        inThrottle = true
        setTimeout(() => inThrottle = false, limit)
      }
    }
  }

  /**
   * Clear image cache
   */
  clearCache() {
    // Revoke object URLs to free memory
    for (const blob of this.cache.values()) {
      if (blob instanceof Blob) {
        URL.revokeObjectURL(blob)
      }
    }
    this.cache.clear()
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    const totalSize = Array.from(this.cache.values())
      .reduce((total, blob) => total + (blob.size || 0), 0)
    
    return {
      cachedImages: this.cache.size,
      totalSize: this.formatBytes(totalSize),
      loadingImages: this.loadingImages.size
    }
  }

  /**
   * Format bytes for human readability
   */
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes'
    
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
}

/**
 * WebP support detection and fallback
 */
export const checkWebPSupport = () => {
  return new Promise(resolve => {
    const webP = new Image()
    webP.onload = webP.onerror = () => {
      resolve(webP.height === 2)
    }
    webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA'
  })
}

/**
 * Progressive image loading with blur effect
 */
export const setupProgressiveLoading = (container) => {
  const images = container.querySelectorAll('img[data-src]')
  
  images.forEach(img => {
    // Create low-quality placeholder
    const placeholderSrc = img.dataset.placeholder
    if (placeholderSrc) {
      img.src = placeholderSrc
      img.style.filter = 'blur(10px)'
      img.style.transition = 'filter 0.3s ease'
    }

    // Load high-quality image
    const highQualitySrc = img.dataset.src
    if (highQualitySrc) {
      const highResImg = new Image()
      highResImg.onload = () => {
        img.src = highQualitySrc
        img.style.filter = 'blur(0px)'
        img.classList.add('loaded')
      }
      highResImg.src = highQualitySrc
    }
  })
}

// Singleton instance
export const imageOptimizer = new ImageOptimizer()

// Auto-cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    imageOptimizer.clearCache()
  })
}

export default imageOptimizer