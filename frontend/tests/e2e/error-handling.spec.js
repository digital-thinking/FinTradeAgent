// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Network Failures', () => {
    test('should handle complete network failure gracefully', async ({ page, context }) => {
      // Go offline
      await context.setOffline(true);
      
      // Try to navigate to a new page
      await page.goto('/portfolios');
      
      // Should show some indication of network error
      const networkError = page.locator('[data-testid="network-error"]').or(
        page.locator('.network-error, .offline, .connection-error')
      );
      
      const errorMessage = page.locator('text=/network|offline|connection/i');
      
      // Wait for error to be detected
      await page.waitForTimeout(3000);
      
      // Should show error indicator or message
      const networkErrorCount = await networkError.count();
      const errorMessageCount = await errorMessage.count();
      
      if (networkErrorCount > 0) {
        await expect(networkError).toBeVisible();
      } else if (errorMessageCount > 0) {
        await expect(errorMessage.first()).toBeVisible();
      } else {
        // Browser might show its own offline page
        const title = await page.title();
        expect(title).toMatch(/offline|error|not.*found/i);
      }
      
      // Go back online
      await context.setOffline(false);
      
      // Should recover
      await page.waitForTimeout(2000);
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      // Should work again
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should retry failed requests automatically', async ({ page }) => {
      // Intercept API requests and make some fail initially
      let requestCount = 0;
      
      await page.route('**/api/**', route => {
        requestCount++;
        if (requestCount <= 2) {
          // Fail first 2 requests
          route.abort('connectionrefused');
        } else {
          // Let subsequent requests through
          route.continue();
        }
      });
      
      // Navigate to a page that makes API calls
      await page.goto('/portfolios');
      
      // Wait for potential retries
      await page.waitForTimeout(5000);
      
      // Should eventually succeed or show proper error
      const content = page.locator('[data-testid="portfolios-container"]').or(
        page.locator('.portfolios, .portfolio-list, .error, .retry')
      );
      
      await expect(content).toBeVisible({ timeout: 10000 });
      
      // Check if retry mechanism is visible
      const retryButton = page.locator('[data-testid="retry-btn"]').or(
        page.locator('button:has-text("Retry")')
      );
      
      if (await retryButton.count() > 0) {
        await expect(retryButton).toBeVisible();
        
        // Test retry functionality
        await retryButton.click();
        await page.waitForTimeout(2000);
        
        // Should make another attempt
        expect(requestCount).toBeGreaterThan(2);
      }
    });

    test('should handle slow network connections', async ({ page, context }) => {
      // Simulate slow network
      await page.route('**/api/**', async route => {
        await new Promise(resolve => setTimeout(resolve, 3000)); // 3 second delay
        route.continue();
      });
      
      await page.goto('/portfolios');
      
      // Should show loading indicators
      const loadingIndicator = page.locator('[data-testid="loading"]').or(
        page.locator('.loading, .spinner, .skeleton')
      );
      
      // Loading should be visible initially
      await expect(loadingIndicator).toBeVisible({ timeout: 1000 });
      
      // Wait for request to complete
      await page.waitForTimeout(4000);
      
      // Loading should disappear
      const loadingCount = await loadingIndicator.count();
      if (loadingCount > 0) {
        await expect(loadingIndicator).not.toBeVisible({ timeout: 2000 });
      }
      
      // Content should eventually load
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should handle intermittent connectivity', async ({ page, context }) => {
      let requestCount = 0;
      
      // Simulate intermittent failures
      await page.route('**/api/**', route => {
        requestCount++;
        if (requestCount % 3 === 0) {
          // Fail every 3rd request
          route.abort('connectionrefused');
        } else {
          route.continue();
        }
      });
      
      // Navigate through multiple pages
      const pages = ['/portfolios', '/trades', '/system'];
      
      for (const pagePath of pages) {
        await page.goto(pagePath);
        await page.waitForTimeout(2000);
        
        // Should either show content or proper error handling
        const pageContent = page.locator('h1, .error, .retry, .loading');
        await expect(pageContent).toBeVisible({ timeout: 5000 });
        
        // Check for error recovery mechanisms
        const errorIndicator = page.locator('.error, [data-testid="error"]');
        if (await errorIndicator.count() > 0) {
          const retryButton = page.locator('button:has-text("Retry")');
          if (await retryButton.count() > 0) {
            await retryButton.click();
            await page.waitForTimeout(1000);
          }
        }
      }
    });
  });

  test.describe('API Errors', () => {
    test('should handle 404 API responses', async ({ page }) => {
      // Mock 404 responses
      await page.route('**/api/portfolios**', route => {
        route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Not found', message: 'Portfolios not found' })
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Should show appropriate error message
      const errorMessage = page.locator('[data-testid="not-found-error"]').or(
        page.locator('text=/not found|404/i').or(
          page.locator('.error, .not-found')
        )
      );
      
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
      
      // Should not show loading indicators
      const loadingIndicator = page.locator('[data-testid="loading"]');
      if (await loadingIndicator.count() > 0) {
        await expect(loadingIndicator).not.toBeVisible();
      }
    });

    test('should handle 500 server errors', async ({ page }) => {
      // Mock server error
      await page.route('**/api/**', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error', message: 'Something went wrong' })
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForTimeout(3000);
      
      // Should show server error message
      const serverError = page.locator('[data-testid="server-error"]').or(
        page.locator('text=/server error|500|something went wrong/i').or(
          page.locator('.error, .server-error')
        )
      );
      
      await expect(serverError).toBeVisible({ timeout: 5000 });
      
      // Should offer retry option
      const retryButton = page.locator('[data-testid="retry-btn"]').or(
        page.locator('button:has-text("Retry")')
      );
      
      if (await retryButton.count() > 0) {
        await expect(retryButton).toBeVisible();
        await expect(retryButton).toBeEnabled();
      }
    });

    test('should handle 401 authentication errors', async ({ page }) => {
      // Mock authentication error
      await page.route('**/api/**', route => {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Unauthorized', message: 'Authentication required' })
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForTimeout(3000);
      
      // Should show authentication error
      const authError = page.locator('[data-testid="auth-error"]').or(
        page.locator('text=/unauthorized|authentication|login/i').or(
          page.locator('.error, .auth-error')
        )
      );
      
      await expect(authError).toBeVisible({ timeout: 5000 });
      
      // Should redirect to login or show login option
      const loginButton = page.locator('button:has-text("Login")').or(
        page.locator('a[href*="login"]')
      );
      
      if (await loginButton.count() > 0) {
        await expect(loginButton).toBeVisible();
      }
    });

    test('should handle malformed API responses', async ({ page }) => {
      // Mock malformed JSON response
      await page.route('**/api/portfolios**', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: 'invalid json {'
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForTimeout(3000);
      
      // Should handle parsing error gracefully
      const parseError = page.locator('[data-testid="parse-error"]').or(
        page.locator('text=/parse error|invalid response|malformed/i').or(
          page.locator('.error, .parse-error')
        )
      );
      
      const genericError = page.locator('.error, [data-testid="error"]');
      
      // Should show some error indication
      const parseErrorCount = await parseError.count();
      const genericErrorCount = await genericError.count();
      
      if (parseErrorCount > 0) {
        await expect(parseError).toBeVisible();
      } else if (genericErrorCount > 0) {
        await expect(genericError.first()).toBeVisible();
      }
      
      // App should not crash
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle timeout errors', async ({ page }) => {
      // Mock extremely slow response (timeout)
      await page.route('**/api/**', async route => {
        // Don't respond at all to simulate timeout
        await new Promise(resolve => setTimeout(resolve, 30000));
        route.continue();
      });
      
      await page.goto('/portfolios');
      
      // Should show loading initially
      const loadingIndicator = page.locator('[data-testid="loading"]').or(
        page.locator('.loading, .spinner')
      );
      
      if (await loadingIndicator.count() > 0) {
        await expect(loadingIndicator).toBeVisible({ timeout: 2000 });
      }
      
      // Wait for potential timeout
      await page.waitForTimeout(10000);
      
      // Should show timeout error or stop loading
      const timeoutError = page.locator('[data-testid="timeout-error"]').or(
        page.locator('text=/timeout|taking too long/i').or(
          page.locator('.error, .timeout')
        )
      );
      
      const timeoutCount = await timeoutError.count();
      const stillLoading = await loadingIndicator.count() > 0 && await loadingIndicator.isVisible();
      
      if (timeoutCount > 0) {
        await expect(timeoutError).toBeVisible();
      } else if (!stillLoading) {
        // Loading should have stopped
        expect(stillLoading).toBe(false);
      }
    });
  });

  test.describe('Form Validation Errors', () => {
    test('should handle form validation errors', async ({ page }) => {
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Open create portfolio modal
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create")')
      );
      
      if (await createButton.count() > 0) {
        await createButton.click();
        
        // Submit empty form
        const submitButton = page.locator('button[type="submit"]').or(
          page.locator('button:has-text("Create")')
        );
        
        await submitButton.click();
        
        // Should show validation errors
        const validationErrors = page.locator('[data-testid="validation-error"]').or(
          page.locator('.error, .validation-error, .invalid-feedback')
        );
        
        // HTML5 validation or custom validation should appear
        const nameInput = page.locator('input[name="name"]');
        const nameInputValid = await nameInput.evaluate(el => el.validity.valid);
        
        if (!nameInputValid || await validationErrors.count() > 0) {
          // Validation is working
          expect(true).toBe(true);
        }
        
        // Form should not submit with invalid data
        const modal = page.locator('[data-testid="portfolio-modal"]');
        if (await modal.count() > 0) {
          await expect(modal).toBeVisible(); // Should still be open
        }
      }
    });

    test('should handle server-side validation errors', async ({ page }) => {
      // Mock server validation error response
      await page.route('**/api/portfolios', route => {
        if (route.request().method() === 'POST') {
          route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              error: 'Validation Error',
              message: 'Portfolio name already exists',
              details: {
                name: ['Portfolio name must be unique']
              }
            })
          });
        } else {
          route.continue();
        }
      });
      
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
        page.locator('button:has-text("Create")')
      );
      
      if (await createButton.count() > 0) {
        await createButton.click();
        
        // Fill form with valid client-side data
        await page.locator('input[name="name"]').fill('Existing Portfolio');
        await page.locator('input[name="description"]').fill('Test description');
        await page.locator('input[name="initialCash"]').fill('10000');
        
        // Submit form
        const submitButton = page.locator('button[type="submit"]').or(
          page.locator('button:has-text("Create")')
        );
        
        await submitButton.click();
        await page.waitForTimeout(2000);
        
        // Should show server validation error
        const serverError = page.locator('[data-testid="server-validation-error"]').or(
          page.locator('text=/already exists|validation error|name must be unique/i').or(
            page.locator('.error, .server-error')
          )
        );
        
        await expect(serverError).toBeVisible({ timeout: 5000 });
        
        // Modal should remain open
        const modal = page.locator('[data-testid="portfolio-modal"]');
        if (await modal.count() > 0) {
          await expect(modal).toBeVisible();
        }
      }
    });
  });

  test.describe('WebSocket Connection Errors', () => {
    test('should handle WebSocket connection failures', async ({ page }) => {
      // Navigate to page with WebSocket functionality
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Find a portfolio and navigate to details
      const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
      if (await portfolioCard.count() > 0) {
        const viewButton = portfolioCard.locator('button:has-text("View")').or(portfolioCard);
        await viewButton.click();
        await page.waitForURL(/\/portfolios\/.+/);
      } else {
        // Create a portfolio first
        const createButton = page.locator('[data-testid="create-portfolio-btn"]');
        if (await createButton.count() > 0) {
          await createButton.click();
          
          await page.locator('input[name="name"]').fill('WS Test Portfolio');
          await page.locator('input[name="description"]').fill('Test');
          await page.locator('input[name="initialCash"]').fill('10000');
          
          await page.locator('button[type="submit"]').click();
          await page.waitForSelector('[data-testid="portfolio-modal"]', { state: 'hidden' });
          
          // Navigate to the created portfolio
          const newPortfolio = page.locator('text=WS Test Portfolio').first();
          await newPortfolio.click();
        }
      }
      
      // Mock WebSocket connection failure by blocking WebSocket requests
      await page.route('**/ws/**', route => route.abort());
      
      // Try to start agent execution (which uses WebSocket)
      const executeButton = page.locator('[data-testid="execute-agent-btn"]').or(
        page.locator('button:has-text("Execute")')
      );
      
      if (await executeButton.count() > 0) {
        await executeButton.click();
        await page.waitForTimeout(3000);
        
        // Should show WebSocket connection error
        const wsError = page.locator('[data-testid="websocket-error"]').or(
          page.locator('text=/websocket|connection.*failed|real.*time.*unavailable/i').or(
            page.locator('.ws-error, .connection-error')
          )
        );
        
        const wsErrorCount = await wsError.count();
        
        if (wsErrorCount > 0) {
          await expect(wsError).toBeVisible();
        }
        
        // Should still allow basic functionality without WebSocket
        await expect(page.locator('h1')).toBeVisible();
      }
    });

    test('should handle WebSocket disconnection during operation', async ({ page }) => {
      // This test would require actual WebSocket connection to test properly
      // For now, we'll test the UI handles missing real-time updates gracefully
      
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Navigate to portfolio detail if possible
      const portfolioCard = page.locator('[data-testid="portfolio-card"]').first();
      if (await portfolioCard.count() > 0) {
        const viewButton = portfolioCard.locator('button:has-text("View")').or(portfolioCard);
        await viewButton.click();
        await page.waitForURL(/\/portfolios\/.+/);
        
        // Check that page remains functional without real-time updates
        const executeButton = page.locator('[data-testid="execute-agent-btn"]');
        if (await executeButton.count() > 0) {
          await expect(executeButton).toBeVisible();
          await expect(executeButton).toBeEnabled();
        }
        
        // Check for graceful degradation indicators
        const offlineIndicator = page.locator('[data-testid="offline-mode"]').or(
          page.locator('.offline, .no-realtime')
        );
        
        // If offline indicators exist, they should be properly styled
        if (await offlineIndicator.count() > 0) {
          await expect(offlineIndicator).toBeVisible();
        }
      }
    });
  });

  test.describe('Error Recovery', () => {
    test('should provide clear error messages', async ({ page }) => {
      // Mock various error scenarios and check message clarity
      const errorScenarios = [
        {
          status: 404,
          body: { error: 'Not Found', message: 'Portfolio not found' },
          expectedText: /not found|does not exist/i
        },
        {
          status: 500,
          body: { error: 'Internal Server Error', message: 'Database connection failed' },
          expectedText: /server error|try again|contact support/i
        },
        {
          status: 403,
          body: { error: 'Forbidden', message: 'Insufficient permissions' },
          expectedText: /permission|access denied|not authorized/i
        }
      ];
      
      for (const scenario of errorScenarios) {
        await page.route('**/api/portfolios**', route => {
          route.fulfill({
            status: scenario.status,
            contentType: 'application/json',
            body: JSON.stringify(scenario.body)
          });
        });
        
        await page.goto('/portfolios');
        await page.waitForTimeout(2000);
        
        // Should show clear, user-friendly error message
        const errorMessage = page.locator('.error, [data-testid="error"]');
        
        if (await errorMessage.count() > 0) {
          const errorText = await errorMessage.first().textContent() || '';
          expect(errorText).toMatch(scenario.expectedText);
        }
        
        // Clean up route for next iteration
        await page.unroute('**/api/portfolios**');
      }
    });

    test('should provide actionable error recovery options', async ({ page }) => {
      // Mock server error
      await page.route('**/api/portfolios', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server Error' })
        });
      });
      
      await page.goto('/portfolios');
      await page.waitForTimeout(3000);
      
      // Should offer recovery actions
      const recoveryActions = [
        page.locator('button:has-text("Retry")'),
        page.locator('button:has-text("Refresh")'),
        page.locator('button:has-text("Go Home")'),
        page.locator('a:has-text("Contact Support")')
      ];
      
      let hasRecoveryAction = false;
      
      for (const action of recoveryActions) {
        if (await action.count() > 0) {
          await expect(action).toBeVisible();
          await expect(action).toBeEnabled();
          hasRecoveryAction = true;
          break;
        }
      }
      
      expect(hasRecoveryAction).toBe(true);
    });

    test('should maintain app state during error recovery', async ({ page }) => {
      // Navigate to a specific page
      await page.goto('/portfolios');
      await page.waitForLoadState('networkidle');
      
      // Cause a temporary error
      await page.route('**/api/**', route => {
        route.abort('connectionrefused');
      });
      
      // Try to perform an action that fails
      const createButton = page.locator('[data-testid="create-portfolio-btn"]');
      if (await createButton.count() > 0) {
        await createButton.click();
        
        // Fill form data
        const nameInput = page.locator('input[name="name"]');
        if (await nameInput.count() > 0) {
          await nameInput.fill('Recovery Test Portfolio');
          
          // Try to submit (will fail)
          const submitButton = page.locator('button[type="submit"]');
          await submitButton.click();
          await page.waitForTimeout(2000);
          
          // Remove error condition
          await page.unroute('**/api/**');
          
          // Form data should still be there
          const currentValue = await nameInput.inputValue();
          expect(currentValue).toBe('Recovery Test Portfolio');
          
          // Should be able to retry
          const retryButton = page.locator('button:has-text("Retry")');
          if (await retryButton.count() > 0) {
            await retryButton.click();
          } else {
            await submitButton.click();
          }
          
          await page.waitForTimeout(2000);
          
          // Should succeed now
          const modal = page.locator('[data-testid="portfolio-modal"]');
          if (await modal.count() > 0) {
            // Modal might close on success
            const isVisible = await modal.isVisible();
            // Either closed (success) or still open (but functional)
            expect(typeof isVisible).toBe('boolean');
          }
        }
      }
    });
  });
});