<template>
  <view class="weaning-page">
    <NbNetworkBanner />

    <NbState
      v-if="!isLoggedIn"
      type="info"
      title="请先登录"
      desc="登录后才能同步转奶期与喂养数据"
      actionText="去登录"
      @action="goLogin"
    />

    <NbState
      v-else-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能开启转奶期"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbLoadable
      v-else
      :loading="pageLoading"
      :errorText="errorText"
      :empty="!plan"
      emptyTitle="未开启转奶期"
      emptyDesc="更换奶粉后，可选择开启 7 天转奶期（交替喂次，不混合）"
      emptyActionText="去更换奶粉"
      @retry="init"
      @emptyAction="goFormula"
    >
      <template #skeleton>
        <view class="group">
          <view class="summary-head">
            <NbSkeleton :w="72" :h="16" :radius="8" />
            <NbSkeleton :w="64" :h="22" :radius="11" />
          </view>
          <view style="margin-top:10px;">
            <NbSkeleton :w="140" :h="34" :radius="14" />
          </view>
          <view style="margin-top:10px;">
            <NbSkeleton :w="240" :h="12" :radius="6" />
          </view>
        </view>

        <view class="group">
          <view class="cells">
            <view v-for="i in 4" :key="i" class="cell">
              <NbSkeleton :w="72" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="120" :h="12" :radius="6" />
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>
      </template>

          <view class="group">
            <view class="summary-head">
              <text class="summary-title">转奶期</text>
              <view class="status-pill" :class="statusPillClass">
                <text class="status-pill-text">{{ statusText }}</text>
              </view>
            </view>

            <text class="summary-big">{{ dayProgressText }}</text>
            <text class="summary-sub">{{ summarySubText }}</text>
          </view>

          <view class="group">
            <view class="cells">
              <view class="cell">
                <text class="cell-title">旧奶粉</text>
                <view class="cell-right">
                  <text class="cell-value">{{ oldBrandName }}</text>
                </view>
              </view>
              <view class="cell">
                <text class="cell-title">新奶粉</text>
                <view class="cell-right">
                  <text class="cell-value">{{ newBrandName }}</text>
                </view>
              </view>
              <view class="cell">
                <text class="cell-title">模式</text>
                <view class="cell-right">
                  <text class="cell-value">交替喂次（不混合）</text>
                </view>
              </view>
              <view class="cell">
                <text class="cell-title">下次建议</text>
                <view class="cell-right">
                  <text class="cell-value" :class="{ muted: !nextSideLabel }">{{ nextSideLabel || '—' }}</text>
                </view>
              </view>
            </view>

            <view class="group-foot">
              <text class="group-foot-text">提示：如宝宝出现明显不适，请暂停并咨询医生。</text>
            </view>
          </view>

          <view class="group">
            <view class="cells">
              <view v-if="canEdit" class="cell tappable" @click="togglePause">
                <text class="cell-title">{{ plan.status === 'paused' ? '继续转奶' : '暂停转奶' }}</text>
                <text class="chev">›</text>
              </view>

              <view v-if="canEdit" class="cell tappable danger" @click="askEndPlan">
                <text class="cell-title danger-text">结束转奶期</text>
                <text class="chev danger-text">›</text>
              </view>

              <view v-if="!canEdit" class="cell">
                <text class="cell-title">仅管理员可修改</text>
                <view class="cell-right">
                  <text class="cell-value muted">当前为成员</text>
                </view>
              </view>
            </view>
          </view>
    </NbLoadable>

    <NbConfirmSheet
      :visible="confirmVisible"
      :title="confirmTitle"
      :desc="confirmDesc"
      :confirmText="confirmConfirmText"
      :cancelText="confirmCancelText"
      :confirmVariant="confirmVariant"
      :loading="confirmLoading"
      @confirm="handleConfirm"
      @cancel="closeConfirm"
    />
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'

function parseMs(v) {
  if (!v) return 0
  const d = new Date(String(v))
  const ms = d.getTime()
  return Number.isFinite(ms) ? ms : 0
}

