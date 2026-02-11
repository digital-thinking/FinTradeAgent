<template>
  <div class="execution-progress">
    <!-- Header with overall progress -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h4 class="font-medium text-text-primary">Agent Execution</h4>
        <div class="flex items-center gap-2 mt-1">
          <div :class="statusIndicatorClass"></div>
          <span class="text-sm" :class="statusTextClass">
            {{ currentStatusText }}
          </span>
          <span v-if="timeRemaining" class="text-xs text-text-tertiary">
            • {{ timeRemaining }} remaining
          </span>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right">
          <div class="text-2xl font-bold text-text-primary">{{ Math.round(execution.progress) }}%</div>
          <div class="text-xs text-text-tertiary">Overall Progress</div>
        </div>
        <BaseButton 
          v-if="execution.cancellable && canCancel"
          @click="$emit('cancel')"
          size="sm"
          variant="danger"
        >
          Cancel
        </BaseButton>
      </div>
    </div>

    <!-- Overall progress bar -->
    <div class="mb-6">
      <div class="w-full bg-surface rounded-full h-3 overflow-hidden">
        <div 
          class="h-full rounded-full transition-all duration-500 ease-out"
          :class="progressBarClass"
          :style="{ width: execution.progress + '%' }"
        ></div>
      </div>
    </div>

    <!-- Step-by-step progress -->
    <div class="space-y-4">
      <h5 class="font-medium text-text-secondary">Execution Steps</h5>
      <div class="space-y-3">
        <div
          v-for="(step, index) in execution.steps"
          :key="step.id"
          class="execution-step"
          :class="getStepClass(step, index)"
        >
          <div class="flex items-center gap-3">
            <!-- Step indicator -->
            <div class="flex-shrink-0 relative">
              <div :class="getStepIndicatorClass(step)">
                <CheckIcon v-if="step.completed" class="w-4 h-4 text-text-primary" />
                <div v-else-if="isCurrentStep(step)" class="w-4 h-4">
                  <div class="w-full h-full border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div v-else class="w-2 h-2 bg-surface-hover rounded-full"></div>
              </div>
              
              <!-- Step connector line -->
              <div 
                v-if="index < execution.steps.length - 1"
                class="absolute top-8 left-1/2 w-0.5 h-6 bg-surface transform -translate-x-1/2"
                :class="{ 'bg-green-500': step.completed }"
              ></div>
            </div>

            <!-- Step content -->
            <div class="flex-grow min-w-0">
              <div class="flex items-center justify-between">
                <span class="font-medium" :class="getStepTextClass(step)">
                  {{ step.label }}
                </span>
                <span v-if="isCurrentStep(step)" class="text-xs text-text-tertiary">
                  {{ Math.round(execution.stepProgress) }}%
                </span>
              </div>
              
              <!-- Current step progress bar -->
              <div v-if="isCurrentStep(step)" class="mt-2">
                <div class="w-full bg-surface rounded-full h-1.5">
                  <div 
                    class="h-full bg-blue-500 rounded-full transition-all duration-300"
                    :style="{ width: execution.stepProgress + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent messages -->
    <div v-if="execution.messages.length > 0" class="mt-6">
      <h5 class="font-medium text-text-secondary mb-3">Live Updates</h5>
      <div class="bg-theme-secondary/50 rounded-lg p-3 max-h-32 overflow-y-auto">
        <div class="space-y-1">
          <div
            v-for="message in recentMessages"
            :key="message.id"
            class="flex gap-2 text-xs text-text-secondary fade-in"
          >
            <span class="text-text-tertiary shrink-0">{{ formatTime(message.timestamp) }}</span>
            <span>{{ message.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Error display -->
    <div v-if="execution.error" class="mt-4 p-3 bg-red-900/50 border border-red-500/50 rounded text-red-200 text-sm">
      <strong>Execution Failed:</strong> {{ execution.error }}
    </div>

    <!-- Success message -->
    <div v-if="execution.status === 'complete'" class="mt-4 p-3 bg-green-900/50 border border-green-500/50 rounded text-green-200 text-sm">
      <strong>Execution Complete!</strong> Agent finished successfully in {{ executionDuration }}.
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { EXECUTION_STEPS, EXECUTION_STEP_LABELS } from '../stores/executionStore'
import BaseButton from './BaseButton.vue'
import CheckIcon from './icons/CheckIcon.vue'

const props = defineProps({
  execution: {
    type: Object,
    required: true
  },
  canCancel: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['cancel'])

// Computed properties
const currentStatusText = computed(() => {
  return EXECUTION_STEP_LABELS[props.execution.status] || props.execution.status
})

const statusIndicatorClass = computed(() => {
  const baseClass = 'w-2 h-2 rounded-full'
  
  switch (props.execution.status) {
    case EXECUTION_STEPS.COMPLETE:
      return `${baseClass} bg-green-500`
    case EXECUTION_STEPS.ERROR:
    case EXECUTION_STEPS.CANCELLED:
      return `${baseClass} bg-red-500`
    case EXECUTION_STEPS.IDLE:
      return `${baseClass} bg-surface-hover`
    default:
      return `${baseClass} bg-blue-500 animate-pulse`
  }
})

const statusTextClass = computed(() => {
  switch (props.execution.status) {
    case EXECUTION_STEPS.COMPLETE:
      return 'text-green-400'
    case EXECUTION_STEPS.ERROR:
    case EXECUTION_STEPS.CANCELLED:
      return 'text-red-400'
    case EXECUTION_STEPS.IDLE:
      return 'text-text-tertiary'
    default:
      return 'text-blue-400'
  }
})

const progressBarClass = computed(() => {
  switch (props.execution.status) {
    case EXECUTION_STEPS.COMPLETE:
      return 'bg-green-500'
    case EXECUTION_STEPS.ERROR:
    case EXECUTION_STEPS.CANCELLED:
      return 'bg-red-500'
    default:
      return 'bg-blue-500'
  }
})

const timeRemaining = computed(() => {
  if (!props.execution.estimatedTimeRemaining) return null
  
  const minutes = Math.ceil(props.execution.estimatedTimeRemaining / 1000 / 60)
  if (minutes < 1) return '< 1 min'
  if (minutes === 1) return '1 min'
  return `${minutes} mins`
})

const recentMessages = computed(() => {
  return props.execution.messages.slice(-5).reverse()
})

const executionDuration = computed(() => {
  if (!props.execution.startTime || !props.execution.endTime) return 'Unknown'
  
  const durationMs = props.execution.endTime - props.execution.startTime
  const seconds = Math.round(durationMs / 1000)
  
  if (seconds < 60) return `${seconds}s`
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (remainingSeconds === 0) return `${minutes}m`
  return `${minutes}m ${remainingSeconds}s`
})

// Methods
const isCurrentStep = (step) => {
  return step.id === props.execution.currentStep && 
         ![EXECUTION_STEPS.COMPLETE, EXECUTION_STEPS.ERROR, EXECUTION_STEPS.CANCELLED].includes(props.execution.status)
}

const getStepClass = (step, index) => {
  return {
    'opacity-50': !step.completed && !isCurrentStep(step),
    'opacity-100': step.completed || isCurrentStep(step)
  }
}

const getStepIndicatorClass = (step) => {
  const baseClass = 'w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300'
  
  if (step.completed) {
    return `${baseClass} bg-green-500`
  } else if (isCurrentStep(step)) {
    return `${baseClass} bg-blue-500 ring-4 ring-blue-500/20`
  } else {
    return `${baseClass} bg-surface`
  }
}

const getStepTextClass = (step) => {
  if (step.completed) {
    return 'text-text-primary'
  } else if (isCurrentStep(step)) {
    return 'text-blue-400'
  } else {
    return 'text-text-tertiary'
  }
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}
</script>

<style scoped>
.execution-step {
  @apply transition-all duration-300;
}

.fade-in {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Custom scrollbar for messages */
.max-h-32::-webkit-scrollbar {
  width: 4px;
}

.max-h-32::-webkit-scrollbar-track {
  background: #1e293b;
}

.max-h-32::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 2px;
}

.max-h-32::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>