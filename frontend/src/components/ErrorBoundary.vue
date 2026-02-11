<template>
  <div v-if="hasError" class="error-boundary">
    <div class="p-6 bg-red-900/20 border border-red-500/30 rounded-lg">
      <div class="flex items-start gap-4">
        <XCircleIcon class="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
        <div class="flex-grow">
          <h3 class="text-lg font-semibold text-red-300 mb-2">
            {{ title }}
          </h3>
          <p class="text-red-200 text-sm leading-relaxed mb-4">
            {{ message }}
          </p>
          
          <!-- Error details (collapsible) -->
          <details v-if="showDetails && errorDetails" class="mb-4">
            <summary class="text-sm text-red-400 cursor-pointer hover:text-red-300 mb-2">
              Error Details
            </summary>
            <pre class="text-xs text-red-200 bg-red-900/30 p-3 rounded overflow-x-auto whitespace-pre-wrap">{{ errorDetails }}</pre>
          </details>
          
          <!-- Actions -->
          <div class="flex gap-3">
            <BaseButton
              size="sm"
              variant="danger"
              @click="retry"
            >
              Try Again
            </BaseButton>
            <BaseButton
              v-if="showReload"
              size="sm"
              variant="ghost"
              @click="reload"
            >
              Reload Page
            </BaseButton>
            <BaseButton
              v-if="showReport"
              size="sm"
              variant="ghost"
              @click="reportError"
            >
              Report Issue
            </BaseButton>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Fallback content when there's an error -->
  <div v-else-if="fallbackComponent">
    <component :is="fallbackComponent" v-bind="fallbackProps" />
  </div>
  
  <!-- Normal content -->
  <slot v-else></slot>
</template>

<script setup>
import { ref, onErrorCaptured, getCurrentInstance } from 'vue'
import BaseButton from './BaseButton.vue'
import XCircleIcon from './icons/XCircleIcon.vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Something went wrong'
  },
  message: {
    type: String,
    default: 'An error occurred while rendering this component. Please try again.'
  },
  showDetails: {
    type: Boolean,
    default: false
  },
  showReload: {
    type: Boolean,
    default: true
  },
  showReport: {
    type: Boolean,
    default: false
  },
  fallbackComponent: {
    type: [String, Object],
    default: null
  },
  fallbackProps: {
    type: Object,
    default: () => ({})
  },
  onError: {
    type: Function,
    default: null
  }
})

const emit = defineEmits(['error', 'retry'])

const hasError = ref(false)
const errorDetails = ref('')
const errorInstance = ref(null)

// Capture errors from child components
onErrorCaptured((error, instance, info) => {
  hasError.value = true
  errorDetails.value = `${error.message}\n\nComponent: ${instance?.$options.name || 'Unknown'}\nInfo: ${info}\n\nStack:\n${error.stack}`
  errorInstance.value = instance
  
  console.error('Error captured by ErrorBoundary:', error, instance, info)
  
  // Call custom error handler if provided
  if (props.onError) {
    props.onError(error, instance, info)
  }
  
  // Emit error event
  emit('error', { error, instance, info })
  
  // Prevent the error from propagating further
  return false
})

const retry = () => {
  hasError.value = false
  errorDetails.value = ''
  errorInstance.value = null
  emit('retry')
  
  // Force re-render by updating a key or similar mechanism
  // This is a simple approach - in a real app you might want more sophisticated retry logic
  getCurrentInstance()?.proxy?.$forceUpdate()
}

const reload = () => {
  window.location.reload()
}

const reportError = () => {
  // In a real application, this would send the error to a logging service
  console.log('Reporting error:', {
    title: props.title,
    message: props.message,
    details: errorDetails.value,
    url: window.location.href,
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString()
  })
  
  // For now, just copy error details to clipboard
  if (navigator.clipboard && errorDetails.value) {
    navigator.clipboard.writeText(errorDetails.value).then(() => {
      alert('Error details copied to clipboard')
    }).catch(() => {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = errorDetails.value
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      alert('Error details copied to clipboard')
    })
  }
}
</script>

<style scoped>
.error-boundary {
  @apply my-4;
}

/* Ensure error details don't break layout */
pre {
  word-break: break-word;
  white-space: pre-wrap;
}
</style>