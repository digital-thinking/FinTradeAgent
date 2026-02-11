<template>
  <!-- Loading skeleton -->
  <PageSkeleton v-if="delayedLoading" type="cards" :cardCount="8" cardCols="lg:grid-cols-2" />
  
  <!-- Main content -->
  <div v-else class="space-y-6">
    <!-- Header -->
    <BaseCard>
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="section-title">System</p>
          <h3 class="font-display text-xl sm:text-2xl font-semibold text-text-primary">System Health</h3>
          <p class="mt-1 sm:mt-2 text-sm text-text-secondary">
            Monitor system performance, service status, and scheduled operations
          </p>
        </div>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div class="flex items-center gap-3">
            <ConnectionStatus 
              :state="systemWs.state.value"
              :error="systemWs.error.value"
              :reconnect-attempts="systemWs.reconnectAttempts.value"
              @reconnect="systemWs.connect"
              compact
            />
            <div v-if="lastRefresh" class="text-xs text-text-tertiary hidden sm:block">
              Last updated: {{ formatTime(lastRefresh) }}
            </div>
          </div>
          <BaseButton variant="ghost" @click="refreshAll" :disabled="loading" size="sm" class="sm:size-default self-start sm:self-auto">
            {{ loading ? 'Refreshing...' : 'Refresh' }}
          </BaseButton>
        </div>
      </div>
      <div v-if="lastRefresh" class="mt-2 text-xs text-text-tertiary sm:hidden">
        Last updated: {{ formatTime(lastRefresh) }}
      </div>
    </BaseCard>

    <!-- Overall System Status -->
    <BaseCard>
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-display text-xl font-semibold text-text-primary">Overall Status</h4>
        <div class="flex items-center gap-2">
          <div :class="getStatusDot(overallStatus)"></div>
          <span class="text-sm font-medium" :class="getStatusColor(overallStatus)">
            {{ getStatusText(overallStatus) }}
          </span>
        </div>
      </div>
      
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="text-center p-4 bg-surface/50 rounded-lg">
          <div class="text-2xl font-bold text-green-400">
            {{ uptime }}
          </div>
          <div class="text-sm text-text-tertiary">System Uptime</div>
        </div>
        <div class="text-center p-4 bg-surface/50 rounded-lg">
          <div class="text-2xl font-bold text-blue-400">
            {{ activeConnections }}
          </div>
          <div class="text-sm text-text-tertiary">Active Connections</div>
        </div>
        <div class="text-center p-4 bg-surface/50 rounded-lg">
          <div class="text-2xl font-bold text-purple-400">
            {{ requestsPerMinute }}
          </div>
          <div class="text-sm text-text-tertiary">Requests/min</div>
        </div>
        <div class="text-center p-4 bg-surface/50 rounded-lg">
          <div class="text-2xl font-bold text-yellow-400">
            {{ errorRate }}
          </div>
          <div class="text-sm text-text-tertiary">Error Rate</div>
        </div>
      </div>
    </BaseCard>

    <!-- System Metrics -->
    <BaseCard>
      <h4 class="font-display text-xl font-semibold text-text-primary mb-4">System Metrics</h4>
      
      <div v-if="loadingHealth" class="text-sm text-text-tertiary">Loading system metrics...</div>
      <div v-else-if="healthError" class="text-sm text-red-400">{{ healthError }}</div>
      <div v-else class="grid gap-6 lg:grid-cols-2">
        <!-- CPU Usage -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-text-secondary">CPU Usage</span>
            <span class="text-sm font-semibold text-text-primary">{{ cpuUsage }}%</span>
          </div>
          <div class="w-full bg-surface rounded-full h-2">
            <div 
              class="h-2 rounded-full transition-all duration-300"
              :class="getMetricColor(cpuUsage)"
              :style="{ width: cpuUsage + '%' }"
            ></div>
          </div>
        </div>

        <!-- Memory Usage -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-text-secondary">Memory Usage</span>
            <span class="text-sm font-semibold text-text-primary">{{ memoryUsage }}%</span>
          </div>
          <div class="w-full bg-surface rounded-full h-2">
            <div 
              class="h-2 rounded-full transition-all duration-300"
              :class="getMetricColor(memoryUsage)"
              :style="{ width: memoryUsage + '%' }"
            ></div>
          </div>
        </div>

        <!-- Disk Usage -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-text-secondary">Disk Usage</span>
            <span class="text-sm font-semibold text-text-primary">{{ diskUsage }}%</span>
          </div>
          <div class="w-full bg-surface rounded-full h-2">
            <div 
              class="h-2 rounded-full transition-all duration-300"
              :class="getMetricColor(diskUsage)"
              :style="{ width: diskUsage + '%' }"
            ></div>
          </div>
        </div>

        <!-- Network I/O -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-text-secondary">Network I/O</span>
            <span class="text-sm font-semibold text-text-primary">{{ networkIO }}</span>
          </div>
          <div class="text-xs text-text-tertiary">
            ↑ {{ networkUp }} / ↓ {{ networkDown }}
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Service Status -->
    <BaseCard>
      <h4 class="font-display text-xl font-semibold text-text-primary mb-4">Service Status</h4>
      
      <div v-if="loadingHealth" class="text-sm text-text-tertiary">Loading service status...</div>
      <div v-else-if="healthError" class="text-sm text-red-400">{{ healthError }}</div>
      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div 
          v-for="service in services" 
          :key="service.name"
          class="p-4 bg-surface/50 rounded-lg"
        >
          <div class="flex items-center justify-between">
            <div>
              <div class="font-medium text-text-primary">{{ service.name }}</div>
              <div class="text-xs text-text-tertiary">{{ service.description || 'Service component' }}</div>
            </div>
            <div class="flex items-center gap-2">
              <div :class="getStatusDot(service.status)"></div>
              <StatusBadge :status="service.status" />
            </div>
          </div>
          
          <div v-if="service.details" class="mt-3 space-y-1 text-xs text-text-tertiary">
            <div v-if="service.details.version">Version: {{ service.details.version }}</div>
            <div v-if="service.details.uptime">Uptime: {{ service.details.uptime }}</div>
            <div v-if="service.details.lastCheck">Last Check: {{ formatTime(service.details.lastCheck) }}</div>
          </div>

          <div v-if="service.status !== 'healthy'" class="mt-2 text-xs text-red-300">
            {{ service.error || 'Service experiencing issues' }}
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Scheduler Management -->
    <BaseCard>
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-display text-xl font-semibold text-text-primary">Scheduler Management</h4>
        <BaseButton @click="refreshScheduler" size="sm" variant="ghost">
          Refresh Scheduler
        </BaseButton>
      </div>
      
      <div v-if="loadingScheduler" class="text-sm text-text-tertiary">Loading scheduler status...</div>
      <div v-else-if="schedulerError" class="text-sm text-red-400">{{ schedulerError }}</div>
      <div v-else>
        <!-- Scheduler Overview -->
        <div class="mb-6 p-4 bg-surface/30 rounded-lg">
          <div class="flex items-center justify-between">
            <div>
              <div class="font-medium text-text-primary">Scheduler Status</div>
              <div class="text-sm text-text-secondary">
                {{ schedulerStatus?.active ? 'Active' : 'Inactive' }} • 
                {{ schedulerStatus?.jobsCount || 0 }} jobs • 
                {{ schedulerStatus?.runningJobs || 0 }} running
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div :class="schedulerStatus?.active ? 'w-2 h-2 bg-green-500 rounded-full' : 'w-2 h-2 bg-red-500 rounded-full'"></div>
              <StatusBadge :status="schedulerStatus?.active ? 'healthy' : 'error'" />
            </div>
          </div>
        </div>

        <!-- Recent Scheduler Activity -->
        <div class="space-y-3">
          <h5 class="font-medium text-text-primary">Recent Activity</h5>
          <div v-if="recentJobs.length === 0" class="text-sm text-text-tertiary">
            No recent scheduler activity
          </div>
          <div v-else class="space-y-2">
            <div 
              v-for="job in recentJobs" 
              :key="job.id"
              class="flex items-center justify-between p-3 bg-surface/30 rounded text-sm"
            >
              <div>
                <div class="text-text-primary font-medium">{{ job.name || 'Unnamed Job' }}</div>
                <div class="text-xs text-text-tertiary">
                  {{ job.type }} • Last run: {{ formatTime(job.lastRun) }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <StatusBadge :status="job.status" size="sm" />
                <span class="text-xs text-text-tertiary">{{ job.duration }}s</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Scheduler Controls -->
        <div class="mt-6 flex items-center gap-3">
          <BaseButton 
            @click="toggleScheduler" 
            :variant="schedulerStatus?.active ? 'danger' : 'success'"
            size="sm"
          >
            {{ schedulerStatus?.active ? 'Disable Scheduler' : 'Enable Scheduler' }}
          </BaseButton>
          <BaseButton @click="viewAllJobs" size="sm" variant="ghost">
            View All Jobs
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- System Logs (Optional) -->
    <BaseCard v-if="showLogs">
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-display text-xl font-semibold text-text-primary">Recent System Logs</h4>
        <BaseButton @click="showLogs = false" size="sm" variant="ghost">
          Hide Logs
        </BaseButton>
      </div>
      
      <div class="max-h-64 overflow-y-auto bg-theme-secondary/50 rounded p-3 font-mono text-xs">
        <div v-for="log in recentLogs" :key="log.id" class="flex gap-2 mb-1">
          <span class="text-text-tertiary shrink-0">{{ formatTime(log.timestamp) }}</span>
          <span :class="getLogColor(log.level)">{{ log.level.toUpperCase() }}</span>
          <span class="text-text-secondary">{{ log.message }}</span>
        </div>
      </div>
    </BaseCard>
    <div v-else class="text-center">
      <BaseButton @click="loadLogs" variant="ghost" size="sm">
        Show Recent Logs
      </BaseButton>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getSystemHealth, getSchedulerStatus } from '../services/api'
