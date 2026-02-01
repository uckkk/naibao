import { parseBirthDateToLocal } from './age'

// 星座（西方星座）- 用于宝宝资料展示，减少“记忆负担”
const SIGNS = [
  { name: '摩羯座', from: [12, 22], to: [1, 19] },
  { name: '水瓶座', from: [1, 20], to: [2, 18] },
  { name: '双鱼座', from: [2, 19], to: [3, 20] },
  { name: '白羊座', from: [3, 21], to: [4, 19] },
  { name: '金牛座', from: [4, 20], to: [5, 20] },
  { name: '双子座', from: [5, 21], to: [6, 21] },
  { name: '巨蟹座', from: [6, 22], to: [7, 22] },
  { name: '狮子座', from: [7, 23], to: [8, 22] },
  { name: '处女座', from: [8, 23], to: [9, 22] },
  { name: '天秤座', from: [9, 23], to: [10, 23] },
  { name: '天蝎座', from: [10, 24], to: [11, 22] },
  { name: '射手座', from: [11, 23], to: [12, 21] },
]

function isAfterOrEqual(month, day, startMonth, startDay) {
  if (month !== startMonth) return month > startMonth
  return day >= startDay
}

function isBeforeOrEqual(month, day, endMonth, endDay) {
  if (month !== endMonth) return month < endMonth
  return day <= endDay
}

export function formatZodiacText(birthDateInput) {
  const dt = parseBirthDateToLocal(birthDateInput)
  if (!dt) return ''

  const month = dt.getMonth() + 1
  const day = dt.getDate()
  if (!Number.isFinite(month) || !Number.isFinite(day)) return ''

  for (const s of SIGNS) {
    const [fm, fd] = s.from
    const [tm, td] = s.to
    // 跨年区间（摩羯座）
    if (fm > tm) {
      if (isAfterOrEqual(month, day, fm, fd) || isBeforeOrEqual(month, day, tm, td)) return s.name
      continue
    }
    if (isAfterOrEqual(month, day, fm, fd) && isBeforeOrEqual(month, day, tm, td)) return s.name
  }

  return ''
}

