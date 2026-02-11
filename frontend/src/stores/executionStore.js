import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const EXECUTION_STEPS = {
  IDLE: 'idle',
  INITIALIZING: 'initializing', 
  DATA_FETCHING: 'data_fetching',
  ANALYSIS: 'analysis',
  RECOMMENDATIONS: 'recommendations',
  FINALIZING: 'finalizing',
  COMPLETE: 'complete',
  ERROR: 'error',
  CANCELLED: 'cancelled'
}

export const EXECUTION_STEP_LABELS = {
  [EXECUTION_STEPS.IDLE]: 'Ready',
  [EXECUTION_STEPS.INITIALIZING]: 'Initializing Agent',
  [EXECUTION_STEPS.DATA_FETCHING]: 'Fetching Market Data',
  [EXECUTION_STEPS.ANALYSIS]: 'Analyzing Portfolio',
  [EXECUTION_STEPS.RECOMMENDATIONS]: 'Generating Recommendations',
  [EXECUTION_STEPS.FINALIZING]: 'Finalizing Results',
  [EXECUTION_STEPS.COMPLETE]: 'Complete',
  [EXECUTION_STEPS.ERROR]: 'Error',
  [EXECUTION_STEPS.CANCELLED]: 'Cancelled'
}

export const useExecutionStore = defineStore('execution', () => {
  // State
  const executions = ref(new Map()) // portfolioName -> execution state
  
  // Execution state structure
  const createExecutionState = () => ({
    id: null,
    portfolioName: '',
    status: EXECUTION_STEPS.IDLE,
    currentStep: EXECUTION_STEPS.IDLE,
    progress: 0, // Overall progress (0-100)
    stepProgress: 0, // Current step progress (0-100)
    startTime: null,
    endTime: null,
    estimatedTimeRemaining: null,
    messages: [],
    error: null,
    cancellable: false,
    steps: [
      { id: EXECUTION_STEPS.INITIALIZING, label: EXECUTION_STEP_LABELS[EXECUTION_STEPS.INITIALIZING], progress: 0, completed: false },
      { id: EXECUTION_STEPS.DATA_FETCHING, label: EXECUTION_STEP_LABELS[EXECUTION_STEPS.DATA_FETCHING], progress: 0, completed: false },
      { id: EXECUTION_STEPS.ANALYSIS, label: EXECUTION_STEP_LABELS[EXECUTION_STEPS.ANALYSIS], progress: 0, completed: false },
      { id: EXECUTION_STEPS.RECOMMENDATIONS, label: EXECUTION_STEP_LABELS[EXECUTION_STEPS.RECOMMENDATIONS], progress: 0, completed: false },
      { id: EXECUTION_STEPS.FINALIZING, label: EXECUTION_STEP_LABELS[EXECUTION_STEPS.FINALIZING], progress: 0, completed: false }
    ]
  })
  
  // Getters
  const getExecution = (portfolioName) => {
    return computed(() => executions.value.get(portfolioName) || createExecutionState())
  }
  
  const isExecuting = (portfolioName) => {
    return computed(() => {
      const execution = executions.value.get(portfolioName)
      return execution && ![EXECUTION_STEPS.IDLE, EXECUTION_STEPS.COMPLETE, EXECUTION_STEPS.ERROR, EXECUTION_STEPS.CANCELLED].includes(execution.status)
    })
  }
  
  const getActiveExecutions = computed(() => {
    return Array.from(executions.value.values()).filter(execution => 
      ![EXECUTION_STEPS.IDLE, EXECUTION_STEPS.COMPLETE, EXECUTION_STEPS.ERROR, EXECUTION_STEPS.CANCELLED].includes(execution.status)
    )
  })
  
  // Actions
  const startExecution = (portfolioName, executionId = null) => {
    const execution = createExecutionState()
    execution.id = executionId || `exec_${Date.now()}`
    execution.portfolioName = portfolioName
    execution.status = EXECUTION_STEPS.INITIALIZING
    execution.currentStep = EXECUTION_STEPS.INITIALIZING
    execution.startTime = new Date()
    execution.cancellable = true
    
    executions.value.set(portfolioName, execution)
    persistExecution(portfolioName, execution)
    
    return execution
  }
  
  const updateExecutionStep = (portfolioName, step, stepProgress = 0, overallProgress = null) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    // Update current step
    execution.currentStep = step
    execution.status = step
    execution.stepProgress = stepProgress
    
    // Update overall progress if provided
    if (overallProgress !== null) {
      execution.progress = overallProgress
    } else {
      // Calculate overall progress based on step
      const stepIndex = execution.steps.findIndex(s => s.id === step)
      if (stepIndex >= 0) {
        const baseProgress = (stepIndex / execution.steps.length) * 100
        const stepContribution = (stepProgress / 100) * (100 / execution.steps.length)
        execution.progress = Math.min(100, baseProgress + stepContribution)
      }
    }
    
    // Update step in steps array
    const stepObj = execution.steps.find(s => s.id === step)
    if (stepObj) {
      stepObj.progress = stepProgress
      stepObj.completed = stepProgress >= 100
    }
    
    // Mark previous steps as completed
    const currentStepIndex = execution.steps.findIndex(s => s.id === step)
    for (let i = 0; i < currentStepIndex; i++) {
      execution.steps[i].completed = true
      execution.steps[i].progress = 100
    }
    
    persistExecution(portfolioName, execution)
  }
  
  const updateTimeEstimate = (portfolioName, estimatedMs) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    execution.estimatedTimeRemaining = estimatedMs
    persistExecution(portfolioName, execution)
  }
  
  const addExecutionMessage = (portfolioName, message) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    execution.messages.push({
      id: Date.now() + Math.random(),
      timestamp: new Date(),
      text: message,
      type: 'info'
    })
    
    // Keep only last 50 messages
    if (execution.messages.length > 50) {
      execution.messages = execution.messages.slice(-50)
    }
    
    persistExecution(portfolioName, execution)
  }
  
  const completeExecution = (portfolioName) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    execution.status = EXECUTION_STEPS.COMPLETE
    execution.currentStep = EXECUTION_STEPS.COMPLETE
    execution.progress = 100
    execution.stepProgress = 100
    execution.endTime = new Date()
    execution.cancellable = false
    execution.estimatedTimeRemaining = null
    
    // Mark all steps as completed
    execution.steps.forEach(step => {
      step.completed = true
      step.progress = 100
    })
    
    persistExecution(portfolioName, execution)
  }
  
  const failExecution = (portfolioName, error) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    execution.status = EXECUTION_STEPS.ERROR
    execution.currentStep = EXECUTION_STEPS.ERROR
    execution.error = error
    execution.endTime = new Date()
    execution.cancellable = false
    execution.estimatedTimeRemaining = null
    
    persistExecution(portfolioName, execution)
  }
  
  const cancelExecution = (portfolioName) => {
    const execution = executions.value.get(portfolioName)
    if (!execution) return
    
    execution.status = EXECUTION_STEPS.CANCELLED
    execution.currentStep = EXECUTION_STEPS.CANCELLED
    execution.endTime = new Date()
    execution.cancellable = false
    execution.estimatedTimeRemaining = null
    
    persistExecution(portfolioName, execution)
  }
  
  const resetExecution = (portfolioName) => {
    const execution = createExecutionState()
    execution.portfolioName = portfolioName
    executions.value.set(portfolioName, execution)
    clearPersistedExecution(portfolioName)
  }
  
  // Persistence
  const persistExecution = (portfolioName, execution) => {
    try {
      const key = `execution_${portfolioName}`
      localStorage.setItem(key, JSON.stringify({
        ...execution,
        startTime: execution.startTime?.toISOString(),
        endTime: execution.endTime?.toISOString(),
        messages: execution.messages.map(msg => ({
          ...msg,
          timestamp: msg.timestamp.toISOString()
        }))
      }))
    } catch (err) {
      console.warn('Failed to persist execution state:', err)
    }
  }
  
  const restoreExecution = (portfolioName) => {
    try {
      const key = `execution_${portfolioName}`
      const stored = localStorage.getItem(key)
      if (!stored) return null
      
      const data = JSON.parse(stored)
      const execution = {
        ...data,
        startTime: data.startTime ? new Date(data.startTime) : null,
        endTime: data.endTime ? new Date(data.endTime) : null,
        messages: data.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
      }
      
      executions.value.set(portfolioName, execution)
      return execution
    } catch (err) {
      console.warn('Failed to restore execution state:', err)
      return null
    }
  }
  
  const clearPersistedExecution = (portfolioName) => {
    try {
      const key = `execution_${portfolioName}`
      localStorage.removeItem(key)
    } catch (err) {
      console.warn('Failed to clear persisted execution:', err)
    }
  }
  
  // Initialize store
  const initializeStore = () => {
    // Restore any persisted executions on startup
    // This would typically be called during app initialization
  }
  
  return {
    // State
    executions,
    
    // Getters  
    getExecution,
    isExecuting,
    getActiveExecutions,
    
    // Actions
    startExecution,
    updateExecutionStep,
    updateTimeEstimate,
    addExecutionMessage,
    completeExecution,
    failExecution,
    cancelExecution,
    resetExecution,
    restoreExecution,
    clearPersistedExecution,
    initializeStore
  }
})