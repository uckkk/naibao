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
        <!-- 信息减法：资料编辑不再藏到下一层 Sheet；在本页一屏完成（更像 iOS 的“账号资料”）。 -->
        <view class="profile-editor">
          <NbAvatarUpload
            :src="draftAvatarUrl || userAvatar"
            uploadUrl="/user/avatar/upload"
            :size="72"
            :radius="24"
            :disabled="profileSaving"
            @uploaded="handleAvatarUploaded"
          />

          <view class="profile-main">
            <text class="profile-title">账号资料</text>
            <view class="profile-row">
              <text class="profile-label">昵称</text>
              <input
                class="profile-input"
                type="text"
                v-model="draftNickname"
                placeholder="输入昵称（最多20字）"
                placeholder-class="input-ph"
                :disabled="profileSaving"
                @focus="editingNickname = true"
                @blur="handleNicknameBlur"
                @confirm="submitNickname"
              />
            </view>
            <text class="profile-hint">{{ profileHintText }}</text>
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
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbAvatarUpload from '@/components/NbAvatarUpload.vue'

export default {
  components: { NbState, NbNetworkBanner, NbAvatarUpload },
  data() {
    return {
      profileSaving: false,
      draftNickname: '',
      draftAvatarUrl: '',
      editingNickname: false,

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
    profileHintText() {
      if (this.profileSaving) return '保存中...'
      const u = this.user || {}
      const nick = String(this.draftNickname || '').trim()
      const curNick = String(u.nickname || '').trim()
      const dirtyNick = this.editingNickname ? true : (nick && nick !== curNick)
      return dirtyNick ? '编辑完成后自动保存' : '已保存'
    },
  },

  onShow() {
    this.refreshProfile()
  },

  watch: {
    user: {
      immediate: true,
      handler() {
        // 外部刷新/保存后：同步草稿（避免用户看到旧值）
        if (this.profileSaving || this.editingNickname) return
        this.draftNickname = String(this.user?.nickname || '').trim()
        this.draftAvatarUrl = ''
      },
    },
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

    async handleAvatarUploaded(url) {
      const nextUrl = String(url || '').trim()
      if (!nextUrl) return
      if (this.profileSaving) return
      const userStore = useUserStore()
      this.profileSaving = true
      // 先乐观更新：让用户立刻看到新头像（更像 iOS 的“立即生效”）
      this.draftAvatarUrl = nextUrl
      try {
        await userStore.updateProfile({ avatar_url: nextUrl })
        this.draftAvatarUrl = ''
        uni.showToast({ title: '头像已更新', icon: 'success' })
      } catch (e) {
        this.draftAvatarUrl = ''
        uni.showToast({ title: e?.message || '更新失败', icon: 'none' })
      } finally {
        this.profileSaving = false
      }
    },

    handleNicknameBlur() {
      this.editingNickname = false
      this.submitNickname()
    },

    async submitNickname() {
      if (this.profileSaving) return
      const userStore = useUserStore()
      const nick = String(this.draftNickname || '').trim()
      const cur = String(this.user?.nickname || '').trim()
      if (!nick) {
        this.draftNickname = cur
        return
      }
      if (Array.from(nick).length > 20) {
        uni.showToast({ title: '昵称最多20字', icon: 'none' })
        this.draftNickname = cur
        return
      }
      if (nick === cur) return

      this.profileSaving = true
      try {
        await userStore.updateProfile({ nickname: nick })
        uni.showToast({ title: '昵称已更新', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e?.message || '更新失败', icon: 'none' })
        this.draftNickname = cur
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

.profile-editor {
  padding: 14px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  box-sizing: border-box;
}

.profile-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.profile-title {
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.82);
}

.profile-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.profile-label {
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.62);
  white-space: nowrap;
}

.profile-input {
  flex: 1;
  min-width: 0;
  height: 38px;
  border-radius: 12px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(27, 26, 23, 0.04);
  padding: 0 10px;
  font-size: 14px;
  font-weight: 800;
  box-sizing: border-box;
}

.profile-hint {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.52);
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
