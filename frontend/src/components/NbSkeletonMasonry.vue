<template>
  <view class="nb-skel-masonry" :style="wrapStyle" aria-hidden="true">
    <view v-for="it in blocks" :key="it.key" class="item" :style="{ width: itemWidth }">
      <NbSkeleton :w="'100%'" :h="it.h" :radius="radius" :animated="animated" />
      <view class="meta" v-if="withText">
        <NbSkeletonText :lines="2" :gap="6" :animated="animated" />
      </view>
    </view>
  </view>
</template>

<script>
import NbSkeleton from './NbSkeleton.vue'
import NbSkeletonText from './NbSkeletonText.vue'

function clampInt(v, min, max) {
  const n = Number.parseInt(String(v ?? ''), 10)
  if (!Number.isFinite(n)) return min
  return Math.max(min, Math.min(max, n))
}

export default {
  name: 'NbSkeletonMasonry',
  components: { NbSkeleton, NbSkeletonText },
  props: {
    columns: { type: Number, default: 2 },
    count: { type: Number, default: 6 },
    gap: { type: Number, default: 10 },
    radius: { type: [Number, String], default: 16 },
    animated: { type: Boolean, default: true },
    withText: { type: Boolean, default: false },
    minH: { type: Number, default: 110 },
    maxH: { type: Number, default: 200 },
  },
  data() {
    return {
      blocks: [],
    }
  },
  computed: {
    safeCols() {
      return clampInt(this.columns, 2, 4)
    },
    itemWidth() {
      // 简化版瀑布流占位：用 flex-wrap + 固定列宽，避免依赖复杂布局能力
      const gap = Math.max(0, Number(this.gap || 0))
      const cols = this.safeCols
      const totalGap = gap * (cols - 1)
      return `calc(${(100 / cols).toFixed(6)}% - ${(totalGap / cols).toFixed(6)}px)`
    },
    wrapStyle() {
      const gap = Math.max(0, Number(this.gap || 0))
      return { gap: `${gap}px` }
    },
  },
  created() {
    const n = clampInt(this.count, 1, 20)
    const minH = Math.max(60, Number(this.minH || 110))
    const maxH = Math.max(minH, Number(this.maxH || 200))
    const blocks = []
    for (let i = 0; i < n; i += 1) {
      const h = minH + Math.floor(Math.random() * (maxH - minH + 1))
      blocks.push({ key: `b_${i}`, h })
    }
    this.blocks = blocks
  },
}
</script>

<style scoped>
.nb-skel-masonry {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: flex-start;
}

.item {
  display: flex;
  flex-direction: column;
}

.meta {
  margin-top: 10px;
}
</style>

