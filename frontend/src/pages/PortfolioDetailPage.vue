<template>
  <div class="space-y-6">
    <!-- Portfolio Header -->
    <BaseCard>
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="section-title">Portfolio Detail</p>
          <h3 class="font-display text-2xl font-semibold text-text-primary">{{ name }}</h3>
          <p class="mt-2 text-sm text-text-secondary">{{ portfolio?.description || 'No description provided.' }}</p>
        </div>
        <div class="flex items-center gap-3">
          <ConnectionStatus 
            :state="portfolioWs.state.value"
            :error="portfolioWs.error.value"
            :reconnect-attempts="portfolioWs.reconnectAttempts.value"
            @reconnect="portfolioWs.connect"
            compact
          />
          <BaseButton variant="ghost" @click="refresh">Refresh</BaseButton>
          <BaseButton @click="executeAgent" :disabled="isExecuting">
            {{ isExecuting ? 'Executing...' : 'Execute Agent' }}
          </BaseButton>
        </div>
      </div>

      <!-- Enhanced Live Execution Progress -->
      <div v-if="isExecuting" class="mt-6">
        <ExecutionProgress 
          :execution="execution"
          @cancel="cancelCurrentExecution"
        />
      </div>

      <!-- Execution Status Messages -->
      <div v-if="executionMessage" class="mt-4 p-3 bg-green-900/50 border border-green-500/50 rounded text-green-200 text-sm">
        {{ executionMessage }}
      </div>
      <div v-if="executionError" class="mt-4 p-3 bg-red-900/50 border border-red-500/50 rounded text-red-200 text-sm">
        {{ executionError }}
      </div>
    </BaseCard>

    <!-- Loading State -->
    <div v-if="loading" class="text-sm text-text-tertiary">Loading portfolio...</div>
    <div v-else-if="error" class="text-sm text-red-400">{{ errorMessage }}</div>

    <!-- Main Content Tabs -->
    <div v-else>
      <!-- Tab Navigation -->
      <div class="border-b border-border mb-6">
        <nav class="flex space-x-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'py-2 px-1 border-b-2 font-medium text-sm',
              activeTab === tab.id
                ? 'border-green-500 text-green-400'
                : 'border-transparent text-text-tertiary hover:text-text-secondary hover:border-slate-600'
            ]"
          >
            {{ tab.label }}
            <span v-if="tab.badge" class="ml-2 px-2 py-0.5 bg-surface text-xs rounded-full">
              {{ tab.badge }}
            </span>
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Overview Tab -->
        <div v-show="activeTab === 'overview'" class="grid gap-6 lg:grid-cols-2">
          <BaseCard>
            <p class="section-title">Configuration</p>
            <h4 class="font-display text-xl font-semibold text-text-primary">Portfolio Settings</h4>
            <div class="mt-4 space-y-3">
              <div class="flex justify-between text-sm">
                <span class="text-text-tertiary">Strategy:</span>
                <span class="text-text-primary">{{ portfolio?.config?.strategy || 'Default' }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-text-tertiary">Risk Level:</span>
                <span class="text-text-primary">{{ portfolio?.config?.riskLevel || 'Medium' }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-text-tertiary">Max Position Size:</span>
                <span class="text-text-primary">{{ portfolio?.config?.maxPositionSize || '10%' }}</span>
              </div>
            </div>
            <details class="mt-6">
              <summary class="cursor-pointer text-sm text-text-secondary hover:text-text-primary">
                View Full Configuration
              </summary>
              <pre class="mt-3 p-3 bg-surface rounded text-xs text-text-secondary whitespace-pre-wrap">{{ configText }}</pre>
            </details>
          </BaseCard>

          <BaseCard>
            <p class="section-title">Performance</p>
            <h4 class="font-display text-xl font-semibold text-text-primary">Portfolio Metrics</h4>
            <div class="mt-4 grid grid-cols-2 gap-4">
              <div class="text-center p-3 bg-surface rounded">
                <div class="text-2xl font-bold text-green-400">{{ portfolio?.metrics?.totalValue || '$0' }}</div>
                <div class="text-xs text-text-tertiary">Total Value</div>
              </div>
              <div class="text-center p-3 bg-surface rounded">
                <div class="text-2xl font-bold text-text-primary">{{ portfolio?.metrics?.positions || '0' }}</div>
                <div class="text-xs text-text-tertiary">Positions</div>
              </div>
              <div class="text-center p-3 bg-surface rounded">
                <div class="text-2xl font-bold text-blue-400">{{ portfolio?.metrics?.dailyPnL || '$0' }}</div>
                <div class="text-xs text-text-tertiary">Daily P&L</div>
              </div>
              <div class="text-center p-3 bg-surface rounded">
                <div class="text-2xl font-bold text-purple-400">{{ portfolio?.metrics?.winRate || '0%' }}</div>
                <div class="text-xs text-text-tertiary">Win Rate</div>
              </div>
            </div>
          </BaseCard>
        </div>

        <!-- Trades Tab -->
        <div v-show="activeTab === 'trades'">
          <BaseCard>
            <p class="section-title">Trade Recommendations</p>
            <h4 class="font-display text-xl font-semibold text-text-primary">Pending Recommendations</h4>
            
            <div v-if="loadingTrades" class="mt-4 text-sm text-text-tertiary">Loading trades...</div>
            <div v-else-if="pendingTrades.length === 0" class="mt-4">
              <EmptyState 
                title="No Pending Trades"
                description="Execute the agent to generate new trade recommendations."
              />
            </div>
            <div v-else class="mt-4 space-y-3">
              <div 
                v-for="trade in pendingTrades" 
                :key="trade.id"
                class="p-4 bg-surface rounded-lg border border-border"
              >
                <div class="flex items-start justify-between">
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-text-primary">{{ trade.symbol }}</span>
                      <StatusBadge :status="trade.action" />
                      <span class="text-sm text-text-tertiary">{{ trade.quantity }} shares</span>
                    </div>
                    <div class="mt-1 text-sm text-text-secondary">
                      Price: ${{ trade.price }} • Est. Total: ${{ (trade.price * trade.quantity).toFixed(2) }}
                    </div>
                    <div class="mt-1 text-xs text-text-tertiary">
                      Confidence: {{ trade.confidence }}% • Reason: {{ trade.reason }}
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <BaseButton 
                      size="sm" 
                      variant="ghost" 
                      @click="applyTrade(trade.id)"
                      :disabled="trade.applying"
                    >
                      {{ trade.applying ? 'Applying...' : 'Apply' }}
                    </BaseButton>
                    <BaseButton 
                      size="sm" 
                      variant="danger" 
                      @click="rejectTrade(trade.id)"
                      :disabled="trade.applying"
                    >
                      Reject
                    </BaseButton>
                  </div>
                </div>
              </div>
            </div>
          </BaseCard>
        </div>

        <!-- History Tab -->
        <div v-show="activeTab === 'history'">
          <BaseCard>
            <p class="section-title">Execution History</p>
            <h4 class="font-display text-xl font-semibold text-text-primary">Past Executions</h4>
            
            <div v-if="loadingHistory" class="mt-4 text-sm text-text-tertiary">Loading history...</div>
            <div v-else-if="executionHistory.length === 0" class="mt-4">
              <EmptyState 
                title="No Execution History"
                description="Agent executions will appear here after your first run."
              />
            </div>
            <div v-else class="mt-4 space-y-3">
              <div 
                v-for="execution in executionHistory" 
                :key="execution.id"
                class="p-4 bg-surface rounded-lg border border-border"
              >
                <div class="flex items-start justify-between">
                  <div>
                    <div class="flex items-center gap-2">
                      <StatusBadge :status="execution.status" />
                      <span class="text-sm text-text-tertiary">{{ formatDate(execution.timestamp) }}</span>
                    </div>
                    <div class="mt-1 text-sm text-text-primary">
                      Duration: {{ execution.duration }}s • Trades Generated: {{ execution.tradesGenerated || 0 }}
                    </div>
                    <div v-if="execution.error" class="mt-1 text-xs text-red-400">
                      Error: {{ execution.error }}
                    </div>
                  </div>
                  <BaseButton 
                    size="sm" 
                    variant="ghost" 
                    @click="viewExecutionDetails(execution)"
                  >
                    View Details
                  </BaseButton>
                </div>
              </div>
            </div>
          </BaseCard>
        </div>

        <!-- Scheduling Tab -->
        <div v-show="activeTab === 'scheduling'">
          <BaseCard>
            <p class="section-title">Automated Scheduling</p>
            <h4 class="font-display text-xl font-semibold text-text-primary">Execution Schedule</h4>
            
            <div class="mt-4 space-y-4">
              <div class="p-4 bg-surface rounded-lg">
                <div class="flex items-center justify-between">
                  <div>
                    <h5 class="font-medium text-text-primary">Auto-execution</h5>
                    <p class="text-sm text-text-tertiary">Automatically run agent at scheduled intervals</p>
                  </div>
                  <div class="flex items-center gap-3">
                    <select 
                      v-model="schedulingConfig.frequency"
                      class="bg-surface border border-slate-600 rounded px-3 py-1 text-sm text-text-primary"
                      :disabled="schedulingConfig.enabled"
                    >
                      <option value="never">Never</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <BaseButton 
                      size="sm"
                      @click="toggleScheduling"
                      :variant="schedulingConfig.enabled ? 'danger' : 'primary'"
                    >
                      {{ schedulingConfig.enabled ? 'Disable' : 'Enable' }}
                    </BaseButton>
                  </div>
                </div>
                
                <div v-if="schedulingConfig.frequency !== 'never'" class="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs text-text-tertiary mb-1">Time</label>
                    <input 
                      v-model="schedulingConfig.time"
                      type="time"
                      class="w-full bg-surface border border-slate-600 rounded px-3 py-1 text-sm text-text-primary"
                      :disabled="schedulingConfig.enabled"
                    />
                  </div>
                  <div v-if="schedulingConfig.frequency === 'weekly'">
                    <label class="block text-xs text-text-tertiary mb-1">Day of Week</label>
                    <select 
                      v-model="schedulingConfig.dayOfWeek"
                      class="w-full bg-surface border border-slate-600 rounded px-3 py-1 text-sm text-text-primary"
                      :disabled="schedulingConfig.enabled"
                    >
                      <option value="1">Monday</option>
                      <option value="2">Tuesday</option>
                      <option value="3">Wednesday</option>
                      <option value="4">Thursday</option>
                      <option value="5">Friday</option>
                      <option value="6">Saturday</option>
                      <option value="0">Sunday</option>
                    </select>
                  </div>
                </div>

                <div v-if="schedulingConfig.enabled" class="mt-3 p-3 bg-green-900/30 border border-green-500/30 rounded text-sm text-green-200">
                  ✓ Auto-execution enabled - Next run: {{ nextRunTime }}
                </div>
              </div>
            </div>
          </BaseCard>
        </div>
      </div>
    </div>

    <!-- Execution Details Modal -->
    <BaseModal v-if="selectedExecution" @close="selectedExecution = null">
      <template #header>
        Execution Details - {{ formatDate(selectedExecution.timestamp) }}
      </template>
      <template #content>
        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-text-tertiary">Status:</span>
              <StatusBadge :status="selectedExecution.status" class="ml-2" />
            </div>
            <div>
              <span class="text-text-tertiary">Duration:</span>
              <span class="ml-2 text-text-primary">{{ selectedExecution.duration }}s</span>
            </div>
            <div>
              <span class="text-text-tertiary">Trades Generated:</span>
              <span class="ml-2 text-text-primary">{{ selectedExecution.tradesGenerated || 0 }}</span>
            </div>
            <div>
              <span class="text-text-tertiary">Model Used:</span>
              <span class="ml-2 text-text-primary">{{ selectedExecution.model || 'Unknown' }}</span>
            </div>
          </div>
          
          <div v-if="selectedExecution.logs">
            <h4 class="font-medium text-text-primary mb-2">Execution Logs</h4>
            <pre class="p-3 bg-surface rounded text-xs text-text-secondary max-h-64 overflow-y-auto whitespace-pre-wrap">{{ selectedExecution.logs }}</pre>
          </div>
          
          <div v-if="selectedExecution.error">
            <h4 class="font-medium text-red-400 mb-2">Error Details</h4>
            <pre class="p-3 bg-red-900/20 border border-red-500/30 rounded text-xs text-red-200 whitespace-pre-wrap">{{ selectedExecution.error }}</pre>
          </div>
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { 
  getPortfolio, 
  executeAgent as apiExecuteAgent, 
  cancelExecution as apiCancelExecution,
  getPendingTrades, 
  applyTrade as apiApplyTrade, 
  cancelTrade as apiCancelTrade,
  getExecutionLogs
} from '../services/api'
import { usePortfolioWebSocket } from '../composables/useWebSocket'
import { useExecutionStore } from '../stores/executionStore'
import { useErrorHandler } from '../composables/useErrorHandler'
import { useToast } from '../composables/useToast'
import { useDelayedLoading } from '../composables/useLoading'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseModal from '../components/BaseModal.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EmptyState from '../components/EmptyState.vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import ExecutionProgress from '../components/ExecutionProgress.vue'
import PageSkeleton from '../components/skeletons/PageSkeleton.vue'
import TableSkeleton from '../components/skeletons/TableSkeleton.vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  }
})

