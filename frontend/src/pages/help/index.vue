<template>
  <view class="help-page">
    <NbNetworkBanner />
    <view class="title">常见问题</view>

    <view class="group">
      <view class="cells">
        <!-- 信息减法：默认收起，点开再看答案（更像 iOS 设置的层级） -->
        <view
          v-for="it in faqs"
          :key="it.key"
          class="cell faq-cell"
          :id="it.anchorId"
          @click="toggleFaq(it.key)"
        >
          <view class="faq-head">
            <text class="q">{{ it.q }}</text>
            <text class="chev" :class="{ open: openKey === it.key }">›</text>
          </view>
          <text v-if="openKey === it.key" class="a">{{ it.a }}</text>
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
  data() {
    return {
      openKey: '',
      faqs: [
        {
          key: 'recommend',
          q: '推荐奶量是怎么来的？',
          a: '基于宝宝月龄/体重（若有）与权威参考范围计算；仅做趋势参考，不替代医生建议。',
          anchorId: '',
        },
        {
          key: 'interval',
          q: '为什么会提示“喂奶过密/超时”？',
          a: '用于提醒你核对是否误触/重复记录，或是否需要调整喂奶间隔设置。',
          anchorId: '',
        },
        {
          key: 'sync',
          q: '多人一起记会不同步吗？',
          a: '正常网络下会自动同步；弱网/离线时可能延迟，恢复网络后会自动刷新。',
          anchorId: '',
        },
        {
          key: 'notify',
          q: '为什么“系统通知提醒”不生效？',
          a: '需要先在系统/浏览器里允许通知权限；iPhone 通常需先“添加到主屏幕”后才能接收系统通知。Web 无法保证在完全关闭页面后仍准时提醒。',
          anchorId: 'nb-help-notify',
        },
        {
          key: 'weaning',
          q: '转奶期怎么用？',
          a: '在“设置 → 奶粉”里切换到新奶粉后，会提示是否开启 7 天转奶期。开启后首页会标记本次旧/新奶粉，并在每次投喂间自动切换（不做同次混合）。如宝宝出现明显不适，请暂停并咨询医生。',
          anchorId: '',
        },
      ],
    }
  },
  onLoad(options) {
    const topic = String(options?.topic || '').trim()
    if (topic !== 'notify') return
    this.openKey = 'notify'
    this.$nextTick(() => {
      try {
        uni.pageScrollTo({ selector: '#nb-help-notify', duration: 220 })
      } catch {}
    })
  },
  methods: {
    toggleFaq(key) {
      const k = String(key || '').trim()
      if (!k) return
      this.openKey = this.openKey === k ? '' : k
    },
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

.faq-cell:active {
  background: var(--nb-fill-2);
}

.faq-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.q {
  flex: 1;
  min-width: 0;
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
  transition: transform 180ms ease;
}

.chev.open {
  transform: rotate(90deg);
}
</style>
