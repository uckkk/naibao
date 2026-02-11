<template>
  <view class="baby-info-container">
    <NbNetworkBanner />
    <!-- 头像和昵称 -->
    <view class="avatar-section">
      <image 
        :src="baby.avatar_url || '/static/default-avatar.png'" 
        class="baby-avatar"
        @click="selectAvatar"
        mode="aspectFill"
      />
      <text class="nickname-label">昵称</text>
      <text class="nickname-value">{{ baby.nickname || '宝宝' }}</text>
    </view>
    
    <!-- 信息字段 -->
    <view class="info-section">
      <view class="info-item" @click="editField('nickname')">
        <text class="label">昵称</text>
        <text class="value-display">{{ baby.nickname || '宝宝' }}</text>
      </view>
      
      <view class="info-item" @click="editField('birth_date')">
        <text class="label">出生日期</text>
        <view class="value-stack">
          <text class="value-display">{{ formatDateDisplay(baby.birth_date) || '未填写' }}</text>
          <text v-if="zodiacText" class="value-sub">{{ zodiacText }}</text>
        </view>
      </view>
      
      <view class="info-item" @click="editField('birth_time')">
        <text class="label">出生时间</text>
        <text class="value-display">{{ formatTimeDisplay(baby.birth_time) || '未填写' }}</text>
      </view>

      <view class="info-item" @click="editField('weight')">
        <text class="label">体重 <text class="unit">kg</text></text>
        <text class="value-display">{{ formatNumberDisplay(baby.current_weight) }}</text>
      </view>
      
      <view class="info-item" @click="editField('height')">
        <text class="label">身高 <text class="unit">cm</text></text>
        <text class="value-display">{{ formatNumberDisplay(baby.current_height) }}</text>
      </view>
    </view>
    
    <!-- 编辑弹窗 -->
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
          <text class="edit-modal-title">编辑{{ editFieldName }}</text>
          <text class="close-btn" @click="closeEditModal">×</text>
        </view>
        <view class="edit-modal-body">
          <!-- 昵称输入 -->
          <input 
            v-if="editingField === 'nickname'"
            v-model="editValue"
            class="edit-input-mobile"
            placeholder="请输入昵称"
            type="text"
            autofocus
          />
          
          <!-- 出生日期：H5 用真实 DOM 原生 date picker；小程序/App 用 picker -->
          <!-- #ifdef H5 -->
          <view
            v-if="editingField === 'birth_date'"
            class="picker-display-mobile"
            @click="openNativeBirthDate"
          >
            <text class="picker-label">选择日期</text>
            <text class="picker-value">{{ formatDateDisplay(editValue) || '请选择日期' }}</text>
          </view>
          <!-- #endif -->
          <!-- #ifndef H5 -->
          <picker
            v-if="editingField === 'birth_date'"
            mode="date"
            :value="editValue"
            @change="onEditDateChange"
          >
            <view class="picker-display-mobile">
              <text class="picker-label">选择日期</text>
              <text class="picker-value">{{ formatDateDisplay(editValue) || '请选择日期' }}</text>
            </view>
          </picker>
          <!-- #endif -->
          
          <!-- 出生时间：H5 用真实 DOM 原生 time picker；小程序/App 用 picker -->
          <!-- #ifdef H5 -->
          <view
            v-if="editingField === 'birth_time'"
            class="picker-display-mobile"
            @click="openNativeBirthTime"
          >
            <text class="picker-label">选择时间</text>
            <text class="picker-value">{{ editValue || '请选择时间' }}</text>
          </view>
          <!-- #endif -->
          <!-- #ifndef H5 -->
          <picker
            v-if="editingField === 'birth_time'"
            mode="time"
            :value="editValue"
            @change="onEditTimeChange"
          >
            <view class="picker-display-mobile">
              <text class="picker-label">选择时间</text>
              <text class="picker-value">{{ editValue || '请选择时间' }}</text>
            </view>
          </picker>
          <!-- #endif -->
          
          <!-- 体重/身高输入 -->
          <view v-if="editingField === 'weight' || editingField === 'height'" class="number-input-wrapper">
            <input 
              type="tel"
              inputmode="decimal"
              v-model="editValue"
              class="edit-input-mobile number-input"
              :placeholder="`请输入${editingField === 'weight' ? '体重' : '身高'}`"
              autofocus
            />
            <text class="input-unit">{{ editingField === 'weight' ? 'kg' : 'cm' }}</text>
          </view>
        </view>
        <view class="edit-modal-footer">
          <button class="cancel-btn" @click="closeEditModal">取消</button>
          <button class="confirm-btn" @click="saveEdit">确认</button>
        </view>
      </view>
    </view>

    <!-- 底部“完成”：H5 刷新/直达时可能没有返回栈，用它兜底回首页 -->
    <view class="page-footer">
      <button class="nb-primary-btn done-btn" :disabled="saving" @click="handleDone">
        {{ saving ? '保存中...' : '完成' }}
      </button>
    </view>

    <!-- 未完成也允许返回：避免“卡在建档流程”导致反复切换 -->
    <NbConfirmSheet
      :visible="incompleteSheetVisible"
      title="宝宝资料未完成"
      :desc="incompleteSheetDesc"
      confirmText="继续填写"
      cancelText="稍后再说"
      @confirm="handleIncompleteContinue"
      @cancel="handleIncompleteLater"
    />
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatZodiacText } from '@/utils/zodiac'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'

