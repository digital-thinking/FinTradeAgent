<template>
  <div class="app-shell min-h-screen text-text-primary bg-theme transition-theme duration-300">
    <!-- Mobile Header with Hamburger Menu -->
    <div class="sticky top-0 z-40 flex items-center justify-between px-4 py-3 glass lg:hidden">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-text-tertiary">FinTradeAgent</p>
        <h1 class="font-display text-lg font-semibold text-text-primary">Control Center</h1>
      </div>
      <div class="flex items-center gap-2">
        <ThemeToggle />
        <button @click="toggleMobileSidebar" class="glass p-2 rounded-xl">
          <svg class="w-6 h-6 text-text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="!showMobileSidebar" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Sidebar Overlay -->
    <div v-if="showMobileSidebar" class="fixed inset-0 z-40 lg:hidden">
      <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="closeMobileSidebar"></div>
      <aside class="fixed right-0 top-0 bottom-0 w-80 max-w-[85vw] glass p-6 overflow-y-auto">
        <div class="flex items-center justify-between mb-6">
          <div>
            <p class="text-xs uppercase tracking-[0.3em] text-text-tertiary">FinTradeAgent</p>
            <h1 class="font-display text-xl font-semibold text-text-primary">Control Center</h1>
          </div>
          <div class="flex items-center gap-2">
            <ThemeToggle />
            <button @click="closeMobileSidebar" class="glass p-2 rounded-xl">
              <svg class="w-5 h-5 text-text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>
        <nav class="flex flex-col gap-2 mb-8">
          <RouterLink class="nav-link" to="/" @click="closeMobileSidebar">Dashboard</RouterLink>
          <RouterLink class="nav-link" to="/portfolios" @click="closeMobileSidebar">Portfolios</RouterLink>
          <RouterLink class="nav-link" to="/trades" @click="closeMobileSidebar">Pending Trades</RouterLink>
          <RouterLink class="nav-link" to="/comparison" @click="closeMobileSidebar">Comparison</RouterLink>
          <RouterLink class="nav-link" to="/system" @click="closeMobileSidebar">System Health</RouterLink>
        </nav>
        <div class="rounded-2xl border border-border bg-theme-secondary/60 p-4 text-xs text-text-secondary">
          <p class="font-medium text-text-primary">Backend</p>
          <p>http://localhost:8000</p>
          <p class="mt-3">Streaming updates enabled once agents run.</p>
        </div>
      </aside>
    </div>

    <!-- Desktop Layout -->
    <div class="mx-auto flex min-h-screen max-w-7xl gap-6 px-4 py-4 sm:px-6 sm:py-6">
      <!-- Desktop Sidebar -->
      <aside class="glass hidden w-64 flex-col rounded-3xl p-6 lg:flex">
        <div class="mb-10">
          <div class="flex items-center justify-between mb-4">
            <div>
              <p class="text-xs uppercase tracking-[0.3em] text-text-tertiary">FinTradeAgent</p>
              <h1 class="font-display text-2xl font-semibold text-text-primary">Control Center</h1>
            </div>
            <ThemeToggle />
          </div>
        </div>
        <nav class="flex flex-1 flex-col gap-2">
          <RouterLink class="nav-link" to="/">Dashboard</RouterLink>
          <RouterLink class="nav-link" to="/portfolios">Portfolios</RouterLink>
          <RouterLink class="nav-link" to="/trades">Pending Trades</RouterLink>
          <RouterLink class="nav-link" to="/comparison">Comparison</RouterLink>
          <RouterLink class="nav-link" to="/system">System Health</RouterLink>
        </nav>
        <div class="mt-10 rounded-2xl border border-border bg-theme-secondary/60 p-4 text-xs text-text-secondary">
          <p class="font-medium text-text-primary">Backend</p>
          <p>http://localhost:8000</p>
          <p class="mt-3">Streaming updates enabled once agents run.</p>
        </div>
      </aside>

      <!-- Main Content -->
      <div class="flex min-w-0 flex-1 flex-col gap-6">
        <!-- Desktop Header -->
        <header class="glass hidden lg:flex flex-col gap-4 rounded-3xl px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p class="section-title text-text-tertiary">AI Portfolio Management</p>
            <h2 class="font-display text-2xl xl:text-3xl font-semibold text-text-primary">FinTradeAgent Dashboard</h2>
          </div>
          <div class="flex items-center gap-3">
            <BaseButton variant="ghost" class="hidden sm:inline-flex">Docs</BaseButton>
            <BaseButton variant="primary">Create Portfolio</BaseButton>
          </div>
        </header>

        <!-- Mobile Content Area (with top padding to account for sticky header) -->
        <main class="flex min-h-[70vh] flex-col gap-4 sm:gap-6 lg:pt-0 pt-0">
          <RouterView />
        </main>
      </div>
    </div>

    <!-- Mobile Bottom Navigation (Removed as mobile sidebar is better) -->
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import BaseButton from '../components/BaseButton.vue'
import ThemeToggle from '../components/ThemeToggle.vue'

// Mobile sidebar state
const showMobileSidebar = ref(false)

const toggleMobileSidebar = () => {
  showMobileSidebar.value = !showMobileSidebar.value
}

const closeMobileSidebar = () => {
  showMobileSidebar.value = false
}
</script>
