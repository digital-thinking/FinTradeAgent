<template>
  <div class="p-6 bg-surface/50 rounded-xl border border-border/50">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div class="space-y-2">
        <BaseSkeleton width="120px" height="1.5rem" />
        <BaseSkeleton width="200px" height="1rem" />
      </div>
      <BaseSkeleton width="60px" height="2rem" rounded="lg" />
    </div>

    <!-- Main content -->
    <div class="space-y-4">
      <!-- Value display -->
      <div class="text-center py-4">
        <BaseSkeleton width="120px" height="2.5rem" class="mx-auto mb-2" />
        <BaseSkeleton width="80px" height="1rem" class="mx-auto" />
      </div>

      <!-- Metrics -->
      <div class="grid grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="space-y-1">
          <BaseSkeleton width="100%" height="1rem" />
          <BaseSkeleton width="60%" height="0.875rem" />
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2 pt-2">
        <BaseSkeleton width="80px" height="2rem" rounded="lg" />
        <BaseSkeleton width="100px" height="2rem" rounded="lg" />
      </div>
    </div>
  </div>
</template>

<script setup>
import BaseSkeleton from './BaseSkeleton.vue'
</script>