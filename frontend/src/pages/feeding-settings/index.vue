<template>
  <view class="settings-container">
    <NbNetworkBanner />
    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能设置喂奶间隔与提醒"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbLoadingSwitch v-else :loading="pageLoading">
      <template #skeleton>
        <view class="section">
          <view class="section-header">
            <NbSkeleton :w="52" :h="16" :radius="8" />
            <view style="margin-top:10px;">
              <NbSkeleton :w="160" :h="12" :radius="6" />
            </view>
          </view>
          <view class="number-picker-container">
            <NbSkeleton :w="'100%'" :h="56" :radius="16" />
          </view>
        </view>

        <view class="section">
          <view class="section-header">
            <NbSkeleton :w="52" :h="16" :radius="8" />
            <view style="margin-top:10px;">
              <NbSkeleton :w="160" :h="12" :radius="6" />
            </view>
          </view>
          <view class="number-picker-container">
            <NbSkeleton :w="'100%'" :h="56" :radius="16" />
          </view>
        </view>

        <view class="section">
          <view class="section-header">
            <NbSkeleton :w="96" :h="16" :radius="8" />
          </view>
          <view class="next-time-display">
            <NbSkeleton :w="120" :h="26" :radius="13" />
            <view style="margin-top:12px;display:flex;justify-content:center;">
              <NbSkeleton :w="260" :h="12" :radius="6" />
            </view>
          </view>
        </view>

        <view class="section">
          <view class="toggle-section">
            <NbSkeleton :w="50" :h="30" :radius="15" />
            <NbSkeleton :w="72" :h="14" :radius="7" />
          </view>
        </view>

        <view class="footer">
          <NbSkeleton :w="'100%'" :h="50" :radius="25" />
        </view>
      </template>

      <NbState
        v-if="errorText"
        type="error"
        title="加载失败"
        :desc="errorText"
        actionText="重试"
        @action="init"
      />

      <template v-else>
    <!-- 白天设置 -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">白天</text>
        <text class="section-desc">早上6点-晚上18点</text>
      </view>
      <view class="number-picker-container">
        <scroll-view class="number-picker" scroll-x>
          <view 
            v-for="num in dayNumbers" 
            :key="num"
            :class="['number-item', { active: num === settings.dayInterval }]"
            @click="selectDayInterval(num)"
          >
            <text>{{ num }}</text>
          </view>
        </scroll-view>
      </view>
    </view>

    <!-- 晚上设置 -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">晚上</text>
        <text class="section-desc">晚上18点-早上06点</text>
      </view>
      <view class="number-picker-container">
        <scroll-view class="number-picker" scroll-x>
          <view 
            v-for="num in nightNumbers" 
            :key="num"
            :class="['number-item', { active: num === settings.nightInterval }]"
            @click="selectNightInterval(num)"
          >
            <text>{{ num }}</text>
          </view>
        </scroll-view>
      </view>
    </view>

    <!-- 下次喂奶时间 -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">下次喂奶时间</text>
      </view>
      <view class="next-time-display">
        <text class="time-value">{{ nextFeedingTime }}</text>
        <text class="time-desc">应用内提醒：提前{{ settings.advanceMinutes }}分钟提示（需保持应用打开）</text>
      </view>
    </view>

    <!-- 提醒开关 -->
    <view class="section" id="nb-focus-reminder">
      <view class="toggle-section">
        <view class="toggle-switch" :class="{ active: settings.reminderEnabled }" @click="toggleReminder">
          <view class="toggle-circle"></view>
        </view>
        <text class="toggle-label">应用内提醒</text>
      </view>
    </view>

    <!-- 系统通知权限（H5 Web Notification） -->
    <view class="section" id="nb-focus-notify">
      <view class="section-header">
        <text class="section-title">系统通知</text>
        <text class="section-desc">{{ systemNotifyStatusText }}</text>
      </view>

      <view class="toggle-section">
        <view
          class="toggle-switch"
          :class="{ active: systemNotifyEffective }"
          :style="{ opacity: systemNotifySupported ? 1 : 0.5 }"
          @click="toggleSystemNotify"
        >
          <view class="toggle-circle"></view>
        </view>
        <text class="toggle-label">允许通知</text>

        <button
          class="mini-btn"
          :class="{ disabled: !systemNotifyEffective }"
          @click="sendTestNotify(false)"
        >
          测试
        </button>
      </view>

      <text v-if="systemNotifyHintText" class="picker-hint">{{ systemNotifyHintText }}</text>
    </view>

    <!-- 提前提醒时长 -->
    <view class="section" v-if="settings.reminderEnabled">
      <view class="section-header">
        <text class="section-title">提前提醒时长</text>
      </view>
      <view class="number-picker-container">
        <scroll-view class="number-picker" scroll-x>
          <view 
            v-for="num in advanceNumbers" 
            :key="num"
            :class="['number-item', { active: num === settings.advanceMinutes }]"
            @click="selectAdvanceMinutes(num)"
          >
            <text>{{ num }}</text>
          </view>
        </scroll-view>
      </view>
      <text class="picker-hint">拖动数字设置提前提醒时长</text>
    </view>

    <!-- 底部保存按钮 -->
    <view class="footer">
      <button class="save-btn" :disabled="!dirty || saving" @click="saveSettings">
        {{ saving ? '保存中...' : (dirty ? '保存设置' : '已保存') }}
      </button>
    </view>
    </template>
    </NbLoadingSwitch>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadingSwitch from '@/components/NbLoadingSwitch.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import {
  getNotificationPermission,
  getSystemNotifyEnabled,
  isNotificationSupported,
  isStandalonePwa,
  requestNotificationPermission,
  sendSystemNotify,
  setSystemNotifyEnabled,
} from '@/utils/system_notify'

