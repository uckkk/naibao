<template>
  <view class="formula-page">
    <NbNetworkBanner />
    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="需要先创建宝宝，才能绑定奶粉品牌与冲泡规格"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbLoadable
      v-else
      :loading="pageLoading"
      :errorText="errorText"
      :empty="brands.length === 0"
      emptyTitle="暂无品牌数据"
      emptyDesc="请稍后重试，或检查服务器是否正常运行"
      emptyActionText="刷新"
      @retry="init"
      @emptyAction="init"
    >
      <template #skeleton>
        <view class="group">
          <view class="group-head">
            <NbSkeleton :w="72" :h="14" :radius="7" />
            <NbSkeleton :w="44" :h="14" :radius="7" />
          </view>

          <view class="cells">
            <view class="cell">
              <view class="cell-main">
                <NbSkeleton :w="140" :h="14" :radius="7" />
                <view style="margin-top:8px;">
                  <NbSkeleton :w="220" :h="12" :radius="6" />
                </view>
              </view>
              <NbSkeleton :w="46" :h="12" :radius="6" />
            </view>

            <view class="cell">
              <view class="cell-main">
                <NbSkeleton :w="84" :h="14" :radius="7" />
                <view style="margin-top:8px;">
                  <NbSkeleton :w="180" :h="12" :radius="6" />
                </view>
              </view>
              <NbSkeleton :w="10" :h="12" :radius="6" />
            </view>
          </view>
        </view>

        <view class="search-wrap">
          <NbSkeleton :w="'100%'" :h="44" :radius="16" />
        </view>

        <view class="group">
          <view class="group-head">
            <NbSkeleton :w="84" :h="14" :radius="7" />
            <view style="margin-top:8px;">
              <NbSkeleton :w="160" :h="12" :radius="6" />
            </view>
          </view>
          <view class="cells">
            <view v-for="i in 4" :key="i" class="cell">
              <view class="lead">
                <NbSkeleton :w="36" :h="36" :radius="18" />
              </view>
              <view class="cell-main">
                <NbSkeleton :w="140" :h="14" :radius="7" />
                <view style="margin-top:8px;">
                  <NbSkeleton :w="200" :h="12" :radius="6" />
                </view>
              </view>
              <NbSkeleton :w="44" :h="20" :radius="10" />
            </view>
          </view>
        </view>

        <view class="footer">
          <NbSkeleton :w="'100%'" :h="48" :radius="24" />
        </view>
      </template>
      <!-- 当前使用 -->
      <view class="group">
        <view class="group-head">
          <text class="group-title">当前使用</text>
          <text class="group-pill" v-if="!canEdit">只读</text>
        </view>

        <view class="cells">
          <view class="cell">
            <view class="cell-main">
              <text class="cell-title">{{ currentBrandName }}</text>
              <text class="cell-desc">{{ currentSelectionMeta }}</text>
            </view>
            <text class="cell-right">{{ currentSelection ? '已绑定' : '未绑定' }}</text>
          </view>

          <view class="cell tappable" v-if="babyId" @click="goToSpecDetail">
            <view class="cell-main">
              <text class="cell-title">冲泡要求</text>
              <text class="cell-desc">{{ specPreviewText }}</text>
            </view>
            <text class="chev">›</text>
          </view>
        </view>

        <view class="group-foot" v-if="!canEdit">
          <text class="group-foot-text">当前账号为成员，仅可查看。需要更换奶粉请让管理员操作。</text>
        </view>
      </view>

      <!-- 搜索（仅管理员可操作） -->
      <view class="search-wrap" v-if="canEdit">
        <view class="search-bar">
          <text class="search-icon">⌕</text>
          <input
            class="search-input"
            type="text"
            v-model="searchKey"
            placeholder="搜索品牌 / 英文名"
            placeholder-class="search-placeholder"
          />
          <text v-if="searchKey" class="search-clear" @click="clearSearch">×</text>
        </view>
      </view>

      <!-- 购买偏好（为未来 CPS/返利做铺垫：先解决“去哪买”这件事） -->
      <view class="group" v-if="canEdit">
        <view class="group-head">
          <text class="group-title">购买偏好</text>
          <text class="group-desc">打开同一渠道，少做一次选择</text>
        </view>
        <view class="chips">
          <view class="chip" :class="{ active: buyPlatform === 'official' }" @click="setBuyPlatform('official')">官方</view>
          <view class="chip" :class="{ active: buyPlatform === 'jd' }" @click="setBuyPlatform('jd')">京东</view>
          <view class="chip" :class="{ active: buyPlatform === 'tmall' }" @click="setBuyPlatform('tmall')">天猫</view>
          <view class="chip" :class="{ active: buyPlatform === 'pdd' }" @click="setBuyPlatform('pdd')">拼多多</view>
        </view>
      </view>

      <!-- 推荐 -->
      <view class="group" v-if="canEdit && recommendedBrands.length">
        <view class="group-head">
          <text class="group-title">为{{ babyNickname }}推荐</text>
          <text class="group-desc">{{ recommendHintText }}</text>
        </view>
        <view class="cells">
          <view v-for="brand in recommendedBrands" :key="brand.id" class="cell tappable" @click="selectBrand(brand)">
            <view class="lead" :style="{ background: getBrandColor(brand.name_cn) }">
              <text class="lead-text">{{ getBrandInitial(brand.name_cn) }}</text>
            </view>
            <view class="cell-main">
              <view class="cell-title-row">
                <text class="cell-title">{{ brand.name_cn }}</text>
                <text class="tag current" v-if="isCurrentBrand(brand.id)">当前</text>
                <text class="tag rec" v-else>热门</text>
              </view>
              <text class="cell-desc">{{ brandSubtitle(brand) }}</text>
            </view>
            <view class="link-chip" @click.stop="openBrandLink(brand)">{{ buyChipLabel(brand) }}</view>
          </view>
        </view>
      </view>

      <!-- 最近使用 -->
      <view class="group" v-if="canEdit && recentBrands.length">
        <view class="group-head">
          <text class="group-title">最近使用</text>
          <text class="group-desc">切换更快</text>
        </view>
        <view class="cells">
          <view v-for="brand in recentBrands" :key="brand.id" class="cell tappable" @click="selectBrand(brand)">
            <view class="lead" :style="{ background: getBrandColor(brand.name_cn) }">
              <text class="lead-text">{{ getBrandInitial(brand.name_cn) }}</text>
            </view>
            <view class="cell-main">
              <text class="cell-title">{{ brand.name_cn }}</text>
              <text class="cell-desc">{{ brandSubtitle(brand) }}</text>
            </view>
            <view class="link-chip" @click.stop="openBrandLink(brand)">{{ buyChipLabel(brand) }}</view>
          </view>
        </view>
      </view>

      <!-- 全部品牌 -->
      <view class="group" v-if="canEdit">
        <view class="group-head">
          <text class="group-title">全部品牌</text>
          <text class="group-desc">点选后可进一步选择规格</text>
        </view>
        <view class="cells">
          <view v-for="brand in filteredBrands" :key="brand.id" class="cell tappable brand-cell" @click="selectBrand(brand)">
            <view class="lead" :style="{ background: getBrandColor(brand.name_cn) }">
              <text class="lead-text">{{ getBrandInitial(brand.name_cn) }}</text>
            </view>
            <view class="cell-main">
              <text class="cell-title">{{ brand.name_cn }}</text>
              <text class="cell-desc">{{ brand.name_en || '' }}</text>
            </view>
            <text class="check" v-if="String(selectedBrandId) === String(brand.id)">✓</text>
            <text class="chev" v-else>›</text>
          </view>
        </view>
      </view>

      <!-- 规格 -->
	      <view class="group" id="spec-section" v-if="canEdit && selectedBrandId">
	        <view class="group-head">
	          <text class="group-title">系列/冲泡规格</text>
	          <text class="group-desc">用于勺数与水温提示（可选）</text>
	        </view>

          <!-- 段数/适用月龄：即使没有官方规格数据，也允许手动设置（用于展示与提醒） -->
          <view class="stage-head">
            <text class="stage-title">段数</text>
            <text class="stage-desc">用于展示与提醒</text>
          </view>
          <view class="chips stage-chips">
            <view class="chip" :class="{ active: !selectedAgeRange }" @click="setAgeRange('')">自动</view>
            <view class="chip" :class="{ active: selectedAgeRange === '0-6' }" @click="setAgeRange('0-6')">1段</view>
            <view class="chip" :class="{ active: selectedAgeRange === '6-12' }" @click="setAgeRange('6-12')">2段</view>
            <view class="chip" :class="{ active: selectedAgeRange === '12-36' }" @click="setAgeRange('12-36')">3段</view>
            <view class="chip" :class="{ active: selectedAgeRange === '36+' }" @click="setAgeRange('36+')">4段</view>
          </view>
	
	        <view v-if="specLoading" class="inner-hint">
	          <text class="inner-hint-text">加载规格中...</text>
	        </view>

        <view v-else-if="specifications.length === 0" class="inner-hint">
          <text class="inner-hint-text">该品牌暂无官方规格数据，可直接确认（冲泡请以包装说明为准）</text>
        </view>

        <view v-else class="cells">
          <view
            v-for="spec in specifications"
            :key="spec.id"
            class="cell tappable"
            @click="selectSpec(spec)"
          >
            <view class="cell-main">
              <text class="cell-title">{{ spec.series_name || '默认系列' }}</text>
              <text class="cell-desc">{{ formatAgeRange(spec.age_range) }} · {{ formatScoopMeta(spec) }}</text>
            </view>
            <text class="check" v-if="String(selectedSpecId) === String(spec.id)">✓</text>
            <text class="chev" v-else>›</text>
          </view>
        </view>

        <view class="group-foot">
          <text class="group-foot-text">提示：未来若包含返利/推广链接，会在这里明确标注。</text>
        </view>
      </view>

      <!-- 保存 -->
      <view class="footer" v-if="canEdit">
        <button class="nb-primary-btn formula-save-btn" :disabled="confirmDisabled || saving" @click="confirmSelection">
          {{ saving ? '保存中...' : confirmText }}
        </button>
      </view>
    </NbLoadable>

    <NbConfirmSheet
      :visible="confirmSheetVisible"
      :title="confirmSheetTitle"
      :desc="confirmSheetDesc"
      :confirmText="confirmSheetConfirmText"
      :cancelText="confirmSheetCancelText"
      :confirmVariant="confirmSheetVariant"
      :loading="confirmSheetLoading"
      @confirm="handleConfirmSheetConfirm"
      @cancel="handleConfirmSheetCancel"
    />
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import NbState from '@/components/NbState.vue'
import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
import { parseBirthDateToLocal, diffYmd } from '@/utils/age'
import { formatStageTextFromAgeRange } from '@/utils/formula_stage'
import NbLoadable from '@/components/NbLoadable.vue'
import NbSkeleton from '@/components/NbSkeleton.vue'
import NbConfirmSheet from '@/components/NbConfirmSheet.vue'

