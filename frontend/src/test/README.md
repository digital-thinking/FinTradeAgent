# Frontend Testing Documentation

This directory contains all testing utilities, mocks, and documentation for the Vue.js frontend application.

## Test Structure

```
src/test/
├── README.md           # This documentation
├── setup.js           # Test environment setup
├── utils.js           # Common test utilities
└── mocks/
    ├── api.js         # API mocking utilities
    └── websocket.js   # WebSocket mocking utilities
```

## Running Tests

### Basic Commands

```bash
# Run all tests
npm test

# Run tests in watch mode (development)
npm run test:watch

# Run tests once (CI)
npm run test:run

# Run tests with UI
npm run test:ui

# Generate test coverage report
npm run test:coverage
```

### Test Types

1. **Unit Tests**: Individual component and composable tests
2. **Integration Tests**: Component interaction and API integration tests
3. **End-to-End Tests**: Full user workflow tests (planned for Task 5.4)

## Test Categories

### Component Tests

Located in `src/components/__tests__/` and `src/pages/__tests__/`

#### UI Components
- `BaseButton.test.js` - Button component variations and interactions
- `BaseCard.test.js` - Card component layouts and slots
- `BaseModal.test.js` - Modal component behavior and accessibility
- `StatCard.test.js` - Statistical display component
- `ToastNotification.test.js` - Notification system

#### Functional Components  
- `ExecutionProgress.test.js` - Trading agent execution progress
- `ErrorBoundary.test.js` - Error handling and recovery
- `ConnectionStatus.test.js` - WebSocket connection states

#### Chart Components
- `LineChart.test.js` - Chart.js integration and theming

#### Skeleton Components
- `DashboardSkeleton.test.js` - Dashboard loading states
- `PageSkeleton.test.js` - Generic page loading states
- `TableSkeleton.test.js` - Table loading states

### Composable Tests

Located in `src/composables/__tests__/`

- `useTheme.test.js` - Dark/light mode switching and persistence
- `useLoading.test.js` - Delayed loading state management
- `useWebSocket.test.js` - WebSocket connection and message handling
- `useErrorHandler.test.js` - Error handling and display logic
- `useToast.test.js` - Toast notification system

### Page Component Tests

Located in `src/pages/__tests__/`

- `DashboardPage.test.js` - Main dashboard with stats and charts
- `PortfoliosPage.test.js` - Portfolio CRUD operations
- `PortfolioDetailPage.test.js` - Complex WebSocket integration and execution flow

## Testing Utilities

### `mountComponent()`

Wrapper around Vue Test Utils `mount()` with common providers:

```javascript
import { mountComponent } from '../test/utils.js'

const wrapper = mountComponent(MyComponent, {
  props: { title: 'Test' }
})
```

### API Mocking

```javascript
import { createMockApi, mockApiResponses } from '../test/mocks/api.js'

const api = createMockApi()
api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
```

### WebSocket Mocking

```javascript
import { createMockWebSocket } from '../test/mocks/websocket.js'

const mockWs = createMockWebSocket('connected')
mockWs.simulateMessage({ type: 'execution_progress', status: 'running' })
```

## Test Coverage Goals

- **Components**: 90%+ coverage for all UI and functional components
- **Composables**: 95%+ coverage for business logic
- **Pages**: 85%+ coverage for integration scenarios

### Current Coverage

Run `npm run test:coverage` to see detailed coverage reports.

## Best Practices

### 1. Test Behavior, Not Implementation

```javascript
// ✅ Good - testing behavior
it('shows error message when API call fails', async () => {
  api.get.mockRejectedValue(new Error('API Error'))
  const wrapper = mountComponent(MyComponent)
  await flushPromises()
  
  expect(wrapper.text()).toContain('Failed to load data')
})

// ❌ Bad - testing implementation
it('calls fetchData method on mount', () => {
  const spy = vi.spyOn(MyComponent.methods, 'fetchData')
  mountComponent(MyComponent)
  
  expect(spy).toHaveBeenCalled()
})
```

### 2. Use Realistic Mock Data

```javascript
// ✅ Good - realistic portfolio data
const portfolioData = {
  name: 'growth-strategy',
  strategy: 'growth',
  cash_balance: 15000,
  positions: {
    'AAPL': { shares: 100, price: 180 }
  }
}

// ❌ Bad - unrealistic data
const portfolioData = {
  name: 'test',
  value: 123
}
```

