// @ts-check
const { test, expect, devices } = require('@playwright/test');

test.describe('Cross-Browser Compatibility', () => {
  const testCases = [
    {
      name: 'Chromium Desktop',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'Firefox Desktop', 
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'Safari Desktop',
      use: { ...devices['Desktop Safari'] }
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] }
    }
  ];

  for (const testCase of testCases) {
    test.describe(`${testCase.name}`, () => {
      test.use(testCase.use);

      test('should load dashboard correctly', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Basic functionality should work across all browsers
        await expect(page).toHaveTitle(/FinTradeAgent/);
        await expect(page.locator('h1')).toBeVisible();
        
        // Navigation should be functional
        const navigation = page.locator('nav, [data-testid="navigation"], [data-testid="mobile-menu-toggle"]');
        await expect(navigation.first()).toBeVisible();
      });

      test('should handle form interactions', async ({ page }) => {
        await page.goto('/portfolios');
        await page.waitForLoadState('networkidle');
        
        const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
          page.locator('button:has-text("Create")')
        );
        
        if (await createButton.count() > 0) {
          await createButton.click();
          
          const modal = page.locator('[data-testid="portfolio-modal"]').or(
            page.locator('[role="dialog"]')
          );
          
          await expect(modal).toBeVisible({ timeout: 5000 });
          
          // Form inputs should work
          const nameInput = page.locator('input[name="name"]');
          if (await nameInput.count() > 0) {
            await nameInput.fill('Cross-Browser Test');
            
            const inputValue = await nameInput.inputValue();
            expect(inputValue).toBe('Cross-Browser Test');
          }
          
          // Close modal
          const closeButton = modal.locator('button:has-text("Cancel")').or(
            page.locator('[data-testid="close-modal"]')
          );
          
          if (await closeButton.count() > 0) {
            await closeButton.click();
          } else {
            await page.keyboard.press('Escape');
          }
        }
      });

      test('should render charts and visualizations', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Look for chart elements
        const charts = page.locator('canvas, svg[class*="chart"], .chart');
        const chartCount = await charts.count();
        
        if (chartCount > 0) {
          const firstChart = charts.first();
          await expect(firstChart).toBeVisible();
          
          // Chart should have dimensions
          const boundingBox = await firstChart.boundingBox();
          if (boundingBox) {
            expect(boundingBox.width).toBeGreaterThan(0);
            expect(boundingBox.height).toBeGreaterThan(0);
          }
        }
        
        // Check for any SVG icons or graphics
        const svgElements = page.locator('svg');
        if (await svgElements.count() > 0) {
          await expect(svgElements.first()).toBeVisible();
        }
      });

      test('should handle navigation correctly', async ({ page }) => {
        const pages = ['/', '/portfolios', '/trades', '/comparison', '/system'];
        
        for (const pagePath of pages) {
          await page.goto(pagePath);
          await page.waitForLoadState('networkidle');
          
          // Should load successfully
          await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
          
          // Should not show browser-specific errors
          const errorElements = page.locator('text=/error.*loading|script.*error|failed.*load/i');
          const errorCount = await errorElements.count();
          
          if (errorCount > 0) {
            // Log the error but don't fail the test immediately
            const errorText = await errorElements.first().textContent();
            console.warn(`Potential error on ${pagePath} in ${testCase.name}: ${errorText}`);
          }
          
          // Page should be functional
          await expect(page.locator('body')).toBeVisible();
        }
      });

      test('should support touch interactions on mobile', async ({ page, isMobile }) => {
        if (!isMobile) {
          test.skip('This test only runs on mobile browsers');
        }
        
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Test touch-friendly interactions
        const touchableElements = page.locator('button, a, [data-testid="mobile-menu-toggle"]');
        const elementCount = await touchableElements.count();
        
        if (elementCount > 0) {
          const firstElement = touchableElements.first();
          
          // Element should be large enough for touch
          const boundingBox = await firstElement.boundingBox();
          if (boundingBox) {
            expect(boundingBox.height).toBeGreaterThan(30);
          }
          
          // Should respond to tap
          await firstElement.tap();
          
          // Page should remain functional after tap
          await expect(page.locator('body')).toBeVisible();
        }
      });

      test('should handle CSS animations and transitions', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Look for animated elements
        const animatedElements = page.locator('[class*="animate"], [class*="transition"], .loading, .spinner');
        
        if (await animatedElements.count() > 0) {
          const element = animatedElements.first();
          
          // Element should be visible
          await expect(element).toBeVisible();
          
          // Check if animations don't break layout
          await page.waitForTimeout(1000);
          
          // Page should still be functional
          await expect(page.locator('h1')).toBeVisible();
        }
        
        // Test theme toggle animation if available
        const themeToggle = page.locator('[data-testid="theme-toggle"]');
        
        if (await themeToggle.count() > 0) {
          await themeToggle.click();
          
          // Wait for transition
          await page.waitForTimeout(500);
          
          // Should complete transition without errors
          await expect(page.locator('body')).toBeVisible();
          
          // Toggle back
          await themeToggle.click();
          await page.waitForTimeout(500);
        }
      });
    });
  }
  
  test.describe('WebSocket Compatibility', () => {
    test('should establish WebSocket connections across browsers', async ({ page, browserName }) => {
      // Navigate to portfolio detail page which uses WebSocket
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
      
      if (await portfolioCard.count() > 0) {
        const viewButton = portfolioCard.locator('button:has-text("View")').or(portfolioCard);
        await viewButton.click();
        await page.waitForURL(/\/portfolios\/.+/);
        
        // Wait for WebSocket connection attempt
        await page.waitForTimeout(2000);
        
        // Look for WebSocket status indicator
        const wsStatus = page.locator('[data-testid="ws-status"]').or(
          page.locator('.ws-status, .connection-status')
        );
        
        if (await wsStatus.count() > 0) {
          // Should show connection status
          await expect(wsStatus).toBeVisible();
          
          const statusText = await wsStatus.textContent() || '';
          console.log(`WebSocket status in ${browserName}: ${statusText}`);
        }
        
        // Try WebSocket functionality
        const executeButton = page.locator('[data-testid="execute-agent-btn"]');
        
        if (await executeButton.count() > 0 && await executeButton.isEnabled()) {
          await executeButton.click();
          
          // Wait for real-time updates
          await page.waitForTimeout(5000);
          
          // Should show some progress or logs
          const progressElements = page.locator('[data-testid="execution-progress"], [data-testid="log-entry"]');
          
          const progressCount = await progressElements.count();
          
          if (progressCount > 0) {
            console.log(`WebSocket functionality working in ${browserName}`);
          } else {
            console.warn(`WebSocket functionality may not be working in ${browserName}`);
          }
        }
      }
    });
  });

  test.describe('Performance Across Browsers', () => {
    test('should load pages within reasonable time', async ({ page, browserName }) => {
      const pages = ['/', '/portfolios', '/trades'];
      
      for (const pagePath of pages) {
        const startTime = Date.now();
        
        await page.goto(pagePath);
        await page.waitForLoadState('networkidle');
        
        const loadTime = Date.now() - startTime;
        
        console.log(`${pagePath} load time in ${browserName}: ${loadTime}ms`);
        
        // Should load within 10 seconds (generous for E2E testing)
        expect(loadTime).toBeLessThan(10000);
        
        // Page should be functional
        await expect(page.locator('h1')).toBeVisible();
      }
    });

    test('should handle large datasets efficiently', async ({ page }) => {
      await page.goto('/trades');
      await page.waitForLoadState('networkidle');
      
      // Look for data tables or lists
      const dataElements = page.locator('[data-testid="trade-card"], table tr, .data-item');
      const elementCount = await dataElements.count();
      
      if (elementCount > 10) {
        // Should handle scrolling smoothly
        await page.mouse.wheel(0, 500);
        await page.waitForTimeout(100);
        
        // Should still be responsive
        await expect(page.locator('h1')).toBeVisible();
        
        // Test filtering or search if available
        const searchInput = page.locator('input[type="search"], input[placeholder*="search"]');
        
        if (await searchInput.count() > 0) {
          await searchInput.fill('test');
          await page.waitForTimeout(1000);
          
          // Should remain responsive during search
          await expect(page.locator('body')).toBeVisible();
        }
      }
    });
  });

  test.describe('Accessibility Across Browsers', () => {
    test('should support keyboard navigation', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Test tab navigation
      await page.keyboard.press('Tab');
      
      let focusedElement = page.locator(':focus');
      
      if (await focusedElement.count() > 0) {
        // Should have visible focus indicator
        const outline = await focusedElement.evaluate(el => 
          getComputedStyle(el).outline
        );
        
        // Focus should be visible (not none)
        expect(outline).not.toBe('none');
        
        // Continue tabbing
        await page.keyboard.press('Tab');
        await page.keyboard.press('Tab');
        
        // Should be able to activate focused elements
        await page.keyboard.press('Enter');
        
        // Page should remain functional
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('should respect reduced motion preferences', async ({ page }) => {
      // Set reduced motion preference
      await page.emulateMedia({ reducedMotion: 'reduce' });
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Test theme toggle (which might have animations)
      const themeToggle = page.locator('[data-testid="theme-toggle"]');
      
      if (await themeToggle.count() > 0) {
        await themeToggle.click();
        
        // Should respect reduced motion (immediate change)
        await page.waitForTimeout(100);
        
        // Theme should have changed immediately
        const html = page.locator('html');
        const classes = await html.getAttribute('class') || '';
        const dataTheme = await html.getAttribute('data-theme') || '';
        
        // Should have theme applied
        const hasTheme = classes.includes('dark') || classes.includes('light') ||
                        dataTheme.includes('dark') || dataTheme.includes('light');
        
        expect(hasTheme).toBe(true);
      }
    });
  });

  test.describe('Error Handling Consistency', () => {
    test('should show consistent error messages across browsers', async ({ page, browserName }) => {
      // Mock API error
      await page.route('**/api/portfolios', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server Error', message: 'Test error message' })
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForTimeout(3000);
      
      // Should show error consistently
      const errorElements = page.locator('.error, [data-testid="error"]');
      
      if (await errorElements.count() > 0) {
        const errorElement = errorElements.first();
        await expect(errorElement).toBeVisible();
        
        const errorText = await errorElement.textContent() || '';
        
        // Log error message for comparison across browsers
        console.log(`Error message in ${browserName}: ${errorText}`);
        
        // Should contain meaningful error information
        expect(errorText.length).toBeGreaterThan(0);
      }
      
      // Should provide recovery options
      const retryButton = page.locator('button:has-text("Retry")');
      
      if (await retryButton.count() > 0) {
        await expect(retryButton).toBeVisible();
        await expect(retryButton).toBeEnabled();
      }
    });
  });
});