<template>
  <view class="data-detail-container">
    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能查看身高体重与奶量趋势"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbState v-else-if="pageLoading" type="loading" title="加载中..." />

    <NbState
      v-else-if="errorText"
      type="error"
      title="加载失败"
      :desc="errorText"
      actionText="重试"
      @action="reload"
    />

    <template v-else>
    <!-- 顶部信息 -->
    <view class="header-info">
      <text class="info-item">出生 {{ ageText }}</text>
      <text class="info-item">身高 {{ currentHeight }} cm</text>
      <text class="info-item">体重 {{ currentWeight }} kg</text>
      <view class="info-action" @click="goToFeedingSettings">
        <text class="info-action-text">喂奶设置</text>
        <text class="info-action-arrow">›</text>
      </view>
    </view>

    <!-- 统计卡片 -->
    <view class="stats-cards">
      <view class="stat-card weight-gain">
        <view class="stat-header">
          <text class="stat-top-label">出生 {{ ageText }}</text>
        </view>
        <view class="stat-content">
          <text class="stat-label">日均增重</text>
          <text class="stat-value">{{ dailyWeightGain }}kg</text>
        </view>
      </view>
      
      <view class="stat-card height-gain">
        <view class="stat-header">
          <text class="stat-top-label">身高 {{ currentHeight }} cm</text>
        </view>
        <view class="stat-content">
          <text class="stat-label">日均增高</text>
          <text class="stat-value">{{ dailyHeightGain }}mm</text>
        </view>
      </view>
      
      <view class="stat-card milk-avg">
        <view class="stat-header">
          <text class="stat-top-label">体重 {{ currentWeight }} kg</text>
        </view>
        <view class="stat-content">
          <text class="stat-label">日奶均量</text>
          <text class="stat-value">{{ dailyAvgMilk }}ml</text>
        </view>
      </view>
    </view>

    <!-- 参考值 -->
    <view class="reference-section">
      <view class="reference-bar">
        <text class="reference-label">参考值</text>
        <view class="reference-values">
          <text class="reference-value">{{ reference.weightGain }}</text>
          <text class="reference-value">{{ reference.heightGain }}</text>
          <text class="reference-value">{{ reference.milk }}</text>
        </view>
        <text class="reference-help">?</text>
      </view>
      <text class="reference-suggestion" v-if="suggestion">
        {{ suggestion }}
      </text>
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

    <!-- 数据表格 -->
    <view class="table-section">
      <view class="table-header">
        <text class="table-col">体重 kg</text>
        <text class="table-col">身高 cm</text>
        <text class="table-col">日总奶量 ml</text>
      </view>
      
      <view 
        v-for="(record, index) in dailyRecords" 
        :key="record.date || index"
        class="table-row"
        @click="editRecord(record)"
      >
        <text class="table-col-date">{{ formatDate(record.date) }}</text>
        <text class="table-col" :class="{ 'data-highlight': record.weight }">
          {{ record.weight ? record.weight.toFixed(1) : '/' }}
        </text>
        <text class="table-col" :class="{ 'data-highlight': record.height }">
          {{ record.height || '/' }}
        </text>
        <text class="table-col" :class="{ 'data-highlight red-text': record.daily_amount > 0 }">
          {{ record.daily_amount || '/' }}
          <text v-if="record.daily_amount > 0 && record.isManual" class="manual-indicator">+</text>
        </text>
      </view>
    </view>

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
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatAgeTextFromDays, formatBabyAgeText } from '@/utils/age'
import NbState from '@/components/NbState.vue'

