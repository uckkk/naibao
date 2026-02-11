<template>
  <view class="data-detail-container">
    <NbNetworkBanner />
    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能查看身高体重与奶量趋势"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbLoadingSwitch v-else :loading="pageLoading">
      <template #skeleton>
        <view class="dd-hero">
          <view class="dd-title-row">
            <NbSkeleton :w="72" :h="18" :radius="9" />
            <NbSkeleton :w="56" :h="14" :radius="7" />
          </view>
          <view style="margin-top:10px;">
            <NbSkeleton :w="220" :h="12" :radius="6" />
          </view>

          <view class="dd-metrics">
            <view class="dd-metric">
              <view class="dd-metric-head">
                <NbSkeleton :w="130" :h="12" :radius="6" />
                <NbSkeleton :w="92" :h="16" :radius="8" />
              </view>
              <view style="margin-top:10px;">
                <NbSkeleton :w="'100%'" :h="12" :radius="6" />
              </view>
            </view>
            <view class="dd-divider"></view>
            <view class="dd-metric">
              <view class="dd-metric-head">
                <NbSkeleton :w="100" :h="12" :radius="6" />
                <NbSkeleton :w="92" :h="16" :radius="8" />
              </view>
              <view style="margin-top:10px;">
                <NbSkeleton :w="'100%'" :h="12" :radius="6" />
              </view>
            </view>
            <view class="dd-divider"></view>
            <view class="dd-metric">
              <view class="dd-metric-head">
                <NbSkeleton :w="100" :h="12" :radius="6" />
                <NbSkeleton :w="92" :h="16" :radius="8" />
              </view>
              <view style="margin-top:10px;">
                <NbSkeleton :w="'100%'" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>

        <view class="month-picker-section">
          <NbSkeleton :w="'100%'" :h="50" :radius="18" />
        </view>

        <view class="records-toolbar">
          <NbSkeleton :w="70" :h="14" :radius="7" />
          <NbSkeleton :w="150" :h="34" :radius="17" />
        </view>

        <view class="records-list">
          <view v-for="i in 6" :key="i" class="record-cell">
            <NbSkeleton :w="70" :h="12" :radius="6" />
            <NbSkeleton :w="180" :h="12" :radius="6" />
            <NbSkeleton :w="10" :h="12" :radius="6" />
          </view>
        </view>
      </template>

      <NbState
        v-if="errorText"
        type="error"
        title="加载失败"
        :desc="errorText"
        actionText="重试"
        @action="reload"
      />

      <template v-else>
    <!-- 信息减法：合并“宝宝信息/统计/参考”到一个摘要卡（更像 iOS Health 的信息层级） -->
    <view class="dd-hero">
      <view class="dd-title-row">
        <text class="dd-title">{{ babyName }}</text>
        <view class="dd-help" @click="openReferenceSheet">
          <text class="dd-help-text">参考</text>
          <text class="dd-help-icon">?</text>
        </view>
      </view>

      <text v-if="heroSubText" class="dd-sub">{{ heroSubText }}</text>

      <view class="dd-metrics">
        <view class="dd-metric">
          <view class="dd-metric-head">
            <text class="dd-metric-label">近7天奶量</text>
            <text class="dd-metric-value">{{ milkValueText }}</text>
          </view>
          <view v-if="milkRangeModel.showTrack" class="dd-range">
            <view class="dd-range-track">
              <view class="dd-range-band" :style="{ left: milkRangeModel.bandLeft + '%', width: milkRangeModel.bandWidth + '%' }"></view>
              <view class="dd-range-marker" :class="`st-${milkRangeModel.status}`" :style="{ left: milkRangeModel.markerLeft + '%' }"></view>
            </view>
            <text v-if="milkRangeModel.status === 'low' || milkRangeModel.status === 'high'" class="dd-range-ref">{{ milkRangeModel.refText }}</text>
          </view>
          <text v-if="milkTipText" class="dd-tip">{{ milkTipText }}</text>
        </view>

        <view class="dd-divider"></view>

        <view class="dd-metric">
          <view class="dd-metric-head">
            <text class="dd-metric-label">增重</text>
            <text class="dd-metric-value">{{ weightGainValueText }}</text>
          </view>
          <view v-if="weightGainRangeModel.showTrack" class="dd-range">
            <view class="dd-range-track">
              <view class="dd-range-band" :style="{ left: weightGainRangeModel.bandLeft + '%', width: weightGainRangeModel.bandWidth + '%' }"></view>
              <view class="dd-range-marker" :class="`st-${weightGainRangeModel.status}`" :style="{ left: weightGainRangeModel.markerLeft + '%' }"></view>
            </view>
            <text v-if="weightGainRangeModel.status === 'low' || weightGainRangeModel.status === 'high'" class="dd-range-ref">{{ weightGainRangeModel.refText }}</text>
          </view>
        </view>

        <view class="dd-divider"></view>

        <view class="dd-metric">
          <view class="dd-metric-head">
            <text class="dd-metric-label">增高</text>
            <text class="dd-metric-value">{{ heightGainValueText }}</text>
          </view>
          <view v-if="heightGainRangeModel.showTrack" class="dd-range">
            <view class="dd-range-track">
              <view class="dd-range-band" :style="{ left: heightGainRangeModel.bandLeft + '%', width: heightGainRangeModel.bandWidth + '%' }"></view>
              <view class="dd-range-marker" :class="`st-${heightGainRangeModel.status}`" :style="{ left: heightGainRangeModel.markerLeft + '%' }"></view>
            </view>
            <text v-if="heightGainRangeModel.status === 'low' || heightGainRangeModel.status === 'high'" class="dd-range-ref">{{ heightGainRangeModel.refText }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 月份切换 -->
    <view class="month-picker-section">
      <scroll-view class="month-picker" scroll-x>
        <view 
          v-for="month in months" 
          :key="month"
          :class="['month-item', { active: month === selectedMonth }]"
          @click="selectMonth(month)"
        >
          {{ formatMonth(month) }}
        </view>
      </scroll-view>
    </view>

    <!-- 每日记录：默认只显示“有记录”的日期，避免信息噪音 -->
    <view class="records-toolbar">
      <text class="records-title">每日记录</text>
      <view class="records-seg">
        <view class="seg-item" :class="{ active: !showAllDays }" @click="setShowAllDays(false)">有记录</view>
        <view class="seg-item" :class="{ active: showAllDays }" @click="setShowAllDays(true)">全部</view>
      </view>
    </view>

    <view class="records-list">
      <view v-if="visibleDailyRecords.length <= 0" class="records-empty">
        <text class="records-empty-title">本月还没有记录</text>
        <text class="records-empty-sub">喂奶会自动汇总到这里；体重/身高可点任意日期补录</text>
      </view>

      <view
        v-for="(record, index) in visibleDailyRecords"
        :key="record.date || index"
        class="record-cell tappable"
        @click="editRecord(record)"
      >
        <view class="record-left">
          <text class="record-date">{{ formatDateMD(record.date) }}</text>
          <text class="record-week">{{ formatWeekday(record.date) }}</text>
        </view>

        <view class="record-right">
          <view v-if="Number(record.daily_amount || 0) > 0" class="record-milk-row">
            <view class="record-dot" :class="`st-${milkDayStatus(record.daily_amount)}`"></view>
            <text class="record-milk">{{ record.daily_amount }}ml</text>
          </view>
          <text v-else class="record-milk-empty">—</text>

          <text v-if="growthText(record)" class="record-growth">{{ growthText(record) }}</text>
        </view>

        <text class="record-arrow">›</text>
      </view>
    </view>

    <NbConfirmSheet
      :visible="referenceSheetVisible"
      title="参考范围"
      :desc="referenceSheetDesc"
      confirmText="知道了"
      :showCancel="false"
      @confirm="closeReferenceSheet"
      @cancel="closeReferenceSheet"
    />

    <!-- 编辑弹窗：录入体重/身高（按日期 upsert） -->
    <view
      v-if="showEditModal"
      class="edit-modal-overlay"
      @click.self="closeEditModal"
      @touchmove.prevent
      @wheel.prevent
    >
      <view
        class="edit-modal-content"
        @click.stop
        @touchstart.stop
        @touchmove.stop
        @wheel.stop
      >
        <view class="edit-modal-header">
          <text class="edit-modal-title">编辑 {{ editingDateDisplay }}</text>
          <text class="close-btn" @click="closeEditModal">×</text>
        </view>

        <view class="edit-modal-body">
          <view class="edit-field">
            <text class="edit-label">体重 (kg)</text>
            <input
              class="edit-input"
              type="number"
              inputmode="decimal"
              v-model="editWeight"
              placeholder="例如 4.5"
            />
          </view>

          <view class="edit-field">
            <text class="edit-label">身高 (cm)</text>
            <input
              class="edit-input"
              type="number"
              inputmode="numeric"
              v-model="editHeight"
              placeholder="例如 55"
            />
          </view>
        </view>

        <view class="edit-modal-footer">
          <button class="cancel-btn" @click="closeEditModal">取消</button>
          <button class="confirm-btn" :disabled="saving" @click="saveEdit">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </view>
      </view>
    </view>
    </template>
    </NbLoadingSwitch>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatAgeTextFromDays, formatBabyAgeText } from '@/utils/age'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadingSwitch from '@/components/NbLoadingSwitch.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'

