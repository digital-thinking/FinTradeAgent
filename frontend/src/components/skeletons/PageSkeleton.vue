<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="bg-surface/50 rounded-xl border border-border/50 p-6">
      <div class="flex items-center justify-between">
        <div class="space-y-2">
          <BaseSkeleton width="80px" height="1rem" />
          <BaseSkeleton width="200px" height="2rem" />
          <BaseSkeleton width="300px" height="1rem" />
        </div>
        <div class="flex gap-3">
          <BaseSkeleton width="80px" height="2.5rem" rounded="lg" />
          <BaseSkeleton width="120px" height="2.5rem" rounded="lg" />
        </div>
      </div>
    </div>

    <!-- Dynamic content based on type -->
    <template v-if="type === 'dashboard'">
      <DashboardSkeleton />
    </template>

    <template v-else-if="type === 'table'">
      <div class="bg-surface/50 rounded-xl border border-border/50">
        <TableSkeleton :rows="tableRows" :columns="tableColumns" />
      </div>
    </template>

    <template v-else-if="type === 'cards'">
      <div :class="cardGridClass">
        <PortfolioCardSkeleton v-for="i in cardCount" :key="`card-${i}`" />
      </div>
    </template>

    <template v-else-if="type === 'detail'">
      <!-- Detail page layout -->
      <div class="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <!-- Main content -->
        <div class="space-y-6">
          <!-- Content blocks -->
          <div v-for="i in 3" :key="`block-${i}`" class="bg-surface/50 rounded-xl border border-border/50 p-6">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <BaseSkeleton width="150px" height="1.5rem" />
                <BaseSkeleton width="100px" height="1.5rem" rounded="full" />
              </div>
              <BaseSkeleton width="100%" height="200px" />
              <div class="flex gap-2">
                <BaseSkeleton width="80px" height="2rem" rounded="lg" />
                <BaseSkeleton width="100px" height="2rem" rounded="lg" />
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <div v-for="i in 2" :key="`sidebar-${i}`" class="bg-surface/50 rounded-xl border border-border/50 p-6">
            <BaseSkeleton width="120px" height="1.5rem" class="mb-4" />
            <div class="space-y-3">
              <div v-for="j in 4" :key="`sidebar-item-${j}`" class="flex items-center justify-between">
                <BaseSkeleton width="80px" height="1rem" />
                <BaseSkeleton width="60px" height="1rem" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- Generic content blocks -->
      <div class="space-y-6">
        <div v-for="i in contentBlocks" :key="`content-${i}`" class="bg-surface/50 rounded-xl border border-border/50 p-6">
          <div class="space-y-4">
            <BaseSkeleton width="180px" height="1.5rem" />
            <div class="space-y-2">
              <BaseSkeleton width="100%" height="1rem" />
              <BaseSkeleton width="85%" height="1rem" />
              <BaseSkeleton width="70%" height="1rem" />
            </div>
            <BaseSkeleton width="100%" height="150px" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BaseSkeleton from './BaseSkeleton.vue'
import DashboardSkeleton from './DashboardSkeleton.vue'
import TableSkeleton from './TableSkeleton.vue'
import PortfolioCardSkeleton from './PortfolioCardSkeleton.vue'

const props = defineProps({
  type: {
    type: String,
    default: 'generic', // 'dashboard', 'table', 'cards', 'detail', 'generic'
    validator: (value) => ['dashboard', 'table', 'cards', 'detail', 'generic'].includes(value)
  },
  contentBlocks: {
    type: Number,
    default: 3
  },
  cardCount: {
    type: Number,
    default: 6
  },
  cardCols: {
    type: String,
    default: 'lg:grid-cols-3'
  },
  tableRows: {
    type: Number,
    default: 8
  },
  tableColumns: {
    type: Array,
    default: () => [
      { key: 'name', width: '100%', subtitle: true },
      { key: 'status', type: 'badge' },
      { key: 'value', type: 'number' },
      { key: 'date', type: 'text', width: '120px' },
      { key: 'actions', type: 'button' }
    ]
  }
})

const cardGridClass = computed(() => {
  return `grid gap-6 ${props.cardCols}`
})
</script>