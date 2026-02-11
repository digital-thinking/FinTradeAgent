#!/usr/bin/env node
/**
 * Lighthouse performance testing for FinTradeAgent
 * Runs automated performance audits and generates reports
 */

const lighthouse = require('lighthouse')
const chromeLauncher = require('chrome-launcher')
const fs = require('fs')
const path = require('path')

class LighthouseRunner {
  constructor() {
    this.baseUrl = 'http://localhost:3000'
    this.reportDir = path.join(__dirname, '..', 'reports', 'lighthouse')
    this.config = {
      extends: 'lighthouse:default',
      settings: {
        formFactor: 'desktop',
        throttling: {
          rttMs: 40,
          throughputKbps: 10240,
          cpuSlowdownMultiplier: 1,
          requestLatencyMs: 0,
          downloadThroughputKbps: 0,
          uploadThroughputKbps: 0
        },
        screenEmulation: {
          mobile: false,
          width: 1350,
          height: 940,
          deviceScaleFactor: 1,
          disabled: false
        },
        emulatedUserAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    }
  }

  async runAudits() {
    console.log('🔍 Starting Lighthouse performance audits...\n')
    
    // Ensure report directory exists
    if (!fs.existsSync(this.reportDir)) {
      fs.mkdirSync(this.reportDir, { recursive: true })
    }

    const urls = [
      { path: '/', name: 'Dashboard' },
      { path: '/portfolios', name: 'Portfolios' },
      { path: '/portfolios/Tech%20Portfolio', name: 'Portfolio Detail' },
      { path: '/trades', name: 'Pending Trades' },
      { path: '/comparison', name: 'Comparison' },
      { path: '/system', name: 'System Health' }
    ]

    const results = []
    const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless'] })
    
    try {
      for (const url of urls) {
        console.log(`🔍 Auditing ${url.name} (${url.path})...`)
        
        const result = await this.runSingleAudit(url, chrome.port)
        results.push(result)
        
        // Generate individual report
        await this.generateReport(result, url.name)
        
        console.log(`✅ ${url.name} audit complete`)
        console.log(`   Performance Score: ${result.scores.performance}/100`)
        console.log(`   Load Time: ${result.metrics.firstContentfulPaint}ms`)
        console.log('')
      }
      
      // Generate summary report
      await this.generateSummaryReport(results)
      
      // Display results
      this.displayResults(results)
      
    } finally {
      await chrome.kill()
    }
  }

  async runSingleAudit(url, port) {
    const fullUrl = `${this.baseUrl}${url.path}`
    
    const options = {
      logLevel: 'silent',
      output: 'json',
      onlyCategories: ['performance'],
      port
    }

    try {
      const runnerResult = await lighthouse(fullUrl, options, this.config)
      return this.processLighthouseResult(runnerResult, url)
    } catch (error) {
      console.error(`Error auditing ${url.name}:`, error.message)
      return {
        url,
        error: error.message,
        scores: { performance: 0 },
        metrics: {},
        audits: {}
      }
    }
  }

  processLighthouseResult(runnerResult, url) {
    const lhr = runnerResult.lhr
    
    return {
      url,
      timestamp: new Date().toISOString(),
      scores: {
        performance: Math.round(lhr.categories.performance.score * 100),
      },
      metrics: {
        firstContentfulPaint: Math.round(lhr.audits['first-contentful-paint'].numericValue),
        largestContentfulPaint: Math.round(lhr.audits['largest-contentful-paint'].numericValue),
        speedIndex: Math.round(lhr.audits['speed-index'].numericValue),
        timeToInteractive: Math.round(lhr.audits['interactive'].numericValue),
        totalBlockingTime: Math.round(lhr.audits['total-blocking-time'].numericValue),
        cumulativeLayoutShift: Math.round(lhr.audits['cumulative-layout-shift'].numericValue * 1000) / 1000,
      },
      audits: {
        unusedJavascript: this.processAudit(lhr.audits['unused-javascript']),
        unusedCssRules: this.processAudit(lhr.audits['unused-css-rules']),
        renderBlockingResources: this.processAudit(lhr.audits['render-blocking-resources']),
        unminifiedCss: this.processAudit(lhr.audits['unminified-css']),
        unminifiedJavascript: this.processAudit(lhr.audits['unminified-javascript']),
        textCompression: this.processAudit(lhr.audits['uses-text-compression']),
        imageOptimization: this.processAudit(lhr.audits['uses-optimized-images']),
        nextGenFormats: this.processAudit(lhr.audits['uses-webp-images']),
        criticalRequestChains: this.processAudit(lhr.audits['critical-request-chains'])
      },
      opportunities: this.extractOpportunities(lhr),
      diagnostics: this.extractDiagnostics(lhr),
      fullResult: lhr
    }
  }

  processAudit(audit) {
    if (!audit) return null
    
    return {
      score: audit.score,
      numericValue: audit.numericValue,
      displayValue: audit.displayValue,
      description: audit.description,
      details: audit.details
    }
  }

  extractOpportunities(lhr) {
    const opportunities = []
    
    for (const auditId of Object.keys(lhr.audits)) {
      const audit = lhr.audits[auditId]
      if (audit.score !== null && audit.score < 1 && audit.numericValue > 0) {
        opportunities.push({
          id: auditId,
          title: audit.title,
          description: audit.description,
          score: audit.score,
          numericValue: audit.numericValue,
          displayValue: audit.displayValue,
          savings: this.calculateSavings(audit)
        })
      }
    }
    
    return opportunities.sort((a, b) => b.savings - a.savings)
  }

  extractDiagnostics(lhr) {
    const diagnostics = []
    const diagnosticAudits = [
      'mainthread-work-breakdown',
      'bootup-time',
      'uses-passive-event-listeners',
      'font-display',
      'third-party-summary'
    ]
    
    for (const auditId of diagnosticAudits) {
      const audit = lhr.audits[auditId]
      if (audit && audit.score !== null && audit.score < 1) {
        diagnostics.push({
          id: auditId,
          title: audit.title,
          description: audit.description,
          score: audit.score,
          displayValue: audit.displayValue
        })
      }
    }
    
    return diagnostics
  }

  calculateSavings(audit) {
    if (audit.numericValue && audit.numericValue > 0) {
      return audit.numericValue
    }
    return 0
  }

  async generateReport(result, pageName) {
    const reportPath = path.join(
      this.reportDir, 
      `${pageName.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.json`
    )
    
    fs.writeFileSync(reportPath, JSON.stringify(result, null, 2))
  }

  async generateSummaryReport(results) {
    const summary = {
      timestamp: new Date().toISOString(),
      totalPages: results.length,
      averagePerformanceScore: Math.round(
        results.reduce((sum, r) => sum + r.scores.performance, 0) / results.length
      ),
      results: results.map(r => ({
        page: r.url.name,
        path: r.url.path,
        performance: r.scores.performance,
        fcp: r.metrics.firstContentfulPaint,
        lcp: r.metrics.largestContentfulPaint,
        tti: r.metrics.timeToInteractive,
        cls: r.metrics.cumulativeLayoutShift
      })),
      recommendations: this.generateRecommendations(results)
    }
    
    const summaryPath = path.join(this.reportDir, `summary-${Date.now()}.json`)
    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2))
    