// State
const portfolio = ref(null)
const loading = ref(true)
const error = ref(null)
const activeTab = ref('overview')

// Execution store
const executionStore = useExecutionStore()

// Execution state (computed from store)
const execution = executionStore.getExecution(props.name)
const isExecuting = executionStore.isExecuting(props.name)
const executionMessage = ref('')
const executionError = ref('')

// Trades state
const pendingTrades = ref([])
const loadingTrades = ref(false)

// History state
const executionHistory = ref([])
const loadingHistory = ref(false)
const selectedExecution = ref(null)

// Scheduling state
const schedulingConfig = ref({
  enabled: false,
  frequency: 'never',
  time: '09:00',
  dayOfWeek: '1'
})

// WebSocket integration
const portfolioWs = usePortfolioWebSocket(props.name)

// Error handling and notifications
const { handleApiError, retry } = useErrorHandler()
const { success: showSuccess, error: showError } = useToast()

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(300)

// Computed
const errorMessage = computed(() => error.value?.message || 'Unable to load portfolio.')
const configText = computed(() => JSON.stringify(portfolio.value?.config || {}, null, 2))

const tabs = computed(() => [
  { id: 'overview', label: 'Overview' },
  { id: 'trades', label: 'Trades', badge: pendingTrades.value.length || null },
  { id: 'history', label: 'History', badge: executionHistory.value.length || null },
  { id: 'scheduling', label: 'Scheduling' }
])

