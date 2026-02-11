<template>
  <button
    :type="type"
    :disabled="disabled"
    class="inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-theme touch-manipulation focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
    :class="[variantClasses, sizeClasses]"
  >
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary'
  },
  size: {
    type: String,
    default: 'default'
  },
  type: {
    type: String,
    default: 'button'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const variantClasses = computed(() => {
  if (props.variant === 'ghost') {
    return 'border border-border bg-transparent text-text-secondary hover:bg-surface-hover hover:text-text-primary'
  }
  if (props.variant === 'danger') {
    return 'bg-error text-text-primary hover:bg-red-500 dark:hover:bg-red-400'
  }
  if (props.variant === 'success') {
    return 'bg-success text-text-primary hover:bg-green-400 dark:hover:bg-green-400'
  }
  return 'bg-primary-500 text-text-primary hover:bg-primary-600 dark:hover:bg-primary-400'
})

const sizeClasses = computed(() => {
  if (props.size === 'sm') {
    return 'px-3 py-1.5 text-xs min-h-[32px]'
  }
  if (props.size === 'lg') {
    return 'px-6 py-3 text-base min-h-[48px]'
  }
  // Default size with good mobile touch target (44px min-height)
  return 'px-4 py-2.5 text-sm min-h-[44px]'
})
</script>