export default {
  components: { NbState, NbNetworkBanner, NbLoadable, NbSkeleton, NbConfirmSheet },
  data() {
    return {
      babyId: null,
      baby: null,
      meId: null,
      myRole: '',
      pageLoading: false,
      brands: [],
      errorText: '',
      selectedBrandId: null,
      selectedBrand: null,
      currentSelection: null,
      specifications: [],
      selectedSpecId: null,
      selectedAgeRange: '', // 手动段数（写入 selection.age_range）；为空表示“自动/不指定”

      specLoading: false,
      saving: false,
      searchKey: '',
      recentBrandIds: [],

      buyPlatform: 'official', // official | jd | tmall | pdd

      // 统一 iOS 风格确认 Sheet（替代 uni.showModal）
      confirmSheetVisible: false,
      confirmSheetTitle: '',
      confirmSheetDesc: '',
      confirmSheetConfirmText: '确定',
      confirmSheetCancelText: '取消',
      confirmSheetVariant: 'primary', // primary | danger
      confirmSheetLoading: false,
      confirmSheetResolver: null,
    }
  },

  computed: {
    canEdit() {
      if (this.myRole) return this.myRole === 'admin'
      return String(this.baby?.user_id || '') === String(this.meId || '')
    },
    babyNickname() {
      return this.baby?.nickname || '宝宝'
    },
    babyAgeMonthsInt() {
      const birth = parseBirthDateToLocal(this.baby?.birth_date)
      if (!birth) return 0
      const { years, months } = diffYmd(birth, new Date())
      return Math.max(0, years * 12 + months)
    },
    recommendedAgeRange() {
      const m = Number(this.babyAgeMonthsInt || 0)
      if (!Number.isFinite(m)) return ''
      if (m < 6) return '0-6'
      if (m < 12) return '6-12'
      if (m < 36) return '12-36'
      return '36+'
    },
    recommendHintText() {
      const range = this.recommendedAgeRange
      if (range) return `${range}月段位更匹配`
      return '按热门与可用规格推荐'
    },
    currentBrandName() {
      return this.currentSelection?.brand?.name_cn || '未绑定奶粉'
    },
    currentSelectionMeta() {
      if (!this.currentSelection) return '绑定后可显示勺数、水温与冲泡步骤'
      const parts = []
      const series = String(this.currentSelection.series_name || '').trim()
      const range = String(this.currentSelection.age_range || '').trim()
      const stage = formatStageTextFromAgeRange(range)
      if (series) parts.push(series)
      if (stage) parts.push(stage)
      else if (range) parts.push(`${range}月`)
      return parts.join(' · ') || '—'
    },
    specPreviewText() {
      if (!this.currentSelection) return '未绑定奶粉'
      const v = this.currentSelectionMeta
      return v || '查看勺数、水温与步骤'
    },
    filteredBrands() {
      const key = String(this.searchKey || '').trim().toLowerCase()
      const list = Array.isArray(this.brands) ? this.brands : []
      if (!key) return list
      return list.filter((b) => {
        const cn = String(b?.name_cn || '').toLowerCase()
        const en = String(b?.name_en || '').toLowerCase()
        return cn.includes(key) || en.includes(key)
      })
    },
    recommendedBrands() {
      const list = Array.isArray(this.brands) ? this.brands.slice() : []
      list.sort((a, b) => Number(b?.market_share || 0) - Number(a?.market_share || 0))
      return list.slice(0, 4)
    },
    recentBrands() {
      const ids = Array.isArray(this.recentBrandIds) ? this.recentBrandIds : []
      const map = new Map((this.brands || []).map((b) => [String(b.id), b]))
      const out = []
      for (const id of ids) {
        const hit = map.get(String(id))
        if (hit) out.push(hit)
      }
      return out
    },
    confirmDisabled() {
      if (!this.selectedBrandId) return true
      // “已是当前”不需要重复保存，避免无意覆盖/清空字段
      return this.confirmText === '已是当前奶粉'
    },
    confirmText() {
      if (!this.selectedBrandId) return '选择奶粉'
      const sameBrand = String(this.currentSelection?.brand_id || '') === String(this.selectedBrandId || '')
      if (!sameBrand) return '保存为当前奶粉'
      // 同品牌时：若规格也一致则提示已是当前
      const curSeries = String(this.currentSelection?.series_name || '')
      const curRange = String(this.currentSelection?.age_range || '')
      const spec = this.specifications.find((s) => String(s.id) === String(this.selectedSpecId))
      const nextSeries = spec ? String(spec?.series_name || '') : curSeries
      const nextRange = spec ? String(spec?.age_range || '') : String(this.selectedAgeRange || '')

      const sameSpec = nextSeries === curSeries && nextRange === curRange
      if (sameSpec) return '已是当前奶粉'

      const rangeChanged = nextRange !== curRange
      const seriesChanged = nextSeries !== curSeries
      if (rangeChanged && !seriesChanged) return nextRange ? '切换段数' : '自动段数'
      if (seriesChanged && !rangeChanged) return '切换系列'
      return '更新规格'
    },
  },
  
  onLoad(options) {
    const userStore = useUserStore()
    this.meId = userStore.user?.id || null

    if (options.babyId) {
      this.babyId = options.babyId
    } else {
      if (userStore.currentBaby) {
        this.babyId = userStore.currentBaby.id
        this.baby = userStore.currentBaby
      }
    }

    this.readRecent()
    this.readBuyPlatform()
  },

  onShow() {
    const userStore = useUserStore()
    // 多宝宝：默认全局跟随 currentBaby
    if (userStore.currentBaby?.id) {
      this.babyId = userStore.currentBaby.id
      this.baby = userStore.currentBaby
    }
    this.init()
  },
  
  methods: {
    onNbRetry() {
      this.init()
    },

    openConfirmSheet(opts = {}) {
      // Promise-based sheet so async flows stay readable.
      return new Promise((resolve) => {
        this.confirmSheetTitle = String(opts.title || '').trim()
        this.confirmSheetDesc = String(opts.desc || '').trim()
        this.confirmSheetConfirmText = String(opts.confirmText || '确定')
        this.confirmSheetCancelText = String(opts.cancelText || '取消')
        this.confirmSheetVariant = String(opts.variant || 'primary')
        this.confirmSheetLoading = false
        this.confirmSheetVisible = true
        this.confirmSheetResolver = resolve
      })
    },

    handleConfirmSheetConfirm() {
      const resolve = this.confirmSheetResolver
      this.confirmSheetVisible = false
      this.confirmSheetResolver = null
      resolve && resolve(true)
    },

    handleConfirmSheetCancel() {
      const resolve = this.confirmSheetResolver
      this.confirmSheetVisible = false
      this.confirmSheetResolver = null
      resolve && resolve(false)
    },

    async init() {
      if (!this.babyId) return
      this.pageLoading = true
      this.errorText = ''
      try {
        await Promise.all([this.loadBaby(), this.loadMyRole(), this.loadBrands()])
        await this.loadCurrentSelection()
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    async loadBaby() {
      if (!this.babyId) return
      // 已有 currentBaby 且 id 一致，直接用；否则拉取一次，保证月龄计算正确
      const userStore = useUserStore()
      if (userStore.currentBaby?.id && String(userStore.currentBaby.id) === String(this.babyId)) {
        this.baby = userStore.currentBaby
        return
      }
      const res = await api.get(`/babies/${this.babyId}`)
      this.baby = res.baby || null
    },

    async loadMyRole() {
      if (!this.babyId) return
      try {
        const res = await api.get(`/babies/${this.babyId}/family-members`)
        const members = Array.isArray(res.members) ? res.members : []
        const me = members.find((m) => String(m.user_id) === String(this.meId))
        this.myRole = me?.role || ''
      } catch {
        // 网络失败时不阻塞：用 baby.user_id 兜底推断
        this.myRole = ''
      }
    },

    async loadBrands() {
      const res = await api.get('/formula/brands')
      this.brands = Array.isArray(res.brands) ? res.brands : []
    },

    async loadCurrentSelection() {
      if (!this.babyId) return
      try {
        const res = await api.get(`/babies/${this.babyId}/formula`, {}, { silent: true })
        const sel = res.selection || null
        this.currentSelection = sel
        this.selectedAgeRange = String(sel?.age_range || '')
        if (sel?.brand_id) {
          this.selectedBrandId = sel.brand_id
          this.selectedBrand = sel.brand || null
          await this.loadSpecifications(sel.brand_id, { preferSeries: sel.series_name, preferRange: sel.age_range })
        }
      } catch {
        this.currentSelection = null
        this.selectedAgeRange = ''
      }
    },

    selectBrand(brand) {
      if (!this.canEdit) {
        uni.showToast({ title: '仅管理员可更换奶粉', icon: 'none' })
        return
      }
      if (!brand?.id) return
      const sameBrand = String(this.currentSelection?.brand_id || '') === String(brand.id)
      this.selectedBrandId = brand.id
      this.selectedBrand = brand
      this.selectedSpecId = null
      this.selectedAgeRange = sameBrand ? String(this.currentSelection?.age_range || '') : ''
      this.loadSpecifications(brand.id)
        .finally(() => {
          // 选中品牌后把规格区域滚到可见，减少“找不到下一步”
          this.$nextTick(() => {
            try {
              uni.pageScrollTo({ selector: '#spec-section', duration: 220 })
            } catch {}
          })
        })
    },

    async loadSpecifications(brandId, opts = {}) {
      if (!brandId) {
        this.specifications = []
        this.selectedSpecId = null
        return
      }
      this.specLoading = true
      try {
        const res = await api.get('/formula/specifications', { brand_id: brandId })
        this.specifications = Array.isArray(res.specifications) ? res.specifications : []
        this.selectedSpecId = this.pickBestSpecId(this.specifications, opts)
      } catch {
        this.specifications = []
        this.selectedSpecId = null
      } finally {
        this.specLoading = false
      }
    },

    pickBestSpecId(specs, opts = {}) {
      const list = Array.isArray(specs) ? specs : []
      if (list.length === 0) return null

      const preferSeries = String(opts.preferSeries || '').trim()
      const preferRange = String(opts.preferRange || '').trim()
      if (preferSeries || preferRange) {
        const hit = list.find((s) => String(s.series_name || '') === preferSeries && String(s.age_range || '') === preferRange)
        if (hit?.id) return hit.id
      }

      const targetMonths = Number(this.babyAgeMonthsInt || 0)
      if (Number.isFinite(targetMonths)) {
        const best = list.find((s) => this.isMonthsInRange(targetMonths, s.age_range))
        if (best?.id) return best.id
      }

      // 兜底：第一条
      return list[0]?.id || null
    },

    isMonthsInRange(months, ageRange) {
      const s = String(ageRange || '').trim()
      const m = s.match(/^(\\d+)\\s*-\\s*(\\d+)$/)
      if (!m) return false
      const min = Number(m[1])
      const max = Number(m[2])
      if (!Number.isFinite(min) || !Number.isFinite(max)) return false
      return months >= min && months < max
    },

    selectSpec(spec) {
      if (!spec?.id) return
      this.selectedSpecId = spec.id
      if (spec?.age_range != null) this.selectedAgeRange = String(spec.age_range || '')
    },

    setAgeRange(range) {
      const next = String(range || '').trim()
      this.selectedAgeRange = next
      // “自动”代表不指定段数：避免被某个规格强行覆盖
      if (!next) {
        this.selectedSpecId = null
        return
      }

      const list = Array.isArray(this.specifications) ? this.specifications : []
      const hit = list.find((s) => String(s?.age_range || '').trim() === next)
      this.selectedSpecId = hit?.id || null
    },

    async confirmSelection() {
      if (!this.canEdit) {
        uni.showToast({ title: '仅管理员可更换奶粉', icon: 'none' })
        return
      }

      if (!this.selectedBrandId || !this.babyId || this.saving) {
        uni.showToast({
          title: this.babyId ? '请选择奶粉品牌' : '请先创建宝宝档案',
          icon: 'none'
        })
        if (!this.babyId) this.goToBabyInfo()
        return
      }

      const prevSelection = this.currentSelection ? { ...this.currentSelection } : null
      const prevBrandId = prevSelection?.brand_id || null
      const sameBrand = !!(prevBrandId && String(prevBrandId) === String(this.selectedBrandId))
      const brandChanged = !!(prevBrandId && String(prevBrandId) !== String(this.selectedBrandId))

      try {
        this.saving = true
        const spec = this.specifications.find((s) => String(s.id) === String(this.selectedSpecId))

        // 后端的 SelectFormula 会把 series_name/age_range 写回 selection（缺省为空），这里显式构造“最终要保存的值”，避免误清空。
        const payload = {
          brand_id: this.selectedBrandId,
          series_name: sameBrand ? String(prevSelection?.series_name || '') : '',
          age_range: sameBrand ? String(prevSelection?.age_range || '') : '',
        }
        if (spec) {
          payload.series_name = String(spec?.series_name || '')
          payload.age_range = String(spec?.age_range || payload.age_range || '')
        } else {
          payload.age_range = String(this.selectedAgeRange || '')
        }

        const prevRange = String(prevSelection?.age_range || '')
        const prevSeries = String(prevSelection?.series_name || '')
        const nextRange = String(payload.age_range || '')
        const nextSeries = String(payload.series_name || '')
        const rangeChanged = !brandChanged && nextRange !== prevRange
        const seriesChanged = !brandChanged && nextSeries !== prevSeries

        // 无变化：直接退出（避免重复保存造成字段被覆盖/时间戳抖动）
        if (!brandChanged && sameBrand && !rangeChanged && !seriesChanged) {
          uni.showToast({ title: '已是当前奶粉', icon: 'none' })
          return
        }

        await api.post(`/babies/${this.babyId}/formula`, payload)

        this.pushRecent(this.selectedBrandId)

        // 刷新当前绑定，用于下一次进入展示
        await this.loadCurrentSelection()

        // 品牌变更：引导开启 7 天转奶期（低风险：交替喂次，不做同次混合的精确勺数引导）
        let startedWeaning = false
        if (brandChanged && prevSelection?.brand_id) {
          let hasExistingPlan = false
          try {
            const wp = await api.get(`/babies/${this.babyId}/weaning-plan`, {}, { silent: true })
            hasExistingPlan = !!wp?.plan
          } catch {
            hasExistingPlan = false
          }

          const title = hasExistingPlan ? '开始新的转奶期？' : '开始转奶期？'
          const desc = hasExistingPlan
            ? '将结束当前转奶期，并按“旧奶粉 → 新奶粉”开启 7 天转奶期（交替喂次，不混合）。'
            : '按“旧奶粉 → 新奶粉”开启 7 天转奶期（交替喂次，不混合）。'

          const ok = await this.openConfirmSheet({
            title,
            desc,
            cancelText: '暂不',
            confirmText: '开始 7 天转奶',
            variant: 'primary',
          })
          if (ok) {
            try {
              await api.post(`/babies/${this.babyId}/weaning-plan`, {
                mode: 'alternate',
                duration_days: 7,
                old_brand_id: prevSelection.brand_id,
                old_series_name: prevSelection.series_name || '',
                old_age_range: prevSelection.age_range || '',
                new_brand_id: this.selectedBrandId,
                new_series_name: payload.series_name || '',
                new_age_range: payload.age_range || '',
              })
              startedWeaning = true
            } catch (e) {
              uni.showToast({ title: e?.message || '开启转奶期失败', icon: 'none' })
            }
          }
        }

        uni.showToast({
          title: startedWeaning
            ? '已开启转奶期'
            : brandChanged
              ? '已更换奶粉'
              : rangeChanged
                ? (nextRange ? `已切换到 ${formatStageTextFromAgeRange(nextRange) || '新段数'}` : '已改为自动段数')
                : seriesChanged
                  ? '已切换系列'
                  : '选择成功',
          icon: 'success'
        })

        // 返回上一页（给 toast 留一点时间）
        setTimeout(() => uni.navigateBack(), 450)
      } catch (error) {
        uni.showToast({
          title: error.message || '选择失败',
          icon: 'none'
        })
      } finally {
        this.saving = false
      }
    },

    goToSpecDetail() {
      if (!this.babyId) return
      uni.navigateTo({ url: `/pages/formula-spec/index?babyId=${this.babyId}` })
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
    },

    clearSearch() {
      this.searchKey = ''
    },
    
    getBrandInitial(name) {
      if (!name) return ''
      return name.charAt(0)
    },
    
    getBrandColor(name) {
      const colors = {
        '飞鹤': '#1890ff',
        '金领冠': '#52c41a',
        '君乐宝': '#faad14',
        '贝因美': '#f5222d',
        '澳优': '#722ed1',
        '爱他美': '#f5222d',
        '合生元': '#722ed1',
        '伊利': '#1890ff',
        '蒙牛': '#52c41a',
        '美素佳儿': '#722ed1',
        '惠氏': '#722ed1',
        'a2': '#1890ff'
      }
      return colors[name] || '#999'
    },

    isCurrentBrand(brandId) {
      return String(this.currentSelection?.brand_id || '') === String(brandId || '')
    },

    brandSubtitle(brand) {
      // iOS 风格：副标题只给“一句话”，不塞市场份额/长特性
      const features = Array.isArray(brand?.features) ? brand.features : []
      const pick = features.slice(0, 2).join(' · ')
      const range = this.recommendedAgeRange ? `${this.recommendedAgeRange}月` : ''
      return [pick, range].filter(Boolean).join(' · ') || '—'
    },

    buyChipLabel(brand) {
      const p = String(this.buyPlatform || 'official')
      if (p === 'jd') return '京东'
      if (p === 'tmall') return '天猫'
      if (p === 'pdd') return '拼多多'
      return String(brand?.official_url || '').trim() ? '官网' : '搜索'
    },

    openBrandLink(brand) {
      const url = this.buildBuyUrl(brand)
      if (!url) {
        const name = String(brand?.name_cn || '').trim()
        if (!name) return
        uni.setClipboardData({ data: name })
        uni.showToast({ title: '已复制品牌名，可去平台搜索', icon: 'none' })
        return
      }
      // H5：直接跳转；其他端：先复制链接（避免无 WebView 页面时卡住）
      if (typeof window !== 'undefined' && window.location) {
        window.open ? window.open(url, '_blank') : (window.location.href = url)
        return
      }
      uni.setClipboardData({ data: url })
      uni.showToast({ title: '已复制链接', icon: 'none' })
    },

    buildBuyUrl(brand) {
      const name = String(brand?.name_cn || '').trim()
      const official = String(brand?.official_url || '').trim()
      const p = String(this.buyPlatform || 'official')
      if (p === 'official') return official ? this.appendUtm(official) : ''
      if (!name) return official ? this.appendUtm(official) : ''

      const q = encodeURIComponent(name)
      if (p === 'jd') return `https://so.m.jd.com/ware/search.action?keyword=${q}`
      if (p === 'tmall') return `https://s.m.tmall.com/m/search.htm?q=${q}`
      if (p === 'pdd') return `https://mobile.yangkeduo.com/search_result.html?search_key=${q}`
      return official ? this.appendUtm(official) : ''
    },

    appendUtm(url) {
      try {
        const u = new URL(url)
        if (!u.searchParams.get('utm_source')) u.searchParams.set('utm_source', 'naibao')
        if (!u.searchParams.get('utm_medium')) u.searchParams.set('utm_medium', 'app')
        return u.toString()
      } catch {
        return url
      }
    },

    readRecent() {
      if (!this.babyId) return
      const key = `recent_formula_brand_ids:${this.babyId}`
      try {
        const v = uni.getStorageSync(key)
        const ids = Array.isArray(v) ? v : []
        this.recentBrandIds = ids.map((x) => String(x)).slice(0, 6)
      } catch {
        this.recentBrandIds = []
      }
    },

    pushRecent(brandId) {
      if (!this.babyId || !brandId) return
      const key = `recent_formula_brand_ids:${this.babyId}`
      const id = String(brandId)
      const next = [id, ...(this.recentBrandIds || []).filter((x) => String(x) !== id)].slice(0, 6)
      this.recentBrandIds = next
      try {
        uni.setStorageSync(key, next)
      } catch {}
    },

    readBuyPlatform() {
      try {
        const v = uni.getStorageSync('buy_platform_pref')
        const s = String(v || '').trim()
        if (s) this.buyPlatform = s
      } catch {}
    },

    setBuyPlatform(v) {
      const next = String(v || '').trim()
      if (!next) return
      this.buyPlatform = next
      try {
        uni.setStorageSync('buy_platform_pref', next)
      } catch {}
    },

    formatAgeRange(ageRange) {
      const s = String(ageRange || '').trim()
      if (!s) return ''
      const stage = formatStageTextFromAgeRange(s)
      if (stage) return stage
      if (s.includes('-')) return `${s}个月`
      return s
    },

    formatScoopMeta(spec) {
      if (!spec) return ''
      const scoopMl = Number(spec.scoop_ml || 0)
      const mlText = scoopMl > 0 ? `${scoopMl}ml/勺` : ''
      const tMin = spec.water_temp_min
      const tMax = spec.water_temp_max
      const tempText = (tMin || tMax) ? `${tMin || ''}-${tMax || ''}℃` : ''
      return [mlText, tempText].filter(Boolean).join(' · ') || '—'
    }
  }
}
</script>

<style scoped>
.formula-page {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + var(--nb-safe-top)) var(--nb-page-x)
    calc(120px + var(--nb-safe-bottom));
  box-sizing: border-box;
}

.group {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(27, 26, 23, 0.08);
  margin-bottom: 14px;
}

.group-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  padding: 14px 14px 8px;
}