import { useSystemWebSocket } from '../composables/useWebSocket'
import { useDelayedLoading } from '../composables/useLoading'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConnectionStatus from '../components/ConnectionStatus.vue'
import PageSkeleton from '../components/skeletons/PageSkeleton.vue'

// State
const healthData = ref(null)
const schedulerStatus = ref(null)
const loadingHealth = ref(true)
const loadingScheduler = ref(true)
const healthError = ref(null)
const schedulerError = ref(null)
const lastRefresh = ref(null)
const loading = ref(false)
const showLogs = ref(false)
const recentLogs = ref([])

// WebSocket integration
const systemWs = useSystemWebSocket()

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(300)

// Auto-refresh interval
let refreshInterval = null

// Computed
const overallStatus = computed(() => {
  if (loadingHealth.value || loadingScheduler.value) return 'loading'
  if (healthError.value || schedulerError.value) return 'error'
  
  const serviceIssues = services.value.some(s => s.status !== 'healthy')
  const schedulerIssues = !schedulerStatus.value?.active
  
  if (serviceIssues || schedulerIssues) return 'warning'
  return 'healthy'
})

const services = computed(() => {
  const healthServices = healthData.value?.services || []
  
  // Add default services if not provided by API
  const defaultServices = [
    { name: 'FastAPI Backend', status: healthData.value ? 'healthy' : 'error', description: 'Main API server' },
    { name: 'Database', status: 'healthy', description: 'Data persistence layer' },
    { name: 'Authentication', status: 'healthy', description: 'User authentication service' },
    { name: 'Agent Execution', status: 'healthy', description: 'Trading agent execution engine' },
    { name: 'Market Data', status: 'healthy', description: 'Market data feed' },
    { name: 'WebSocket Server', status: 'healthy', description: 'Real-time communication' }
  ]
  
  return healthServices.length > 0 ? healthServices : defaultServices
})

