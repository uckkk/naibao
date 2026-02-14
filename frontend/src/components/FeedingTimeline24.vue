<template>
  <view class="ft24" @click="emitOpen">
    <view class="ft24-track">
      <view class="ft24-line"></view>

      <view
        v-if="showNow && nowPercent !== ''"
        class="ft24-now"
        :style="{ left: nowPercent + '%' }"
        aria-hidden="true"
      >
        <view class="ft24-now-line"></view>
        <view class="ft24-now-dot"></view>
      </view>

      <view
        v-if="showNext && nextPercent !== ''"
        class="ft24-next"
        :style="{ left: nextPercent + '%' }"
        aria-hidden="true"
      >
        <view class="ft24-dot next"></view>
      </view>

      <view
        v-for="m in safeMarks"
        :key="m.key"
        class="ft24-mark"
        :style="{
          left: m.leftPercent + '%',
          zIndex: m.zIndex,
          '--ft24-shift-y': (m.shiftY || 0) + 'px',
        }"
      >
        <view
          class="ft24-dot"
          :class="{ active: selectedKey === String(m.key), latest: !!m.isLatest, plan: m.kind === 'plan' }"
          @click.stop="handleMarkTap(m)"
        ></view>
        <view
          v-if="m.kind !== 'plan' && Number(m.count || 0) > 1"
          class="ft24-badge"
          @click.stop="handleMarkTap(m)"
        >
          <text class="ft24-badge-text">{{ Number(m.count || 0) }}</text>
        </view>
      </view>
    </view>

    <view v-if="showAxis" class="ft24-axis" aria-hidden="true">
      <text class="axis-item">0</text>
      <text class="axis-item">6</text>
      <text class="axis-item">12</text>
      <text class="axis-item">18</text>
      <text class="axis-item">24</text>
    </view>

    <view v-if="selectedMark" class="ft24-callout" @click.stop>
      <view class="ft24-callout-card">
        <view v-for="it in selectedMark.items || []" :key="it.key" class="ft24-row">
          <text class="ft24-time">{{ it.timeText }}</text>
          <text class="ft24-amount">{{ it.amountText }}</text>
          <view v-if="it.tagText" class="ft24-tag" :class="it.tagText === '新' ? 'new' : 'old'">
            <text class="ft24-tag-text">{{ it.tagText }}</text>
          </view>
          <text v-if="it.userText" class="ft24-user">{{ it.userText }}</text>
        </view>
      </view>
    </view>

    <view v-if="metaVisible" class="ft24-meta" aria-hidden="true">
      <text v-if="summaryText" class="ft24-meta-left">{{ summaryText }}</text>
      <text v-if="latestText" class="ft24-meta-right">最近 {{ latestText }}</text>
    </view>

    <view v-if="legendVisible" class="ft24-legend" @click.stop>
      <view class="ft24-legend-items" aria-hidden="true">
        <view class="ft24-legend-item">
          <view class="ft24-legend-dot solid"></view>
          <text class="ft24-legend-label">记录</text>
        </view>
        <view class="ft24-legend-item">
          <view class="ft24-legend-dot hollow"></view>
          <text class="ft24-legend-label">下次</text>
        </view>
        <view v-if="hasPlanMarks" class="ft24-legend-item">
          <view class="ft24-legend-dot plan"></view>
          <text class="ft24-legend-label">预估</text>
        </view>
        <view class="ft24-legend-item">
          <view class="ft24-legend-now">
            <view class="ft24-legend-now-line"></view>
            <view class="ft24-legend-now-dot"></view>
          </view>
          <text class="ft24-legend-label">现在</text>
        </view>
      </view>
      <text class="ft24-legend-close" @click.stop="closeLegend">×</text>
    </view>
  </view>
</template>

<script>
const LEGEND_KEY = 'nb_timeline_legend_v1'

function clampPct(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return ''
  const c = Math.max(0, Math.min(100, n))
  return c.toFixed(2)
}

function msToPercent(ms) {
  const t = Number(ms || 0)
  if (!Number.isFinite(t) || t <= 0) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return ''
  const minutes = d.getHours() * 60 + d.getMinutes()
  return clampPct((minutes / 1440) * 100)
}

