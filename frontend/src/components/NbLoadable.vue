<template>
  <NbLoadingSwitch :loading="loading" :delayMs="delayMs" :minShowMs="minShowMs" :fadeMs="fadeMs">
    <template #skeleton>
      <slot name="skeleton" />
    </template>

    <slot v-if="errorText" name="error">
      <NbState
        type="error"
        :title="errorTitle"
        :desc="errorText"
        :actionText="retryText"
        @action="$emit('retry')"
      />
    </slot>

    <slot v-else-if="empty" name="empty">
      <NbState
        :type="emptyType"
        :title="emptyTitle"
        :desc="emptyDesc"
        :actionText="emptyActionText"
        @action="$emit('emptyAction')"
      />
    </slot>

    <slot v-else />
  </NbLoadingSwitch>
</template>

<script>
import NbLoadingSwitch from './NbLoadingSwitch.vue'
import NbState from './NbState.vue'

export default {
  name: 'NbLoadable',
  components: { NbLoadingSwitch, NbState },
  props: {
    loading: { type: Boolean, default: false },

    errorText: { type: String, default: '' },
    errorTitle: { type: String, default: '加载失败' },
    retryText: { type: String, default: '重试' },

    empty: { type: Boolean, default: false },
    emptyType: { type: String, default: 'empty' }, // empty | info
    emptyTitle: { type: String, default: '暂无数据' },
    emptyDesc: { type: String, default: '' },
    emptyActionText: { type: String, default: '' },

    // 透传给 NbLoadingSwitch，用于全站统一“骨架->内容”节奏
    delayMs: { type: Number, default: 120 },
    minShowMs: { type: Number, default: 280 },
    fadeMs: { type: Number, default: 220 },
  },
  emits: ['retry', 'emptyAction'],
}
</script>