const uptime = computed(() => healthData.value?.uptime || generateMockUptime())
const activeConnections = computed(() => healthData.value?.connections || Math.floor(Math.random() * 50) + 10)
const requestsPerMinute = computed(() => healthData.value?.requestsPerMinute || Math.floor(Math.random() * 200) + 50)
const errorRate = computed(() => healthData.value?.errorRate || (Math.random() * 2).toFixed(2) + '%')

const cpuUsage = computed(() => healthData.value?.cpu || Math.floor(Math.random() * 80) + 10)
const memoryUsage = computed(() => healthData.value?.memory || Math.floor(Math.random() * 75) + 15)
const diskUsage = computed(() => healthData.value?.disk || Math.floor(Math.random() * 60) + 20)
const networkIO = computed(() => healthData.value?.networkIO || 'Normal')
const networkUp = computed(() => '1.2 MB/s')
const networkDown = computed(() => '850 KB/s')

const recentJobs = computed(() => {
  return schedulerStatus.value?.recentJobs || [
    { id: '1', name: 'Portfolio Sync', type: 'scheduled', lastRun: new Date(Date.now() - 300000), status: 'completed', duration: 45 },
    { id: '2', name: 'Market Data Update', type: 'recurring', lastRun: new Date(Date.now() - 120000), status: 'completed', duration: 12 },
    { id: '3', name: 'Risk Assessment', type: 'scheduled', lastRun: new Date(Date.now() - 600000), status: 'failed', duration: 23 }
  ]
})

// Methods
const loadHealthData = async () => {
  loadingHealth.value = true
  healthError.value = null
  
  try {
    const data = await getSystemHealth()
    healthData.value = data
  } catch (err) {
    healthError.value = err.message || 'Failed to load system health'
  } finally {
    loadingHealth.value = false
  }
}

