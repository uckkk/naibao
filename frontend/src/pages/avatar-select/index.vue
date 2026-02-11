<template>
  <view class="avatar-select-container">
    <view class="header">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">‹</text>
      </view>
      <text class="title">选择头像</text>
      <view class="placeholder"></view>
    </view>

    <NbNetworkBanner />
    
    <view class="current-avatar-section">
      <text class="current-label">当前头像</text>
      <view class="current-avatar-wrapper">
        <image 
          :src="currentAvatarUrl || '/static/default-avatar.png'" 
          class="current-avatar"
          mode="aspectFill"
        />
      </view>
    </view>
    
    <view class="avatars-grid">
      <view 
        v-for="avatar in avatars" 
        :key="avatar.id"
        class="avatar-item"
        :class="{ 'selected': selectedAvatarId === avatar.id }"
        @click="selectAvatar(avatar)"
      >
        <image 
          :src="avatar.url || '/static/default-avatar.png'" 
          class="avatar-img"
          mode="aspectFill"
        />
        <view v-if="selectedAvatarId === avatar.id" class="selected-badge">
          <text class="check-icon">✓</text>
        </view>
      </view>
    </view>
    
    <view class="footer">
      <button class="nb-primary-btn confirm-btn" @click="confirmSelect" :disabled="loading">
        {{ loading ? '保存中...' : '确认选择' }}
      </button>
    </view>
  </view>
</template>

<script>
import { getAllAvatars } from '@/utils/avatars'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbNetworkBanner },
  data() {
    return {
      avatars: [],
      selectedAvatarId: null,
      currentAvatarUrl: '',
      loading: false,
      target: 'user', // user | baby
      babyId: null
    }
  },
  
  onLoad(options) {
    this.target = options?.target === 'baby' ? 'baby' : 'user'
    if (this.target === 'baby') {
      this.babyId = options?.babyId || null
    }
    this.loadAvatars()
    this.loadCurrentAvatar()
  },
  
  methods: {
    loadAvatars() {
      this.avatars = getAllAvatars()
    },
    
    async loadCurrentAvatar() {
      const userStore = useUserStore()
      if (this.target === 'baby') {
        const storeBaby = userStore.currentBaby
        const storeBabyId = storeBaby?.id ? String(storeBaby.id) : ''
        const routeBabyId = this.babyId ? String(this.babyId) : ''

        // 优先使用 store 里的宝宝
        if (storeBaby && storeBaby.avatar_url && (!routeBabyId || routeBabyId === storeBabyId)) {
          this.currentAvatarUrl = storeBaby.avatar_url
        } else if (routeBabyId) {
          // 兜底：从后端读取宝宝信息（避免 store 未初始化导致空白）
          try {
            const res = await api.get(`/babies/${routeBabyId}`)
            this.currentAvatarUrl = res?.baby?.avatar_url || ''
          } catch {
            this.currentAvatarUrl = ''
          }
        }

        const currentAvatar = this.avatars.find(avatar => avatar.url === this.currentAvatarUrl)
        if (currentAvatar) this.selectedAvatarId = currentAvatar.id
        return
      }

      // user
      if (userStore.user && userStore.user.avatar_url) {
        this.currentAvatarUrl = userStore.user.avatar_url
        const currentAvatar = this.avatars.find(avatar => avatar.url === userStore.user.avatar_url)
        if (currentAvatar) this.selectedAvatarId = currentAvatar.id
      }
    },
    
    selectAvatar(avatar) {
      this.selectedAvatarId = avatar.id
    },
    
    async confirmSelect() {
      if (!this.selectedAvatarId) {
        uni.showToast({
          title: '请选择一个头像',
          icon: 'none'
        })
        return
      }
      
      const selectedAvatar = this.avatars.find(avatar => avatar.id === this.selectedAvatarId)
      if (!selectedAvatar) {
        return
      }
      
      this.loading = true
      
      try {
        const userStore = useUserStore()
        if (this.target === 'baby') {
          const babyId = this.babyId || userStore.currentBaby?.id
          if (!babyId) {
            throw new Error('缺少 babyId')
          }
          const res = await api.put(`/babies/${babyId}`, {
            avatar_url: selectedAvatar.url
          })
          // 同步 store（仅当更新的是当前宝宝）
          if (userStore.currentBaby?.id && String(userStore.currentBaby.id) === String(babyId)) {
            userStore.setCurrentBaby(res.baby)
          }
        } else {
          await userStore.updateAvatar(selectedAvatar.url)
        }
        
        uni.showToast({
          title: this.target === 'baby' ? '宝宝头像更新成功' : '头像更新成功',
          icon: 'success'
        })
        
        setTimeout(() => {
          this.goBack()
        }, 500)
      } catch (error) {
        console.error('更新头像失败:', error)
        uni.showToast({
          title: error.message || '更新头像失败',
          icon: 'none'
        })
      } finally {
        this.loading = false
      }
    },
    
    goBack() {
      uni.navigateBack()
    }
  }
}
</script>

<style scoped>
.avatar-select-container {
  min-height: 100vh;
  background-color: transparent;
  padding-bottom: calc(110px + env(safe-area-inset-bottom, 0px));
}

.header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top, 0px));
  background-color: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid rgba(27, 26, 23, 0.10);
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.back-icon {
  font-size: 32px;
  color: #333;
  line-height: 1;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.placeholder {
  width: 40px;
}

.current-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 20px;
  background-color: rgba(255, 255, 255, 0.92);
  margin: 16px;
  border-radius: 18px;
  border: 1px solid rgba(27, 26, 23, 0.10);
}

.current-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 16px;
}

.current-avatar-wrapper {
  width: 100px;
  height: 100px;
  border-radius: 50px;
  overflow: hidden;
  border: 3px solid var(--nb-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.current-avatar {
  width: 100%;
  height: 100%;
}

.avatars-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: space-between;
  padding: 16px;
  margin: 0 16px;
  background-color: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(27, 26, 23, 0.10);
}

.avatar-item {
  position: relative;
  width: 31%;
  padding-top: 31%;
  border-radius: 14px;
  overflow: hidden;
  border: 3px solid transparent;
  cursor: pointer;
}

.avatar-item:active {
  transform: scale(0.95);
}

.avatar-item.selected {
  border-color: var(--nb-accent);
  box-shadow: 0 4px 12px rgba(247, 201, 72, 0.22);
}

.avatar-img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.selected-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 14px;
  background-color: var(--nb-accent-2);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.check-icon {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  line-height: 1;
}

.footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 14px 16px;
  padding-bottom: calc(14px + env(safe-area-inset-bottom, 0px));
  background-color: rgba(255, 255, 255, 0.92);
  border-top: 1px solid rgba(27, 26, 23, 0.10);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
}

.confirm-btn {
  height: 50px;
  font-size: 18px;
}

.confirm-btn[disabled] {
  background: rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.45);
}
</style>
