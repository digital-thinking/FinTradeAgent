<template>
  <!-- Loading skeleton -->
  <PageSkeleton v-if="delayedLoading" type="table" :tableRows="8" :tableColumns="[
    { key: 'symbol', width: '100%', subtitle: true },
    { key: 'action', type: 'badge' },
    { key: 'quantity', type: 'number' },
    { key: 'price', type: 'number' },
    { key: 'total', type: 'number' },
    { key: 'portfolio', type: 'text' },
    { key: 'confidence', type: 'number' },
    { key: 'created', type: 'text', width: '120px' },
    { key: 'actions', type: 'button' }
  ]" />
  
  <!-- Main content -->
  <div v-else class="space-y-6">
    <!-- Header -->
    <BaseCard>
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="section-title">Trades</p>
          <h3 class="font-display text-xl sm:text-2xl font-semibold text-text-primary">Pending Trades</h3>
          <p class="mt-1 sm:mt-2 text-sm text-text-secondary">
            Review and manage trade recommendations from agent executions
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <ConnectionStatus 
            :state="tradesWs.state.value"
            :error="tradesWs.error.value"
            :reconnect-attempts="tradesWs.reconnectAttempts.value"
            @reconnect="tradesWs.connect"
            compact
          />
          <BaseButton variant="ghost" @click="fetchTrades" :disabled="loading" size="sm" class="sm:size-default">
            {{ loading ? 'Loading...' : 'Refresh' }}
          </BaseButton>
          <BaseButton @click="applyAllTrades" :disabled="loading || trades.length === 0" size="sm" class="sm:size-default">
            Apply All
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- Loading State -->
    <div v-if="loading" class="text-sm text-text-tertiary">Loading pending trades...</div>
    
    <!-- Error State -->
    <div v-else-if="error" class="p-4 bg-red-900/50 border border-red-500/50 rounded text-red-200 text-sm">
      {{ errorMessage }}
    </div>
    
    <!-- Empty State -->
    <div v-else-if="trades.length === 0">
      <EmptyState
        title="No pending trades"
        description="Trades appear here after agent execution. Execute agents from portfolio detail pages to generate new recommendations."
      />
    </div>
    
    <!-- Trades Content -->
    <section v-else>
      <!-- Mobile Card Layout -->
      <div class="block lg:hidden space-y-4">
        <BaseCard v-for="trade in trades" :key="trade.id" class="space-y-4">
          <!-- Trade Header -->
          <div class="flex items-start justify-between">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-3">
                <h4 class="font-semibold text-text-primary">{{ trade.symbol }}</h4>
                <StatusBadge 
                  :status="trade.action" 
                  :variant="trade.action === 'sell' ? 'danger' : 'success'" 
                />
              </div>
              <p class="text-xs text-text-tertiary mt-1">{{ trade.name || 'Unknown Company' }}</p>
              <p class="text-xs text-text-tertiary mt-1">{{ trade.portfolio }}</p>
            </div>
          </div>
          
          <!-- Trade Metrics -->
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-text-tertiary text-xs block">Quantity</span>
              <span class="text-text-primary font-medium">{{ formatNumber(trade.quantity) }}</span>
            </div>
            <div>
              <span class="text-text-tertiary text-xs block">Price</span>
              <span class="text-text-primary font-medium">${{ formatNumber(trade.price, 2) }}</span>
            </div>
            <div>
              <span class="text-text-tertiary text-xs block">Total Value</span>
              <span class="text-text-primary font-medium">${{ formatNumber(trade.price * trade.quantity, 2) }}</span>
            </div>
            <div>
              <span class="text-text-tertiary text-xs block">Created</span>
              <span class="text-text-secondary text-xs">{{ formatDate(trade.created_at) }}</span>
            </div>
          </div>

          <!-- Confidence Bar -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-text-tertiary text-xs">Confidence</span>
              <span class="text-text-primary text-sm font-medium">{{ trade.confidence }}%</span>
            </div>
            <div class="w-full h-2 bg-surface rounded-full overflow-hidden">
              <div 
                class="h-full rounded-full transition-all"
                :class="getConfidenceColor(trade.confidence)"
                :style="{ width: trade.confidence + '%' }"
              ></div>
            </div>
          </div>

          <!-- Mobile Actions -->
          <div class="flex flex-wrap gap-2 pt-2 border-t border-border/60">
            <BaseButton 
              size="sm"
              variant="ghost"
              @click="viewTradeDetails(trade)"
              class="flex-1 min-w-0"
            >
              Details
            </BaseButton>
            <BaseButton 
              size="sm" 
              variant="success"
              @click="applyTrade(trade.id)"
              :disabled="trade.applying"
              class="flex-1 min-w-0"
            >
              {{ trade.applying ? 'Applying...' : 'Apply' }}
            </BaseButton>
            <BaseButton 
              size="sm" 
              variant="danger"
              @click="cancelTrade(trade.id)"
              :disabled="trade.applying"
              class="flex-1 min-w-0"
            >
              Cancel
            </BaseButton>
          </div>
        </BaseCard>
      </div>

      <!-- Desktop Table Layout -->
      <BaseCard class="hidden lg:block">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="border-b border-border">
              <tr class="text-xs uppercase tracking-[0.2em] text-text-tertiary">
                <th class="px-4 py-3">Symbol</th>
                <th class="px-4 py-3">Action</th>
                <th class="px-4 py-3">Quantity</th>
                <th class="px-4 py-3">Price</th>
                <th class="px-4 py-3">Total</th>
                <th class="px-4 py-3">Portfolio</th>
                <th class="px-4 py-3">Confidence</th>
                <th class="px-4 py-3">Created</th>
                <th class="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700/50">
              <tr 
                v-for="trade in trades" 
                :key="trade.id"
                class="hover:bg-surface/30 transition-colors"
              >
                <td class="px-4 py-4">
                  <div class="font-semibold text-text-primary">{{ trade.symbol }}</div>
                  <div class="text-xs text-text-tertiary">{{ trade.name || 'Unknown' }}</div>
                </td>
                <td class="px-4 py-4">
                  <StatusBadge 
                    :status="trade.action" 
                    :variant="trade.action === 'sell' ? 'danger' : 'success'" 
                  />
                </td>
                <td class="px-4 py-4 text-text-secondary">
                  {{ formatNumber(trade.quantity) }}
                </td>
                <td class="px-4 py-4 text-text-secondary">
                  ${{ formatNumber(trade.price, 2) }}
                </td>
                <td class="px-4 py-4 text-text-secondary">
                  ${{ formatNumber(trade.price * trade.quantity, 2) }}
                </td>
                <td class="px-4 py-4 text-text-secondary">{{ trade.portfolio }}</td>
                <td class="px-4 py-4">
                  <div class="flex items-center gap-2">
                    <div class="text-text-secondary">{{ trade.confidence }}%</div>
                    <div 
                      class="w-12 h-1.5 bg-surface rounded-full overflow-hidden"
                      :title="trade.confidence + '% confidence'"
                    >
                      <div 
                        class="h-full rounded-full transition-all"
                        :class="getConfidenceColor(trade.confidence)"
                        :style="{ width: trade.confidence + '%' }"
                      ></div>
                    </div>
                  </div>
                </td>
                <td class="px-4 py-4 text-text-tertiary text-xs">
                  {{ formatDate(trade.created_at) }}
                </td>
                <td class="px-4 py-4">
                  <div class="flex items-center gap-2">
                    <BaseButton 
                      size="sm"
                      @click="viewTradeDetails(trade)"
                    >
                      Details
                    </BaseButton>
                    <BaseButton 
                      size="sm" 
                      variant="success"
                      @click="applyTrade(trade.id)"
                      :disabled="trade.applying"
                    >
                      {{ trade.applying ? 'Applying...' : 'Apply' }}
                    </BaseButton>
                    <BaseButton 
                      size="sm" 
                      variant="danger"
                      @click="cancelTrade(trade.id)"
                      :disabled="trade.applying"
                    >
                      Cancel
                    </BaseButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>
    </section>

    <!-- Trade Details Modal -->
    <BaseModal 
      v-if="selectedTrade" 
      :open="!!selectedTrade"
      :title="`Trade Details - ${selectedTrade.symbol}`"
      @close="selectedTrade = null"
    >
      <div class="space-y-4 sm:space-y-6">
        <!-- Trade Overview -->
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Symbol</label>
              <div class="text-lg font-semibold text-text-primary">{{ selectedTrade.symbol }}</div>
              <div class="text-sm text-text-tertiary">{{ selectedTrade.name || 'Unknown Company' }}</div>
            </div>
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Quantity</label>
              <div class="text-text-primary">{{ formatNumber(selectedTrade.quantity) }} shares</div>
            </div>
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Total Value</label>
              <div class="text-lg font-semibold text-text-primary">
                ${{ formatNumber(selectedTrade.price * selectedTrade.quantity, 2) }}
              </div>
            </div>
          </div>
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Action</label>
              <StatusBadge 
                :status="selectedTrade.action" 
                :variant="selectedTrade.action === 'sell' ? 'danger' : 'success'"
                class="inline-block"
              />
            </div>
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Price</label>
              <div class="text-text-primary">${{ formatNumber(selectedTrade.price, 2) }}</div>
            </div>
            <div>
              <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Portfolio</label>
              <div class="text-text-primary">{{ selectedTrade.portfolio }}</div>
            </div>
          </div>
        </div>

        <!-- Analysis Section -->
        <div>
          <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-3">Analysis</label>
          <div class="space-y-3">
            <!-- Confidence -->
            <div class="glass p-3 sm:p-4 rounded-xl">
              <div class="flex items-center justify-between mb-2">
                <span class="text-text-secondary text-sm">Confidence</span>
                <span class="text-text-primary font-medium">{{ selectedTrade.confidence }}%</span>
              </div>
              <div class="w-full h-2 bg-surface rounded-full overflow-hidden">
                <div 
                  class="h-full rounded-full transition-all"
                  :class="getConfidenceColor(selectedTrade.confidence)"
                  :style="{ width: selectedTrade.confidence + '%' }"
                ></div>
              </div>
            </div>
            
            <!-- Risk & Model -->
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="glass p-3 rounded-xl">
                <span class="text-text-tertiary text-xs block mb-1">Risk Level</span>
                <StatusBadge :status="selectedTrade.risk_level || 'medium'" />
              </div>
              <div class="glass p-3 rounded-xl">
                <span class="text-text-tertiary text-xs block mb-1">Model Used</span>
                <span class="text-text-primary text-sm">{{ selectedTrade.model || 'Unknown' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Reasoning -->
        <div v-if="selectedTrade.reason">
          <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Reasoning</label>
          <div class="glass p-3 sm:p-4 rounded-xl text-sm text-text-secondary leading-relaxed break-words">
            {{ selectedTrade.reason }}
          </div>
        </div>

        <!-- Technical Analysis -->
        <div v-if="selectedTrade.technical_analysis">
          <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-2">Technical Analysis</label>
          <div class="glass p-3 sm:p-4 rounded-xl text-sm text-text-secondary leading-relaxed whitespace-pre-line break-words">
            {{ selectedTrade.technical_analysis }}
          </div>
        </div>

        <!-- Timestamps -->
        <div class="grid gap-4 sm:grid-cols-2 pt-4 border-t border-border/60">
          <div>
            <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-1">Created</label>
            <div class="text-sm text-text-secondary">{{ formatDateTime(selectedTrade.created_at) }}</div>
          </div>
          <div v-if="selectedTrade.expires_at">
            <label class="block text-xs font-medium uppercase tracking-wide text-text-tertiary mb-1">Expires</label>
            <div class="text-sm text-text-secondary">{{ formatDateTime(selectedTrade.expires_at) }}</div>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="flex flex-col gap-3 pt-4 sm:flex-row sm:justify-end border-t border-border/60">
          <BaseButton variant="ghost" @click="selectedTrade = null" class="sm:order-1">
            Close
          </BaseButton>
          <BaseButton 
            variant="danger"
            @click="cancelTradeFromModal"
            :disabled="selectedTrade.applying"
            class="sm:order-2"
          >
            Cancel Trade
          </BaseButton>
          <BaseButton 
            @click="applyTradeFromModal"
            :disabled="selectedTrade.applying"
            class="sm:order-3"
          >
            {{ selectedTrade.applying ? 'Applying...' : 'Apply Trade' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { 
  getPendingTrades, 
  applyTrade as apiApplyTrade, 
  cancelTrade as apiCancelTrade 
} from '../services/api'
import { useTradesWebSocket } from '../composables/useWebSocket'
import { useDelayedLoading } from '../composables/useLoading'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import PageSkeleton from '../components/skeletons/PageSkeleton.vue'

// State
const trades = ref([])
const loading = ref(true)
const error = ref(null)
const selectedTrade = ref(null)

// WebSocket integration
const tradesWs = useTradesWebSocket()

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(300)

// Computed
const errorMessage = computed(() => error.value?.message || 'Unable to load trades.')

// Methods
const fetchTrades = async () => {
  loading.value = true
  startLoading()
  error.value = null
  try {
    const data = await getPendingTrades()
    if (!Array.isArray(data)) {
      throw new Error('Trades response must be an array.')
    }
    // Add reactive properties for UI state
    trades.value = data.map(trade => ({
      ...trade,
      applying: false
    }))
  } catch (err) {
    error.value = err
  } finally {
    loading.value = false
    stopLoading()
  }
}

const applyTrade = async (tradeId) => {
  const trade = trades.value.find(t => t.id === tradeId)
  if (!trade) return
  
  trade.applying = true
  try {
    await apiApplyTrade(tradeId)
    // Remove trade from list after successful application
    trades.value = trades.value.filter(t => t.id !== tradeId)
    
    // Show success message (could be enhanced with toast notifications)
    console.log('Trade applied successfully:', tradeId)
  } catch (err) {
    console.error('Failed to apply trade:', err)
    error.value = err
  } finally {
    trade.applying = false
  }
}

const cancelTrade = async (tradeId) => {
  const trade = trades.value.find(t => t.id === tradeId)
  if (!trade) return
  
  trade.applying = true
  try {
    await apiCancelTrade(tradeId)
    // Remove trade from list after successful cancellation
    trades.value = trades.value.filter(t => t.id !== tradeId)
    
    console.log('Trade cancelled successfully:', tradeId)
  } catch (err) {
    console.error('Failed to cancel trade:', err)
    error.value = err
  } finally {
    trade.applying = false
  }
}

const applyAllTrades = async () => {
  if (trades.value.length === 0) return
  
  const confirmMessage = `Apply all ${trades.value.length} pending trades?`
  if (!confirm(confirmMessage)) return
  
  // Apply trades sequentially to avoid overwhelming the API
  for (const trade of trades.value) {
    try {
      await applyTrade(trade.id)
    } catch (err) {
      console.error('Failed to apply trade in bulk:', trade.id, err)
      // Continue with other trades even if one fails
    }
  }
}

const viewTradeDetails = (trade) => {
  selectedTrade.value = { ...trade }
}

const applyTradeFromModal = async () => {
  if (!selectedTrade.value) return
  
  await applyTrade(selectedTrade.value.id)
  selectedTrade.value = null
}

const cancelTradeFromModal = async () => {
  if (!selectedTrade.value) return
  
  await cancelTrade(selectedTrade.value.id)
  selectedTrade.value = null
}

// Utility functions
const formatNumber = (num, decimals = 0) => {
  if (num == null) return '—'
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

const formatDate = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 80) return 'bg-green-500'
  if (confidence >= 60) return 'bg-blue-500'
  if (confidence >= 40) return 'bg-yellow-500'
  return 'bg-red-500'
}

// WebSocket event handlers
tradesWs.on('trade_created', (data) => {
  // New trade created - add to list
  const newTrade = { ...data.trade, applying: false }
  trades.value.unshift(newTrade)
})

tradesWs.on('trade_updated', (data) => {
  // Trade updated - find and update in list
  const index = trades.value.findIndex(t => t.id === data.trade.id)
  if (index >= 0) {
    trades.value[index] = { ...trades.value[index], ...data.trade }
  }
})

tradesWs.on('trade_removed', (data) => {
  // Trade removed (applied/cancelled) - remove from list
  trades.value = trades.value.filter(t => t.id !== data.trade_id)
})

tradesWs.on('trades_refresh', () => {
  // Full refresh requested
  fetchTrades()
})

// Lifecycle
onMounted(fetchTrades)
</script>

<style scoped>
.section-title {
  @apply text-xs font-medium uppercase tracking-wider text-text-tertiary;
}
</style>