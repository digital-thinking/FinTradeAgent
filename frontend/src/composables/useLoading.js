import { ref, reactive, computed } from 'vue'

// Global loading states
const globalLoadingStates = reactive({})
const globalOperations = ref(new Set())

export function useLoading(key = null) {
  // If no key provided, create local loading state
  const localLoading = ref(false)
  const localOperations = ref(new Set())
  
  // Use global or local state based on key
  const isLoading = key 
    ? computed(() => globalLoadingStates[key] || false)
    : localLoading
  
  const operations = key 
    ? computed(() => Array.from(globalOperations.value).filter(op => op.startsWith(key + ':')))
    : computed(() => Array.from(localOperations.value))

  const startLoading = (operation = 'default') => {
    if (key) {
      globalLoadingStates[key] = true
      globalOperations.value.add(`${key}:${operation}`)
    } else {
      localLoading.value = true
      localOperations.value.add(operation)
    }
  }

  const stopLoading = (operation = 'default') => {
    if (key) {
      globalOperations.value.delete(`${key}:${operation}`)
      if (!Array.from(globalOperations.value).some(op => op.startsWith(key + ':'))) {
        globalLoadingStates[key] = false
      }
    } else {
      localOperations.value.delete(operation)
      if (localOperations.value.size === 0) {
        localLoading.value = false
      }
    }
  }

  const isOperationLoading = (operation) => {
    if (key) {
      return globalOperations.value.has(`${key}:${operation}`)
    } else {
      return localOperations.value.has(operation)
    }
  }

  const withLoading = (fn, operation = 'default') => {
    return async (...args) => {
      startLoading(operation)
      try {
        return await fn(...args)
      } finally {
        stopLoading(operation)
      }
    }
  }

  const withOptimisticUpdate = (updateFn, apiFn, rollbackFn) => {
    return async (...args) => {
      // Apply optimistic update immediately
      const rollbackData = updateFn(...args)
      
      try {
        // Make API call
        const result = await apiFn(...args)
        return result
      } catch (error) {
        // Rollback optimistic update on error
        if (rollbackFn && rollbackData) {
          rollbackFn(rollbackData)
        }
        throw error
      }
    }
  }

  // Progressive loading helper
  const useProgressiveLoading = (stages = []) => {
    const currentStage = ref(0)
    const stageProgress = ref(0)
    
    const nextStage = () => {
      if (currentStage.value < stages.length - 1) {
        currentStage.value++
        stageProgress.value = 0
      }
    }
    
    const updateProgress = (progress) => {
      stageProgress.value = Math.min(100, Math.max(0, progress))
    }
    
    const currentStageInfo = computed(() => {
      return stages[currentStage.value] || { name: 'Loading...', description: '' }
    })
    
    const overallProgress = computed(() => {
      const baseProgress = (currentStage.value / stages.length) * 100
      const stageContribution = (stageProgress.value / 100) * (100 / stages.length)
      return Math.min(100, baseProgress + stageContribution)
    })
    
    return {
      currentStage,
      stageProgress,
      currentStageInfo,
      overallProgress,
      nextStage,
      updateProgress
    }
  }

  return {
    isLoading,
    operations,
    startLoading,
    stopLoading,
    isOperationLoading,
    withLoading,
    withOptimisticUpdate,
    useProgressiveLoading
  }
}

// Specialized loading composables
export function useDataLoading() {
  return useLoading('data')
}

export function useApiLoading() {
  return useLoading('api')
}

export function useFormLoading() {
  return useLoading('form')
}

// Loading delay helper - prevents flash for fast operations
export function useDelayedLoading(delay = 300) {
  const loading = ref(false)
  const delayedLoading = ref(false)
  let timeoutId = null

  const startLoading = () => {
    loading.value = true
    timeoutId = setTimeout(() => {
      delayedLoading.value = true
    }, delay)
  }

  const stopLoading = () => {
    loading.value = false
    delayedLoading.value = false
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return {
    loading,
    delayedLoading,
    startLoading,
    stopLoading
  }
}