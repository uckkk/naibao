<template>
  <view class="baby-info-container">
    <!-- 头像和昵称 -->
    <view class="avatar-section">
      <image 
        :src="baby.avatar_url || '/static/default-avatar.png'" 
        class="baby-avatar"
        @click="selectAvatar"
        mode="aspectFill"
      />
      <text class="nickname-label">昵称</text>
      <text class="nickname-value">{{ baby.nickname || '元宝' }}</text>
    </view>
    
    <!-- 信息字段 -->
    <view class="info-section">
      <view class="info-item" @click="editField('nickname')">
        <text class="label">昵称</text>
        <text class="value-display">{{ baby.nickname || '元宝' }}</text>
      </view>
      
      <view class="info-item" @click="editField('birth_date')">
        <text class="label">出生日期</text>
        <text class="value-display">{{ formatDateDisplay(baby.birth_date) || '未填写' }}</text>
      </view>
      
      <view class="info-item" @click="editField('birth_time')">
        <text class="label">出生时间</text>
        <text class="value-display">{{ formatTimeDisplay(baby.birth_time) || '未填写' }}</text>
      </view>

      <view class="info-item readonly">
        <text class="label">星座</text>
        <text class="value-display">{{ zodiacText || '—' }}</text>
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
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatZodiacText } from '@/utils/zodiac'

export default {
  data() {
    return {
      baby: {
        id: null,
        nickname: '',
        avatar_url: '',
        birth_date: '',
        birth_time: '',
        current_weight: '',
        current_height: ''
      },
      isNew: true,
      showEditModal: false,
      editingField: '',
      editValue: '',
      editFieldName: '',
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
      }
    }
  },

  onShow() {
    // 处理从“选择头像”等页面返回后，本页数据需要刷新
    if (this.baby.id && !this.isNew) {
      this.loadBabyInfo()
    }
  },
  
  methods: {
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
        // 取消/关闭时没有 change，依赖 blur 清理（iOS/微信内置浏览器表现一致）
        input.addEventListener('blur', () => setTimeout(() => finish(null), 0), { once: true })

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
      if (typeof document !== 'undefined' && document.body) {
        document.body.style.overflow = 'hidden'
        document.body.style.position = 'fixed'
        document.body.style.width = '100%'
      }
      
    },
    
    closeEditModal() {
      this.showEditModal = false
      this.editingField = ''
      this.editValue = ''
      
      // 恢复背景滚动
      if (typeof document !== 'undefined' && document.body) {
        document.body.style.overflow = ''
        document.body.style.position = ''
        document.body.style.width = ''
      }
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
      
      await this.saveBabyInfo()
      this.closeEditModal()
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
    
    async saveBabyInfo() {
      if (!this.baby.nickname) {
        uni.showToast({
          title: '请输入昵称',
          icon: 'none'
        })
        return
      }
      
      if (!this.baby.birth_date) {
        uni.showToast({
          title: '请选择出生日期',
          icon: 'none'
        })
        return
      }

      const birthDateYmd = this.normalizeDateToYMD(this.baby.birth_date)
      if (!birthDateYmd) {
        uni.showToast({
          title: '出生日期格式不正确',
          icon: 'none'
        })
        return
      }

      const weightNum = (() => {
        const n = Number.parseFloat(String(this.baby.current_weight || '').trim())
        return Number.isFinite(n) && n > 0 ? n : null
      })()
      const heightNum = (() => {
        const n = Number.parseInt(String(this.baby.current_height || '').trim(), 10)
        return Number.isFinite(n) && n > 0 ? n : null
      })()
      
      try {
        const created = this.isNew
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
        
        uni.showToast({
          title: '保存成功',
          icon: 'success'
        })

        // 创建宝宝后回到首页；更新则停留当前页，方便连续编辑多个字段
        if (created) {
          setTimeout(() => {
            uni.navigateBack()
          }, 500)
        }
      } catch (error) {
        uni.showToast({
          title: error.message || '保存失败',
          icon: 'none'
        })
      }
    }
  }
}
</script>

<style scoped>
.baby-info-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(12px + env(safe-area-inset-top, 0px)) 0 calc(24px + env(safe-area-inset-bottom, 0px));
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
