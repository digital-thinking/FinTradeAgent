<template>
  <!-- Loading skeleton -->
  <PageSkeleton v-if="delayedLoading" type="table" :contentBlocks="4" />
  
  <!-- Main content -->
  <div v-else class="space-y-6">
    <!-- Header -->
    <BaseCard>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="section-title">Analysis</p>
          <h3 class="font-display text-xl sm:text-2xl font-semibold text-text-primary">Portfolio Comparison</h3>
          <p class="mt-1 sm:mt-2 text-sm text-text-secondary">
            Compare performance, risk, and allocation across multiple portfolios
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <BaseButton variant="ghost" @click="refreshData" :disabled="loading" size="sm" class="sm:size-default">
            {{ loading ? 'Loading...' : 'Refresh' }}
          </BaseButton>
          <BaseButton @click="clearComparison" :disabled="selectedPortfolios.length === 0" size="sm" class="sm:size-default">
            Clear Selection
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- Portfolio Selection -->
    <BaseCard>
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-display text-xl font-semibold text-text-primary">Select Portfolios</h4>
        <div class="text-sm text-text-tertiary">
          {{ selectedPortfolios.length }} of {{ availablePortfolios.length }} selected
        </div>
      </div>

      <div v-if="loadingPortfolios" class="text-sm text-text-tertiary">Loading portfolios...</div>
      <div v-else-if="portfolioError" class="text-sm text-red-400">{{ portfolioError }}</div>
      <div v-else-if="availablePortfolios.length === 0">
        <EmptyState 
          title="No portfolios found"
          description="Create portfolios first to enable comparison functionality."
        />
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="portfolio in availablePortfolios"
          :key="portfolio.name"
          @click="togglePortfolio(portfolio)"
          :class="[
            'p-4 rounded-lg border-2 cursor-pointer transition-all',
            isSelected(portfolio.name)
              ? 'border-green-500 bg-green-900/20'
              : 'border-border bg-surface/50 hover:border-slate-600 hover:bg-surface/70'
          ]"
        >
          <div class="flex items-center justify-between">
            <div>
              <div class="font-medium text-text-primary">{{ portfolio.name }}</div>
              <div class="text-xs text-text-tertiary">{{ portfolio.description || 'No description' }}</div>
            </div>
            <div class="text-right">
              <div class="text-sm font-semibold text-green-400">
                {{ portfolio.metrics?.totalValue || '$0' }}
              </div>
              <div class="text-xs text-text-tertiary">
                {{ portfolio.metrics?.dailyPnL || '$0' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Comparison Results -->
    <div v-if="selectedPortfolios.length >= 2" class="space-y-6">
      <!-- Performance Charts -->
      <BaseCard>
        <h4 class="font-display text-xl font-semibold text-text-primary mb-4">Performance Comparison</h4>
        <div class="h-64">
          <LineChart 
            :data="performanceChartData" 
            :options="chartOptions"
          />
        </div>
      </BaseCard>

      <!-- Side-by-Side Metrics -->
      <BaseCard>
        <h4 class="font-display text-xl font-semibold text-text-primary mb-4">Key Metrics</h4>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border">
                <th class="text-left py-3 px-4 text-text-tertiary font-medium">Portfolio</th>
                <th class="text-right py-3 px-4 text-text-tertiary font-medium">Total Value</th>
                <th class="text-right py-3 px-4 text-text-tertiary font-medium">Daily P&L</th>
                <th class="text-right py-3 px-4 text-text-tertiary font-medium">Positions</th>
                <th class="text-right py-3 px-4 text-text-tertiary font-medium">Win Rate</th>
                <th class="text-right py-3 px-4 text-text-tertiary font-medium">Risk Level</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="portfolio in selectedPortfolios" 
                :key="portfolio.name"
                class="border-b border-border/50"
              >
                <td class="py-3 px-4">
                  <div class="font-medium text-text-primary">{{ portfolio.name }}</div>
                  <div class="text-xs text-text-tertiary">{{ portfolio.config?.strategy || 'Default' }}</div>
                </td>
                <td class="py-3 px-4 text-right font-semibold text-green-400">
                  {{ portfolio.metrics?.totalValue || '$0' }}
                </td>
                <td class="py-3 px-4 text-right" :class="getPnLColor(portfolio.metrics?.dailyPnL)">
                  {{ portfolio.metrics?.dailyPnL || '$0' }}
                </td>
                <td class="py-3 px-4 text-right text-text-secondary">
                  {{ portfolio.metrics?.positions || '0' }}
                </td>
                <td class="py-3 px-4 text-right text-text-secondary">
                  {{ portfolio.metrics?.winRate || '0%' }}
                </td>
                <td class="py-3 px-4 text-right">
                  <StatusBadge :status="portfolio.config?.riskLevel || 'medium'" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>

      <!-- Allocation Comparison -->
      <BaseCard>
        <h4 class="font-display text-xl font-semibold text-text-primary mb-4">Allocation Analysis</h4>
        <div class="grid gap-6 lg:grid-cols-2">
          <div
            v-for="portfolio in selectedPortfolios"
            :key="portfolio.name"
            class="space-y-3"
          >
            <div class="flex items-center justify-between">
              <h5 class="font-medium text-text-primary">{{ portfolio.name }}</h5>
              <div class="text-sm text-text-tertiary">
                {{ portfolio.metrics?.positions || 0 }} positions
              </div>
            </div>
            
            <div class="space-y-2">
              <div 
                v-for="(allocation, index) in getPortfolioAllocations(portfolio)" 
                :key="allocation.symbol"
                class="flex items-center justify-between p-2 bg-surface/50 rounded"
              >
                <div class="flex items-center gap-2">
                  <div 
                    class="w-3 h-3 rounded-full"
                    :style="{ backgroundColor: getColorForIndex(index) }"
                  ></div>
                  <span class="text-sm text-text-primary">{{ allocation.symbol }}</span>
                </div>
                <div class="text-right">
                  <div class="text-sm font-medium text-text-primary">{{ allocation.percentage }}%</div>
                  <div class="text-xs text-text-tertiary">${{ formatNumber(allocation.value) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </BaseCard>

      <!-- Performance Summary -->
      <BaseCard>
        <h4 class="font-display text-xl font-semibold text-text-primary mb-4">Performance Summary</h4>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="text-center p-4 bg-surface/50 rounded">
            <div class="text-2xl font-bold text-green-400">
              {{ getBestPerformer().name }}
            </div>
            <div class="text-sm text-text-tertiary">Best Performer</div>
            <div class="text-xs text-text-tertiary mt-1">
              {{ getBestPerformer().value }}
            </div>
          </div>
          <div class="text-center p-4 bg-surface/50 rounded">
            <div class="text-2xl font-bold text-blue-400">
              {{ getHighestValue().name }}
            </div>
            <div class="text-sm text-text-tertiary">Highest Value</div>
            <div class="text-xs text-text-tertiary mt-1">
              {{ getHighestValue().value }}
            </div>
          </div>
          <div class="text-center p-4 bg-surface/50 rounded">
            <div class="text-2xl font-bold text-purple-400">
              {{ getMostActive().name }}
            </div>
            <div class="text-sm text-text-tertiary">Most Active</div>
            <div class="text-xs text-text-tertiary mt-1">
              {{ getMostActive().value }}
            </div>
          </div>
          <div class="text-center p-4 bg-surface/50 rounded">
            <div class="text-2xl font-bold text-yellow-400">
              {{ getAverageReturn() }}
            </div>
            <div class="text-sm text-text-tertiary">Avg Daily Return</div>
            <div class="text-xs text-text-tertiary mt-1">
              Across {{ selectedPortfolios.length }} portfolios
            </div>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Empty State for No Selection -->
    <div v-else-if="!loadingPortfolios && availablePortfolios.length > 0">
      <EmptyState
        title="Select portfolios to compare"
        description="Choose 2 or more portfolios above to view detailed performance comparison and analytics."
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listPortfolios, getPortfolio, getDashboard } from '../services/api'
import { useDelayedLoading } from '../composables/useLoading'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import EmptyState from '../components/EmptyState.vue'
import LineChart from '../components/LineChart.vue'
import StatusBadge from '../components/StatusBadge.vue'
import PageSkeleton from '../components/skeletons/PageSkeleton.vue'

// State
const availablePortfolios = ref([])
const selectedPortfolios = ref([])
const loadingPortfolios = ref(true)
const loading = ref(false)
const portfolioError = ref(null)

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(300)

// Chart configuration
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index'
  },
  plugins: {
    legend: {
      labels: {
        color: '#e2e8f0'
      }
    }
  },
  scales: {
    x: {
      ticks: { color: '#94a3b8' },
      grid: { color: '#334155' }
    },
    y: {
      ticks: { color: '#94a3b8' },
      grid: { color: '#334155' }
    }
  }
}

// Computed
const performanceChartData = computed(() => {
  if (selectedPortfolios.value.length === 0) return { labels: [], datasets: [] }

  // Mock performance data - in real app this would come from API
  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
  const colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4']
  
  const datasets = selectedPortfolios.value.map((portfolio, index) => ({
    label: portfolio.name,
    data: generateMockPerformanceData(),
    borderColor: colors[index % colors.length],
    backgroundColor: colors[index % colors.length] + '20',
    fill: false,
    tension: 0.1
  }))

  return { labels, datasets }
})

// Methods
const loadPortfolios = async () => {
  loadingPortfolios.value = true
  startLoading()
  portfolioError.value = null
  
  try {
    const portfolios = await listPortfolios()
    if (!Array.isArray(portfolios)) {
      throw new Error('Expected array of portfolios')
    }
    
    // Load detailed data for each portfolio
    const detailedPortfolios = await Promise.all(
      portfolios.map(async (portfolio) => {
        try {
          const details = await getPortfolio(portfolio.name)
          return {
            ...portfolio,
            ...details,
            metrics: details.metrics || generateMockMetrics()
          }
        } catch (err) {
          return {
            ...portfolio,
            metrics: generateMockMetrics()
          }
        }
      })
    )
    
    availablePortfolios.value = detailedPortfolios
  } catch (err) {
    portfolioError.value = err.message || 'Failed to load portfolios'
  } finally {
    loadingPortfolios.value = false
    stopLoading()
  }
}

const refreshData = async () => {
  loading.value = true
  await loadPortfolios()
  loading.value = false
}

const togglePortfolio = (portfolio) => {
  const index = selectedPortfolios.value.findIndex(p => p.name === portfolio.name)
  if (index >= 0) {
    selectedPortfolios.value.splice(index, 1)
  } else {
    selectedPortfolios.value.push(portfolio)
  }
}

const isSelected = (portfolioName) => {
  return selectedPortfolios.value.some(p => p.name === portfolioName)
}

const clearComparison = () => {
  selectedPortfolios.value = []
}

const getPortfolioAllocations = (portfolio) => {
  // Mock allocation data - in real app this would come from portfolio details
  const mockAllocations = [
    { symbol: 'AAPL', percentage: 35, value: 15000 },
    { symbol: 'GOOGL', percentage: 25, value: 10000 },
    { symbol: 'MSFT', percentage: 20, value: 8000 },
    { symbol: 'TSLA', percentage: 15, value: 6000 },
    { symbol: 'AMZN', percentage: 5, value: 2000 }
  ]
  
  return mockAllocations.slice(0, Math.floor(Math.random() * 5) + 2)
}

const getPnLColor = (pnl) => {
  if (!pnl) return 'text-text-secondary'
  const value = parseFloat(pnl.replace(/[$,]/g, ''))
  return value >= 0 ? 'text-green-400' : 'text-red-400'
}

const getColorForIndex = (index) => {
  const colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4']
  return colors[index % colors.length]
}

const getBestPerformer = () => {
  if (selectedPortfolios.value.length === 0) return { name: '—', value: '' }
  
  const best = selectedPortfolios.value.reduce((prev, current) => {
    const prevValue = parseFloat((prev.metrics?.dailyPnL || '$0').replace(/[$,]/g, ''))
    const currentValue = parseFloat((current.metrics?.dailyPnL || '$0').replace(/[$,]/g, ''))
    return currentValue > prevValue ? current : prev
  })
  
  return { name: best.name, value: best.metrics?.dailyPnL || '$0' }
}

const getHighestValue = () => {
  if (selectedPortfolios.value.length === 0) return { name: '—', value: '' }
  
  const highest = selectedPortfolios.value.reduce((prev, current) => {
    const prevValue = parseFloat((prev.metrics?.totalValue || '$0').replace(/[$,]/g, ''))
    const currentValue = parseFloat((current.metrics?.totalValue || '$0').replace(/[$,]/g, ''))
    return currentValue > prevValue ? current : prev
  })
  
  return { name: highest.name, value: highest.metrics?.totalValue || '$0' }
}

const getMostActive = () => {
  if (selectedPortfolios.value.length === 0) return { name: '—', value: '' }
  
  const mostActive = selectedPortfolios.value.reduce((prev, current) => {
    const prevPositions = parseInt(prev.metrics?.positions || '0')
    const currentPositions = parseInt(current.metrics?.positions || '0')
    return currentPositions > prevPositions ? current : prev
  })
  
  return { 
    name: mostActive.name, 
    value: `${mostActive.metrics?.positions || '0'} positions` 
  }
}

const getAverageReturn = () => {
  if (selectedPortfolios.value.length === 0) return '$0'
  
  const total = selectedPortfolios.value.reduce((sum, portfolio) => {
    const value = parseFloat((portfolio.metrics?.dailyPnL || '$0').replace(/[$,]/g, ''))
    return sum + value
  }, 0)
  
  const average = total / selectedPortfolios.value.length
  return average >= 0 ? `+$${average.toFixed(2)}` : `-$${Math.abs(average).toFixed(2)}`
}

const formatNumber = (num) => {
  return Number(num).toLocaleString()
}

// Mock data generators (replace with real API data in production)
const generateMockMetrics = () => ({
  totalValue: `$${(Math.random() * 50000 + 10000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`,
  dailyPnL: Math.random() > 0.6 ? `+$${(Math.random() * 500 + 50).toFixed(2)}` : `-$${(Math.random() * 300 + 25).toFixed(2)}`,
  positions: Math.floor(Math.random() * 15) + 3,
  winRate: `${Math.floor(Math.random() * 40 + 50)}%`
})

const generateMockPerformanceData = () => {
  let value = 10000
  return Array.from({ length: 6 }, () => {
    value += (Math.random() - 0.4) * 1000
    return Math.round(value)
  })
}

// Lifecycle
onMounted(() => {
  loadPortfolios()
})
</script>

<style scoped>
.section-title {
  @apply text-xs font-medium uppercase tracking-wider text-text-tertiary;
}
</style>