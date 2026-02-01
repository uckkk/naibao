<template>
  <view class="spec-container">
    <NbState v-if="loading" type="loading" title="加载中..." />

    <NbState
      v-else-if="error"
      type="error"
      title="冲泡要求"
      :desc="error"
      actionText="重试"
      @action="loadSpec"
    />

    <view class="card" v-else-if="spec">
      <view class="head">
        <view class="brand">
          <text class="brand-name">{{ spec.brand?.name_cn || '奶粉' }}</text>
          <text class="brand-sub">{{ spec.series_name || '默认系列' }} {{ formatAgeRange(spec.age_range) }}</text>
        </view>
      </view>

      <view class="row">
        <text class="k">勺数换算</text>
        <text class="v">{{ formatScoop(spec) }}</text>
      </view>
      <view class="row">
        <text class="k">水温</text>
        <text class="v">{{ formatTemp(spec) }}</text>
      </view>

      <view class="block">
        <text class="k">冲泡步骤</text>
        <view class="steps">
          <text v-for="(line, idx) in mixingLines" :key="idx" class="step">{{ line }}</text>
        </view>
      </view>

      <view class="foot" v-if="spec.data_source">
        <text class="muted">数据来源：{{ spec.data_source }}</text>
      </view>
    </view>

    <view class="footer">
      <button class="nb-primary-btn" @click="goBack">返回</button>
    </view>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'

export default {
  components: { NbState },
  data() {
    return {
      babyId: null,
      loading: false,
      error: '',
      spec: null,
    }
  },

  computed: {
    mixingLines() {
      const raw = String(this.spec?.mixing_method || '').trim()
      if (!raw) return ['暂无官方步骤，请以包装说明为准']
      return raw.split('\n').map((s) => String(s).trim()).filter(Boolean)
    },
  },

  onLoad(options) {
    const userStore = useUserStore()
    this.babyId = options?.babyId || userStore.currentBaby?.id || null
    this.loadSpec()
  },

  methods: {
    async loadSpec() {
      if (!this.babyId) {
        this.error = '缺少 babyId'
        return
      }
      this.loading = true
      this.error = ''
      try {
        const res = await api.get(`/babies/${this.babyId}/formula/specification`)
        this.spec = res.specification || null
        if (!this.spec) this.error = '未找到奶粉规格数据'
      } catch (e) {
        this.spec = null
        this.error = e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },

    goBack() {
      uni.navigateBack()
    },

    formatAgeRange(ageRange) {
      const s = String(ageRange || '').trim()
      if (!s) return ''
      if (s.includes('-')) return `· ${s}个月`
      return `· ${s}`
    },

    formatScoop(spec) {
      const ml = Number(spec?.scoop_ml || 0)
      const g = Number(spec?.scoop_weight_gram || 0)
      const a = []
      if (ml > 0) a.push(`${ml}ml/勺`)
      if (g > 0) a.push(`${g}g/勺`)
      return a.join(' · ') || '暂无数据'
    },

    formatTemp(spec) {
      const min = spec?.water_temp_min
      const max = spec?.water_temp_max
      if (!min && !max) return '暂无数据'
      if (min && max) return `${min}-${max}℃`
      return `${min || max}℃`
    },
  },
}
</script>

<style scoped>
.spec-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + env(safe-area-inset-top, 0px)) var(--nb-page-x)
    calc(96px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
}

.card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 16px;
}

.head {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.brand-name {
  font-size: 18px;
  font-weight: 900;
  color: var(--nb-text);
}

.brand-sub {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: var(--nb-muted);
}

.row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.block {
  padding: 12px 0 0;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.k {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.62);
  font-weight: 700;
}

.v {
  font-size: 14px;
  color: var(--nb-text);
  font-weight: 800;
}

.steps {
  margin-top: 10px;
  background: rgba(27, 26, 23, 0.04);
  border: 1px solid rgba(27, 26, 23, 0.08);
  border-radius: 14px;
  padding: 12px;
}

.step {
  display: block;
  font-size: 14px;
  color: var(--nb-text);
  line-height: 1.6;
  margin-bottom: 6px;
}

.step:last-child {
  margin-bottom: 0;
}

.title {
  font-size: 18px;
  font-weight: 900;
  color: var(--nb-text);
}

.muted {
  display: block;
  margin-top: 8px;
  color: var(--nb-muted);
  font-size: 13px;
  line-height: 1.5;
}

.foot {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px var(--nb-page-x);
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid var(--nb-border);
}
</style>