const nextRunTime = computed(() => {
  if (!schedulingConfig.value.enabled || schedulingConfig.value.frequency === 'never') return 'N/A'
  
  const now = new Date()
  const [hours, minutes] = schedulingConfig.value.time.split(':')
  const nextRun = new Date()
  nextRun.setHours(parseInt(hours), parseInt(minutes), 0, 0)
  
  if (nextRun <= now) {
    nextRun.setDate(nextRun.getDate() + 1)
  }
  
  return nextRun.toLocaleString()
})

// Methods
const loadPortfolio = async () => {
  loading.value = true
  startLoading()
  error.value = null
  try {
    const data = await getPortfolio(props.name)
    if (!data || typeof data !== 'object') {
      throw new Error('Portfolio response must be an object.')
    }
    portfolio.value = data
  } catch (err) {
    error.value = err
    handleApiError(err, 'loading portfolio')
  } finally {
    loading.value = false
    stopLoading()
  }
}

const loadPendingTrades = async () => {
  loadingTrades.value = true
  try {
    const trades = await getPendingTrades()
    // Filter trades for this portfolio
    pendingTrades.value = trades.filter(trade => trade.portfolio === props.name)
  } catch (err) {
    console.error('Failed to load pending trades:', err)
    handleApiError(err, 'loading pending trades')
  } finally {
    loadingTrades.value = false
  }
}

