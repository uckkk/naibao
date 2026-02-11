<template>
  <view class="nb-screen register-screen">
    <NbNetworkBanner />
    <view class="nb-hero hero">
      <text class="nb-logo">🍼</text>
      <text class="nb-app-name">奶宝</text>
      <text class="nb-app-desc">纯奶粉喂养，科学记录</text>
    </view>
    
    <view class="nb-card card">
      <view class="nb-field">
        <input 
          class="nb-input" 
          type="number" 
          placeholder="请输入手机号" 
          v-model="phone"
          maxlength="11"
        />
      </view>

      <view class="nb-field">
        <input 
          class="nb-input" 
          type="text" 
          placeholder="请输入昵称（可选）" 
          v-model="nickname"
          maxlength="20"
        />
      </view>

      <view class="nb-field">
        <input 
          class="nb-input" 
          type="password" 
          placeholder="请输入密码（至少6位）" 
          v-model="password"
        />
      </view>

      <view class="nb-field">
        <input 
          class="nb-input" 
          type="password" 
          placeholder="请再次输入密码" 
          v-model="confirmPassword"
        />
      </view>
      
      <button 
        class="nb-primary-btn register-btn" 
        :disabled="loading || !phone || !password || !confirmPassword"
        @click="handleRegister"
      >
        {{ loading ? '注册中...' : '注册' }}
      </button>
      
      <view class="nb-link" @click="goToLogin">
        已有账号？<text class="nb-link-accent">立即登录</text>
      </view>
    </view>
  </view>
</template>

<script>
import { useUserStore } from '@/stores/user'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbNetworkBanner },
  data() {
    return {
      phone: '',
      nickname: '',
      password: '',
      confirmPassword: '',
      loading: false
    }
  },
  
  onLoad() {
  },
  
  methods: {
    async handleRegister() {
      // 验证手机号
      if (!this.phone) {
        uni.showToast({
          title: '请输入手机号',
          icon: 'none'
        })
        return
      }
      
      if (!/^1[3-9]\d{9}$/.test(this.phone)) {
        uni.showToast({
          title: '请输入正确的手机号',
          icon: 'none'
        })
        return
      }
      
      // 验证密码
      if (!this.password) {
        uni.showToast({
          title: '请输入密码',
          icon: 'none'
        })
        return
      }
      
      if (this.password.length < 6) {
        uni.showToast({
          title: '密码至少6位',
          icon: 'none'
        })
        return
      }
      
      // 验证确认密码
      if (!this.confirmPassword) {
        uni.showToast({
          title: '请再次输入密码',
          icon: 'none'
        })
        return
      }
      
      if (this.password !== this.confirmPassword) {
        uni.showToast({
          title: '两次输入的密码不一致',
          icon: 'none'
        })
        return
      }
      
      this.loading = true
      
      try {
        const userStore = useUserStore()
        await userStore.register(this.phone, this.password, this.nickname || undefined)
        
        uni.showToast({
          title: '注册成功',
          icon: 'success'
        })
        
        // 跳转到首页
        setTimeout(() => {
          uni.reLaunch({
            url: '/pages/home/index'
          })
        }, 500)
      } catch (error) {
        console.error('注册失败:', error)
        
        // 处理不同类型的错误
        let errorMessage = '注册失败，请稍后重试'
        
        if (error) {
          if (typeof error === 'string') {
            errorMessage = error
          } else if (error.message) {
            errorMessage = error.message
          } else if (error.error) {
            errorMessage = error.error
          } else if (error.errMsg) {
            errorMessage = error.errMsg
          }
        }
        
        uni.showToast({
          title: errorMessage,
          icon: 'none',
          duration: 3000
        })
      } finally {
        this.loading = false
      }
    },
    
    goToLogin() {
      uni.navigateBack()
    }
  }
}
</script>

<style scoped>
.hero {
  animation: fadeInDown 0.55s ease-out;
}

.card {
  animation: fadeInUp 0.55s ease-out 0.08s both;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