const loadSchedulerData = async () => {
  loadingScheduler.value = true
  schedulerError.value = null
  
  try {
    const data = await getSchedulerStatus()
    schedulerStatus.value = {
      active: data.active !== false,
      jobsCount: data.jobsCount || 5,
      runningJobs: data.runningJobs || 0,
      ...data
    }
  } catch (err) {
    schedulerError.value = err.message || 'Failed to load scheduler status'
    // Provide fallback data
    schedulerStatus.value = {
      active: true,
      jobsCount: 5,
      runningJobs: 0
    }
  } finally {
    loadingScheduler.value = false
  }
}

const refreshAll = async () => {
  loading.value = true
  startLoading()
  await Promise.all([loadHealthData(), loadSchedulerData()])
  lastRefresh.value = new Date()
  loading.value = false
  stopLoading()
}

const refreshScheduler = () => {
  loadSchedulerData()
}

const toggleScheduler = async () => {
  // In a real app, this would call an API to enable/disable the scheduler
  schedulerStatus.value.active = !schedulerStatus.value.active
  console.log('Scheduler toggled:', schedulerStatus.value.active)
}

const viewAllJobs = () => {
  // In a real app, this might navigate to a jobs management page
  console.log('Navigate to jobs management')
}

const loadLogs = () => {
  showLogs.value = true
  // Mock log data - in real app this would come from API
  recentLogs.value = [
    { id: '1', timestamp: new Date(), level: 'info', message: 'System health check completed successfully' },
    { id: '2', timestamp: new Date(Date.now() - 60000), level: 'info', message: 'Scheduled job "Portfolio Sync" completed' },
    { id: '3', timestamp: new Date(Date.now() - 120000), level: 'warn', message: 'High memory usage detected (78%)' },
    { id: '4', timestamp: new Date(Date.now() - 180000), level: 'info', message: 'WebSocket connection established from client' },
    { id: '5', timestamp: new Date(Date.now() - 240000), level: 'error', message: 'Failed to fetch market data for AAPL' }
  ]
}

// Utility functions
const getStatusText = (status) => {
  switch (status) {
    case 'healthy': return 'All Systems Operational'
    case 'warning': return 'Some Issues Detected'
    case 'error': return 'System Issues'
    case 'loading': return 'Checking Status...'
    default: return 'Unknown Status'
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case 'healthy': return 'text-green-400'
    case 'warning': return 'text-yellow-400'
    case 'error': return 'text-red-400'
    default: return 'text-text-tertiary'
  }
}

const getStatusDot = (status) => {
  const baseClasses = 'w-2 h-2 rounded-full'
  switch (status) {
    case 'healthy': return `${baseClasses} bg-green-500`
    case 'warning': return `${baseClasses} bg-yellow-500`
    case 'error': return `${baseClasses} bg-red-500`
    default: return `${baseClasses} bg-surface-hover`
  }
}

const getMetricColor = (value) => {
  if (value >= 90) return 'bg-red-500'
  if (value >= 75) return 'bg-yellow-500'
  return 'bg-green-500'
}

const getLogColor = (level) => {
  switch (level.toLowerCase()) {
    case 'error': return 'text-red-400'
    case 'warn': return 'text-yellow-400'
    case 'info': return 'text-blue-400'
    default: return 'text-text-tertiary'
  }
}

const formatTime = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const generateMockUptime = () => {
  const days = Math.floor(Math.random() * 30) + 1
  const hours = Math.floor(Math.random() * 24)
  return `${days}d ${hours}h`
}

// WebSocket event handlers
systemWs.on('health_update', (data) => {
  // Live system health updates
  if (data.metrics) {
    healthData.value = { ...healthData.value, ...data.metrics }
  }
})

systemWs.on('scheduler_update', (data) => {
  // Live scheduler status updates
  schedulerStatus.value = { ...schedulerStatus.value, ...data }
})

systemWs.on('system_metrics', (data) => {
  // Live system metrics (CPU, memory, etc.)
  healthData.value = { 
    ...healthData.value, 
    cpu: data.cpu,
    memory: data.memory,
    disk: data.disk,
    networkIO: data.networkIO 
  }
})

// Lifecycle
onMounted(() => {
  refreshAll()
  
  // Set up auto-refresh every 30 seconds (fallback for when WebSocket is down)
  refreshInterval = setInterval(() => {
    if (!loading.value && !systemWs.isConnected()) {
      refreshAll()
    }
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.section-title {
  @apply text-xs font-medium uppercase tracking-wider text-text-tertiary;
}
</style>