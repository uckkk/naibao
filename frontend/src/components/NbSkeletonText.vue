<template>
  <view class="nb-skel-text" :style="wrapStyle" aria-hidden="true">
    <NbSkeleton
      v-for="i in safeLines"
      :key="i"
      :w="i === safeLines ? lastWidth : '100%'"
      :h="lineHeight"
      :radius="radius"
      :animated="animated"
    />
  </view>
</template>

<script>
import NbSkeleton from './NbSkeleton.vue'

function clampInt(v, min, max) {
  const n = Number.parseInt(String(v ?? ''), 10)
  if (!Number.isFinite(n)) return min
  return Math.max(min, Math.min(max, n))
}

export default {
  name: 'NbSkeletonText',
  components: { NbSkeleton },
  props: {
    lines: { type: Number, default: 3 },
    lineHeight: { type: [Number, String], default: 12 },
    radius: { type: [Number, String], default: 8 },
    gap: { type: Number, default: 8 },
    animated: { type: Boolean, default: true },
    // 末行宽度范围（百分比），做“更像真实文本”的随机长度
    lastMin: { type: Number, default: 52 },
    lastMax: { type: Number, default: 86 },
  },
  data() {
    return {
      lastWidthPct: 70,
    }
  },
  computed: {
    safeLines() {
      return clampInt(this.lines, 1, 12)
    },
    lastWidth() {
      const pct = clampInt(this.lastWidthPct, 10, 100)
      return `${pct}%`
    },
    wrapStyle() {
      return {
        gap: `${Math.max(0, Number(this.gap || 0))}px`,
      }
    },
  },
  created() {
    const min = clampInt(this.lastMin, 10, 100)
    const max = clampInt(this.lastMax, min, 100)
    this.lastWidthPct = min + Math.floor(Math.random() * (max - min + 1))
  },
}
</script>

<style scoped>
.nb-skel-text {
  display: flex;
  flex-direction: column;
}
</style>

