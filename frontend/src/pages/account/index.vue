<template>
  <view class="account-page">
    <NbNetworkBanner />
    <NbState
      v-if="!isLoggedIn"
      type="info"
      title="请先登录"
      actionText="去登录"
      @action="goLogin"
    />

    <template v-else>
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="openProfileSheet">
            <image class="avatar" :src="userAvatar" mode="aspectFill" />
            <text class="cell-title">{{ userName }}</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <text class="section-h">账号</text>
      <view class="group">
        <view class="cells">
          <view class="cell">
            <text class="cell-title">手机号</text>
            <view class="cell-right">
              <text class="cell-value">{{ maskedPhone || '—' }}</text>
            </view>
          </view>

          <view class="cell tappable" @click="openPasswordSheet">
            <text class="cell-title">修改密码</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable danger" @click="openClearSheet">
            <text class="cell-title danger-text">清除本机缓存</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>
        </view>
      </view>

      <view class="group">
        <view class="cells">
          <view class="cell tappable danger" @click="logout">
            <text class="cell-title danger-text">退出登录</text>
          </view>
        </view>
      </view>
    </template>

    <!-- 修改密码 -->
    <view
      v-if="passwordSheetVisible"
      class="sheet-mask"
      @click.self="closePasswordSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">修改密码</text>
        <view class="fields">
          <input
            class="input"
            type="password"
            v-model="oldPassword"
            placeholder="旧密码"
            placeholder-class="input-ph"
          />
          <input
            class="input"
            type="password"
            v-model="newPassword"
            placeholder="新密码（至少6位）"
            placeholder-class="input-ph"
          />
          <input
            class="input"
            type="password"
            v-model="newPassword2"
            placeholder="再次输入新密码"
            placeholder-class="input-ph"
          />
        </view>
        <view class="sheet-actions">
          <button class="ghost-btn" :disabled="saving" @click="closePasswordSheet">取消</button>
          <button class="primary-btn" :disabled="saving" @click="submitPassword">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </view>
      </view>
    </view>

    <!-- 编辑资料（昵称/头像一层完成，避免入口过深） -->
    <view
      v-if="profileSheetVisible"
      class="sheet-mask"
      @click.self="closeProfileSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">账号资料</text>

        <view class="profile-hero">
          <image class="profile-avatar" :src="draftAvatarUrl || userAvatar" mode="aspectFill" />
          <text class="profile-name">{{ draftNickname || userName }}</text>
        </view>

        <view class="fields">
          <input
            class="input"
            type="text"
            v-model="draftNickname"
            placeholder="昵称（最多20字）"
            placeholder-class="input-ph"
          />
        </view>

        <view class="avatar-grid">
          <view
            v-for="a in avatars"
            :key="a.id"
            class="avatar-item"
            :class="{ selected: draftAvatarId === a.id }"
            @click="selectDraftAvatar(a)"
          >
            <image class="avatar-img" :src="a.url" mode="aspectFill" />
            <view v-if="draftAvatarId === a.id" class="avatar-check">
              <text class="avatar-check-text">✓</text>
            </view>
          </view>
        </view>

        <view class="sheet-actions">
          <button class="ghost-btn" :disabled="profileSaving" @click="closeProfileSheet">取消</button>
          <button class="primary-btn" :disabled="profileSaving" @click="submitProfile">
            {{ profileSaving ? '保存中...' : '保存' }}
          </button>
        </view>
      </view>
    </view>

    <!-- 清除缓存 -->
    <view
      v-if="clearSheetVisible"
      class="sheet-mask"
      @click.self="closeClearSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">清除本机缓存</text>
        <text class="sheet-desc">将清除本机缓存并退出登录</text>
        <view class="sheet-actions">
          <button class="ghost-btn" @click="closeClearSheet">取消</button>
          <button class="danger-btn" @click="clearAndLogout">清除</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { getAllAvatars } from '@/utils/avatars'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbState, NbNetworkBanner },
  data() {
    return {
      profileSheetVisible: false,
      profileSaving: false,
      draftNickname: '',
      draftAvatarId: null,
      avatars: [],

      passwordSheetVisible: false,
      clearSheetVisible: false,

      oldPassword: '',
      newPassword: '',
      newPassword2: '',
      saving: false,
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
    userName() {
      return this.user?.nickname || '账号'
    },
    userAvatar() {
      return this.user?.avatar_url || '/static/default-avatar.png'
    },
    maskedPhone() {
      const raw = String(this.user?.phone || '').trim()
      if (raw.length < 7) return raw || ''
      return raw.slice(0, 3) + '****' + raw.slice(-4)
    },
    draftAvatarUrl() {
      const id = this.draftAvatarId
      if (!id) return ''
      const found = (Array.isArray(this.avatars) ? this.avatars : []).find((x) => x.id === id)
      return found?.url || ''
    },
  },

  onShow() {
    this.refreshProfile()
  },

  methods: {
    onNbRetry() {
      this.refreshProfile()
    },

    goLogin() {
      uni.reLaunch({ url: '/pages/login/index' })
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
        // ignore
      }
    },

    openProfileSheet() {
      if (this.profileSaving) return
      this.avatars = getAllAvatars()
      this.draftNickname = this.user?.nickname || ''
      const cur = this.user?.avatar_url || ''
      const found = this.avatars.find((a) => a.url === cur)
      this.draftAvatarId = found?.id || (this.avatars[0] ? this.avatars[0].id : null)
      this.profileSheetVisible = true
    },

    closeProfileSheet() {
      if (this.profileSaving) return
      this.profileSheetVisible = false
    },

    selectDraftAvatar(a) {
      if (!a || !a.id) return
      this.draftAvatarId = a.id
    },

    async submitProfile() {
      if (this.profileSaving) return
      const userStore = useUserStore()
      const nick = String(this.draftNickname || '').trim()
      if (!nick) return uni.showToast({ title: '请输入昵称', icon: 'none' })
      if (Array.from(nick).length > 20) return uni.showToast({ title: '昵称最多20字', icon: 'none' })

      const avatarUrl = this.draftAvatarUrl || this.userAvatar

      this.profileSaving = true
      try {
        await userStore.updateProfile({ nickname: nick, avatar_url: avatarUrl })
        uni.showToast({ title: '已更新', icon: 'success' })
        setTimeout(() => this.closeProfileSheet(), 450)
      } catch (e) {
        uni.showToast({ title: e?.message || '更新失败', icon: 'none' })
      } finally {
        this.profileSaving = false
      }
    },

    openPasswordSheet() {
      this.passwordSheetVisible = true
      this.oldPassword = ''
      this.newPassword = ''
      this.newPassword2 = ''
    },

    closePasswordSheet() {
      if (this.saving) return
      this.passwordSheetVisible = false
    },

    async submitPassword() {
      if (this.saving) return
      const oldP = String(this.oldPassword || '').trim()
      const p1 = String(this.newPassword || '').trim()
      const p2 = String(this.newPassword2 || '').trim()

      if (!oldP) return uni.showToast({ title: '请输入旧密码', icon: 'none' })
      if (p1.length < 6) return uni.showToast({ title: '新密码至少6位', icon: 'none' })
      if (p1 !== p2) return uni.showToast({ title: '两次密码不一致', icon: 'none' })
      if (oldP === p1) return uni.showToast({ title: '新密码不能相同', icon: 'none' })

      this.saving = true
      try {
        await api.put('/user/password', { old_password: oldP, new_password: p1 })
        uni.showToast({ title: '已更新', icon: 'success' })
        setTimeout(() => this.closePasswordSheet(), 450)
      } catch (e) {
        uni.showToast({ title: e?.message || '修改失败', icon: 'none' })
      } finally {
        this.saving = false
      }
    },

    openClearSheet() {
      this.clearSheetVisible = true
    },

    closeClearSheet() {
      this.clearSheetVisible = false
    },

    clearAndLogout() {
      try {
        uni.clearStorageSync()
      } catch {
        // fallback: 至少清掉登录态
        try {
          uni.removeStorageSync('token')
          uni.removeStorageSync('user')
          uni.removeStorageSync('currentBaby')
        } catch {}
      }
      uni.reLaunch({ url: '/pages/login/index' })
    },

    logout() {
      const userStore = useUserStore()
      userStore.logout()
    },
  },
}
</script>

