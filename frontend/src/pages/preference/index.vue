<template>
  <view class="pref-page">
    <NbNetworkBanner />
    <NbState
      v-if="!isLoggedIn"
      type="info"
      title="请先登录"
      desc="登录后才能保存你的投喂偏好"
      actionText="去登录"
      @action="goLogin"
    />

    <NbState
      v-else-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="先创建宝宝，才能设置投喂偏好"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbLoadable v-else :loading="pageLoading" :errorText="errorText" @retry="init">
      <template #skeleton>
        <view class="group">
          <view class="group-head">
            <NbSkeleton :w="92" :h="14" :radius="7" />
            <NbSkeleton :w="64" :h="16" :radius="8" />
          </view>
          <view style="margin-top:10px;">
            <NbSkeleton :w="160" :h="12" :radius="6" />
          </view>

          <view class="segments">
            <view v-for="i in 5" :key="i" class="seg">
              <NbSkeleton :w="'100%'" :h="50" :radius="18" />
            </view>
          </view>

          <view class="hint">
            <NbSkeletonText :lines="2" :gap="6" />
          </view>
        </view>

        <view class="group">
          <view class="cells">
            <view class="cell">
              <NbSkeleton :w="70" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="52" :h="12" :radius="6" />
              </view>
            </view>
            <view class="cell">
              <NbSkeleton :w="70" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>

        <view class="footer">
          <NbSkeleton :w="'100%'" :h="48" :radius="24" />
        </view>
      </template>

      <view class="group">
        <view class="group-head">
          <text class="group-title">投喂默认量</text>
          <text class="group-value">{{ previewAmount }}ml</text>
        </view>
        <text class="group-desc">基于当前推荐 {{ baseRecommended }}ml</text>

        <view class="segments" role="tablist" aria-label="投喂偏好">
          <view
            v-for="opt in deltaOptions"
            :key="opt.delta"
            class="seg"
            :class="{ active: opt.delta === delta }"
            role="tab"
            @click="selectDelta(opt.delta)"
          >
            <text class="seg-text">{{ opt.label }}</text>
            <text class="seg-sub">{{ opt.sub }}</text>
          </view>
        </view>

        <view class="hint">
          <text class="hint-text">你也可以继续直接点“投喂”，系统会根据你的记录自动学习。</text>
        </view>
      </view>

      <view class="group">
        <view class="cells">
          <view class="cell">
            <text class="cell-title">当前偏好</text>
            <view class="cell-right">
              <text class="cell-value">{{ deltaLabel }}</text>
            </view>
          </view>

          <view class="cell tappable" @click="resetDelta">
            <text class="cell-title">恢复标准</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <view class="footer">
        <button class="nb-primary-btn save-btn" :disabled="!dirty || saving" @click="save">
          {{ saving ? '保存中...' : (dirty ? '保存' : '已保存') }}
        </button>
      </view>
    </NbLoadable>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbSkeletonText from '@/components/NbSkeletonText.vue'