export default {
  name: 'FeedingTimeline24',
  props: {
    marks: { type: Array, default: () => [] },
    selectedKey: { type: String, default: '' },
    nowMs: { type: Number, default: 0 },
    nextMs: { type: Number, default: 0 },
    summaryText: { type: String, default: '' },
    latestText: { type: String, default: '' },
    showAxis: { type: Boolean, default: true },
    showNow: { type: Boolean, default: true },
    showNext: { type: Boolean, default: true },
    showLegendOnce: { type: Boolean, default: true },
  },
  emits: ['select', 'open'],
  data() {
    return {
      legendVisible: false,
    }
  },
  computed: {
    safeMarks() {
      const list = Array.isArray(this.marks) ? this.marks : []
      const normalized = list
        .map((m) => ({
          ...m,
          key: m?.key != null ? String(m.key) : '',
          leftPercent: clampPct(m?.leftPercent),
          count: Number(m?.count || 0),
          kind: String(m?.kind || ''),
        }))
        .filter((m) => m.key && m.leftPercent !== '')

      // 极端频繁记录时，多个点位会在视觉上重叠：这里做“轻量避让”，通过纵向分层提高可读性/可点性。
      normalized.sort((a, b) => Number(a.leftPercent) - Number(b.leftPercent))
      const thresholdPct = 2.7 // ~40min on 24h axis
      const laneLastLeft = [-999, -999, -999]
      const laneShiftY = [0, -8, 8]
      const selected = String(this.selectedKey || '')

      return normalized.map((m) => {
        const left = Number(m.leftPercent)
        let lane = 0
        for (let i = 0; i < laneLastLeft.length; i++) {
          if (left - laneLastLeft[i] >= thresholdPct) {
            lane = i
            break
          }
          lane = i + 1
        }
        if (lane >= laneLastLeft.length) lane = laneLastLeft.length - 1
        laneLastLeft[lane] = left

        const isSelected = selected && String(m.key) === selected
        const baseZ = m.kind === 'plan' ? 1 : 2
        const zIndex = baseZ
          + (isSelected ? 10 : 0)
          + (m.isLatest ? 6 : 0)
          + (lane === 1 ? 2 : lane === 2 ? 1 : 0)

        return {
          ...m,
          lane,
          shiftY: laneShiftY[lane] || 0,
          zIndex,
        }
      })
    },
    nowPercent() {
      return msToPercent(this.nowMs)
    },
    nextPercent() {
      return msToPercent(this.nextMs)
    },
    selectedMark() {
      const key = String(this.selectedKey || '')
      if (!key) return null
      return this.safeMarks.find((m) => String(m.key) === key) || null
    },
    metaVisible() {
      return !!(this.summaryText || this.latestText)
    },
    hasPlanMarks() {
      return (this.safeMarks || []).some((m) => String(m?.kind || '') === 'plan')
    },
  },
  created() {
    if (!this.showLegendOnce) return
    try {
      const v = uni.getStorageSync(LEGEND_KEY)
      if (!v) this.legendVisible = true
    } catch {
      this.legendVisible = true
    }
  },
  methods: {
    emitOpen() {
      this.$emit('open')
    },
    handleMarkTap(m) {
      if (!m || !m.key) return
      if (String(m.kind || '') === 'plan') return
      this.$emit('select', String(m.key))
    },
    closeLegend() {
      this.legendVisible = false
      try {
        uni.setStorageSync(LEGEND_KEY, '1')
      } catch {}
    },
  },
}
</script>

<style scoped>
.ft24 {
  width: 100%;
}

.ft24-track {
  position: relative;
  height: 30px;
}

.ft24-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 14px;
  height: 2px;
  border-radius: 2px;
  background: rgba(27, 26, 23, 0.12);
}

.ft24-now {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0;
  transform: translateX(-50%);
  pointer-events: none;
  z-index: 3;
}

.ft24-now-line {
  position: absolute;
  left: -1px;
  top: 2px;
  bottom: 2px;
  width: 2px;
  border-radius: 1px;
  background: rgba(27, 26, 23, 0.16);
}

.ft24-now-dot {
  position: absolute;
  top: 11px;
  left: 0;
  transform: translateX(-50%);
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.62);
  border: 2px solid rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 24px rgba(27, 26, 23, 0.14);
  box-sizing: border-box;
}

.ft24-next {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 1;
}

