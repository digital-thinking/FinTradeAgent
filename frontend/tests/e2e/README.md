# End-to-End (E2E) Testing with Playwright

This directory contains comprehensive E2E tests for the FinTradeAgent Vue.js application using Playwright.

## Overview

The E2E test suite covers:

- **Core User Workflows**: Portfolio management, agent execution, trade management, dashboard navigation
- **Advanced Scenarios**: Real-time features, theme switching, responsive design, error handling
- **Cross-Browser Testing**: Chromium, Firefox, Safari compatibility
- **Mobile Testing**: Touch interactions, responsive layouts
- **Performance**: Load times, WebSocket functionality
- **Accessibility**: Keyboard navigation, screen reader compatibility

## Test Structure

```
tests/e2e/
├── README.md                     # This file
├── portfolio-management.spec.js  # Portfolio CRUD operations
├── agent-execution.spec.js       # Agent execution and real-time updates
├── trade-management.spec.js      # Trade recommendations and actions
├── dashboard-navigation.spec.js  # Navigation and page routing
├── realtime-features.spec.js     # WebSocket and live updates
├── theme-switching.spec.js       # Dark/light mode functionality
├── responsive-design.spec.js     # Mobile, tablet, desktop layouts
├── error-handling.spec.js        # Network errors, API failures
└── cross-browser.spec.js         # Browser compatibility tests
```

## Setup

### Prerequisites

1. **Node.js** (v18 or higher)
2. **Frontend application** running on `http://localhost:3000`
3. **Backend API** running on `http://localhost:8000`

### Installation

```bash
# Install Playwright and dependencies
npm run test:e2e:install

# Install system dependencies (Linux)
npx playwright install-deps
```

## Running Tests

### All E2E Tests
```bash
npm run test:e2e
```

### Specific Browsers
```bash
npm run test:e2e:chromium    # Chromium only
npm run test:e2e:firefox     # Firefox only  
npm run test:e2e:webkit      # Safari/WebKit only
npm run test:e2e:mobile      # Mobile browsers only
```

### Development & Debugging
```bash
npm run test:e2e:headed      # Run with browser UI visible
npm run test:e2e:debug       # Debug mode with inspector
npm run test:e2e:ui          # Interactive test UI
```

### Specific Test Files
```bash
npx playwright test portfolio-management.spec.js
npx playwright test --grep "should create portfolio"
```

### Test Reports
```bash
npm run test:e2e:report      # View HTML report
```

## Configuration

The tests are configured in `playwright.config.js`:

- **Base URL**: `http://localhost:3000`
- **Browsers**: Chrome, Firefox, Safari, Mobile Chrome, Mobile Safari
- **Screenshots**: Captured on failure
- **Videos**: Recorded on failure
- **Traces**: Collected on retry
- **Parallel execution**: Enabled
- **Retries**: 2 retries on CI

## Test Scenarios

### 1. Portfolio Management (`portfolio-management.spec.js`)
- ✅ Create, edit, delete portfolios
- ✅ Form validation (client and server-side)
- ✅ Modal interactions
- ✅ Navigation to portfolio details

### 2. Agent Execution (`agent-execution.spec.js`)
- ✅ Start/stop agent execution
- ✅ Real-time progress updates via WebSocket
- ✅ Execution logs streaming
- ✅ Error handling during execution
- ✅ Multiple concurrent sessions

### 3. Trade Management (`trade-management.spec.js`)
- ✅ View pending trades
- ✅ Apply/cancel trades with confirmation
- ✅ Trade details and recommendations
- ✅ Bulk actions and filtering
- ✅ Portfolio navigation from trades

### 4. Dashboard Navigation (`dashboard-navigation.spec.js`)
- ✅ All page navigation and routing
- ✅ Active navigation states
- ✅ Breadcrumb navigation
- ✅ Loading states and error pages
- ✅ Dashboard statistics and charts

### 5. Real-time Features (`realtime-features.spec.js`)
- ✅ WebSocket connection establishment
- ✅ Live execution progress updates
- ✅ Real-time log streaming
- ✅ Connection error handling
- ✅ Multiple client synchronization
- ✅ Message queuing during disconnection

