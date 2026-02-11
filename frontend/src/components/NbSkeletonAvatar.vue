<template>
  <NbSkeleton :w="size" :h="size" :radius="computedRadius" :animated="animated" />
</template>

<script>
import NbSkeleton from './NbSkeleton.vue'

export default {
  name: 'NbSkeletonAvatar',
  components: { NbSkeleton },
  props: {
    size: { type: Number, default: 40 },
    shape: { type: String, default: 'rounded' }, // rounded | circle
    radius: { type: [Number, String], default: '' },
    animated: { type: Boolean, default: true },
  },
  computed: {
    computedRadius() {
      if (this.radius !== '' && this.radius !== null && this.radius !== undefined) return this.radius
      const s = Math.max(0, Number(this.size || 0))
      if (String(this.shape || '') === 'circle') return Math.round(s / 2)
      return 14
    },
  },
}
</script>

