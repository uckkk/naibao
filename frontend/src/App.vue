<script>
export default {
  onLaunch() {
    // 如存在 token：直接进入首页，减少“每次都看到登录页”的摩擦。
    // token 过期会在 API 层 401 时自动清理并回到登录页。
    try {
      const token = uni.getStorageSync('token')
      if (token) {
        uni.reLaunch({ url: '/pages/home/index' })
      }
    } catch {
      // 忽略：低端机/隐私模式可能读取 storage 失败
    }
  },
  onShow() {},
  onHide() {},
}
</script>

<style>
/* 全局设计基线：偏“奶油/焦糖”氛围，避免默认紫色渐变与平台割裂 */
page {
  /* 轻纹理背景：H5 友好，低成本提升质感 */
  background:
    radial-gradient(1200px 600px at 20% -10%, rgba(255, 216, 136, 0.35), rgba(255, 216, 136, 0) 60%),
    radial-gradient(900px 500px at 90% 0%, rgba(255, 155, 92, 0.22), rgba(255, 155, 92, 0) 55%),
    #fffaf2;
  color: #1b1a17;
  font-family: "PingFang SC", "HarmonyOS Sans SC", "Source Han Sans SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 轻量 tokens（以 H5/小程序主流内核为目标） */
page {
  --nb-surface: #ffffff;
  --nb-text: #1b1a17;
  --nb-muted: rgba(27, 26, 23, 0.62);
  --nb-border: rgba(27, 26, 23, 0.10);
  --nb-accent: #f7c948; /* 焦糖黄 */
  --nb-accent-2: #ff8a3d; /* 奶橙 */
  --nb-danger: #e24a3b;
  --nb-radius-lg: 22px;
  --nb-radius-md: 16px;
  --nb-radius-sm: 12px;
  --nb-safe-top: env(safe-area-inset-top, 0px);
  --nb-safe-bottom: env(safe-area-inset-bottom, 0px);
  --nb-page-x: 16px;
}

/* 轻量全局样式：表单/按钮/卡片统一，降低页面重复与端差异 */
.nb-screen {
  min-height: 100vh;
  padding:
    calc(28px + env(safe-area-inset-top, 0px))
    20px
    calc(28px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.nb-hero {
  text-align: center;
  margin-bottom: 22px;
}

.nb-logo {
  font-size: 72px;
  display: block;
  margin-bottom: 10px;
}

.nb-app-name {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 1px;
  color: var(--nb-text);
  display: block;
}

.nb-app-desc {
  font-size: 14px;
  color: var(--nb-muted);
  display: block;
  margin-top: 8px;
}

.nb-card {
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 22px;
  box-sizing: border-box;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.10);
}

.nb-field {
  margin-bottom: 14px;
}

.nb-input {
  width: 100%;
  height: 48px;
  background: #fff;
  border-radius: 14px;
  padding: 0 14px;
  font-size: 16px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  box-sizing: border-box;
}

.nb-input:focus {
  outline: none;
  border-color: var(--nb-accent);
  box-shadow: 0 0 0 4px rgba(247, 201, 72, 0.22);
}

.nb-input::placeholder {
  color: rgba(27, 26, 23, 0.42);
}

.nb-primary-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
  border-radius: 24px;
  font-size: 16px;
  font-weight: 700;
  border: none;
}

.nb-primary-btn:active:not([disabled]) {
  transform: scale(0.99);
}

.nb-primary-btn[disabled] {
  background: rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.45);
}

.nb-link {
  margin-top: 14px;
  text-align: center;
  user-select: none;
  color: var(--nb-muted);
  font-size: 14px;
}

.nb-link-accent {
  color: var(--nb-text);
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 4px;
}
</style>
