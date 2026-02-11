<template>
  <view class="nb-load-switch" :style="rootStyle">
    <view v-if="showSkeleton" class="slot-skel">
      <slot name="skeleton" />
    </view>

    <view v-else class="slot-content" :class="{ enter: contentEnter }">
      <slot />
    </view>
  </view>
</template>

<script>
export default {
  name: 'NbLoadingSwitch',
  props: {
    loading: { type: Boolean, default: false },
    // 避免“闪一下”的骨架：加载很快时延迟出现
    delayMs: { type: Number, default: 120 },
    // 骨架一旦出现，至少展示一小段时间，避免来回切换抖动
    minShowMs: { type: Number, default: 280 },
    // 内容淡入时长
    fadeMs: { type: Number, default: 220 },
  },
  data() {
    return {
      showSkeleton: false,
      skeletonShownAt: 0,
      contentEnter: false,
      delayTimer: null,
      hideTimer: null,
    }
  },
  computed: {
    rootStyle() {
      const ms = Math.max(120, Number(this.fadeMs || 0))
      return { '--nb-fade-ms': `${ms}ms` }
    },
  },
  watch: {
    loading: {
      immediate: true,
      handler(v) {
        this.sync(Boolean(v))
      },
    },
  },
  beforeUnmount() {
    this.clearTimers()
  },
  methods: {
    clearTimers() {
      if (this.delayTimer) clearTimeout(this.delayTimer)
      if (this.hideTimer) clearTimeout(this.hideTimer)
      this.delayTimer = null
      this.hideTimer = null
    },
    sync(isLoading) {
      this.clearTimers()
      if (isLoading) {
        this.contentEnter = false
        // 已显示骨架：保持
        if (this.showSkeleton) return
        const delay = Math.max(0, Number(this.delayMs || 0))
        this.delayTimer = setTimeout(() => {
          this.showSkeleton = true
          this.skeletonShownAt = Date.now()
        }, delay)
        return
      }

      // ready: 尽量平滑地从骨架过渡到内容
      if (!this.showSkeleton) {
        this.$nextTick(() => {
          this.contentEnter = true
        })
        return
      }

      const minShow = Math.max(0, Number(this.minShowMs || 0))
      const elapsed = Date.now() - Number(this.skeletonShownAt || 0)
      const wait = Math.max(0, minShow - elapsed)
      this.hideTimer = setTimeout(() => {
        this.showSkeleton = false
        this.$nextTick(() => {
          this.contentEnter = true
        })
      }, wait)
    },
  },
}
</script>

<style scoped>
.slot-content {
  opacity: 0;
  transition: opacity var(--nb-fade-ms) ease;
}

.slot-content.enter {
  opacity: 1;
}
</style>

