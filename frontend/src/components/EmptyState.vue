<template>
  <div class="flex flex-col items-start gap-2 rounded-2xl border border-dashed border-border/70 p-6 text-text-secondary">
    <p class="font-semibold text-text-primary">{{ title }}</p>
    <p class="text-sm text-text-tertiary">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: String,
  description: String
})
</script>