.ft24-mark {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 仅让“点/徽标”可点，避免密集点位时容器互相覆盖导致点不到 */
  pointer-events: none;
}

.ft24-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 138, 61, 0.92);
  border: 2px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 6px 14px rgba(27, 26, 23, 0.12);
  transform: translateY(var(--ft24-shift-y, 0px));
  pointer-events: auto;
}

.ft24-dot.active {
  background: rgba(27, 26, 23, 0.92);
}

.ft24-dot.latest {
  border-color: rgba(27, 26, 23, 0.92);
}

.ft24-dot.next {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(27, 26, 23, 0.42);
}

.ft24-dot.plan {
  width: 8px;
  height: 8px;
  background: rgba(255, 255, 255, 0.80);
  border-color: rgba(27, 26, 23, 0.22);
  box-shadow: none;
  pointer-events: none;
}

.ft24-badge {
  position: absolute;
  top: -2px;
  right: 2px;
  min-width: 14px;
  height: 14px;
  padding: 0 4px;
  border-radius: 8px;
  background: rgba(27, 26, 23, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px rgba(27, 26, 23, 0.16);
  box-sizing: border-box;
  transform: translateY(var(--ft24-shift-y, 0px));
  pointer-events: auto;
}

.ft24-badge-text {
  font-size: 10px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.92);
  line-height: 1;
}

.ft24-axis {
  margin-top: 8px;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}

.ft24-axis .axis-item {
  font-size: 11px;
  color: rgba(27, 26, 23, 0.48);
}

.ft24-callout {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ft24-callout-card {
  width: 100%;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(27, 26, 23, 0.10);
  padding: 10px 12px;
  box-sizing: border-box;
  box-shadow: 0 10px 28px rgba(27, 26, 23, 0.10);
}

.ft24-row {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 10px;
  padding: 2px 0;
}

.ft24-time {
  width: 46px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
  font-family: 'Courier New', monospace;
  white-space: nowrap;
}

.ft24-amount {
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.88);
  white-space: nowrap;
}

.ft24-tag {
  padding: 2px 6px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(27, 26, 23, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.ft24-tag.new {
  background: rgba(247, 201, 72, 0.18);
  border-color: rgba(247, 201, 72, 0.26);
}

.ft24-tag-text {
  font-size: 10px;
  font-weight: 1000;
  color: rgba(27, 26, 23, 0.70);
}

.ft24-user {
  margin-left: auto;
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ft24-meta {
  margin-top: 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ft24-meta-left,
.ft24-meta-right {
  font-size: 12px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.65);
  white-space: nowrap;
}

.ft24-meta-right {
  max-width: 56%;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: right;
}

.ft24-legend {
  margin-top: 10px;
  border-radius: 14px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(255, 255, 255, 0.84);
  padding: 10px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  box-shadow: 0 12px 34px rgba(27, 26, 23, 0.10);
  box-sizing: border-box;
}

.ft24-legend-items {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.ft24-legend-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.ft24-legend-label {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.70);
  font-weight: 800;
  white-space: nowrap;
}

.ft24-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-sizing: border-box;
}

.ft24-legend-dot.solid {
  background: rgba(255, 138, 61, 0.92);
  border: 2px solid rgba(255, 255, 255, 0.92);
}

.ft24-legend-dot.hollow {
  background: rgba(255, 255, 255, 0.92);
  border: 2px solid rgba(27, 26, 23, 0.42);
}

.ft24-legend-dot.plan {
  background: rgba(255, 255, 255, 0.80);
  border: 2px solid rgba(27, 26, 23, 0.22);
}

.ft24-legend-now {
  position: relative;
  width: 10px;
  height: 14px;
}

.ft24-legend-now-line {
  position: absolute;
  left: 4px;
  top: 0;
  bottom: 0;
  width: 2px;
  border-radius: 1px;
  background: rgba(27, 26, 23, 0.16);
}

.ft24-legend-now-dot {
  position: absolute;
  top: 4px;
  left: 5px;
  transform: translateX(-50%);
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(27, 26, 23, 0.62);
  border: 2px solid rgba(255, 255, 255, 0.96);
  box-sizing: border-box;
}

.ft24-legend-close {
  font-size: 18px;
  color: rgba(27, 26, 23, 0.45);
  font-weight: 900;
  line-height: 1;
  user-select: none;
}
</style>