function clamp(n, min, max) {
  const v = Number(n)
  if (!Number.isFinite(v)) return min
  return Math.max(min, Math.min(max, v))
}

function parseDateOnly(dateStr) {
  // 统一处理 YYYY-MM-DD（纯日期）字符串，避免 new Date('YYYY-MM-DD') 在不同时区产生偏移。
  const s = String(dateStr || '').trim()
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(d)) return null
  const dt = new Date(y, mo - 1, d)
  if (Number.isNaN(dt.getTime())) return null
  return dt
}

function parseRangeText(text) {
  const s = String(text || '').trim()
  if (!s) return null
  const m = s.match(/(-?\d+(?:\.\d+)?)\s*(?:-|~|至|—|–)\s*(-?\d+(?:\.\d+)?)/)
  if (!m) return null
  const min = Number(m[1])
  const max = Number(m[2])
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null
  if (max <= min) return null
  return { min, max, raw: s }
}

function buildRangeModel(value, range, refText) {
  const ref = String(refText || '').trim()
  const v = Number(value)
  if (!range || !Number.isFinite(v)) {
    return { refText: ref ? `参考 ${ref}` : '', showTrack: false, bandLeft: 0, bandWidth: 0, markerLeft: 0, status: 'unknown' }
  }

  const min = Number(range.min)
  const max = Number(range.max)
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    return { refText: ref ? `参考 ${ref}` : '', showTrack: false, bandLeft: 0, bandWidth: 0, markerLeft: 0, status: 'unknown' }
  }

  const span = max - min
  const pad = Math.max(span * 0.35, span * 0.15, 1e-6)
  const scaleMin = min - pad
  const scaleMax = max + pad
  const denom = Math.max(1e-6, scaleMax - scaleMin)

  const bandLeft = clamp(((min - scaleMin) / denom) * 100, 0, 100)
  const bandWidth = clamp(((max - min) / denom) * 100, 1, 100)
  const markerLeft = clamp(((v - scaleMin) / denom) * 100, 0, 100)
  const status = v < min ? 'low' : (v > max ? 'high' : 'ok')

  return {
    refText: ref ? `参考 ${ref}` : '',
    showTrack: true,
    bandLeft: Number(bandLeft.toFixed(2)),
    bandWidth: Number(bandWidth.toFixed(2)),
    markerLeft: Number(markerLeft.toFixed(2)),
    status,
  }
}

