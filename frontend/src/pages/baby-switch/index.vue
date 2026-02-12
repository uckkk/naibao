<template>
  <view class="baby-switch-page">
    <NbNetworkBanner />

    <NbLoadingSwitch :loading="loading">
      <template #skeleton>
        <view class="group">
          <view class="cells">
            <view v-for="i in 3" :key="i" class="cell">
              <NbSkeletonAvatar :size="44" :radius="16" />
              <view class="cell-main">
                <NbSkeleton :w="110" :h="14" :radius="7" />
                <view style="margin-top:8px;">
                  <NbSkeleton :w="160" :h="12" :radius="6" />
                </view>
              </view>
              <view class="cell-right">
                <NbSkeleton :w="18" :h="12" :radius="6" />
              </view>
            </view>
          </view>
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

      <NbState
        v-else-if="babies.length === 0"
        type="info"
        title="还没有宝宝档案"
        desc="先创建宝宝，才能记录与计算下次喂奶"
        actionText="去建档"
        @action="addBaby"
      />

      <template v-else>
        <view class="group">
          <view class="cells">
            <view
              v-for="b in babies"
              :key="b.id"
              class="cell tappable"
              :class="{ active: isCurrent(b) }"
              @click="selectBaby(b)"
            >
              <image class="avatar" :src="b.avatar_url || '/static/default-avatar.png'" mode="aspectFill" />
              <view class="cell-main">
                <text class="cell-title">{{ b.nickname || '宝宝' }}</text>
                <text class="cell-sub">{{ babySubText(b) }}</text>
              </view>
              <view class="cell-right">
                <text v-if="isCurrent(b)" class="check">✓</text>
                <text v-else class="chev">›</text>
              </view>
            </view>
          </view>
        </view>

        <view class="actions">
          <button class="ghost-btn" :disabled="!currentBabyId" @click="editCurrentBaby">编辑当前宝宝</button>
          <button class="primary-btn" @click="addBaby">添加宝宝</button>
        </view>
      </template>
    </NbLoadingSwitch>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatBabyAgeText } from '@/utils/age'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadingSwitch from '@/components/NbLoadingSwitch.vue'
import NbState from '@/components/NbState.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbSkeletonAvatar from '@/components/NbSkeletonAvatar.vue'

export default {
  components: { NbNetworkBanner, NbLoadingSwitch, NbState, NbSkeleton, NbSkeletonAvatar },
  data() {
    return {
      loading: false,
      errorText: '',
      babies: [],
      returnTo: '',
    }
  },

  computed: {
    currentBabyId() {
      const store = useUserStore()
      return store.currentBaby?.id || null
    },
  },

  onLoad(options) {
    const store = useUserStore()
    if (!store.token) {
      try {
        const msg = uni.getStorageSync('nb_auth_notice')
        if (!msg) uni.setStorageSync('nb_auth_notice', '请先登录')
      } catch {}
      uni.reLaunch({ url: '/pages/login/index' })
      return
    }

    this.returnTo = String(options?.returnTo || options?.from || '').trim()
    this.init()
  },

  onShow() {
    // 从“新建宝宝/编辑宝宝”返回后刷新列表（即使之前为空，也要重拉一次）
    this.init({ silent: true })
  },

  methods: {
    onNbRetry() {
      this.init()
    },

    async init(opts = {}) {
      if (this.loading) return
      const silent = !!opts.silent
      this.loading = !silent
      this.errorText = ''
      try {
        const res = await api.get('/babies')
        this.babies = Array.isArray(res?.babies) ? res.babies : []

        const store = useUserStore()
        // 兜底：只有一个宝宝时，自动设为当前宝宝（减少首次使用摩擦）
        if (!store.currentBaby?.id && this.babies.length === 1 && this.babies[0]?.id) {
          store.setCurrentBaby(this.babies[0])
        }
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.loading = false
      }
    },

    isCurrent(b) {
      const bid = b?.id
      if (!bid) return false
      return String(bid) === String(this.currentBabyId || '')
    },

    babySubText(b) {
      const age = formatBabyAgeText(b?.birth_date)
      const z = String(b?.birth_time || '').trim()
      const parts = []
      if (age) parts.push(age)
      if (z) parts.push(z.slice(0, 5))
      return parts.join(' · ') || '—'
    },

    selectBaby(b) {
      if (!b?.id) return
      const store = useUserStore()
      store.setCurrentBaby(b)
      uni.showToast({ title: `已切换为「${b.nickname || '宝宝'}」`, icon: 'success' })

      // 选择完成后按来源返回：从设置来则回设置；否则回首页（避免多个页面 babyId 不一致）
      const pages = (typeof getCurrentPages === 'function') ? (getCurrentPages() || []) : []
      const canBack = pages.length > 1
      const from = String(this.returnTo || '').toLowerCase()
      const backToSettings = from === 'settings'

      setTimeout(() => {
        if (backToSettings && canBack) {
          uni.navigateBack()
          return
        }
        uni.reLaunch({ url: '/pages/home/index' })
      }, 350)
    },

    editCurrentBaby() {
      const id = this.currentBabyId
      if (!id) return
      uni.navigateTo({ url: `/pages/baby-info/index?id=${encodeURIComponent(String(id))}` })
    },

    addBaby() {
      // 多宝宝：必须允许“新建宝宝”而不是复用 currentBaby
      uni.navigateTo({ url: '/pages/baby-info/index?mode=new' })
    },
  },
}
</script>

<style scoped>
.baby-switch-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(24px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.group {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.08);
  margin-bottom: 12px;
}

.cells {
  display: flex;
  flex-direction: column;
}

.cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 12px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
  gap: 10px;
}

.cell:first-child {
  border-top: none;
}

.cell.tappable:active {
  background: rgba(27, 26, 23, 0.03);
}

.cell.active {
  background: rgba(247, 201, 72, 0.10);
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
}

.cell-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cell-title {
  font-size: 15px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-sub {
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.56);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.check {
  font-size: 18px;
  font-weight: 1000;
  color: rgba(27, 26, 23, 0.92);
}

.chev {
  font-size: 18px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.34);
}

.actions {
  display: flex;
  flex-direction: row;
  gap: 10px;
}

.ghost-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.82);
  font-weight: 900;
  font-size: 14px;
}

.primary-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
  font-weight: 900;
  border: none;
  font-size: 14px;
}
</style>