export default {
  components: { NbState, NbNetworkBanner, NbLoadingSwitch, NbSkeleton },
  data() {
    return {
      babyId: null,
      focusTarget: '',
      focusDone: false,
      pageLoading: false,
      errorText: '',
      lastInitBabyId: null,
      settings: {
        dayInterval: 3,
        nightInterval: 5,
        reminderEnabled: true,
        advanceMinutes: 15,
        dayStartHour: 6,
        dayEndHour: 18
      },
      nextFeedingTime: '21:50:00',
      nextFeedingTimestampMs: null,
      dayNumbers: [1, 2, 3, 4, 5],
      nightNumbers: [3, 4, 5, 6, 7],
      advanceNumbers: [5, 10, 15, 20, 30],
      dirty: false,
      saving: false,

      // 系统通知（H5）开关：本机偏好，不同步到后端
      systemNotifySupported: false,
      systemNotifyPermission: 'unsupported', // granted | denied | default | unsupported
      systemNotifyEnabled: false,
    }
  },

  computed: {
    systemNotifyEffective() {
      return !!(this.systemNotifySupported && this.systemNotifyEnabled && this.systemNotifyPermission === 'granted')
    },

    systemNotifyStatusText() {
      if (!this.systemNotifySupported) return '当前环境不支持'
      const p = String(this.systemNotifyPermission || 'default')
      if (p === 'granted') return '已允许'
      if (p === 'denied') return '已拒绝'
      return '未授权'
    },

    systemNotifyHintText() {
      if (!this.systemNotifySupported) return '系统通知依赖浏览器能力：当前环境不支持'

      if (String(this.systemNotifyPermission || 'default') === 'denied') {
        return '你已拒绝通知权限；需到浏览器/系统的站点设置中手动开启'
      }

      // iOS：更常见的失败原因是未安装到主屏
      if (this.isIOSPlatform() && !isStandalonePwa()) {
        return 'iPhone：建议先“添加到主屏幕”再开启系统通知（Safari 内可能无法接收）'
      }

      if (!this.systemNotifyEffective) return '开启后，退到后台时会尽量用系统通知提醒（不同机型/浏览器可能有差异）'
      return ''
    },
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
    this.focusTarget = String(options.focus || '').trim()
  },

  onShow() {
    // 从“建档/选择宝宝”等页面返回时，刷新 babyId 并重载
    if (!this.babyId) {
      const userStore = useUserStore()
      if (userStore.currentBaby?.id) {
        this.babyId = userStore.currentBaby.id
      }
    }
    if (this.babyId && String(this.lastInitBabyId) !== String(this.babyId)) {
      this.init()
    }

    // 通知权限可能在系统设置中被更改：每次回到页面刷新一下状态
    this.refreshSystemNotifyState()
  },
  
  methods: {
    onNbRetry() {
      this.init()
    },

    async init() {
      if (!this.babyId) return
      this.pageLoading = true
      this.errorText = ''
      try {
        await this.loadSettings()
        await this.loadNextFeedingTime()
        this.lastInitBabyId = this.babyId
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
        this.refreshSystemNotifyState()
        this.maybeScrollToFocus()
      }
    },

    maybeScrollToFocus() {
      const target = String(this.focusTarget || '').trim()
      if (!target || this.focusDone) return
      if (this.pageLoading || this.errorText) return
      this.focusDone = true
      const selector = target === 'notify' ? '#nb-focus-notify' : target === 'reminder' ? '#nb-focus-reminder' : ''
      if (!selector) return
      this.$nextTick(() => {
        try {
          uni.pageScrollTo({ selector, duration: 220 })
        } catch {}
      })
    },

    async loadSettings() {
      try {
        const res = await api.get(`/babies/${this.babyId}/settings`)
        if (res.settings) {
          // 后端为 snake_case；页面内部统一用 camelCase，避免模板/逻辑大改
          this.settings = {
            dayInterval: res.settings.day_interval ?? 3,
            nightInterval: res.settings.night_interval ?? 5,
            reminderEnabled: res.settings.reminder_enabled ?? true,
            advanceMinutes: res.settings.advance_minutes ?? 15,
            dayStartHour: res.settings.day_start_hour ?? 6,
            dayEndHour: res.settings.day_end_hour ?? 18
          }
          this.dirty = false
        }
      } catch (error) {
        console.error('加载设置失败', error)
        throw error
      }
    },
    
    async loadNextFeedingTime() {
      try {
        const res = await api.get(`/babies/${this.babyId}/next-feeding-time`)
        if (res.next_feeding_timestamp) {
          // 使用 timestamp（秒）避免 Safari 解析 "YYYY-MM-DD HH:mm:ss" 兼容问题
          this.nextFeedingTimestampMs = Number(res.next_feeding_timestamp) * 1000
          const time = new Date(this.nextFeedingTimestampMs)
          this.nextFeedingTime = `${String(time.getHours()).padStart(2, '0')}:${String(time.getMinutes()).padStart(2, '0')}:${String(time.getSeconds()).padStart(2, '0')}`
        } else if (res.next_feeding_time) {
          // 兜底：将空格替换为 T 以提升兼容性
          const time = new Date(String(res.next_feeding_time).replace(' ', 'T'))
          this.nextFeedingTime = `${String(time.getHours()).padStart(2, '0')}:${String(time.getMinutes()).padStart(2, '0')}:${String(time.getSeconds()).padStart(2, '0')}`
        }
      } catch (error) {
        console.error('加载下次喂奶时间失败', error)
        throw error
      }
    },

    markDirty() {
      this.dirty = true
    },
    
    selectDayInterval(num) {
      this.settings.dayInterval = num
      this.markDirty()
    },
    
    selectNightInterval(num) {
      this.settings.nightInterval = num
      this.markDirty()
    },
    
    selectAdvanceMinutes(num) {
      this.settings.advanceMinutes = num
      this.markDirty()
    },
    
    toggleReminder() {
      this.settings.reminderEnabled = !this.settings.reminderEnabled
      this.markDirty()
    },

    isIOSPlatform() {
      try {
        const sys = uni.getSystemInfoSync()
        const p = String(sys?.platform || sys?.osName || '').toLowerCase()
        return p.includes('ios') || p.includes('iphone') || p.includes('ipad')
      } catch {
        return false
      }
    },

    refreshSystemNotifyState() {
      this.systemNotifySupported = isNotificationSupported()
      this.systemNotifyPermission = getNotificationPermission()
      this.systemNotifyEnabled = getSystemNotifyEnabled()

      // 权限被撤销时：避免 UI 显示为“已开启”造成误导
      if (this.systemNotifyPermission !== 'granted' && this.systemNotifyEnabled) {
        this.systemNotifyEnabled = false
      }
    },

    async toggleSystemNotify() {
      if (!this.systemNotifySupported) {
        uni.showToast({ title: '当前环境不支持系统通知', icon: 'none' })
        return
      }

      // 关闭：只改本机开关，不影响“应用内提醒”
      if (this.systemNotifyEnabled) {
        this.systemNotifyEnabled = false
        setSystemNotifyEnabled(false)
        uni.showToast({ title: '已关闭系统通知', icon: 'none' })
        return
      }

      // 开启：请求权限（需用户手势触发）
      const perm = await requestNotificationPermission()
      this.systemNotifyPermission = perm
      if (perm !== 'granted') {
        setSystemNotifyEnabled(false)
        this.systemNotifyEnabled = false
        uni.showToast({
          title: perm === 'denied' ? '你拒绝了通知权限' : '未开启通知权限',
          icon: 'none',
        })
        return
      }

      setSystemNotifyEnabled(true)
      this.systemNotifyEnabled = true
      uni.showToast({ title: '已开启系统通知', icon: 'none' })

      // 轻量确认：发一条“测试通知”，让用户知道确实拿到了系统权限
      this.sendTestNotify(true)
    },

    sendTestNotify(silent) {
      const isSilent = typeof silent === 'boolean' ? silent : false
      if (!this.systemNotifyEffective) {
        if (!isSilent) uni.showToast({ title: '请先允许系统通知', icon: 'none' })
        return
      }
      const t = '奶宝提醒已开启'
      const body = '下次喂奶到点/提前会尽量用系统通知提示你'
      const n = sendSystemNotify(t, {
        body,
        icon: '/static/naiping1.svg',
        tag: 'naibao-test',
      })
      if (!n && !isSilent) {
        uni.showToast({ title: '发送失败（可能被系统拦截）', icon: 'none' })
        return
      }
      if (!isSilent) uni.showToast({ title: '已发送测试通知', icon: 'none' })
    },

    async saveSettings() {
      if (!this.babyId || this.saving) return
      this.saving = true
      try {
        const res = await api.put(`/babies/${this.babyId}/settings`, {
          day_interval: this.settings.dayInterval,
          night_interval: this.settings.nightInterval,
          reminder_enabled: this.settings.reminderEnabled,
          advance_minutes: this.settings.advanceMinutes,
          day_start_hour: this.settings.dayStartHour,
          day_end_hour: this.settings.dayEndHour
        })

        if (res.settings) {
          this.settings = {
            dayInterval: res.settings.day_interval ?? this.settings.dayInterval,
            nightInterval: res.settings.night_interval ?? this.settings.nightInterval,
            reminderEnabled: res.settings.reminder_enabled ?? this.settings.reminderEnabled,
            advanceMinutes: res.settings.advance_minutes ?? this.settings.advanceMinutes,
            dayStartHour: res.settings.day_start_hour ?? this.settings.dayStartHour,
            dayEndHour: res.settings.day_end_hour ?? this.settings.dayEndHour
          }
        }
        
        uni.showToast({
          title: '保存成功',
          icon: 'success'
        })

        this.dirty = false
        await this.loadNextFeedingTime()
      } catch (error) {
        uni.showToast({
          title: error.message || '保存失败',
          icon: 'none'
        })
      } finally {
        this.saving = false
      }
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },
  }
}
</script>

