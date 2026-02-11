<template>
  <!-- Loading skeleton -->
  <DashboardSkeleton v-if="delayedLoading" />

  <!-- Dashboard content -->
  <div v-else>
    <!-- Mobile-first responsive stats grid -->
    <section class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 sm:gap-6">
      <StatCard
        v-for="stat in summaryStats"
        :key="stat.label"
        :label="stat.label"
        :value="stat.value"
        :description="stat.description"
        :trend="stat.trend"
        :trend-direction="stat.trendDirection"
      />
      <BaseCard v-if="summaryStats.length === 0" class="sm:col-span-2 lg:col-span-3">
        <EmptyState
          title="Waiting on dashboard metrics"
          description="Run an agent to populate analytics."
        />
      </BaseCard>
    </section>

    <!-- Mobile-first responsive main content grid -->
    <section class="grid gap-4 sm:gap-6 lg:grid-cols-[2fr,1fr]">
    <BaseCard>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="section-title">Performance</p>
          <h3 class="font-display text-xl sm:text-2xl font-semibold text-text-primary">Portfolio Momentum</h3>
        </div>
        <div class="flex items-center gap-3 self-start sm:self-auto">
          <ConnectionStatus 
            :state="systemWs.state.value"
            :error="systemWs.error.value"
            :reconnect-attempts="systemWs.reconnectAttempts.value"
            @reconnect="systemWs.connect"
            compact
          />
        </div>
      </div>
      <div class="mt-4 sm:mt-6">
        <!-- Chart container with mobile-optimized height -->
        <div class="min-h-[200px] sm:min-h-[300px]">
          <LineChart v-if="chartReady" :labels="chartLabels" :datasets="chartDatasets" />
          <EmptyState
            v-else
            title="No chart data"
            description="Analytics data will appear here after execution runs."
          />
        </div>
      </div>
    </BaseCard>

    <!-- Mobile-responsive sidebar content -->
    <div class="space-y-4 sm:space-y-6">
      <BaseCard>
        <p class="section-title">Execution</p>
        <h3 class="font-display text-lg sm:text-xl lg:text-2xl font-semibold text-text-primary">Recent Activity</h3>
        <div class="mt-4 sm:mt-6 space-y-3 sm:space-y-4">
          <div v-if="loading" class="text-sm text-text-tertiary">Loading dashboard data...</div>
          <div v-else-if="error" class="text-sm text-danger">Unable to load dashboard data.</div>
          <div v-else-if="recentLogs.length === 0">
            <EmptyState
              title="No executions yet"
              description="Trigger an agent run to start tracking execution history."
            />
          </div>
          <div v-else class="space-y-3 sm:space-y-4">
            <!-- Mobile-optimized log entries -->
            <div
              v-for="log in recentLogs"
              :key="log.id || log.timestamp || log"
              class="rounded-2xl border border-slate-800/60 bg-theme-secondary/60 p-3 sm:p-4"
            >
              <p class="text-sm font-semibold text-text-primary break-words">
                {{ log.title || log.action || 'Execution' }}
              </p>
              <p class="text-xs text-text-tertiary mt-1">
                {{ log.timestamp || log.created_at || 'Timestamp pending' }}
              </p>
              <p v-if="log.summary" class="mt-2 text-sm text-text-secondary break-words">{{ log.summary }}</p>
            </div>
          </div>
        </div>
      </BaseCard>

      <BaseCard>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="section-title">Scheduler</p>
            <h3 class="font-display text-lg sm:text-xl lg:text-2xl font-semibold text-text-primary">Status</h3>
          </div>
          <StatusBadge :label="schedulerStatusLabel" :tone="schedulerTone" class="self-start sm:self-auto" />
        </div>
        <div class="mt-4 sm:mt-6 space-y-3 sm:space-y-4">
          <div v-if="schedulerLoading" class="text-sm text-text-tertiary">
            Loading scheduler status...
          </div>
          <div v-else-if="schedulerError" class="text-sm text-danger">
            Unable to load scheduler status.
          </div>
          <div v-else class="space-y-3 text-sm text-text-secondary">
            <!-- Mobile-friendly key-value pairs -->
            <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <span class="text-text-tertiary text-xs sm:text-sm">Next run</span>
              <span class="text-text-primary font-medium break-all sm:break-normal">{{ schedulerNextRun }}</span>
            </div>
            <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <span class="text-text-tertiary text-xs sm:text-sm">Interval</span>
              <span class="text-text-primary font-medium">{{ schedulerInterval }}</span>
            </div>
          </div>
        </div>
      </BaseCard>
    </div>
  </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getDashboard, getSchedulerStatus } from '../services/api'
