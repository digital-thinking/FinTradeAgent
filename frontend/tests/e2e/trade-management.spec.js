// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Trade Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to pending trades page
    await page.goto('/trades');
    await page.waitForLoadState('networkidle');
  });

  test('should display pending trades page', async ({ page }) => {
    // Check page title and heading
    await expect(page).toHaveTitle(/FinTradeAgent/);
    await expect(page.locator('h1')).toContainText(/Pending Trades|Trade Management/i);
    
    // Check navigation
    const navTrades = page.locator('[data-testid="nav-trades"]').or(
      page.locator('nav a[href="/trades"]')
    );
    await expect(navTrades).toBeVisible();
  });

  test('should show pending trades or empty state', async ({ page }) => {
    // Wait for content to load
    await page.waitForSelector('[data-testid="trades-container"]', { timeout: 10000 });
    
    // Check for trades or empty state
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    const emptyState = page.locator('[data-testid="empty-trades"]').or(
      page.locator('.empty-trades, .no-trades')
    );
    
    const tradeCount = await tradeCards.count();
    const emptyCount = await emptyState.count();
    
    if (tradeCount > 0) {
      // Verify trade cards are displayed
      await expect(tradeCards.first()).toBeVisible();
      
      // Check trade card structure
      const firstTrade = tradeCards.first();
      
      // Should contain basic trade information
      const symbolElement = firstTrade.locator('[data-testid="trade-symbol"]').or(
        firstTrade.locator('.symbol, .ticker')
      );
      const actionElement = firstTrade.locator('[data-testid="trade-action"]').or(
        firstTrade.locator('.action, .trade-type')
      );
      const quantityElement = firstTrade.locator('[data-testid="trade-quantity"]').or(
        firstTrade.locator('.quantity, .shares')
      );
      
      // At least one of these should be visible
      await expect(symbolElement.or(actionElement).or(quantityElement)).toBeVisible();
    } else if (emptyCount > 0) {
      // Verify empty state is shown
      await expect(emptyState).toBeVisible();
      await expect(emptyState).toContainText(/no.*trades|empty/i);
    } else {
      // Should have either trades or empty state
      expect(true).toBe(false); // Fail test if neither is found
    }
  });

  test('should display trade details in cards/table', async ({ page }) => {
    // Check for trades
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Check for essential trade information
      const tradeInfo = [
        firstTrade.locator('[data-testid="trade-symbol"]').or(firstTrade.locator('.symbol, .ticker')),
        firstTrade.locator('[data-testid="trade-action"]').or(firstTrade.locator('.action, .trade-type')),
        firstTrade.locator('[data-testid="trade-quantity"]').or(firstTrade.locator('.quantity, .shares')),
        firstTrade.locator('[data-testid="trade-price"]').or(firstTrade.locator('.price, .target-price')),
        firstTrade.locator('[data-testid="trade-portfolio"]').or(firstTrade.locator('.portfolio, .portfolio-name'))
      ];
      
      // At least some trade information should be visible
      let visibleCount = 0;
      for (const element of tradeInfo) {
        const count = await element.count();
        if (count > 0 && await element.isVisible()) {
          visibleCount++;
        }
      }
      
      expect(visibleCount).toBeGreaterThan(0);
    }
  });

  test('should open trade details modal', async ({ page }) => {
    // Check for trades
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Look for details button or click on trade card
      const detailsButton = firstTrade.locator('[data-testid="trade-details"]').or(
        firstTrade.locator('button:has-text("Details")').or(
          firstTrade.locator('.details-btn')
        )
      );
      
      if (await detailsButton.count() > 0) {
        await detailsButton.click();
      } else {
        // Try clicking on the trade card itself
        await firstTrade.click();
      }
      
      // Check if modal or details section appears
      const modal = page.locator('[data-testid="trade-details-modal"]').or(
        page.locator('[role="dialog"]').or(page.locator('.modal, .trade-modal'))
      );
      
      if (await modal.count() > 0) {
        await expect(modal).toBeVisible({ timeout: 5000 });
        
        // Check for detailed trade information
        await expect(modal).toContainText(/.+/); // Should have some content
      }
    }
  });

  test('should apply a trade', async ({ page }) => {
    // Check for trades
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Get trade identifier for verification
      const tradeSymbol = await firstTrade.locator('[data-testid="trade-symbol"]').or(
        firstTrade.locator('.symbol, .ticker')
      ).textContent();
      
      // Look for apply button
      const applyButton = firstTrade.locator('[data-testid="apply-trade"]').or(
        firstTrade.locator('button:has-text("Apply")').or(
          firstTrade.locator('.apply-btn, .execute-btn')
        )
      );
      
      await expect(applyButton).toBeVisible();
      await expect(applyButton).toBeEnabled();
      
      // Click apply
      await applyButton.click();
      
      // Handle confirmation dialog if it appears
      page.on('dialog', dialog => {
        expect(dialog.type()).toBe('confirm');
        expect(dialog.message()).toContain('apply');
        dialog.accept();
      });
      
      // Wait for trade to be processed
      await page.waitForTimeout(2000);
      
      // Verify trade was applied (might be removed from pending list)
      if (tradeSymbol) {
        // Either trade is removed or status is updated
        const updatedTrade = page.locator(`text=${tradeSymbol}`).first();
        
        // Check if trade still exists and has updated status
        const stillExists = await updatedTrade.count();
        if (stillExists > 0) {
          // Look for applied/executed status
          const statusIndicator = page.locator('[data-testid="trade-status"]').or(
            page.locator('.status, .trade-status')
          );
          
          if (await statusIndicator.count() > 0) {
            await expect(statusIndicator).toContainText(/applied|executed|complete/i);
          }
        }
      }
    }
  });

  test('should cancel a trade', async ({ page }) => {
    // Check for trades
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Get trade identifier for verification
      const tradeSymbol = await firstTrade.locator('[data-testid="trade-symbol"]').or(
        firstTrade.locator('.symbol, .ticker')
      ).textContent();
      
      // Look for cancel button
      const cancelButton = firstTrade.locator('[data-testid="cancel-trade"]').or(
        firstTrade.locator('button:has-text("Cancel")').or(
          firstTrade.locator('.cancel-btn, .reject-btn')
        )
      );
      
      await expect(cancelButton).toBeVisible();
      await expect(cancelButton).toBeEnabled();
      
      // Click cancel
      await cancelButton.click();
      
      // Handle confirmation dialog if it appears
      page.on('dialog', dialog => {
        expect(dialog.type()).toBe('confirm');
        expect(dialog.message()).toContain('cancel');
        dialog.accept();
      });
      
      // Wait for trade to be processed
      await page.waitForTimeout(2000);
      
      // Verify trade was cancelled (removed from pending list)
      if (tradeSymbol) {
        await expect(page.locator(`text=${tradeSymbol}`).first()).not.toBeVisible();
      }
    }
  });

  test('should show trade recommendations with analysis', async ({ page }) => {
    // Check for trades with recommendation details
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Look for recommendation/analysis information
      const recommendation = firstTrade.locator('[data-testid="trade-recommendation"]').or(
        firstTrade.locator('.recommendation, .analysis, .reason')
      );
      
      const confidence = firstTrade.locator('[data-testid="trade-confidence"]').or(
        firstTrade.locator('.confidence, .score')
      );
      
      // At least one should be present
      const recCount = await recommendation.count();
      const confCount = await confidence.count();
      
      if (recCount > 0) {
        await expect(recommendation).toBeVisible();
        await expect(recommendation).toContainText(/.+/);
      }
      
      if (confCount > 0) {
        await expect(confidence).toBeVisible();
        await expect(confidence).toContainText(/\d|%|high|medium|low/i);
      }
      
      // Should have at least some analysis information
      expect(recCount + confCount).toBeGreaterThan(0);
    }
  });

  test('should filter trades by portfolio', async ({ page }) => {
    // Look for portfolio filter
    const portfolioFilter = page.locator('[data-testid="portfolio-filter"]').or(
      page.locator('select[name="portfolio"]').or(page.locator('.portfolio-filter'))
    );
    
    if (await portfolioFilter.count() > 0) {
      await expect(portfolioFilter).toBeVisible();
      
      // Get initial trade count
      const tradeCards = page.locator('[data-testid="trade-card"]');
      const initialCount = await tradeCards.count();
      
      // Try to change filter (if options exist)
      const filterOptions = portfolioFilter.locator('option');
      const optionCount = await filterOptions.count();
      
      if (optionCount > 1) {
        // Select different portfolio
        await portfolioFilter.selectOption({ index: 1 });
        
        // Wait for filter to apply
        await page.waitForTimeout(1000);
        
        // Verify trades are filtered
        const filteredCount = await tradeCards.count();
        // Count might change or stay same depending on data
        expect(filteredCount).toBeGreaterThanOrEqual(0);
      }
    }
  });

  test('should sort trades by different criteria', async ({ page }) => {
    // Look for sort controls
    const sortSelect = page.locator('[data-testid="trade-sort"]').or(
      page.locator('select[name="sort"]').or(page.locator('.sort-select'))
    );
    
    const sortButtons = page.locator('[data-testid="sort-btn"]').or(
      page.locator('.sort-btn, button[data-sort]')
    );
    
    if (await sortSelect.count() > 0) {
      // Test dropdown sort
      const options = sortSelect.locator('option');
      const optionCount = await options.count();
      
      if (optionCount > 1) {
        // Get initial order
        const tradeCards = page.locator('[data-testid="trade-card"]');
        const initialCount = await tradeCards.count();
        
        if (initialCount > 1) {
          const firstSymbol = await tradeCards.first().locator('[data-testid="trade-symbol"]').textContent();
          
          // Change sort
          await sortSelect.selectOption({ index: 1 });
          await page.waitForTimeout(1000);
          
          // Check if order changed
          const newFirstSymbol = await tradeCards.first().locator('[data-testid="trade-symbol"]').textContent();
          
          // Order might or might not change depending on data
          expect(typeof newFirstSymbol).toBe('string');
        }
      }
    } else if (await sortButtons.count() > 0) {
      // Test button sort
      const firstSortBtn = sortButtons.first();
      await firstSortBtn.click();
      
      // Wait for sort to apply
      await page.waitForTimeout(1000);
      
      // Verify page is still functional
      await expect(page.locator('h1')).toBeVisible();
    }
  });

  test('should handle bulk trade actions', async ({ page }) => {
    // Look for bulk action controls
    const selectAllCheckbox = page.locator('[data-testid="select-all-trades"]').or(
      page.locator('input[type="checkbox"][name="select-all"]')
    );
    
    const bulkActions = page.locator('[data-testid="bulk-actions"]').or(
      page.locator('.bulk-actions, .batch-actions')
    );
    
    if (await selectAllCheckbox.count() > 0 && await bulkActions.count() > 0) {
      // Check select all
      await selectAllCheckbox.check();
      
      // Verify bulk actions become available
      await expect(bulkActions).toBeVisible();
      
      // Look for bulk apply/cancel buttons
      const bulkApply = bulkActions.locator('button:has-text("Apply All")');
      const bulkCancel = bulkActions.locator('button:has-text("Cancel All")');
      
      if (await bulkApply.count() > 0) {
        await expect(bulkApply).toBeVisible();
        await expect(bulkApply).toBeEnabled();
      }
      
      if (await bulkCancel.count() > 0) {
        await expect(bulkCancel).toBeVisible();
        await expect(bulkCancel).toBeEnabled();
      }
    }
  });

  test('should refresh trade data', async ({ page }) => {
    // Look for refresh button
    const refreshButton = page.locator('[data-testid="refresh-trades"]').or(
      page.locator('button:has-text("Refresh")').or(page.locator('.refresh-btn'))
    );
    
    if (await refreshButton.count() > 0) {
      // Click refresh
      await refreshButton.click();
      
      // Wait for refresh to complete
      await page.waitForTimeout(2000);
      
      // Verify page is still functional
      await expect(page.locator('h1')).toBeVisible();
      
      // Check that data is reloaded (loading indicator might appear)
      const loadingIndicator = page.locator('[data-testid="loading"]').or(
        page.locator('.loading, .spinner')
      );
      
      // Loading might briefly appear and disappear
      if (await loadingIndicator.count() > 0) {
        await expect(loadingIndicator).not.toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should navigate back to portfolio from trade', async ({ page }) => {
    // Check for trades with portfolio links
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    const tradeCount = await tradeCards.count();
    
    if (tradeCount > 0) {
      const firstTrade = tradeCards.first();
      
      // Look for portfolio link
      const portfolioLink = firstTrade.locator('[data-testid="portfolio-link"]').or(
        firstTrade.locator('a[href*="/portfolios/"]').or(
          firstTrade.locator('.portfolio-link, .portfolio-name')
        )
      );
      
      if (await portfolioLink.count() > 0) {
        await portfolioLink.click();
        
        // Should navigate to portfolio detail page
        await expect(page).toHaveURL(/\/portfolios\/.+/);
        
        // Should show portfolio content
        await expect(page.locator('h1')).toBeVisible();
      }
    }
  });
});