const DRAFT_KEY_NEW = 'nb_baby_draft_new_v1'

export default {
  components: { NbNetworkBanner, NbConfirmSheet },
  data() {
    return {
      baby: {
        id: null,
        nickname: '宝宝',
        avatar_url: '',
        birth_date: '',
        birth_time: '',
        current_weight: '',
        current_height: ''
      },
      isNew: true,
      dirty: false,
      saving: false,
      showEditModal: false,
      editingField: '',
      editValue: '',
      editFieldName: '',

      incompleteSheetVisible: false,
      incompleteSheetDesc: '',
      incompleteMissingField: '',
    }
  },

  computed: {
    zodiacText() {
      return formatZodiacText(this.baby?.birth_date) || ''
    }
  },
  
  onLoad(options) {
    if (options.id) {
      this.baby.id = options.id
      this.isNew = false
      this.loadBabyInfo()
    } else {
      const userStore = useUserStore()
      if (userStore.currentBaby) {
        this.baby = { ...userStore.currentBaby }
        this.isNew = false
        this.dirty = false
      }
    }

    // 新建时：如果用户中途返回/退出过，自动恢复草稿，避免反复切换
    if (this.isNew && !this.baby.id) {
      this.restoreDraft()
    }
  },

  onShow() {
    // 处理从“选择头像”等页面返回后，本页数据需要刷新
    if (this.baby.id && !this.isNew) {
      this.loadBabyInfo()
    }
  },

  onHide() {
    // 兜底：避免弹窗打开时离开页面导致 body 滚动锁死，影响“返回首页/返回上一页”
    this.unlockBodyScroll()

    // 新建宝宝时：允许未完成就返回，下次进来自动继续
    this.persistDraft()
  },

  onUnload() {
    this.unlockBodyScroll()
    this.persistDraft()
  },
  
  methods: {
    onNbRetry() {
      if (this.baby?.id && !this.isNew) this.loadBabyInfo()
    },

    goBackOrHome() {
      if (this.showEditModal) {
        this.closeEditModal()
        return
      }

      try {
        if (typeof getCurrentPages === 'function') {
          const pages = getCurrentPages() || []
          if (pages.length > 1) {
            uni.navigateBack()
            return
          }
        }
      } catch {}

      // 无返回栈（例如 H5 刷新/分享直达）：回到首页（重置栈，避免卡在资料页）
      uni.reLaunch({ url: '/pages/home/index' })
    },

    markDirty() {
      this.dirty = true
    },

    persistDraft() {
      // 仅对“新建宝宝”保存草稿，避免覆盖已存在宝宝的真实数据
      if (!this.isNew || this.baby?.id) return
      if (!this.dirty) return
      try {
        const draft = {
          nickname: this.baby.nickname || '',
          avatar_url: this.baby.avatar_url || '',
          birth_date: this.baby.birth_date || '',
          birth_time: this.baby.birth_time || '',
          current_weight: this.baby.current_weight || '',
          current_height: this.baby.current_height || '',
        }
        uni.setStorageSync(DRAFT_KEY_NEW, JSON.stringify(draft))
      } catch {}
    },

    clearDraft() {
      try {
        uni.removeStorageSync(DRAFT_KEY_NEW)
      } catch {}
    },

    restoreDraft() {
      try {
        const raw = uni.getStorageSync(DRAFT_KEY_NEW)
        if (!raw) return
        const d = JSON.parse(String(raw))
        if (!d || typeof d !== 'object') return

        const hasAny = ['nickname', 'avatar_url', 'birth_date', 'birth_time', 'current_weight', 'current_height']
          .some((k) => String(d?.[k] || '').trim())
        if (!hasAny) return

        const nickname = String(d.nickname || '').trim()
        this.baby = {
          ...this.baby,
          nickname: nickname || this.baby.nickname || '宝宝',
          avatar_url: String(d.avatar_url || ''),
          birth_date: String(d.birth_date || ''),
          birth_time: String(d.birth_time || ''),
          current_weight: String(d.current_weight || ''),
          current_height: String(d.current_height || ''),
        }
        this.dirty = true
      } catch {}
    },

    buildIncompleteDesc(missingField) {
      if (missingField === 'birth_date') return '出生日期用于计算喂奶节奏与推荐量。\n你也可以稍后再填，内容会自动保留。'
      if (missingField === 'nickname') return '给宝宝取个昵称，记录会更清晰。\n你也可以稍后再填，内容会自动保留。'
      return '你也可以稍后再填，内容会自动保留。'
    },

    handleIncompleteContinue() {
      this.incompleteSheetVisible = false
      const field = this.incompleteMissingField || 'birth_date'
      this.incompleteMissingField = ''
      this.editField(field)
    },

    handleIncompleteLater() {
      this.incompleteSheetVisible = false
      this.incompleteMissingField = ''
      this.persistDraft()
      this.goBackOrHome()
    },

    async handleDone() {
      if (this.showEditModal) {
        this.closeEditModal()
        return
      }

      // 没有任何改动：直接返回
      if (!this.dirty && this.baby?.id) {
        this.goBackOrHome()
        return
      }

      // 新建未满足关键字段：允许稍后完善（不强行卡住）
      const miss = this.getFirstMissingRequiredField()
      if (miss) {
        this.incompleteMissingField = miss
        this.incompleteSheetDesc = this.buildIncompleteDesc(miss)
        this.incompleteSheetVisible = true
        return
      }

      // 保存并返回
      const ok = await this.saveBabyInfo({ navigateAfter: true, showToast: true })
      if (!ok) return
    },

    lockBodyScroll() {
      if (typeof document === 'undefined' || !document.body) return
      document.body.style.overflow = 'hidden'
      document.body.style.position = 'fixed'
      document.body.style.width = '100%'
    },

    unlockBodyScroll() {
      if (typeof document === 'undefined' || !document.body) return
      document.body.style.overflow = ''
      document.body.style.position = ''
      document.body.style.width = ''
    },

    async openNativeBirthDate() {
      const current = this.normalizeDateToYMD(this.editValue) || this.formatDateYMD(new Date())
      const picked = await this.openNativePicker('date', current)
      if (picked) this.editValue = picked
    },

    async openNativeBirthTime() {
      const current = String(this.editValue || '').trim().slice(0, 5) || '12:00'
      const picked = await this.openNativePicker('time', current)
      if (picked) this.editValue = picked
    },

    openNativePicker(type, value) {
      // H5 only: 用真实 DOM input 调起系统选择器（uni-app 的 <input> 组件不支持 type=date/time，会退化成文本输入）
      if (typeof document === 'undefined') return Promise.resolve(null)
      return new Promise((resolve) => {
        let done = false
        let latestValue = ''
        const ua = (typeof navigator !== 'undefined' && navigator.userAgent) ? navigator.userAgent : ''
        const isMobile = /iPhone|iPad|iPod|Android|Mobi/i.test(ua)

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

        const updateLatest = () => {
          try {
            latestValue = String(input.value || '').trim()
          } catch {}
        }

        // iOS/部分 WebView：date/time 的 change 可能在滚动年月日/时分时频繁触发。
        // 为避免“只能改一个字段就自动结束”，移动端以 blur 作为完成信号；桌面端仍在 change 立即完成。
        input.addEventListener('input', updateLatest)
        input.addEventListener('change', () => {
          updateLatest()
          if (!isMobile) finish(latestValue)
        })
        // 取消/关闭时没有 change，依赖 blur 清理（iOS/微信内置浏览器表现一致）
        input.addEventListener('blur', () => setTimeout(() => finish(latestValue || null), 0), { once: true })

        document.body.appendChild(input)

        // 必须在用户手势回调内触发
        try {
          input.focus({ preventScroll: true })
        } catch {
          try { input.focus() } catch {}
        }
        try { input.click() } catch {}
      })
    },
    async loadBabyInfo() {
      try {
        const res = await api.get(`/babies/${this.baby.id}`)
        this.baby = res.baby
      } catch (error) {
        uni.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    },
    
    selectAvatar() {
      // 为了跨平台一致性与低维护成本：使用内置头像库（不做文件上传）
      if (!this.baby.id) {
        uni.showToast({
          title: '请先保存宝宝信息后再更换头像',
          icon: 'none'
        })
        return
      }

      uni.navigateTo({
        url: `/pages/avatar-select/index?target=baby&babyId=${this.baby.id}`
      })
    },

    editField(field) {
      this.editingField = field
      const fieldNames = {
        'nickname': '昵称',
        'birth_date': '出生日期',
        'birth_time': '出生时间',
        'weight': '体重',
        'height': '身高'
      }
      this.editFieldName = fieldNames[field] || field
      
      if (field === 'weight') {
        this.editValue = this.baby.current_weight
      } else if (field === 'height') {
        this.editValue = this.baby.current_height
      } else if (field === 'birth_time') {
        const t = String(this.baby.birth_time || '').trim()
        // time picker/input 期望 HH:MM（避免被秒数/空值影响）
        this.editValue = t ? t.slice(0, 5) : '12:00'
      } else if (field === 'birth_date') {
        // 如果没有出生日期，使用当前日期
        const targetDate = this.normalizeDateToYMD(this.baby.birth_date) || this.formatDateYMD(new Date())
        this.editValue = targetDate
      } else {
        this.editValue = this.baby[field]
      }
      
      this.showEditModal = true
      
      // 禁用背景滚动
      this.lockBodyScroll()
      
    },
    
    closeEditModal() {
      this.showEditModal = false
      this.editingField = ''
      this.editValue = ''
      
      // 恢复背景滚动
      this.unlockBodyScroll()
    },
    
    onEditDateChange(e) {
      // 兼容自定义元素和 uni-app 的事件格式
      const value = e.detail?.value || e.detail || e.target?.value || ''
      this.editValue = value
    },
    
    onEditTimeChange(e) {
      // 兼容自定义元素和 uni-app 的事件格式
      const value = e.detail?.value || e.detail || e.target?.value || ''
      this.editValue = value
    },
    
    async saveEdit() {
      if (this.editingField === 'weight') {
        this.baby.current_weight = this.editValue
      } else if (this.editingField === 'height') {
        this.baby.current_height = this.editValue
      } else {
        this.baby[this.editingField] = this.editValue
      }

      this.markDirty()
      this.persistDraft()

      this.closeEditModal()

      // 体验优化：新建时不强制每次确认都校验/报错；当关键字段齐全后再自动保存（创建后停留本页继续完善）。
      const missing = this.getFirstMissingRequiredField()
      if (missing) {
        // 新建流程：自动引导补齐下一个关键字段，减少“点来点去”。
        if (this.isNew && !this.baby?.id && missing !== this.editingField) {
          setTimeout(() => {
            try { this.editField(missing) } catch {}
          }, 0)
        }
        return
      }

      const willCreate = this.isNew && !this.baby?.id
      await this.saveBabyInfo({
        navigateAfter: false,
        showToast: willCreate,
        toastText: willCreate ? '已创建宝宝档案，可继续完善' : '',
      })
    },
    
    formatDateYMD(date) {
      // Date -> YYYY-MM-DD（用于后端/日期选择器）
      const d = date instanceof Date ? date : new Date(date)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },

    formatDateDisplay(dateInput) {
      // string/date -> YYYY.MM.DD（用于展示）
      const ymd = this.normalizeDateToYMD(dateInput)
      if (!ymd) return ''
      return ymd.replace(/-/g, '.')
    },

    normalizeDateToYMD(dateInput) {
      if (!dateInput) return ''
      if (dateInput instanceof Date) return this.formatDateYMD(dateInput)

      const s = String(dateInput)
      // RFC3339 / ISO：直接取前 10 位即可（YYYY-MM-DD）
      if (s.length >= 10 && /^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10)
      // 兼容：YYYY.MM.DD
      if (/^\d{4}\.\d{2}\.\d{2}$/.test(s)) return s.replace(/\./g, '-')
      // 兜底：尝试 Date 解析后再格式化
      const d = this.parseDateString(s)
      if (isNaN(d.getTime())) return ''
      return this.formatDateYMD(d)
    },

    parseDateString(dateStr) {
      // 避免 Safari 对 "YYYY-MM-DD" / "YYYY-MM-DD HH:mm:ss" 的差异解析
      const s = String(dateStr || '').trim()
      const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
      if (m) {
        const y = Number(m[1])
        const mo = Number(m[2])
        const d = Number(m[3])
        return new Date(y, mo - 1, d)
      }
      const dot = s.match(/^(\d{4})\.(\d{2})\.(\d{2})$/)
      if (dot) {
        const y = Number(dot[1])
        const mo = Number(dot[2])
        const d = Number(dot[3])
        return new Date(y, mo - 1, d)
      }
      return new Date(s)
    },

    formatNumberDisplay(v) {
      if (v === null || v === undefined || v === '' || Number(v) <= 0) return '未填写'
      return String(v)
    },

    formatTimeDisplay(timeInput) {
      const s = String(timeInput || '').trim()
      if (!s) return ''
      // 兼容 "HH:MM" / "HH:MM:SS"
      const m = s.match(/^(\d{2}):(\d{2})/)
      if (m) return `${m[1]}:${m[2]}`
      return s
    },
    
    getFirstMissingRequiredField() {
      const name = String(this.baby?.nickname || '').trim()
      if (!name) return 'nickname'
      const ymd = this.normalizeDateToYMD(this.baby?.birth_date)
      if (!ymd) return 'birth_date'
      return ''
    },

    async saveBabyInfo(options = {}) {
      const navigateAfter = !!options.navigateAfter
      const showSuccessToast = options.showToast !== false
      const showErrorToast = options.showErrorToast !== false
      const toastText = String(options.toastText || '').trim()

      const missing = this.getFirstMissingRequiredField()
      if (missing) {
        if (showErrorToast) {
          uni.showToast({
            title: missing === 'birth_date' ? '请选择出生日期' : '请输入昵称',
            icon: 'none'
          })
        }
        return false
      }

      const birthDateYmd = this.normalizeDateToYMD(this.baby.birth_date)
      if (!birthDateYmd) {
        if (showErrorToast) {
          uni.showToast({
            title: '出生日期格式不正确',
            icon: 'none'
          })
        }
        return false
      }

      const weightNum = (() => {
        const n = Number.parseFloat(String(this.baby.current_weight || '').trim())
        return Number.isFinite(n) && n > 0 ? n : null
      })()
      const heightNum = (() => {
        const n = Number.parseInt(String(this.baby.current_height || '').trim(), 10)
        return Number.isFinite(n) && n > 0 ? n : null
      })()
      
      if (this.saving) return false
      this.saving = true
      try {
        const created = this.isNew || !this.baby?.id
        let res
        if (created) {
          const payload = {
            nickname: this.baby.nickname,
            avatar_url: this.baby.avatar_url,
            birth_date: birthDateYmd,
            birth_time: this.baby.birth_time || '12:00',
          }
          if (weightNum !== null) payload.current_weight = weightNum
          if (heightNum !== null) payload.current_height = heightNum
          res = await api.post('/babies', payload)
        } else {
          const payload = {
            nickname: this.baby.nickname,
            avatar_url: this.baby.avatar_url,
            birth_date: birthDateYmd,
            birth_time: this.baby.birth_time,
          }
          if (weightNum !== null) payload.current_weight = weightNum
          if (heightNum !== null) payload.current_height = heightNum
          res = await api.put(`/babies/${this.baby.id}`, payload)
        }
        
        const userStore = useUserStore()
        this.baby = res.baby
        this.isNew = false
        userStore.setCurrentBaby(res.baby)

        this.dirty = false
        this.clearDraft()

        if (showSuccessToast) {
          uni.showToast({
            title: toastText || '保存成功',
            icon: 'success'
          })
        }

        if (navigateAfter) {
          setTimeout(() => {
            this.goBackOrHome()
          }, 200)
        }
        return true
      } catch (error) {
        if (showErrorToast) {
          uni.showToast({
            title: error.message || '保存失败',
            icon: 'none'
          })
        }
        return false
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style scoped>
.baby-info-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(12px + env(safe-area-inset-top, 0px)) 0 calc(92px + env(safe-area-inset-bottom, 0px)); /* 底部完成按钮占位 */
  box-sizing: border-box;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 0 18px;
}

.baby-avatar {
  width: 120px;
  height: 120px;
  border-radius: 60px;
  background: #FFD700;
  margin-bottom: 15px;
}

.nickname-label {
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
}

.nickname-value {
  font-size: 24px;
  font-weight: bold;
  color: #000;
}

.info-section {
  padding: 0 var(--nb-page-x);
}

.info-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  cursor: pointer;
  transition: background-color 0.2s;
}

.info-item:active {
  background-color: #f5f5f5;
}

.info-item.readonly {
  cursor: default;
}

.info-item.readonly:active {
  background-color: rgba(255, 255, 255, 0.92);
}

.label {
  font-size: 15px;
  color: var(--nb-muted);
  margin-bottom: 0;
}

.unit {
  color: #999;
  font-size: 12px;
}

.value-display {
  font-size: 17px;
  font-weight: 600;
  color: var(--nb-text);
}

.value-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.value-sub {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.55);
}

.page-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px var(--nb-page-x) calc(12px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid var(--nb-border);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.done-btn {
  height: 48px;
  border-radius: 24px;
  font-weight: 700;
}

.edit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  touch-action: none; /* 阻止所有触摸手势 */
  overflow: hidden; /* 防止滚动 */
}

.edit-modal-content {
  width: 90%;
  max-width: 500px;
  background: #fff;
  border-radius: 20px;
  padding: 30px;
  max-height: 80vh;
  overflow-y: auto;
  overscroll-behavior: contain; /* 防止滚动链 */
  touch-action: pan-y; /* 允许垂直滚动 */
}

.edit-modal-header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.edit-modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.close-btn {
  font-size: 36px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.edit-modal-body {
  padding: 30px 0;
}

.edit-input-mobile {
  width: 100%;
  min-height: 60px;
  border: 2px solid #e0e0e0;
  border-radius: 16px;
  padding: 0 24px;
  font-size: 20px;
  box-sizing: border-box;
  background: #fff;
  -webkit-appearance: none;
  appearance: none;
  touch-action: manipulation;
}

.edit-input-mobile:focus {
  outline: none;
  border-color: #FFD700;
}

.edit-input-mobile::placeholder {
  color: #bbb;
  font-size: 18px;
}

.picker-display-mobile {
  width: 100%;
  min-height: 60px;
  border: 2px solid #e0e0e0;
  border-radius: 16px;
  padding: 16px 24px;
  cursor: pointer;
  box-sizing: border-box;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: all 0.2s;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.picker-display-mobile:active {
  background: #f8f8f8;
  border-color: #FFD700;
  transform: scale(0.98);
}

.picker-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 6px;
}

.picker-value {
  font-size: 20px;
  color: #333;
  font-weight: 500;
}

.number-input-wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  border: 2px solid #e0e0e0;
  border-radius: 16px;
  padding: 0 24px;
  box-sizing: border-box;
  background: #fff;
  min-height: 60px;
  transition: all 0.2s;
}

.number-input-wrapper:focus-within {
  border-color: #FFD700;
}

.number-input {
  flex: 1;
  border: none;
  padding: 0;
  font-size: 20px;
  background: transparent;
  -webkit-appearance: none;
  appearance: none;
  touch-action: manipulation;
}

.number-input:focus {
  outline: none;
}

.number-input::placeholder {
  color: #bbb;
  font-size: 18px;
}

.input-unit {
  font-size: 18px;
  color: #999;
  margin-left: 12px;
  font-weight: 500;
}

.edit-modal-footer {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  margin-top: 40px;
  gap: 16px;
}

.cancel-btn, .confirm-btn {
  flex: 1;
  min-height: 60px;
  border-radius: 30px;
  font-size: 18px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

.cancel-btn {
  background: #f5f5f5;
  color: #666;
}

.cancel-btn:active {
  background: #e0e0e0;
  transform: scale(0.97);
}

.confirm-btn {
  background: #FFD700;
  color: #333;
}

.confirm-btn:active {
  background: #FFC107;
  transform: scale(0.97);
}
</style>
