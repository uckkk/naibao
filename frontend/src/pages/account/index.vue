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
          <!-- 设置中不再提供“用户头像替换”：只展示头像（减少噪音/减少运营与审核心智负担）。 -->
          <image :src="userAvatar" class="profile-avatar" mode="aspectFill" />

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

      <text class="section-h">隐私与数据</text>
      <view class="group">
        <view class="cells">
          <view class="cell tappable" @click="openExportSheet">
            <text class="cell-title">导出我的数据</text>
            <view class="cell-right">
              <text class="chev">›</text>
            </view>
          </view>

          <view class="cell tappable danger" @click="openDeleteSheet">
            <text class="cell-title danger-text">注销账号</text>
            <view class="cell-right">
              <text class="chev danger-text">›</text>
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

    <!-- 导出数据 -->
    <view
      v-if="exportSheetVisible"
      class="sheet-mask"
      @click.self="closeExportSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">导出我的数据</text>
        <text class="sheet-desc">
          将生成一份 JSON（包含账号、宝宝、喂奶记录等），你可以复制保存到安全的地方。
        </text>
        <text v-if="exportSummaryText" class="sheet-desc" style="margin-top:8px;">{{ exportSummaryText }}</text>
        <text v-if="exportErrorText" class="sheet-desc" style="margin-top:8px;color:var(--nb-danger);">
          {{ exportErrorText }}
        </text>

        <view class="sheet-actions">
          <button class="ghost-btn" :disabled="exportLoading" @click="closeExportSheet">关闭</button>
          <button class="primary-btn" :disabled="exportLoading" @click="generateExportAndCopy">
            {{ exportLoading ? '生成中...' : (exportReady ? '再次复制' : '生成并复制') }}
          </button>
        </view>
      </view>
    </view>

    <!-- 注销账号 -->
    <view
      v-if="deleteSheetVisible"
      class="sheet-mask"
      @click.self="closeDeleteSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">注销账号</text>
        <text class="sheet-desc">
          这会删除你在服务器上的账号与数据（宝宝、喂奶记录等），不可恢复。为防误触，请输入 DELETE 或「注销」后再确认。
        </text>
        <view class="fields">
          <input
            class="input"
            type="text"
            v-model="deleteConfirmText"
            placeholder="输入 DELETE 或 注销"
            placeholder-class="input-ph"
            :disabled="deleteLoading"
          />
        </view>
        <view class="sheet-actions">
          <button class="ghost-btn" :disabled="deleteLoading" @click="closeDeleteSheet">取消</button>
          <button class="danger-btn" :disabled="deleteLoading || !deleteConfirmOk" @click="submitDelete">
            {{ deleteLoading ? '注销中...' : '注销' }}
          </button>
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

export default {
  components: { NbState, NbNetworkBanner },
  data() {
    return {
      profileSaving: false,
      draftNickname: '',
      editingNickname: false,

      passwordSheetVisible: false,
      clearSheetVisible: false,
      exportSheetVisible: false,
      exportLoading: false,
      exportReady: false,
      exportPayload: null,
      exportErrorText: '',
      deleteSheetVisible: false,
      deleteConfirmText: '',
      deleteLoading: false,

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

    exportSummaryText() {
      if (!this.exportPayload || typeof this.exportPayload !== 'object') return ''
      const babies = Array.isArray(this.exportPayload?.babies) ? this.exportPayload.babies.length : 0
      const feedings = Array.isArray(this.exportPayload?.feedings) ? this.exportPayload.feedings.length : 0
      const growth = Array.isArray(this.exportPayload?.growth) ? this.exportPayload.growth.length : 0
      const parts = []
      if (babies) parts.push(`${babies} 个宝宝`)
      if (feedings) parts.push(`${feedings} 条喂奶记录`)
      if (growth) parts.push(`${growth} 条生长记录`)
      return parts.length ? `已包含：${parts.join('，')}` : ''
    },

    deleteConfirmOk() {
      const s = String(this.deleteConfirmText || '').trim()
      return s === 'DELETE' || s === '注销'
    },
  },

  onLoad(options) {
    const focus = String(options?.focus || '').trim().toLowerCase()
    if (focus === 'export') {
      setTimeout(() => this.openExportSheet({ autoGenerate: true }), 0)
    } else if (focus === 'delete') {
      setTimeout(() => this.openDeleteSheet(), 0)
    }
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

    openExportSheet(opts = {}) {
      if (this.exportLoading) return
      this.exportSheetVisible = true
      this.exportErrorText = ''
      const auto = !!opts.autoGenerate
      if (auto) this.generateExportAndCopy()
    },

    closeExportSheet() {
      if (this.exportLoading) return
      this.exportSheetVisible = false
    },

    async generateExportAndCopy() {
      if (this.exportLoading) return
      this.exportLoading = true
      this.exportErrorText = ''
      try {
        const payload = await api.get('/user/export', {}, { silent: true })
        this.exportPayload = payload || null
        this.exportReady = true

        // 直接复制，避免“生成了但不知道在哪里”的困惑
        const text = JSON.stringify(payload || {}, null, 2)
        await new Promise((resolve, reject) => {
          uni.setClipboardData({
            data: text,
            success: resolve,
            fail: reject,
          })
        })
        uni.showToast({ title: '已复制', icon: 'none' })
      } catch (e) {
        this.exportErrorText = e?.message || '生成失败'
      } finally {
        this.exportLoading = false
      }
    },

    openDeleteSheet() {
      this.deleteSheetVisible = true
      this.deleteConfirmText = ''
    },

    closeDeleteSheet() {
      if (this.deleteLoading) return
      this.deleteSheetVisible = false
    },

    async submitDelete() {
      if (this.deleteLoading) return
      if (!this.deleteConfirmOk) return
      this.deleteLoading = true
      try {
        await api.post('/user/delete', { confirm: String(this.deleteConfirmText || '').trim() })
        uni.showToast({ title: '账号已注销', icon: 'none' })
        setTimeout(() => this.clearAndLogout(), 300)
      } catch (e) {
        uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
      } finally {
        this.deleteLoading = false
      }
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

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(27, 26, 23, 0.10);
  box-shadow: 0 10px 24px rgba(27, 26, 23, 0.10);
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
