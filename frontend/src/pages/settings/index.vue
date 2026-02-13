<template>
  <view class="settings-page">
    <NbNetworkBanner />
    <NbState
      v-if="!isLoggedIn"
      type="info"
      title="请先登录"
      desc="登录后才能同步喂养与宝宝数据"
      actionText="去登录"
      @action="goLogin"
    />

    <NbLoadable v-else :loading="pageLoading" :errorText="errorText" @retry="init">
      <template #skeleton>
        <view class="group">
          <view class="cells">
            <view class="cell">
              <NbSkeletonAvatar :size="40" :radius="14" />
              <NbSkeleton :w="120" :h="16" :radius="8" />
              <view class="cell-right">
                <NbSkeleton :w="90" :h="12" :radius="6" />
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>

        <view style="margin:12px 6px 8px;">
          <NbSkeleton :w="40" :h="10" :radius="6" />
        </view>
        <view class="group">
          <view class="cells">
            <view class="cell">
              <NbSkeleton :w="88" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="64" :h="12" :radius="6" />
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
            <view class="cell">
              <NbSkeleton :w="46" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="86" :h="12" :radius="6" />
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
            <view class="cell">
              <NbSkeleton :w="64" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>

        <view style="margin:12px 6px 8px;">
          <NbSkeleton :w="40" :h="10" :radius="6" />
        </view>
        <view class="group">
          <view class="cells">
            <view class="cell">
              <NbSkeleton :w="64" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="70" :h="12" :radius="6" />
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
            <view class="cell">
              <NbSkeleton :w="72" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
            <view class="cell">
              <NbSkeleton :w="64" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>

        <view style="margin:12px 6px 8px;">
          <NbSkeleton :w="40" :h="10" :radius="6" />
        </view>
        <view class="group">
          <view class="cells">
            <view class="cell">
              <NbSkeleton :w="72" :h="14" :radius="7" />
              <view class="cell-right">
                <NbSkeleton :w="10" :h="12" :radius="6" />
              </view>
            </view>
          </view>
        </view>
      </template>

      <!-- 账号 -->
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="goAccount">
            <!-- 入口减深：在设置页即可一键更换头像（仍可点整行进入账号页改昵称/密码等）。 -->
            <view @click.stop>
              <NbAvatarUpload
                :src="userAvatar"
                uploadUrl="/user/avatar/upload"
                :size="40"
                :radius="14"
                :disabled="pageLoading"
                @uploaded="handleUserAvatarUploaded"
              />
            </view>
            <text class="cell-title">{{ userName }}</text>
            <view class="cell-right">
              <text class="cell-value">{{ maskedPhone }}</text>
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 宝宝 -->
      <text class="section-h">宝宝</text>
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="goBabySwitch">
            <text class="cell-title">切换宝宝</text>
            <view class="cell-right">
              <text class="cell-value">{{ babyName }}</text>
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goBabyInfo">
            <text class="cell-title">宝宝资料</text>
            <view class="cell-right">
              <text class="cell-value">{{ currentBaby?.id ? '编辑' : '去建档' }}</text>
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goFormula">
            <text class="cell-title">奶粉</text>
            <view class="cell-right">
              <text class="cell-value">{{ formulaName }}</text>
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goWeaningPlan">
            <text class="cell-title">转奶期</text>
            <view class="cell-right">
              <text class="cell-value">{{ weaningPlanText }}</text>
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goFamily">
            <text class="cell-title">家庭共享</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 喂养 -->
      <text class="section-h">喂养</text>
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="goFeedingSettings">
            <text class="cell-title">喂奶间隔</text>
            <view class="cell-right">
              <text class="cell-value">{{ feedingIntervalText }}</text>
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goPreference">
            <text class="cell-title">投喂偏好</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goReport">
            <text class="cell-title">数据报告</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goDataDetail">
            <text class="cell-title">数据详情</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 帮助 -->
      <text class="section-h">帮助</text>
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="goHelp">
            <text class="cell-title">常见问题</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable" @click="goLegal">
            <text class="cell-title">隐私与数据</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>
    </NbLoadable>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { formatStageTextFromAgeRange } from '@/utils/formula_stage'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbSkeletonAvatar from '@/components/NbSkeletonAvatar.vue'
