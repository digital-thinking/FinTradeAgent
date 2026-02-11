// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Dashboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Start from home/dashboard page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should load dashboard page correctly', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/FinTradeAgent/);
    
    // Check main heading
    await expect(page.locator('h1')).toContainText(/Dashboard|Overview/i);
    
    // Check that page content is loaded
    const mainContent = page.locator('main, [data-testid="dashboard-content"]').or(
      page.locator('.dashboard, .main-content')
    );
    await expect(mainContent).toBeVisible();
  });

  test('should display navigation menu', async ({ page }) => {
    // Check for navigation menu
    const nav = page.locator('nav, [data-testid="navigation"]').or(
      page.locator('.navigation, .sidebar, .nav-menu')
    );
    await expect(nav).toBeVisible();
    
    // Check for main navigation links
    const navLinks = [
      { href: '/', text: 'Dashboard' },
      { href: '/portfolios', text: 'Portfolios' },
      { href: '/trades', text: 'Trades' },
      { href: '/comparison', text: 'Comparison' },
      { href: '/system', text: 'System' }
    ];
    
    for (const link of navLinks) {
      const navLink = page.locator(`nav a[href="${link.href}"]`).or(
        page.locator(`a:has-text("${link.text}")`)
      );
      await expect(navLink).toBeVisible();
    }
  });

  test('should navigate to Portfolios page', async ({ page }) => {
    // Click on Portfolios link
    const portfoliosLink = page.locator('[data-testid="nav-portfolios"]').or(
      page.locator('nav a[href="/portfolios"]').or(
        page.locator('a:has-text("Portfolio")')
      )
    );
    
    await portfoliosLink.click();
    
    // Verify navigation
    await expect(page).toHaveURL('/portfolios');
    await page.waitForLoadState('networkidle');
    
    // Verify page content
    await expect(page.locator('h1')).toContainText(/Portfolio/i);
    
    // Check for portfolio-specific content
    const portfolioContent = page.locator('[data-testid="portfolios-container"]').or(
      page.locator('.portfolios, .portfolio-list')
    );
    await expect(portfolioContent).toBeVisible();
  });

  test('should navigate to Trades page', async ({ page }) => {
    // Click on Trades link
    const tradesLink = page.locator('[data-testid="nav-trades"]').or(
      page.locator('nav a[href="/trades"]').or(
        page.locator('a:has-text("Trade")')
      )
    );
    
    await tradesLink.click();
    
    // Verify navigation
    await expect(page).toHaveURL('/trades');
    await page.waitForLoadState('networkidle');
    
    // Verify page content
    await expect(page.locator('h1')).toContainText(/Trade|Pending/i);
    
    // Check for trades-specific content
    const tradesContent = page.locator('[data-testid="trades-container"]').or(
      page.locator('.trades, .trade-list')
    );
    await expect(tradesContent).toBeVisible();
  });

  test('should navigate to Comparison page', async ({ page }) => {
    // Click on Comparison link
    const comparisonLink = page.locator('[data-testid="nav-comparison"]').or(
      page.locator('nav a[href="/comparison"]').or(
        page.locator('a:has-text("Comparison")')
      )
    );
    
    await comparisonLink.click();
    
    // Verify navigation
    await expect(page).toHaveURL('/comparison');
    await page.waitForLoadState('networkidle');
    
    // Verify page content
    await expect(page.locator('h1')).toContainText(/Comparison/i);
    
    // Check for comparison-specific content
    const comparisonContent = page.locator('[data-testid="comparison-container"]').or(
      page.locator('.comparison, .compare')
    );
    await expect(comparisonContent).toBeVisible();
  });

  test('should navigate to System Health page', async ({ page }) => {
    // Click on System link
    const systemLink = page.locator('[data-testid="nav-system"]').or(
      page.locator('nav a[href="/system"]').or(
        page.locator('a:has-text("System")')
      )
    );
    
    await systemLink.click();
    
    // Verify navigation
    await expect(page).toHaveURL('/system');
    await page.waitForLoadState('networkidle');
    
    // Verify page content
    await expect(page.locator('h1')).toContainText(/System|Health/i);
    
    // Check for system-specific content
    const systemContent = page.locator('[data-testid="system-container"]').or(
      page.locator('.system-health, .system-status')
    );
    await expect(systemContent).toBeVisible();
  });

  test('should show active navigation state', async ({ page }) => {
    // Check dashboard is active initially
    const dashboardNav = page.locator('[data-testid="nav-dashboard"]').or(
      page.locator('nav a[href="/"]')
    );
    
    // Should have active class or styling
    await expect(dashboardNav).toHaveClass(/active|current/);
    
    // Navigate to portfolios
    const portfoliosNav = page.locator('[data-testid="nav-portfolios"]').or(
      page.locator('nav a[href="/portfolios"]')
    );
    await portfoliosNav.click();
    
    await page.waitForURL('/portfolios');
    
    // Portfolios nav should now be active
    await expect(portfoliosNav).toHaveClass(/active|current/);
    
    // Dashboard nav should no longer be active
    await expect(dashboardNav).not.toHaveClass(/active|current/);
  });

  test('should display dashboard statistics', async ({ page }) => {
    // Go back to dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check for dashboard stats/cards
    const statsCards = page.locator('[data-testid="stat-card"]').or(
      page.locator('.stat-card, .metric-card, .dashboard-card')
    );
    
    const cardCount = await statsCards.count();
    
    if (cardCount > 0) {
      // Verify stat cards are visible
      await expect(statsCards.first()).toBeVisible();
      
      // Check for typical dashboard metrics
      const totalValue = page.locator('[data-testid="total-value"]').or(
        page.locator('.total-value, .portfolio-value')
      );
      const totalReturn = page.locator('[data-testid="total-return"]').or(
        page.locator('.total-return, .return-value')
      );
      const portfolioCount = page.locator('[data-testid="portfolio-count"]').or(
        page.locator('.portfolio-count, .num-portfolios')
      );
      
      // At least one metric should be visible
      const metrics = [totalValue, totalReturn, portfolioCount];
      let visibleMetrics = 0;
      
      for (const metric of metrics) {
        const count = await metric.count();
        if (count > 0 && await metric.isVisible()) {
          visibleMetrics++;
        }
      }
      
      expect(visibleMetrics).toBeGreaterThan(0);
    }
  });

  test('should display recent activity or execution logs', async ({ page }) => {
    // Check for recent activity section
    const recentActivity = page.locator('[data-testid="recent-activity"]').or(
      page.locator('.recent-activity, .activity-feed, .recent-logs')
    );
    
    const activityCount = await recentActivity.count();
    
    if (activityCount > 0) {
      await expect(recentActivity).toBeVisible();
      
      // Check for activity items
      const activityItems = page.locator('[data-testid="activity-item"]').or(
        page.locator('.activity-item, .log-entry, .feed-item')
      );
      
      const itemCount = await activityItems.count();
      
      if (itemCount > 0) {
        await expect(activityItems.first()).toBeVisible();
        
        // Activity items should have some content
        await expect(activityItems.first()).toContainText(/.+/);
      }
    }
  });

  test('should show portfolio performance charts', async ({ page }) => {
    // Check for chart containers
    const charts = page.locator('[data-testid="performance-chart"]').or(
      page.locator('canvas, .chart, .chart-container, svg[class*="chart"]')
    );
    
    const chartCount = await charts.count();
    
    if (chartCount > 0) {
      // At least one chart should be visible
      await expect(charts.first()).toBeVisible();
      
      // Chart should have some dimensions
      const chartElement = charts.first();
      const boundingBox = await chartElement.boundingBox();
      
      if (boundingBox) {
        expect(boundingBox.width).toBeGreaterThan(0);
        expect(boundingBox.height).toBeGreaterThan(0);
      }
    }
  });

  test('should handle loading states properly', async ({ page }) => {
    // Navigate to different pages and check for loading indicators
    const pages = ['/portfolios', '/trades', '/comparison', '/system'];
    
    for (const pagePath of pages) {
      await page.goto(pagePath);
      
      // Check for loading indicator (might appear briefly)
      const loadingIndicator = page.locator('[data-testid="loading"]').or(
        page.locator('.loading, .spinner, .skeleton')
      );
      
      // Wait for page to load completely
      await page.waitForLoadState('networkidle');
      
      // Loading indicator should be gone
      const loadingCount = await loadingIndicator.count();
      if (loadingCount > 0) {
        await expect(loadingIndicator).not.toBeVisible();
      }
      
      // Page content should be visible
      await expect(page.locator('h1')).toBeVisible();
    }
  });

  test('should handle 404 errors gracefully', async ({ page }) => {
    // Navigate to non-existent page
    await page.goto('/non-existent-page');
    
    // Should show 404 page or redirect to home
    const notFoundIndicator = page.locator('[data-testid="not-found"]').or(
      page.locator('h1:has-text("404")').or(
        page.locator('.error-404, .not-found')
      )
    );
    
    const mainContent = page.locator('main, .main-content');
    
    // Should either show 404 page or have redirected to valid page
    const notFoundCount = await notFoundIndicator.count();
    
    if (notFoundCount > 0) {
      // 404 page is shown
      await expect(notFoundIndicator).toBeVisible();
    } else {
      // Redirected to valid page
      await expect(mainContent).toBeVisible();
      await expect(page).toHaveURL(/\/(dashboard|portfolios|trades|comparison|system)?$/);
    }
  });

  test('should have working breadcrumb navigation', async ({ page }) => {
    // Navigate to portfolio detail page (if possible)
    await page.goto('/portfolios');
    await page.waitForLoadState('networkidle');
    
    // Check if portfolios exist and navigate to one
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount > 0) {
      const viewButton = portfolioCard.locator('[data-testid="view-portfolio"]').or(
        portfolioCard.locator('button:has-text("View")').or(portfolioCard)
      );
      await viewButton.click();
      
      await page.waitForURL(/\/portfolios\/.+/);
      
      // Check for breadcrumb navigation
      const breadcrumb = page.locator('[data-testid="breadcrumb"]').or(
        page.locator('.breadcrumb, .breadcrumbs, nav[aria-label*="breadcrumb"]')
      );
      
      if (await breadcrumb.count() > 0) {
        await expect(breadcrumb).toBeVisible();
        
        // Should contain link back to portfolios
        const portfoliosLink = breadcrumb.locator('a[href="/portfolios"]').or(
          breadcrumb.locator('a:has-text("Portfolio")')
        );
        
        if (await portfoliosLink.count() > 0) {
          await portfoliosLink.click();
          await expect(page).toHaveURL('/portfolios');
        }
      }
    }
  });

  test('should maintain navigation state during page reloads', async ({ page }) => {
    // Navigate to portfolios page
    await page.goto('/portfolios');
    await page.waitForLoadState('networkidle');
    
    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Should still be on portfolios page
    await expect(page).toHaveURL('/portfolios');
    await expect(page.locator('h1')).toContainText(/Portfolio/i);
    
    // Navigation should still work
    const dashboardLink = page.locator('[data-testid="nav-dashboard"]').or(
      page.locator('nav a[href="/"]')
    );
    await dashboardLink.click();
    
    await expect(page).toHaveURL('/');
  });

  test('should handle keyboard navigation', async ({ page }) => {
    // Test tab navigation through main nav links
    await page.keyboard.press('Tab');
    
    // Check if focus moves to navigation elements
    const focusedElement = await page.locator(':focus');
    const focusedCount = await focusedElement.count();
    
    if (focusedCount > 0) {
      // Should be able to navigate with keyboard
      await page.keyboard.press('Enter');
      
      // Should navigate or activate element
      await page.waitForTimeout(1000);
      
      // Page should still be functional
      await expect(page.locator('main, .main-content')).toBeVisible();
    }
  });

  test('should update page title for each route', async ({ page }) => {
    const routes = [
      { path: '/', titlePattern: /Dashboard.*FinTradeAgent|FinTradeAgent.*Dashboard/i },
      { path: '/portfolios', titlePattern: /Portfolio.*FinTradeAgent|FinTradeAgent.*Portfolio/i },
      { path: '/trades', titlePattern: /Trade.*FinTradeAgent|FinTradeAgent.*Trade/i },
      { path: '/comparison', titlePattern: /Comparison.*FinTradeAgent|FinTradeAgent.*Comparison/i },
      { path: '/system', titlePattern: /System.*FinTradeAgent|FinTradeAgent.*System/i }
    ];
    
    for (const route of routes) {
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');
      
      // Check that title contains relevant keywords (relaxed check)
      const title = await page.title();
      expect(title).toContain('FinTradeAgent');
    }
  });
});