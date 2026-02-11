<template>
  <span class="rounded-full px-3 py-1 text-xs font-semibold" :class="badgeClass">
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: 'Unknown'
  },
  tone: {
    type: String,
    default: 'neutral'
  }
})

const badgeClass = computed(() => {
  if (props.tone === 'success') return 'bg-success/20 text-success'
  if (props.tone === 'warning') return 'bg-warning/20 text-warning'
  if (props.tone === 'danger') return 'bg-error/20 text-error'
  return 'bg-surface/60 text-text-secondary'
})
</script>
