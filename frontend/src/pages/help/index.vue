<template>
  <view class="help-page">
    <NbNetworkBanner />
    <view class="title">常见问题</view>

    <view class="group">
      <view class="cells">
        <view class="cell">
          <text class="q">1. 推荐奶量是怎么来的？</text>
          <text class="a">基于宝宝月龄/体重（若有）与权威参考范围计算；仅做趋势参考，不替代医生建议。</text>
        </view>
        <view class="cell">
          <text class="q">2. 为什么会提示“喂奶过密/超时”？</text>
          <text class="a">用于提醒你核对是否误触/重复记录，或是否需要调整喂奶间隔设置。</text>
        </view>
        <view class="cell">
          <text class="q">3. 多人一起记会不同步吗？</text>
          <text class="a">正常网络下会自动同步；弱网/离线时可能延迟，恢复网络后会自动刷新。</text>
        </view>
        <view class="cell" id="nb-help-notify">
          <text class="q">4. 为什么“系统通知提醒”不生效？</text>
          <text class="a">需要先在系统/浏览器里允许通知权限；iPhone 通常需先“添加到主屏幕”后才能接收系统通知。Web 无法保证在完全关闭页面后仍准时提醒。</text>
        </view>
        <view class="cell">
          <text class="q">5. 转奶期怎么用？</text>
          <text class="a">在“设置 → 奶粉”里切换到新奶粉后，会提示是否开启 7 天转奶期。开启后首页会标记本次旧/新奶粉，并在每次投喂间自动切换（不做同次混合）。如宝宝出现明显不适，请暂停并咨询医生。</text>
        </view>
      </view>
    </view>

    <view class="group">
      <view class="cells">
        <view class="cell tappable" @click="copyFeedback">
          <text class="q">反馈与建议</text>
          <text class="chev">›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbNetworkBanner },
  onLoad(options) {
    const topic = String(options?.topic || '').trim()
    if (topic !== 'notify') return
    this.$nextTick(() => {
      try {
        uni.pageScrollTo({ selector: '#nb-help-notify', duration: 220 })
      } catch {}
    })
  },
  methods: {
    copyFeedback() {
      // 先用最轻量的方式闭环：复制关键定位信息，便于在微信/群里发给作者
      const text = '奶宝反馈：请描述你遇到的问题/建议，并附上机型与浏览器版本（如 iPhone 14 / iOS 17 / Safari）。'
      uni.setClipboardData({ data: text })
      uni.showToast({ title: '已复制', icon: 'none' })
    },
  },
}
</script>

<style scoped>
.help-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(28px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.title {
  font-size: 20px;
  font-weight: 900;
  color: var(--nb-text);
  margin: 4px 2px 12px;
}

.group {
  background: var(--nb-card-bg);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: var(--nb-shadow-card);
  margin-bottom: 12px;
}

.cells {
  display: flex;
  flex-direction: column;
}

.cell {
  padding: 14px;
  border-top: 1px solid var(--nb-line);
}

.cell:first-child {
  border-top: none;
}

.q {
  display: block;
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.a {
  display: block;
  margin-top: 6px;
  font-size: 13px;
  color: var(--nb-muted);
  line-height: 1.6;
}

.tappable {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tappable:active {
  background: var(--nb-fill-2);
}

.chev {
  font-size: 18px;
  color: rgba(var(--nb-ink-rgb), 0.38);
  font-weight: 900;
}
</style>