function clampInt(n, min, max) {
  const v = Number.parseInt(String(n ?? '').trim(), 10)
  if (!Number.isFinite(v)) return min
  return Math.max(min, Math.min(max, v))
}

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton, NbSkeletonText },
  data() {
    return {
      babyId: null,
      pageLoading: false,
      errorText: '',
      saving: false,
      dirty: false,

      baseRecommended: 150,
      delta: 0,

      deltaOptions: [
        { delta: -20, label: '少一点', sub: '-20ml' },
        { delta: -10, label: '偏少', sub: '-10ml' },
        { delta: 0, label: '标准', sub: '0' },
        { delta: 10, label: '偏多', sub: '+10ml' },
        { delta: 20, label: '多一点', sub: '+20ml' },
      ],
    }
  },

  computed: {
    isLoggedIn() {
      const userStore = useUserStore()
      return !!userStore.token
    },
    deltaLabel() {
      const d = Number(this.delta || 0)
      if (!Number.isFinite(d) || d === 0) return '标准'
      return d > 0 ? `+${d}ml` : `${d}ml`
    },
    previewAmount() {
      const base = Number(this.baseRecommended || 0)
      const d = Number(this.delta || 0)
      const v = (Number.isFinite(base) ? base : 0) + (Number.isFinite(d) ? d : 0)
      return clampInt(v, 10, 300)
    },
  },

  onLoad(options) {
    const userStore = useUserStore()
    this.babyId = options?.babyId || userStore.currentBaby?.id || null
  },

  onShow() {
    // 多宝宝：默认全局跟随 currentBaby
    const userStore = useUserStore()
    if (userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
    this.init()
  },

  methods: {
    onNbRetry() {
      this.init()
    },

    goLogin() {
      uni.reLaunch({ url: '/pages/login/index' })
    },
    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },

    async init() {
      if (!this.isLoggedIn || !this.babyId) return
      this.pageLoading = true
      this.errorText = ''
      try {
        // 推荐量用于“偏好预览”；偏好用于默认选中。
        const [prefRes, statsRes] = await Promise.all([
          api.get(`/babies/${this.babyId}/preferences`, {}, { silent: true }),
          api.get('/feedings/stats', { baby_id: this.babyId }, { silent: true }),
        ])

        const pref = prefRes?.preference || {}
        const statsReco = statsRes?.recommended || {}
        const base = Number(statsReco.recommended || 0)
        if (Number.isFinite(base) && base > 0) this.baseRecommended = Math.round(base)

        const delta = Number(pref.adjustment_pattern || 0)
        if (Number.isFinite(delta)) this.delta = clampInt(delta, -120, 120)
        this.dirty = false
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    selectDelta(v) {
      const next = clampInt(v, -120, 120)
      if (next === this.delta) return
      this.delta = next
      this.dirty = true
    },

    resetDelta() {
      if (this.delta === 0) return
      this.delta = 0
      this.dirty = true
    },

    async save() {
      if (!this.babyId || this.saving || !this.dirty) return
      this.saving = true
      try {
        await api.put(`/babies/${this.babyId}/preferences`, { adjustment_pattern: this.delta })
        uni.showToast({ title: '已保存', icon: 'success' })
        this.dirty = false
      } catch (e) {
        uni.showToast({ title: e?.message || '保存失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },
  },
}
</script>

<style scoped>
.pref-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(28px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.group {
  background: var(--nb-card-bg);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: var(--nb-shadow-card);
  margin-bottom: 12px;
  padding: 14px;
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
  padding: 12px 14px;
  border-top: 1px solid var(--nb-line);
  gap: 10px;
}

.cell:first-child {
  border-top: none;
}

.tappable:active {
  background: var(--nb-fill-2);
}

.cell-title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 900;
  color: var(--nb-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.cell-value {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.56);
  font-weight: 800;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chev {
  font-size: 18px;
  color: rgba(var(--nb-ink-rgb), 0.38);
  font-weight: 900;
}

.group-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.group-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
}

.group-value {
  font-size: 18px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.92);
}

.group-desc {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--nb-muted-2);
}

.segments {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.seg {
  padding: 10px 6px;
  border-radius: 14px;
  border: 1px solid var(--nb-border);
  background: rgba(var(--nb-ink-rgb), 0.04);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  user-select: none;
}

.seg.active {
  background: rgba(247, 201, 72, 0.22);
  border-color: rgba(247, 201, 72, 0.45);
}

.seg:active {
  transform: scale(0.99);
}

.seg-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.88);
  white-space: nowrap;
}

.seg-sub {
  font-size: 11px;
  color: rgba(var(--nb-ink-rgb), 0.54);
  font-weight: 800;
  white-space: nowrap;
}

.hint {
  margin-top: 12px;
  border-radius: 14px;
  border: 1px solid var(--nb-line);
  background: rgba(255, 255, 255, 0.70);
  padding: 10px 12px;
}

.hint-text {
  font-size: 12px;
  color: var(--nb-muted);
  line-height: 1.6;
}

.footer {
  margin-top: 4px;
}

.save-btn {
  height: 48px;
  border-radius: 24px;
}
</style>
