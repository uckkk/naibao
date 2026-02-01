<template>
  <view class="rail">
    <view class="rail-head">
      <view class="brand" @click="$emit('tapBrand')">
        <view class="brand-badge">
          <text class="brand-text">{{ brandBadgeText }}</text>
          <text v-if="stageBadgeText" class="brand-stage">{{ stageBadgeText }}</text>
        </view>
        <view class="brand-meta">
          <text class="brand-name">{{ brandNameText }}</text>
          <text class="brand-sub">{{ brandSubText }}</text>
        </view>
      </view>

      <view class="summary">
        <text class="summary-strong">{{ doneCount }}</text>
        <text class="summary-muted">次</text>
        <text class="summary-dot">·</text>
        <text class="summary-strong">{{ todayAmount }}</text>
        <text class="summary-muted">ml</text>
      </view>
    </view>

    <scroll-view class="rail-track" scroll-x show-scrollbar="false">
      <view class="rail-track-inner">
        <view
          v-for="slot in slots"
          :key="slot.key"
          class="slot"
          :class="{ filled: slot.filled }"
          @click="$emit('tapSlot', slot)"
        >
          <view class="slot-top">
            <image :src="slot.icon" class="bottle" mode="aspectFit" />
            <view v-if="slot.filled" class="pulse"></view>
          </view>

          <view class="slot-bottom">
            <image
              v-if="slot.avatar"
              :src="slot.avatar"
              class="avatar"
              mode="aspectFill"
            />
            <view v-else class="avatar avatar-empty"></view>
            <text class="amount" :class="{ empty: !slot.filled }">
              {{ slot.filled ? slot.amount : '—' }}
            </text>
          </view>
        </view>

        <view v-if="overflowCount > 0" class="more">
          <text class="more-text">+{{ overflowCount }}</text>
        </view>
      </view>
    </scroll-view>

    <view v-if="hintText" class="rail-foot">
      <text class="hint">{{ hintText }}</text>
    </view>
  </view>
</template>

<script>
export default {
  name: 'FeedingRail',
  props: {
    feedings: { type: Array, default: () => [] },
    familyMembers: { type: Array, default: () => [] },
    formula: { type: Object, default: null },
    recommended: { type: Object, default: null },
    scoopsText: { type: String, default: '' },
    stageBadgeText: { type: String, default: '' },
    minSlots: { type: Number, default: 8 },
    maxSlots: { type: Number, default: 12 },
    todayAmount: { type: Number, default: 0 },
  },
  computed: {
    doneCount() {
      return Array.isArray(this.feedings) ? this.feedings.length : 0
    },
    remainingTimes() {
      const v = this.recommended?.remaining_times
      const n = Number(v)
      return Number.isFinite(n) && n > 0 ? n : 0
    },
    targetSlots() {
      const raw = this.doneCount + this.remainingTimes
      const base = Number.isFinite(raw) && raw > 0 ? raw : this.minSlots
      return Math.max(this.minSlots, Math.min(this.maxSlots, base))
    },
    overflowCount() {
      return Math.max(0, this.doneCount - this.targetSlots)
    },
    brandNameText() {
      const b = this.formula?.brand
      const cn = b?.name_cn || this.formula?.brand_name || this.formula?.name_cn
      return cn || '未选奶粉'
    },
    brandBadgeText() {
      const name = String(this.brandNameText || '')
      if (!name) return 'A'
      if (name.toLowerCase().includes('a2')) return 'a2'
      return name.slice(0, 1)
    },
    brandSubText() {
      if (this.scoopsText) return this.scoopsText
      if (this.brandNameText === '未选奶粉') return '点这里选择'
      const range = this.formula?.age_range
      return range ? `适用：${range}` : '已选择'
    },
    hintText() {
      if (this.doneCount > 0) return ''
      return '今天还没有记录，点下方“投喂”开始'
    },
    slots() {
      const feedings = Array.isArray(this.feedings) ? this.feedings : []
      const visible = feedings.slice(0, this.targetSlots)
      const slots = []
      for (let i = 0; i < this.targetSlots; i++) {
        const feeding = visible[i] || null
        const filled = !!feeding
        const amount = filled ? Number(feeding.amount || 0) : 0
        const avatar = filled ? this.resolveAvatarUrl(feeding.user_id) : ''
        slots.push({
          key: `${i}`,
          filled,
          amount,
          avatar,
          icon: filled ? '/static/naiping1.svg' : '/static/naiping0.svg',
          feeding,
        })
      }
      return slots
    },
  },
  methods: {
    resolveAvatarUrl(userId) {
      if (!userId) return '/static/default-avatar.png'
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(userId))
      return (m && m.avatar_url) || '/static/default-avatar.png'
    },
  },
}
</script>

<style scoped>
.rail {
  margin: 10px 20px 0;
  padding: 14px 14px 12px;
  border-radius: 22px;
  background:
    radial-gradient(720px 260px at 18% 0%, rgba(247, 201, 72, 0.22), rgba(247, 201, 72, 0) 60%),
    radial-gradient(520px 260px at 100% 30%, rgba(255, 138, 61, 0.16), rgba(255, 138, 61, 0) 62%),
    linear-gradient(135deg, rgba(27, 26, 23, 0.94), rgba(27, 26, 23, 0.86));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 18px 44px rgba(27, 26, 23, 0.18);
}

.rail-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.brand {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.brand-badge {
  width: 44px;
  height: 44px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(27, 26, 23, 0.10);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.brand-text {
  font-size: 18px;
  font-weight: 800;
  color: #1b1a17;
  line-height: 1;
}

.brand-stage {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 18px;
  height: 18px;
  border-radius: 9px;
  background: var(--nb-accent);
  color: #1b1a17;
  font-size: 12px;
  text-align: center;
  line-height: 18px;
  font-weight: 800;
  border: 1px solid rgba(27, 26, 23, 0.10);
}

.brand-meta {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 14px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.94);
  line-height: 1.1;
  max-width: 180px;
}

.brand-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.66);
  margin-top: 2px;
}

.summary {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 4px;
  color: rgba(255, 255, 255, 0.86);
}

.summary-strong {
  font-size: 16px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.94);
}

.summary-muted {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.60);
}

.summary-dot {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.36);
  margin: 0 2px;
}

.rail-track {
  white-space: nowrap;
  height: 86px;
}

.rail-track-inner {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding-right: 10px;
}

.slot {
  width: 64px;
  height: 82px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.10);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px 10px 8px;
  box-sizing: border-box;
}

.slot.filled {
  background: rgba(255, 255, 255, 0.10);
  border-color: rgba(247, 201, 72, 0.40);
  box-shadow: 0 10px 24px rgba(247, 201, 72, 0.10);
}

.slot-top {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
}

.bottle {
  width: 26px;
  height: 38px;
  opacity: 0.96;
}

.pulse {
  position: absolute;
  width: 34px;
  height: 34px;
  border-radius: 17px;
  background: rgba(255, 138, 61, 0.18);
  filter: blur(0.2px);
}

.slot-bottom {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.avatar {
  width: 18px;
  height: 18px;
  border-radius: 9px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.10);
}

.avatar-empty {
  opacity: 0.30;
}

.amount {
  font-size: 14px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.92);
}

.amount.empty {
  color: rgba(255, 255, 255, 0.32);
  font-weight: 700;
}

.more {
  width: 44px;
  height: 82px;
  border-radius: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
}

.more-text {
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  font-weight: 800;
}

.rail-foot {
  margin-top: 10px;
}

.hint {
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
}
</style>

