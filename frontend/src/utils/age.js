// 统一“宝宝年龄”相关展示与计算，避免各页面口径不一致。

export function parseBirthDateToLocal(dateInput) {
  if (!dateInput) return null
  const s = String(dateInput).trim()
  // 优先按 YYYY-MM-DD 解析，避免 Safari/小程序对 Date.parse 的差异。
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (m) {
    const y = Number(m[1])
    const mo = Number(m[2])
    const d = Number(m[3])
    return new Date(y, mo - 1, d)
  }
  const dt = new Date(s)
  return Number.isNaN(dt.getTime()) ? null : dt
}

export function calcAgeInDays(birthDateInput, now = new Date()) {
  const birth = parseBirthDateToLocal(birthDateInput)
  if (!birth) return 0
  const diff = now.getTime() - birth.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  return Math.max(0, days)
}

export function diffYmd(from, to) {
  // 计算日历意义上的年/月/天差：用于展示“X年X月X天 / X月X天”
  let y = to.getFullYear() - from.getFullYear()
  let m = to.getMonth() - from.getMonth()
  let d = to.getDate() - from.getDate()
  if (d < 0) {
    m -= 1
    const prevMonthEnd = new Date(to.getFullYear(), to.getMonth(), 0)
    d += prevMonthEnd.getDate()
  }
  if (m < 0) {
    y -= 1
    m += 12
  }
  return { years: Math.max(0, y), months: Math.max(0, m), days: Math.max(0, d) }
}

export function formatAgeTextFromDays(daysInput) {
  const totalDays = Math.max(0, Math.floor(Number(daysInput || 0)))
  if (totalDays < 30) return `${totalDays}天`

  if (totalDays >= 365) {
    const years = Math.floor(totalDays / 365)
    const rest = totalDays % 365
    const months = Math.floor(rest / 30)
    const days = rest % 30
    return `${years}年${months}月${days}天`
  }

  const months = Math.floor(totalDays / 30)
  const days = totalDays % 30
  return `${months}月${days}天`
}

export function formatBabyAgeText(birthDateInput, now = new Date()) {
  const birth = parseBirthDateToLocal(birthDateInput)
  if (!birth) return ''

  const totalDays = calcAgeInDays(birthDateInput, now)
  if (totalDays < 30) return `${totalDays}天`

  const { years, months, days } = diffYmd(birth, now)
  if (years >= 1) return `${years}年${months}月${days}天`
  return `${months}月${days}天`
}