.group-title {
  font-size: 15px;
  font-weight: 900;
  color: var(--nb-text);
}

.group-desc {
  font-size: 12px;
  color: var(--nb-muted);
}

.group-pill {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.72);
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  padding: 3px 8px;
  border-radius: 999px;
  font-weight: 800;
}

.cells {
  display: flex;
  flex-direction: column;
}

.cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 12px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
  gap: 10px;
}

.cell:first-child {
  border-top: none;
}

.tappable:active {
  background: rgba(27, 26, 23, 0.03);
}

.lead {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 40px;
}

.lead-text {
  color: #fff;
  font-size: 16px;
  font-weight: 900;
}

.cell-main {
  flex: 1;
  min-width: 0;
}

.cell-title-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.cell-title {
  font-size: 15px;
  font-weight: 900;
  color: var(--nb-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-desc {
  display: block;
  margin-top: 3px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-right {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.56);
  font-weight: 800;
}

.chev {
  font-size: 18px;
  color: rgba(27, 26, 23, 0.38);
  font-weight: 900;
}

.check {
  font-size: 16px;
  color: var(--nb-text);
  font-weight: 900;
}

.tag {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
  color: rgba(27, 26, 23, 0.66);
  font-weight: 800;
}

.tag.rec {
  border-color: rgba(247, 201, 72, 0.40);
  background: rgba(247, 201, 72, 0.18);
  color: rgba(181, 83, 29, 0.95);
}

.tag.current {
  border-color: rgba(27, 26, 23, 0.18);
}

.link-chip {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.04);
  color: rgba(27, 26, 23, 0.72);
  font-weight: 800;
}

.link-chip:active {
  background: rgba(27, 26, 23, 0.08);
}

.group-foot {
  padding: 10px 14px 14px;
  border-top: 1px solid rgba(27, 26, 23, 0.08);
}

.group-foot-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.56);
  line-height: 1.5;
}