### 6. Theme Switching (`theme-switching.spec.js`)
- ✅ Toggle between dark/light themes
- ✅ Theme persistence across sessions
- ✅ System preference detection
- ✅ Chart color adaptation
- ✅ Accessibility in both themes
- ✅ Smooth transitions

### 7. Responsive Design (`responsive-design.spec.js`)
- ✅ Mobile layout (375px): Hamburger menu, stacked cards, touch-friendly controls
- ✅ Tablet layout (768px): 2-column grids, optimized forms
- ✅ Desktop layout (1920px): Full navigation, multi-column layouts, detailed tables
- ✅ Viewport transition handling
- ✅ Content reflow and readability

### 8. Error Handling (`error-handling.spec.js`)
- ✅ Network failures and offline scenarios
- ✅ API errors (404, 500, 401, timeouts)
- ✅ Form validation errors
- ✅ WebSocket connection failures
- ✅ Error recovery mechanisms
- ✅ Graceful degradation

### 9. Cross-Browser Compatibility (`cross-browser.spec.js`)
- ✅ Core functionality across all browsers
- ✅ WebSocket compatibility
- ✅ CSS animation support
- ✅ Performance consistency
- ✅ Accessibility features
- ✅ Error message consistency

## Best Practices

### Writing Tests

1. **Use data-testid attributes** for reliable element selection
2. **Wait for network idle** after navigation
3. **Handle dynamic content** with proper waiting strategies
4. **Test error states** alongside happy paths
5. **Keep tests isolated** - each test should be independent

### Test Data Management

```javascript
// Good: Use unique identifiers
const testPortfolioName = `Test Portfolio ${Date.now()}`;

// Good: Clean up test data
await page.locator('[data-testid="delete-portfolio"]').click();
```

### Element Selection Priority

1. `[data-testid="element-id"]` (preferred)
2. Semantic selectors (`button:has-text("Submit")`)
3. CSS classes/IDs (last resort)

```javascript
// Preferred approach with fallbacks
const createButton = page.locator('[data-testid="create-portfolio-btn"]').or(
  page.locator('button:has-text("Create Portfolio")')
);
```

### Handling Real-time Features

```javascript
// Wait for WebSocket connection
await page.waitForTimeout(2000);

// Check for real-time updates
await expect(progressSteps.first()).toBeVisible({ timeout: 15000 });
```

## CI/CD Integration

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run dev &
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: test-results/
```

## Troubleshooting

### Common Issues

1. **Tests timing out**
   ```bash
   # Increase timeout in test
   await expect(element).toBeVisible({ timeout: 10000 });
   ```

2. **WebSocket connection failures**
   ```bash
   # Check backend is running
   curl http://localhost:8000/api/health
   ```

3. **Browser installation issues**
   ```bash
   # Reinstall browsers
   npx playwright install --force
   ```

4. **Port conflicts**
   ```bash
   # Update playwright.config.js baseURL
   baseURL: 'http://localhost:3001'
   ```

### Debugging

```bash
# Run single test with debug
npx playwright test portfolio-management.spec.js --debug

# Generate trace
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip
```

### Performance Optimization

1. **Run tests in parallel** (default configuration)
2. **Use selective test execution** for faster feedback
3. **Cache browser installations** in CI
4. **Optimize wait strategies** to reduce test duration

## Test Data

The tests are designed to work with the existing FinTradeAgent application without requiring specific seed data. They:

- Create test portfolios dynamically
- Handle empty states gracefully  
- Clean up test data where possible
- Use unique identifiers to avoid conflicts

## Maintenance

### Updating Tests

When application features change:

1. Update corresponding test files
2. Add new test scenarios for new features
3. Update element selectors if UI changes
4. Review cross-browser compatibility

### Adding New Tests

1. Create new `.spec.js` file in `tests/e2e/`
2. Follow existing patterns and structure
3. Add appropriate `data-testid` attributes to components
4. Include in CI/CD pipeline

## Performance Benchmarks

Target performance metrics:
- Page load: < 3 seconds
- WebSocket connection: < 2 seconds
- Form submission: < 1 second
- Theme switch: < 0.5 seconds

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Vue Testing Handbook](https://vue-test-utils.vuejs.org/)
- [Web Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Responsive Design Testing](https://web.dev/responsive-web-design-basics/)