import NbAvatarUpload from '@/components/NbAvatarUpload.vue'

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton, NbSkeletonAvatar, NbAvatarUpload },
  data() {
    return {
      pageLoading: false,
      errorText: '',

      formulaName: '未绑定',
      feedingIntervalText: '—',
      weaningPlanText: '—',
    }
  },

  computed: {
    isLoggedIn() {
      const userStore = useUserStore()
      return !!userStore.token
    },
    user() {
      const userStore = useUserStore()
      return userStore.user || null
    },
    currentBaby() {
      const userStore = useUserStore()
      return userStore.currentBaby || null
    },
    userName() {
      return this.user?.nickname || '账号'
    },
    userAvatar() {
      return this.user?.avatar_url || '/static/default-avatar.png'
    },
    maskedPhone() {
      const raw = String(this.user?.phone || '').trim()
      if (raw.length < 7) return raw || '—'
      return raw.slice(0, 3) + '****' + raw.slice(-4)
    },
    babyName() {
      const b = this.currentBaby
      if (!b?.id) return '未创建'
      return b.nickname || '宝宝'
    },
  },

  onShow() {
    // 切换宝宝/更新绑定后，从设置页返回时要刷新显示文案
    this.init()
  },

  methods: {
    onNbRetry() {
      this.init()
    },

    async handleUserAvatarUploaded(nextUrl) {
      const url = String(nextUrl || '').trim()
      if (!url) return
      try {
        const userStore = useUserStore()
        await userStore.updateProfile({ avatar_url: url })
        uni.showToast({ title: '头像已更新', icon: 'none' })
      } catch (e) {
        uni.showToast({ title: e?.message || '更新失败', icon: 'none' })
      }
    },

    async init() {
      if (!this.isLoggedIn) return
      this.pageLoading = true
      this.errorText = ''

      try {
        await this.refreshProfile()
        await this.refreshBabyAndMeta()
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    async refreshProfile() {
      const userStore = useUserStore()
      try {
        const res = await api.get('/user/profile')
        if (res?.user) {
          userStore.user = res.user
          uni.setStorageSync('user', res.user)
        }
      } catch {
        // 失败时用本地缓存兜底
      }
    },

    async refreshBabyAndMeta() {
      const userStore = useUserStore()

      // 兜底：若没有 currentBaby，自动选择第一个（避免“设置页一片空”）
      if (!userStore.currentBaby?.id) {
        try {
          const res = await api.get('/babies')
          const first = Array.isArray(res.babies) ? res.babies[0] : null
          if (first?.id) userStore.setCurrentBaby(first)
        } catch {
          // ignore
        }
      }

      const babyId = userStore.currentBaby?.id
      if (!babyId) {
        this.formulaName = '未绑定'
        this.feedingIntervalText = '—'
        this.weaningPlanText = '—'
        return
      }

      // 并行加载：奶粉 + 喂奶间隔 + 转奶期状态
      await Promise.all([this.loadFormulaName(babyId), this.loadFeedingInterval(babyId), this.loadWeaningPlanMeta(babyId)])
    },

    async loadFormulaName(babyId) {
      try {
        const res = await api.get(`/babies/${babyId}/formula`, {}, { silent: true })
        const sel = res?.selection || null
        if (!sel) {
          this.formulaName = '未绑定'
          return
        }
        const brandName = sel?.brand?.name_cn || '未绑定'
        const stageText = formatStageTextFromAgeRange(sel?.age_range)
        this.formulaName = [brandName, stageText].filter(Boolean).join(' · ') || brandName
      } catch {
        this.formulaName = '未绑定'
      }
    },

    async loadFeedingInterval(babyId) {
      try {
        const res = await api.get(`/babies/${babyId}/settings`)
        const s = res?.settings || null
        const d = Number(s?.day_interval ?? 0)
        const n = Number(s?.night_interval ?? 0)
        if (d > 0 && n > 0) this.feedingIntervalText = `${d}h/${n}h`
        else if (d > 0) this.feedingIntervalText = `${d}h`
        else this.feedingIntervalText = '—'
      } catch {
        this.feedingIntervalText = '—'
      }
    },

    async loadWeaningPlanMeta(babyId) {
      try {
        const res = await api.get(`/babies/${babyId}/weaning-plan`, {}, { silent: true })
        const plan = res?.plan || null
        if (!plan) {
          this.weaningPlanText = '未开启'
          return
        }

        const d = Number(plan.duration_days || 7) || 7
        const startMs = plan.start_at ? new Date(String(plan.start_at)).getTime() : 0
        const endMs = startMs ? startMs + d * 24 * 60 * 60 * 1000 : 0
        const now = Date.now()
        const completed = endMs ? now >= endMs : false
        if (completed) {
          this.weaningPlanText = '已完成'
          return
        }
        if (plan.status === 'paused') {
          this.weaningPlanText = '已暂停'
          return
        }
        if (startMs) {
          const day = Math.floor(Math.max(0, now - startMs) / (24 * 60 * 60 * 1000)) + 1
          const idx = Math.min(d, Math.max(1, day))
          this.weaningPlanText = `进行中 ${idx}/${d}`
          return
        }
        this.weaningPlanText = '进行中'
      } catch {
        this.weaningPlanText = '—'
      }
    },

    goLogin() {
      uni.reLaunch({ url: '/pages/login/index' })
    },

    goAccount() {
      uni.navigateTo({ url: '/pages/account/index' })
    },

    goBabySwitch() {
      uni.navigateTo({ url: '/pages/baby-switch/index?returnTo=settings' })
    },

    goBabyInfo() {
      // 未建档时：直接进入建档页
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },

    goFormula() {
      const babyId = this.currentBaby?.id
      if (!babyId) return this.goBabyInfo()
      uni.navigateTo({ url: `/pages/formula-select/index?babyId=${babyId}` })
    },

    goWeaningPlan() {
      const babyId = this.currentBaby?.id
      if (!babyId) return this.goBabyInfo()
      uni.navigateTo({ url: `/pages/weaning-plan/index?babyId=${babyId}` })
    },

    goFamily() {
      const babyId = this.currentBaby?.id
      uni.navigateTo({ url: `/pages/family/index?babyId=${babyId || ''}` })
    },

    goFeedingSettings() {
      const babyId = this.currentBaby?.id
      if (!babyId) return this.goBabyInfo()
      uni.navigateTo({ url: `/pages/feeding-settings/index?babyId=${babyId}` })
    },

    goPreference() {
      const babyId = this.currentBaby?.id
      if (!babyId) return this.goBabyInfo()
      uni.navigateTo({ url: `/pages/preference/index?babyId=${babyId}` })
    },

    goReport() {
      const babyId = this.currentBaby?.id
      if (!babyId) return this.goBabyInfo()
      uni.navigateTo({ url: `/pages/report/index?babyId=${babyId}` })
    },

    goDataDetail() {
      uni.navigateTo({ url: '/pages/data-detail/index' })
    },

    goHelp() {
      uni.navigateTo({ url: '/pages/help/index' })
    },

    goLegal() {
      uni.navigateTo({ url: '/pages/legal/index' })
    },
  },
}
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  padding: calc(14px + var(--nb-safe-top)) var(--nb-page-x) calc(28px + var(--nb-safe-bottom));
  box-sizing: border-box;
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

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
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
  color: rgba(27, 26, 23, 0.56);
  font-weight: 800;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chev {
  font-size: 18px;
  color: rgba(27, 26, 23, 0.38);
  font-weight: 900;
}
</style>
