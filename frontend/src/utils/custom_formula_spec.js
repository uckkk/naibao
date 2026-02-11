// 自定义冲泡规格（v1：仅本机存储）。
// 目标：当官方没有规格数据时，依然能给出“勺数/水温/步骤”的可用体验。
//
// 设计原则：
// - 仅用于“补齐缺失字段”，默认不覆盖官方值（降低错误风险）。
// - key 绑定到 baby + brand + series + age_range，避免不同段位/系列串用。

const PREFIX = 'nb_custom_formula_spec_v1:'

function hasUni() {
  // eslint-disable-next-line no-undef
  return typeof uni !== 'undefined'
}

function safeEnc(v) {
  try {
    return encodeURIComponent(String(v ?? '').trim())
  } catch {
    return ''
  }
}

export function buildCustomFormulaSpecKey({ babyId, brandId, seriesName, ageRange }) {
  const bid = String(babyId ?? '').trim()
  const br = String(brandId ?? '').trim()
  const s = safeEnc(seriesName)
  const r = safeEnc(ageRange)
  if (!bid || !br) return ''
  return `${PREFIX}${bid}:${br}:${s}:${r}`
}

export function readCustomFormulaSpec(key) {
  const k = String(key || '').trim()
  if (!k || !hasUni()) return null
  try {
    // eslint-disable-next-line no-undef
    const raw = uni.getStorageSync(k)
    if (!raw) return null
    const obj = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!obj || typeof obj !== 'object') return null

    const scoopMl = Number(obj.scoop_ml || 0)
    const waterMin = Number(obj.water_temp_min || 0)
    const waterMax = Number(obj.water_temp_max || 0)
    const mixing = String(obj.mixing_method || '').trim()

    const out = {
      scoop_ml: Number.isFinite(scoopMl) && scoopMl > 0 ? Math.round(scoopMl) : 0,
      water_temp_min: Number.isFinite(waterMin) && waterMin > 0 ? Math.round(waterMin) : 0,
      water_temp_max: Number.isFinite(waterMax) && waterMax > 0 ? Math.round(waterMax) : 0,
      mixing_method: mixing,
      updated_at: obj.updated_at ? String(obj.updated_at) : '',
      _source: 'custom_local',
    }

    // 空对象视为无效
    const hasAny = out.scoop_ml > 0 || out.water_temp_min > 0 || out.water_temp_max > 0 || !!out.mixing_method
    return hasAny ? out : null
  } catch {
    return null
  }
}

export function writeCustomFormulaSpec(key, spec) {
  const k = String(key || '').trim()
  if (!k || !hasUni()) return false
  const s = spec || {}
  const payload = {
    scoop_ml: Number(s.scoop_ml || 0),
    water_temp_min: Number(s.water_temp_min || 0),
    water_temp_max: Number(s.water_temp_max || 0),
    mixing_method: String(s.mixing_method || '').trim(),
    updated_at: new Date().toISOString(),
  }
  try {
    // eslint-disable-next-line no-undef
    uni.setStorageSync(k, JSON.stringify(payload))
    return true
  } catch {
    return false
  }
}

export function clearCustomFormulaSpec(key) {
  const k = String(key || '').trim()
  if (!k || !hasUni()) return false
  try {
    // eslint-disable-next-line no-undef
    uni.removeStorageSync(k)
    return true
  } catch {
    return false
  }
}

export function applyCustomSpecIfMissing(official, custom) {
  const o = official && typeof official === 'object' ? { ...official } : null
  const c = custom && typeof custom === 'object' ? custom : null
  if (!o && !c) return { spec: null, usedCustom: false }
  if (!o && c) return { spec: { ...c }, usedCustom: true }

  let used = false
  const out = { ...o }

  const oScoop = Number(out.scoop_ml || 0)
  const cScoop = Number(c?.scoop_ml || 0)
  if (!(Number.isFinite(oScoop) && oScoop > 0) && Number.isFinite(cScoop) && cScoop > 0) {
    out.scoop_ml = Math.round(cScoop)
    used = true
  }

  const oMin = Number(out.water_temp_min || 0)
  const oMax = Number(out.water_temp_max || 0)
  const cMin = Number(c?.water_temp_min || 0)
  const cMax = Number(c?.water_temp_max || 0)
  if (!(Number.isFinite(oMin) && oMin > 0) && Number.isFinite(cMin) && cMin > 0) {
    out.water_temp_min = Math.round(cMin)
    used = true
  }
  if (!(Number.isFinite(oMax) && oMax > 0) && Number.isFinite(cMax) && cMax > 0) {
    out.water_temp_max = Math.round(cMax)
    used = true
  }

  const oMix = String(out.mixing_method || '').trim()
  const cMix = String(c?.mixing_method || '').trim()
  if (!oMix && cMix) {
    out.mixing_method = cMix
    used = true
  }

  return { spec: out, usedCustom: used }
}
