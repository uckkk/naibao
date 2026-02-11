<template>
  <view class="admin-container">
    <NbNetworkBanner />
    <NbState
      v-if="unauthorized"
      type="error"
      title="无管理员权限"
      :desc="unauthorizedDesc"
      actionText="返回"
      @action="goBack"
    />

    <template v-else>
    <view class="header">
      <text class="title">管理后台</text>
      <text class="sub">仅管理员可见：标准版本管理 / 奶粉规格维护</text>
    </view>

    <view class="tabs">
      <view class="tab" :class="{ active: activeTab === 'standards' }" @click="activeTab = 'standards'">
        <text>卫健委标准</text>
      </view>
      <view class="tab" :class="{ active: activeTab === 'formula' }" @click="activeTab = 'formula'">
        <text>奶粉规格</text>
      </view>
    </view>

    <!-- Standards -->
    <view v-if="activeTab === 'standards'" class="card">
      <view class="card-head">
        <text class="card-title">版本</text>
        <button class="ghost-btn" :disabled="loading" @click="refreshStandards">刷新</button>
      </view>

      <view v-if="versions.length === 0" class="empty">
        <text class="empty-text">暂无版本信息</text>
      </view>

      <scroll-view v-else class="chips" scroll-x show-scrollbar="false">
        <view class="chips-inner">
          <view
            v-for="v in versions"
            :key="v.version"
            class="chip"
            :class="{ active: selectedVersion === v.version }"
            @click="selectVersion(v.version)"
          >
            <text class="chip-text">{{ v.version }}</text>
            <text v-if="v.version === activeVersion" class="chip-badge">启用中</text>
          </view>
        </view>
      </scroll-view>

      <view class="row" v-if="selectedVersion">
        <text class="row-k">当前选择</text>
        <text class="row-v">{{ selectedVersion }}</text>
        <button
          v-if="selectedVersion && selectedVersion !== activeVersion"
          class="primary-btn"
          :disabled="loading"
          @click="activateSelected"
        >
          启用该版本
        </button>
      </view>

      <view class="filters" v-if="selectedVersion">
        <view class="filter" :class="{ active: selectedType === '' }" @click="setType('')">全部</view>
        <view class="filter" :class="{ active: selectedType === 'milk_by_weight' }" @click="setType('milk_by_weight')">奶量(体重)</view>
        <view class="filter" :class="{ active: selectedType === 'milk_by_age' }" @click="setType('milk_by_age')">奶量(月龄)</view>
        <view class="filter" :class="{ active: selectedType === 'weight_gain' }" @click="setType('weight_gain')">增重</view>
        <view class="filter" :class="{ active: selectedType === 'height_gain' }" @click="setType('height_gain')">增高</view>
      </view>

      <view v-if="selectedVersion" class="list">
        <view v-if="stdLoading" class="hint">
          <text class="hint-text">加载中...</text>
        </view>
        <view v-else-if="standards.length === 0" class="empty">
          <text class="empty-text">该版本暂无数据</text>
        </view>

        <view v-else class="std-list">
          <view v-for="s in standards" :key="s.id" class="std-item">
            <view class="std-top">
              <text class="std-type">{{ s.type }}</text>
              <text class="std-range">{{ monthRangeText(s) }}</text>
              <text class="std-flag" :class="{ on: s.is_active }">{{ s.is_active ? 'active' : 'inactive' }}</text>
            </view>
            <text class="std-data">{{ safeJsonPreview(s.data) }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-if="activeTab === 'standards'" class="card">
      <view class="card-head">
        <text class="card-title">导入 JSON</text>
      </view>
      <text class="card-sub">
        粘贴标准 JSON（数组或对象）。若条目未写 version，将自动使用“当前选择版本”。默认导入为 inactive（避免误切换），需要手动“启用该版本”。
      </text>

      <textarea
        class="textarea"
        v-model="importJson"
        placeholder='示例：[{ "type":"milk_by_weight", "data":{"min":120,"max":150,"recommended":135,"unit":"ml/kg/day"} } ]'
      ></textarea>

      <view class="actions">
        <button class="ghost-btn" :disabled="loading || !importJson.trim()" @click="clearImport">清空</button>
        <button class="primary-btn" :disabled="loading || !importJson.trim()" @click="doImport">导入</button>
      </view>
    </view>

    <!-- Formula specs -->
    <view v-if="activeTab === 'formula'" class="card">
      <view class="card-head">
        <text class="card-title">奶粉规格</text>
        <button class="ghost-btn" :disabled="loading" @click="refreshFormula">刷新</button>
      </view>

      <view class="row">
        <text class="row-k">品牌</text>
        <picker v-if="brands.length > 0" :range="brands" range-key="name_cn" @change="onBrandPick">
          <view class="picker-btn">
            <text class="picker-text">{{ selectedBrandName }}</text>
          </view>
        </picker>
        <text v-else class="row-v">加载中...</text>
        <button class="primary-btn" :disabled="loading || !selectedBrandId" @click="openCreateSpec">新增规格</button>
      </view>

      <view v-if="specLoading" class="hint">
        <text class="hint-text">加载中...</text>
      </view>
      <view v-else-if="specs.length === 0" class="empty">
        <text class="empty-text">暂无规格数据</text>
      </view>

      <view v-else class="spec-list">
        <view v-for="sp in specs" :key="sp.id" class="spec-item" @click="openEditSpec(sp)">
          <view class="spec-top">
            <text class="spec-name">{{ sp.series_name || '默认系列' }}</text>
            <text class="spec-range">{{ sp.age_range }}</text>
            <text class="spec-flag" :class="{ on: sp.is_verified }">{{ sp.is_verified ? '已验证' : '未验证' }}</text>
          </view>
          <text class="spec-sub">{{ scoopMeta(sp) }}</text>
        </view>
      </view>
    </view>

    <!-- Spec modal -->
    <view v-if="showSpecModal" class="modal-overlay" @click.self="closeSpecModal">
      <view class="modal" @click.stop @touchstart.stop>
        <view class="modal-head">
          <text class="modal-title">{{ editingSpec?.id ? '编辑规格' : '新增规格' }}</text>
          <text class="close" @click="closeSpecModal">×</text>
        </view>

        <view class="form">
          <view class="field">
            <text class="k">系列</text>
            <input class="input" v-model="specForm.series_name" placeholder="例如 至初系列" />
          </view>
          <view class="field">
            <text class="k">月龄段</text>
            <input class="input" v-model="specForm.age_range" placeholder="例如 0-6" />
          </view>
          <view class="field">
            <text class="k">每勺水量(ml)</text>
            <input class="input" type="number" inputmode="decimal" v-model="specForm.scoop_ml" placeholder="30" />
          </view>
          <view class="field">
            <text class="k">每勺重量(g)</text>
            <input class="input" type="number" inputmode="decimal" v-model="specForm.scoop_weight_gram" placeholder="4.5" />
          </view>
          <view class="field">
            <text class="k">水温(℃)</text>
            <view class="twins">
              <input class="input" type="number" inputmode="numeric" v-model="specForm.water_temp_min" placeholder="40" />
              <text class="dash">-</text>
              <input class="input" type="number" inputmode="numeric" v-model="specForm.water_temp_max" placeholder="50" />
            </view>
          </view>
          <view class="field">
            <text class="k">冲泡步骤</text>
            <textarea class="textarea small" v-model="specForm.mixing_method" placeholder="可粘贴官方说明"></textarea>
          </view>
          <view class="field">
            <text class="k">数据来源</text>
            <input class="input" v-model="specForm.data_source" placeholder="官网/包装/客服等" />
          </view>
        </view>

        <view class="modal-actions">
          <button class="ghost-btn" :disabled="loading" @click="closeSpecModal">取消</button>
          <button class="primary-btn" :disabled="loading" @click="saveSpec">保存</button>
        </view>

        <view v-if="editingSpec?.id && !editingSpec?.is_verified" class="danger-row">
          <button class="verify-btn" :disabled="loading" @click="verifySpec">标记为已验证</button>
        </view>
      </view>
    </view>
    </template>
  </view>
</template>

<script>
import api from '@/utils/api'
import NbState from '@/components/NbState.vue'
import { useUserStore } from '@/stores/user'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'

export default {
  components: { NbState, NbNetworkBanner },
  data() {
    return {
      activeTab: 'standards',
      loading: false,
      unauthorized: false,
      unauthorizedText: '',
      meId: null,

      // standards
      versions: [],
      activeVersion: '',
      selectedVersion: '',
      selectedType: '',
      standards: [],
      stdLoading: false,
      importJson: '',

      // formula
      brands: [],
      selectedBrandId: null,
      specs: [],
      specLoading: false,

      // spec modal
      showSpecModal: false,
      editingSpec: null,
      specForm: {
        series_name: '',
        age_range: '',
        scoop_ml: '',
        scoop_weight_gram: '',
        water_temp_min: '',
        water_temp_max: '',
        mixing_method: '',
        data_source: '',
      },
    }
  },

  computed: {
    unauthorizedDesc() {
      const me = this.meId ? String(this.meId) : '未知'
      const hint = `当前账号 user_id=${me}。请在服务端设置环境变量 ADMIN_USER_IDS=${me}（可多个，用逗号分隔），并重启后端后再进入。`
      if (this.unauthorizedText) return `${hint}\n\n原因：${this.unauthorizedText}`
      return hint
    },
    selectedBrandName() {
      const b = this.brands.find((x) => String(x.id) === String(this.selectedBrandId))
      return b?.name_cn || '请选择'
    },
  },

  async onLoad() {
    const store = useUserStore()
    this.meId = store.user?.id || null
    // 权限校验：任一 admin API 可用即视为管理员
    try {
      await this.refreshStandards()
    } catch (e) {
      this.unauthorized = true
      this.unauthorizedText = e?.message || ''
      return
    }

    await this.refreshFormula()
  },

  methods: {
    onNbRetry() {
      if (this.unauthorized) return
      if (this.activeTab === 'formula') {
        this.refreshFormula()
        return
      }
      this.refreshStandards()
    },

    goBack() {
      try {
        uni.navigateBack()
      } catch {
        uni.reLaunch({ url: '/pages/home/index' })
      }
    },
    monthRangeText(s) {
      const min = s?.month_min
      const max = s?.month_max
      if (min == null && max == null) return '—'
      if (min != null && max == null) return `${min}月+`
      if (min == null && max != null) return `0-${max}月`
      return `${min}-${max}月`
    },

    safeJsonPreview(raw) {
      try {
        const s = typeof raw === 'string' ? raw : JSON.stringify(raw)
        if (!s) return ''
        const text = s.replace(/\s+/g, ' ').trim()
        return text.length > 120 ? text.slice(0, 120) + '...' : text
      } catch {
        return ''
      }
    },

    setType(t) {
      this.selectedType = t
      this.loadStandards()
    },

    async refreshStandards() {
      this.loading = true
      try {
        const res = await api.get('/admin/health-standards/versions')
        this.activeVersion = res.active_version || ''
        this.versions = Array.isArray(res.versions) ? res.versions : []
        if (!this.selectedVersion) {
          this.selectedVersion = this.activeVersion || this.versions[0]?.version || ''
        }
        await this.loadStandards()
      } finally {
        this.loading = false
      }
    },

    selectVersion(v) {
      this.selectedVersion = v
      this.loadStandards()
    },

    async loadStandards() {
      if (!this.selectedVersion) return
      this.stdLoading = true
      try {
        const res = await api.get('/admin/health-standards', {
          version: this.selectedVersion,
          type: this.selectedType || '',
        })
        this.standards = Array.isArray(res.standards) ? res.standards : []
      } catch (e) {
        this.standards = []
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      } finally {
        this.stdLoading = false
      }
    },

    async activateSelected() {
      if (!this.selectedVersion) return
      this.loading = true
      try {
        await api.post('/admin/health-standards/activate', { version: this.selectedVersion })
        uni.showToast({ title: '已启用', icon: 'success' })
        await this.refreshStandards()
      } catch (e) {
        uni.showToast({ title: e.message || '启用失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    clearImport() {
      this.importJson = ''
    },

    async doImport() {
      const raw = String(this.importJson || '').trim()
      if (!raw) return
      let parsed = null
      try {
        parsed = JSON.parse(raw)
      } catch {
        uni.showToast({ title: 'JSON 格式错误', icon: 'none' })
        return
      }

      const selected = String(this.selectedVersion || '').trim()
      const normalizeOne = (x) => {
        const item = { ...(x || {}) }
        if (!item.version && selected) item.version = selected
        return item
      }

      let payload = null
      if (Array.isArray(parsed)) {
        payload = { standards: parsed.map(normalizeOne) }
      } else if (parsed && typeof parsed === 'object' && Array.isArray(parsed.standards)) {
        payload = { standards: parsed.standards.map(normalizeOne) }
      } else if (parsed && typeof parsed === 'object') {
        payload = normalizeOne(parsed)
      }

      if (!payload) {
        uni.showToast({ title: '不支持的 JSON 结构', icon: 'none' })
        return
      }

      this.loading = true
      try {
        await api.post('/admin/health-standards', payload)
        uni.showToast({ title: '导入成功', icon: 'success' })
        this.importJson = ''
        await this.refreshStandards()
      } catch (e) {
        uni.showToast({ title: e.message || '导入失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    // formula
    async refreshFormula() {
      // brands 用普通接口即可；规格用 admin 接口
      try {
        const res = await api.get('/formula/brands')
        this.brands = Array.isArray(res.brands) ? res.brands : []
        if (!this.selectedBrandId && this.brands[0]?.id) {
          this.selectedBrandId = this.brands[0].id
        }
      } catch {
        this.brands = []
      }
      await this.loadSpecs()
    },

    onBrandPick(e) {
      const idx = Number(e?.detail?.value)
      const b = this.brands[idx]
      if (b?.id) {
        this.selectedBrandId = b.id
        this.loadSpecs()
      }
    },

    async loadSpecs() {
      if (!this.selectedBrandId) {
        this.specs = []
        return
      }
      this.specLoading = true
      try {
        const res = await api.get('/admin/formula/specifications', { brand_id: this.selectedBrandId })
        this.specs = Array.isArray(res.specifications) ? res.specifications : []
      } catch (e) {
        this.specs = []
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      } finally {
        this.specLoading = false
      }
    },

    scoopMeta(sp) {
      const ml = Number(sp?.scoop_ml || 0)
      const g = Number(sp?.scoop_weight_gram || 0)
      const t1 = sp?.water_temp_min
      const t2 = sp?.water_temp_max
      const parts = []
      if (ml > 0) parts.push(`${ml}ml/勺`)
      if (g > 0) parts.push(`${g}g/勺`)
      if (t1 || t2) parts.push(`${t1 || ''}-${t2 || ''}℃`)
      return parts.join(' · ') || '—'
    },

    openCreateSpec() {
      this.editingSpec = null
      this.specForm = {
        series_name: '',
        age_range: '',
        scoop_ml: '',
        scoop_weight_gram: '',
        water_temp_min: '',
        water_temp_max: '',
        mixing_method: '',
        data_source: '',
      }
      this.showSpecModal = true
    },

    openEditSpec(sp) {
      this.editingSpec = sp
      this.specForm = {
        series_name: sp?.series_name || '',
        age_range: sp?.age_range || '',
        scoop_ml: sp?.scoop_ml != null ? String(sp.scoop_ml) : '',
        scoop_weight_gram: sp?.scoop_weight_gram != null ? String(sp.scoop_weight_gram) : '',
        water_temp_min: sp?.water_temp_min != null ? String(sp.water_temp_min) : '',
        water_temp_max: sp?.water_temp_max != null ? String(sp.water_temp_max) : '',
        mixing_method: sp?.mixing_method || '',
        data_source: sp?.data_source || '',
      }
      this.showSpecModal = true
    },

    closeSpecModal() {
      this.showSpecModal = false
      this.editingSpec = null
    },

    async saveSpec() {
      if (!this.selectedBrandId) return
      const series = String(this.specForm.series_name || '').trim()
      const age = String(this.specForm.age_range || '').trim()
      const scoopMl = Number(this.specForm.scoop_ml)
      const scoopG = Number(this.specForm.scoop_weight_gram)
      if (!series || !age || !Number.isFinite(scoopMl) || scoopMl <= 0 || !Number.isFinite(scoopG) || scoopG <= 0) {
        uni.showToast({ title: '请完整填写：系列/月龄段/每勺水量/每勺重量', icon: 'none' })
        return
      }

      const payload = {
        brand_id: this.selectedBrandId,
        series_name: series,
        age_range: age,
        scoop_ml: scoopMl,
        scoop_weight_gram: scoopG,
        water_temp_min: this.specForm.water_temp_min ? Number(this.specForm.water_temp_min) : null,
        water_temp_max: this.specForm.water_temp_max ? Number(this.specForm.water_temp_max) : null,
        mixing_method: String(this.specForm.mixing_method || ''),
        data_source: String(this.specForm.data_source || ''),
      }

      this.loading = true
      try {
        if (this.editingSpec?.id) {
          await api.put(`/admin/formula/specifications/${this.editingSpec.id}`, payload)
        } else {
          await api.post('/admin/formula/specifications', payload)
        }
        uni.showToast({ title: '已保存', icon: 'success' })
        this.closeSpecModal()
        await this.loadSpecs()
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    async verifySpec() {
      if (!this.editingSpec?.id) return
      this.loading = true
      try {
        await api.post(`/admin/formula/specifications/${this.editingSpec.id}/verify`, {})
        uni.showToast({ title: '已标记验证', icon: 'success' })
        this.closeSpecModal()
        await this.loadSpecs()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.admin-container {
  min-height: 100vh;
  padding: calc(16px + var(--nb-safe-top)) var(--nb-page-x) calc(20px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.header {
  padding: 6px 4px 12px;
}

.title {
  font-size: 22px;
  font-weight: 900;
  color: var(--nb-text);
  display: block;
}

.sub {
  margin-top: 6px;
  display: block;
  color: var(--nb-muted);
  font-size: 12px;
}

.tabs {
  display: flex;
  gap: 10px;
  margin: 10px 0 12px;
}

.tab {
  flex: 1;
  height: 40px;
  border-radius: 20px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--nb-muted);
  font-weight: 800;
  font-size: 13px;
}

.tab.active {
  background: rgba(247, 201, 72, 0.22);
  color: var(--nb-text);
  border-color: rgba(247, 201, 72, 0.55);
}

.card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 14px 36px rgba(27, 26, 23, 0.08);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 15px;
  font-weight: 900;
  color: var(--nb-text);
}

.card-sub {
  display: block;
  margin-top: 8px;
  color: var(--nb-muted);
  font-size: 12px;
  line-height: 1.4;
}

.chips {
  margin-top: 10px;
  white-space: nowrap;
}

.chips-inner {
  display: flex;
  gap: 10px;
  padding-bottom: 4px;
}

.chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(27, 26, 23, 0.04);
  display: flex;
  align-items: center;
  gap: 8px;
}

.chip.active {
  background: rgba(247, 201, 72, 0.22);
  border-color: rgba(247, 201, 72, 0.55);
}

.chip-text {
  font-size: 12px;
  font-weight: 900;
  color: var(--nb-text);
}

.chip-badge {
  font-size: 11px;
  color: var(--nb-text);
  background: rgba(247, 201, 72, 0.55);
  padding: 2px 6px;
  border-radius: 999px;
  font-weight: 800;
}

.row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.row-k {
  color: var(--nb-muted);
  font-size: 12px;
}

.row-v {
  flex: 1;
  color: var(--nb-text);
  font-weight: 900;
  font-size: 13px;
}

.filters {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter {
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(27, 26, 23, 0.04);
  color: var(--nb-muted);
  font-size: 12px;
}

.filter.active {
  background: rgba(247, 201, 72, 0.22);
  color: var(--nb-text);
  border-color: rgba(247, 201, 72, 0.55);
}

.list {
  margin-top: 12px;
}

.std-item, .spec-item {
  padding: 12px 12px;
  border-radius: var(--nb-radius-md);
  border: 1px solid rgba(27, 26, 23, 0.08);
  background: rgba(27, 26, 23, 0.03);
  margin-top: 10px;
}

.std-top, .spec-top {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.std-type, .spec-name {
  font-weight: 900;
  color: var(--nb-text);
  font-size: 13px;
}

.std-range, .spec-range {
  color: var(--nb-muted);
  font-size: 12px;
  flex: 1;
}

.std-flag, .spec-flag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  color: var(--nb-muted);
}

.std-flag.on, .spec-flag.on {
  background: rgba(82, 196, 26, 0.14);
  border-color: rgba(82, 196, 26, 0.24);
  color: rgba(27, 26, 23, 0.85);
}

.std-data, .spec-sub {
  margin-top: 8px;
  display: block;
  font-size: 12px;
  color: var(--nb-muted);
  line-height: 1.4;
}

.hint {
  padding: 10px 0 0;
}

.hint-text {
  color: var(--nb-muted);
  font-size: 12px;
}

.empty {
  padding: 12px 0;
}

.empty-text {
  color: var(--nb-muted);
  font-size: 12px;
}

.textarea {
  margin-top: 10px;
  width: 100%;
  min-height: 120px;
  padding: 12px;
  box-sizing: border-box;
  border-radius: var(--nb-radius-md);
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  color: var(--nb-text);
}

.textarea.small {
  min-height: 86px;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.ghost-btn, .primary-btn {
  height: 40px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 800;
}

.primary-btn {
  background: linear-gradient(135deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
  border: none;
  color: var(--nb-text);
  padding: 0 14px;
}

.ghost-btn {
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid var(--nb-border);
  color: var(--nb-text);
  padding: 0 14px;
}

.picker-btn {
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(27, 26, 23, 0.04);
}

.picker-text {
  font-size: 12px;
  font-weight: 900;
  color: var(--nb-text);
}

.modal-overlay {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  box-sizing: border-box;
}

.modal {
  width: 100%;
  max-width: 520px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: var(--nb-radius-lg);
  border: 1px solid var(--nb-border);
  padding: 14px;
  box-sizing: border-box;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.modal-title {
  font-size: 15px;
  font-weight: 900;
  color: var(--nb-text);
}

.close {
  font-size: 20px;
  color: var(--nb-muted);
}

.form {
  max-height: 60vh;
  overflow: auto;
}

.field {
  margin-top: 10px;
}

.k {
  display: block;
  font-size: 12px;
  color: var(--nb-muted);
  margin-bottom: 6px;
}

.input {
  width: 100%;
  height: 40px;
  border-radius: var(--nb-radius-md);
  border: 1px solid var(--nb-border);
  padding: 0 12px;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  color: var(--nb-text);
}

.twins {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dash {
  color: var(--nb-muted);
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  justify-content: flex-end;
}

.danger-row {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.verify-btn {
  height: 40px;
  border-radius: 20px;
  background: rgba(82, 196, 26, 0.16);
  border: 1px solid rgba(82, 196, 26, 0.28);
  color: rgba(27, 26, 23, 0.92);
  padding: 0 14px;
  font-size: 12px;
  font-weight: 900;
}
</style>
