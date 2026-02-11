<template>
  <div class="space-y-6">
    <!-- Stats cards row -->
    <div class="grid gap-6 lg:grid-cols-3">
      <div v-for="i in 3" :key="`stat-${i}`" class="bg-surface/50 rounded-xl border border-border/50 p-6">
        <div class="flex items-center justify-between">
          <div class="space-y-2">
            <BaseSkeleton width="80px" height="1rem" />
            <BaseSkeleton width="120px" height="2rem" />
            <BaseSkeleton width="100px" height="0.875rem" />
          </div>
          <BaseSkeleton width="48px" height="48px" rounded="lg" />
        </div>
      </div>
    </div>

    <!-- Main content grid -->
    <div class="grid gap-6 lg:grid-cols-[2fr,1fr]">
      <!-- Chart section -->
      <div class="space-y-6">
        <!-- Chart card -->
        <div class="bg-surface/50 rounded-xl border border-border/50">
          <ChartSkeleton type="line" />
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Activity feed -->
        <div class="bg-surface/50 rounded-xl border border-border/50 p-6">
          <div class="flex items-center justify-between mb-4">
            <BaseSkeleton width="120px" height="1.5rem" />
            <BaseSkeleton width="60px" height="1.5rem" rounded="full" />
          </div>
          
          <div class="space-y-4">
            <div v-for="i in 5" :key="`activity-${i}`" class="flex items-start gap-3">
              <BaseSkeleton width="40px" height="40px" rounded="full" />
              <div class="flex-1 space-y-2">
                <BaseSkeleton width="100%" height="1rem" />
                <BaseSkeleton width="70%" height="0.875rem" />
                <BaseSkeleton width="50%" height="0.75rem" />
              </div>
            </div>
          </div>
        </div>

        <!-- Status widget -->
        <div class="bg-surface/50 rounded-xl border border-border/50 p-6">
          <div class="flex items-center justify-between mb-4">
            <BaseSkeleton width="100px" height="1.5rem" />
            <BaseSkeleton width="60px" height="1.5rem" rounded="full" />
          </div>
          
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <BaseSkeleton width="80px" height="1rem" />
              <BaseSkeleton width="60px" height="1rem" />
            </div>
            <div class="flex items-center justify-between">
              <BaseSkeleton width="70px" height="1rem" />
              <BaseSkeleton width="80px" height="1rem" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import BaseSkeleton from './BaseSkeleton.vue'
import ChartSkeleton from './ChartSkeleton.vue'
</script>