    console.log(`💾 Summary report saved: ${summaryPath}`)
    return summary
  }

  generateRecommendations(results) {
    const recommendations = []
    const commonIssues = {}
    
    // Analyze common performance issues across all pages
    results.forEach(result => {
      Object.entries(result.audits).forEach(([auditId, audit]) => {
        if (audit && audit.score < 0.9) {
          if (!commonIssues[auditId]) {
            commonIssues[auditId] = { count: 0, pages: [] }
          }
          commonIssues[auditId].count++
          commonIssues[auditId].pages.push(result.url.name)
        }
      })
    })
    
    // Generate recommendations based on common issues
    for (const [auditId, issue] of Object.entries(commonIssues)) {
      if (issue.count >= results.length * 0.5) { // Affects 50% or more pages
        recommendations.push({
          type: 'critical',
          category: auditId,
          title: `${auditId.replace(/-/g, ' ').toUpperCase()} optimization needed`,
          description: `This issue affects ${issue.count}/${results.length} pages`,
          pages: issue.pages,
          priority: issue.count / results.length
        })
      }
    }
    
    // Performance-specific recommendations
    const avgFCP = results.reduce((sum, r) => sum + r.metrics.firstContentfulPaint, 0) / results.length
    const avgLCP = results.reduce((sum, r) => sum + r.metrics.largestContentfulPaint, 0) / results.length
    
    if (avgFCP > 2000) {
      recommendations.push({
        type: 'warning',
        category: 'first-contentful-paint',
        title: 'Slow First Contentful Paint',
        description: `Average FCP is ${Math.round(avgFCP)}ms (target: <2000ms)`,
        priority: 0.8
      })
    }
    
    if (avgLCP > 2500) {
      recommendations.push({
        type: 'warning',
        category: 'largest-contentful-paint',
        title: 'Slow Largest Contentful Paint',
        description: `Average LCP is ${Math.round(avgLCP)}ms (target: <2500ms)`,
        priority: 0.9
      })
    }
    
    return recommendations.sort((a, b) => b.priority - a.priority)
  }

  displayResults(results) {
    console.log('\n📊 Lighthouse Performance Results')
    console.log('='.repeat(50))
    
    // Summary table
    console.log('\n📈 Performance Scores:')
    results.forEach(result => {
      const score = result.scores.performance
      const icon = score >= 90 ? '🟢' : score >= 50 ? '🟡' : '🔴'
      console.log(`  ${icon} ${result.url.name.padEnd(20)} ${score}/100`)
    })
    
    // Average metrics
    const avgMetrics = this.calculateAverageMetrics(results)
    console.log('\n📊 Average Metrics:')
    console.log(`  First Contentful Paint: ${avgMetrics.fcp}ms`)
    console.log(`  Largest Contentful Paint: ${avgMetrics.lcp}ms`)
    console.log(`  Time to Interactive: ${avgMetrics.tti}ms`)
    console.log(`  Cumulative Layout Shift: ${avgMetrics.cls}`)
    
    // Top opportunities
    console.log('\n🎯 Top Optimization Opportunities:')
    const allOpportunities = results.flatMap(r => r.opportunities || [])
    const topOpportunities = allOpportunities
      .sort((a, b) => b.savings - a.savings)
      .slice(0, 5)
    
    topOpportunities.forEach((opp, index) => {
      console.log(`  ${index + 1}. ${opp.title}`)
      console.log(`     Potential savings: ${opp.displayValue || 'N/A'}`)
    })
    
    console.log('\n💡 Run individual page reports for detailed recommendations')
  }

  calculateAverageMetrics(results) {
    const validResults = results.filter(r => !r.error)
    
    return {
      fcp: Math.round(validResults.reduce((sum, r) => sum + r.metrics.firstContentfulPaint, 0) / validResults.length),
      lcp: Math.round(validResults.reduce((sum, r) => sum + r.metrics.largestContentfulPaint, 0) / validResults.length),
      tti: Math.round(validResults.reduce((sum, r) => sum + r.metrics.timeToInteractive, 0) / validResults.length),
      cls: Math.round((validResults.reduce((sum, r) => sum + r.metrics.cumulativeLayoutShift, 0) / validResults.length) * 1000) / 1000
    }
  }
}

