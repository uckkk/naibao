<template>
  <view
    v-if="visible"
    class="nb-sheet-mask"
    @click.self="$emit('cancel')"
    @touchmove.prevent
    @wheel.prevent
  >
    <view class="nb-sheet" @click.stop>
      <text v-if="title" class="nb-sheet-title">{{ title }}</text>
      <text v-if="desc" class="nb-sheet-desc">{{ desc }}</text>

      <view class="nb-sheet-actions">
        <button v-if="showCancel" class="nb-ghost-btn" :disabled="loading" @click="$emit('cancel')">
          {{ cancelText }}
        </button>
        <button
          class="nb-confirm-btn"
          :class="{ danger: confirmVariant === 'danger' }"
          :disabled="loading || confirmDisabled"
          @click="$emit('confirm')"
        >
          {{ loading ? loadingText : confirmText }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'NbConfirmSheet',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '' },
    desc: { type: String, default: '' },
    confirmText: { type: String, default: '确定' },
    cancelText: { type: String, default: '取消' },
    loadingText: { type: String, default: '处理中...' },
    loading: { type: Boolean, default: false },
    confirmDisabled: { type: Boolean, default: false },
    confirmVariant: { type: String, default: 'primary' }, // primary | danger
    showCancel: { type: Boolean, default: true },
  },
  emits: ['confirm', 'cancel'],
}
</script>

<style scoped>
.nb-sheet-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 12px var(--nb-page-x) calc(12px + var(--nb-safe-bottom));
  box-sizing: border-box;
  z-index: 2000;
}

.nb-sheet {
  background:
    radial-gradient(860px 320px at 18% 0%, rgba(247, 201, 72, 0.18), rgba(247, 201, 72, 0) 60%),
    radial-gradient(700px 320px at 100% 20%, rgba(255, 138, 61, 0.12), rgba(255, 138, 61, 0) 62%),
    rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.70);
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.25);
}

.nb-sheet-title {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
  margin-bottom: 8px;
}

.nb-sheet-desc {
  display: block;
  font-size: 13px;
  color: rgba(27, 26, 23, 0.62);
  line-height: 1.6;
  white-space: pre-line;
}

.nb-sheet-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.nb-ghost-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.82);
  font-weight: 800;
  font-size: 14px;
}

.nb-confirm-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  color: var(--nb-text);
  font-weight: 900;
  border: none;
  font-size: 14px;
}

.nb-confirm-btn.danger {
  background: rgba(226, 74, 59, 0.12);
  border: 1px solid rgba(226, 74, 59, 0.22);
  color: var(--nb-danger);
}
</style>

