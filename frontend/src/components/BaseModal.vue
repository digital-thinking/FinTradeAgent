<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-black/80 backdrop-blur-sm overflow-y-auto">
    <!-- Mobile-first modal sizing -->
    <div class="glass w-full max-w-2xl mx-4 my-8 sm:my-auto rounded-2xl sm:rounded-3xl p-4 sm:p-6 max-h-[calc(100vh-2rem)] overflow-y-auto">
      <!-- Modal Header -->
      <div class="flex items-start justify-between pb-4 border-b border-border">
        <div class="min-w-0 flex-1 pr-4">
          <p v-if="eyebrow" class="section-title">{{ eyebrow }}</p>
          <h3 class="font-display text-lg sm:text-xl lg:text-2xl font-semibold text-text-primary break-words">{{ title }}</h3>
        </div>
        <button
          class="glass p-2 rounded-xl text-text-tertiary hover:text-text-primary transition-theme shrink-0 ml-4"
          type="button"
          @click="$emit('close')"
          aria-label="Close modal"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <!-- Modal Content -->
      <div class="pt-4 sm:pt-6">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  open: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  eyebrow: {
    type: String,
    default: ''
  }
})

defineEmits(['close'])
</script>
