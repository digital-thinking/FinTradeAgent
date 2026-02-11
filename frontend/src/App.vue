<template>
  <AppLayout />
  <ToastNotification @close="handleToastClose" />
  <PerformanceMonitor />
</template>

<script setup>
import { onMounted } from 'vue'
import AppLayout from './layouts/AppLayout.vue'
import ToastNotification from './components/ToastNotification.vue'
import PerformanceMonitor from './components/PerformanceMonitor.vue'
import { useToast } from './composables/useToast'
import { useTheme } from './composables/useTheme'

const { remove } = useToast()
const { initializeTheme, watchSystemTheme } = useTheme()

const handleToastClose = (toastId) => {
  remove(toastId)
}

// Initialize theme system when app mounts
onMounted(() => {
  initializeTheme()
  watchSystemTheme()
})
</script>
