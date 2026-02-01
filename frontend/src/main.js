import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// 使用 uni-app 官方运行时（路由/生命周期/uni.* API），避免 H5 自研 polyfill 带来的端差异与维护成本。
export function createApp() {
  const app = createSSRApp(App)
  const pinia = createPinia()
  app.use(pinia)
  return {
    app,
    pinia,
  }
}
