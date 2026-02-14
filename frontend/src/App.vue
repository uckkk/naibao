<script>
export default {
  onLaunch() {
    // 全局收敛：避免 401 跳转登录时，各页面 catch 里反复 toast 出“无意义错误”。
    // 真正的提示在登录页一次性展示（更像一个产品，而不是一堆页面各说各话）。
    try {
      if (!uni.__nb_toast_patched && typeof uni.showToast === 'function') {
        const original = uni.showToast.bind(uni)
        uni.showToast = (opts = {}) => {
          try {
            const title = typeof opts === 'string' ? opts : opts?.title
            if (title === '__NB_AUTH_REDIRECT__' || title === '未登录或登录已过期') return
          } catch {}
          return original(opts)
        }
        uni.__nb_toast_patched = true
      }
    } catch {}

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

    // 全站弱网/错误交互收敛：NetworkBanner 的“重试”触发当前页面的 onNbRetry()（若存在）
    // 这样每个页面只需实现一个方法即可复用一致的交互入口。
    try {
      if (!uni.__nb_net_retry_hooked && typeof uni.$on === 'function') {
        uni.$on('nb:network:retry', () => {
          try {
            if (typeof getCurrentPages !== 'function') return
            const pages = getCurrentPages() || []
            const last = pages[pages.length - 1]
            const vm = last && (last.$vm || last)
            if (vm && typeof vm.onNbRetry === 'function') vm.onNbRetry()
          } catch {
            // ignore
          }
        })
        uni.__nb_net_retry_hooked = true
      }
    } catch {
      // ignore
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
    /* 顶部轻压暗：配合 iOS 主屏幕 black-translucent 状态栏，提升白色状态栏图标可读性 */
    linear-gradient(180deg, rgba(27, 26, 23, 0.12) 0%, rgba(27, 26, 23, 0) 140px),
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
  --nb-ink-rgb: 27, 26, 23;

  --nb-muted: rgba(var(--nb-ink-rgb), 0.62);
  --nb-muted-2: rgba(var(--nb-ink-rgb), 0.55);
  --nb-muted-3: rgba(var(--nb-ink-rgb), 0.45);
  --nb-faint: rgba(var(--nb-ink-rgb), 0.35);

  --nb-line: rgba(var(--nb-ink-rgb), 0.08);
  --nb-border: rgba(var(--nb-ink-rgb), 0.10);
  --nb-border-2: rgba(var(--nb-ink-rgb), 0.12);
  --nb-fill: rgba(var(--nb-ink-rgb), 0.06);
  --nb-fill-2: rgba(var(--nb-ink-rgb), 0.03);

  --nb-card-bg: rgba(255, 255, 255, 0.92);
  --nb-card-bg-2: rgba(255, 255, 255, 0.82);
  --nb-card-bg-soft: rgba(255, 255, 255, 0.86);
  --nb-shadow-card: 0 18px 50px rgba(var(--nb-ink-rgb), 0.08);
  --nb-shadow-card-strong: 0 18px 50px rgba(var(--nb-ink-rgb), 0.12);
  --nb-shadow-card-weak: 0 14px 34px rgba(var(--nb-ink-rgb), 0.05);
  --nb-shadow-float: 0 10px 24px rgba(var(--nb-ink-rgb), 0.10);
  --nb-ring: 0 0 0 4px rgba(247, 201, 72, 0.22);

  --nb-accent: #f7c948; /* 焦糖黄 */
  --nb-accent-2: #ff8a3d; /* 奶橙 */
  --nb-danger: #e24a3b;
  --nb-radius-lg: 22px;
  --nb-radius-md: 16px;
  --nb-radius-sm: 12px;
  --nb-safe-top: env(safe-area-inset-top, 0px);
  --nb-safe-bottom: env(safe-area-inset-bottom, 0px);
  --nb-page-x: 16px;
  /* 内容最大宽度（iPad/桌面 H5 时避免卡片过窄） */
  --nb-content-max: 680px;
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
  background: var(--nb-card-bg);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 22px;
  box-sizing: border-box;
  box-shadow: 0 18px 50px rgba(var(--nb-ink-rgb), 0.10);
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
  border: 2px solid var(--nb-border);
  box-sizing: border-box;
}

.nb-input:focus {
  outline: none;
  border-color: var(--nb-accent);
  box-shadow: var(--nb-ring);
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
  background: rgba(var(--nb-ink-rgb), 0.12);
  color: var(--nb-muted-3);
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
