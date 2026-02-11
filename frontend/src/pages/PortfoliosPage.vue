<template>
  <!-- Loading skeleton -->
  <PageSkeleton v-if="delayedLoading" type="table" :tableRows="6" :tableColumns="[
    { key: 'name', width: '100%' },
    { key: 'totalValue', type: 'number' },
    { key: 'cash', type: 'number' },
    { key: 'holdings', type: 'number' },
    { key: 'scheduler', type: 'badge' },
    { key: 'updated', type: 'text', width: '120px' },
    { key: 'actions', type: 'button' }
  ]" />
  
  <!-- Main content -->
  <div v-else>
    <BaseCard>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="section-title">Portfolios</p>
          <h3 class="font-display text-xl sm:text-2xl font-semibold text-text-primary">Strategy Library</h3>
        </div>
        <BaseButton @click="openCreateModal" class="self-start sm:self-auto">New Portfolio</BaseButton>
      </div>
      <p v-if="actionMessage" class="mt-3 text-sm text-mint">{{ actionMessage }}</p>
      <p v-if="actionError" class="mt-2 text-sm text-danger">{{ actionError }}</p>
    </BaseCard>

  <section v-if="loading" class="text-sm text-text-tertiary">Loading portfolios...</section>
  <section v-else-if="error" class="text-sm text-danger">{{ errorMessage }}</section>
  <section v-else-if="portfolios.length === 0">
    <EmptyState
      title="No portfolios yet"
      description="Create your first portfolio to start executing strategies."
    >
      <BaseButton class="mt-3" @click="openCreateModal">Create Portfolio</BaseButton>
    </EmptyState>
  </section>
  <section v-else>
    <!-- Mobile Card Layout -->
    <div class="block lg:hidden space-y-4">
      <BaseCard v-for="portfolio in portfolios" :key="portfolio.name" class="space-y-4">
        <!-- Portfolio Header -->
        <div class="flex items-start justify-between">
          <div class="min-w-0 flex-1">
            <h4 class="font-semibold text-text-primary truncate">{{ portfolio.name }}</h4>
            <div class="flex items-center gap-2 mt-1">
              <StatusBadge
                :label="portfolio.scheduler_enabled ? 'Enabled' : 'Disabled'"
                :tone="portfolio.scheduler_enabled ? 'success' : 'neutral'"
              />
            </div>
          </div>
          <RouterLink
            class="glass px-3 py-1.5 text-xs font-semibold text-accent rounded-lg shrink-0 ml-3"
            :to="`/portfolios/${portfolio.name}`"
          >
            View
          </RouterLink>
        </div>
        
        <!-- Portfolio Metrics Grid -->
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-text-tertiary text-xs block">Total Value</span>
            <span class="text-text-primary font-medium">{{ formatCurrency(portfolio.total_value) }}</span>
          </div>
          <div>
            <span class="text-text-tertiary text-xs block">Cash</span>
            <span class="text-text-secondary">{{ formatCurrency(portfolio.cash) }}</span>
          </div>
          <div>
            <span class="text-text-tertiary text-xs block">Holdings</span>
            <span class="text-text-secondary">{{ portfolio.holdings_count ?? '—' }}</span>
          </div>
          <div>
            <span class="text-text-tertiary text-xs block">Last Updated</span>
            <span class="text-text-secondary text-xs">{{ formatTimestamp(portfolio.last_updated) }}</span>
          </div>
        </div>

        <!-- Mobile Actions -->
        <div class="flex items-center justify-end gap-3 pt-2 border-t border-border/60">
          <button class="text-xs text-text-secondary font-medium" type="button" @click="openEditModal(portfolio.name)">
            Edit
          </button>
          <button
            class="text-xs text-danger font-medium"
            type="button"
            @click="removePortfolio(portfolio.name)"
          >
            Delete
          </button>
        </div>
      </BaseCard>
    </div>

    <!-- Desktop Table Layout -->
    <div class="glass overflow-hidden rounded-3xl hidden lg:block">
      <table class="w-full text-left text-sm">
        <thead class="bg-theme-secondary/80 text-xs uppercase tracking-[0.2em] text-text-tertiary">
          <tr>
            <th class="px-6 py-4">Name</th>
            <th class="px-6 py-4">Total Value</th>
            <th class="px-6 py-4">Cash</th>
            <th class="px-6 py-4">Holdings</th>
            <th class="px-6 py-4">Scheduler</th>
            <th class="px-6 py-4">Last Updated</th>
            <th class="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60">
          <tr v-for="portfolio in portfolios" :key="portfolio.name" class="hover:bg-surface/30 transition-colors">
            <td class="px-6 py-4 font-semibold text-text-primary">{{ portfolio.name }}</td>
            <td class="px-6 py-4 text-text-secondary">{{ formatCurrency(portfolio.total_value) }}</td>
            <td class="px-6 py-4 text-text-secondary">{{ formatCurrency(portfolio.cash) }}</td>
            <td class="px-6 py-4 text-text-secondary">{{ portfolio.holdings_count ?? '—' }}</td>
            <td class="px-6 py-4">
              <StatusBadge
                :label="portfolio.scheduler_enabled ? 'Enabled' : 'Disabled'"
                :tone="portfolio.scheduler_enabled ? 'success' : 'neutral'"
              />
            </td>
            <td class="px-6 py-4 text-text-secondary">{{ formatTimestamp(portfolio.last_updated) }}</td>
            <td class="px-6 py-4">
              <div class="flex items-center justify-end gap-3">
                <RouterLink
                  class="text-xs font-semibold text-accent hover:text-accent/80"
                  :to="`/portfolios/${portfolio.name}`"
                >
                  View
                </RouterLink>
                <button class="text-xs text-text-secondary hover:text-text-primary" type="button" @click="openEditModal(portfolio.name)">
                  Edit
                </button>
                <button
                  class="text-xs text-danger hover:text-danger/80"
                  type="button"
                  @click="removePortfolio(portfolio.name)"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <BaseModal
    :open="modalOpen"
    :title="modalTitle"
    :eyebrow="modalEyebrow"
    @close="closeModal"
  >
    <div v-if="modalLoading" class="text-sm text-text-tertiary">Loading portfolio...</div>
    <form v-else class="space-y-4 sm:space-y-6" @submit.prevent="submitPortfolio">
      <!-- Basic Information -->
      <div class="space-y-4">
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Name</label>
          <input
            v-model.trim="form.name"
            class="form-input"
            placeholder="Alpha Growth"
            :disabled="isEditing"
            required
          />
          <p v-if="isEditing" class="mt-2 text-xs text-text-tertiary">Portfolio names cannot be edited.</p>
        </div>
        
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Initial Capital</label>
          <input
            v-model.number="form.initial_capital"
            type="number"
            min="1"
            step="100"
            class="form-input"
            placeholder="100000"
            required
          />
        </div>
        
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">LLM Model</label>
          <input
            v-model.trim="form.llm_model"
            class="form-input"
            placeholder="gpt-4o"
            required
          />
        </div>
      </div>

      <!-- Configuration Grid - Mobile First -->
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Asset Class</label>
          <input
            v-model.trim="form.asset_class"
            class="form-input"
            placeholder="stocks"
          />
        </div>
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Agent Mode</label>
          <input
            v-model.trim="form.agent_mode"
            class="form-input"
            placeholder="langgraph"
          />
        </div>
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Run Frequency</label>
          <input
            v-model.trim="form.run_frequency"
            class="form-input"
            placeholder="daily"
          />
        </div>
        <div>
          <label class="block text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">Ollama Base URL</label>
          <input
            v-model.trim="form.ollama_base_url"
            class="form-input"
            placeholder="http://localhost:11434"
          />
        </div>
      </div>

      <!-- Checkboxes - Mobile Friendly Layout -->
      <div class="space-y-3 sm:space-y-4">
        <label class="flex items-start gap-3 text-sm text-text-secondary cursor-pointer">
          <input 
            v-model="form.scheduler_enabled" 
            type="checkbox" 
            class="mt-0.5 h-4 w-4 rounded border-border bg-theme/70 text-accent focus:ring-accent shrink-0" 
          />
          <span>Scheduler Enabled</span>
        </label>
        <label class="flex items-start gap-3 text-sm text-text-secondary cursor-pointer">
          <input 
            v-model="form.auto_apply_trades" 
            type="checkbox" 
            class="mt-0.5 h-4 w-4 rounded border-border bg-theme/70 text-accent focus:ring-accent shrink-0" 
          />
          <span>Auto-apply Trades</span>
        </label>
      </div>

      <!-- Error Message -->
      <div v-if="formError" class="text-sm text-danger bg-red-900/20 border border-red-500/30 rounded-xl p-3">
        {{ formError }}
      </div>

      <!-- Action Buttons - Mobile First -->
      <div class="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:pt-6">
        <BaseButton type="submit" :disabled="formSubmitting" class="w-full sm:w-auto order-2 sm:order-1">
          {{ isEditing ? 'Save Changes' : 'Create' }}
        </BaseButton>
        <BaseButton variant="ghost" type="button" @click="closeModal" class="w-full sm:w-auto order-1 sm:order-2">
          Cancel
        </BaseButton>
      </div>
    </form>
  </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createPortfolio, deletePortfolio, getPortfolio, listPortfolios, updatePortfolio } from '../services/api'
