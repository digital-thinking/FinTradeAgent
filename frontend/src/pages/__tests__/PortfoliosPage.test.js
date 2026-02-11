import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import PortfoliosPage from '../PortfoliosPage.vue'
import { mountComponent, mockApiResponses, flushPromises } from '../../test/utils.js'

// Mock API module
vi.mock('../../services/api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

describe('PortfoliosPage', () => {
  let api

  beforeEach(() => {
    setActivePinia(createPinia())
    api = require('../../services/api.js').default
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders portfolios page layout', () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    
    expect(wrapper.find('h1').text()).toContain('Portfolios')
    expect(wrapper.find('[data-testid="create-portfolio-button"]').exists()).toBe(true)
  })

  it('loads portfolios data on mount', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    mountComponent(PortfoliosPage)
    await flushPromises()
    
    expect(api.get).toHaveBeenCalledWith('/api/portfolios/')
  })

  it('displays loading skeleton while fetching', () => {
    api.get.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    const wrapper = mountComponent(PortfoliosPage)
    
    expect(wrapper.findComponent({ name: 'PageSkeleton' }).exists()).toBe(true)
  })

  it('displays portfolio cards on desktop', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const portfolioCards = wrapper.findAll('[data-testid="portfolio-card"]')
    expect(portfolioCards.length).toBe(mockApiResponses.portfolios.length)
  })

  it('displays portfolio information correctly', async () => {
    const portfoliosData = [
      {
        name: 'growth-portfolio',
        strategy: 'growth',
        cash_balance: 25000,
        total_value: 45000,
        positions: {
          'AAPL': { shares: 50, price: 180 },
          'GOOGL': { shares: 10, price: 150 }
        },
        last_updated: '2026-02-11T10:30:00Z'
      }
    ]
    
    api.get.mockResolvedValue({ data: portfoliosData })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('growth-portfolio')
    expect(wrapper.text()).toContain('Growth')
    expect(wrapper.text()).toContain('$45,000')
    expect(wrapper.text()).toContain('2 positions')
  })

  it('opens create portfolio modal when create button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const createButton = wrapper.find('[data-testid="create-portfolio-button"]')
    await createButton.trigger('click')
    
    expect(wrapper.findComponent({ name: 'BaseModal' }).props('open')).toBe(true)
    expect(wrapper.text()).toContain('Create Portfolio')
  })

  it('creates new portfolio when form submitted', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    api.post.mockResolvedValue({ data: { name: 'new-portfolio' } })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Open create modal
    const createButton = wrapper.find('[data-testid="create-portfolio-button"]')
    await createButton.trigger('click')
    
    // Fill form
    const nameInput = wrapper.find('[data-testid="portfolio-name-input"]')
    const strategySelect = wrapper.find('[data-testid="portfolio-strategy-select"]')
    const cashInput = wrapper.find('[data-testid="portfolio-cash-input"]')
    
    await nameInput.setValue('new-test-portfolio')
    await strategySelect.setValue('momentum')
    await cashInput.setValue('50000')
    
    // Submit form
    const submitButton = wrapper.find('[data-testid="create-portfolio-submit"]')
    await submitButton.trigger('click')
    
    expect(api.post).toHaveBeenCalledWith('/api/portfolios/', {
      name: 'new-test-portfolio',
      strategy: 'momentum',
      cash_balance: 50000
    })
  })

  it('shows validation errors for invalid form data', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Open create modal
    const createButton = wrapper.find('[data-testid="create-portfolio-button"]')
    await createButton.trigger('click')
    
    // Submit empty form
    const submitButton = wrapper.find('[data-testid="create-portfolio-submit"]')
    await submitButton.trigger('click')
    
    expect(wrapper.text()).toContain('Portfolio name is required')
  })

  it('opens edit modal when edit button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const editButton = wrapper.find('[data-testid="edit-portfolio-button"]')
    await editButton.trigger('click')
    
    expect(wrapper.findComponent({ name: 'BaseModal' }).props('open')).toBe(true)
    expect(wrapper.text()).toContain('Edit Portfolio')
  })

  it('updates portfolio when edit form submitted', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    api.put.mockResolvedValue({ data: { name: 'updated-portfolio' } })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Open edit modal
    const editButton = wrapper.find('[data-testid="edit-portfolio-button"]')
    await editButton.trigger('click')
    
    // Update form
    const nameInput = wrapper.find('[data-testid="portfolio-name-input"]')
    await nameInput.setValue('updated-name')
    
    // Submit form
    const submitButton = wrapper.find('[data-testid="update-portfolio-submit"]')
    await submitButton.trigger('click')
    
    expect(api.put).toHaveBeenCalledWith(
      `/api/portfolios/${mockApiResponses.portfolios[0].name}`,
      expect.objectContaining({
        name: 'updated-name'
      })
    )
  })

  it('opens delete confirmation when delete button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const deleteButton = wrapper.find('[data-testid="delete-portfolio-button"]')
    await deleteButton.trigger('click')
    
    expect(wrapper.findComponent({ name: 'ConfirmDialog' }).props('open')).toBe(true)
    expect(wrapper.text()).toContain('Delete Portfolio')
  })

  it('deletes portfolio when confirmed', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    api.delete.mockResolvedValue({ data: { success: true } })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Open delete confirmation
    const deleteButton = wrapper.find('[data-testid="delete-portfolio-button"]')
    await deleteButton.trigger('click')
    
    // Confirm deletion
    const confirmButton = wrapper.find('[data-testid="confirm-delete-button"]')
    await confirmButton.trigger('click')
    
    expect(api.delete).toHaveBeenCalledWith(
      `/api/portfolios/${mockApiResponses.portfolios[0].name}`
    )
  })

  it('navigates to portfolio detail when portfolio clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const portfolioCard = wrapper.find('[data-testid="portfolio-card"]')
    await portfolioCard.trigger('click')
    
    expect(wrapper.vm.$router.push).toHaveBeenCalledWith(
      `/portfolio/${mockApiResponses.portfolios[0].name}`
    )
  })

  it('filters portfolios by search query', async () => {
    const portfoliosData = [
      { name: 'growth-portfolio', strategy: 'growth' },
      { name: 'value-portfolio', strategy: 'value' },
      { name: 'momentum-portfolio', strategy: 'momentum' }
    ]
    
    api.get.mockResolvedValue({ data: portfoliosData })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Enter search query
    const searchInput = wrapper.find('[data-testid="portfolio-search"]')
    await searchInput.setValue('growth')
    
    // Should only show matching portfolios
    const visibleCards = wrapper.findAll('[data-testid="portfolio-card"]:not([style*="display: none"])')
    expect(visibleCards.length).toBe(1)
    expect(wrapper.text()).toContain('growth-portfolio')
  })

  it('filters portfolios by strategy', async () => {
    const portfoliosData = [
      { name: 'growth-1', strategy: 'growth' },
      { name: 'growth-2', strategy: 'growth' },
      { name: 'value-1', strategy: 'value' }
    ]
    
    api.get.mockResolvedValue({ data: portfoliosData })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Filter by growth strategy
    const strategyFilter = wrapper.find('[data-testid="strategy-filter"]')
    await strategyFilter.setValue('growth')
    
    const visibleCards = wrapper.findAll('[data-testid="portfolio-card"]:not([style*="display: none"])')
    expect(visibleCards.length).toBe(2)
  })

  it('sorts portfolios by different criteria', async () => {
    const portfoliosData = [
      { name: 'portfolio-c', total_value: 30000, last_updated: '2026-02-10T10:00:00Z' },
      { name: 'portfolio-a', total_value: 50000, last_updated: '2026-02-11T10:00:00Z' },
      { name: 'portfolio-b', total_value: 20000, last_updated: '2026-02-09T10:00:00Z' }
    ]
    
    api.get.mockResolvedValue({ data: portfoliosData })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Sort by value (descending)
    const sortSelect = wrapper.find('[data-testid="sort-select"]')
    await sortSelect.setValue('value-desc')
    
    const cards = wrapper.findAll('[data-testid="portfolio-card"]')
    expect(cards[0].text()).toContain('portfolio-a') // Highest value first
  })

  it('shows empty state when no portfolios exist', async () => {
    api.get.mockResolvedValue({ data: [] })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    expect(wrapper.findComponent({ name: 'EmptyState' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('No portfolios found')
    expect(wrapper.text()).toContain('Create your first portfolio')
  })

  it('handles API errors gracefully', async () => {
    api.get.mockRejectedValue(new Error('Failed to load portfolios'))
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('Failed to load portfolios')
    expect(wrapper.find('[data-testid="retry-button"]').exists()).toBe(true)
  })

  it('retries loading when retry button clicked', async () => {
    api.get
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Should show error state
    expect(wrapper.text()).toContain('Failed to load')
    
    // Click retry
    const retryButton = wrapper.find('[data-testid="retry-button"]')
    await retryButton.trigger('click')
    await flushPromises()
    
    // Should show portfolios
    expect(wrapper.findAll('[data-testid="portfolio-card"]').length).toBe(1)
  })

  it('shows portfolio performance indicators', async () => {
    const portfoliosData = [
      {
        name: 'test-portfolio',
        total_value: 45000,
        cash_balance: 10000,
        daily_pnl: 1250,
        daily_pnl_percent: 2.85
      }
    ]
    
    api.get.mockResolvedValue({ data: portfoliosData })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    expect(wrapper.text()).toContain('+$1,250')
    expect(wrapper.text()).toContain('+2.85%')
    expect(wrapper.find('.text-green-600').exists()).toBe(true) // Positive change color
  })

  it('supports bulk operations on selected portfolios', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    // Select portfolios
    const checkboxes = wrapper.findAll('[data-testid="portfolio-checkbox"]')
    await checkboxes[0].trigger('click')
    
    expect(wrapper.find('[data-testid="bulk-actions"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('1 selected')
  })

  it('applies responsive layout changes', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    const portfoliosGrid = wrapper.find('[data-testid="portfolios-grid"]')
    expect(portfoliosGrid.classes()).toContain('grid-cols-1')
    expect(portfoliosGrid.classes()).toContain('md:grid-cols-2')
    expect(portfoliosGrid.classes()).toContain('lg:grid-cols-3')
  })

  it('refreshes data when refresh button clicked', async () => {
    api.get.mockResolvedValue({ data: mockApiResponses.portfolios })
    
    const wrapper = mountComponent(PortfoliosPage)
    await flushPromises()
    
    api.get.mockClear()
    
    const refreshButton = wrapper.find('[data-testid="refresh-button"]')
    await refreshButton.trigger('click')
    
    expect(api.get).toHaveBeenCalledWith('/api/portfolios/')
  })
})