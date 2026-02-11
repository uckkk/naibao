<template>
  <NbSkeleton :w="w" :h="h" :radius="radius" :animated="animated" />
</template>

<script>
import NbSkeleton from './NbSkeleton.vue'

export default {
  name: 'NbSkeletonButton',
  components: { NbSkeleton },
  props: {
    w: { type: [String, Number], default: '100%' },
    h: { type: [String, Number], default: 44 },
    radius: { type: [String, Number], default: 22 },
    animated: { type: Boolean, default: true },
  },
}
</script>

