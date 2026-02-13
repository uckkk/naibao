<template>
  <view class="report-container">
    <NbNetworkBanner />
    <view class="top-bar">
      <text class="title">数据报告</text>
      <text class="subtitle">{{ babyName }}</text>
    </view>

    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能生成奶量与生长趋势报告"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <template v-else>
    <view class="range-card">
      <view class="range-row">
        <text class="range-label">范围</text>
        <text class="range-value">{{ fromDate }} ~ {{ toDate }}</text>
      </view>

      <view class="chips">
        <view class="chip" :class="{ active: quickRange === 7 }" @click="setQuickRange(7)">近7天</view>
        <view class="chip" :class="{ active: quickRange === 30 }" @click="setQuickRange(30)">近30天</view>
        <view class="chip" :class="{ active: quickRange === 90 }" @click="setQuickRange(90)">近90天</view>
      </view>

      <view class="pickers">
        <!-- #ifdef H5 -->
        <view class="picker" @click="pickFrom">
          <text class="picker-k">开始</text>
          <text class="picker-v">{{ fromDate }}</text>
        </view>
        <!-- #endif -->
        <!-- #ifndef H5 -->
        <picker mode="date" :value="fromDate" @change="onFromChange">
          <view class="picker">
            <text class="picker-k">开始</text>
            <text class="picker-v">{{ fromDate }}</text>
          </view>
        </picker>
        <!-- #endif -->

        <!-- #ifdef H5 -->
        <view class="picker" @click="pickTo">
          <text class="picker-k">结束</text>
          <text class="picker-v">{{ toDate }}</text>
        </view>
        <!-- #endif -->
        <!-- #ifndef H5 -->
        <picker mode="date" :value="toDate" @change="onToChange">
          <view class="picker">
            <text class="picker-k">结束</text>
            <text class="picker-v">{{ toDate }}</text>
          </view>
        </picker>
        <!-- #endif -->
      </view>

      <view class="actions">
        <button class="primary-btn" :disabled="loading" @click="loadReport">
          {{ loading ? '生成中...' : '生成报告' }}
        </button>
        <button class="ghost-btn" :disabled="!report || loading" @click="copyCsv">复制CSV</button>
        <button class="ghost-btn" :disabled="!report || loading" @click="downloadCsv">下载CSV</button>
      </view>
    </view>

    <view class="report-body">
    <NbLoadable
      :loading="loading"
      :errorText="errorText"
      errorTitle="生成失败"
      :empty="!report"
      emptyTitle="还没有报告"
      emptyDesc="选择范围后点“生成报告”"
      emptyActionText="生成报告"
      @retry="loadReport"
      @emptyAction="loadReport"
    >
      <template #skeleton>
        <view class="report-skel">
          <view class="summary-grid">
            <view v-for="i in 4" :key="i" class="summary-card">
              <NbSkeleton :w="44" :h="12" :radius="6" />
              <view style="margin-top:10px;">
                <NbSkeleton :w="110" :h="26" :radius="13" />
              </view>
            </view>
          </view>

          <view class="days-card">
            <view class="days-header">
              <NbSkeleton :w="64" :h="14" :radius="7" />
              <NbSkeleton :w="120" :h="12" :radius="6" />
            </view>
            <view class="days-table">
              <view class="days-row days-row-head">
                <NbSkeleton :w="42" :h="12" :radius="6" />
                <NbSkeleton :w="42" :h="12" :radius="6" />
                <NbSkeleton :w="42" :h="12" :radius="6" />
                <NbSkeleton :w="92" :h="12" :radius="6" />
              </view>
              <view v-for="i in 5" :key="i" class="days-row">
                <NbSkeleton :w="42" :h="12" :radius="6" />
                <NbSkeleton :w="52" :h="12" :radius="6" />
                <NbSkeleton :w="30" :h="12" :radius="6" />
                <NbSkeleton :w="110" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>
      </template>
      <view class="summary-grid">
        <view class="summary-card">
          <text class="summary-k">总奶量</text>
          <text class="summary-v">{{ report.summary.total_amount }}ml</text>
          </view>
          <view class="summary-card">
            <text class="summary-k">日均</text>
            <text class="summary-v">{{ report.summary.avg_per_day }}ml</text>
          </view>
          <view class="summary-card">
            <text class="summary-k">记录次数</text>
            <text class="summary-v">{{ report.summary.feedings_count }}</text>
          </view>
          <view class="summary-card">
            <text class="summary-k">单次均值</text>
            <text class="summary-v">{{ report.summary.avg_per_feeding }}ml</text>
          </view>
        </view>

        <view class="days-card">
          <view class="days-header">
            <text class="days-title">每日明细</text>
            <text class="days-hint">点击复制单日数据</text>
          </view>

          <view class="days-table">
            <view class="days-row days-row-head">
              <text class="col date">日期</text>
              <text class="col amt">奶量</text>
              <text class="col cnt">次数</text>
              <text class="col wh">体重/身高</text>
            </view>

            <view
              v-for="d in report.days"
              :key="d.date"
              class="days-row"
              @click="copyDay(d)"
            >
              <text class="col date">{{ d.date.slice(5) }}</text>
              <text class="col amt">{{ d.total_amount || 0 }}</text>
              <text class="col cnt">{{ d.feedings_count || 0 }}</text>
              <text class="col wh">{{ weightHeightText(d) }}</text>
            </view>
          </view>
        </view>
    </NbLoadable>
    </view>
    </template>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton },
  data() {
    return {
      babyId: null,
      fromDate: '',
      toDate: '',
      quickRange: 30,
      loading: false,
      report: null,
      errorText: '',
    }
  },

  computed: {
    babyName() {
      const store = useUserStore()
      const b = store.currentBaby
      if (b && b.nickname) return b.nickname
      return '宝宝'
    },
  },

  onLoad(options) {
    const store = useUserStore()
    this.babyId = options.babyId || store.currentBaby?.id || null
    this.setQuickRange(30)
  },

  onShow() {
    const store = useUserStore()
    // 多宝宝：默认全局跟随 currentBaby
    if (store.currentBaby?.id) this.babyId = store.currentBaby.id
  },

  methods: {
    onNbRetry() {
      if (this.babyId) this.loadReport()
    },

    weightHeightText(d) {
      const w = d.weight ? `${Number(d.weight).toFixed(1)}kg` : '--kg'
      const h = d.height ? `${d.height}cm` : '--cm'
      return `${w} / ${h}`
    },

    formatDateYMD(date) {
      const y = date.getFullYear()
      const m = String(date.getMonth() + 1).padStart(2, '0')
      const d = String(date.getDate()).padStart(2, '0')
      return `${y}-${m}-${d}`
    },

    setQuickRange(days) {
      const n = Number(days)
      this.quickRange = Number.isFinite(n) ? n : 30
      const to = new Date()
      const from = new Date()
      from.setDate(to.getDate() - (this.quickRange - 1))
      this.toDate = this.formatDateYMD(to)
      this.fromDate = this.formatDateYMD(from)
    },

    async pickFrom() {
      const picked = await this.openNativePicker('date', this.fromDate)
      if (picked) {
        this.fromDate = picked
        this.quickRange = 0
      }
    },

    async pickTo() {
      const picked = await this.openNativePicker('date', this.toDate)
      if (picked) {
        this.toDate = picked
        this.quickRange = 0
      }
    },

    onFromChange(e) {
      const v = e?.detail?.value
      if (v) {
        this.fromDate = v
        this.quickRange = 0
      }
    },

    onToChange(e) {
      const v = e?.detail?.value
      if (v) {
        this.toDate = v
        this.quickRange = 0
      }
    },

    openNativePicker(type, value) {
      // H5: 用真实 DOM input 调起系统选择器；其他端走 <picker mode="date">（见模板条件编译）。
      if (typeof document === 'undefined') return Promise.resolve(null)

      return new Promise((resolve) => {
        let done = false
        const input = document.createElement('input')
        input.type = type
        input.value = value || ''

        input.style.position = 'fixed'
        input.style.left = '0'
        input.style.top = '0'
        input.style.width = '1px'
        input.style.height = '1px'
        input.style.opacity = '0'
        input.style.border = '0'
        input.style.padding = '0'
        input.style.margin = '0'
        input.style.background = 'transparent'
        input.style.zIndex = '2147483647'

        const cleanup = () => {
          try { input.remove() } catch {}
        }
        const finish = (v) => {
          if (done) return
          done = true
          cleanup()
          resolve(v || null)
        }

        input.addEventListener('change', () => finish(input.value))
        input.addEventListener('blur', () => setTimeout(() => finish(null), 0), { once: true })

        document.body.appendChild(input)
        try {
          input.focus({ preventScroll: true })
        } catch {
          try { input.focus() } catch {}
        }
        try { input.click() } catch {}
      })
    },

    async loadReport() {
      this.errorText = ''
      this.report = null
      if (!this.babyId) {
        this.errorText = '缺少 babyId，请先在首页选择/创建宝宝'
        return
      }
      if (!this.fromDate || !this.toDate) {
        this.errorText = '请选择日期范围'
        return
      }
      this.loading = true
      try {
        const res = await api.get(`/babies/${this.babyId}/report`, { from: this.fromDate, to: this.toDate })
        this.report = res
      } catch (e) {
        this.errorText = e.message || '生成失败'
      } finally {
        this.loading = false
      }
    },

    buildCsv() {
      const days = Array.isArray(this.report?.days) ? this.report.days : []
      const lines = ['date,total_amount_ml,feedings_count,weight_kg,height_cm']
      for (const d of days) {
        const w = d.weight ? String(d.weight) : ''
        const h = d.height ? String(d.height) : ''
        lines.push([d.date, String(d.total_amount || 0), String(d.feedings_count || 0), w, h].join(','))
      }
      return lines.join('\n') + '\n'
    },

    copyCsv() {
      if (!this.report) return
      const csv = this.buildCsv()
      uni.setClipboardData({
        data: csv,
        success: () => uni.showToast({ title: '已复制', icon: 'none' }),
        fail: () => uni.showToast({ title: '复制失败', icon: 'none' }),
      })
    },

    copyDay(d) {
      const text = `${d.date}  总奶量:${d.total_amount || 0}ml  次数:${d.feedings_count || 0}  体重:${d.weight || '--'}kg  身高:${d.height || '--'}cm`
      uni.setClipboardData({
        data: text,
        success: () => uni.showToast({ title: '已复制', icon: 'none' }),
        fail: () => uni.showToast({ title: '复制失败', icon: 'none' }),
      })
    },

    downloadCsv() {
      if (!this.report) return
      if (typeof document === 'undefined') {
        return this.copyCsv()
      }
      const csv = this.buildCsv()
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `naibao-report-${this.fromDate}-${this.toDate}.csv`
      document.body.appendChild(a)
      a.click()
      try { a.remove() } catch {}
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },
  },
}
</script>

