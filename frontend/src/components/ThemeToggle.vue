<template>
  <button
    @click="toggleTheme"
    :class="[
      'relative inline-flex items-center justify-center rounded-xl p-2.5',
      'glass border border-white/20 hover:border-white/30',
      'transition-all duration-300 ease-in-out',
      'hover:scale-105 active:scale-95',
      'group'
    ]"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <!-- Sun Icon (Light Mode) -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-75 rotate-90"
      enter-to-class="opacity-100 scale-100 rotate-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 rotate-0"
      leave-to-class="opacity-0 scale-75 rotate-90"
    >
      <svg
        v-if="!isDark"
        class="w-5 h-5 text-amber-400 group-hover:text-amber-300"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fill-rule="evenodd"
          d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
          clip-rule="evenodd"
        />
      </svg>
    </Transition>

    <!-- Moon Icon (Dark Mode) -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-75 rotate-90"
      enter-to-class="opacity-100 scale-100 rotate-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 rotate-0"
      leave-to-class="opacity-0 scale-75 rotate-90"
    >
      <svg
        v-if="isDark"
        class="w-5 h-5 text-blue-300 group-hover:text-blue-200"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"
        />
      </svg>
    </Transition>
  </button>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>

<style scoped>
/* Additional styles for glass morphism effect */
.glass {
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  background: rgba(255, 255, 255, 0.1);
}

.dark .glass {
  background: rgba(255, 255, 255, 0.05);
}
</style>