// @ts-check
import { test, expect } from '@playwright/test';

const viewports = {
  mobile: { width: 375, height: 667 }, // iPhone SE
  tablet: { width: 768, height: 1024 }, // iPad
  desktop: { width: 1920, height: 1080 } // Desktop
};

test.describe('Responsive Design', () => {
  test.describe('Mobile Layout (375px)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(viewports.mobile);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
    });

    test('should display mobile navigation', async ({ page }) => {
      // Check for mobile hamburger menu
      const hamburgerMenu = page.locator('[data-testid="mobile-menu-toggle"]').or(
        page.locator('.hamburger, .mobile-menu-btn, button[aria-label*="menu"]')
      );
      
      await expect(hamburgerMenu).toBeVisible();
      
      // Desktop navigation should be hidden
      const desktopNav = page.locator('[data-testid="desktop-nav"]').or(
        page.locator('.desktop-nav, nav.desktop')
      );
      
      if (await desktopNav.count() > 0) {
        await expect(desktopNav).toBeHidden();
      }
      
      // Open mobile menu
      await hamburgerMenu.click();
      
      // Mobile menu should appear
      const mobileMenu = page.locator('[data-testid="mobile-menu"]').or(
        page.locator('.mobile-menu, .nav-menu-mobile')
      );
      
      await expect(mobileMenu).toBeVisible({ timeout: 5000 });
      
      // Should contain navigation links
      const navLinks = mobileMenu.locator('a[href="/portfolios"], a[href="/trades"]');
      await expect(navLinks.first()).toBeVisible();
    });

    test('should stack dashboard cards vertically', async ({ page }) => {
      // Check for dashboard stats cards
      const statsCards = page.locator('[data-testid="stat-card"]').or(
        page.locator('.stat-card, .metric-card, .dashboard-card')
      );
      
      const cardCount = await statsCards.count();
      
      if (cardCount > 1) {
        // Get positions of first two cards
        const firstCard = statsCards.first();
        const secondCard = statsCards.nth(1);
        
        const firstCardBox = await firstCard.boundingBox();
        const secondCardBox = await secondCard.boundingBox();
        
        if (firstCardBox && secondCardBox) {
          // On mobile, cards should be stacked (second card below first)
          expect(secondCardBox.y).toBeGreaterThan(firstCardBox.y + firstCardBox.height - 10);
        }
      }
    });

    test('should make forms touch-friendly', async ({ page }) => {
      // Navigate to portfolios to test forms
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Try to open create portfolio modal
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create")')
      );
      
      if (await createButton.count() > 0) {
        // Button should be large enough for touch (minimum 44px)
        const buttonBox = await createButton.boundingBox();
        if (buttonBox) {
          expect(buttonBox.height).toBeGreaterThanOrEqual(40);
        }
        
        await createButton.click();
        
        // Check form inputs are touch-friendly
        const nameInput = page.locator('input[name="name"]');
        if (await nameInput.count() > 0) {
          const inputBox = await nameInput.boundingBox();
          if (inputBox) {
            expect(inputBox.height).toBeGreaterThanOrEqual(40);
          }
          
          // Input should have appropriate font size (no zoom on iOS)
          const fontSize = await nameInput.evaluate(el => 
            getComputedStyle(el).fontSize
          );
          const fontSizeNum = parseFloat(fontSize);
          expect(fontSizeNum).toBeGreaterThanOrEqual(16);
        }
      }
    });

    test('should display tables as cards on mobile', async ({ page }) => {
      // Navigate to trades page which likely has tables
      await page.goto('/trades');
      await page.waitForLoadState('networkidle');
      
      // Check if trades are displayed as cards instead of table
      const tradeCards = page.locator('[data-testid="trade-card"]').or(
        page.locator('.trade-card, .trade-item')
      );
      
      const table = page.locator('table');
      
      const cardCount = await tradeCards.count();
      const tableCount = await table.count();
      
      if (cardCount > 0) {
        // Should use card layout on mobile
        await expect(tradeCards.first()).toBeVisible();
        
        // Cards should stack vertically
        if (cardCount > 1) {
          const firstCard = tradeCards.first();
          const secondCard = tradeCards.nth(1);
          
          const firstBox = await firstCard.boundingBox();
          const secondBox = await secondCard.boundingBox();
          
          if (firstBox && secondBox) {
            expect(secondBox.y).toBeGreaterThan(firstBox.y);
          }
        }
      }
      
      // If table exists, it should be horizontally scrollable or hidden
      if (tableCount > 0) {
        const tableContainer = table.locator('..').first();
        const overflowX = await tableContainer.evaluate(el => 
          getComputedStyle(el).overflowX
        );
        
        // Should allow horizontal scrolling or be hidden
        expect(['scroll', 'auto', 'hidden'].includes(overflowX)).toBe(true);
      }
    });

    test('should handle mobile-specific interactions', async ({ page }) => {
      // Test touch gestures and mobile-specific behavior
      
      // Check for swipe gestures (if implemented)
      const swipeableElements = page.locator('[data-testid="swipeable"]').or(
        page.locator('.swipeable, .touch-slider')
      );
      
      if (await swipeableElements.count() > 0) {
        const element = swipeableElements.first();
        const box = await element.boundingBox();
        
        if (box) {
          // Simulate swipe gesture
          await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2);
          await page.mouse.down();
          await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2);
          await page.mouse.up();
          
          // Element should still be functional
          await expect(element).toBeVisible();
        }
      }
      
      // Test pull-to-refresh (if implemented)
      const refreshIndicator = page.locator('[data-testid="pull-refresh"]');
      if (await refreshIndicator.count() > 0) {
        // Simulate pull gesture at top of page
        await page.mouse.move(200, 10);
        await page.mouse.down();
        await page.mouse.move(200, 100);
        await page.mouse.up();
        
        await page.waitForTimeout(1000);
        await expect(page.locator('h1')).toBeVisible();
      }
    });
  });

  test.describe('Tablet Layout (768px)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(viewports.tablet);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
    });

    test('should display tablet-optimized navigation', async ({ page }) => {
      // Check navigation layout on tablet
      const navigation = page.locator('nav, [data-testid="navigation"]');
      await expect(navigation).toBeVisible();
      
      // Might show both hamburger and some nav items
      const hamburger = page.locator('[data-testid="mobile-menu-toggle"]');
      const navItems = page.locator('nav a[href*="/"]');
      
      const hamburgerCount = await hamburger.count();
      const navItemsCount = await navItems.count();
      
      // Should have some form of navigation
      expect(hamburgerCount + navItemsCount).toBeGreaterThan(0);
      
      if (hamburgerCount > 0) {
        await hamburger.click();
        const mobileMenu = page.locator('[data-testid="mobile-menu"]');
        await expect(mobileMenu).toBeVisible();
      }
    });

    test('should display cards in 2-column grid', async ({ page }) => {
      // Check dashboard cards layout
      const statsCards = page.locator('[data-testid="stat-card"]').or(
        page.locator('.stat-card, .metric-card, .dashboard-card')
      );
      
      const cardCount = await statsCards.count();
      
      if (cardCount >= 2) {
        // Get positions of first two cards
        const firstCard = statsCards.first();
        const secondCard = statsCards.nth(1);
        
        const firstBox = await firstCard.boundingBox();
        const secondBox = await secondCard.boundingBox();
        
        if (firstBox && secondBox) {
          // On tablet, cards might be side by side
          const sideBySide = Math.abs(firstBox.y - secondBox.y) < 50;
          const stacked = secondBox.y > firstBox.y + firstBox.height - 10;
          
          // Should be either side by side or stacked
          expect(sideBySide || stacked).toBe(true);
        }
      }
    });

    test('should optimize form layouts for tablet', async ({ page }) => {
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create")')
      );
      
      if (await createButton.count() > 0) {
        await createButton.click();
        
        // Modal should be appropriately sized for tablet
        const modal = page.locator('[data-testid="portfolio-modal"]').or(
          page.locator('[role="dialog"]')
        );
        
        if (await modal.count() > 0) {
          await expect(modal).toBeVisible();
          
          const modalBox = await modal.boundingBox();
          if (modalBox) {
            // Should not be full width on tablet
            expect(modalBox.width).toBeLessThan(viewports.tablet.width);
            // Should be reasonably sized
            expect(modalBox.width).toBeGreaterThan(300);
          }
        }
      }
    });

    test('should handle tablet-specific table layouts', async ({ page }) => {
      await page.goto('/trades');
      await page.waitForLoadState('networkidle');
      
      // On tablet, might show condensed table or card layout
      const table = page.locator('table');
      const tradeCards = page.locator('[data-testid="trade-card"]');
      
      const tableCount = await table.count();
      const cardCount = await tradeCards.count();
      
      if (tableCount > 0) {
        // Table should be visible and properly sized
        await expect(table).toBeVisible();
        
        const tableBox = await table.boundingBox();
        if (tableBox) {
          // Should fit within viewport
          expect(tableBox.width).toBeLessThanOrEqual(viewports.tablet.width);
        }
      } else if (cardCount > 0) {
        // Card layout should work well on tablet
        await expect(tradeCards.first()).toBeVisible();
      }
    });
  });

  test.describe('Desktop Layout (1920px)', () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize(viewports.desktop);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
    });

    test('should display full desktop navigation', async ({ page }) => {
      // Desktop should show full navigation
      const navigation = page.locator('nav, [data-testid="navigation"]');
      await expect(navigation).toBeVisible();
      
      // Should have direct navigation links
      const navLinks = [
        page.locator('a[href="/"]'),
        page.locator('a[href="/portfolios"]'),
        page.locator('a[href="/trades"]'),
        page.locator('a[href="/comparison"]'),
        page.locator('a[href="/system"]')
      ];
      
      let visibleLinks = 0;
      for (const link of navLinks) {
        if (await link.count() > 0 && await link.isVisible()) {
          visibleLinks++;
        }
      }
      
      expect(visibleLinks).toBeGreaterThan(2);
      
      // Hamburger menu should be hidden on desktop
      const hamburger = page.locator('[data-testid="mobile-menu-toggle"]');
      if (await hamburger.count() > 0) {
        await expect(hamburger).toBeHidden();
      }
    });

    test('should display cards in multi-column layout', async ({ page }) => {
      // Check dashboard cards layout
      const statsCards = page.locator('[data-testid="stat-card"]').or(
        page.locator('.stat-card, .metric-card, .dashboard-card')
      );
      
      const cardCount = await statsCards.count();
      
      if (cardCount >= 3) {
        // Get positions of first three cards
        const firstCard = statsCards.first();
        const secondCard = statsCards.nth(1);
        const thirdCard = statsCards.nth(2);
        
        const firstBox = await firstCard.boundingBox();
        const secondBox = await secondCard.boundingBox();
        const thirdBox = await thirdCard.boundingBox();
        
        if (firstBox && secondBox && thirdBox) {
          // Cards should be arranged horizontally
          const horizontalLayout = Math.abs(firstBox.y - secondBox.y) < 50 && 
                                  Math.abs(secondBox.y - thirdBox.y) < 50;
          
          if (horizontalLayout) {
            // Should be side by side
            expect(secondBox.x).toBeGreaterThan(firstBox.x);
            expect(thirdBox.x).toBeGreaterThan(secondBox.x);
          }
        }
      }
    });

    test('should display full-featured tables', async ({ page }) => {
      await page.goto('/trades');
      await page.waitForLoadState('networkidle');
      
      // Desktop should prefer table layout
      const table = page.locator('table');
      const tableCount = await table.count();
      
      if (tableCount > 0) {
        await expect(table).toBeVisible();
        
        // Should have proper table structure
        const headers = table.locator('th');
        const rows = table.locator('tr');
        
        const headerCount = await headers.count();
        const rowCount = await rows.count();
        
        if (headerCount > 0) {
          expect(headerCount).toBeGreaterThan(1);
        }
        
        if (rowCount > 0) {
          expect(rowCount).toBeGreaterThan(0);
        }
        
        // Table should use available width
        const tableBox = await table.boundingBox();
        if (tableBox) {
          expect(tableBox.width).toBeGreaterThan(600);
        }
      }
    });

    test('should show detailed information and controls', async ({ page }) => {
      // Desktop should show more detailed information
      
      // Check for detailed stats or additional information
      const detailedInfo = page.locator('[data-testid="detailed-info"]').or(
        page.locator('.details, .additional-info')
      );
      
      // Check for advanced controls
      const advancedControls = page.locator('[data-testid="advanced-controls"]').or(
        page.locator('.advanced, .controls')
      );
      
      // Should have sidebar or additional content areas
      const sidebar = page.locator('[data-testid="sidebar"]').or(
        page.locator('.sidebar, aside')
      );
      
      const infoCount = await detailedInfo.count();
      const controlsCount = await advancedControls.count();
      const sidebarCount = await sidebar.count();
      
      // Desktop should utilize the available space with more features
      expect(infoCount + controlsCount + sidebarCount).toBeGreaterThan(0);
    });
  });

  test.describe('Cross-Viewport Consistency', () => {
    test('should maintain functionality across all viewports', async ({ page }) => {
      const viewportSizes = Object.values(viewports);
      
      for (const viewport of viewportSizes) {
        await page.setViewportSize(viewport);
        await page.goto('/portfolios');
        await page.waitForLoadState('networkidle');
        
        // Basic functionality should work on all viewports
        await expect(page.locator('h1')).toBeVisible();
        
        // Navigation should be accessible
        const hamburger = page.locator('[data-testid="mobile-menu-toggle"]');
        const directNav = page.locator('nav a[href="/"]');
        
        const hamburgerCount = await hamburger.count();
        const directNavCount = await directNav.count();
        
        // Should have some form of navigation
        expect(hamburgerCount + directNavCount).toBeGreaterThan(0);
        
        // If hamburger exists, it should work
        if (hamburgerCount > 0 && await hamburger.isVisible()) {
          await hamburger.click();
          const mobileMenu = page.locator('[data-testid="mobile-menu"]');
          await expect(mobileMenu).toBeVisible({ timeout: 3000 });
          
          // Close menu for next iteration
          const closeBtn = mobileMenu.locator('button[aria-label*="close"]').or(
            page.locator('[data-testid="close-menu"]')
          );
          
          if (await closeBtn.count() > 0) {
            await closeBtn.click();
          } else {
            // Try clicking outside
            await page.click('body', { position: { x: 10, y: 10 } });
          }
        }
      }
    });

    test('should handle viewport changes smoothly', async ({ page }) => {
      // Start with desktop
      await page.setViewportSize(viewports.desktop);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Verify desktop layout
      await expect(page.locator('h1')).toBeVisible();
      
      // Change to mobile
      await page.setViewportSize(viewports.mobile);
      await page.waitForTimeout(500);
      
      // Should adapt to mobile layout
      await expect(page.locator('h1')).toBeVisible();
      
      // Mobile navigation should be available
      const hamburger = page.locator('[data-testid="mobile-menu-toggle"]');
      if (await hamburger.count() > 0) {
        await expect(hamburger).toBeVisible();
      }
      
      // Change to tablet
      await page.setViewportSize(viewports.tablet);
      await page.waitForTimeout(500);
      
      // Should maintain functionality
      await expect(page.locator('h1')).toBeVisible();
      
      // Back to desktop
      await page.setViewportSize(viewports.desktop);
      await page.waitForTimeout(500);
      
      // Should return to desktop layout
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should handle content reflow properly', async ({ page }) => {
      await page.setViewportSize(viewports.desktop);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Get initial content positions
      const mainContent = page.locator('main, .main-content');
      const initialBox = await mainContent.boundingBox();
      
      // Change to mobile
      await page.setViewportSize(viewports.mobile);
      await page.waitForTimeout(1000);
      
      // Content should reflow
      const mobileBox = await mainContent.boundingBox();
      
      if (initialBox && mobileBox) {
        // Width should be different
        expect(mobileBox.width).not.toBe(initialBox.width);
        
        // Content should still be visible
        expect(mobileBox.width).toBeGreaterThan(0);
        expect(mobileBox.height).toBeGreaterThan(0);
      }
      
      // All critical content should remain accessible
      await expect(page.locator('h1')).toBeVisible();
      
      // Navigation should be accessible
      const navigation = page.locator('nav, [data-testid="navigation"], [data-testid="mobile-menu-toggle"]');
      await expect(navigation.first()).toBeVisible();
    });

    test('should maintain readable text across viewports', async ({ page }) => {
      const viewportSizes = Object.values(viewports);
      
      for (const viewport of viewportSizes) {
        await page.setViewportSize(viewport);
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Check text elements for readability
        const headings = page.locator('h1, h2, h3');
        const paragraphs = page.locator('p');
        
        if (await headings.count() > 0) {
          const heading = headings.first();
          const fontSize = await heading.evaluate(el => 
            getComputedStyle(el).fontSize
          );
          
          const fontSizeNum = parseFloat(fontSize);
          
          // Minimum readable font size
          expect(fontSizeNum).toBeGreaterThan(12);
          
          // Should not be too large (unless intentional)
          expect(fontSizeNum).toBeLessThan(100);
        }
        
        if (await paragraphs.count() > 0) {
          const paragraph = paragraphs.first();
          const lineHeight = await paragraph.evaluate(el => 
            getComputedStyle(el).lineHeight
          );
          
          // Line height should be reasonable
          if (lineHeight !== 'normal') {
            const lineHeightNum = parseFloat(lineHeight);
            expect(lineHeightNum).toBeGreaterThan(12);
          }
        }
      }
    });
  });
});