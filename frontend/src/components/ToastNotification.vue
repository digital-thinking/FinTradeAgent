<template>
  <teleport to="body">
    <!-- Mobile-friendly positioning: top center on mobile, top right on desktop -->
    <div class="fixed top-4 left-4 right-4 sm:left-auto sm:right-4 z-50 space-y-2 max-w-md sm:max-w-sm mx-auto sm:mx-0">
      <transition-group 
        name="toast" 
        tag="div" 
        class="space-y-2"
        @before-enter="onBeforeEnter"
        @enter="onEnter"
        @leave="onLeave"
      >
        <div
          v-for="toast in visibleToasts"
          :key="toast.id"
          :class="getToastClass(toast)"
          class="toast-item"
        >
          <div class="flex items-start gap-3 p-4">
            <!-- Icon -->
            <div class="flex-shrink-0">
              <CheckCircleIcon v-if="toast.type === 'success'" class="w-5 h-5 text-green-400" />
              <ExclamationTriangleIcon v-else-if="toast.type === 'warning'" class="w-5 h-5 text-yellow-400" />
              <XCircleIcon v-else-if="toast.type === 'error'" class="w-5 h-5 text-red-400" />
              <InformationCircleIcon v-else class="w-5 h-5 text-blue-400" />
            </div>

            <!-- Content -->
            <div class="flex-grow min-w-0">
              <p class="text-sm font-medium text-text-primary">{{ toast.message }}</p>
              
              <!-- Actions -->
              <div v-if="toast.actions.length > 0" class="mt-3 flex gap-2">
                <button
                  v-for="action in toast.actions"
                  :key="action.label"
                  @click="handleAction(toast, action)"
                  class="text-xs font-medium px-2 py-1 rounded hover:bg-white/10 transition-colors"
                  :class="getActionClass(toast.type)"
                >
                  {{ action.label }}
                </button>
              </div>
            </div>

            <!-- Close button -->
            <button 
              @click="$emit('close', toast.id)"
              class="flex-shrink-0 p-0.5 rounded hover:bg-white/10 transition-colors"
            >
              <XMarkIcon class="w-4 h-4 text-text-tertiary" />
            </button>
          </div>

          <!-- Progress bar for non-persistent toasts -->
          <div 
            v-if="!toast.persistent && toast.duration > 0" 
            class="toast-progress"
            :class="getProgressClass(toast.type)"
            :style="{ animationDuration: toast.duration + 'ms' }"
          ></div>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useToast } from '../composables/useToast'
import CheckCircleIcon from './icons/CheckCircleIcon.vue'
import ExclamationTriangleIcon from './icons/ExclamationTriangleIcon.vue'
import XCircleIcon from './icons/XCircleIcon.vue'
import InformationCircleIcon from './icons/InformationCircleIcon.vue'
import XMarkIcon from './icons/XMarkIcon.vue'

const emit = defineEmits(['close'])

const { toasts } = useToast()

const visibleToasts = computed(() => toasts.value.filter(toast => toast.visible))

const getToastClass = (toast) => {
  const baseClass = 'relative rounded-lg shadow-theme-lg border backdrop-blur-sm overflow-hidden'
  
  switch (toast.type) {
    case 'success':
      return `${baseClass} bg-green-900/90 dark:bg-green-900/90 border-green-500/50`
    case 'error':
      return `${baseClass} bg-red-900/90 dark:bg-red-900/90 border-red-500/50`
    case 'warning':
      return `${baseClass} bg-yellow-900/90 dark:bg-yellow-900/90 border-yellow-500/50`
    default:
      return `${baseClass} bg-blue-900/90 dark:bg-blue-900/90 border-blue-500/50`
  }
}

const getActionClass = (type) => {
  switch (type) {
    case 'success':
      return 'text-green-300 hover:text-green-200'
    case 'error':
      return 'text-red-300 hover:text-red-200'
    case 'warning':
      return 'text-yellow-300 hover:text-yellow-200'
    default:
      return 'text-blue-300 hover:text-blue-200'
  }
}

const getProgressClass = (type) => {
  switch (type) {
    case 'success':
      return 'bg-green-500'
    case 'error':
      return 'bg-red-500'
    case 'warning':
      return 'bg-yellow-500'
    default:
      return 'bg-blue-500'
  }
}

const handleAction = (toast, action) => {
  if (action.handler) {
    action.handler()
  }
  if (action.dismissOnClick !== false) {
    emit('close', toast.id)
  }
}

// Animation hooks
const onBeforeEnter = (el) => {
  el.style.opacity = '0'
  el.style.transform = 'translateX(100%)'
}

const onEnter = (el, done) => {
  el.offsetHeight // Trigger reflow
  el.style.transition = 'all 0.3s ease-out'
  el.style.opacity = '1'
  el.style.transform = 'translateX(0)'
  setTimeout(done, 300)
}

const onLeave = (el, done) => {
  el.style.transition = 'all 0.3s ease-in'
  el.style.opacity = '0'
  el.style.transform = 'translateX(100%)'
  setTimeout(done, 300)
}
</script>

<style scoped>
.toast-item {
  @apply transition-all duration-300 ease-out;
  max-width: 100%;
  width: 100%;
}

@media (min-width: 640px) {
  .toast-item {
    max-width: 400px;
    width: auto;
  }
}

.toast-progress {
  @apply absolute bottom-0 left-0 h-1;
  animation: toast-progress linear;
  width: 100%;
  transform-origin: left;
}

@keyframes toast-progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>