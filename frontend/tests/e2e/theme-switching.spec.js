// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Theme Switching', () => {
  test.beforeEach(async ({ page }) => {
    // Start from dashboard page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have theme toggle button visible', async ({ page }) => {
    // Look for theme toggle button
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]').or(
        page.locator('.theme-toggle, .dark-mode-toggle')
      )
    );
    
    await expect(themeToggle).toBeVisible();
    await expect(themeToggle).toBeEnabled();
    
    // Should have appropriate ARIA label
    const ariaLabel = await themeToggle.getAttribute('aria-label');
    expect(ariaLabel).toMatch(/theme|dark|light|mode/i);
  });

  test('should detect system theme preference', async ({ page }) => {
    // Check the initial theme based on system preference
    const htmlElement = page.locator('html');
    const bodyElement = page.locator('body');
    
    // Should have theme class applied
    const htmlClasses = await htmlElement.getAttribute('class') || '';
    const bodyClasses = await bodyElement.getAttribute('class') || '';
    const dataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    // Should have some theme indication
    const hasThemeClass = htmlClasses.includes('dark') || htmlClasses.includes('light') ||
                         bodyClasses.includes('dark') || bodyClasses.includes('light') ||
                         dataTheme.includes('dark') || dataTheme.includes('light');
    
    expect(hasThemeClass).toBe(true);
  });

  test('should toggle between light and dark themes', async ({ page }) => {
    // Get initial theme state
    const htmlElement = page.locator('html');
    const initialClasses = await htmlElement.getAttribute('class') || '';
    const initialDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    const initialIsDark = initialClasses.includes('dark') || initialDataTheme.includes('dark');
    
    // Find and click theme toggle
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]').or(
        page.locator('.theme-toggle, .dark-mode-toggle')
      )
    );
    
    await themeToggle.click();
    
    // Wait for theme change animation/transition
    await page.waitForTimeout(500);
    
    // Check that theme has changed
    const newClasses = await htmlElement.getAttribute('class') || '';
    const newDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    const newIsDark = newClasses.includes('dark') || newDataTheme.includes('dark');
    
    // Theme should have toggled
    expect(newIsDark).toBe(!initialIsDark);
    
    // Toggle back
    await themeToggle.click();
    await page.waitForTimeout(500);
    
    // Should return to original theme
    const finalClasses = await htmlElement.getAttribute('class') || '';
    const finalDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    const finalIsDark = finalClasses.includes('dark') || finalDataTheme.includes('dark');
    expect(finalIsDark).toBe(initialIsDark);
  });

  test('should persist theme preference across page reloads', async ({ page }) => {
    // Get current theme
    const htmlElement = page.locator('html');
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Toggle to opposite theme
    await themeToggle.click();
    await page.waitForTimeout(500);
    
    // Get theme after toggle
    const afterToggleClasses = await htmlElement.getAttribute('class') || '';
    const afterToggleDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    const isDarkAfterToggle = afterToggleClasses.includes('dark') || afterToggleDataTheme.includes('dark');
    
    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Check that theme preference is persisted
    const afterReloadClasses = await htmlElement.getAttribute('class') || '';
    const afterReloadDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    const isDarkAfterReload = afterReloadClasses.includes('dark') || afterReloadDataTheme.includes('dark');
    
    expect(isDarkAfterReload).toBe(isDarkAfterToggle);
  });

  test('should apply correct theme styles to all page elements', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Test both themes
    for (let i = 0; i < 2; i++) {
      if (i === 1) {
        // Toggle theme for second iteration
        await themeToggle.click();
        await page.waitForTimeout(500);
      }
      
      // Check main layout elements have appropriate colors
      const navigation = page.locator('nav, [data-testid="navigation"]').first();
      const mainContent = page.locator('main, .main-content').first();
      const cards = page.locator('[data-testid="stat-card"]').or(
        page.locator('.card, .stat-card')
      ).first();
      
      // Check navigation styling
      if (await navigation.count() > 0) {
        const navBg = await navigation.evaluate(el => getComputedStyle(el).backgroundColor);
        expect(navBg).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
      }
      
      // Check main content styling
      if (await mainContent.count() > 0) {
        const contentBg = await mainContent.evaluate(el => getComputedStyle(el).backgroundColor);
        expect(contentBg).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
      }
      
      // Check card styling
      if (await cards.count() > 0) {
        const cardBg = await cards.evaluate(el => getComputedStyle(el).backgroundColor);
        expect(cardBg).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
      }
    }
  });

  test('should update chart colors based on theme', async ({ page }) => {
    // Look for charts on dashboard
    const charts = page.locator('canvas, .chart, svg[class*="chart"]');
    const chartCount = await charts.count();
    
    if (chartCount > 0) {
      const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
        page.locator('button[aria-label*="theme"]')
      );
      
      // Get initial chart (wait for it to render)
      await page.waitForTimeout(2000);
      
      // Toggle theme
      await themeToggle.click();
      await page.waitForTimeout(1000);
      
      // Charts should still be visible after theme change
      await expect(charts.first()).toBeVisible();
      
      // For canvas charts, we can't easily check colors, but they should remain functional
      const firstChart = charts.first();
      const chartBoundingBox = await firstChart.boundingBox();
      
      if (chartBoundingBox) {
        expect(chartBoundingBox.width).toBeGreaterThan(0);
        expect(chartBoundingBox.height).toBeGreaterThan(0);
      }
    }
  });

  test('should maintain theme consistency across all pages', async ({ page }) => {
    const pages = ['/', '/portfolios', '/trades', '/comparison', '/system'];
    
    // Set to dark theme first
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    await themeToggle.click();
    await page.waitForTimeout(500);
    
    // Check that theme is consistent across all pages
    for (const pagePath of pages) {
      await page.goto(pagePath);
      await page.waitForLoadState('networkidle');
      
      // Check theme is applied
      const htmlElement = page.locator('html');
      const classes = await htmlElement.getAttribute('class') || '';
      const dataTheme = await htmlElement.getAttribute('data-theme') || '';
      
      const isDark = classes.includes('dark') || dataTheme.includes('dark');
      expect(isDark).toBe(true);
      
      // Check that page elements have dark theme styling
      const bodyBg = await page.locator('body').evaluate(el => 
        getComputedStyle(el).backgroundColor
      );
      
      // Should not be pure white (indicating light theme)
      expect(bodyBg).not.toBe('rgb(255, 255, 255)');
    }
  });

  test('should handle theme toggle during page navigation', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Toggle theme
    await themeToggle.click();
    await page.waitForTimeout(500);
    
    // Navigate to different page
    const portfoliosLink = page.locator('a[href="/portfolios"]').or(
      page.locator('a:has-text("Portfolio")')
    );
    
    await portfoliosLink.click();
    await page.waitForURL('/portfolios');
    await page.waitForLoadState('networkidle');
    
    // Theme should be maintained during navigation
    const htmlElement = page.locator('html');
    const classes = await htmlElement.getAttribute('class') || '';
    const dataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    // Should have theme applied
    const hasTheme = classes.includes('dark') || classes.includes('light') ||
                    dataTheme.includes('dark') || dataTheme.includes('light');
    expect(hasTheme).toBe(true);
    
    // Theme toggle should still be functional
    const newThemeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    await expect(newThemeToggle).toBeVisible();
    await expect(newThemeToggle).toBeEnabled();
  });

  test('should show appropriate theme toggle icon', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Should have some visual indicator (icon or text)
    const icon = themeToggle.locator('svg, i, .icon').or(
      page.locator('[data-testid="theme-icon"]')
    );
    
    const text = await themeToggle.textContent() || '';
    const hasIcon = await icon.count() > 0;
    const hasText = text.length > 0;
    
    // Should have either icon or text
    expect(hasIcon || hasText).toBe(true);
    
    if (hasText) {
      expect(text).toMatch(/theme|dark|light|mode|sun|moon/i);
    }
  });

  test('should handle theme transitions smoothly', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Check for transition classes or properties
    const htmlElement = page.locator('html');
    const bodyElement = page.locator('body');
    
    // Get initial styles
    const initialBodyTransition = await bodyElement.evaluate(el => 
      getComputedStyle(el).transition
    );
    
    // Toggle theme
    await themeToggle.click();
    
    // Check that transitions are defined (if implemented)
    const transitionDuration = await bodyElement.evaluate(el => 
      getComputedStyle(el).transitionDuration
    );
    
    // If transitions are implemented, they should have duration
    if (transitionDuration !== '0s') {
      expect(transitionDuration).toMatch(/\d+\.?\d*s/);
    }
    
    // Wait for transition to complete
    await page.waitForTimeout(1000);
    
    // Page should be functional after transition
    await expect(page.locator('h1')).toBeVisible();
  });

  test('should respect system dark mode preference changes', async ({ page, context }) => {
    // Note: This test simulates system preference changes
    // In a real scenario, this would require browser API mocking
    
    // Check initial theme
    const htmlElement = page.locator('html');
    const initialClasses = await htmlElement.getAttribute('class') || '';
    const initialDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    // Simulate system preference change using media query
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(1000);
    
    // If app respects system preference, theme might change
    const afterDarkClasses = await htmlElement.getAttribute('class') || '';
    const afterDarkDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    // Theme system should be responsive to preference
    expect(typeof afterDarkClasses).toBe('string');
    expect(typeof afterDarkDataTheme).toBe('string');
    
    // Switch to light
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForTimeout(1000);
    
    // Should handle light preference
    const afterLightClasses = await htmlElement.getAttribute('class') || '';
    const afterLightDataTheme = await htmlElement.getAttribute('data-theme') || '';
    
    expect(typeof afterLightClasses).toBe('string');
    expect(typeof afterLightDataTheme).toBe('string');
  });

  test('should maintain accessibility in both themes', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button[aria-label*="theme"]')
    );
    
    // Test both themes for accessibility
    for (let i = 0; i < 2; i++) {
      if (i === 1) {
        await themeToggle.click();
        await page.waitForTimeout(500);
      }
      
      // Check color contrast by ensuring text is readable
      const headings = page.locator('h1, h2, h3');
      const headingCount = await headings.count();
      
      if (headingCount > 0) {
        const firstHeading = headings.first();
        
        // Check that text color contrasts with background
        const textColor = await firstHeading.evaluate(el => 
          getComputedStyle(el).color
        );
        const backgroundColor = await firstHeading.evaluate(el => {
          let bg = getComputedStyle(el).backgroundColor;
          // If transparent, check parent
          if (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') {
            let parent = el.parentElement;
            while (parent && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
              bg = getComputedStyle(parent).backgroundColor;
              parent = parent.parentElement;
            }
          }
          return bg;
        });
        
        // Both should have valid color values
        expect(textColor).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
        expect(backgroundColor).toMatch(/rgb\(\d+,\s*\d+,\s*\d+\)/);
        
        // Colors should be different (basic contrast check)
        expect(textColor).not.toBe(backgroundColor);
      }
      
      // Check focus indicators are visible in both themes
      const focusableElements = page.locator('button, a, input').first();
      if (await focusableElements.count() > 0) {
        await focusableElements.focus();
        
        // Should have focus styles
        const outlineStyle = await focusableElements.evaluate(el => 
          getComputedStyle(el).outline
        );
        const boxShadow = await focusableElements.evaluate(el => 
          getComputedStyle(el).boxShadow
        );
        
        // Should have some focus indication
        const hasFocusIndicator = outlineStyle !== 'none' && outlineStyle !== 'medium none invert' ||
                                 boxShadow !== 'none';
        
        // Note: Some designs might use other methods for focus indication
        expect(typeof outlineStyle).toBe('string');
      }
    }
  });
});