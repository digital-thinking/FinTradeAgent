<template>
  <div v-if="showStatus" class="flex items-center gap-2 text-xs">
    <div :class="statusDotClass"></div>
    <span :class="statusTextClass">{{ statusText }}</span>
    <button 
      v-if="canReconnect" 
      @click="onReconnect"
      class="ml-1 px-2 py-0.5 bg-blue-600 hover:bg-blue-700 rounded text-xs text-text-primary transition-colors"
    >
      Reconnect
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { WEBSOCKET_STATES } from '../composables/useWebSocket'

const props = defineProps({
  state: {
    type: String,
    required: true
  },
  error: {
    type: Error,
    default: null
  },
  reconnectAttempts: {
    type: Number,
    default: 0
  },
  showWhenConnected: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['reconnect'])

const showStatus = computed(() => {
  return props.showWhenConnected || props.state !== WEBSOCKET_STATES.CONNECTED
})

const statusDotClass = computed(() => {
  const baseClass = 'w-2 h-2 rounded-full'
  switch (props.state) {
    case WEBSOCKET_STATES.CONNECTED:
      return `${baseClass} bg-green-500 animate-pulse`
    case WEBSOCKET_STATES.CONNECTING:
      return `${baseClass} bg-yellow-500 animate-pulse`
    case WEBSOCKET_STATES.ERROR:
      return `${baseClass} bg-red-500`
    default:
      return `${baseClass} bg-surface-hover`
  }
})

const statusTextClass = computed(() => {
  switch (props.state) {
    case WEBSOCKET_STATES.CONNECTED:
      return 'text-green-400'
    case WEBSOCKET_STATES.CONNECTING:
      return 'text-yellow-400'
    case WEBSOCKET_STATES.ERROR:
      return 'text-red-400'
    default:
      return 'text-text-tertiary'
  }
})

const statusText = computed(() => {
  if (props.compact) {
    switch (props.state) {
      case WEBSOCKET_STATES.CONNECTED:
        return 'Live'
      case WEBSOCKET_STATES.CONNECTING:
        return 'Connecting...'
      case WEBSOCKET_STATES.ERROR:
        return 'Error'
      default:
        return 'Offline'
    }
  }
  
  switch (props.state) {
    case WEBSOCKET_STATES.CONNECTED:
      return 'Live updates active'
    case WEBSOCKET_STATES.CONNECTING:
      return 'Connecting to live updates...'
    case WEBSOCKET_STATES.ERROR:
      return props.error?.message || 'Connection error'
    default:
      return 'Live updates offline'
  }
})

const canReconnect = computed(() => {
  return props.state === WEBSOCKET_STATES.ERROR || props.state === WEBSOCKET_STATES.DISCONNECTED
})

const onReconnect = () => {
  emit('reconnect')
}
</script>