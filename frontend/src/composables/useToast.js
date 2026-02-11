import { ref, reactive } from 'vue'

export const TOAST_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
}

// Global toast state
const toasts = ref([])
let toastId = 0

export function useToast() {
  const show = (message, type = TOAST_TYPES.INFO, options = {}) => {
    const {
      duration = type === TOAST_TYPES.ERROR ? 8000 : 4000,
      persistent = false,
      actions = []
    } = options

    const toast = {
      id: ++toastId,
      message,
      type,
      duration,
      persistent,
      actions,
      createdAt: Date.now(),
      visible: true
    }

    toasts.value.push(toast)

    // Auto-remove after duration (unless persistent)
    if (!persistent && duration > 0) {
      setTimeout(() => {
        remove(toast.id)
      }, duration)
    }

    return toast.id
  }

  const remove = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value[index].visible = false
      // Remove from array after animation
      setTimeout(() => {
        const currentIndex = toasts.value.findIndex(t => t.id === id)
        if (currentIndex > -1) {
          toasts.value.splice(currentIndex, 1)
        }
      }, 300)
    }
  }

  const clear = () => {
    toasts.value.forEach(toast => {
      toast.visible = false
    })
    setTimeout(() => {
      toasts.value.splice(0)
    }, 300)
  }

  // Convenience methods
  const success = (message, options = {}) => show(message, TOAST_TYPES.SUCCESS, options)
  const error = (message, options = {}) => show(message, TOAST_TYPES.ERROR, options)
  const warning = (message, options = {}) => show(message, TOAST_TYPES.WARNING, options)
  const info = (message, options = {}) => show(message, TOAST_TYPES.INFO, options)

  return {
    toasts,
    show,
    remove,
    clear,
    success,
    error,
    warning,
    info
  }
}