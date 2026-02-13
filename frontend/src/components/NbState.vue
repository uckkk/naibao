<template>
  <view class="nb-state" :class="[`t-${type}`, { embedded }]">
    <view class="icon" aria-hidden="true">
      <text class="icon-text">{{ iconText }}</text>
    </view>
    <view class="text">
      <text class="title">{{ computedTitle }}</text>
      <text v-if="computedDesc" class="desc">{{ computedDesc }}</text>
    </view>

    <view v-if="actionText" class="actions">
      <button class="nb-primary-btn action-btn" @click="$emit('action')">{{ actionText }}</button>
    </view>

    <slot />
  </view>
</template>

<script>
export default {
  name: 'NbState',
  props: {
    type: { type: String, default: 'info' }, // loading | empty | error | info
    title: { type: String, default: '' },
    desc: { type: String, default: '' },
    actionText: { type: String, default: '' },
    embedded: { type: Boolean, default: false }, // 嵌入式：用于卡片内部，弱化边框与阴影
  },
  emits: ['action'],
  computed: {
    iconText() {
      const t = String(this.type || 'info')
      if (t === 'loading') return '...'
      if (t === 'empty') return '0'
      if (t === 'error') return '!'
      return 'i'
    },
    computedTitle() {
      if (this.title) return this.title
      const t = String(this.type || 'info')
      if (t === 'loading') return '加载中...'
      if (t === 'empty') return '暂无数据'
      if (t === 'error') return '出错了'
      return '提示'
    },
    computedDesc() {
      return this.desc || ''
    },
  },
}
</script>

<style scoped>
.nb-state {
  background: var(--nb-card-bg);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
  box-shadow: 0 18px 50px rgba(var(--nb-ink-rgb), 0.10);
}

.nb-state.embedded {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 10px 0;
}

.nb-state.embedded .icon {
  display: none;
}

.icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--nb-fill);
  border: 1px solid var(--nb-line);
}

.icon-text {
  font-size: 18px;
  color: rgba(var(--nb-ink-rgb), 0.72);
  font-weight: 900;
}

.t-loading .icon {
  background: rgba(247, 201, 72, 0.20);
  border-color: rgba(247, 201, 72, 0.35);
}

.t-error .icon {
  background: rgba(226, 74, 59, 0.12);
  border-color: rgba(226, 74, 59, 0.22);
}

.t-empty .icon {
  background: rgba(var(--nb-ink-rgb), 0.04);
}

.title {
  font-size: 16px;
  color: var(--nb-text);
  font-weight: 900;
}

.desc {
  margin-top: 6px;
  display: block;
  font-size: 13px;
  color: var(--nb-muted);
  line-height: 1.6;
  white-space: pre-line;
}

.actions {
  margin-top: 2px;
}

.action-btn {
  height: 44px;
  border-radius: 22px;
  font-size: 15px;
}
</style>
