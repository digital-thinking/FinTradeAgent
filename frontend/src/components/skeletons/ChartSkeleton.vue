<template>
  <div class="chart-skeleton p-6">
    <!-- Chart title and controls -->
    <div class="flex items-center justify-between mb-6">
      <div class="space-y-2">
        <BaseSkeleton width="180px" height="1.5rem" />
        <BaseSkeleton width="120px" height="1rem" />
      </div>
      <div class="flex gap-2">
        <BaseSkeleton width="60px" height="2rem" rounded="lg" />
        <BaseSkeleton width="80px" height="2rem" rounded="lg" />
      </div>
    </div>

    <!-- Chart area -->
    <div class="relative" :style="{ height: chartHeight }">
      <!-- Y-axis labels -->
      <div class="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between py-4">
        <BaseSkeleton 
          v-for="i in 5" 
          :key="`y-${i}`"
          width="40px" 
          height="0.875rem"
        />
      </div>

      <!-- Chart content area -->
      <div class="ml-16 h-full relative">
        <!-- Chart background with grid lines -->
        <div class="absolute inset-0 flex flex-col justify-between">
          <div 
            v-for="i in 5" 
            :key="`grid-${i}`"
            class="h-px bg-surface/30"
          ></div>
        </div>

        <!-- Chart data visualization -->
        <div v-if="type === 'line'" class="absolute inset-0">
          <!-- Line chart simulation -->
          <svg class="w-full h-full">
            <defs>
              <linearGradient id="skeleton-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#475569;stop-opacity:0.8" />
                <stop offset="50%" style="stop-color:#64748b;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#475569;stop-opacity:0.8" />
              </linearGradient>
            </defs>
            <path 
              :d="linePathData" 
              stroke="url(#skeleton-gradient)" 
              stroke-width="2" 
              fill="none"
              class="animate-pulse"
            />
            <!-- Data points -->
            <circle 
              v-for="(point, index) in linePoints" 
              :key="`point-${index}`"
              :cx="point.x" 
              :cy="point.y" 
              r="4" 
              fill="url(#skeleton-gradient)"
              class="animate-pulse"
              :style="{ animationDelay: `${index * 0.1}s` }"
            />
          </svg>
        </div>

        <div v-else-if="type === 'bar'" class="absolute inset-0 flex items-end justify-between px-2">
          <!-- Bar chart simulation -->
          <BaseSkeleton 
            v-for="i in 8" 
            :key="`bar-${i}`"
            :width="`${Math.max(20, 100 / 8 - 4)}%`"
            :height="`${Math.random() * 80 + 20}%`"
            class="mx-1"
            :style="{ animationDelay: `${i * 0.1}s` }"
          />
        </div>

        <div v-else class="absolute inset-0 flex items-center justify-center">
          <!-- Generic chart placeholder -->
          <div class="w-3/4 h-3/4 border-2 border-dashed border-slate-600 rounded-lg flex items-center justify-center">
            <BaseSkeleton width="120px" height="1rem" />
          </div>
        </div>
      </div>

      <!-- X-axis labels -->
      <div class="ml-16 mt-4 flex justify-between">
        <BaseSkeleton 
          v-for="i in 6" 
          :key="`x-${i}`"
          width="40px" 
          height="0.875rem"
        />
      </div>
    </div>

    <!-- Chart legend -->
    <div v-if="showLegend" class="flex justify-center gap-6 mt-6">
      <div v-for="i in 3" :key="`legend-${i}`" class="flex items-center gap-2">
        <BaseSkeleton width="12px" height="12px" rounded="full" />
        <BaseSkeleton width="60px" height="0.875rem" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BaseSkeleton from './BaseSkeleton.vue'

const props = defineProps({
  type: {
    type: String,
    default: 'line', // 'line', 'bar', 'generic'
    validator: (value) => ['line', 'bar', 'generic'].includes(value)
  },
  chartHeight: {
    type: String,
    default: '300px'
  },
  showLegend: {
    type: Boolean,
    default: true
  }
})

// Generate mock line chart data
const linePoints = computed(() => {
  const points = []
  const width = 300 // approximate chart width
  const height = 200 // approximate chart height
  
  for (let i = 0; i < 8; i++) {
    points.push({
      x: (i * width) / 7,
      y: height * 0.2 + Math.random() * height * 0.6
    })
  }
  
  return points
})

const linePathData = computed(() => {
  if (linePoints.value.length === 0) return ''
  
  let path = `M ${linePoints.value[0].x} ${linePoints.value[0].y}`
  
  for (let i = 1; i < linePoints.value.length; i++) {
    const point = linePoints.value[i]
    path += ` L ${point.x} ${point.y}`
  }
  
  return path
})
</script>

<style scoped>
.chart-skeleton {
  @apply bg-surface/30 rounded-lg;
}

/* Stagger animation for chart elements */
.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}
</style>