export default {
  components: { NbState, NbNetworkBanner, NbLoadingSwitch, NbSkeleton, NbConfirmSheet },
  data() {
    return {
      babyId: null,
      pageLoading: false,
      errorText: '',
      lastInitBabyId: null,
      ageInDays: 0,
      currentHeight: 0,
      currentWeight: 0,
      dailyWeightGain: 0, // kg/天（后端原始值）
      dailyHeightGain: 0, // mm/天（后端原始值）
      dailyAvgMilk: 0, // ml/天（后端原始值：最近7天平均）
      reference: {
        weightGain: '0.15-0.2',
        heightGain: '8-11',
        milk: '800-900'
      },
      selectedMonth: '',
      months: [],
      dailyRecords: [],
      showAllDays: false,

      // 参考说明（信息减法：默认不占屏）
      referenceSheetVisible: false,

      // 编辑弹窗
      showEditModal: false,
      editingDate: '',
      editWeight: '',
      editHeight: '',
      saving: false
    }
  },

  computed: {
    babyName() {
      const userStore = useUserStore()
      return userStore.currentBaby?.nickname || '宝宝'
    },

    ageText() {
      const userStore = useUserStore()
      const t = formatBabyAgeText(userStore.currentBaby?.birth_date)
      if (t) return t
      return formatAgeTextFromDays(this.ageInDays)
    },

    heroSubText() {
      const parts = []
      const age = String(this.ageText || '').trim()
      if (age) parts.push(age)

      const w = Number(this.currentWeight || 0)
      if (Number.isFinite(w) && w > 0) parts.push(`${w.toFixed(1)}kg`)

      const h = Number(this.currentHeight || 0)
      if (Number.isFinite(h) && h > 0) parts.push(`${Math.round(h)}cm`)

      return parts.join(' · ')
    },

    milkValueText() {
      const v = Number(this.dailyAvgMilk || 0)
      if (!Number.isFinite(v) || v <= 0) return '—'
      return `${Math.round(v)}ml/天`
    },

    weightGainValueText() {
      const vKg = Number(this.dailyWeightGain || 0)
      if (!Number.isFinite(vKg) || vKg <= 0) return '—'
      const g = Math.round(vKg * 1000)
      return `${g}g/天`
    },

    heightGainValueText() {
      const v = Number(this.dailyHeightGain || 0)
      if (!Number.isFinite(v) || v <= 0) return '—'
      return `${Math.round(v)}mm/天`
    },

    milkRangeModel() {
      const v = Number(this.dailyAvgMilk || 0)
      const range = parseRangeText(this.reference?.milk)
      const value = Number.isFinite(v) && v > 0 ? v : NaN
      return buildRangeModel(value, range, this.reference?.milk)
    },

    weightGainRangeModel() {
      const refText = String(this.reference?.weightGain || '').trim()
      const raw = parseRangeText(refText)
      if (!raw) return buildRangeModel(NaN, null, refText)

      // 统一为 g/天：后端值为 kg/天；参考可能为 kg/天 或 g/天（来自 DB）
      const refLower = refText.toLowerCase()
      const assumeKg = refLower.includes('kg') || (!refLower.includes('g') && raw.max < 1)
      const range = assumeKg
        ? { min: raw.min * 1000, max: raw.max * 1000 }
        : { min: raw.min, max: raw.max }

      const vKg = Number(this.dailyWeightGain || 0)
      const value = Number.isFinite(vKg) && vKg > 0 ? vKg * 1000 : NaN

      const displayRef = `${Math.round(range.min)}-${Math.round(range.max)}g/天`
      return buildRangeModel(value, range, displayRef)
    },

    heightGainRangeModel() {
      const refText = String(this.reference?.heightGain || '').trim()
      const range = parseRangeText(refText)
      const v = Number(this.dailyHeightGain || 0)
      const value = Number.isFinite(v) && v > 0 ? v : NaN
      return buildRangeModel(value, range, refText)
    },

    milkTipText() {
      const model = this.milkRangeModel
      if (!model || !model.showTrack) return ''
      if (model.status !== 'low' && model.status !== 'high') return ''

      const delta = 20
      if (model.status === 'low') {
        return `偏低：每次 +${delta}ml`
      }
      return `偏高：每次 -${delta}ml`
    },

    referenceSheetDesc() {
      const milk = String(this.reference?.milk || '').trim()
      const wg = String(this.reference?.weightGain || '').trim()
      const hg = String(this.reference?.heightGain || '').trim()

      const lines = []
      if (milk) lines.push(`奶量 ${milk}`)
      if (wg) lines.push(`增重 ${wg}`)
      if (hg) lines.push(`增高 ${hg}`)
      lines.push('')
      lines.push('仅供趋势参考，不替代医生建议')
      return lines.join('\\n')
    },

    visibleDailyRecords() {
      const list = Array.isArray(this.dailyRecords) ? this.dailyRecords : []
      if (this.showAllDays) return list
      return list.filter((r) => {
        const hasMilk = Number(r?.daily_amount || 0) > 0
        const hasW = r?.weight != null && Number(r.weight) > 0
        const hasH = r?.height != null && Number(r.height) > 0
        return hasMilk || hasW || hasH
      })
    },

    editingDateDisplay() {
      if (!this.editingDate) return ''
      // YYYY-MM-DD -> MM.DD（列表一致）
      const d = parseDateOnly(this.editingDate)
      if (!d) return this.editingDate
      return `${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
    }
  },
  
  onLoad(options) {
    if (options.babyId) {
      this.babyId = options.babyId
    } else {
      const userStore = useUserStore()
      if (userStore.currentBaby) {
        this.babyId = userStore.currentBaby.id
      }
    }
  },

  onShow() {
    // 从其他页面返回时，可能刚创建/切换宝宝，需要刷新数据
    if (!this.babyId) {
      const userStore = useUserStore()
      if (userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
    }

    if (this.babyId && String(this.lastInitBabyId) !== String(this.babyId)) {
      this.reload()
    }
  },
  
  methods: {
    onNbRetry() {
      this.reload()
    },

    initMonths() {
      const now = new Date()
      const months = []
      
      // 生成最近6个月
      for (let i = 5; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
        const y = date.getFullYear()
        const m = String(date.getMonth() + 1).padStart(2, '0')
        months.push(`${y}-${m}`) // YYYY-MM（本地口径，避免时区偏移）
      }
      
      this.months = months
      this.selectedMonth = months[months.length - 1] // 默认当前月
    },
    
    async loadData() {
      await Promise.all([
        this.loadGrowthStats(),
        this.loadDailyRecords(),
      ])
    },
    
    async loadGrowthStats() {
      try {
        const res = await api.get(`/babies/${this.babyId}/growth-stats`)
        this.ageInDays = res.age_in_days || 0
        this.currentHeight = res.current_height || 0
        this.currentWeight = res.current_weight || 0
        this.dailyWeightGain = Number(res.daily_weight_gain || 0)
        this.dailyHeightGain = Number(res.daily_height_gain || 0)
        this.dailyAvgMilk = Number(res.daily_avg_milk || 0)
        
        if (res.reference) {
          this.reference = {
            weightGain: res.reference.weight_gain || '0.15-0.2',
            heightGain: res.reference.height_gain || '8-11',
            milk: res.reference.milk || '800-900'
          }
        }
      } catch (error) {
        console.error('加载统计数据失败', error)
        throw error
      }
    },
    
    async loadDailyRecords() {
      try {
        const res = await api.get(`/babies/${this.babyId}/daily-records`, {
          month: this.selectedMonth
        })
        this.dailyRecords = res.records || []
      } catch (error) {
        console.error('加载每日记录失败', error)
        throw error
      }
    },

    async reload() {
      if (!this.babyId) return
      this.pageLoading = true
      this.errorText = ''
      try {
        this.initMonths()
        await this.loadData()
        this.lastInitBabyId = this.babyId
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },

    openReferenceSheet() {
      this.referenceSheetVisible = true
    },

    closeReferenceSheet() {
      this.referenceSheetVisible = false
    },

    setShowAllDays(v) {
      this.showAllDays = !!v
    },
    
    async selectMonth(month) {
      this.selectedMonth = month
      try {
        await this.loadDailyRecords()
      } catch (e) {
        uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
      }
    },
    
    formatDateMD(dateStr) {
      if (!dateStr) return ''
      const date = parseDateOnly(dateStr)
      if (!date) return String(dateStr)
      return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
    },

    formatWeekday(dateStr) {
      if (!dateStr) return ''
      const date = parseDateOnly(dateStr)
      if (!date) return ''
      const names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      return names[date.getDay()] || ''
    },
    
    formatMonth(monthStr) {
      if (!monthStr) return ''
      const [year, month] = monthStr.split('-')
      const now = new Date()
      const y = Number(year)
      const m = Number(month)
      if (Number.isFinite(y) && Number.isFinite(m) && y === now.getFullYear()) return `${m}月`
      if (Number.isFinite(y) && Number.isFinite(m)) return `${y}年${m}月`
      return `${year}.${month}`
    },
    
    editRecord(record) {
      if (!record || !record.date) return
      this.editingDate = record.date
      this.editWeight = record.weight ? String(Number(record.weight).toFixed(1)) : ''
      this.editHeight = record.height ? String(record.height) : ''
      this.showEditModal = true
    },

    closeEditModal() {
      this.showEditModal = false
      this.editingDate = ''
      this.editWeight = ''
      this.editHeight = ''
      this.saving = false
    },

    async saveEdit() {
      if (!this.babyId || !this.editingDate || this.saving) return

      const weightStr = String(this.editWeight || '').trim()
      const heightStr = String(this.editHeight || '').trim()

      const payload = { record_date: this.editingDate }
      if (weightStr) {
        const w = Number.parseFloat(weightStr)
        if (!Number.isFinite(w) || w <= 0 || w > 30) {
          uni.showToast({ title: '体重格式不正确', icon: 'none' })
          return
        }
        payload.weight = w
      }
      if (heightStr) {
        const h = Number.parseInt(heightStr, 10)
        if (!Number.isFinite(h) || h <= 0 || h > 200) {
          uni.showToast({ title: '身高格式不正确', icon: 'none' })
          return
        }
        payload.height = h
      }

      if (!('weight' in payload) && !('height' in payload)) {
        uni.showToast({ title: '请至少填写体重或身高', icon: 'none' })
        return
      }

      this.saving = true
      try {
        await api.post(`/babies/${this.babyId}/growth-records`, payload)
        uni.showToast({ title: '保存成功', icon: 'success' })
        this.closeEditModal()
        await this.loadData()
      } catch (error) {
        uni.showToast({ title: error.message || '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
    
    milkDayStatus(amount) {
      const a = Number(amount || 0)
      if (!Number.isFinite(a) || a <= 0) return 'unknown'
      const range = parseRangeText(this.reference?.milk)
      if (!range) return 'unknown'
      if (a < range.min) return 'low'
      if (a > range.max) return 'high'
      return 'ok'
    },

    growthText(record) {
      const w = Number(record?.weight)
      const h = Number(record?.height)
      const parts = []
      if (Number.isFinite(w) && w > 0) parts.push(`${w.toFixed(1)}kg`)
      if (Number.isFinite(h) && h > 0) parts.push(`${Math.round(h)}cm`)
      return parts.join(' · ')
    }
  }
}
</script>

<style scoped>
.data-detail-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x)
    calc(28px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.tappable:active {
  background: rgba(27, 26, 23, 0.03);
}

.dd-hero {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 14px 34px rgba(27, 26, 23, 0.06);
  box-sizing: border-box;
}

.dd-title-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.dd-title {
  font-size: 18px;
  font-weight: 900;
  color: var(--nb-text);
  letter-spacing: -0.2px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dd-help {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(255, 255, 255, 0.65);
  box-sizing: border-box;
}

.dd-help-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.72);
}

.dd-help-icon {
  width: 18px;
  height: 18px;
  border-radius: 9px;
  background: rgba(27, 26, 23, 0.08);
  color: rgba(27, 26, 23, 0.72);
  text-align: center;
  line-height: 18px;
  font-size: 12px;
  font-weight: 900;
}

.dd-sub {
  margin-top: 10px;
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.60);
}

.dd-metrics {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dd-metric-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.dd-metric-label {
  font-size: 13px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.70);
}

.dd-metric-value {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
  white-space: nowrap;
}

.dd-divider {
  height: 1px;
  background: rgba(27, 26, 23, 0.08);
}

.dd-range {
  margin-top: 10px;
}

.dd-range-track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.08);
  overflow: hidden;
}

.dd-range-band {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 999px;
  background: rgba(46, 125, 50, 0.18);
}

.dd-range-marker {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  transform: translate(-50%, -50%);
  background: rgba(27, 26, 23, 0.92);
  border: 2px solid rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 24px rgba(27, 26, 23, 0.14);
  box-sizing: border-box;
}

.dd-range-marker.st-low {
  background: rgba(25, 118, 210, 0.92);
}

.dd-range-marker.st-high {
  background: rgba(255, 138, 61, 0.92);
}

.dd-range-marker.st-unknown {
  background: rgba(27, 26, 23, 0.30);
}

.dd-range-ref {
  margin-top: 8px;
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.55);
}

.dd-tip {
  margin-top: 8px;
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: rgba(181, 83, 29, 0.95);
}

.month-picker-section {
  margin-bottom: 12px;
}

.month-picker {
  white-space: nowrap;
  height: 50px;
}

.month-item {
  display: inline-block;
  padding: 0 16px;
  height: 38px;
  line-height: 38px;
  margin-right: 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  color: var(--nb-muted);
  font-size: 14px;
  cursor: pointer;
}

.month-item.active {
  background: rgba(247, 201, 72, 0.22);
  border-color: rgba(247, 201, 72, 0.45);
  color: var(--nb-text);
  font-weight: bold;
}

.records-toolbar {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 6px 2px 10px;
}

.records-title {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.records-seg {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 2px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  box-sizing: border-box;
}

.seg-item {
  padding: 0 12px;
  height: 30px;
  line-height: 30px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.62);
  user-select: none;
}

.seg-item.active {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.86);
  box-shadow: 0 10px 24px rgba(27, 26, 23, 0.10);
  box-sizing: border-box;
}

.records-list {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: 0 14px 34px rgba(27, 26, 23, 0.05);
}

.records-empty {
  padding: 22px 16px;
  text-align: center;
}

.records-empty-title {
  display: block;
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.records-empty-sub {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.55);
  line-height: 1.6;
}

.record-cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.record-cell:first-child {
  border-top: none;
}

.record-left {
  width: 78px;
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.record-date {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.record-week {
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.55);
  white-space: nowrap;
}

.record-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
}

.record-milk-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.record-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.30);
  box-shadow: 0 6px 16px rgba(27, 26, 23, 0.14);
}

.record-dot.st-ok {
  background: rgba(46, 125, 50, 0.88);
}

.record-dot.st-low {
  background: rgba(25, 118, 210, 0.90);
}

.record-dot.st-high {
  background: rgba(255, 138, 61, 0.92);
}

.record-dot.st-unknown {
  background: rgba(27, 26, 23, 0.26);
}

.record-milk {
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.86);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.record-milk-empty {
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.35);
  white-space: nowrap;
}

.record-growth {
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.55);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.record-arrow {
  flex: none;
  font-size: 18px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.35);
  line-height: 1;
}

/* 编辑弹窗 */
.edit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 2000;
  box-sizing: border-box;
}

.edit-modal-content {
  width: 100%;
  max-width: 560px;
  background:
    radial-gradient(900px 320px at 20% 0%, rgba(247, 201, 72, 0.18), rgba(247, 201, 72, 0) 60%),
    radial-gradient(700px 320px at 100% 20%, rgba(255, 138, 61, 0.14), rgba(255, 138, 61, 0) 62%),
    rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.70);
  border-radius: 24px 24px 0 0;
  padding: 18px 16px calc(18px + var(--nb-safe-bottom));
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.25);
  box-sizing: border-box;
  max-height: 78vh;
  overflow: hidden;
}

.edit-modal-header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  color: rgba(27, 26, 23, 0.62);
  text-align: center;
  line-height: 34px;
  font-size: 22px;
  font-weight: 900;
  user-select: none;
}

.edit-modal-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
}

.edit-modal-body {
  padding: 14px 0 10px;
}

.edit-field {
  margin-bottom: 14px;
}

.edit-label {
  display: block;
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.62);
  margin-bottom: 6px;
}

.edit-input {
  width: 100%;
  height: 46px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  border-radius: 14px;
  padding: 0 14px;
  box-sizing: border-box;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.96);
}

.edit-input:focus {
  outline: none;
  border-color: var(--nb-accent);
  box-shadow: 0 0 0 4px rgba(247, 201, 72, 0.22);
}

.edit-modal-footer {
  display: flex;
  flex-direction: row;
  gap: 12px;
  margin-top: 6px;
}

.cancel-btn, .confirm-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  font-size: 14px;
  font-weight: 900;
}

.cancel-btn {
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.82);
}

.confirm-btn {
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  border: none;
  color: var(--nb-text);
}

.confirm-btn[disabled] {
  background: rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.45);
}
</style>