export default {
  components: { NbState },
  data() {
    return {
      babyId: null,
      pageLoading: false,
      errorText: '',
      lastInitBabyId: null,
      ageInDays: 0,
      currentHeight: 0,
      currentWeight: 0,
      dailyWeightGain: 0,
      dailyHeightGain: 0,
      dailyAvgMilk: 0,
      reference: {
        weightGain: '0.15-0.2',
        heightGain: '8-11',
        milk: '800-900'
      },
      suggestion: '',
      selectedMonth: '',
      months: [],
      dailyRecords: [],
      formulaSpec: null,

      // 编辑弹窗
      showEditModal: false,
      editingDate: '',
      editWeight: '',
      editHeight: '',
      saving: false
    }
  },

  computed: {
    ageText() {
      const userStore = useUserStore()
      const t = formatBabyAgeText(userStore.currentBaby?.birth_date)
      if (t) return t
      return formatAgeTextFromDays(this.ageInDays)
    },
    editingDateDisplay() {
      if (!this.editingDate) return ''
      // YYYY-MM-DD -> MM.DD（列表一致）
      const d = new Date(this.editingDate)
      if (Number.isNaN(d.getTime())) return this.editingDate
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
    // tabBar 页：从其他页面返回时，可能刚创建/切换宝宝，需要刷新数据
    if (!this.babyId) {
      const userStore = useUserStore()
      if (userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
    }

    if (this.babyId && String(this.lastInitBabyId) !== String(this.babyId)) {
      this.reload()
    }
  },
  
  methods: {
    initMonths() {
      const now = new Date()
      const months = []
      
      // 生成最近6个月
      for (let i = 5; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
        months.push(date.toISOString().slice(0, 7)) // YYYY-MM
      }
      
      this.months = months
      this.selectedMonth = months[months.length - 1] // 默认当前月
    },
    
    async loadData() {
      await Promise.all([
        this.loadGrowthStats(),
        this.loadDailyRecords(),
        // 非核心：失败时兜底为 null
        this.loadFormulaSpec()
      ])
    },
    
    async loadGrowthStats() {
      try {
        const res = await api.get(`/babies/${this.babyId}/growth-stats`)
        this.ageInDays = res.age_in_days || 0
        this.currentHeight = res.current_height || 0
        this.currentWeight = res.current_weight || 0
        this.dailyWeightGain = (res.daily_weight_gain || 0).toFixed(3)
        this.dailyHeightGain = Math.round(res.daily_height_gain || 0)
        this.dailyAvgMilk = Math.round(res.daily_avg_milk || 0)
        
        if (res.reference) {
          this.reference = {
            weightGain: res.reference.weight_gain || '0.15-0.2',
            heightGain: res.reference.height_gain || '8-11',
            milk: res.reference.milk || '800-900'
          }
        }
        
        // 生成建议
        this.generateSuggestion()
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

    async loadFormulaSpec() {
      if (!this.babyId) return
      try {
        const res = await api.get(`/babies/${this.babyId}/formula/specification`)
        this.formulaSpec = res.specification || null
      } catch {
        this.formulaSpec = null
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

    goToFeedingSettings() {
      if (!this.babyId) return
      uni.navigateTo({ url: `/pages/feeding-settings/index?babyId=${this.babyId}` })
    },
    
    async selectMonth(month) {
      this.selectedMonth = month
      try {
        await this.loadDailyRecords()
      } catch (e) {
        uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
      }
    },
    
    formatDate(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return String(date.getDate()).padStart(2, '0')
    },
    
    formatMonth(monthStr) {
      if (!monthStr) return ''
      const [year, month] = monthStr.split('-')
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
    
    generateSuggestion() {
      // 根据数据生成建议
      if (this.dailyAvgMilk < 800) {
        const delta = 20
        this.suggestion = `建议每餐+${delta}ml（${this.getFormulaSuggestion(delta)}）`
      } else if (this.dailyAvgMilk > 900) {
        const delta = 20
        this.suggestion = `建议每餐-${delta}ml（${this.getFormulaSuggestion(-delta)}）`
      } else {
        this.suggestion = ''
      }
    },
    
    getFormulaSuggestion(deltaMl) {
      const ml = Number(this.formulaSpec?.scoop_ml || 0)
      const delta = Number(deltaMl || 0)
      if (!ml || ml <= 0 || !delta) return '按包装换算勺数'
      const raw = Math.abs(delta) / ml
      const rounded = Math.round(raw * 2) / 2
      const sign = delta > 0 ? '+' : '-'
      return `约 ${sign}${rounded}勺（按${ml}ml/勺）`
    }
  }
}
</script>

<style scoped>
.data-detail-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + env(safe-area-inset-top, 0px)) var(--nb-page-x)
    calc(88px + env(safe-area-inset-bottom, 0px)); /* tabbar + 安全区 */
  box-sizing: border-box;
}

.header-info {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 14px 16px;
  margin-bottom: 14px;
}

.info-item {
  font-size: 13px;
  color: var(--nb-muted);
  flex: 1 1 30%;
  text-align: center;
}

.info-action {
  flex: 1 1 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.60);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.info-action-text {
  font-size: 13px;
  font-weight: 700;
  color: var(--nb-text);
}

.info-action-arrow {
  font-size: 16px;
  color: rgba(27, 26, 23, 0.55);
  line-height: 1;
}

.stats-cards {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  margin-bottom: 14px;
  gap: 10px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 0;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 14px 14px;
  display: flex;
  flex-direction: column;
}

@media (max-width: 360px) {
  .stat-card {
    flex: 1 1 100%;
  }
}

.stat-header {
  margin-bottom: 10px;
}

.stat-top-label {
  font-size: 12px;
  color: var(--nb-muted);
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: var(--nb-muted);
  margin-bottom: 5px;
}

.stat-value {
  font-size: 16px;
  font-weight: bold;
  color: var(--nb-text);
}

.weight-gain .stat-value {
  color: #f5222d;
}

.height-gain .stat-value {
  color: #52c41a;
}

.milk-avg .stat-value {
  color: #ff7a3d;
}

.reference-section {
  margin-bottom: 14px;
}

.reference-bar {
  display: flex;
  flex-direction: row;
  align-items: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 12px 14px;
  gap: 10px;
}

.reference-label {
  font-size: 13px;
  color: var(--nb-muted);
  font-weight: 600;
}

.reference-values {
  display: flex;
  flex-direction: row;
  flex: 1;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.reference-value {
  font-size: 12px;
  color: var(--nb-text);
  background: rgba(27, 26, 23, 0.06);
  padding: 6px 10px;
  border-radius: 999px;
}

.reference-help {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(27, 26, 23, 0.08);
  color: var(--nb-text);
  text-align: center;
  line-height: 24px;
  font-size: 14px;
}

.reference-suggestion {
  font-size: 12px;
  color: var(--nb-muted);
  display: block;
  margin-top: 10px;
  padding: 0 2px;
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

.table-section {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
}

.table-header {
  display: flex;
  flex-direction: row;
  background: rgba(27, 26, 23, 0.05);
  padding: 12px 12px;
  border-bottom: 1px solid var(--nb-border);
}

.table-row {
  display: flex;
  flex-direction: row;
  min-height: 52px;
  padding: 12px 12px;
  border-bottom: 1px solid rgba(27, 26, 23, 0.08);
}

.table-col-date {
  width: 50px;
  font-size: 14px;
  color: var(--nb-muted);
  text-align: left;
}

.table-col {
  flex: 1;
  font-size: 14px;
  color: var(--nb-text);
  text-align: center;
}

.table-header .table-col {
  font-weight: 500;
  color: var(--nb-muted);
}

.data-highlight {
  font-weight: bold;
}

.red-text {
  color: #f5222d;
}

.manual-indicator {
  color: #f5222d;
  font-size: 12px;
  margin-left: 3px;
}

/* 编辑弹窗 */
.edit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: 18px;
  box-sizing: border-box;
}

.edit-modal-content {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: var(--nb-radius-lg);
  padding: 18px;
  box-sizing: border-box;
}

.edit-modal-header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.edit-modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.edit-modal-body {
  padding: 20px 0 10px;
}

.edit-field {
  margin-bottom: 14px;
}

.edit-label {
  display: block;
  font-size: 13px;
  color: var(--nb-muted);
  margin-bottom: 6px;
}

.edit-input {
  width: 100%;
  height: 48px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 0 14px;
  box-sizing: border-box;
  font-size: 16px;
}

.edit-input:focus {
  outline: none;
  border-color: #FFD700;
}

.edit-modal-footer {
  display: flex;
  flex-direction: row;
  gap: 12px;
  margin-top: 6px;
}

.cancel-btn, .confirm-btn {
  flex: 1;
  height: 48px;
  border-radius: 24px;
  border: none;
  font-size: 16px;
  font-weight: 600;
}

.cancel-btn {
  background: #f5f5f5;
  color: #666;
}

.confirm-btn {
  background: #FFD700;
  color: #333;
}

.confirm-btn[disabled] {
  background: #f0f0f0;
  color: #999;
}
</style>