import { useSystemWebSocket } from '../composables/useWebSocket'
import { useDelayedLoading } from '../composables/useLoading'
import BaseCard from '../components/BaseCard.vue'
import EmptyState from '../components/EmptyState.vue'
import LineChart from '../components/LineChart.vue'
import StatCard from '../components/StatCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import DashboardSkeleton from '../components/skeletons/DashboardSkeleton.vue'

// State
const data = ref(null)
const loading = ref(true)
const error = ref(null)
const scheduler = ref(null)
const schedulerLoading = ref(true)
const schedulerError = ref(null)

// WebSocket integration
const systemWs = useSystemWebSocket()

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(200)

const formatLabel = (label) =>
  label
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())

const formatValue = (value) => {
  if (typeof value === 'number') return value.toLocaleString()
  if (value === null || value === undefined) return '—'
  return String(value)
}

const summaryStats = computed(() => {
  const summary = data.value?.summary
  if (!summary || typeof summary !== 'object') return []
  return Object.entries(summary).slice(0, 3).map(([key, value]) => ({
    label: formatLabel(key),
    value: formatValue(value)
  }))
})

const chartLabels = computed(() => data.value?.performance?.labels || [])
const chartDatasets = computed(() => data.value?.performance?.datasets || [])
const chartReady = computed(() => chartLabels.value.length > 0 && chartDatasets.value.length > 0)

const recentLogs = computed(() =>
  data.value?.recent_logs || data.value?.execution_logs || []
)

const schedulerStatusLabel = computed(() => {
  if (!scheduler.value) return 'Unknown'
  return scheduler.value.running ? 'Running' : 'Stopped'
})

const schedulerTone = computed(() => {
  if (!scheduler.value) return 'neutral'
  return scheduler.value.running ? 'success' : 'warning'
})

const schedulerNextRun = computed(() => {
  const nextRuns = scheduler.value?.next_runs
  if (!nextRuns || typeof nextRuns !== 'object' || Object.keys(nextRuns).length === 0) return '—'
  return nextRuns[Object.keys(nextRuns)[0]] || '—'
})

const schedulerInterval = computed(() => scheduler.value?.interval || '—')

// WebSocket event handlers
systemWs.on('dashboard_update', (updateData) => {
  // Live dashboard data updates
  if (updateData.summary) {
    data.value = { ...data.value, summary: updateData.summary }
  }
  if (updateData.recent_logs) {
    data.value = { ...data.value, recent_logs: updateData.recent_logs }
  }
  if (updateData.performance) {
    data.value = { ...data.value, performance: updateData.performance }
  }
})

systemWs.on('scheduler_update', (updateData) => {
  // Live scheduler status updates
  scheduler.value = { ...scheduler.value, ...updateData }
})

systemWs.on('execution_complete', (updateData) => {
  // Refresh dashboard when executions complete
  if (updateData.portfolio) {
    loadDashboardData()
  }
})

// Load initial data
const loadDashboardData = async () => {
  loading.value = true
  startLoading()
  try {
    data.value = await getDashboard()
    error.value = null
  } catch (err) {
    error.value = err
  } finally {
    loading.value = false
    stopLoading()
  }
}

const loadSchedulerData = async () => {
  schedulerLoading.value = true
  try {
    scheduler.value = await getSchedulerStatus()
  } catch (err) {
    schedulerError.value = err
  } finally {
    schedulerLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadDashboardData(), loadSchedulerData()])
})
</script>
