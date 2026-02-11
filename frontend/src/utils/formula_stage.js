// 统一“奶粉段数/适用月龄段”的解析与展示，避免各页面口径不一致。

export function parseAgeRangeMonths(ageRange) {
  const s = String(ageRange || '').trim()
  if (!s) return null

  // 0-6 / 6-12 / 12-36
  const m = s.match(/(\d+)\s*-\s*(\d+)/)
  if (m) {
    const min = Number(m[1])
    const max = Number(m[2])
    if (!Number.isFinite(min) || !Number.isFinite(max)) return null
    return { min: Math.min(min, max), max: Math.max(min, max) }
  }

  // 3+ / 3岁+
  const p = s.match(/(\d+)\s*(?:\+|岁\+|岁以上|月\+|月以上)/)
  if (p) {
    const min = Number(p[1])
    if (!Number.isFinite(min)) return null
    return { min, max: null }
  }

  return null
}

export function parseAgeRangeToStage(ageRange) {
  const r = parseAgeRangeMonths(ageRange)
  if (!r) return 0
  const min = Number(r.min)
  if (!Number.isFinite(min) || min < 0) return 0

  // 经验映射（对国内常见“1段/2段/3段/4段”足够稳定）
  if (min < 6) return 1
  if (min < 12) return 2
  if (min < 36) return 3
  return 4
}

export function formatStageTextFromAgeRange(ageRange) {
  const stage = parseAgeRangeToStage(ageRange)
  return stage > 0 ? `${stage}段` : ''
}