const loadExecutionHistory = async () => {
  loadingHistory.value = true
  try {
    const logs = await getExecutionLogs(props.name)
    executionHistory.value = logs.slice(0, 20) // Limit to recent 20
  } catch (err) {
    console.error('Failed to load execution history:', err)
    handleApiError(err, 'loading execution history')
  } finally {
    loadingHistory.value = false
  }
}

const refresh = () => {
  loadPortfolio()
  if (activeTab.value === 'trades') loadPendingTrades()
  if (activeTab.value === 'history') loadExecutionHistory()
}

const executeAgent = async () => {
  executionMessage.value = ''
  executionError.value = ''
  
  try {
    // Start execution in store
    const executionState = executionStore.startExecution(props.name)
    
    // Ensure WebSocket is connected
    if (!portfolioWs.isConnected()) {
      portfolioWs.connect()
    }
    
    // Start execution via API with retry capability
    const result = await retry(
      () => apiExecuteAgent(props.name),
      3, // Max 3 attempts
      1000 // 1 second initial delay
    )
    
    // Update execution ID if provided by API
    if (result.executionId) {
      executionState.id = result.executionId
    }
    
    executionMessage.value = 'Agent execution started. Monitoring progress...'
    showSuccess('Agent execution started successfully')
  } catch (err) {
    executionError.value = err?.message || 'Unable to execute agent.'
    executionStore.failExecution(props.name, err?.message || 'Execution failed')
    handleApiError(err, 'starting agent execution')
  }
}

const cancelCurrentExecution = async () => {
  try {
    const currentExecution = execution.value
    if (currentExecution.id) {
      await apiCancelExecution(props.name, currentExecution.id)
      showSuccess('Execution cancelled successfully')
    }
    executionStore.cancelExecution(props.name)
    executionMessage.value = 'Execution cancelled.'
  } catch (err) {
    executionError.value = err?.message || 'Failed to cancel execution.'
    handleApiError(err, 'cancelling execution')
  }
}

