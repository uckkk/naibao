import { defineStore } from 'pinia'
import api from '@/utils/api'
import { getRandomAvatar } from '@/utils/avatars'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: uni.getStorageSync('token') || '',
    user: uni.getStorageSync('user') || null,
    currentBaby: uni.getStorageSync('currentBaby') || null
  }),
  
  getters: {
    isLoggedIn: (state) => !!state.token,
    hasBaby: (state) => !!state.currentBaby
  },
  
  actions: {
    async login(phone, password) {
      try {
        // 确保 phone 是字符串类型（因为 input type="number" 会返回数字）
        const res = await api.post('/public/login', { 
          phone: String(phone || ''), 
          password 
        })
        this.token = res.token
        this.user = res.user
        uni.setStorageSync('token', res.token)
        uni.setStorageSync('user', res.user)
        return res
      } catch (error) {
        throw error
      }
    },
    
    async register(phone, password, nickname) {
      try {
        // 随机选择一个默认头像
        const randomAvatar = getRandomAvatar()
        
        // 确保 phone 是字符串类型（因为 input type="number" 会返回数字）
        const res = await api.post('/public/register', { 
          phone: String(phone || ''), 
          password, 
          nickname,
          avatar_url: randomAvatar.url
        })
        this.token = res.token
        this.user = res.user
        uni.setStorageSync('token', res.token)
        uni.setStorageSync('user', res.user)
        return res
      } catch (error) {
        throw error
      }
    },
    
    async updateAvatar(avatarUrl) {
      try {
        const res = await api.put('/user/avatar', {
          avatar_url: avatarUrl
        })
        this.user = res.user
        uni.setStorageSync('user', res.user)
        return res
      } catch (error) {
        throw error
      }
    },
    
    async getProfile() {
      try {
        const res = await api.get('/user/profile')
        this.user = res.user
        return res.user
      } catch (error) {
        throw error
      }
    },
    
    logout() {
      this.token = ''
      this.user = null
      this.currentBaby = null
      uni.removeStorageSync('token')
      uni.removeStorageSync('user')
      uni.reLaunch({
        url: '/pages/login/index'
      })
    },
    
    setCurrentBaby(baby) {
      this.currentBaby = baby
      uni.setStorageSync('currentBaby', baby)
    }
  }
})
