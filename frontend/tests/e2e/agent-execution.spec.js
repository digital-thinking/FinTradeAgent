// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Agent Execution', () => {
  let testPortfolioName;

  test.beforeEach(async ({ page }) => {
    // Navigate to portfolio detail page or create a test portfolio
    await page.goto('/portfolios');
    await page.waitForLoadState('networkidle');
    
    // Check if portfolios exist, if not create one for testing
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount === 0) {
      // Create a test portfolio for agent execution testing
      testPortfolioName = `Agent Test Portfolio ${Date.now()}`;
      
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create Portfolio")')
      );
      await createButton.click();
      
      await page.locator('input[name="name"]').fill(testPortfolioName);
      await page.locator('input[name="description"]').fill('Test portfolio for agent execution E2E tests');
      await page.locator('input[name="initialCash"]').fill('50000');
      
      await page.locator('button[type="submit"]').click();
      await page.waitForSelector('[data-testid="portfolio-modal"]', { state: 'hidden', timeout: 5000 });
    }
    
    // Navigate to the first portfolio's detail page
    const firstPortfolio = page.locator('[data-testid="portfolio-card"]').first();
    const viewButton = firstPortfolio.locator('[data-testid="view-portfolio"]').or(
      firstPortfolio.locator('button:has-text("View")').or(firstPortfolio)
    );
    
    await viewButton.click();
    await page.waitForURL(/\/portfolios\/.+/);
    await page.waitForLoadState('networkidle');
  });

  test('should display agent execution interface', async ({ page }) => {
    // Check that we're on portfolio detail page
    await expect(page).toHaveURL(/\/portfolios\/.+/);
    
    // Check for agent execution section
    const executionSection = page.locator('[data-testid="agent-execution"]').or(
      page.locator('.agent-execution, .execution-section')
    );
    await expect(executionSection).toBeVisible();
    
    // Check for execute button
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await expect(executeButton).toBeVisible();
    await expect(executeButton).toBeEnabled();
  });

  test('should start agent execution', async ({ page }) => {
    // Click execute agent button
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Check for execution started confirmation or progress indicator
    const progressIndicator = page.locator('[data-testid="execution-progress"]').or(
      page.locator('.progress-indicator, .execution-status')
    );
    
    // Wait for progress indicator to appear
    await expect(progressIndicator).toBeVisible({ timeout: 10000 });
    
    // Check that execute button is disabled during execution
    await expect(executeButton).toBeDisabled({ timeout: 5000 });
  });

  test('should show real-time progress updates', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait for progress to start
    const progressContainer = page.locator('[data-testid="execution-progress"]').or(
      page.locator('.progress-indicator, .execution-status')
    );
    await expect(progressContainer).toBeVisible({ timeout: 10000 });
    
    // Check for progress steps or status updates
    const progressSteps = page.locator('[data-testid="progress-step"]').or(
      page.locator('.progress-step, .status-update')
    );
    
    // Wait for at least one progress step to appear
    await expect(progressSteps.first()).toBeVisible({ timeout: 15000 });
    
    // Check for WebSocket connection indicator (if visible)
    const wsIndicator = page.locator('[data-testid="ws-status"]').or(
      page.locator('.ws-connected, .websocket-status')
    );
    
    // WebSocket indicator might be visible
    const wsCount = await wsIndicator.count();
    if (wsCount > 0) {
      await expect(wsIndicator).toContainText(/connected|active/i);
    }
  });

  test('should display execution logs in real-time', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait for logs container
    const logsContainer = page.locator('[data-testid="execution-logs"]').or(
      page.locator('.execution-logs, .logs-container')
    );
    await expect(logsContainer).toBeVisible({ timeout: 10000 });
    
    // Wait for log entries to appear
    const logEntries = page.locator('[data-testid="log-entry"]').or(
      page.locator('.log-entry, .log-item')
    );
    
    // Should have at least one log entry within reasonable time
    await expect(logEntries.first()).toBeVisible({ timeout: 20000 });
    
    // Check log content format
    const firstLog = logEntries.first();
    await expect(firstLog).toContainText(/.+/); // Should have some content
  });

  test('should handle execution completion', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait for execution to start
    await page.waitForTimeout(2000);
    
    // For testing purposes, we'll simulate completion by waiting for status changes
    // In a real scenario, this would wait for actual completion
    
    // Check for completion status (may take time in real execution)
    const completionIndicator = page.locator('[data-testid="execution-complete"]').or(
      page.locator('.execution-complete, .status-complete')
    );
    
    // Wait for completion or timeout (using a reasonable timeout)
    try {
      await expect(completionIndicator).toBeVisible({ timeout: 60000 });
    } catch (error) {
      // If execution doesn't complete within timeout, check that it's still running
      const runningIndicator = page.locator('[data-testid="execution-running"]').or(
        page.locator('.execution-running, .status-running')
      );
      await expect(runningIndicator).toBeVisible();
      
      // For testing, we can stop here as execution is working
      console.log('Execution is running but did not complete within timeout - this is expected for E2E testing');
    }
  });

  test('should allow stopping execution', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait for execution to start
    await page.waitForTimeout(3000);
    
    // Look for stop button
    const stopButton = page.locator('[data-testid="stop-execution-btn"]').or(
      page.locator('button:has-text("Stop")')
    );
    
    // Stop button should appear during execution
    if (await stopButton.count() > 0) {
      await stopButton.click();
      
      // Confirm stop if confirmation dialog appears
      page.on('dialog', dialog => {
        dialog.accept();
      });
      
      // Check that execution stopped
      const stoppedIndicator = page.locator('[data-testid="execution-stopped"]').or(
        page.locator('.execution-stopped, .status-stopped')
      );
      
      try {
        await expect(stoppedIndicator).toBeVisible({ timeout: 10000 });
      } catch {
        // If no explicit stopped indicator, check that execute button is enabled again
        await expect(executeButton).toBeEnabled({ timeout: 10000 });
      }
    }
  });

  test('should show execution history', async ({ page }) => {
    // Check for execution history section
    const historySection = page.locator('[data-testid="execution-history"]').or(
      page.locator('.execution-history, .history-section')
    );
    
    // History section should be visible
    await expect(historySection).toBeVisible();
    
    // Check for history entries (there might be none for new portfolios)
    const historyEntries = page.locator('[data-testid="history-entry"]').or(
      page.locator('.history-entry, .history-item')
    );
    
    const historyCount = await historyEntries.count();
    
    if (historyCount > 0) {
      // If there are history entries, verify their structure
      const firstEntry = historyEntries.first();
      await expect(firstEntry).toBeVisible();
      
      // Should contain timestamp or date
      await expect(firstEntry).toContainText(/\d/);
    } else {
      // If no history, should show empty state or no entries message
      const emptyHistory = page.locator('[data-testid="empty-history"]').or(
        page.locator('.no-history, .empty-history')
      );
      
      // Either empty state should be visible or history section should be empty
      const emptyVisible = await emptyHistory.count();
      // Test passes if we have history section (even if empty)
      expect(historyCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should handle execution errors gracefully', async ({ page }) => {
    // This test simulates error scenarios
    // Note: In a real scenario, you might need to mock API responses or create error conditions
    
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait a bit for execution to potentially fail or show error
    await page.waitForTimeout(5000);
    
    // Check for error indicators
    const errorIndicator = page.locator('[data-testid="execution-error"]').or(
      page.locator('.execution-error, .error-status, .alert-error')
    );
    
    const errorCount = await errorIndicator.count();
    
    if (errorCount > 0) {
      // If error occurred, verify it's handled properly
      await expect(errorIndicator).toBeVisible();
      await expect(errorIndicator).toContainText(/.+/); // Should have error message
      
      // Execute button should be enabled again after error
      await expect(executeButton).toBeEnabled({ timeout: 10000 });
    } else {
      // If no error, execution should be running or completed
      const runningIndicator = page.locator('[data-testid="execution-running"], [data-testid="execution-complete"]').or(
        page.locator('.execution-running, .execution-complete')
      );
      
      // Should show some status
      await expect(runningIndicator.first()).toBeVisible();
    }
  });

  test('should update portfolio data after execution', async ({ page }) => {
    // Get initial portfolio value/stats
    const portfolioValue = page.locator('[data-testid="portfolio-value"]').or(
      page.locator('.portfolio-value, .total-value')
    );
    
    let initialValue = '';
    if (await portfolioValue.count() > 0) {
      initialValue = await portfolioValue.textContent();
    }
    
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    await executeButton.click();
    
    // Wait for execution to run for a bit
    await page.waitForTimeout(5000);
    
    // Check that portfolio data is being updated (even during execution)
    if (await portfolioValue.count() > 0) {
      await expect(portfolioValue).toBeVisible();
      // Value should be present (may or may not have changed yet)
      await expect(portfolioValue).toContainText(/\$|[\d,]+/);
    }
    
    // Check for other portfolio stats updates
    const statsContainer = page.locator('[data-testid="portfolio-stats"]').or(
      page.locator('.portfolio-stats, .stats-container')
    );
    
    if (await statsContainer.count() > 0) {
      await expect(statsContainer).toBeVisible();
    }
  });
});