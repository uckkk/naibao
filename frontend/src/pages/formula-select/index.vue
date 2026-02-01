<template>
  <view class="formula-select-container">
    <NbState
      v-if="!babyId"
      type="info"
      title="还没有宝宝档案"
      desc="需要先创建宝宝，才能绑定奶粉品牌与规格"
      actionText="去建档"
      @action="goToBabyInfo"
    />

    <NbState v-else-if="loadingBrands" type="loading" title="加载品牌中..." />

    <NbState
      v-else-if="errorText"
      type="error"
      title="品牌加载失败"
      :desc="errorText"
      actionText="重试"
      @action="loadBrands"
    />

    <NbState
      v-else-if="brands.length === 0"
      type="empty"
      title="暂无品牌数据"
      desc="请稍后重试，或检查服务器是否正常运行"
      actionText="刷新"
      @action="loadBrands"
    />

    <!-- 品牌列表 -->
    <view class="brands-grid" v-else>
      <view 
        v-for="brand in brands" 
        :key="brand.id"
        :class="['brand-card', { selected: selectedBrandId === brand.id }]"
        @click="selectBrand(brand)"
      >
        <!-- Logo -->
        <view class="brand-logo" :style="{ background: getBrandColor(brand.name_cn) }">
          <text class="logo-text">{{ getBrandInitial(brand.name_cn) }}</text>
        </view>
        
        <!-- 品牌名称 -->
        <text class="brand-name-cn">{{ brand.name_cn }}</text>
        <text class="brand-name-en">{{ brand.name_en }}</text>
        
        <!-- 特性标签 -->
        <view class="features">
          <text 
            v-for="(feature, index) in brand.features.slice(0, 3)" 
            :key="index"
            class="feature-tag"
          >
            {{ feature }}
          </text>
        </view>
        
        <!-- 市场份额 -->
        <text class="market-share">市场份额: {{ brand.market_share }}%</text>
      </view>
    </view>

    <!-- 规格/系列（可选增强）：有官方数据则引导选择，便于勺数/冲泡提示 -->
    <view class="spec-section" v-if="selectedBrandId">
      <view class="spec-head">
        <text class="spec-title">系列/冲泡规格</text>
        <text class="spec-link" v-if="babyId" @click="goToSpecDetail">查看冲泡要求</text>
      </view>

      <view v-if="specifications.length === 0" class="spec-empty">
        <text class="spec-empty-text">该品牌暂无官方规格数据，先选品牌也可使用（冲泡请以包装说明为准）</text>
      </view>

      <view v-else class="spec-list">
        <view
          v-for="spec in specifications"
          :key="spec.id"
          :class="['spec-card', { selected: selectedSpecId === spec.id }]"
          @click="selectSpec(spec)"
        >
          <view class="spec-row">
            <text class="spec-name">{{ spec.series_name || '默认系列' }}</text>
            <text class="spec-range">{{ formatAgeRange(spec.age_range) }}</text>
          </view>
          <text class="spec-meta">
            {{ formatScoopMeta(spec) }}
          </text>
        </view>
      </view>
    </view>

    <!-- 确认按钮 -->
    <view class="confirm-section" v-if="babyId && !loadingBrands && !errorText && brands.length > 0">
      <button 
        class="nb-primary-btn confirm-btn" 
        :disabled="!selectedBrandId || (specifications.length > 0 && !selectedSpecId)"
        @click="confirmSelection"
      >
        确认选择
      </button>
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
      brands: [],
      loadingBrands: false,
      errorText: '',
      selectedBrandId: null,
      selectedBrand: null,

      specifications: [],
      selectedSpecId: null,
    }
  },
  
  onLoad(options) {
    if (options.babyId) {
      this.babyId = options.babyId
    } else {
      const userStore = useUserStore()
      if (userStore.currentBaby) {
        this.babyId = userStore.currentBaby.id
      }
    }
    
    this.loadBrands()
    this.loadCurrentSelection()
  },
  
  methods: {
    async loadBrands() {
      if (!this.babyId) return
      this.loadingBrands = true
      this.errorText = ''
      try {
        const res = await api.get('/formula/brands')
        this.brands = Array.isArray(res.brands) ? res.brands : []
      } catch (error) {
        this.brands = []
        this.errorText = error?.message || '加载失败'
      } finally {
        this.loadingBrands = false
      }
    },
    
    async loadCurrentSelection() {
      if (!this.babyId) return
      
      try {
        const res = await api.get(`/babies/${this.babyId}/formula`)
        if (res.selection) {
          this.selectedBrandId = res.selection.brand_id
          this.selectedBrand = res.selection
          await this.loadSpecifications(res.selection.brand_id)
          const series = res.selection.series_name
          const range = res.selection.age_range
          if (series || range) {
            const hit = this.specifications.find((s) => s.series_name === series && s.age_range === range)
            if (hit) this.selectedSpecId = hit.id
          }
        }
      } catch (error) {
        // 未选择，忽略错误
      }
    },
    
    selectBrand(brand) {
      this.selectedBrandId = brand.id
      this.selectedBrand = brand
      this.selectedSpecId = null
      this.loadSpecifications(brand.id)
    },

    async loadSpecifications(brandId) {
      if (!brandId) {
        this.specifications = []
        this.selectedSpecId = null
        return
      }
      try {
        const res = await api.get('/formula/specifications', { brand_id: brandId })
        this.specifications = Array.isArray(res.specifications) ? res.specifications : []
        // 默认选中第一条，减少操作步骤（也便于“勺数提示”闭环）
        if (this.specifications.length > 0 && !this.selectedSpecId) {
          this.selectedSpecId = this.specifications[0].id
        }
      } catch (e) {
        this.specifications = []
        this.selectedSpecId = null
      }
    },

    selectSpec(spec) {
      if (!spec || !spec.id) return
      this.selectedSpecId = spec.id
    },
    
    async confirmSelection() {
      if (!this.selectedBrandId || !this.babyId) {
        uni.showToast({
          title: this.babyId ? '请选择奶粉品牌' : '请先创建宝宝档案',
          icon: 'none'
        })
        if (!this.babyId) this.goToBabyInfo()
        return
      }
      
      try {
        const payload = { brand_id: this.selectedBrandId }
        const spec = this.specifications.find((s) => String(s.id) === String(this.selectedSpecId))
        if (spec) {
          if (spec.series_name) payload.series_name = spec.series_name
          if (spec.age_range) payload.age_range = spec.age_range
        }
        await api.post(`/babies/${this.babyId}/formula`, payload)
        
        uni.showToast({
          title: '选择成功',
          icon: 'success'
        })
        
        // 返回上一页
        setTimeout(() => {
          uni.navigateBack()
        }, 500)
      } catch (error) {
        uni.showToast({
          title: error.message || '选择失败',
          icon: 'none'
        })
      }
    },

    goToSpecDetail() {
      if (!this.babyId) return
      uni.navigateTo({ url: `/pages/formula-spec/index?babyId=${this.babyId}` })
    },

    goToBabyInfo() {
      uni.navigateTo({ url: '/pages/baby-info/index' })
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

    formatAgeRange(ageRange) {
      const s = String(ageRange || '').trim()
      if (!s) return ''
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
.formula-select-container {
  min-height: 100vh;
  background: transparent;
  padding: calc(16px + env(safe-area-inset-top, 0px)) var(--nb-page-x)
    calc(120px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
}

.brands-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: space-between;
}

.brand-card {
  width: 31%;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16rpx;
  padding: 30rpx 20rpx;
  text-align: center;
  border: 2rpx solid transparent;
  transition: all 0.3s;
  margin-bottom: 16rpx;
}

.brand-card.selected {
  border-color: var(--nb-accent);
  background: rgba(247, 201, 72, 0.18);
}

.brand-logo {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50rpx;
  margin: 0 auto 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 48rpx;
  font-weight: bold;
  color: #fff;
}

.brand-name-cn {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.brand-name-en {
  font-size: 22rpx;
  color: #999;
  display: block;
  margin-bottom: 15rpx;
}

.features {
  margin: 15rpx 0;
}

.feature-tag {
  display: inline-block;
  font-size: 20rpx;
  color: #666;
  background: #f5f5f5;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
  margin: 4rpx;
}

.market-share {
  font-size: 22rpx;
  color: #999;
  display: block;
  margin-top: 10rpx;
}

.confirm-section {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 14px var(--nb-page-x);
  padding-bottom: calc(14px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border-top: 1rpx solid rgba(27, 26, 23, 0.10);
}

.confirm-btn {
  height: 88rpx;
  border-radius: 44rpx;
  font-size: 32rpx;
  font-weight: bold;
  border: none;
}

.confirm-btn[disabled] {
  background: rgba(27, 26, 23, 0.12);
  color: rgba(27, 26, 23, 0.45);
}

.spec-section {
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: 18px;
  padding: 14px;
}

.spec-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.spec-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--nb-text);
}

.spec-link {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.62);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.spec-empty-text {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.62);
}

.spec-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.spec-card {
  padding: 12px 12px;
  border-radius: 14px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(27, 26, 23, 0.03);
}

.spec-card.selected {
  border-color: rgba(247, 201, 72, 0.45);
  background: rgba(247, 201, 72, 0.18);
}

.spec-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.spec-name {
  font-size: 15px;
  color: var(--nb-text);
  font-weight: 800;
}

.spec-range {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.56);
  white-space: nowrap;
}

.spec-meta {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
}

/* 小屏：3列会过窄，降到2列更符合 iOS 的可点按尺寸 */
@media (max-width: 380px) {
  .brand-card {
    width: 48%;
  }
}
</style>