<style scoped>
.settings-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + env(safe-area-inset-top, 0px)) var(--nb-page-x)
    calc(110px + env(safe-area-inset-bottom, 0px)); /* 给固定底部按钮留出空间 */
  box-sizing: border-box;
}

.section {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 18px 16px;
  margin-bottom: 14px;
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--nb-text);
  display: block;
  margin-bottom: 8px;
}

.section-desc {
  font-size: 14px;
  color: var(--nb-muted);
}

.number-picker-container {
  margin: 15px 0;
}

.number-picker {
  white-space: nowrap;
  height: 56px;
}

.number-item {
  display: inline-block;
  min-width: 52px;
  height: 52px;
  line-height: 52px;
  text-align: center;
  margin-right: 10px;
  color: var(--nb-muted);
  font-size: 18px;
  border-radius: 16px;
  background: rgba(27, 26, 23, 0.06);
}

.number-item.active {
  color: var(--nb-text);
  font-weight: bold;
  background: rgba(247, 201, 72, 0.22);
}

.next-time-display {
  text-align: center;
  padding: 20px 0;
}

.time-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--nb-text);
  display: block;
  margin-bottom: 10px;
}

.time-desc {
  font-size: 14px;
  color: var(--nb-muted);
}

.toggle-section {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 15px;
}

.toggle-switch {
  width: 50px;
  height: 30px;
  background: rgba(27, 26, 23, 0.18);
  border-radius: 15px;
  position: relative;
  cursor: pointer;
  transition: background-color 0.3s;
}

.toggle-switch.active {
  background: var(--nb-accent);
}

.toggle-circle {
  width: 26px;
  height: 26px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
}

.toggle-switch.active .toggle-circle {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 16px;
  color: var(--nb-text);
}

.picker-hint {
  font-size: 14px;
  color: var(--nb-muted);
  text-align: center;
  margin-top: 15px;
  display: block;
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px var(--nb-page-x);
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid var(--nb-border);
}

.save-btn {
  width: 100%;
  height: 48px;
  border-radius: 24px;
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
  font-size: 16px;
  font-weight: 600;
  border: none;
}

.save-btn[disabled] {
  background: #f0f0f0;
  color: #999;
}

.mini-btn {
  margin-left: auto;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(27, 26, 23, 0.04);
  color: rgba(27, 26, 23, 0.86);
  font-size: 13px;
  font-weight: 800;
  line-height: 34px;
}

.mini-btn[disabled] {
  opacity: 0.4;
}

.mini-btn.disabled {
  opacity: 0.45;
}
</style>