.search-wrap {
  margin-bottom: 14px;
}

.chips {
  display: flex;
  gap: 10px;
  padding: 0 14px 14px;
  flex-wrap: wrap;
}

.stage-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 14px 8px;
}

.stage-title {
  font-size: 13px;
  font-weight: 900;
  color: var(--nb-text);
}

.stage-desc {
  font-size: 12px;
  color: var(--nb-muted);
}

.chips.stage-chips {
  padding-top: 0;
}

.chip {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.72);
  color: var(--nb-muted);
  font-size: 12px;
  user-select: none;
}

.chip.active {
  background: rgba(247, 201, 72, 0.22);
  color: var(--nb-text);
  border-color: rgba(247, 201, 72, 0.55);
  font-weight: 800;
}

.search-bar {
  display: flex;
  flex-direction: row;
  align-items: center;
  background: rgba(27, 26, 23, 0.06);
  border: 1px solid rgba(27, 26, 23, 0.10);
  border-radius: 16px;
  padding: 10px 12px;
  gap: 8px;
}

.search-icon {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.52);
  font-weight: 900;
}

.search-input {
  flex: 1;
  height: 22px;
  font-size: 14px;
  color: var(--nb-text);
}

.search-clear {
  width: 22px;
  height: 22px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(27, 26, 23, 0.10);
  color: rgba(27, 26, 23, 0.62);
  font-weight: 900;
}

.inner-hint {
  padding: 0 14px 14px;
}

.inner-hint-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.56);
  line-height: 1.6;
}

.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px var(--nb-page-x);
  padding-bottom: calc(12px + var(--nb-safe-bottom));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1px solid rgba(27, 26, 23, 0.10);
}
</style>
