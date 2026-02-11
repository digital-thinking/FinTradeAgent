import { defineStore } from 'pinia'
import { getSystemHealth } from '../services/api'

export const useAppStore = defineStore('app', {
  state: () => ({
    health: null,
    loading: false,
    error: null
  }),
  actions: {
    async fetchHealth() {
      this.loading = true
      this.error = null
      try {
        this.health = await getSystemHealth()
      } catch (error) {
        this.error = error
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
