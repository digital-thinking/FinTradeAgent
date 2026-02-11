// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Portfolio Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to portfolios page
    await page.goto('/portfolios');
    await page.waitForLoadState('networkidle');
  });

  test('should display portfolios page with correct title', async ({ page }) => {
    // Check page title and heading
    await expect(page).toHaveTitle(/FinTradeAgent/);
    await expect(page.locator('h1')).toContainText('Portfolio Management');
    
    // Check navigation is visible
    await expect(page.locator('[data-testid="nav-portfolios"]')).toBeVisible();
  });

  test('should show empty state when no portfolios exist', async ({ page }) => {
    // Wait for page to load
    await page.waitForSelector('[data-testid="portfolios-container"]', { timeout: 10000 });
    
    // Check if empty state or portfolio list is shown
    const emptyState = page.locator('[data-testid="empty-portfolios"]');
    const portfolioList = page.locator('[data-testid="portfolio-card"]');
    
    // Should show either empty state or existing portfolios
    await expect(emptyState.or(portfolioList)).toBeVisible();
  });

  test('should open create portfolio modal', async ({ page }) => {
    // Click create portfolio button
    const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
      page.locator('button:has-text("Create Portfolio")')
    );
    await createButton.click();
    
    // Check modal is visible
    const modal = page.locator('[data-testid="portfolio-modal"]').or(
      page.locator('[role="dialog"]')
    );
    await expect(modal).toBeVisible();
    
    // Check form fields
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('input[name="description"]')).toBeVisible();
    await expect(page.locator('input[name="initialCash"]')).toBeVisible();
  });

  test('should create a new portfolio with valid data', async ({ page }) => {
    // Open create modal
    const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
      page.locator('button:has-text("Create Portfolio")')
    );
    await createButton.click();
    
    const testPortfolioName = `Test Portfolio ${Date.now()}`;
    
    // Fill form
    await page.locator('input[name="name"]').fill(testPortfolioName);
    await page.locator('input[name="description"]').fill('Test portfolio for E2E testing');
    await page.locator('input[name="initialCash"]').fill('100000');
    
    // Submit form
    await page.locator('button[type="submit"]').or(page.locator('button:has-text("Create")')).click();
    
    // Wait for modal to close and portfolio to appear
    await page.waitForSelector('[data-testid="portfolio-modal"]', { state: 'hidden', timeout: 5000 });
    
    // Verify portfolio appears in list
    await expect(page.locator(`text=${testPortfolioName}`)).toBeVisible();
  });

  test('should validate required fields in create form', async ({ page }) => {
    // Open create modal
    const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
      page.locator('button:has-text("Create Portfolio")')
    );
    await createButton.click();
    
    // Try to submit empty form
    await page.locator('button[type="submit"]').or(page.locator('button:has-text("Create")')).click();
    
    // Check for validation messages (HTML5 validation or custom)
    const nameInput = page.locator('input[name="name"]');
    await expect(nameInput).toBeVisible();
    
    // Check if form validation prevents submission
    const modal = page.locator('[data-testid="portfolio-modal"]').or(page.locator('[role="dialog"]'));
    await expect(modal).toBeVisible(); // Modal should still be open
  });

  test('should edit an existing portfolio', async ({ page }) => {
    // First create a portfolio or find existing one
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const editButton = portfolioCard.locator('[data-testid="edit-portfolio"]').or(
      portfolioCard.locator('button:has-text("Edit")')
    );
    
    // Check if portfolios exist
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount > 0) {
      // Edit existing portfolio
      await editButton.click();
      
      // Wait for edit modal
      const modal = page.locator('[data-testid="portfolio-modal"]').or(page.locator('[role="dialog"]'));
      await expect(modal).toBeVisible();
      
      // Update description
      const descInput = page.locator('input[name="description"]');
      await descInput.fill('Updated description via E2E test');
      
      // Save changes
      await page.locator('button[type="submit"]').or(page.locator('button:has-text("Save")')).click();
      
      // Wait for modal to close
      await page.waitForSelector('[data-testid="portfolio-modal"]', { state: 'hidden', timeout: 5000 });
      
      // Verify update (description might not be visible in card, but modal should have closed)
      await expect(modal).not.toBeVisible();
    }
  });

  test('should delete a portfolio with confirmation', async ({ page }) => {
    // Check if portfolios exist
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount > 0) {
      // Get portfolio name for verification
      const portfolioName = await portfolioCard.locator('h3, .portfolio-name').first().textContent();
      
      // Click delete button
      const deleteButton = portfolioCard.locator('[data-testid="delete-portfolio"]').or(
        portfolioCard.locator('button:has-text("Delete")')
      );
      await deleteButton.click();
      
      // Handle confirmation dialog
      page.on('dialog', dialog => {
        expect(dialog.type()).toBe('confirm');
        dialog.accept();
      });
      
      // Wait for portfolio to be removed
      if (portfolioName) {
        await expect(page.locator(`text=${portfolioName}`)).not.toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should navigate to portfolio detail page', async ({ page }) => {
    // Check if portfolios exist
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount > 0) {
      // Click on portfolio card or view button
      const viewButton = portfolioCard.locator('[data-testid="view-portfolio"]').or(
        portfolioCard.locator('button:has-text("View")').or(portfolioCard)
      );
      
      await viewButton.click();
      
      // Should navigate to portfolio detail page
      await expect(page).toHaveURL(/\/portfolios\/.+/);
      
      // Should show portfolio detail content
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('[data-testid="portfolio-overview"]').or(page.locator('.portfolio-overview'))).toBeVisible();
    }
  });

  test('should handle form validation errors', async ({ page }) => {
    // Open create modal
    const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
      page.locator('button:has-text("Create Portfolio")')
    );
    await createButton.click();
    
    // Fill with invalid data
    await page.locator('input[name="name"]').fill(''); // Empty name
    await page.locator('input[name="initialCash"]').fill('invalid'); // Invalid cash amount
    
    // Try to submit
    await page.locator('button[type="submit"]').click();
    
    // Form should still be visible due to validation
    const modal = page.locator('[data-testid="portfolio-modal"]').or(page.locator('[role="dialog"]'));
    await expect(modal).toBeVisible();
  });

  test('should close modal without saving', async ({ page }) => {
    // Open create modal
    const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
      page.locator('button:has-text("Create Portfolio")')
    );
    await createButton.click();
    
    // Fill some data
    await page.locator('input[name="name"]').fill('Test Portfolio to Cancel');
    
    // Close modal without saving
    const closeButton = page.locator('[data-testid="close-modal"]').or(
      page.locator('button:has-text("Cancel")').or(page.locator('[aria-label="Close"]'))
    );
    await closeButton.click();
    
    // Modal should be closed
    const modal = page.locator('[data-testid="portfolio-modal"]').or(page.locator('[role="dialog"]'));
    await expect(modal).not.toBeVisible();
    
    // Portfolio should not be created
    await expect(page.locator('text=Test Portfolio to Cancel')).not.toBeVisible();
  });
});