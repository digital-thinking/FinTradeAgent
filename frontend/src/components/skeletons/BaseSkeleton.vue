<template>
  <div 
    :class="[
      'skeleton-base',
      rounded ? 'rounded' : '',
      rounded === 'full' ? 'rounded-full' : '',
      rounded === 'lg' ? 'rounded-lg' : '',
      rounded === 'xl' ? 'rounded-xl' : '',
      className
    ]"
    :style="{
      width: width,
      height: height,
      minHeight: minHeight,
      maxWidth: maxWidth
    }"
  >
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '1rem'
  },
  minHeight: {
    type: String,
    default: null
  },
  maxWidth: {
    type: String,
    default: null
  },
  rounded: {
    type: [Boolean, String],
    default: true
  },
  className: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.skeleton-base {
  @apply bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800;
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Reduce motion for users who prefer it */
@media (prefers-reduced-motion: reduce) {
  .skeleton-base {
    animation: none;
    @apply bg-surface;
  }
}
</style>