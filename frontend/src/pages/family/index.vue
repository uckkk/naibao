<template>
  <view class="family-container">
    <NbNetworkBanner />

    <view class="card">
      <text class="card-title">加入家庭</text>
      <text class="card-sub">输入 6 位邀请码即可加入并同步同一宝宝的数据</text>

      <view class="join-row">
        <input
          class="code-input"
          type="number"
          inputmode="numeric"
          maxlength="6"
          v-model="inviteCode"
          placeholder="例如 123456"
        />
        <button class="join-btn" :disabled="joining || inviteCode.trim().length !== 6" @click="useInvite">
          {{ joining ? '加入中...' : '加入' }}
        </button>
      </view>
    </view>

    <view class="card" v-if="babyId">
      <view class="card-head">
        <text class="card-title">家庭成员</text>
        <text class="pill" v-if="myRole">{{ myRole === 'admin' ? '管理员' : '成员' }}</text>
      </view>

      <NbState v-if="membersLoading" embedded type="loading" title="加载中..." />

      <NbState
        v-else-if="membersError"
        embedded
        type="error"
        title="加载失败"
        :desc="membersError"
        actionText="重试"
        @action="loadMembers"
      />

      <NbState v-else-if="members.length === 0" embedded type="empty" title="暂无成员" :desc="emptyMembersDesc" />

      <view v-else class="members">
        <view v-for="m in members" :key="m.user_id" class="member">
          <image :src="m.avatar_url || '/static/default-avatar.png'" class="avatar" mode="aspectFill" />
          <view class="meta">
            <text class="name">{{ m.nickname || '未命名' }}</text>
            <text class="role">{{ m.role === 'admin' ? '管理员' : '成员' }}</text>
          </view>
          <button
            v-if="canManage && String(m.user_id) !== String(meId)"
            class="remove-btn"
            @click="removeMember(m)"
          >
            移除
          </button>
        </view>
      </view>
    </view>

    <view class="card" v-if="babyId && canManage">
      <text class="card-title">邀请家人</text>
      <text class="card-sub">生成邀请码后复制给家人（7天有效，用后失效）</text>

      <view class="invite-box" v-if="generatedCode">
        <view class="digits">
          <view v-for="(d, idx) in generatedCode.split('')" :key="idx" class="digit">{{ d }}</view>
        </view>
        <view class="invite-actions">
          <button class="ghost-btn" @click="copyCode">复制</button>
          <button class="primary-btn" :disabled="generating" @click="generateInvite">
            {{ generating ? '生成中...' : '重新生成' }}
          </button>
        </view>
        <text v-if="expiresAt" class="hint">有效期至：{{ expiresAtDisplay }}</text>
      </view>

      <view class="invite-actions" v-else>
        <button class="primary-btn" :disabled="generating" @click="generateInvite">
          {{ generating ? '生成中...' : '生成邀请码' }}
        </button>
      </view>
    </view>

    <NbConfirmSheet
      :visible="removeSheetVisible"
      title="移除成员"
      :desc="removeSheetDesc"
      confirmText="移除"
      cancelText="取消"
      confirmVariant="danger"
      :loading="removing"
      @confirm="confirmRemoveMember"
      @cancel="cancelRemoveMember"
    />
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbState from '@/components/NbState.vue'