// CLI execution
async function main() {
  const args = process.argv.slice(2)
  
  if (args.includes('--help')) {
    console.log(`
Lighthouse Performance Testing for FinTradeAgent

Usage:
  node lighthouse-test.js [options]

Options:
  --help          Show this help message
  --url <url>     Base URL (default: http://localhost:3000)
  --mobile        Run mobile audits instead of desktop
  --fast          Use fast network simulation
  --slow          Use slow 3G network simulation

Examples:
  node lighthouse-test.js
  node lighthouse-test.js --mobile
  node lighthouse-test.js --url http://localhost:8080
`)
    return
  }
  
  const runner = new LighthouseRunner()
  
  // Process CLI arguments
  if (args.includes('--mobile')) {
    runner.config.settings.formFactor = 'mobile'
    runner.config.settings.screenEmulation.mobile = true
  }
  
  const urlIndex = args.indexOf('--url')
  if (urlIndex !== -1 && args[urlIndex + 1]) {
    runner.baseUrl = args[urlIndex + 1]
  }
  
  if (args.includes('--fast')) {
    runner.config.settings.throttling = {
      rttMs: 20,
      throughputKbps: 50000,
      cpuSlowdownMultiplier: 1
    }
  }
  
  if (args.includes('--slow')) {
    runner.config.settings.throttling = {
      rttMs: 150,
      throughputKbps: 1600,
      cpuSlowdownMultiplier: 4
    }
  }
  
  try {
    await runner.runAudits()
    console.log('\n✅ Lighthouse audits completed successfully!')
  } catch (error) {
    console.error('\n❌ Lighthouse audit failed:', error.message)
    process.exit(1)
  }
}

if (require.main === module) {
  main().catch(console.error)
}

module.exports = LighthouseRunner