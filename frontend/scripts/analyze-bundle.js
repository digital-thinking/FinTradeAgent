#!/usr/bin/env node
/**
 * Bundle analysis script for FinTradeAgent frontend
 * Analyzes build output and provides optimization recommendations
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

class BundleAnalyzer {
  constructor() {
    this.distPath = path.join(__dirname, '..', 'dist')
    this.results = {
      assets: [],
      chunks: [],
      recommendations: [],
      metrics: {}
    }
  }

  async analyze() {
    console.log('🔍 Analyzing bundle...\n')
    
    if (!fs.existsSync(this.distPath)) {
      console.error('❌ Build directory not found. Please run "npm run build" first.')
      process.exit(1)
    }

    // Analyze assets
    this.analyzeAssets()
    
    // Analyze JavaScript chunks
    this.analyzeJSChunks()
    
    // Analyze CSS files
    this.analyzeCSSFiles()
    
    // Calculate metrics
    this.calculateMetrics()
    
    // Generate recommendations
    this.generateRecommendations()
    
    // Display results
    this.displayResults()
    
    // Save analysis report
    this.saveReport()
  }

  analyzeAssets() {
    const assetsDir = path.join(this.distPath, 'assets')
    if (!fs.existsSync(assetsDir)) return

    const analyzeDir = (dir, category) => {
      const files = fs.readdirSync(dir)
      
      files.forEach(file => {
        const filePath = path.join(dir, file)
        const stats = fs.statSync(filePath)
        
        if (stats.isFile()) {
          this.results.assets.push({
            name: file,
            category,
            size: stats.size,
            sizeKB: Math.round(stats.size / 1024),
            sizeMB: Math.round(stats.size / (1024 * 1024) * 100) / 100
          })
        }
      })
    }

    // Analyze different asset types
    const subDirs = fs.readdirSync(assetsDir)
    
    subDirs.forEach(subDir => {
      const subDirPath = path.join(assetsDir, subDir)
      if (fs.statSync(subDirPath).isDirectory()) {
        analyzeDir(subDirPath, subDir)
      } else {
        // Files directly in assets folder
        const stats = fs.statSync(subDirPath)
        this.results.assets.push({
          name: subDir,
          category: this.getCategoryFromExtension(subDir),
          size: stats.size,
          sizeKB: Math.round(stats.size / 1024),
          sizeMB: Math.round(stats.size / (1024 * 1024) * 100) / 100
        })
      }
    })
  }

  analyzeJSChunks() {
    const jsAssets = this.results.assets.filter(asset => 
      asset.name.endsWith('.js') || asset.category === 'js'
    )

    jsAssets.forEach(asset => {
      const chunkInfo = this.analyzeJSChunk(asset)
      this.results.chunks.push(chunkInfo)
    })
  }

  analyzeJSChunk(asset) {
    // Determine chunk type based on name
    let type = 'unknown'
    let purpose = 'Unknown'

    if (asset.name.includes('vendor')) {
      type = 'vendor'
      purpose = 'Third-party libraries'
    } else if (asset.name.includes('pages-')) {
      type = 'page'
      purpose = 'Page components'
    } else if (asset.name.includes('components-')) {
      type = 'component'
      purpose = 'Shared components'
    } else if (asset.name.includes('main') || asset.name.includes('index')) {
      type = 'entry'
      purpose = 'Application entry point'
    } else if (asset.name.includes('chunk')) {
      type = 'dynamic'
      purpose = 'Lazy-loaded content'
    }

    return {
      ...asset,
      type,
      purpose,
      isLarge: asset.sizeKB > 250,
      isHuge: asset.sizeKB > 500
    }
  }

  analyzeCSSFiles() {
    const cssAssets = this.results.assets.filter(asset => 
      asset.name.endsWith('.css') || asset.category === 'css'
    )

    // Add CSS-specific analysis
    cssAssets.forEach(asset => {
      asset.type = 'stylesheet'
      asset.purpose = 'Styling'
      asset.isLarge = asset.sizeKB > 50
    })
  }

  calculateMetrics() {
    const assets = this.results.assets
    
    this.results.metrics = {
      totalSize: assets.reduce((sum, asset) => sum + asset.size, 0),
      totalSizeKB: Math.round(assets.reduce((sum, asset) => sum + asset.sizeKB, 0)),
      totalSizeMB: Math.round(assets.reduce((sum, asset) => sum + asset.sizeMB, 0) * 100) / 100,
      
      jsSize: this.getSizeByCategory(['js']),
      cssSize: this.getSizeByCategory(['css']),
      imageSize: this.getSizeByCategory(['img', 'images']),
      fontSize: this.getSizeByCategory(['fonts']),
      
      chunkCount: this.results.chunks.length,
      largeChunks: this.results.chunks.filter(chunk => chunk.isLarge).length,
      hugeChunks: this.results.chunks.filter(chunk => chunk.isHuge).length,
      
      gzipEstimate: Math.round(this.results.metrics?.totalSizeKB * 0.3) // Rough gzip estimate
    }
  }

  getSizeByCategory(categories) {
    return this.results.assets
      .filter(asset => categories.includes(asset.category))
      .reduce((sum, asset) => sum + asset.sizeKB, 0)
  }

  generateRecommendations() {
    const metrics = this.results.metrics
    const chunks = this.results.chunks

    // Bundle size recommendations
    if (metrics.totalSizeMB > 5) {
      this.results.recommendations.push({
        type: 'critical',
        category: 'bundle-size',
        title: 'Bundle size is very large',
        description: `Total bundle size is ${metrics.totalSizeMB}MB. Consider code splitting and lazy loading.`,
        actions: [
          'Implement more aggressive code splitting',
          'Lazy load non-critical components',
          'Review and remove unused dependencies'
        ]
      })
    } else if (metrics.totalSizeMB > 2) {
      this.results.recommendations.push({
        type: 'warning',
        category: 'bundle-size',
        title: 'Bundle size could be optimized',
        description: `Bundle size is ${metrics.totalSizeMB}MB. Consider additional optimizations.`,
        actions: [
          'Implement code splitting for large pages',
          'Optimize images and assets'
        ]
      })
    }

    // Chunk size recommendations
    const hugeChunks = chunks.filter(chunk => chunk.isHuge)
    if (hugeChunks.length > 0) {
      this.results.recommendations.push({
        type: 'warning',
        category: 'chunk-size',
        title: `${hugeChunks.length} chunk(s) are very large`,
        description: 'Large chunks can slow down initial load times.',
        actions: [
          'Split large chunks further',
          'Move heavy dependencies to separate chunks',
          'Consider lazy loading for non-critical features'
        ],
        details: hugeChunks.map(chunk => `${chunk.name}: ${chunk.sizeKB}KB`)
      })
    }

    // JavaScript recommendations
    if (metrics.jsSize > 1000) {
      this.results.recommendations.push({
        type: 'warning',
        category: 'javascript',
        title: 'JavaScript bundle is large',
        description: `JavaScript size: ${metrics.jsSize}KB`,
        actions: [
          'Enable tree shaking',
          'Remove unused code',
          'Consider using smaller alternatives for heavy libraries'
        ]
      })
    }

    // CSS recommendations
    if (metrics.cssSize > 200) {
      this.results.recommendations.push({
        type: 'info',
        category: 'css',
        title: 'CSS bundle could be optimized',
        description: `CSS size: ${metrics.cssSize}KB`,
        actions: [
          'Remove unused CSS',
          'Consider CSS-in-JS for component-specific styles',
          'Use PurgeCSS to eliminate dead code'
        ]
      })
    }

    // Performance recommendations
    if (chunks.some(chunk => chunk.type === 'vendor' && chunk.sizeKB > 400)) {
      this.results.recommendations.push({
        type: 'warning',
        category: 'performance',
        title: 'Vendor chunk is large',
        description: 'Large vendor chunks can slow down the application startup.',
        actions: [
          'Split vendor chunk by usage frequency',
          'Load non-critical libraries on demand',
          'Consider using CDN for common libraries'
        ]
      })
    }
  }

  displayResults() {
    console.log('📊 Bundle Analysis Results')
    console.log('=' .repeat(50))
    console.log()

    // Summary metrics
    console.log('📈 Summary Metrics:')
    console.log(`  Total Size: ${this.results.metrics.totalSizeMB}MB (${this.results.metrics.totalSizeKB}KB)`)
    console.log(`  JavaScript: ${this.results.metrics.jsSize}KB`)
    console.log(`  CSS: ${this.results.metrics.cssSize}KB`)
    console.log(`  Images: ${this.results.metrics.imageSize}KB`)
    console.log(`  Fonts: ${this.results.metrics.fontSize}KB`)
    console.log(`  Estimated Gzipped: ~${this.results.metrics.gzipEstimate}KB`)
    console.log()

    // Chunk analysis
    console.log('🧩 Chunk Analysis:')
    console.log(`  Total Chunks: ${this.results.metrics.chunkCount}`)
    console.log(`  Large Chunks (>250KB): ${this.results.metrics.largeChunks}`)
    console.log(`  Huge Chunks (>500KB): ${this.results.metrics.hugeChunks}`)
    console.log()

    // Top 10 largest assets
    const sortedAssets = [...this.results.assets].sort((a, b) => b.sizeKB - a.sizeKB)
    console.log('📦 Top 10 Largest Assets:')
    sortedAssets.slice(0, 10).forEach((asset, index) => {
      console.log(`  ${index + 1}. ${asset.name} (${asset.category}) - ${asset.sizeKB}KB`)
    })
    console.log()

    // Recommendations
    if (this.results.recommendations.length > 0) {
      console.log('💡 Recommendations:')
      this.results.recommendations.forEach((rec, index) => {
        const icon = rec.type === 'critical' ? '🚨' : rec.type === 'warning' ? '⚠️' : 'ℹ️'
        console.log(`  ${icon} ${rec.title}`)
        console.log(`     ${rec.description}`)
        rec.actions.forEach(action => {
          console.log(`     - ${action}`)
        })
        if (rec.details) {
          rec.details.forEach(detail => {
            console.log(`     → ${detail}`)
          })
        }
        console.log()
      })
    } else {
      console.log('✅ No optimization recommendations at this time!')
      console.log()
    }

    // Performance score
    const score = this.calculatePerformanceScore()
    console.log('🎯 Performance Score:')
    console.log(`   ${score}/100 ${this.getScoreEmoji(score)}`)
    console.log()
  }

  calculatePerformanceScore() {
    let score = 100
    const metrics = this.results.metrics

    // Deduct points for large bundle
    if (metrics.totalSizeMB > 5) score -= 30
    else if (metrics.totalSizeMB > 2) score -= 15
    else if (metrics.totalSizeMB > 1) score -= 5

    // Deduct points for large chunks
    score -= this.results.metrics.hugeChunks * 10
    score -= this.results.metrics.largeChunks * 5

    // Deduct points for recommendations
    const criticalRecs = this.results.recommendations.filter(r => r.type === 'critical').length
    const warningRecs = this.results.recommendations.filter(r => r.type === 'warning').length
    
    score -= criticalRecs * 15
    score -= warningRecs * 5

    return Math.max(0, score)
  }

  getScoreEmoji(score) {
    if (score >= 90) return '🟢 Excellent'
    if (score >= 75) return '🟡 Good'
    if (score >= 60) return '🟠 Needs Improvement'
    return '🔴 Poor'
  }

  getCategoryFromExtension(filename) {
    const ext = path.extname(filename).toLowerCase()
    
    if (['.js', '.mjs'].includes(ext)) return 'js'
    if (['.css'].includes(ext)) return 'css'
    if (['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'].includes(ext)) return 'img'
    if (['.woff', '.woff2', '.ttf', '.eot'].includes(ext)) return 'fonts'
    
    return 'other'
  }

  saveReport() {
    const reportPath = path.join(__dirname, '..', 'bundle-analysis.json')
    const report = {
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      ...this.results
    }
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
    console.log(`💾 Detailed report saved to: ${reportPath}`)
  }
}

// Run analysis if called directly
if (require.main === module) {
  const analyzer = new BundleAnalyzer()
  analyzer.analyze().catch(console.error)
}

module.exports = BundleAnalyzer