### 3. Test Edge Cases

- Empty states (no data)
- Error conditions (API failures, network errors)
- Loading states
- User interactions (clicks, form submissions)
- Responsive behavior

### 4. Clean Up After Tests

```javascript
beforeEach(() => {
  vi.clearAllMocks()
  // Reset any global state
})

afterEach(() => {
  // Clean up timers, event listeners, etc.
})
```

## Mock Data

### API Responses

All mock API responses are centralized in `src/test/mocks/api.js`:

- `mockApiResponses.portfolios` - Portfolio list and details
- `mockApiResponses.dashboard` - Dashboard summary data
- `mockApiResponses.pendingTrades` - Trading queue data
- `mockApiResponses.systemHealth` - System status data

### WebSocket Messages

WebSocket message templates in `src/test/mocks/websocket.js`:

- `mockWebSocketMessages.executionStarted` - Execution start event
- `mockWebSocketMessages.executionProgress` - Progress updates
- `mockWebSocketMessages.executionCompleted` - Completion with results
- `mockWebSocketMessages.executionFailed` - Error scenarios

## Debugging Tests

### Test UI

Use `npm run test:ui` to open Vitest's web interface for:
- Interactive test running
- Test file exploration
- Real-time coverage updates
- Test output visualization

### Console Debugging

```javascript
it('debugs component state', () => {
  const wrapper = mountComponent(MyComponent)
  
  console.log('Component HTML:', wrapper.html())
  console.log('Component data:', wrapper.vm.$data)
  
  // Use screen.debug() for Testing Library style debugging
})
```

### Async Test Debugging

```javascript
it('handles async operations', async () => {
  const wrapper = mountComponent(MyComponent)
  
  // Wait for all promises to resolve
  await flushPromises()
  
  // Or wait for specific DOM changes
  await wrapper.vm.$nextTick()
  
  expect(wrapper.text()).toContain('Expected content')
})
```

## Common Issues

### 1. Async Test Failures

**Problem**: Tests fail intermittently with async operations

**Solution**: Use `flushPromises()` or `await wrapper.vm.$nextTick()`

```javascript
it('loads data correctly', async () => {
  api.get.mockResolvedValue({ data: testData })
  
  const wrapper = mountComponent(MyComponent)
  await flushPromises() // Wait for API call to complete
  
  expect(wrapper.text()).toContain('Expected data')
})
```

### 2. Timer-based Tests

**Problem**: Tests with setTimeout/setInterval

**Solution**: Use fake timers

```javascript
it('auto-refreshes data', async () => {
  vi.useFakeTimers()
  
  const wrapper = mountComponent(MyComponent)
  
  vi.advanceTimersByTime(30000) // Fast-forward 30 seconds
  await flushPromises()
  
  expect(api.get).toHaveBeenCalledTimes(2) // Initial + refresh
  
  vi.useRealTimers()
})
```

### 3. Router/Store Tests

**Problem**: Components depend on Vue Router or Pinia

**Solution**: Use `mountComponent()` utility which includes providers

```javascript
// mountComponent automatically provides router and store
const wrapper = mountComponent(MyPageComponent)
```

### 4. WebSocket Tests

**Problem**: WebSocket connections in tests

**Solution**: Mock the entire useWebSocket composable

```javascript
vi.mock('../composables/useWebSocket.js', () => ({
  useWebSocket: vi.fn(() => createMockWebSocket())
}))
```

## Contributing to Tests

1. **Every new component** should have corresponding tests
2. **Critical business logic** requires comprehensive test coverage
3. **API integrations** should be tested with realistic mock data
4. **User interactions** should be tested end-to-end
5. **Error scenarios** must be covered

### Test File Naming

- Component tests: `ComponentName.test.js`
- Composable tests: `useComposableName.test.js`
- Page tests: `PageName.test.js`
- Utility tests: `utilityName.test.js`

### Describe Block Structure

```javascript
describe('ComponentName', () => {
  describe('rendering', () => {
    // Basic rendering tests
  })
  
  describe('user interactions', () => {
    // Click, form submission tests
  })
  
  describe('API integration', () => {
    // Data loading, error handling
  })
  
  describe('edge cases', () => {
    // Empty states, errors, etc.
  })
})
```

This testing framework provides comprehensive coverage of the Vue.js application with realistic scenarios and robust mocking utilities.