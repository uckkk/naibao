<template>
  <view class="spec-container">
    <NbNetworkBanner />
    <NbLoadable
      :loading="loading"
      :errorText="error"
      errorTitle="冲泡要求"
      :empty="!selection"
      emptyType="info"
      emptyTitle="还没有绑定奶粉"
      emptyDesc="绑定后可显示勺数、水温与冲泡步骤"
      emptyActionText="去绑定"
      @retry="init"
      @emptyAction="goBindFormula"
    >
      <template #skeleton>
        <view class="card">
          <view class="head">
            <view class="brand">
              <NbSkeleton :w="120" :h="18" :radius="9" />
              <view style="margin-top:8px;">
                <NbSkeleton :w="220" :h="12" :radius="6" />
              </view>
            </view>
          </view>

          <view class="row">
            <NbSkeleton :w="72" :h="12" :radius="6" />
            <NbSkeleton :w="120" :h="12" :radius="6" />
          </view>
          <view class="row">
            <NbSkeleton :w="44" :h="12" :radius="6" />
            <NbSkeleton :w="80" :h="12" :radius="6" />
          </view>

          <view class="block">
            <NbSkeleton :w="72" :h="12" :radius="6" />
            <view style="margin-top:10px;">
              <NbSkeletonText :lines="4" :gap="8" />
            </view>
          </view>
        </view>
      </template>
      <view class="card">
        <view class="head">
          <view class="brand">
            <text class="brand-name">{{ brandNameText }}</text>
            <text v-if="brandSubText" class="brand-sub">{{ brandSubText }}</text>
          </view>
          <view v-if="sourcePillText" class="pill">
            <text class="pill-text">{{ sourcePillText }}</text>
          </view>
        </view>

        <view class="row">
          <text class="k">勺数换算</text>
          <text class="v">{{ scoopText }}</text>
        </view>
        <view class="row">
          <text class="k">水温</text>
          <text class="v">{{ tempText }}</text>
        </view>

        <view class="block">
          <text class="k">冲泡步骤</text>
          <view class="steps">
            <text v-for="(line, idx) in mixingLines" :key="idx" class="step">{{ line }}</text>
          </view>
        </view>

        <view class="foot">
          <text v-if="officialSourceText" class="muted">数据来源：{{ officialSourceText }}</text>
          <text v-else-if="!officialSpec" class="muted">暂无官方数据，请以包装说明为准</text>
          <text v-if="customNoteText" class="muted">{{ customNoteText }}</text>
        </view>
      </view>
    </NbLoadable>

    <view class="footer">
      <button class="ghost-btn" @click="goBack">返回</button>
      <button
        v-if="showEditEntry"
        class="nb-primary-btn"
        @click="openEditSheet"
      >
        {{ editEntryText }}
      </button>
    </view>

    <!-- 补充/编辑（仅本机存储，不同步） -->
    <view
      v-if="editVisible"
      class="sheet-mask"
      @click.self="closeEditSheet"
      @touchmove.prevent
      @wheel.prevent
    >
      <view class="sheet" @click.stop>
        <text class="sheet-title">{{ editSheetTitle }}</text>
        <text class="sheet-desc">仅保存在本机，用于补齐缺失的冲泡信息</text>

        <view class="fields">
          <view class="field-block">
            <text class="field-k">勺数换算</text>
            <text v-if="!canEditScoop" class="field-v">{{ scoopText || '—' }}</text>
            <view v-else class="input-row">
              <input
                class="input"
                type="number"
                inputmode="numeric"
                v-model="draftScoopMl"
                placeholder="例如 30"
                placeholder-class="input-ph"
              />
              <text class="unit">ml/勺</text>
            </view>
          </view>

          <view class="field-block">
            <text class="field-k">水温</text>
            <text v-if="!canEditTempAny" class="field-v">{{ tempText || '—' }}</text>
            <view v-else class="temp-row">
              <input
                class="input small"
                type="number"
                inputmode="numeric"
                v-model="draftTempMin"
                :disabled="!canEditTempMin"
                placeholder="最小"
                placeholder-class="input-ph"
              />
              <text class="dash">-</text>
              <input
                class="input small"
                type="number"
                inputmode="numeric"
                v-model="draftTempMax"
                :disabled="!canEditTempMax"
                placeholder="最大"
                placeholder-class="input-ph"
              />
              <text class="unit">℃</text>
            </view>
          </view>

          <view class="field-block">
            <text class="field-k">冲泡步骤</text>
            <text v-if="!canEditSteps" class="field-v">{{ mixingLines.join(' / ') }}</text>
            <textarea
              v-else
              class="textarea"
              v-model="draftMixing"
              placeholder="每行一步（可选）"
              placeholder-class="input-ph"
            />
          </view>
        </view>

        <view class="sheet-actions">
          <button class="ghost-btn" :disabled="savingLocal" @click="closeEditSheet">取消</button>
          <button class="primary-btn" :disabled="savingLocal" @click="saveCustom">
            {{ savingLocal ? '保存中...' : '保存' }}
          </button>
        </view>

        <view v-if="customSpec" class="sheet-actions secondary">
          <button class="danger-btn" :disabled="savingLocal" @click="askClearCustom">清除本机补充</button>
        </view>
      </view>
    </view>

    <NbConfirmSheet
      :visible="confirmVisible"
      title="清除本机补充？"
      desc="将删除你在本机录入的冲泡补充信息（不会影响官方数据）。"
      confirmText="清除"
      cancelText="取消"
      confirmVariant="danger"
      @confirm="confirmClearCustom"
      @cancel="cancelClearCustom"
    />
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbSkeletonText from '@/components/NbSkeletonText.vue'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'
import {
  applyCustomSpecIfMissing,
  buildCustomFormulaSpecKey,
  clearCustomFormulaSpec,
  readCustomFormulaSpec,
  writeCustomFormulaSpec,
} from '@/utils/custom_formula_spec'

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton, NbSkeletonText, NbConfirmSheet },
  data() {
    return {
      babyId: null,
      loading: false,
      error: '',
      selection: null,
      officialSpec: null,

      customKey: '',
      customSpec: null,

      editVisible: false,
      savingLocal: false,
      draftScoopMl: '',
      draftTempMin: '',
      draftTempMax: '',
      draftMixing: '',

      confirmVisible: false,
    }
  },

  computed: {
    specModel() {
      return applyCustomSpecIfMissing(this.officialSpec, this.customSpec)
    },
    effectiveSpec() {
      return this.specModel?.spec || null
    },
    usedCustom() {
      return !!this.specModel?.usedCustom
    },

    mixingLines() {
      const raw = String(this.effectiveSpec?.mixing_method || '').trim()
      if (!raw) return ['暂无官方步骤，请以包装说明为准']
      return raw.split('\n').map((s) => String(s).trim()).filter(Boolean)
    },

    brandNameText() {
      return this.officialSpec?.brand?.name_cn || this.selection?.brand?.name_cn || '奶粉'
    },
    brandSubText() {
      const series = String(this.selection?.series_name || '').trim() || '默认系列'
      const range = String(this.selection?.age_range || '').trim()
      const r = this.formatAgeRange(range)
      return [series, r].filter(Boolean).join(' ')
    },

    officialSourceText() {
      const s = String(this.officialSpec?.data_source || '').trim()
      return s
    },
    sourcePillText() {
      if (this.officialSpec && this.usedCustom) return '官方 · 补充'
      if (this.officialSpec) return '官方'
      if (this.customSpec) return '本机补充'
      return ''
    },

    scoopText() {
      const spec = this.effectiveSpec || null
      const ml = Number(spec?.scoop_ml || 0)
      const g = Number(spec?.scoop_weight_gram || 0)
      const a = []
      if (Number.isFinite(ml) && ml > 0) a.push(`${Math.round(ml)}ml/勺`)
      if (Number.isFinite(g) && g > 0) a.push(`${Math.round(g)}g/勺`)
      return a.join(' · ') || '未设置'
    },

    tempText() {
      const spec = this.effectiveSpec || null
      const min = Number(spec?.water_temp_min || 0)
      const max = Number(spec?.water_temp_max || 0)
      const hasMin = Number.isFinite(min) && min > 0
      const hasMax = Number.isFinite(max) && max > 0
      if (!hasMin && !hasMax) return '未设置'
      if (hasMin && hasMax) return `${Math.round(min)}-${Math.round(max)}℃`
      return `${Math.round(hasMin ? min : max)}℃`
    },

    canEditScoop() {
      const ml = Number(this.officialSpec?.scoop_ml || 0)
      return !(Number.isFinite(ml) && ml > 0)
    },
    canEditTempMin() {
      const min = Number(this.officialSpec?.water_temp_min || 0)
      return !(Number.isFinite(min) && min > 0)
    },
    canEditTempMax() {
      const max = Number(this.officialSpec?.water_temp_max || 0)
      return !(Number.isFinite(max) && max > 0)
    },
    canEditTempAny() {
      return this.canEditTempMin || this.canEditTempMax
    },
    canEditSteps() {
      const raw = String(this.officialSpec?.mixing_method || '').trim()
      return !raw
    },

    showEditEntry() {
      // 仅在“官方缺失可补齐字段”或已存在本机补充时提供入口，避免无意义按钮。
      if (!this.selection) return false
      return this.canEditScoop || this.canEditTempAny || this.canEditSteps || !!this.customSpec
    },
    editEntryText() {
      if (this.customSpec) return '编辑补充'
      if (!this.officialSpec) return '录入冲泡要求'
      return '补充缺失信息'
    },

    customNoteText() {
      if (!this.customSpec) return ''
      if (!this.usedCustom && this.officialSpec) return '官方信息已完整，你的补充暂未生效（可清除）'
      return this.usedCustom ? '已使用本机补充信息' : ''
    },

    editSheetTitle() {
      return this.customSpec ? '编辑补充' : '补充冲泡要求'
    },
  },

  onLoad(options) {
    const userStore = useUserStore()
    this.babyId = options?.babyId || userStore.currentBaby?.id || null
  },

  onShow() {
    const userStore = useUserStore()
    // 多宝宝：默认全局跟随 currentBaby
    if (userStore.currentBaby?.id) this.babyId = userStore.currentBaby.id
    this.init()
  },

  methods: {
    onNbRetry() {
      this.init()
    },

    async init() {
      if (!this.babyId) {
        this.error = '缺少 babyId'
        return
      }
      this.loading = true
      this.error = ''
      try {
        await Promise.all([this.loadSelection(), this.loadOfficialSpec()])
        this.refreshCustom()
      } catch (e) {
        this.selection = null
        this.officialSpec = null
        this.error = e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },

    async loadSelection() {
      const res = await api.get(`/babies/${this.babyId}/formula`, {}, { silent: true })
      this.selection = res?.selection || null
    },

    async loadOfficialSpec() {
      const res = await api.get(`/babies/${this.babyId}/formula/specification`, {}, { silent: true })
      this.officialSpec = res?.specification || null
    },

    refreshCustom() {
      const sel = this.selection || null
      const key = buildCustomFormulaSpecKey({
        babyId: this.babyId,
        brandId: sel?.brand_id,
        seriesName: sel?.series_name,
        ageRange: sel?.age_range,
      })
      this.customKey = key
      this.customSpec = key ? readCustomFormulaSpec(key) : null
    },

    goBack() {
      uni.navigateBack()
    },

    goBindFormula() {
      if (!this.babyId) return
      uni.navigateTo({ url: `/pages/formula-select/index?babyId=${this.babyId}` })
    },

    formatAgeRange(ageRange) {
      const s = String(ageRange || '').trim()
      if (!s) return ''
      if (s.includes('-')) return `· ${s}个月`
      return `· ${s}`
    },

    openEditSheet() {
      if (this.savingLocal) return
      const cur = this.customSpec || {}
      // 仅编辑“官方缺失的字段”：让补充一定生效，避免用户以为在改官方。
      this.draftScoopMl = this.canEditScoop ? String(cur.scoop_ml || '') : ''
      this.draftTempMin = this.canEditTempMin ? String(cur.water_temp_min || '') : ''
      this.draftTempMax = this.canEditTempMax ? String(cur.water_temp_max || '') : ''
      this.draftMixing = this.canEditSteps ? String(cur.mixing_method || '') : ''
      this.editVisible = true
    },

    closeEditSheet() {
      if (this.savingLocal) return
      this.editVisible = false
      this.draftScoopMl = ''
      this.draftTempMin = ''
      this.draftTempMax = ''
      this.draftMixing = ''
    },

    clampInt(raw, min, max) {
      const n = Number.parseInt(String(raw ?? '').trim(), 10)
      if (!Number.isFinite(n)) return null
      return Math.max(min, Math.min(max, n))
    },

    async saveCustom() {
      if (!this.customKey || this.savingLocal) {
        uni.showToast({ title: '请先选择奶粉', icon: 'none' })
        return
      }

      const next = { ...(this.customSpec || {}) }
      if (this.canEditScoop) {
        const v = String(this.draftScoopMl || '').trim()
        next.scoop_ml = v ? (this.clampInt(v, 1, 200) || 0) : 0
      }
      if (this.canEditTempMin) {
        const v = String(this.draftTempMin || '').trim()
        next.water_temp_min = v ? (this.clampInt(v, 1, 100) || 0) : 0
      }
      if (this.canEditTempMax) {
        const v = String(this.draftTempMax || '').trim()
        next.water_temp_max = v ? (this.clampInt(v, 1, 100) || 0) : 0
      }
      if (this.canEditSteps) {
        next.mixing_method = String(this.draftMixing || '').trim()
      }

      const min = Number(next.water_temp_min || 0)
      const max = Number(next.water_temp_max || 0)
      if (min > 0 && max > 0 && min > max) {
        uni.showToast({ title: '水温范围不正确', icon: 'none' })
        return
      }

      const hasAny = (Number(next.scoop_ml || 0) > 0)
        || (Number(next.water_temp_min || 0) > 0)
        || (Number(next.water_temp_max || 0) > 0)
        || !!String(next.mixing_method || '').trim()
      if (!hasAny) {
        uni.showToast({ title: '请至少补充一项', icon: 'none' })
        return
      }

      this.savingLocal = true
      try {
        writeCustomFormulaSpec(this.customKey, next)
        this.refreshCustom()
        uni.showToast({ title: '已保存（仅本机）', icon: 'success' })
        this.closeEditSheet()
      } finally {
        this.savingLocal = false
      }
    },

    askClearCustom() {
      if (this.savingLocal || !this.customSpec) return
      this.confirmVisible = true
    },

    cancelClearCustom() {
      this.confirmVisible = false
    },

    confirmClearCustom() {
      this.confirmVisible = false
      if (!this.customKey) return
      clearCustomFormulaSpec(this.customKey)
      this.refreshCustom()
      this.closeEditSheet()
      uni.showToast({ title: '已清除', icon: 'success' })
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

.pill {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
}

.pill-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.70);
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

.ghost-btn {
  height: 48px;
  border-radius: 24px;
  background: rgba(27, 26, 23, 0.06);
  color: var(--nb-text);
  border: 1px solid var(--nb-border);
  font-size: 15px;
  font-weight: 800;
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
  display: flex;
  gap: 10px;
}

.sheet-mask {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0 var(--nb-page-x) calc(10px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  z-index: 999;
}

.sheet {
  width: 100%;
  max-width: 520px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(27, 26, 23, 0.10);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.18);
  padding: 16px;
  box-sizing: border-box;
}

.sheet-title {
  font-size: 17px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
}

.sheet-desc {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.58);
  display: block;
  line-height: 1.5;
}

.fields {
  margin-top: 14px;
}

.field-block {
  padding: 12px 0;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.field-block:first-child {
  border-top: none;
  padding-top: 0;
}

.field-k {
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.62);
  display: block;
}

.field-v {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.86);
}

