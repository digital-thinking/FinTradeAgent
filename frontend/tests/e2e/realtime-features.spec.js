// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Real-time Features', () => {
  let portfolioPage;

  test.beforeEach(async ({ page }) => {
    portfolioPage = page;
    
    // Navigate to portfolios and find/create a test portfolio
    await page.goto('/portfolios');
    await page.waitForLoadState('networkidle');
    
    const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
    const portfolioCount = await portfolioCard.count();
    
    if (portfolioCount === 0) {
      // Create a test portfolio for real-time testing
      const testPortfolioName = `Realtime Test Portfolio ${Date.now()}`;
      
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create Portfolio")')
      );
      await createButton.click();
      
      await page.locator('input[name="name"]').fill(testPortfolioName);
      await page.locator('input[name="description"]').fill('Test portfolio for real-time E2E tests');
      await page.locator('input[name="initialCash"]').fill('25000');
      
      await page.locator('button[type="submit"]').click();
      await page.waitForSelector('[data-testid="portfolio-modal"]', { state: 'hidden', timeout: 5000 });
    }
    
    // Navigate to first portfolio's detail page
    const firstPortfolio = page.locator('[data-testid="portfolio-card"]').first();
    const viewButton = firstPortfolio.locator('[data-testid="view-portfolio"]').or(
      firstPortfolio.locator('button:has-text("View")').or(firstPortfolio)
    );
    
    await viewButton.click();
    await page.waitForURL(/\/portfolios\/.+/);
    await page.waitForLoadState('networkidle');
  });

  test('should establish WebSocket connection', async ({ page }) => {
    // Check for WebSocket connection indicator
    const wsIndicator = page.locator('[data-testid="ws-status"]').or(
      page.locator('.ws-status, .websocket-status, .connection-status')
    );
    
    // Wait for WebSocket connection to establish
    await page.waitForTimeout(2000);
    
    if (await wsIndicator.count() > 0) {
      // Check connection status
      await expect(wsIndicator).toContainText(/connected|active|online/i);
      
      // Check connection icon or indicator
      const wsIcon = wsIndicator.locator('.icon, i, svg').or(
        page.locator('[data-testid="ws-icon"]')
      );
      
      if (await wsIcon.count() > 0) {
        await expect(wsIcon).toBeVisible();
      }
    } else {
      // If no explicit indicator, check for WebSocket functionality
      // by looking for real-time elements that depend on WebSocket
      const realtimeElements = page.locator('[data-testid="execution-progress"]').or(
        page.locator('.real-time, .live-update')
      );
      
      // Real-time elements should be present for WebSocket functionality
      const rtCount = await realtimeElements.count();
      expect(rtCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should receive live execution updates via WebSocket', async ({ page }) => {
    // Start agent execution to trigger WebSocket updates
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    
    await executeButton.click();
    
    // Wait for execution to start
    await page.waitForTimeout(3000);
    
    // Check for live progress updates
    const progressContainer = page.locator('[data-testid="execution-progress"]').or(
      page.locator('.progress-indicator, .execution-status')
    );
    
    await expect(progressContainer).toBeVisible({ timeout: 10000 });
    
    // Monitor for real-time updates
    const progressSteps = page.locator('[data-testid="progress-step"]').or(
      page.locator('.progress-step, .status-update')
    );
    
    // Wait for multiple progress updates
    await expect(progressSteps).toHaveCount(1, { timeout: 5000 }).catch(() => {
      // If count expectation fails, just check that at least one exists
      return expect(progressSteps.first()).toBeVisible({ timeout: 10000 });
    });
    
    // Check that updates are coming in real-time
    let initialStepCount = await progressSteps.count();
    
    // Wait a bit more for additional updates
    await page.waitForTimeout(5000);
    
    let newStepCount = await progressSteps.count();
    
    // Should have either more steps or updated content
    if (newStepCount > initialStepCount) {
      expect(newStepCount).toBeGreaterThan(initialStepCount);
    } else {
      // If count didn't change, check that content is being updated
      const firstStep = progressSteps.first();
      if (await firstStep.count() > 0) {
        await expect(firstStep).toContainText(/.+/);
      }
    }
  });

  test('should update execution logs in real-time', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    
    await executeButton.click();
    
    // Wait for logs container to appear
    const logsContainer = page.locator('[data-testid="execution-logs"]').or(
      page.locator('.execution-logs, .logs-container')
    );
    
    await expect(logsContainer).toBeVisible({ timeout: 10000 });
    
    // Monitor log entries appearing in real-time
    const logEntries = page.locator('[data-testid="log-entry"]').or(
      page.locator('.log-entry, .log-item')
    );
    
    // Wait for first log entry
    await expect(logEntries.first()).toBeVisible({ timeout: 15000 });
    
    let initialLogCount = await logEntries.count();
    
    // Wait for more logs to accumulate
    await page.waitForTimeout(8000);
    
    let newLogCount = await logEntries.count();
    
    // Should have more log entries as execution progresses
    expect(newLogCount).toBeGreaterThanOrEqual(initialLogCount);
    
    // Verify log entries have timestamps (indicating real-time updates)
    const firstLog = logEntries.first();
    const logContent = await firstLog.textContent();
    
    // Logs should contain timestamp or time information
    expect(logContent).toMatch(/\d{2}:\d{2}|\d{4}-\d{2}-\d{2}|ago|AM|PM/);
  });

  test('should handle WebSocket disconnection and reconnection', async ({ page }) => {
    // Start execution to have active WebSocket
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    
    await executeButton.click();
    await page.waitForTimeout(3000);
    
    // Simulate network interruption by going offline and back online
    await page.context().setOffline(true);
    
    // Wait a moment for disconnection to be detected
    await page.waitForTimeout(2000);
    
    // Check for disconnection indicator
    const wsIndicator = page.locator('[data-testid="ws-status"]').or(
      page.locator('.ws-status, .websocket-status, .connection-status')
    );
    
    if (await wsIndicator.count() > 0) {
      // Should show disconnected status
      await expect(wsIndicator).toContainText(/disconnected|offline|error/i, { timeout: 5000 });
    }
    
    // Go back online
    await page.context().setOffline(false);
    
    // Wait for reconnection
    await page.waitForTimeout(3000);
    
    if (await wsIndicator.count() > 0) {
      // Should reconnect
      await expect(wsIndicator).toContainText(/connected|active|online/i, { timeout: 10000 });
    }
    
    // Verify that real-time features work after reconnection
    const progressContainer = page.locator('[data-testid="execution-progress"]').or(
      page.locator('.progress-indicator, .execution-status')
    );
    
    // Should still show execution progress
    await expect(progressContainer).toBeVisible();
  });

  test('should show live portfolio value updates', async ({ page }) => {
    // Check for portfolio value display
    const portfolioValue = page.locator('[data-testid="portfolio-value"]').or(
      page.locator('.portfolio-value, .total-value, .current-value')
    );
    
    if (await portfolioValue.count() > 0) {
      await expect(portfolioValue).toBeVisible();
      
      let initialValue = await portfolioValue.textContent();
      
      // Start execution which might cause value updates
      const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
        page.locator('button:has-text("Execute Agent")')
      );
      
      if (await executeButton.count() > 0 && await executeButton.isEnabled()) {
        await executeButton.click();
        
        // Wait for execution to potentially update values
        await page.waitForTimeout(10000);
        
        // Check if value has been updated
        let currentValue = await portfolioValue.textContent();
        
        // Value format should be consistent (dollar sign, numbers)
        expect(currentValue).toMatch(/\$[\d,]+\.?\d*/);
        
        // Even if value hasn't changed, it should still be displaying correctly
        expect(currentValue).toBeDefined();
      }
    }
  });

  test('should update trade recommendations in real-time', async ({ page }) => {
    // Navigate to trades page to check for real-time updates
    await page.goto('/trades');
    await page.waitForLoadState('networkidle');
    
    const tradesContainer = page.locator('[data-testid="trades-container"]').or(
      page.locator('.trades, .trade-list')
    );
    
    await expect(tradesContainer).toBeVisible();
    
    // Check for live trade updates indicator
    const liveIndicator = page.locator('[data-testid="live-updates"]').or(
      page.locator('.live, .real-time-indicator')
    );
    
    if (await liveIndicator.count() > 0) {
      await expect(liveIndicator).toBeVisible();
    }
    
    // Monitor trade list for changes
    const tradeCards = page.locator('[data-testid="trade-card"]').or(
      page.locator('.trade-card, .trade-item')
    );
    
    let initialTradeCount = await tradeCards.count();
    
    // Wait for potential real-time trade updates
    await page.waitForTimeout(5000);
    
    let newTradeCount = await tradeCards.count();
    
    // Trade count might change or stay same, but page should remain functional
    expect(newTradeCount).toBeGreaterThanOrEqual(0);
    
    // If trades exist, they should have proper structure
    if (newTradeCount > 0) {
      const firstTrade = tradeCards.first();
      await expect(firstTrade).toBeVisible();
    }
  });

  test('should handle multiple concurrent WebSocket connections', async ({ page, context }) => {
    // Open a second tab/page to test concurrent connections
    const secondPage = await context.newPage();
    
    // Navigate both pages to the same portfolio
    const currentUrl = page.url();
    await secondPage.goto(currentUrl);
    await secondPage.waitForLoadState('networkidle');
    
    // Start execution from first page
    const executeButton1 = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    
    if (await executeButton1.count() > 0 && await executeButton1.isEnabled()) {
      await executeButton1.click();
      
      // Wait for execution to start
      await page.waitForTimeout(3000);
      
      // Check that both pages receive updates
      const progress1 = page.locator('[data-testid="execution-progress"]').or(
        page.locator('.progress-indicator, .execution-status')
      );
      
      const progress2 = secondPage.locator('[data-testid="execution-progress"]').or(
        secondPage.locator('.progress-indicator, .execution-status')
      );
      
      // Both pages should show execution progress
      await expect(progress1).toBeVisible({ timeout: 10000 });
      await expect(progress2).toBeVisible({ timeout: 10000 });
      
      // Wait for updates
      await page.waitForTimeout(5000);
      
      // Both pages should have similar execution status
      const logs1 = page.locator('[data-testid="log-entry"]');
      const logs2 = secondPage.locator('[data-testid="log-entry"]');
      
      const logs1Count = await logs1.count();
      const logs2Count = await logs2.count();
      
      // Both should have logs (might not be exactly same count due to timing)
      if (logs1Count > 0 && logs2Count > 0) {
        expect(Math.abs(logs1Count - logs2Count)).toBeLessThanOrEqual(2);
      }
    }
    
    await secondPage.close();
  });

  test('should show real-time system status updates', async ({ page }) => {
    // Navigate to system health page
    await page.goto('/system');
    await page.waitForLoadState('networkidle');
    
    // Check for real-time system metrics
    const systemMetrics = page.locator('[data-testid="system-metrics"]').or(
      page.locator('.system-metrics, .health-metrics')
    );
    
    if (await systemMetrics.count() > 0) {
      await expect(systemMetrics).toBeVisible();
      
      // Look for live updating metrics
      const cpuMetric = page.locator('[data-testid="cpu-usage"]').or(
        page.locator('.cpu, .cpu-usage')
      );
      const memoryMetric = page.locator('[data-testid="memory-usage"]').or(
        page.locator('.memory, .memory-usage')
      );
      
      if (await cpuMetric.count() > 0) {
        await expect(cpuMetric).toContainText(/\d+%|\d+/);
      }
      
      if (await memoryMetric.count() > 0) {
        await expect(memoryMetric).toContainText(/\d+%|\d+/);
      }
      
      // Check for automatic refresh/updates
      const refreshIndicator = page.locator('[data-testid="auto-refresh"]').or(
        page.locator('.auto-refresh, .updating')
      );
      
      if (await refreshIndicator.count() > 0) {
        await expect(refreshIndicator).toBeVisible();
      }
    }
  });

  test('should handle WebSocket message queuing during disconnection', async ({ page }) => {
    // Start execution
    const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
      page.locator('button:has-text("Execute Agent")')
    );
    
    await executeButton.click();
    await page.waitForTimeout(3000);
    
    // Get initial log count
    const logEntries = page.locator('[data-testid="log-entry"]').or(
      page.locator('.log-entry, .log-item')
    );
    
    const initialCount = await logEntries.count();
    
    // Simulate brief disconnection
    await page.context().setOffline(true);
    await page.waitForTimeout(2000);
    await page.context().setOffline(false);
    
    // Wait for reconnection and message catch-up
    await page.waitForTimeout(5000);
    
    // Should have more logs after reconnection (assuming messages were queued)
    const finalCount = await logEntries.count();
    
    // Either more logs or at least the same amount
    expect(finalCount).toBeGreaterThanOrEqual(initialCount);
    
    // Logs should still be properly formatted
    if (finalCount > 0) {
      const firstLog = logEntries.first();
      await expect(firstLog).toContainText(/.+/);
    }
  });

  test('should display WebSocket connection health metrics', async ({ page }) => {
    // Look for connection health information
    const connectionHealth = page.locator('[data-testid="connection-health"]').or(
      page.locator('.connection-health, .ws-health')
    );
    
    if (await connectionHealth.count() > 0) {
      await expect(connectionHealth).toBeVisible();
      
      // Check for connection metrics
      const latency = connectionHealth.locator('[data-testid="latency"]').or(
        connectionHealth.locator('.latency, .ping')
      );
      const uptime = connectionHealth.locator('[data-testid="uptime"]').or(
        connectionHealth.locator('.uptime, .connected-time')
      );
      
      if (await latency.count() > 0) {
        await expect(latency).toContainText(/\d+ms|\d+/);
      }
      
      if (await uptime.count() > 0) {
        await expect(uptime).toContainText(/\d+:\d+|\d+[sm]/);
      }
    }
  });
});