<template>
  <view class="nb-screen login-screen">
    <NbNetworkBanner />
    <view class="nb-hero hero">
      <text class="nb-logo">🍼</text>
      <text class="nb-app-name">奶宝</text>
      <text class="nb-app-desc">纯奶粉喂养，科学记录</text>
    </view>

    <!-- 登录提示：仅在“跳转回登录页”时出现，点一下即可关闭 -->
    <view v-if="notice" class="nb-notice" @click="notice = ''">
      <text class="nb-notice-text">{{ notice }}</text>
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
          type="password" 
          placeholder="请输入密码" 
          v-model="password"
        />
      </view>
      
      <button 
        class="nb-primary-btn login-btn" 
        :disabled="loading || !phone || !password"
        @click="handleLogin"
      >
        {{ loading ? '登录中...' : '登录' }}
      </button>
      
      <view class="nb-link" @click="goToRegister">
        还没有账号？<text class="nb-link-accent">立即注册</text>
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
      password: '',
      loading: false,
      notice: ''
    }
  },
  
  onLoad() {
    // 来自 API 401 的一次性提示（登录过期/未登录）
    try {
      const msg = uni.getStorageSync('nb_auth_notice')
      if (msg) {
        this.notice = String(msg)
        uni.removeStorageSync('nb_auth_notice')
      }
    } catch {}
  },
  
  methods: {
    async handleLogin() {
      if (!this.phone || !this.password) {
        uni.showToast({
          title: '请输入手机号和密码',
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
      
      this.loading = true
      
      try {
        const userStore = useUserStore()
        await userStore.login(this.phone, this.password)
        
        uni.showToast({
          title: '登录成功',
          icon: 'success'
        })
        
        // 跳转到首页
        setTimeout(() => {
          uni.reLaunch({
            url: '/pages/home/index'
          })
        }, 500)
      } catch (error) {
        console.error('登录失败:', error)
        
        // 处理不同类型的错误
        let errorMessage = '登录失败，请稍后重试'
        
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
    
    goToRegister() {
      uni.navigateTo({
        url: '/pages/register/index'
      })
    }
  }
}
</script>

<style scoped>
.nb-notice {
  width: 100%;
  max-width: 420px;
  margin: 0 auto 14px;
  padding: 10px 14px;
  box-sizing: border-box;
  border-radius: 14px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  text-align: center;
  user-select: none;
}

.nb-notice-text {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.75);
}

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