.input-row,
.temp-row {
  margin-top: 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.input {
  flex: 1;
  height: 44px;
  border-radius: 14px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  padding: 0 12px;
  box-sizing: border-box;
  background: #fff;
  font-size: 15px;
  color: var(--nb-text);
}

.input.small {
  flex: 0 0 96px;
}

.input[disabled] {
  background: rgba(27, 26, 23, 0.06);
  color: rgba(27, 26, 23, 0.45);
}

.unit {
  font-size: 13px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.60);
  white-space: nowrap;
}

.dash {
  color: rgba(27, 26, 23, 0.45);
  font-weight: 900;
}

.textarea {
  width: 100%;
  min-height: 110px;
  margin-top: 10px;
  border-radius: 14px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  padding: 10px 12px;
  box-sizing: border-box;
  background: #fff;
  font-size: 14px;
  color: var(--nb-text);
}

.sheet-actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
}

.sheet-actions.secondary {
  margin-top: 10px;
}

.primary-btn {
  flex: 1;
  height: 44px;
  border-radius: 22px;
  background: rgba(27, 26, 23, 0.92);
  color: rgba(255, 255, 255, 0.92);
  font-weight: 900;
  border: none;
  font-size: 15px;
}

.danger-btn {
  width: 100%;
  height: 40px;
  border-radius: 20px;
  background: rgba(226, 74, 59, 0.10);
  border: 1px solid rgba(226, 74, 59, 0.22);
  color: var(--nb-danger);
  font-weight: 900;
  font-size: 13px;
}
</style>