<style scoped>
.report-container {
  min-height: 100vh;
  padding: calc(18px + var(--nb-safe-top)) var(--nb-page-x) calc(18px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.top-bar {
  padding: 8px 4px 14px;
}

.title {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--nb-text);
  display: block;
}

.subtitle {
  margin-top: 6px;
  display: block;
  color: var(--nb-muted);
  font-size: 13px;
}

.range-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 16px;
  box-sizing: border-box;
  box-shadow: 0 14px 36px rgba(27, 26, 23, 0.10);
}

.range-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.range-label {
  color: var(--nb-muted);
  font-size: 12px;
}

.range-value {
  color: var(--nb-text);
  font-size: 13px;
  font-weight: 700;
}

.chips {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.72);
  color: var(--nb-muted);
  font-size: 12px;
  user-select: none;
}

.chip.active {
  background: rgba(247, 201, 72, 0.22);
  color: var(--nb-text);
  border-color: rgba(247, 201, 72, 0.55);
}

.pickers {
  display: flex;
  gap: 12px;
}

.picker {
  flex: 1;
  padding: 12px 12px;
  border-radius: var(--nb-radius-md);
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.78);
}

.picker-k {
  color: var(--nb-muted);
  font-size: 11px;
  display: block;
}

.picker-v {
  margin-top: 6px;
  color: var(--nb-text);
  font-size: 14px;
  font-weight: 800;
  display: block;
}

.actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
}

.primary-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
  font-weight: 800;
  border: none;
  font-size: 14px;
}

.ghost-btn {
  width: 92px;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.06);
  color: var(--nb-text);
  border: 1px solid var(--nb-border);
  font-size: 12px;
}

.report-body {
  margin-top: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-card {
  padding: 14px;
  border-radius: var(--nb-radius-lg);
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.9);
}

.summary-k {
  color: var(--nb-muted);
  font-size: 12px;
  display: block;
}

.summary-v {
  margin-top: 8px;
  font-size: 18px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
}

.days-card {
  margin-top: 14px;
  border-radius: var(--nb-radius-lg);
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.92);
  overflow: hidden;
}

.days-header {
  padding: 14px 14px 10px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.days-title {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.days-hint {
  font-size: 11px;
  color: var(--nb-muted);
}

.days-table {
  padding: 0 10px 10px;
}

.days-row {
  display: flex;
  align-items: center;
  border-radius: 14px;
  padding: 10px 10px;
  margin-top: 8px;
  background: rgba(27, 26, 23, 0.03);
  border: 1px solid rgba(27, 26, 23, 0.06);
}

.days-row-head {
  background: rgba(247, 201, 72, 0.16);
  border-color: rgba(247, 201, 72, 0.35);
  margin-top: 0;
}

.col {
  font-size: 12px;
  color: var(--nb-text);
}

.col.date { width: 70px; }
.col.amt  { width: 64px; text-align: right; }
.col.cnt  { width: 56px; text-align: right; }
.col.wh   { flex: 1; text-align: right; color: var(--nb-muted); }
</style>
