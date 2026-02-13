<template>
  <view class="legal-page">
    <NbNetworkBanner />

    <view class="hero">
      <text class="title">隐私与数据</text>
      <text class="subtitle">我们尽量只收集必要信息，用于计算与同步。</text>
    </view>

    <text class="section-h">我们收集什么</text>
    <view class="group">
      <view class="cells">
        <view class="cell">
          <text class="cell-title">账号</text>
          <text class="cell-value">手机号、昵称、头像</text>
        </view>
        <view class="cell">
          <text class="cell-title">宝宝</text>
          <text class="cell-value">昵称、出生日期/时间、头像、身高体重</text>
        </view>
        <view class="cell">
          <text class="cell-title">喂养</text>
          <text class="cell-value">喂奶时间、毫升、奶粉选择、勺数</text>
        </view>
        <view class="cell">
          <text class="cell-title">设置</text>
          <text class="cell-value">喂奶间隔、提醒偏好</text>
        </view>
      </view>
    </view>

    <text class="section-h">我们如何使用</text>
    <view class="group">
      <view class="cells">
        <view class="cell">
          <text class="cell-title">目的</text>
          <text class="cell-value">计算下次喂奶、统计趋势、同步到你的设备</text>
        </view>
        <view class="cell">
          <text class="cell-title">存储</text>
          <text class="cell-value">本机缓存 + 服务器数据库（用于多设备/多人协作）</text>
        </view>
        <view class="cell">
          <text class="cell-title">共享</text>
          <text class="cell-value">你可通过邀请码邀请家庭成员协作</text>
        </view>
      </view>
    </view>

    <text class="section-h">你的权利</text>
    <view class="group">
      <view class="cells">
        <view class="cell tappable" @click="goAccountExport">
          <text class="cell-title">导出我的数据</text>
          <text class="chev">›</text>
        </view>
        <view class="cell tappable" @click="goAccountDelete">
          <text class="cell-title danger-text">注销账号</text>
          <text class="chev danger-text">›</text>
        </view>
      </view>
    </view>

    <text class="section-h">免责声明</text>
    <view class="note">
      <text class="note-text">
        “奶宝”提供的推荐/参考仅用于记录与趋势参考，不替代专业医疗建议。如有不适或喂养疑问，请咨询医生/专业人士。
      </text>
    </view>

    <view class="footer">
      <button class="ghost-btn" @click="copyPageText">复制本页内容</button>
    </view>
  </view>
</template>

<script>
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbNetworkBanner },
  methods: {
    goAccountExport() {
      uni.navigateTo({ url: '/pages/account/index?focus=export' })
    },
    goAccountDelete() {
      uni.navigateTo({ url: '/pages/account/index?focus=delete' })
    },
    copyPageText() {
      const text = [
        '隐私与数据',
        '',
        '我们收集什么：账号（手机号/昵称/头像）；宝宝（昵称/出生日期时间/头像/身高体重）；喂养（时间/毫升/奶粉/勺数）；设置（间隔/提醒偏好）。',
        '我们如何使用：用于计算下次喂奶、统计趋势、同步到你的设备；数据存储在本机缓存与服务器数据库（用于多设备/多人协作）。',
        '你的权利：你可以导出自己的数据，也可以注销账号删除数据。',
        '',
        '免责声明：本应用提供的推荐/参考仅用于记录与趋势参考，不替代专业医疗建议。如有不适或喂养疑问，请咨询医生/专业人士。',
      ].join('\n')
      uni.setClipboardData({
        data: text,
        success: () => uni.showToast({ title: '已复制', icon: 'none' }),
        fail: () => uni.showToast({ title: '复制失败', icon: 'none' }),
      })
    },
  },
}
</script>

<style scoped>
.legal-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(24px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.hero {
  padding: 8px 4px 12px;
}

.title {
  font-size: 22px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
}

.subtitle {
  margin-top: 6px;
  display: block;
  color: var(--nb-muted);
  font-size: 13px;
}

.section-h {
  display: block;
  margin: 12px 6px 8px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.50);
  letter-spacing: 0.4px;
  font-weight: 800;
}

.group {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.08);
  margin-bottom: 10px;
}

.cells {
  display: flex;
  flex-direction: column;
}

.cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.cell:first-child {
  border-top: none;
}

.cell.tappable:active {
  background: rgba(27, 26, 23, 0.03);
}

.cell-title {
  flex: 0 0 auto;
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.92);
}

.cell-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.62);
  text-align: right;
}

.chev {
  font-size: 18px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.34);
}

.danger-text {
  color: rgba(226, 74, 59, 0.92);
}

.note {
  padding: 12px 6px 4px;
}

.note-text {
  font-size: 12px;
  line-height: 1.5;
  color: rgba(27, 26, 23, 0.62);
}

.footer {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

.ghost-btn {
  height: 40px;
  padding: 0 16px;
  border-radius: 20px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.82);
  font-weight: 900;
  font-size: 13px;
}
</style>