<style scoped>
.account-page {
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

.profile-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.profile-avatar {
  width: 68px;
  height: 68px;
  border-radius: 22px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
}

.profile-name {
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.82);
}

.avatar-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.avatar-item {
  position: relative;
  width: 100%;
  padding-top: 100%;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
}

.avatar-item.selected {
  border-color: rgba(255, 138, 61, 0.65);
  box-shadow: 0 0 0 4px rgba(255, 138, 61, 0.16);
}

.avatar-img {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
}

.avatar-check {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 18px;
  height: 18px;
  border-radius: 9px;
  background: rgba(255, 138, 61, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.9);
}

.avatar-check-text {
  font-size: 12px;
  color: #fff;
  font-weight: 900;
  line-height: 1;
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
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chev {
  font-size: 18px;
  color: rgba(27, 26, 23, 0.38);
  font-weight: 900;
}

.danger-text {
  color: var(--nb-danger);
}

.sheet-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 12px var(--nb-page-x) calc(12px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.sheet {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.25);
}

.sheet-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
  margin-bottom: 10px;
}

.sheet-desc {
  display: block;
  margin-top: -2px;
  font-size: 13px;
  color: rgba(27, 26, 23, 0.62);
  line-height: 1.6;
}

.fields {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input {
  height: 46px;
  border-radius: 14px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(27, 26, 23, 0.04);
  padding: 0 12px;
  font-size: 14px;
  box-sizing: border-box;
}

.sheet-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.ghost-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.82);
  font-weight: 800;
  font-size: 14px;
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

.danger-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: rgba(226, 74, 59, 0.12);
  border: 1px solid rgba(226, 74, 59, 0.22);
  color: var(--nb-danger);
  font-weight: 900;
  font-size: 14px;
}
</style>
