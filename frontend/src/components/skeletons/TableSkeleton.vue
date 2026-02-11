<template>
  <div class="skeleton-table">
    <!-- Table Header -->
    <div class="grid gap-4 p-4 border-b border-border/50" :style="{ gridTemplateColumns }">
      <BaseSkeleton 
        v-for="col in columns" 
        :key="`header-${col.key}`"
        :width="col.headerWidth || '100%'"
        height="1rem"
      />
    </div>

    <!-- Table Rows -->
    <div class="divide-y divide-slate-700/30">
      <div 
        v-for="row in rows" 
        :key="`row-${row}`" 
        class="grid gap-4 p-4 hover:bg-surface/20 transition-colors"
        :style="{ gridTemplateColumns }"
      >
        <div v-for="col in columns" :key="`${row}-${col.key}`">
          <template v-if="col.type === 'avatar'">
            <BaseSkeleton width="2.5rem" height="2.5rem" rounded="full" />
          </template>
          <template v-else-if="col.type === 'badge'">
            <BaseSkeleton width="60px" height="1.5rem" rounded="full" />
          </template>
          <template v-else-if="col.type === 'button'">
            <BaseSkeleton width="70px" height="2rem" rounded="lg" />
          </template>
          <template v-else-if="col.type === 'number'">
            <BaseSkeleton :width="col.width || '80px'" height="1rem" />
          </template>
          <template v-else>
            <div class="space-y-1">
              <BaseSkeleton :width="col.width || '100%'" height="1rem" />
              <BaseSkeleton 
                v-if="col.subtitle" 
                :width="col.subtitleWidth || '70%'" 
                height="0.875rem" 
              />
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import BaseSkeleton from './BaseSkeleton.vue'

const props = defineProps({
  columns: {
    type: Array,
    default: () => [
      { key: 'name', width: '100%', subtitle: true },
      { key: 'status', type: 'badge' },
      { key: 'value', type: 'number' },
      { key: 'actions', type: 'button' }
    ]
  },
  rows: {
    type: Number,
    default: 5
  },
  gridCols: {
    type: String,
    default: null
  }
})

const gridTemplateColumns = computed(() => {
  if (props.gridCols) {
    return props.gridCols
  }
  
  // Auto-generate grid columns based on column types
  return props.columns.map(col => {
    switch (col.type) {
      case 'avatar':
        return 'auto'
      case 'badge':
      case 'button':
        return 'min-content'
      case 'number':
        return '100px'
      default:
        return '1fr'
    }
  }).join(' ')
})
</script>

<script>
import { computed } from 'vue'
</script>

<style scoped>
.skeleton-table {
  @apply bg-surface/30 rounded-lg overflow-hidden;
}
</style>