import { useDelayedLoading } from '../composables/useLoading'
import BaseButton from '../components/BaseButton.vue'
import BaseCard from '../components/BaseCard.vue'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusBadge from '../components/StatusBadge.vue'
import PageSkeleton from '../components/skeletons/PageSkeleton.vue'

const portfolios = ref([])
const loading = ref(true)
const error = ref(null)
const actionMessage = ref('')
const actionError = ref('')

// Loading state management
const { delayedLoading, startLoading, stopLoading } = useDelayedLoading(300)

const modalOpen = ref(false)
const modalMode = ref('create')
const modalLoading = ref(false)
const formSubmitting = ref(false)
const form = ref({
  name: '',
  initial_capital: 100000,
  llm_model: '',
  asset_class: 'stocks',
  agent_mode: 'langgraph',
  run_frequency: 'daily',
  scheduler_enabled: false,
  auto_apply_trades: false,
  ollama_base_url: 'http://localhost:11434'
})
const formError = ref('')
const editingName = ref('')

const errorMessage = computed(() => getErrorMessage(error.value, 'Unable to load portfolios.'))
const isEditing = computed(() => modalMode.value === 'edit')
const modalTitle = computed(() => (isEditing.value ? 'Edit Portfolio' : 'Create Portfolio'))
const modalEyebrow = computed(() => (isEditing.value ? 'Update Strategy' : 'New Strategy'))

