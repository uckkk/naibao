<template>
  <view class="nb-skel-select" :style="wrapStyle" aria-hidden="true">
    <NbSkeleton :w="'100%'" :h="h" :radius="radius" :animated="animated" />
    <view class="arrow">
      <NbSkeleton :w="12" :h="12" :radius="6" :animated="animated" />
    </view>
  </view>
</template>

<script>
import NbSkeleton from './NbSkeleton.vue'

export default {
  name: 'NbSkeletonSelect',
  components: { NbSkeleton },
  props: {
    w: { type: [String, Number], default: '100%' },
    h: { type: [String, Number], default: 46 },
    radius: { type: [String, Number], default: 14 },
    animated: { type: Boolean, default: true },
  },
  computed: {
    wrapStyle() {
      const w = this.w
      if (typeof w === 'number' && Number.isFinite(w)) return { width: `${w}px` }
      if (typeof w === 'string' && w) return { width: w }
      return {}
    },
  },
}
</script>

<style scoped>
.nb-skel-select {
  position: relative;
}

.arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.72;
}
</style>