const applyTrade = async (tradeId) => {
  const trade = pendingTrades.value.find(t => t.id === tradeId)
  if (!trade) return
  
  trade.applying = true
  try {
    await apiApplyTrade(tradeId)
    // Remove from pending trades
    pendingTrades.value = pendingTrades.value.filter(t => t.id !== tradeId)
    // Refresh history
    loadExecutionHistory()
    showSuccess(`Trade ${trade.symbol} applied successfully`)
  } catch (err) {
    console.error('Failed to apply trade:', err)
    handleApiError(err, `applying trade ${trade.symbol}`)
  } finally {
    trade.applying = false
  }
}

const rejectTrade = async (tradeId) => {
  const trade = pendingTrades.value.find(t => t.id === tradeId)
  if (!trade) return
  
  trade.applying = true
  try {
    await apiCancelTrade(tradeId)
    // Remove from pending trades
    pendingTrades.value = pendingTrades.value.filter(t => t.id !== tradeId)
    showSuccess(`Trade ${trade.symbol} rejected`)
  } catch (err) {
    console.error('Failed to reject trade:', err)
    handleApiError(err, `rejecting trade ${trade.symbol}`)
  } finally {
    trade.applying = false
  }
}

const viewExecutionDetails = (execution) => {
  selectedExecution.value = execution
}

const toggleScheduling = () => {
  schedulingConfig.value.enabled = !schedulingConfig.value.enabled
  // In a real implementation, this would save to backend
  console.log('Scheduling toggled:', schedulingConfig.value)
}

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

const formatDate = (date) => {
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Watch tab changes to load data
watch(activeTab, (newTab) => {
  if (newTab === 'trades' && pendingTrades.value.length === 0) {
    loadPendingTrades()
  } else if (newTab === 'history' && executionHistory.value.length === 0) {
    loadExecutionHistory()
  }
})

// Enhanced WebSocket event handlers for real-time execution progress
portfolioWs.on('execution_started', (data) => {
  executionStore.startExecution(props.name, data.executionId)
})

portfolioWs.on('execution_step', (data) => {
  executionStore.updateExecutionStep(props.name, data.step, data.stepProgress, data.overallProgress)
})

portfolioWs.on('execution_progress', (data) => {
  executionStore.updateExecutionStep(props.name, data.currentStep, data.stepProgress, data.overallProgress)
})

portfolioWs.on('execution_estimate', (data) => {
  executionStore.updateTimeEstimate(props.name, data.estimatedMs)
})

portfolioWs.on('execution_message', (data) => {
  executionStore.addExecutionMessage(props.name, data.message)
})

portfolioWs.on('execution_complete', (data) => {
  executionStore.completeExecution(props.name)
  executionMessage.value = 'Agent execution completed successfully.'
  // Refresh trades and history
  loadPendingTrades()
  loadExecutionHistory()
})

portfolioWs.on('execution_cancelled', (data) => {
  executionStore.cancelExecution(props.name)
  executionMessage.value = 'Execution was cancelled.'
})

portfolioWs.on('execution_error', (data) => {
  executionStore.failExecution(props.name, data.error || 'Execution failed')
  executionError.value = data.error || 'Execution failed.'
})

// Legacy WebSocket handlers (fallback)
portfolioWs.on('progress', (data) => {
  executionStore.updateExecutionStep(props.name, execution.value.currentStep, data.progress)
})

portfolioWs.on('message', (data) => {
  executionStore.addExecutionMessage(props.name, data.message)
})

portfolioWs.on('complete', (data) => {
  executionStore.completeExecution(props.name)
  executionMessage.value = 'Agent execution completed successfully.'
  loadPendingTrades()
  loadExecutionHistory()
})

portfolioWs.on('error', (data) => {
  executionStore.failExecution(props.name, data.error || 'Execution failed')
  executionError.value = data.error || 'Execution failed.'
})

portfolioWs.on('portfolio_update', (data) => {
  // Live portfolio metrics updates
  if (portfolio.value && data.portfolio === props.name) {
    portfolio.value.metrics = { ...portfolio.value.metrics, ...data.metrics }
  }
})

portfolioWs.on('trade_update', (data) => {
  // Live trade updates
  if (data.portfolio === props.name) {
    loadPendingTrades() // Refresh trades when updates occur
  }
})

// Lifecycle
onMounted(() => {
  loadPortfolio()
  
  // Try to restore any persisted execution state
  executionStore.restoreExecution(props.name)
})

onUnmounted(() => {
  // WebSocket cleanup handled by composable
})
</script>

<style scoped>
.section-title {
  @apply text-xs font-medium uppercase tracking-wider text-text-tertiary;
}
</style>