function computeNextSide(plan, feedings) {
  if (!plan || !plan.start_at) return ''
  const oldId = Number(plan.old_brand_id || 0)
  const newId = Number(plan.new_brand_id || 0)
  if (!oldId || !newId) return ''

  const startMs = parseMs(plan.start_at)
  if (!startMs) return ''
  const list = Array.isArray(feedings) ? feedings : []

  // Find latest feeding after start that has a recognizable brand_id (old/new).
  let last = null
  for (const f of list) {
    const t = parseMs(f?.feeding_time)
    if (!t || t < startMs) continue
    const bid = Number(f?.formula_brand_id || 0)
    if (bid !== oldId && bid !== newId) continue
    last = { bid }
    break
  }

  if (!last) return 'old'
  return last.bid === oldId ? 'new' : 'old'
}

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton, NbConfirmSheet },
  data() {
    return {
      babyId: null,
      baby: null,
      meId: null,
      myRole: '',

      plan: null,
      nextSide: '',

      pageLoading: false,
      errorText: '',

      confirmVisible: false,
      confirmTitle: '',
      confirmDesc: '',
      confirmConfirmText: '确定',
      confirmCancelText: '取消',
      confirmVariant: 'primary',
      confirmLoading: false,
      confirmAction: '',
    }
  },

  computed: {
    isLoggedIn() {
      const userStore = useUserStore()
      return !!userStore.token
    },
    canEdit() {
      if (this.myRole) return this.myRole === 'admin'
      return String(this.baby?.user_id || '') === String(this.meId || '')
    },
    durationDays() {
      const d = Number(this.plan?.duration_days || 0)
      return Number.isFinite(d) && d > 0 ? d : 7
    },
    startAtMs() {
      return parseMs(this.plan?.start_at)
    },
    endAtMs() {
      const s = this.startAtMs
      const d = this.durationDays
      if (!s || !d) return 0
      return s + d * 24 * 60 * 60 * 1000
    },
    isCompleted() {
      const end = this.endAtMs
      if (!end) return false
      return Date.now() >= end
    },
    statusText() {
      if (!this.plan) return ''
      if (this.isCompleted) return '已完成'
      return this.plan.status === 'paused' ? '已暂停' : '进行中'
    },
    statusPillClass() {
      if (!this.plan) return ''
      if (this.isCompleted) return 'done'
      return this.plan.status === 'paused' ? 'paused' : 'active'
    },
    dayIndex() {
      const s = this.startAtMs
      if (!s) return 0
      const diff = Math.max(0, Date.now() - s)
      const day = Math.floor(diff / (24 * 60 * 60 * 1000)) + 1
      return Math.min(this.durationDays, Math.max(1, day))
    },
    dayProgressText() {
      if (!this.plan) return ''
      return `第 ${this.dayIndex}/${this.durationDays} 天`
    },
    summarySubText() {
      if (!this.plan) return ''
      const s = this.formatClockText(this.startAtMs)
      const e = this.formatClockText(this.endAtMs)
      const extra = this.isCompleted ? '建议切换为全新奶粉喂养' : '每次投喂会自动切换旧/新'
      if (s && e) return `开始 ${s} · 预计结束 ${e} · ${extra}`
      return extra
    },
    oldBrandName() {
      return this.plan?.old_brand?.name_cn || this.plan?.old_brand?.name_en || '旧奶粉'
    },
    newBrandName() {
      return this.plan?.new_brand?.name_cn || this.plan?.new_brand?.name_en || '新奶粉'
    },
    nextSideLabel() {
      if (!this.plan) return ''
      if (this.plan.status === 'paused') return '已暂停'
      if (this.isCompleted) return '建议：新奶粉'
      if (this.nextSide === 'old') return '旧奶粉'
      if (this.nextSide === 'new') return '新奶粉'
      return ''
    },
  },

  onLoad(options) {
    const userStore = useUserStore()
    this.meId = userStore.user?.id || null
    if (options?.babyId) this.babyId = options.babyId
    if (!this.babyId && userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
  },

  onShow() {
    const userStore = useUserStore()
    // 多宝宝：默认全局跟随 currentBaby
    if (userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
    // 从奶粉页返回时刷新，确保计划状态及时更新
    this.init()
  },

  methods: {
    onNbRetry() {
      this.init()
    },

    async init() {
      if (!this.isLoggedIn) return
      if (!this.babyId) return

      this.pageLoading = true
      this.errorText = ''
      try {
        await Promise.all([this.loadBaby(), this.loadMyRole()])
        await this.loadPlan()
        await this.loadNextSide()
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    async loadBaby() {
      if (!this.babyId) return
      const userStore = useUserStore()
      if (userStore.currentBaby?.id && String(userStore.currentBaby.id) === String(this.babyId)) {
        this.baby = userStore.currentBaby
        return
      }
      const res = await api.get(`/babies/${this.babyId}`)
      this.baby = res?.baby || null
    },

    async loadMyRole() {
      if (!this.babyId) return
      try {
        const res = await api.get(`/babies/${this.babyId}/family-members`)
        const members = Array.isArray(res.members) ? res.members : []
        const me = members.find((m) => String(m.user_id) === String(this.meId))
        this.myRole = me?.role || ''
      } catch {
        this.myRole = ''
      }
    },

    async loadPlan() {
      if (!this.babyId) return
      try {
        const res = await api.get(`/babies/${this.babyId}/weaning-plan`, {}, { silent: true })
        this.plan = res?.plan || null
      } catch {
        this.plan = null
      }
    },

    async loadNextSide() {
      if (!this.plan || !this.babyId) {
        this.nextSide = ''
        return
      }
      try {
        const res = await api.get('/feedings', { baby_id: this.babyId }, { silent: true })
        const list = Array.isArray(res.feedings) ? res.feedings : []
        this.nextSide = computeNextSide(this.plan, list)
      } catch {
        this.nextSide = ''
      }
    },

    async togglePause() {
      if (!this.plan || !this.canEdit || this.confirmLoading) return
      const action = this.plan.status === 'paused' ? 'resume' : 'pause'
      this.confirmLoading = true
      try {
        const res = await api.put(`/babies/${this.babyId}/weaning-plan`, { action })
        this.plan = res?.plan || null
        await this.loadNextSide()
        uni.showToast({ title: action === 'pause' ? '已暂停' : '已继续', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
      } finally {
        this.confirmLoading = false
      }
    },

    askEndPlan() {
      if (!this.plan || !this.canEdit) return
      this.confirmVisible = true
      this.confirmTitle = '结束转奶期？'
      this.confirmDesc = '结束后首页将不再自动切换旧/新奶粉。你仍可随时重新开启。'
      this.confirmConfirmText = '结束'
      this.confirmCancelText = '取消'
      this.confirmVariant = 'danger'
      this.confirmAction = 'end'
    },

    async handleConfirm() {
      if (this.confirmAction !== 'end') return
      await this.endPlan()
    },

    closeConfirm() {
      if (this.confirmLoading) return
      this.confirmVisible = false
      this.confirmTitle = ''
      this.confirmDesc = ''
      this.confirmVariant = 'primary'
      this.confirmAction = ''
    },

    async endPlan() {
      if (!this.plan || !this.canEdit || this.confirmLoading) return
      this.confirmLoading = true
      try {
        await api.put(`/babies/${this.babyId}/weaning-plan`, { action: 'end' })
        this.plan = null
        this.nextSide = ''
        this.closeConfirm()
        uni.showToast({ title: '已结束', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e?.message || '结束失败', icon: 'none' })
      } finally {
        this.confirmLoading = false
      }
    },

    formatClockText(ms) {
      const t = Number(ms || 0)
      if (!Number.isFinite(t) || t <= 0) return ''
      const d = new Date(t)
      if (Number.isNaN(d.getTime())) return ''
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const da = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${m}-${da} ${hh}:${mm}`
    },

    goLogin() {
      uni.reLaunch({ url: '/pages/login/index' })
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },

    goFormula() {
      if (!this.babyId) return
      uni.navigateTo({ url: `/pages/formula-select/index?babyId=${this.babyId}` })
    },
  },
}
</script>

<style scoped>
.weaning-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(28px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.group {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.08);
  margin-bottom: 12px;
  padding: 14px;
}

.summary-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.summary-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
}

.status-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  border: 1px solid rgba(27, 26, 23, 0.10);
}

.status-pill.active {
  background: rgba(247, 201, 72, 0.18);
  color: rgba(27, 26, 23, 0.86);
}

.status-pill.paused {
  background: rgba(27, 26, 23, 0.06);
  color: rgba(27, 26, 23, 0.66);
}

.status-pill.done {
  background: rgba(82, 196, 26, 0.12);
  color: rgba(27, 26, 23, 0.78);
}

.status-pill-text {
  font-size: 12px;
  font-weight: 900;
}

.summary-big {
  display: block;
  margin-top: 10px;
  font-size: 28px;
  font-weight: 1000;
  color: var(--nb-text);
}

.summary-sub {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  color: rgba(27, 26, 23, 0.62);
  line-height: 1.6;
}

.cells {
  display: flex;
  flex-direction: column;
  margin: -14px;
}

.cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
  gap: 10px;
}

.cell:first-child {
  border-top: none;
}

.tappable:active {
  background: rgba(27, 26, 23, 0.03);
}

.cell-title {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.cell-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.cell-value {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
  font-weight: 800;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chev {
  font-size: 18px;
  color: rgba(27, 26, 23, 0.38);
  font-weight: 900;
}

.muted {
  color: rgba(27, 26, 23, 0.45);
}

.group-foot {
  margin-top: 10px;
}

.group-foot-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.56);
  line-height: 1.6;
}

.danger-text {
  color: var(--nb-danger);
}
</style>
