<template>
  <view class="nb-skel" :style="wrapStyle" aria-hidden="true">
    <view v-if="animated" class="nb-skel-shimmer" :style="shimmerStyle"></view>
  </view>
</template>

<script>
const SHIMMER_MS = 1400

function toCssSize(v) {
  if (v === undefined || v === null || v === '') return ''
  if (typeof v === 'number' && Number.isFinite(v)) return `${v}px`
  return String(v)
}

function getShimmerT0() {
  try {
    if (typeof uni !== 'undefined') {
      if (!uni.__nb_shimmer_t0) uni.__nb_shimmer_t0 = Date.now()
      return Number(uni.__nb_shimmer_t0) || Date.now()
    }
  } catch {}
  return Date.now()
}

export default {
  name: 'NbSkeleton',
  props: {
    w: { type: [String, Number], default: '100%' },
    h: { type: [String, Number], default: 12 },
    radius: { type: [String, Number], default: 10 },
    animated: { type: Boolean, default: true },
  },
  data() {
    return {
      shimmerDelayMs: 0,
    }
  },
  computed: {
    wrapStyle() {
      const w = toCssSize(this.w)
      const h = toCssSize(this.h)
      const r = toCssSize(this.radius)
      const style = {
        ...(w ? { width: w } : {}),
        ...(h ? { height: h } : {}),
        ...(r ? { borderRadius: r } : {}),
        '--nb-shimmer-delay': `${this.shimmerDelayMs}ms`,
        '--nb-shimmer-duration': `${SHIMMER_MS}ms`,
      }
      return style
    },
    shimmerStyle() {
      return {
        animationDelay: `var(--nb-shimmer-delay)`,
        animationDuration: `var(--nb-shimmer-duration)`,
      }
    },
  },
  created() {
    const t0 = getShimmerT0()
    const now = Date.now()
    const elapsed = now - t0
    // 负 delay：让所有骨架在同一“全局时间轴”上同步扫光相位
    this.shimmerDelayMs = -((elapsed % SHIMMER_MS + SHIMMER_MS) % SHIMMER_MS)
  },
}
</script>

<style scoped>
.nb-skel {
  position: relative;
  overflow: hidden;
  background: rgba(27, 26, 23, 0.06);
}

.nb-skel-shimmer {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -150%;
  width: 150%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.60) 45%,
    rgba(255, 255, 255, 0) 90%
  );
  animation-name: nb-shimmer;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

@keyframes nb-shimmer {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(200%);
  }
}
</style>

