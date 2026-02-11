<template>
  <teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto">
      <!-- Backdrop -->
      <div 
        class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        @click="cancel"
      ></div>

      <!-- Dialog -->
      <div class="flex min-h-full items-center justify-center p-4">
        <div 
          class="relative transform overflow-hidden rounded-lg bg-surface text-left shadow-xl transition-all w-full max-w-lg"
          @click.stop
        >
          <!-- Header -->
          <div class="bg-surface px-6 py-4 border-b border-border">
            <div class="flex items-center gap-3">
              <!-- Icon -->
              <div 
                class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center"
                :class="iconBackgroundClass"
              >
                <ExclamationTriangleIcon 
                  v-if="variant === 'warning'" 
                  class="w-6 h-6" 
                  :class="iconClass" 
                />
                <XCircleIcon 
                  v-else-if="variant === 'danger'" 
                  class="w-6 h-6" 
                  :class="iconClass" 
                />
                <InformationCircleIcon 
                  v-else 
                  class="w-6 h-6" 
                  :class="iconClass" 
                />
              </div>

              <div>
                <h3 class="text-lg font-semibold text-text-primary">
                  {{ title }}
                </h3>
              </div>
            </div>
          </div>

          <!-- Content -->
          <div class="bg-surface px-6 py-4">
            <p class="text-sm text-text-secondary leading-relaxed">
              {{ message }}
            </p>
            
            <!-- Additional details -->
            <div v-if="details" class="mt-3 p-3 bg-surface rounded text-sm text-text-tertiary">
              {{ details }}
            </div>

            <!-- Input field for confirmation text -->
            <div v-if="confirmationText" class="mt-4">
              <label class="block text-sm font-medium text-text-tertiary mb-2">
                Type "{{ confirmationText }}" to confirm:
              </label>
              <input
                v-model="inputValue"
                type="text"
                class="w-full px-3 py-2 bg-surface border border-slate-600 rounded-md text-text-primary placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                :placeholder="confirmationText"
                @keyup.enter="confirm"
                @keyup.escape="cancel"
              />
            </div>
          </div>

          <!-- Actions -->
          <div class="bg-surface px-6 py-4 flex justify-end gap-3">
            <BaseButton
              variant="ghost"
              @click="cancel"
            >
              {{ cancelText }}
            </BaseButton>
            <BaseButton
              :variant="confirmVariant"
              :disabled="!canConfirm"
              @click="confirm"
            >
              {{ confirmText }}
            </BaseButton>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BaseButton from './BaseButton.vue'
import ExclamationTriangleIcon from './icons/ExclamationTriangleIcon.vue'
import XCircleIcon from './icons/XCircleIcon.vue'
import InformationCircleIcon from './icons/InformationCircleIcon.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Confirm Action'
  },
  message: {
    type: String,
    required: true
  },
  details: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'info', // 'info', 'warning', 'danger'
    validator: (value) => ['info', 'warning', 'danger'].includes(value)
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  confirmationText: {
    type: String,
    default: '' // If provided, user must type this text to confirm
  }
})

const emit = defineEmits(['confirm', 'cancel', 'close'])

const inputValue = ref('')

// Reset input when dialog opens/closes
watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    inputValue.value = ''
  }
})

const iconClass = computed(() => {
  switch (props.variant) {
    case 'warning':
      return 'text-yellow-400'
    case 'danger':
      return 'text-red-400'
    default:
      return 'text-blue-400'
  }
})

const iconBackgroundClass = computed(() => {
  switch (props.variant) {
    case 'warning':
      return 'bg-yellow-900/50'
    case 'danger':
      return 'bg-red-900/50'
    default:
      return 'bg-blue-900/50'
  }
})

const confirmVariant = computed(() => {
  switch (props.variant) {
    case 'danger':
      return 'danger'
    case 'warning':
      return 'warning'
    default:
      return 'primary'
  }
})

const canConfirm = computed(() => {
  if (!props.confirmationText) return true
  return inputValue.value.trim().toLowerCase() === props.confirmationText.toLowerCase()
})

const confirm = () => {
  if (!canConfirm.value) return
  emit('confirm')
  emit('close')
}

const cancel = () => {
  emit('cancel')
  emit('close')
}

// Handle escape key
document.addEventListener('keyup', (e) => {
  if (e.key === 'Escape' && props.isOpen) {
    cancel()
  }
})
</script>

<style scoped>
/* Animation classes for the dialog */
.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.2s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
</style>