export default {
  components: { NbConfirmSheet, NbNetworkBanner, NbState },
  data() {
    return {
      babyId: null,
      inviteCode: '',
      joining: false,
      members: [],
      membersLoading: false,
      membersError: '',
      myRole: '',
      meId: null,

      generating: false,
      generatedCode: '',
      expiresAt: '',

      removeSheetVisible: false,
      removing: false,
      pendingRemoveMember: null,
    }
  },

  computed: {
    canManage() {
      return this.myRole === 'admin'
    },
    emptyMembersDesc() {
      return this.canManage ? '生成邀请码邀请家人一起记' : '等待管理员邀请，或输入邀请码加入'
    },
    removeSheetDesc() {
      const m = this.pendingRemoveMember || null
      return `确定移除 ${m?.nickname || '该成员'} 吗？`
    },
    expiresAtDisplay() {
      if (!this.expiresAt) return ''
      const s = String(this.expiresAt)
      // RFC3339 -> 本地展示（不做复杂时区处理，避免 Safari 解析差异）
      const m = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/)
      if (!m) return s
      return `${m[1]}.${m[2]}.${m[3]} ${m[4]}:${m[5]}`
    },
  },

  onLoad(options) {
    const userStore = useUserStore()
    this.meId = userStore.user?.id || null

    if (options.babyId) {
      this.babyId = options.babyId
    } else if (userStore.currentBaby?.id) {
      this.babyId = userStore.currentBaby.id
    }

    if (this.babyId) {
      this.loadMembers()
    }
  },

  onShow() {
    const userStore = useUserStore()
    // 多宝宝：默认全局跟随 currentBaby
    const storeId = userStore.currentBaby?.id || null
    if (storeId && String(storeId) !== String(this.babyId || '')) {
      this.babyId = storeId
      this.inviteCode = ''
      this.members = []
      this.membersError = ''
      this.myRole = ''
      this.generatedCode = ''
      this.expiresAt = ''
      this.loadMembers()
    }
  },

  methods: {
    onNbRetry() {
      // 弱网恢复后：刷新家庭成员（如果已选宝宝）
      if (this.babyId) this.loadMembers()
    },

    async loadMembers() {
      if (!this.babyId) return
      this.membersLoading = true
      this.membersError = ''
      try {
        const res = await api.get(`/babies/${this.babyId}/family-members`)
        this.members = Array.isArray(res.members) ? res.members : []
        const me = this.members.find((m) => String(m.user_id) === String(this.meId))
        this.myRole = me?.role || ''
      } catch (e) {
        console.error('加载家庭成员失败', e)
        this.membersError = e?.message || '加载失败'
      } finally {
        this.membersLoading = false
      }
    },

    async generateInvite() {
      if (!this.babyId || this.generating) return
      this.generating = true
      try {
        const res = await api.post('/invite/generate', { baby_id: Number(this.babyId) })
        this.generatedCode = String(res.code || '').trim()
        this.expiresAt = res.expires_at || ''
        if (this.generatedCode) {
          uni.showToast({ title: '邀请码已生成', icon: 'success' })
        }
      } catch (e) {
        uni.showToast({ title: e.message || '生成失败', icon: 'none' })
      } finally {
        this.generating = false
      }
    },

    copyCode() {
      if (!this.generatedCode) return
      uni.setClipboardData({
        data: this.generatedCode,
        success: () => uni.showToast({ title: '已复制', icon: 'success' }),
      })
    },

    async useInvite() {
      const code = String(this.inviteCode || '').trim()
      if (code.length !== 6 || this.joining) return
      this.joining = true
      try {
        const res = await api.post('/invite/use', { code })
        const baby = res?.baby
        if (baby && baby.id) {
          const userStore = useUserStore()
          userStore.setCurrentBaby(baby)
          this.babyId = baby.id
          await this.loadMembers()
          uni.showToast({ title: '加入成功', icon: 'success' })
          setTimeout(() => {
            uni.reLaunch({ url: '/pages/home/index' })
          }, 500)
          return
        }
        uni.showToast({ title: '加入成功', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '加入失败', icon: 'none' })
      } finally {
        this.joining = false
      }
    },

    removeMember(member) {
      if (!this.babyId || !member?.user_id) return
      this.pendingRemoveMember = member
      this.removeSheetVisible = true
    },

    cancelRemoveMember() {
      if (this.removing) return
      this.removeSheetVisible = false
      this.pendingRemoveMember = null
    },

    async confirmRemoveMember() {
      const member = this.pendingRemoveMember
      if (!this.babyId || !member?.user_id || this.removing) return
      this.removing = true
      try {
        await api.delete(`/babies/${this.babyId}/family-members/${member.user_id}`)
        uni.showToast({ title: '已移除', icon: 'success' })
        await this.loadMembers()
        this.cancelRemoveMember()
      } catch (e) {
        uni.showToast({ title: e.message || '移除失败', icon: 'none' })
      } finally {
        this.removing = false
      }
    },
  },
}
</script>

<style scoped>
.family-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + env(safe-area-inset-top, 0px)) var(--nb-page-x)
    calc(24px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
}

.card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 16px;
  margin-bottom: 14px;
}

.card-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--nb-text);
}

.card-sub {
  display: block;
  margin-top: 6px;
  font-size: 13px;
  color: var(--nb-muted);
}

.pill {
  font-size: 12px;
  color: var(--nb-text);
  background: rgba(247, 201, 72, 0.22);
  border: 1px solid rgba(247, 201, 72, 0.45);
  padding: 6px 10px;
  border-radius: 999px;
}

.join-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.code-input {
  flex: 1;
  height: 48px;
  border-radius: 14px;
  padding: 0 14px;
  font-size: 16px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  box-sizing: border-box;
  background: #fff;
}

.code-input:focus {
  outline: none;
  border-color: var(--nb-accent);
  box-shadow: 0 0 0 4px rgba(247, 201, 72, 0.22);
}

.join-btn {
  height: 48px;
  padding: 0 14px;
  border-radius: 24px;
  background: rgba(27, 26, 23, 0.88);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  border: none;
}

.join-btn[disabled] {
  background: rgba(27, 26, 23, 0.16);
  color: rgba(27, 26, 23, 0.45);
}

.members {
  margin-top: 12px;
}

.member {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(27, 26, 23, 0.08);
}

.member:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.06);
}

.meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.name {
  font-size: 16px;
  font-weight: 700;
  color: var(--nb-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role {
  font-size: 12px;
  color: var(--nb-muted);
  margin-top: 2px;
}

.remove-btn {
  height: 36px;
  padding: 0 12px;
  border-radius: 18px;
  background: rgba(226, 74, 59, 0.12);
  color: var(--nb-danger);
  border: 1px solid rgba(226, 74, 59, 0.22);
  font-size: 13px;
  font-weight: 700;
}

.invite-box {
  margin-top: 14px;
}

.digits {
  display: flex;
  flex-direction: row;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
}

.digit {
  width: 42px;
  height: 48px;
  border-radius: 14px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  text-align: center;
  line-height: 48px;
  font-size: 20px;
  font-weight: 900;
  color: var(--nb-text);
}

.invite-actions {
  display: flex;
  flex-direction: row;
  gap: 10px;
  justify-content: center;
}

.primary-btn,
.ghost-btn {
  height: 44px;
  padding: 0 14px;
  border-radius: 22px;
  font-size: 15px;
  font-weight: 800;
  border: none;
}

.primary-btn {
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
}

.primary-btn[disabled] {
  background: rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.45);
}

.ghost-btn {
  background: rgba(27, 26, 23, 0.08);
  color: var(--nb-text);
}

.hint {
  display: block;
  margin-top: 10px;
  text-align: center;
  font-size: 12px;
  color: var(--nb-muted);
}

.empty {
  padding: 14px 0 4px;
}

.empty-text {
  color: var(--nb-muted);
  font-size: 13px;
}
</style>
