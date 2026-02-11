<template>
  <BaseCard>
    <p class="text-xs uppercase tracking-[0.2em] text-text-tertiary">{{ label }}</p>
    <div class="mt-3 flex items-baseline justify-between">
      <p class="font-display text-3xl font-semibold text-text-primary">{{ value }}</p>
      <span v-if="trend" class="text-sm font-semibold" :class="trendClass">
        {{ trend }}
      </span>
    </div>
    <p v-if="description" class="mt-2 text-sm text-text-secondary">{{ description }}</p>
  </BaseCard>
</template>

<script setup>
import { computed } from 'vue'
import BaseCard from './BaseCard.vue'

const props = defineProps({
  label: String,
  value: String,
  trend: String,
  trendDirection: {
    type: String,
    default: 'up'
  },
  description: String
})

const trendClass = computed(() =>
  props.trendDirection === 'down' ? 'text-error' : 'text-success'
)
</script>