const getErrorMessage = (err, fallback) => {
  if (!err) return fallback
  if (typeof err === 'string') return err
  return err?.response?.data?.detail || err?.response?.data?.error || err?.message || fallback
}

const formatCurrency = (value) => {
  if (typeof value !== 'number') return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value)
}

const formatTimestamp = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

const resetForm = () => {
  form.value = {
    name: '',
    initial_capital: 100000,
    llm_model: '',
    asset_class: 'stocks',
    agent_mode: 'langgraph',
    run_frequency: 'daily',
    scheduler_enabled: false,
    auto_apply_trades: false,
    ollama_base_url: 'http://localhost:11434'
  }
}

const fetchPortfolios = async () => {
  loading.value = true
  startLoading()
  error.value = null
  try {
    const data = await listPortfolios()
    if (!Array.isArray(data)) {
      throw new Error('Portfolios response must be an array.')
    }
    portfolios.value = data
  } catch (err) {
    error.value = err
  } finally {
    loading.value = false
    stopLoading()
  }
}

const openCreateModal = () => {
  modalOpen.value = true
  modalMode.value = 'create'
  editingName.value = ''
  resetForm()
  formError.value = ''
  formSubmitting.value = false
  modalLoading.value = false
}

const openEditModal = async (name) => {
  modalOpen.value = true
  modalMode.value = 'edit'
  editingName.value = name
  resetForm()
  formError.value = ''
  formSubmitting.value = false
  modalLoading.value = true
  try {
    const data = await getPortfolio(name)
    const config = data?.config || {}
    form.value = {
      name: config.name || name,
      initial_capital: config.initial_capital ?? 100000,
      llm_model: config.llm_model || '',
      asset_class: config.asset_class || 'stocks',
      agent_mode: config.agent_mode || 'langgraph',
      run_frequency: config.run_frequency || 'daily',
      scheduler_enabled: Boolean(config.scheduler_enabled),
      auto_apply_trades: Boolean(config.auto_apply_trades),
      ollama_base_url: config.ollama_base_url || 'http://localhost:11434'
    }
  } catch (err) {
    formError.value = getErrorMessage(err, 'Unable to load portfolio.')
  } finally {
    modalLoading.value = false
  }
}

const closeModal = () => {
  modalOpen.value = false
  resetForm()
  formError.value = ''
  formSubmitting.value = false
  modalLoading.value = false
}

const buildPayload = () => ({
  name: isEditing.value ? editingName.value : form.value.name.trim(),
  initial_capital: Number(form.value.initial_capital),
  llm_model: form.value.llm_model.trim(),
  asset_class: form.value.asset_class.trim() || 'stocks',
  agent_mode: form.value.agent_mode.trim() || 'langgraph',
  run_frequency: form.value.run_frequency.trim() || 'daily',
  scheduler_enabled: Boolean(form.value.scheduler_enabled),
  auto_apply_trades: Boolean(form.value.auto_apply_trades),
  ollama_base_url: form.value.ollama_base_url?.trim() || null
})

const submitPortfolio = async () => {
  formError.value = ''
  actionError.value = ''
  actionMessage.value = ''
  if (!form.value.name) {
    formError.value = 'Name is required.'
    return
  }
  if (!form.value.llm_model) {
    formError.value = 'LLM model is required.'
    return
  }
  if (!Number(form.value.initial_capital) || Number(form.value.initial_capital) <= 0) {
    formError.value = 'Initial capital must be greater than zero.'
    return
  }

  formSubmitting.value = true
  try {
    const payload = buildPayload()
    if (isEditing.value) {
      await updatePortfolio(editingName.value, payload)
      actionMessage.value = `Portfolio "${editingName.value}" updated successfully.`
    } else {
      await createPortfolio(payload)
      actionMessage.value = `Portfolio "${payload.name}" created successfully.`
    }
    await fetchPortfolios()
    closeModal()
  } catch (err) {
    formError.value = getErrorMessage(err, 'Unable to save portfolio.')
  } finally {
    formSubmitting.value = false
  }
}

const removePortfolio = async (name) => {
  actionError.value = ''
  actionMessage.value = ''
  if (!window.confirm(`Delete portfolio "${name}"? This cannot be undone.`)) return
  try {
    await deletePortfolio(name)
    actionMessage.value = `Portfolio "${name}" deleted.`
    await fetchPortfolios()
  } catch (err) {
    actionError.value = getErrorMessage(err, 'Unable to delete portfolio.')
  }
}

onMounted(fetchPortfolios)
</script>
