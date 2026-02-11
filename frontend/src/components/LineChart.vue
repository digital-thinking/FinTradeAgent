<template>
  <canvas ref="canvas" class="h-64 w-full"></canvas>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import Chart from 'chart.js/auto'
import { useTheme } from '../composables/useTheme'

const props = defineProps({
  labels: {
    type: Array,
    default: () => []
  },
  datasets: {
    type: Array,
    default: () => []
  }
})

const canvas = ref(null)
let chartInstance = null

const { getChartTheme } = useTheme()

const chartOptions = computed(() => {
  const theme = getChartTheme()
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { 
          color: theme.colors.text,
          usePointStyle: true,
          padding: 20
        }
      },
      tooltip: {
        backgroundColor: theme.colors.surface,
        titleColor: theme.colors.text,
        bodyColor: theme.colors.text,
        borderColor: theme.colors.border,
        borderWidth: 1
      }
    },
    scales: {
      x: {
        ticks: { 
          color: theme.colors.textSecondary 
        },
        grid: { 
          color: theme.colors.grid,
          borderColor: theme.colors.border
        }
      },
      y: {
        ticks: { 
          color: theme.colors.textSecondary 
        },
        grid: { 
          color: theme.colors.grid,
          borderColor: theme.colors.border
        }
      }
    }
  }
})

const renderChart = () => {
  if (!canvas.value) return
  if (chartInstance) chartInstance.destroy()

  chartInstance = new Chart(canvas.value, {
    type: 'line',
    data: {
      labels: props.labels,
      datasets: props.datasets
    },
    options: chartOptions.value
  })
}

onMounted(renderChart)
watch(() => [props.labels, props.datasets], renderChart, { deep: true })
// Watch theme changes and re-render chart
watch(chartOptions, renderChart, { deep: true })

onBeforeUnmount(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
