<template>
  <view v-if="visible" class="nb-net">
    <text class="nb-net-text">网络不可用：数据可能无法同步</text>
    <text class="nb-net-action" @click.stop="retry">重试</text>
  </view>
</template>

<script>
export default {
  name: 'NbNetworkBanner',
  data() {
    return {
      visible: false,
      lastRetryAt: 0,
    }
  },
  created() {
    this.syncOnce()
    try {
      uni.onNetworkStatusChange((res) => {
        const next = !(res && res.isConnected)
        const prev = this.visible
        this.visible = next
        if (prev && !next) {
          // 避免打扰：只在从“离线->在线”切换时提示一次。
          try {
            uni.showToast({ title: '网络已恢复', icon: 'none' })
          } catch {}
        }
      })
    } catch {
      // ignore
    }
  },
  methods: {
    syncOnce() {
      try {
        uni.getNetworkType({
          success: (res) => {
            this.visible = String(res?.networkType || '') === 'none'
          },
          fail: () => {
            // 无法获取网络类型时，不强行显示（避免误报）
            this.visible = false
          },
        })
      } catch {
        this.visible = false
      }
    },
    retry() {
      const now = Date.now()
      if (now - this.lastRetryAt < 800) return
      this.lastRetryAt = now
      this.syncOnce()

      // 全站收敛：让当前页面有机会执行自己的“重试/刷新”逻辑（如重新拉数据）
      try {
        if (typeof uni !== 'undefined' && typeof uni.$emit === 'function') {
          uni.$emit('nb:network:retry')
        }
      } catch {
        // ignore
      }
    },
  },
}
</script>

<style scoped>
.nb-net {
  position: sticky;
  top: 0;
  z-index: 1800;
  width: 100%;
  max-width: 520px;
  margin: 0 auto 10px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(255, 255, 255, 0.86);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  box-sizing: border-box;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.08);
  backdrop-filter: blur(10px);
}

.nb-net-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.72);
  font-weight: 800;
}

.nb-net-action {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.92);
  font-weight: 900;
  text-decoration: underline;
  text-underline-offset: 4px;
  user-select: none;
}
</style>
