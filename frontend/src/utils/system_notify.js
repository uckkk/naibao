// 系统级通知（H5 Web Notification）能力封装。
// 目标：让“喂奶提醒”在应用退到后台时也能弹出系统通知（受浏览器/系统限制）。
//
// 注意：
// - iOS：系统通知通常仅对“添加到主屏幕”的 WebApp(PWA)可用；Safari 里可能无法开启/接收。
// - Web 无法稳定做到“应用完全关闭后仍准时提醒”（需要 Push + Service Worker）。

const ENABLE_KEY = 'nb_system_notify_enabled_v1'

function hasUni() {
  // eslint-disable-next-line no-undef
  return typeof uni !== 'undefined'
}

function isH5Runtime() {
  return typeof window !== 'undefined' && typeof document !== 'undefined'
}

export function isNotificationSupported() {
  return isH5Runtime() && typeof window.Notification !== 'undefined'
}

export function getNotificationPermission() {
  if (!isNotificationSupported()) return 'unsupported'
  try {
    return window.Notification.permission || 'default'
  } catch {
    return 'default'
  }
}

export async function requestNotificationPermission() {
  if (!isNotificationSupported()) return 'unsupported'
  try {
    // 需要用户手势触发（点击开关/按钮）
    const v = await window.Notification.requestPermission()
    return v || getNotificationPermission()
  } catch {
    return getNotificationPermission()
  }
}

export function getSystemNotifyEnabled() {
  try {
    if (!hasUni()) return false
    // eslint-disable-next-line no-undef
    return String(uni.getStorageSync(ENABLE_KEY) || '') === '1'
  } catch {
    return false
  }
}

export function setSystemNotifyEnabled(enabled) {
  try {
    if (!hasUni()) return
    // eslint-disable-next-line no-undef
    uni.setStorageSync(ENABLE_KEY, enabled ? '1' : '')
  } catch {}
}

export function isPageHidden() {
  if (!isH5Runtime()) return false
  try {
    return document.visibilityState === 'hidden'
  } catch {
    return false
  }
}

export function isStandalonePwa() {
  if (!isH5Runtime()) return false
  try {
    // iOS Safari: navigator.standalone
    if (typeof window.navigator !== 'undefined' && window.navigator.standalone) return true
  } catch {}
  try {
    // 其他浏览器
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) return true
  } catch {}
  return false
}

export function canUseSystemNotify() {
  return getSystemNotifyEnabled() && getNotificationPermission() === 'granted'
}

export function sendSystemNotify(title, options = {}) {
  if (!canUseSystemNotify()) return null
  if (!isNotificationSupported()) return null
  const t = String(title || '').trim()
  if (!t) return null
  try {
    return new window.Notification(t, options)
  } catch {
    return null
  }
}

