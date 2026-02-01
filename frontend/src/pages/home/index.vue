<template>
  <view class="home-container">
    <!-- 顶部菜单 -->
    <view class="top-menu">
      <view class="menu-icon" @click="showMenu">
        <text class="menu-line"></text>
        <text class="menu-line"></text>
        <text class="menu-line"></text>
      </view>
    </view>
    
    <!-- 宝宝信息区域 -->
    <view class="baby-profile-section">
      <!-- 大头像 -->
      <view class="baby-avatar-large" @click="goToBabyInfo">
        <image 
          :src="currentBaby.avatar_url || '/static/default-avatar.png'" 
          class="avatar-img-large"
          mode="aspectFill"
        />
      </view>
      
      <!-- 宝宝名字 -->
      <view class="baby-name-row">
        <text class="baby-name-large">{{ currentBaby.nickname || '宝宝' }}</text>
      </view>
      
      <!-- 统计数据 -->
      <view class="baby-stats-row">
        <text class="stat-text">{{ babyAgeText }}</text>
        <text v-if="zodiacText" class="stat-dot">·</text>
        <text v-if="zodiacText" class="stat-text">{{ zodiacText }}</text>
      </view>
    </view>
    
    <!-- 今日概览：减焦虑 + 一眼看懂 + 高频一键（点击打开今日喂奶详情） -->
    <view class="today-card" @click="openTodayModal">
      <view class="today-head">
        <view class="today-title">
          <text class="today-title-prefix">今天已经喝了</text>
          <text class="today-title-num">{{ todayCount }}</text>
          <text class="today-title-suffix">次奶</text>
        </view>
        <view class="health-pill" :class="`lv-${insightLevel}`">
          <text class="health-pill-text">{{ insightLabel }}</text>
        </view>
      </view>

      <view class="today-sub">
        <text class="today-sub-strong">平均每次 {{ avgPerFeeding }}ml</text>
        <text class="today-sub-dot">·</text>
        <text class="today-sub-muted">总计 {{ stats.today_amount || 0 }}ml</text>
      </view>

      <view class="today-progress">
        <view class="today-progress-head">
          <text class="today-progress-left">已喝 {{ todayConsumedMl }}ml</text>
          <text class="today-progress-right">目标 {{ todayTargetMl }}ml</text>
        </view>
        <view class="today-progress-bar" :class="`tone-${amountProgressTone}`">
          <view class="today-progress-fill" :style="{ width: consumptionPercent + '%' }"></view>
          <view
            v-if="expectedNowPercent"
            class="today-progress-marker"
            :style="{ left: expectedNowPercent + '%' }"
          ></view>
        </view>
        <text class="today-progress-text">
          已达 {{ consumptionPercent }}% · 按当前时间进度应≈ {{ expectedNowMl }}ml
        </text>
      </view>

      <!-- 24小时喂奶时间轴：核心体验（分布 + 量差异） -->
      <view class="today-timeline" v-if="todayCount > 0">
        <view class="today-timeline-head">
          <text class="today-timeline-title">24小时喂奶节奏</text>
          <text class="today-timeline-sub">点卡片查看明细</text>
        </view>

        <view class="today-timeline-track">
          <view class="today-timeline-line"></view>
          <view v-if="nowDayPercent" class="today-timeline-now" :style="{ left: nowDayPercent + '%' }"></view>

          <view
            v-for="m in todayTimelineMarks"
            :key="m.key"
            class="today-timeline-mark"
            :style="{ left: m.leftPercent + '%' }"
          >
            <view class="today-timeline-stick" :style="{ height: m.heightPx + 'px' }"></view>
            <view class="today-timeline-dot" :style="{ width: m.dotPx + 'px', height: m.dotPx + 'px' }"></view>
          </view>
        </view>

        <view class="today-timeline-axis">
          <text class="axis-item">0</text>
          <text class="axis-item">6</text>
          <text class="axis-item">12</text>
          <text class="axis-item">18</text>
          <text class="axis-item">24</text>
        </view>
      </view>

      <view class="today-next">
        <view class="today-next-left">
          <text class="today-next-label">下次喂奶时间</text>
          <view class="today-next-clock-row">
            <text v-if="nextFeedingDayLabel" class="today-next-day">{{ nextFeedingDayLabel }}</text>
            <text class="today-next-countdown">{{ nextFeedingClockText }}</text>
          </view>
          <text class="today-next-since">{{ sinceLastFeedingText }}</text>
          <text class="today-next-amount">下次建议 {{ nextSuggestedAmount }}ml</text>
        </view>
      </view>

      <view class="today-hint">
        <text class="today-hint-text">{{ insightDesc }}</text>
        <view v-if="showAdviceBox && insightAdviceItems.length > 0" class="today-advice" @click.stop>
          <text class="today-advice-title">科学建议</text>
          <text
            v-for="(t, idx) in insightAdviceItems"
            :key="idx"
            class="today-advice-item"
          >· {{ t }}</text>
        </view>
        <text class="today-hint-disclaimer">仅供参考，异常请咨询医生</text>
      </view>
    </view>
    
    <!-- 投喂按钮 -->
    <view class="feed-button-large" @click="recordNextSuggested">
      <text class="feed-button-text">{{ quickFeeding ? '记录中' : '投喂' }}</text>
    </view>

    <!-- 撤销条：保存后 3 秒内可撤销 -->
    <view v-if="undoVisible" class="undo-toast" @click.stop>
      <text class="undo-text">已记录 {{ undoFeedingAmount }}ml</text>
      <view class="undo-actions">
        <text class="undo-action" @click="undoLastFeeding">撤销</text>
        <text class="undo-action" @click="viewUndoFeeding">查看</text>
      </view>
    </view>

    <!-- 今日喂奶详情（底部抽屉） -->
    <view v-if="showTodayModal" class="modal-overlay sheet" @click.self="closeTodayModal">
      <view class="modal-content sheet" @click.stop @touchstart.stop>
        <view class="modal-header">
          <text class="modal-title">今日喂奶记录</text>
          <text class="close-btn" @click="closeTodayModal">×</text>
        </view>

        <view class="today-modal-summary">
          <text class="today-modal-summary-text">
            {{ todayCount }} 次 · {{ stats.today_amount || 0 }}ml · 平均 {{ avgPerFeeding }}ml/次
          </text>
        </view>

        <view v-if="formulaMetaText" class="today-modal-meta">
          <text class="today-modal-meta-text">{{ formulaMetaText }}</text>
        </view>

        <!-- 24小时喂奶时间轴：看分布 + 量差异 -->
        <view class="today-timeline" v-if="todayCount > 0">
          <view class="today-timeline-head">
            <text class="today-timeline-title">24小时喂奶节奏</text>
            <text class="today-timeline-sub">点列表项可编辑</text>
          </view>

          <view class="today-timeline-track">
            <view class="today-timeline-line"></view>
            <view v-if="nowDayPercent" class="today-timeline-now" :style="{ left: nowDayPercent + '%' }"></view>

            <view
              v-for="m in todayTimelineMarks"
              :key="m.key"
              class="today-timeline-mark"
              :style="{ left: m.leftPercent + '%' }"
            >
              <view class="today-timeline-stick" :style="{ height: m.heightPx + 'px' }"></view>
              <view class="today-timeline-dot" :style="{ width: m.dotPx + 'px', height: m.dotPx + 'px' }"></view>
            </view>
          </view>

          <view class="today-timeline-axis">
            <text class="axis-item">0</text>
            <text class="axis-item">6</text>
            <text class="axis-item">12</text>
            <text class="axis-item">18</text>
            <text class="axis-item">24</text>
          </view>
        </view>

        <view v-if="todayCount <= 0" class="today-modal-empty">
          <text class="today-modal-empty-text">今天还没有记录</text>
          <text class="today-modal-empty-sub">点下方“投喂”开始（误触可撤销）</text>
        </view>

        <scroll-view v-else class="today-modal-list" scroll-y>
          <view
            v-for="f in todayFeedings"
            :key="f.id"
            class="today-item"
            @click="openDetail(f)"
          >
            <text class="today-item-time">{{ formatFeedingTime(f.feeding_time) }}</text>
            <text class="today-item-amount">{{ Number(f.amount || 0) }}ml</text>
            <text class="today-item-user">{{ resolveMemberName(f.user_id) }}</text>
          </view>
        </scroll-view>

        <view class="modal-actions">
          <button class="cancel-btn" @click="closeTodayModal">关闭</button>
          <button class="confirm-btn" @click="goToDataDetail">查看数据</button>
        </view>
      </view>
    </view>

    <!-- 喂养记录详情/编辑 -->
    <view
      v-if="showDetailModal"
      class="modal-overlay"
      @click.self="closeDetailModal"
    >
      <view class="modal-content" @click.stop @touchstart.stop>
        <view class="modal-header">
          <text class="modal-title">喂养记录</text>
          <text class="close-btn" @click="closeDetailModal">×</text>
        </view>

        <view class="detail-row">
          <text class="detail-label">时间</text>
          <text class="detail-value">{{ detailTimeText }}</text>
        </view>
        <view class="detail-row">
          <text class="detail-label">记录人</text>
          <text class="detail-value">{{ detailUserText }}</text>
        </view>

        <view class="detail-edit">
          <text class="detail-label">奶量</text>
          <view class="detail-input-wrap">
            <input
              class="detail-input"
              type="number"
              inputmode="numeric"
              v-model="detailAmount"
              :disabled="!canEditDetail"
              placeholder="ml"
            />
            <text class="detail-unit">ml</text>
          </view>
          <text v-if="!canEditDetail" class="detail-hint">仅可编辑自己创建的记录（或管理员）</text>
        </view>

        <view class="modal-actions">
          <button class="cancel-btn" @click="closeDetailModal">关闭</button>
          <button class="confirm-btn" :disabled="!canEditDetail || detailSaving" @click="saveDetail">
            {{ detailSaving ? '保存中...' : '保存' }}
          </button>
        </view>

        <view class="danger-row">
          <button class="danger-btn" :disabled="!canEditDetail || detailSaving" @click="deleteDetail">
            删除该记录
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import api from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { calcAgeInDays, formatBabyAgeText } from '@/utils/age'
import { formatZodiacText } from '@/utils/zodiac'

export default {
  components: {},
  data() {
    return {
      currentBaby: {},
      todayFeedings: [],
      stats: {},
      familyMembers: [],
      selectedFormula: null,
      formulaSpec: null,
      recommendedAmount: {
        recommended: 150,
        daily_standard: 810,
        daily_consumed: 0,
        remaining_times: 4,
        warning: 'normal',
        age_reference: '700-900ml/天'
      },
      userPreference: null,
      feedingSettings: null,
      nextFeedingClockText: '--:--',
      nextFeedingDayLabel: '',
      sinceLastFeedingText: '暂无喂奶记录',
      showTodayModal: false,
      lastFeedingTimestampMs: null,
      nextFeedingTimestampMs: null,
      countdownTimer: null,
      remindAdvanceFiredFor: null,
      remindDueFiredFor: null,
      nowTickMs: 0,
      recentFeedings: [],

      // 撤销条（保存后 3 秒内）
      undoVisible: false,
      undoFeeding: null,
      undoTimer: null,

      // 详情/编辑
      showDetailModal: false,
      detailFeeding: null,
      detailAmount: '',
      detailSaving: false,

      // WebSocket（多设备/多成员实时同步）
      socketTask: null,
      wsRefreshTimer: null,

      // 管理员（运营后台）
      isAdmin: false,
      adminChecked: false,

      // 生长趋势（用于首页“科学判断”）
      growthStats: null,

      // 投喂状态
      quickFeeding: false,
      lastFeedTapAtMs: 0,

      // 避免 tabBar 首次进入 onShow 重复请求
      hasLoaded: false,
    }
  },
  
  computed: {
    babyAgeText() {
      return formatBabyAgeText(this.currentBaby?.birth_date) || '0天'
    },
    zodiacText() {
      return formatZodiacText(this.currentBaby?.birth_date) || ''
    },
    babyAge() {
      return calcAgeInDays(this.currentBaby?.birth_date)
    },
    // 奶粉段位徽标：对 0-12 月场景，按月龄给出 1/2 段的轻提示
    formulaStageBadge() {
      const days = Number(this.babyAge || 0)
      if (!Number.isFinite(days)) return '1'
      return days < 180 ? '1' : '2'
    },

    todayCount() {
      return Array.isArray(this.todayFeedings) ? this.todayFeedings.length : 0
    },

    avgPerFeeding() {
      const n = Number(this.todayCount || 0)
      const total = Number(this.stats?.today_amount || 0)
      if (!n || n <= 0 || !Number.isFinite(total) || total <= 0) return 0
      return Math.round(total / n)
    },

    nextSuggestedAmount() {
      const base = Number(this.recommendedAmount?.recommended || 0)
      if (!Number.isFinite(base) || base <= 0) return 0
      const delta = this.getSuggestedDelta()
      const v = base + delta
      return Number.isFinite(v) ? v : base
    },

    insightLevel() {
      // 没有任何记录时，不做“优/差”判断，先引导记录，避免制造焦虑。
      if (this.todayCount <= 0) return 'unknown'

      const feedingStatus = this.feedingStatusForHome()
      const interval = this.getIntervalInsight()

      const g = this.growthStats || null
      const milkRef = this.parseRefRange(g?.reference?.milk)
      const wgRef = this.parseRefRange(g?.reference?.weight_gain)
      const hgRef = this.parseRefRange(g?.reference?.height_gain)

      const milkAvg = Number(g?.daily_avg_milk || 0)
      const wg = Number(g?.daily_weight_gain || 0)
      const hg = Number(g?.daily_height_gain || 0)

      const milkStatus = this.compareToRange(milkAvg, milkRef)
      const wgStatus = this.compareToRange(wg, wgRef)
      const hgStatus = this.compareToRange(hg, hgRef)
      const hasGrowthSignal = [milkStatus, wgStatus, hgStatus].some((x) => x !== 'unknown')

      let score = 100
      if (feedingStatus === 'low' || feedingStatus === 'high') score -= 40
      if (interval?.penalty) score -= Number(interval.penalty || 0)
      if (milkStatus === 'low' || milkStatus === 'high') score -= 15
      if (wgStatus === 'low' || wgStatus === 'high') score -= 30
      if (hgStatus === 'low' || hgStatus === 'high') score -= 20

      let lv = 'alert'
      if (score >= 85) lv = 'excellent'
      else if (score >= 70) lv = 'good'
      else if (score >= 55) lv = 'attention'

      // 超时属于“当前需要处理”的强信号：避免仍显示为“良/优”
      if (interval?.status === 'overdue') {
        if (interval.severity === 'severe') return 'alert'
        if (lv === 'excellent' || lv === 'good') lv = 'attention'
      }
      // 过密喂奶属于高风险误操作：分钟级多次记录要强警示
      if (interval?.status === 'frequent') {
        if (interval.severity === 'severe') return 'alert'
        if (interval.severity === 'moderate' && (lv === 'excellent' || lv === 'good')) lv = 'attention'
      }

      // 没有生长信号时，最多给到“良”，避免误导为“完全健康结论”。
      if (!hasGrowthSignal && lv === 'excellent') lv = 'good'
      return lv
    },

    insightLabel() {
      const lv = String(this.insightLevel || '')
      if (lv === 'unknown') return '待记录'
      if (lv === 'excellent') return '优'
      if (lv === 'good') return '良'
      if (lv === 'attention') return '需关注'
      return '警示'
    },

    insightDesc() {
      if (this.todayCount <= 0) return '今天还没有记录，点“投喂”快速开始（误触可撤销）'

      const interval = this.getIntervalInsight()
      const intervalTail = interval?.text ? `；${interval.text}` : ''
      const prefix = this.getInsightPrefix(interval)

      const rec = this.recommendedAmount || {}
      const consumed = Number(rec.daily_consumed || 0)
      const standard = Number(rec.daily_standard || 0)
      const dayProgress = this.getDayProgress()
      const feedingStatus = this.feedingStatusForHome()

      if (interval?.status === 'overdue') {
        return `${prefix}${interval.text}；可先按推荐量继续记录（下次建议约 ${this.nextSuggestedAmount}ml）`
      }

      // 过密喂奶是高风险信号：必须直接讲清楚原因与下一步，避免“标题警示但正文仍说正常”造成误导。
      if (interval?.status === 'frequent') {
        if (interval.severity === 'severe') {
          return `${prefix}${interval.text}；短时间多次投喂通常不科学，可能是误触/重复记录。建议先打开“今日喂奶记录”核对并撤销多余记录；若宝宝出现吐奶/腹胀/精神差等异常，请及时咨询医生`
        }
        if (interval.severity === 'moderate') {
          return `${prefix}${interval.text}；若不是补喂/吐奶等特殊情况，建议按设置间隔执行，避免“越喂越乱”`
        }
      }

      // “今天”的判断：按时间进度做解释，避免上午就显示“偏低”制造焦虑。
      if (standard > 0 && (feedingStatus === 'low' || feedingStatus === 'high')) {
        const delta = consumed - standard
        const abs = Math.abs(delta)
        const dir = delta < 0 ? '少' : '多'

        if (dayProgress < 0.85) {
          return `${prefix}今天进度偏${feedingStatus === 'low' ? '慢' : '快'}（暂比参考${dir}约${abs}ml），按推荐量继续记录即可${intervalTail}`
        }

        const tip = feedingStatus === 'low'
          ? '可以优先按推荐量补齐今日差距'
          : '若宝宝状态良好可维持；频繁吐奶/不适建议咨询医生'
        return `${prefix}今日奶量偏${feedingStatus === 'low' ? '低' : '高'}（比参考${dir}约${abs}ml），${tip}${intervalTail}`
      }

      // 再补“科学”解释：有生长数据则给趋势判断；无则引导补录。
      const g = this.growthStats
      if (!g) return `${prefix}今天进度正常；补充身高体重后可生成更准确的综合判断${intervalTail}`

      const milkStatus = this.compareToRange(Number(g.daily_avg_milk || 0), this.parseRefRange(g?.reference?.milk))
      const wgStatus = this.compareToRange(Number(g.daily_weight_gain || 0), this.parseRefRange(g?.reference?.weight_gain))
      const hgStatus = this.compareToRange(Number(g.daily_height_gain || 0), this.parseRefRange(g?.reference?.height_gain))

      const parts = []
      if (milkStatus !== 'unknown') parts.push(`近7天奶量${milkStatus === 'ok' ? '正常' : (milkStatus === 'low' ? '偏低' : '偏高')}`)
      if (wgStatus !== 'unknown') parts.push(`增重${wgStatus === 'ok' ? '正常' : (wgStatus === 'low' ? '偏低' : '偏高')}`)
      if (hgStatus !== 'unknown') parts.push(`增高${hgStatus === 'ok' ? '正常' : (hgStatus === 'low' ? '偏低' : '偏高')}`)

      if (parts.length === 0) return `${prefix}暂缺生长记录：补录身高体重后，才能对“奶量与生长关系”做更科学判断${intervalTail}`
      if (parts.every((x) => x.includes('正常'))) return `${prefix}今天进度正常，近7天生长趋势也在参考范围内${intervalTail}`
      return `${prefix}今天进度正常；${parts.join('，')}（点击查看详情）${intervalTail}`
    },

    insightAdviceItems() {
      if (this.todayCount <= 0) return []

      const items = []
      const interval = this.getIntervalInsight()
      const feedingStatus = this.feedingStatusForHome()

      const amount = Number(this.nextSuggestedAmount || 0)
      const scoops = this.formatScoopsForAmount(amount)
      const amountText = amount > 0 ? `${amount}ml${scoops ? `（约${scoops}）` : ''}` : ''

      if (interval?.status === 'overdue') {
        items.push(amountText ? `现在先按推荐量投喂 ${amountText}，把节奏拉回设置间隔` : '现在先记录一次喂奶，把节奏拉回设置间隔')
      } else if (interval?.status === 'sparse') {
        items.push('尽量按设置间隔喂，避免拖太久导致一次性喝太多')
      } else if (interval?.status === 'frequent') {
        if (interval.severity === 'severe') {
          const c = Number(interval?.detail?.burst_10m?.count || 0)
          const t = Number(interval?.detail?.burst_10m?.total_amount || 0)
          const extra = (c >= 2 && t > 0) ? `（10分钟内${c}次共${t}ml）` : ''
          items.push(`可能误触：短时间内记录过密${extra}，建议先打开“今日喂奶记录”撤销多余记录`)
        } else if (interval.severity === 'moderate') {
          items.push('喂奶间隔偏短：若非补喂/吐奶等特殊情况，建议按设置间隔执行')
        } else {
          items.push('如果只是安抚需求，可先用安抚方式替代，避免过密投喂导致总量偏高')
        }
      } else if (interval?.status === 'irregular') {
        items.push('把喂奶时间尽量固定在一个节奏里（例如每次相隔接近设置值）')
      }

      if (feedingStatus === 'low') {
        items.push(amountText ? `今天进度偏慢：接下来优先按推荐量 ${amountText} 继续记录` : '今天进度偏慢：接下来优先按推荐量继续记录')
      } else if (feedingStatus === 'high') {
        items.push(amountText ? `今天进度偏快：后续按推荐量 ${amountText} 记录，避免再加量` : '今天进度偏快：后续按推荐量记录，避免再加量')
      } else if (!interval?.status || interval.status === 'ok') {
        items.push('保持现在的节奏即可（按推荐量记录 + 间隔稳定）')
      }

      const g = this.growthStats || null
      if (!g) {
        items.push('每周补录一次体重和身高，才能更科学评估“奶量-生长”关系')
      } else {
        const wgStatus = this.compareToRange(Number(g.daily_weight_gain || 0), this.parseRefRange(g?.reference?.weight_gain))
        const hgStatus = this.compareToRange(Number(g.daily_height_gain || 0), this.parseRefRange(g?.reference?.height_gain))
        if (wgStatus === 'low' || hgStatus === 'low') {
          items.push('近期生长偏慢：如连续多日偏离参考范围或宝宝状态异常，建议咨询医生')
        } else if (wgStatus === 'high') {
          items.push('近期增重偏快：注意避免过量，优先按推荐量与间隔执行')
        }
      }

      // 去重 + 限制条数，避免信息过载
      return Array.from(new Set(items)).slice(0, 3)
    },

    formulaMetaText() {
      const name = this.selectedFormula?.brand?.name_cn || this.selectedFormula?.brand_name || ''
      const stage = this.formulaStageBadge
      const scoops = this.railScoopsText
      const parts = []
      if (name) parts.push(`奶粉：${name}`)
      if (stage) parts.push(`${stage}段`)
      if (scoops) parts.push(scoops)
      return parts.join(' · ')
    },

    consumptionPercent() {
      const standard = Number(this.recommendedAmount?.daily_standard || 0)
      const consumed = Number(this.recommendedAmount?.daily_consumed || 0)
      if (!standard || standard <= 0) return 0
      const raw = (consumed / standard) * 100
      const clamped = Math.max(0, Math.min(100, raw))
      return clamped.toFixed(1)
    },

    todayConsumedMl() {
      const v = Number(this.recommendedAmount?.daily_consumed ?? this.stats?.today_amount ?? 0)
      return Number.isFinite(v) && v > 0 ? Math.round(v) : 0
    },

    todayTargetMl() {
      const v = Number(this.recommendedAmount?.daily_standard || 0)
      return Number.isFinite(v) && v > 0 ? Math.round(v) : 0
    },

    expectedNowMl() {
      const standard = this.todayTargetMl
      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (!standard || standard <= 0 || Number.isNaN(now.getTime())) return 0
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime()
      const dayMs = 24 * 60 * 60 * 1000
      const progress = dayMs > 0 ? Math.max(0, Math.min(1, (nowMs - start) / dayMs)) : 0
      return Math.round(standard * progress)
    },

    expectedNowPercent() {
      const standard = this.todayTargetMl
      if (!standard || standard <= 0) return ''
      const expected = this.expectedNowMl
      const raw = (expected / standard) * 100
      const clamped = Math.max(0, Math.min(100, raw))
      return clamped.toFixed(1)
    },

    amountProgressTone() {
      const s = this.feedingStatusForHome()
      if (s === 'low' || s === 'high') return s
      return 'ok'
    },

    showAdviceBox() {
      const lv = String(this.insightLevel || '')
      return lv === 'attention' || lv === 'alert'
    },

    nowDayPercent() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const d = new Date(nowMs)
      if (Number.isNaN(d.getTime())) return ''
      const minutes = d.getHours() * 60 + d.getMinutes()
      const p = (minutes / 1440) * 100
      const clamped = Math.max(0, Math.min(100, p))
      return clamped.toFixed(2)
    },

    todayTimelineMarks() {
      const list = Array.isArray(this.todayFeedings) ? this.todayFeedings : []
      if (list.length <= 0) return []

      const points = list
        .map((f, idx) => {
          const ms = this.parseTimeToMs(f?.feeding_time)
          if (!Number.isFinite(ms) || ms <= 0) return null
          const d = new Date(ms)
          if (Number.isNaN(d.getTime())) return null
          const minutes = d.getHours() * 60 + d.getMinutes()
          const leftPercent = (minutes / 1440) * 100
          const amount = Number(f?.amount || 0)
          return {
            key: f?.id ? String(f.id) : `idx-${idx}`,
            leftPercent: Math.max(0, Math.min(100, leftPercent)),
            amount: Number.isFinite(amount) ? amount : 0,
          }
        })
        .filter(Boolean)

      if (points.length <= 0) return []

      const amounts = points.map((p) => Math.max(0, Math.min(300, Number(p.amount || 0))))
      const min = Math.min(...amounts)
      const max = Math.max(...amounts)
      const span = Math.max(1, max - min)

      return points.map((p, idx) => {
        const a = Math.max(0, Math.min(300, Number(p.amount || 0)))
        const t = points.length <= 1 ? 0.5 : (a - min) / span
        const heightPx = Math.round(6 + t * 14) // 6-20px
        const dotPx = Math.round(6 + t * 6) // 6-12px
        return {
          key: p.key || `p-${idx}`,
          leftPercent: p.leftPercent.toFixed(2),
          heightPx,
          dotPx,
          amount: a,
        }
      })
    },

    undoFeedingAmount() {
      const n = Number(this.undoFeeding?.amount || 0)
      return Number.isFinite(n) ? n : 0
    },

    canEditDetail() {
      const feeding = this.detailFeeding
      if (!feeding) return false
      const userStore = useUserStore()
      const me = userStore.user?.id
      if (!me) return false
      if (String(feeding.user_id) === String(me)) return true
      const m = (Array.isArray(this.familyMembers) ? this.familyMembers : []).find((x) => String(x.user_id) === String(me))
      return m?.role === 'admin'
    },

    detailTimeText() {
      const t = this.detailFeeding?.feeding_time
      if (!t) return '--'
      const d = new Date(String(t).replace(' ', 'T'))
      if (Number.isNaN(d.getTime())) return String(t)
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${hh}:${mm}`
    },

    detailUserText() {
      const uid = this.detailFeeding?.user_id
      if (!uid) return '--'
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(uid))
      return (m && (m.nickname || '成员')) || '成员'
    },

    railScoopsText() {
      const ml = Number(this.formulaSpec?.scoop_ml || 0)
      const amount = Number(this.recommendedAmount?.recommended || 0)
      if (!ml || ml <= 0 || !amount || amount <= 0) return ''
      const raw = amount / ml
      const rounded = Math.round(raw * 2) / 2
      return `${rounded}勺/次`
    }
  },
  
  onLoad() {
    this.loadData()
    this.startCountdown()
  },

  async onShow() {
    // tabBar 页：首次进入由 onLoad 拉取；后续从设置/详情返回时再刷新，确保口径一致
    if (!this.hasLoaded) {
      this.hasLoaded = true
      return
    }

    const userStore = useUserStore()
    const baby = userStore.currentBaby || null
    if (baby?.id && String(baby.id) !== String(this.currentBaby?.id || '')) {
      this.currentBaby = baby
    }
    if (!this.currentBaby?.id) {
      await this.loadData()
      return
    }

    await Promise.all([
      this.loadFeedings(),
      this.loadStats(),
      this.loadGrowthStats(),
      this.loadFeedingSettings(),
      this.loadSelectedFormula(),
      this.loadFormulaSpec(),
      this.loadFamilyMembers(),
    ])
  },
  
  onUnload() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }
    if (this.undoTimer) {
      clearTimeout(this.undoTimer)
      this.undoTimer = null
    }
    this.closeWs()
  },
  
  methods: {
    parseRefRange(text) {
      const s = String(text || '').trim()
      const m = s.match(/(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)/)
      if (!m) return null
      const min = Number(m[1])
      const max = Number(m[2])
      if (!Number.isFinite(min) || !Number.isFinite(max)) return null
      return { min: Math.min(min, max), max: Math.max(min, max) }
    },

    compareToRange(value, range) {
      const v = Number(value || 0)
      if (!Number.isFinite(v) || v <= 0) return 'unknown'
      if (!range || !Number.isFinite(range.min) || !Number.isFinite(range.max)) return 'unknown'
      if (v < range.min) return 'low'
      if (v > range.max) return 'high'
      return 'ok'
    },

    parseTimeToMs(raw) {
      // 兼容 iOS/Safari：避免直接解析 "YYYY-MM-DD HH:mm:ss" 造成 NaN
      if (raw === null || raw === undefined) return null
      if (raw instanceof Date) {
        const ms = raw.getTime()
        return Number.isFinite(ms) ? ms : null
      }
      if (typeof raw === 'number') {
        if (!Number.isFinite(raw) || raw <= 0) return null
        // 1e12 约等于 2001-09-09 的毫秒时间戳；小于则视为秒
        return raw < 1e12 ? raw * 1000 : raw
      }
      const s = String(raw).trim()
      if (!s) return null
      if (/^\\d+$/.test(s)) {
        const n = Number(s)
        if (!Number.isFinite(n) || n <= 0) return null
        return n < 1e12 ? n * 1000 : n
      }

      const iso = s.includes('T') ? s : s.replace(' ', 'T')
      let d = new Date(iso)
      let ms = d.getTime()
      if (Number.isFinite(ms)) return ms

      // 兜底：YYYY-MM-DD HH:mm(:ss)
      const m = s.match(/^(\\d{4})-(\\d{1,2})-(\\d{1,2})(?:[ T](\\d{1,2}):(\\d{1,2})(?::(\\d{1,2}))?)?/)
      if (!m) return null
      const y = Number(m[1])
      const mo = Number(m[2])
      const da = Number(m[3])
      const hh = Number(m[4] ?? 0)
      const mm = Number(m[5] ?? 0)
      const ss = Number(m[6] ?? 0)
      if (![y, mo, da, hh, mm, ss].every((x) => Number.isFinite(x))) return null
      d = new Date(y, mo - 1, da, hh, mm, ss, 0)
      ms = d.getTime()
      return Number.isFinite(ms) ? ms : null
    },

    formatClockText(ms) {
      if (!Number.isFinite(ms)) return '--:--'
      const d = new Date(ms)
      if (Number.isNaN(d.getTime())) return '--:--'
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${hh}:${mm}`
    },

    formatDayLabel(targetMs, nowMs) {
      if (!Number.isFinite(targetMs) || !Number.isFinite(nowMs)) return ''
      const t = new Date(targetMs)
      const n = new Date(nowMs)
      if (Number.isNaN(t.getTime()) || Number.isNaN(n.getTime())) return ''
      const tUTC = Date.UTC(t.getFullYear(), t.getMonth(), t.getDate())
      const nUTC = Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())
      const diffDays = Math.round((tUTC - nUTC) / 86400000)
      if (diffDays === 0) return '今天'
      if (diffDays === 1) return '明天'
      if (diffDays === 2) return '后天'
      return `${t.getMonth() + 1}月${t.getDate()}日`
    },

    formatDurationText(ms) {
      const sec = Math.max(0, Math.floor(Number(ms || 0) / 1000))
      if (!Number.isFinite(sec)) return ''
      const days = Math.floor(sec / 86400)
      const hours = Math.floor((sec % 86400) / 3600)
      const minutes = Math.floor((sec % 3600) / 60)
      const seconds = sec % 60
      if (days > 0) return `${days}天${hours}小时${minutes}分`
      if (hours > 0) return `${hours}小时${minutes}分`
      if (minutes > 0) return `${minutes}分`
      return `${seconds}秒`
    },

    getFeedingSettingsSnapshot() {
      const s = this.feedingSettings || {}
      const dayStartHour = Number(s.day_start_hour ?? 6)
      const dayEndHour = Number(s.day_end_hour ?? 18)
      const dayInterval = Number(s.day_interval ?? 3)
      const nightInterval = Number(s.night_interval ?? 5)

      return {
        dayStartHour: Number.isFinite(dayStartHour) && dayStartHour >= 0 ? dayStartHour : 6,
        dayEndHour: Number.isFinite(dayEndHour) && dayEndHour > 0 ? dayEndHour : 18,
        dayInterval: Number.isFinite(dayInterval) && dayInterval > 0 ? dayInterval : 3,
        nightInterval: Number.isFinite(nightInterval) && nightInterval > 0 ? nightInterval : 5,
      }
    },

    // 与后端 services/milk_calculator.go 的 CalculateNextFeedingTime 保持一致（用于“喂奶间隔”判断口径统一）
    calcNextFeedingTimeMs(currentMs, lastFeedingMs) {
      const cur = Number(currentMs || 0)
      let last = Number(lastFeedingMs || 0)
      const nowMs = Number.isFinite(cur) && cur > 0 ? cur : Date.now()
      if (!Number.isFinite(last) || last <= 0) last = nowMs

      const s = this.getFeedingSettingsSnapshot()
      const dayStartHour = s.dayStartHour
      const dayEndHour = s.dayEndHour
      const dayInterval = s.dayInterval
      const nightInterval = s.nightInterval

      const lastDate = new Date(last)
      const curDate = new Date(nowMs)
      if (Number.isNaN(lastDate.getTime())) return null

      // 规则与后端一致：按“上次喂奶发生时刻”所在时段选择间隔，不做跨时段平滑
      const lastHour = lastDate.getHours()
      let intervalH = nightInterval
      if (lastHour >= dayStartHour && lastHour < dayEndHour) intervalH = dayInterval
      if (!Number.isFinite(intervalH) || intervalH <= 0) intervalH = 3
      let nextMs = last + intervalH * 60 * 60 * 1000

      // 确保下次时间不早于当前时间
      if (nextMs < curDate.getTime()) {
        const curHour = curDate.getHours()
        let h = nightInterval
        if (curHour >= dayStartHour && curHour < dayEndHour) h = dayInterval
        if (!Number.isFinite(h) || h <= 0) h = intervalH
        nextMs = curDate.getTime() + h * 60 * 60 * 1000
      }

      return nextMs
    },

    getIntervalPatternStatus() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const list = Array.isArray(this.recentFeedings) ? this.recentFeedings : []
      const times = list
        .map((f) => this.parseTimeToMs(f?.feeding_time))
        .filter((ms) => Number.isFinite(ms) && ms > 0)
        .sort((a, b) => a - b)

      // 仅看最近 36 小时，避免历史数据影响当前节奏
      const cutoff = nowMs - 36 * 60 * 60 * 1000
      const recent = times.filter((ms) => ms >= cutoff)
      if (recent.length < 2) return { status: 'unknown', samples: 0, early: 0, late: 0 }

      const verdicts = []
      for (let i = 1; i < recent.length; i += 1) {
        const prev = recent[i - 1]
        const cur = recent[i]
        const actualInterval = cur - prev
        if (!Number.isFinite(actualInterval) || actualInterval <= 0) continue

        const expectedNext = this.calcNextFeedingTimeMs(prev, prev)
        if (!Number.isFinite(expectedNext) || expectedNext <= prev) continue
        const expectedInterval = expectedNext - prev

        const tolerance = Math.max(20 * 60 * 1000, expectedInterval * 0.2)
        const diff = actualInterval - expectedInterval
        if (Math.abs(diff) <= tolerance) verdicts.push('ok')
        else if (diff < 0) verdicts.push('early')
        else verdicts.push('late')
      }

      const tail = verdicts.slice(-3)
      if (tail.length <= 0) return { status: 'unknown', samples: 0, early: 0, late: 0 }

      const early = tail.filter((v) => v === 'early').length
      const late = tail.filter((v) => v === 'late').length
      let status = 'ok'
      if (late >= 2) status = 'sparse'
      else if (early >= 2) status = 'frequent'
      else if (late >= 1 || early >= 1) status = 'irregular'
      return { status, samples: tail.length, early, late }
    },

    getFeedingBurstSummary(windowMs) {
      const w = Number(windowMs || 0)
      if (!Number.isFinite(w) || w <= 0) return { count: 0, total_amount: 0, min_interval_ms: null }

      const nowMs = Number(this.nowTickMs || Date.now())
      const list = Array.isArray(this.recentFeedings) ? this.recentFeedings : []
      const recent = list
        .map((f) => ({
          ms: this.parseTimeToMs(f?.feeding_time),
          amount: Number(f?.amount || 0),
        }))
        .filter((x) => Number.isFinite(x.ms) && x.ms > 0 && x.ms >= nowMs - w && x.ms <= nowMs + 60 * 1000) // 允许轻微时钟偏差
        .sort((a, b) => a.ms - b.ms)

      const count = recent.length
      let total = 0
      for (const r of recent) {
        if (Number.isFinite(r.amount) && r.amount > 0) total += r.amount
      }

      let minInterval = null
      for (let i = 1; i < recent.length; i += 1) {
        const d = recent[i].ms - recent[i - 1].ms
        if (!Number.isFinite(d) || d <= 0) continue
        if (minInterval === null || d < minInterval) minInterval = d
      }

      return { count, total_amount: total, min_interval_ms: minInterval }
    },

    getIntervalInsight() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const nextMs = Number(this.nextFeedingTimestampMs || 0)
      const graceMs = 10 * 60 * 1000
      const s = this.getFeedingSettingsSnapshot()
      const settingsText = `（白天${s.dayInterval}h/夜间${s.nightInterval}h）`

      if (Number.isFinite(nextMs) && nextMs > 0 && nowMs > nextMs + graceMs) {
        const overdueMs = nowMs - nextMs
        const overdue = this.formatDurationText(overdueMs)
        let severity = 'mild'
        let penalty = 25
        if (overdueMs >= 60 * 60 * 1000) {
          severity = 'severe'
          penalty = 45
        } else if (overdueMs >= 20 * 60 * 1000) {
          severity = 'moderate'
          penalty = 35
        }
        return {
          status: 'overdue',
          severity,
          overdue_ms: overdueMs,
          penalty,
          text: `已超过建议间隔约 ${overdue}${settingsText}`,
        }
      }

      // “过密喂奶”属于高风险误操作：分钟级多次记录要强提示
      const burst10 = this.getFeedingBurstSummary(10 * 60 * 1000)
      const burst2 = this.getFeedingBurstSummary(2 * 60 * 1000)
      const times = (Array.isArray(this.recentFeedings) ? this.recentFeedings : [])
        .map((f) => this.parseTimeToMs(f?.feeding_time))
        .filter((ms) => Number.isFinite(ms) && ms > 0 && ms <= nowMs + 60 * 1000)
        .sort((a, b) => a - b)
      const last = times.length > 0 ? times[times.length - 1] : null
      const prev = times.length > 1 ? times[times.length - 2] : null
      const lastIntervalMs = (Number.isFinite(last) && Number.isFinite(prev)) ? (last - prev) : null

      const hasMinuteBurst = burst2.count >= 2 && Number.isFinite(burst2.min_interval_ms) && burst2.min_interval_ms <= 2 * 60 * 1000
      const hasMultiBurst = burst10.count >= 3 && Number.isFinite(burst10.min_interval_ms) && burst10.min_interval_ms <= 5 * 60 * 1000
      const isExtremeShort = Number.isFinite(lastIntervalMs) && lastIntervalMs <= 2 * 60 * 1000

      if (hasMinuteBurst || hasMultiBurst || isExtremeShort) {
        const parts = []
        if (Number.isFinite(lastIntervalMs)) parts.push(`最近一次间隔约 ${this.formatDurationText(lastIntervalMs)}`)
        if (burst10.count >= 2) parts.push(`10分钟内${burst10.count}次共${burst10.total_amount}ml`)
        const detail = parts.length > 0 ? `（${parts.join('，')}）` : ''
        return {
          status: 'frequent',
          severity: 'severe',
          penalty: 45,
          text: `喂奶记录过于频繁${detail}${settingsText}`,
          detail: { last_interval_ms: lastIntervalMs, burst_10m: burst10, burst_2m: burst2 },
        }
      }

      if (Number.isFinite(lastIntervalMs) && lastIntervalMs > 0 && lastIntervalMs <= 10 * 60 * 1000) {
        const parts = [`最近一次间隔约 ${this.formatDurationText(lastIntervalMs)}`]
        if (burst10.count >= 2) parts.push(`10分钟内${burst10.count}次共${burst10.total_amount}ml`)
        return {
          status: 'frequent',
          severity: 'moderate',
          penalty: 25,
          text: `喂奶间隔偏短（${parts.join('，')}）${settingsText}`,
          detail: { last_interval_ms: lastIntervalMs, burst_10m: burst10 },
        }
      }

      const p = this.getIntervalPatternStatus()
      if (p.status === 'sparse') {
        return { status: 'sparse', severity: 'mild', penalty: 15, text: `近几次喂奶间隔偏长${settingsText}` }
      }
      if (p.status === 'frequent') {
        return { status: 'frequent', severity: 'mild', penalty: 12, text: `近几次喂奶间隔偏短${settingsText}` }
      }
      if (p.status === 'irregular') {
        return { status: 'irregular', severity: 'mild', penalty: 8, text: `喂奶间隔波动较大${settingsText}` }
      }
      if (p.status === 'ok' && p.samples > 0) {
        // 间隔稳定属于“非关键信息”，放到二级（今日明细/建议区）即可，避免首页噪音
        return { status: 'ok', severity: 'mild', penalty: 0, text: '' }
      }
      return { status: 'unknown', severity: 'mild', penalty: 0, text: '' }
    },

    getInsightPrefix(interval) {
      // 统一“赞美/提醒/警示”口径：优先显示“超时提醒”（当前需要处理）
      if (interval?.status === 'overdue') {
        return interval.severity === 'severe' ? '警示：' : '提醒：'
      }
      const lv = String(this.insightLevel || '')
      if (lv === 'excellent') return '赞：'
      if (lv === 'good') return '不错：'
      if (lv === 'attention') return '提醒：'
      if (lv === 'alert') return '警示：'
      return ''
    },

    formatScoopsForAmount(amountMl) {
      const ml = Number(this.formulaSpec?.scoop_ml || 0)
      const amount = Number(amountMl || 0)
      if (!ml || ml <= 0 || !amount || amount <= 0) return ''
      const raw = amount / ml
      const rounded = Math.round(raw * 2) / 2
      return `${rounded}勺`
    },

    getDayProgress() {
      const now = new Date(this.nowTickMs || Date.now())
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0)
      const elapsed = now.getTime() - start.getTime()
      const dayMs = 24 * 60 * 60 * 1000
      const raw = dayMs > 0 ? elapsed / dayMs : 0
      return Math.max(0, Math.min(1, raw))
    },

    feedingStatusForHome() {
      const rec = this.recommendedAmount || {}
      const consumed = Number(rec.daily_consumed || 0)
      const standard = Number(rec.daily_standard || 0)
      if (!Number.isFinite(standard) || standard <= 0) return 'unknown'

      const progress = this.getDayProgress()
      const ratio = standard > 0 ? (consumed / standard) : 0

      // 用“时间进度”做解释：上午不轻易判“偏低”，避免焦虑；越接近一天结束，阈值越严格。
      if (progress < 0.6) {
        if (ratio > 1.4) return 'high'
        return 'ok'
      }
      if (progress < 0.85) {
        if (ratio < 0.5) return 'low'
        if (ratio > 1.5) return 'high'
        return 'ok'
      }
      if (ratio < 0.8) return 'low'
      if (ratio > 1.2) return 'high'
      return 'ok'
    },

    getSuggestedDelta() {
      // 首页“投喂”的默认偏移：复用用户习惯（若超出范围则忽略），避免推荐量与用户习惯冲突。
      const delta = Number(this.userPreference?.adjustment_pattern || 0)
      if (!Number.isFinite(delta) || delta === 0) return 0
      const base = Number(this.recommendedAmount?.recommended || 0)
      if (!Number.isFinite(base) || base <= 0) return 0
      const candidate = base + delta
      if (candidate < 10 || candidate > 300) return 0
      return delta
    },

    async checkAdmin() {
      if (this.adminChecked) return
      this.adminChecked = true
      try {
        await api.get('/admin/health-standards/versions')
        this.isAdmin = true
      } catch {
        this.isAdmin = false
      }
    },
    async loadData() {
      const userStore = useUserStore()
      this.currentBaby = userStore.currentBaby || {}

      // 兜底：若本地未选择宝宝，但账号下已有宝宝，则自动选择第一个（降低首次登录/换设备成本）
      if (!this.currentBaby.id) {
        try {
          const res = await api.get('/babies')
          const first = Array.isArray(res.babies) ? res.babies[0] : null
          if (first && first.id) {
            this.currentBaby = first
            userStore.setCurrentBaby(first)
          }
        } catch {
          // 忽略：未登录/网络错误将由后续 API 统一处理
        }
      }
      
      if (!this.currentBaby.id) {
        // 如果没有当前宝宝，跳转到宝宝资料页
        uni.navigateTo({
          url: '/pages/baby-info/index'
        })
        return
      }
      
      await Promise.all([
        this.loadFeedings(),
        this.loadStats(),
        this.loadGrowthStats(),
        this.loadFamilyMembers(),
        this.loadFeedingSettings(),
        this.loadSelectedFormula(),
        this.loadFormulaSpec()
      ])

      this.connectWs()
      // 不阻塞主流程：后台判断一次管理员权限，用于菜单入口显示
      this.checkAdmin()
    },
    
    async loadFamilyMembers() {
      try {
        const res = await api.get(`/babies/${this.currentBaby.id}/family-members`)
        this.familyMembers = res.members || []
      } catch (error) {
        console.error('加载家庭成员失败', error)
      }
    },
    
    async loadSelectedFormula() {
      try {
        const res = await api.get(`/babies/${this.currentBaby.id}/formula`)
        if (res.selection) {
          this.selectedFormula = res.selection
        }
      } catch (error) {
        // 未选择奶粉，忽略
      }
    },

    async loadFormulaSpec() {
      try {
        const res = await api.get(`/babies/${this.currentBaby.id}/formula/specification`)
        this.formulaSpec = res.specification || null
      } catch {
        this.formulaSpec = null
      }
    },

    connectWs() {
      // uni-app：H5 用同源 /ws（vite 反代），其他端用配置的后端域名
      this.closeWs()

      const babyId = this.currentBaby?.id
      const token = uni.getStorageSync('token')
      if (!babyId || !token) return

      let origin = 'http://127.0.0.1:8080'
      if (typeof window !== 'undefined' && window.location && window.location.origin) {
        origin = String(window.location.origin)
      }
      const wsOrigin = origin.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
      const url = `${wsOrigin}/ws?token=${encodeURIComponent(token)}&baby_id=${encodeURIComponent(String(babyId))}`

      try {
        const task = uni.connectSocket({ url })
        this.socketTask = task

        task.onMessage((evt) => {
          this.onWsMessage(evt?.data)
        })
        task.onError(() => {})
        task.onClose(() => {})
      } catch (e) {
        this.socketTask = null
      }
    },

    closeWs() {
      if (this.wsRefreshTimer) {
        clearTimeout(this.wsRefreshTimer)
        this.wsRefreshTimer = null
      }
      const t = this.socketTask
      this.socketTask = null
      try {
        t && t.close && t.close({ code: 1000 })
      } catch {}
    },

    onWsMessage(data) {
      const s = typeof data === 'string' ? data : (data ? String(data) : '')
      if (!s) return
      let msg = null
      try {
        msg = JSON.parse(s)
      } catch {
        return
      }
      if (!msg || String(msg.baby_id || '') !== String(this.currentBaby?.id || '')) return

      // 高频变更合并刷新，避免多次重拉
      if (this.wsRefreshTimer) return
      this.wsRefreshTimer = setTimeout(async () => {
        this.wsRefreshTimer = null
        await Promise.all([this.loadFeedings(), this.loadStats()])
      }, 300)
    },

    async loadFeedings() {
      try {
        const res = await api.get('/feedings', {
          baby_id: this.currentBaby.id
        })
        const list = Array.isArray(res.feedings) ? res.feedings : []
        this.recentFeedings = list
        const last = list[0] || null
        this.lastFeedingTimestampMs = last ? this.parseTimeToMs(last.feeding_time) : null
        const now = new Date()
        const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime()
        const end = start + 24 * 60 * 60 * 1000
        this.todayFeedings = list.filter((f) => {
          const ms = this.parseTimeToMs(f?.feeding_time)
          return Number.isFinite(ms) && ms >= start && ms < end
        })
      } catch (error) {
        console.error('加载喂养记录失败', error)
      }
    },

    async loadGrowthStats() {
      try {
        const babyId = this.currentBaby?.id
        if (!babyId) {
          this.growthStats = null
          return
        }
        const res = await api.get(`/babies/${babyId}/growth-stats`)
        this.growthStats = res || null
      } catch {
        this.growthStats = null
      }
    },
    
    async loadStats() {
      try {
        const res = await api.get('/feedings/stats', {
          baby_id: this.currentBaby.id
        })
        this.stats = res.stats
        this.recommendedAmount = res.recommended
        this.userPreference = res.preference || null
        const prevNext = this.nextFeedingTimestampMs
        // 优先使用 timestamp（秒）避免 iOS/Safari 对日期字符串的解析差异
        if (res.next_feeding_timestamp) {
          const s = Number(res.next_feeding_timestamp)
          this.nextFeedingTimestampMs = Number.isFinite(s) ? s * 1000 : null
        } else {
          this.nextFeedingTimestampMs = null
        }
        if (this.nextFeedingTimestampMs && this.nextFeedingTimestampMs !== prevNext) {
          this.remindAdvanceFiredFor = null
          this.remindDueFiredFor = null
        }
      } catch (error) {
        console.error('加载统计数据失败', error)
      }
    },

    async loadFeedingSettings() {
      try {
        const res = await api.get(`/babies/${this.currentBaby.id}/settings`)
        this.feedingSettings = res.settings || null
      } catch {
        this.feedingSettings = null
      }
    },

    async recordNextSuggested() {
      if (this.quickFeeding) return

      const nowTap = Date.now()
      if (this.lastFeedTapAtMs && nowTap - this.lastFeedTapAtMs < 800) return
      this.lastFeedTapAtMs = nowTap

      const amount = Number(this.nextSuggestedAmount || 0)
      if (!Number.isFinite(amount) || amount < 10 || amount > 300) {
        uni.showToast({ title: '推荐奶量异常，请稍后重试', icon: 'none' })
        return
      }

      const ok = await this.confirmRapidFeedingIfNeeded(amount)
      if (!ok) return

      this.quickFeeding = true
      try {
        const method = this.getSuggestedDelta() !== 0 ? 'quick' : 'direct'
        await this.createFeeding(amount, method)
      } finally {
        this.quickFeeding = false
      }
    },

    async createFeeding(amount, inputMethod) {
      const n = Number(amount || 0)
      if (!Number.isFinite(n) || n < 10 || n > 300) {
        uni.showToast({ title: '奶量应在10-300ml之间', icon: 'none' })
        return
      }
      if (n > 200) {
        const ok = await this.confirmLargeAmount(n)
        if (!ok) return
      }

      if (!this.currentBaby || !this.currentBaby.id) {
        uni.showToast({ title: '请先设置宝宝信息', icon: 'none' })
        uni.navigateTo({ url: '/pages/baby-info/index' })
        return
      }

      try {
        const payload = {
          baby_id: this.currentBaby.id,
          amount: n,
        }
        if (this.selectedFormula?.brand_id) payload.formula_brand_id = this.selectedFormula.brand_id
        if (this.selectedFormula?.series_name) payload.formula_series_name = this.selectedFormula.series_name
        if (inputMethod) payload.input_method = inputMethod

        // 记录时把“勺数”也存下来，便于回看/家庭协作交接
        const scoopMl = Number(this.formulaSpec?.scoop_ml || 0)
        if (scoopMl > 0) {
          const raw = n / scoopMl
          const scoopsInt = Math.max(1, Math.round(raw))
          payload.scoops = scoopsInt
        }

        const res = await api.post('/feedings', payload)
        uni.showToast({ title: '记录成功', icon: 'success' })

        await Promise.all([this.loadFeedings(), this.loadStats()])

        // 保存后给 3 秒撤销窗口（避免误触）
        if (res && res.feeding && res.feeding.id) {
          this.showUndo(res.feeding)
        }
      } catch (error) {
        uni.showToast({ title: error.message || '记录失败', icon: 'none' })
      }
    },

    confirmLargeAmount(amount) {
      const n = Number(amount || 0)
      return new Promise((resolve) => {
        uni.showModal({
          title: '确认奶量',
          content: `单次奶量通常不建议超过200ml，你输入的是${n}ml，确定记录吗？`,
          cancelText: '返回修改',
          confirmText: '确定',
          success: (res) => resolve(!!res.confirm),
          fail: () => resolve(false)
        })
      })
    },

    confirmRapidFeedingIfNeeded(amount) {
      const lastMs = Number(this.lastFeedingTimestampMs || 0)
      if (!Number.isFinite(lastMs) || lastMs <= 0) return Promise.resolve(true)

      const nowMs = Date.now()
      const diffMs = Math.max(0, nowMs - lastMs)

      const expectedNext = this.calcNextFeedingTimeMs(lastMs, lastMs)
      const expectedIntervalMs = Number.isFinite(expectedNext) ? Math.max(0, expectedNext - lastMs) : (3 * 60 * 60 * 1000)
      const threshold = Math.min(15 * 60 * 1000, expectedIntervalMs * 0.2)
      if (!Number.isFinite(threshold) || threshold <= 0 || diffMs >= threshold) return Promise.resolve(true)

      const burst10 = this.getFeedingBurstSummary(10 * 60 * 1000)
      const diffText = this.formatDurationText(diffMs)
      const n = Number(amount || 0)
      const amountText = Number.isFinite(n) && n > 0 ? `${n}ml` : ''

      let title = '提醒：可能误触'
      if (diffMs <= 2 * 60 * 1000) title = '警示：记录过密'

      const extra = (burst10.count >= 2 && burst10.total_amount > 0)
        ? `\n最近10分钟已记录 ${burst10.count} 次，共 ${burst10.total_amount}ml。`
        : ''

      const content = `距离上次喂奶仅 ${diffText}。短时间多次记录通常不科学，可能是误触/重复记录。${extra}\n建议：先打开“今日喂奶记录”检查并撤销多余记录。${amountText ? `\n仍要记录本次${amountText}请点“继续记录”。` : '\n仍要继续记录请点“继续记录”。'}`

      return new Promise((resolve) => {
        uni.showModal({
          title,
          content,
          cancelText: '先检查',
          confirmText: '继续记录',
          success: (res) => {
            if (!res.confirm) this.openTodayModal()
            resolve(!!res.confirm)
          },
          fail: () => resolve(false)
        })
      })
    },

    openDetail(feeding) {
      this.undoVisible = false
      this.showTodayModal = false
      this.detailFeeding = feeding
      this.detailAmount = String(feeding?.amount ?? '')
      this.detailSaving = false
      this.showDetailModal = true
    },

    closeDetailModal() {
      this.showDetailModal = false
      this.detailFeeding = null
      this.detailAmount = ''
      this.detailSaving = false
    },

    async saveDetail() {
      const feeding = this.detailFeeding
      if (!feeding || !feeding.id || this.detailSaving || !this.canEditDetail) return
      const n = Number.parseInt(String(this.detailAmount || '').trim(), 10)
      if (!Number.isFinite(n) || n < 10 || n > 300) {
        uni.showToast({ title: '奶量应在10-300ml之间', icon: 'none' })
        return
      }
      if (n > 200) {
        const ok = await this.confirmLargeAmount(n)
        if (!ok) return
      }

      this.detailSaving = true
      try {
        await api.put(`/feedings/${feeding.id}`, { amount: n })
        uni.showToast({ title: '已保存', icon: 'success' })
        this.closeDetailModal()
        await this.loadFeedings()
        await this.loadStats()
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      } finally {
        this.detailSaving = false
      }
    },

    deleteDetail() {
      const feeding = this.detailFeeding
      if (!feeding || !feeding.id || this.detailSaving || !this.canEditDetail) return
      uni.showModal({
        title: '确认删除',
        content: '删除后不可恢复，确定删除该记录吗？',
        confirmText: '删除',
        confirmColor: '#E24A3B',
        success: async (res) => {
          if (!res.confirm) return
          this.detailSaving = true
          try {
            await api.delete(`/feedings/${feeding.id}`)
            uni.showToast({ title: '已删除', icon: 'success' })
            this.closeDetailModal()
            await this.loadFeedings()
            await this.loadStats()
          } catch (e) {
            uni.showToast({ title: e.message || '删除失败', icon: 'none' })
          } finally {
            this.detailSaving = false
          }
        }
      })
    },

    showUndo(feeding) {
      if (!feeding || !feeding.id) return
      this.undoFeeding = feeding
      this.undoVisible = true
      if (this.undoTimer) clearTimeout(this.undoTimer)
      this.undoTimer = setTimeout(() => {
        this.undoVisible = false
        this.undoFeeding = null
      }, 3000)
    },

    async undoLastFeeding() {
      const feeding = this.undoFeeding
      if (!feeding || !feeding.id) return
      this.undoVisible = false
      this.undoFeeding = null
      if (this.undoTimer) {
        clearTimeout(this.undoTimer)
        this.undoTimer = null
      }
      try {
        await api.delete(`/feedings/${feeding.id}`)
        uni.showToast({ title: '已撤销', icon: 'success' })
        await this.loadFeedings()
        await this.loadStats()
      } catch (e) {
        uni.showToast({ title: e.message || '撤销失败', icon: 'none' })
      }
    },

    viewUndoFeeding() {
      const feeding = this.undoFeeding
      if (!feeding) return
      this.openDetail(feeding)
    },

    openTodayModal() {
      this.showTodayModal = true
    },

    closeTodayModal() {
      this.showTodayModal = false
    },

    formatFeedingTime(raw) {
      if (!raw) return '--:--'
      const d = new Date(String(raw).replace(' ', 'T'))
      if (Number.isNaN(d.getTime())) return String(raw).slice(11, 16) || '--:--'
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${hh}:${mm}`
    },

    resolveMemberName(userId) {
      if (!userId) return '成员'
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(userId))
      return (m && (m.nickname || '成员')) || '成员'
    },

    goToDataDetail() {
      // tabBar 页必须用 switchTab；无法携带 query，依赖 store 的 currentBaby 即可。
      this.showTodayModal = false
      uni.switchTab({ url: '/pages/data-detail/index' })
    },
    
    goToBabyInfo() {
      uni.navigateTo({
        url: '/pages/baby-info/index'
      })
    },
    
    async showMenu() {
      const userStore = useUserStore()
      const babyId = this.currentBaby?.id
      // 菜单打开前做一次轻量权限探测，保证“管理后台”入口即时可见
      await this.checkAdmin()
      const items = [
        {
          label: '宝宝基础资料',
          onTap: () => uni.navigateTo({ url: '/pages/baby-info/index' }),
        },
        {
          label: '选择奶粉',
          onTap: () => {
            if (!babyId) return this.goToBabyInfo()
            uni.navigateTo({ url: `/pages/formula-select/index?babyId=${babyId}` })
          },
        },
        {
          label: '喂奶设置',
          onTap: () => {
            if (!babyId) return this.goToBabyInfo()
            uni.navigateTo({ url: `/pages/feeding-settings/index?babyId=${babyId}` })
          },
        },
        {
          label: '数据详情',
          onTap: () => uni.switchTab({ url: '/pages/data-detail/index' }),
        },
        {
          label: '数据报告',
          onTap: () => {
            if (!babyId) return this.goToBabyInfo()
            uni.navigateTo({ url: `/pages/report/index?babyId=${babyId}` })
          },
        },
        {
          label: '家庭共享',
          onTap: () => uni.navigateTo({ url: `/pages/family/index?babyId=${babyId || ''}` }),
        },
      ]

      if (this.isAdmin) {
        items.push({
          label: '管理后台',
          onTap: () => uni.navigateTo({ url: '/pages/admin/index' }),
        })
      }

      items.push({
        label: '退出登录',
        onTap: () => userStore.logout(),
      })

      uni.showActionSheet({
        itemList: items.map((x) => x.label),
        success: (res) => {
          const idx = res.tapIndex
          const hit = items[idx]
          if (hit && typeof hit.onTap === 'function') hit.onTap()
        }
      })
    },
    
    startCountdown() {
      if (this.countdownTimer) clearInterval(this.countdownTimer)

      const tick = () => {
        const nowMs = Date.now()
        this.nowTickMs = nowMs

        // 距上次喂奶已过去
        const lastMs = this.lastFeedingTimestampMs
        if (Number.isFinite(lastMs) && lastMs > 0) {
          this.sinceLastFeedingText = `距上次喂奶已过去 ${this.formatDurationText(nowMs - lastMs)}`
        } else {
          this.sinceLastFeedingText = '暂无喂奶记录'
        }

        // 下次喂奶：严格以服务端 timestamp 为准（与喂奶设置口径一致）
        let nextMs = this.nextFeedingTimestampMs
        if (!nextMs && this.stats?.next_feeding_time) {
          nextMs = this.parseTimeToMs(this.stats.next_feeding_time)
        }
        if (Number.isFinite(nextMs) && nextMs > 0) {
          this.nextFeedingClockText = this.formatClockText(nextMs)
          this.nextFeedingDayLabel = this.formatDayLabel(nextMs, nowMs)
          this.maybeFireInAppReminder(nextMs, nowMs)
        } else {
          this.nextFeedingClockText = '--:--'
          this.nextFeedingDayLabel = ''
        }
      }

      tick()
      this.countdownTimer = setInterval(tick, 1000)
    },

    maybeFireInAppReminder(targetMs, nowMs) {
      const s = this.feedingSettings || {}
      const enabled = s.reminder_enabled !== false
      if (!enabled) return

      const advMin = Math.max(0, Number(s.advance_minutes ?? 15) || 0)
      const advMs = advMin * 60 * 1000

      // 每个“下次喂奶时间”最多触发一次提前提示 + 一次到点提示
      if (advMin > 0 && this.remindAdvanceFiredFor !== targetMs) {
        const advAt = targetMs - advMs
        if (nowMs >= advAt && nowMs < targetMs) {
          this.remindAdvanceFiredFor = targetMs
          uni.showToast({ title: `还有${advMin}分钟到下次喂奶`, icon: 'none' })
        }
      }
      if (this.remindDueFiredFor !== targetMs && nowMs >= targetMs) {
        this.remindDueFiredFor = targetMs
        try { uni.vibrateShort() } catch {}
        uni.showToast({ title: '该喂奶了', icon: 'none' })
      }
    }
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: transparent;
  /* 预留 tabbar + 大按钮 + 安全区 */
  padding-bottom: calc(160px + env(safe-area-inset-bottom, 0px));
  position: relative;
}

/* 顶部菜单 */
.top-menu {
  position: fixed;
  top: 0;
  right: 0;
  padding: 16px;
  padding-top: calc(12px + env(safe-area-inset-top, 0px));
  z-index: 100;
}

.menu-icon {
  display: flex;
  flex-direction: column;
  gap: 5px;
  cursor: pointer;
  width: 30px;
  height: 30px;
  justify-content: center;
}

.menu-line {
  display: block;
  width: 24px;
  height: 3px;
  background-color: #333;
  border-radius: 2px;
}

/* 宝宝信息区域 */
.baby-profile-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: calc(68px + env(safe-area-inset-top, 0px)) 20px 28px;
}

.baby-avatar-large {
  width: 100px;
  height: 100px;
  border-radius: 50px;
  overflow: hidden;
  background: #FFD700;
  margin-bottom: 12px;
  border: 2px solid #E0E0E0;
  box-sizing: border-box;
  z-index: 2;
  position: relative;
}

.avatar-img-large {
  width: 100%;
  height: 100%;
}

.baby-name-row {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.baby-name-large {
  font-size: 32px;
  font-weight: 800;
  color: #333;
  text-align: center;
  line-height: 1.2;
}

.baby-stats-row {
  display: flex;
  flex-direction: row;
  gap: 12px;
  justify-content: center;
  align-items: center;
}

.stat-text {
  font-size: 15px;
  font-weight: 700;
  color: rgba(27, 26, 23, 0.62);
  white-space: nowrap;
}

.stat-dot {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.40);
}

/* 今日概览卡（减焦虑：用“状态+建议+一键动作”替代难读的瓶子轨道） */
.today-card {
  margin: 10px var(--nb-page-x) 0;
  padding: 16px 16px 14px;
  border-radius: 24px;
  border: 1px solid var(--nb-border);
  background:
    radial-gradient(720px 260px at 18% 0%, rgba(247, 201, 72, 0.22), rgba(247, 201, 72, 0) 60%),
    radial-gradient(520px 260px at 100% 30%, rgba(255, 138, 61, 0.16), rgba(255, 138, 61, 0) 62%),
    rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 44px rgba(27, 26, 23, 0.12);
  box-sizing: border-box;
}

.today-card:active {
  transform: scale(0.995);
}

.today-head {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.today-title {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 6px;
  color: var(--nb-text);
}

.today-title-prefix,
.today-title-suffix {
  font-size: 14px;
  font-weight: 700;
  color: rgba(27, 26, 23, 0.78);
}

.today-title-num {
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -1px;
  line-height: 1;
}

.health-pill {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(27, 26, 23, 0.12);
  background: rgba(27, 26, 23, 0.06);
}

.health-pill-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.72);
}

.lv-excellent {
  background: rgba(46, 125, 50, 0.12);
  border-color: rgba(46, 125, 50, 0.22);
}
.lv-excellent .health-pill-text { color: #2e7d32; }

.lv-good {
  background: rgba(25, 118, 210, 0.12);
  border-color: rgba(25, 118, 210, 0.22);
}
.lv-good .health-pill-text { color: #1976d2; }

.lv-attention {
  background: rgba(255, 138, 61, 0.16);
  border-color: rgba(255, 138, 61, 0.24);
}
.lv-attention .health-pill-text { color: rgba(181, 83, 29, 0.95); }

.lv-alert {
  background: rgba(226, 74, 59, 0.12);
  border-color: rgba(226, 74, 59, 0.22);
}
.lv-alert .health-pill-text { color: var(--nb-danger); }

.today-sub {
  margin-top: 10px;
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 8px;
}

.today-sub-strong {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.today-sub-dot {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.38);
}

.today-sub-muted {
  font-size: 13px;
  color: var(--nb-muted);
}

.today-progress {
  margin-top: 12px;
}

.today-progress-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.today-progress-left,
.today-progress-right {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.70);
}

.today-progress-bar {
  width: 100%;
  height: 8px;
  border-radius: 6px;
  background: rgba(27, 26, 23, 0.10);
  overflow: hidden;
  position: relative;
}

.today-progress-fill {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--nb-accent) 0%, var(--nb-accent-2) 100%);
}

.today-progress-marker {
  position: absolute;
  top: -2px;
  width: 2px;
  height: 12px;
  background: rgba(27, 26, 23, 0.55);
  border-radius: 2px;
  transform: translateX(-1px);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.55);
}

.tone-low .today-progress-fill {
  background: linear-gradient(90deg, rgba(255, 138, 61, 0.95) 0%, rgba(255, 186, 72, 0.95) 100%);
}
.tone-high .today-progress-fill {
  background: linear-gradient(90deg, rgba(226, 74, 59, 0.95) 0%, rgba(226, 74, 59, 0.70) 100%);
}

.today-progress-text {
  margin-top: 8px;
  display: block;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
}

.today-timeline {
  margin-top: 12px;
}

.today-timeline-head {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.today-timeline-title {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.78);
}

.today-timeline-sub {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.50);
}

.today-timeline-track {
  margin-top: 8px;
  position: relative;
  height: 22px;
}

.today-timeline-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 12px;
  height: 2px;
  border-radius: 2px;
  background: rgba(27, 26, 23, 0.12);
}

.today-timeline-now {
  position: absolute;
  top: 0;
  width: 2px;
  height: 22px;
  background: rgba(27, 26, 23, 0.28);
  border-radius: 2px;
  transform: translateX(-1px);
}

.today-timeline-mark {
  position: absolute;
  bottom: 8px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.today-timeline-stick {
  width: 2px;
  background: rgba(27, 26, 23, 0.55);
  border-radius: 2px;
}

.today-timeline-dot {
  border-radius: 999px;
  background: rgba(255, 138, 61, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 6px 14px rgba(27, 26, 23, 0.14);
}

.today-timeline-axis {
  margin-top: 6px;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
}

.today-timeline-axis .axis-item {
  font-size: 11px;
  color: rgba(27, 26, 23, 0.48);
}

.today-next {
  margin-top: 14px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
}

.today-next-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.today-next-label {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
}

.today-next-amount {
  font-size: 13px;
  font-weight: 800;
  color: rgba(27, 26, 23, 0.70);
  line-height: 1.3;
}

.today-next-countdown {
  font-size: 30px;
  font-weight: 900;
  color: var(--nb-text);
  font-family: 'Courier New', monospace;
  letter-spacing: 2px;
  line-height: 1.05;
}

.today-hint {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.today-hint-text {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.78);
  line-height: 1.6;
}

.today-advice {
  margin-top: 2px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(27, 26, 23, 0.10);
  background: rgba(255, 255, 255, 0.70);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.today-advice-title {
  font-size: 12px;
  font-weight: 900;
  color: rgba(27, 26, 23, 0.78);
}

.today-advice-item {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.70);
  line-height: 1.55;
}

.today-hint-disclaimer {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.50);
}

.today-meta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(27, 26, 23, 0.10);
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.today-meta-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
}

.today-meta-link {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.72);
  text-decoration: underline;
  text-underline-offset: 4px;
}

/* 投喂按钮 */
.feed-button-large {
  position: fixed;
  /* 贴底会压到 tabbar / 手势条，向上抬并考虑安全区 */
  bottom: calc(96px + var(--nb-safe-bottom));
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 100px;
  border-radius: 50px;
  background-color: #333;
  border: 3px solid #FFD700;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.feed-button-large:active {
  transform: translateX(-50%) scale(0.95);
}

.feed-button-text {
  color: #fff;
  font-size: 24px;
  font-weight: 600;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}

.modal-content {
  width: 90%;
  max-width: 500px;
  background: #fff;
  border-radius: 20px;
  padding: 30px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-overlay.sheet {
  align-items: flex-end;
}

.modal-content.sheet {
  width: 100%;
  max-width: 560px;
  border-radius: 24px 24px 0 0;
  padding: 18px 16px calc(18px + var(--nb-safe-bottom));
  background:
    radial-gradient(900px 320px at 20% 0%, rgba(247, 201, 72, 0.18), rgba(247, 201, 72, 0) 60%),
    radial-gradient(700px 320px at 100% 20%, rgba(255, 138, 61, 0.14), rgba(255, 138, 61, 0) 62%),
    rgba(255, 255, 255, 0.96);
  max-height: 78vh;
  overflow: hidden;
}

.today-modal-summary {
  margin-top: -6px;
  margin-bottom: 12px;
}

.today-modal-summary-text {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.70);
}

.today-modal-meta {
  margin-top: -4px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.70);
  border: 1px solid rgba(27, 26, 23, 0.10);
}

.today-modal-meta-text {
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
  line-height: 1.5;
}

.today-modal-empty {
  padding: 18px 0 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.today-modal-empty-text {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.72);
}

.today-modal-empty-sub {
  font-size: 13px;
  color: rgba(27, 26, 23, 0.58);
}

.today-modal-list {
  height: 44vh;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(27, 26, 23, 0.10);
  overflow: hidden;
}

.today-item {
  padding: 12px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid rgba(27, 26, 23, 0.08);
}

.today-item:last-child {
  border-bottom: none;
}

.today-item-time {
  width: 52px;
  font-size: 13px;
  color: rgba(27, 26, 23, 0.66);
  font-family: 'Courier New', monospace;
}

.today-item-amount {
  flex: 1;
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
  text-align: left;
}

.today-item-user {
  width: 88px;
  text-align: right;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.62);
}

.modal-header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.close-btn {
  font-size: 36px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.modal-actions {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  margin-top: 30px;
  gap: 15px;
}

.cancel-btn, .confirm-btn {
  flex: 1;
  height: 50px;
  border-radius: 25px;
  font-size: 18px;
  border: none;
  cursor: pointer;
}

.cancel-btn {
  background: #f5f5f5;
  color: #666;
}

.confirm-btn {
  background: #FFD700;
  color: #333;
  font-weight: 600;
}

.cancel-btn:active {
  background: #e0e0e0;
}

.confirm-btn:active {
  background: #FFC107;
}

/* 撤销条（保存后 3 秒） */
.undo-toast {
  position: fixed;
  left: var(--nb-page-x);
  right: var(--nb-page-x);
  bottom: calc(200px + env(safe-area-inset-bottom, 0px));
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 12px 14px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-shadow: 0 10px 28px rgba(27, 26, 23, 0.12);
  z-index: 998;
}

.undo-text {
  font-size: 14px;
  color: var(--nb-text);
  font-weight: 700;
}

.undo-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.undo-action {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.72);
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 4px;
}

/* 详情弹窗补充样式（复用 modal-* 基础结构） */
.detail-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(27, 26, 23, 0.08);
}

.detail-label {
  font-size: 14px;
  color: rgba(27, 26, 23, 0.62);
}

.detail-value {
  font-size: 14px;
  color: #333;
  font-weight: 700;
}

.detail-edit {
  padding: 14px 0 6px;
}

.detail-input-wrap {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  border: 2px solid rgba(27, 26, 23, 0.10);
  border-radius: 14px;
  padding: 0 14px;
  min-height: 48px;
  box-sizing: border-box;
}

.detail-input-wrap:focus-within {
  border-color: var(--nb-accent);
}

.detail-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 18px;
  height: 48px;
}

.detail-input:focus {
  outline: none;
}

.detail-unit {
  color: rgba(27, 26, 23, 0.45);
  font-size: 14px;
  font-weight: 700;
}

.detail-hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: rgba(27, 26, 23, 0.52);
}

.danger-row {
  margin-top: 12px;
}

.danger-btn {
  width: 100%;
  height: 44px;
  border-radius: 22px;
  border: 1px solid rgba(226, 74, 59, 0.22);
  background: rgba(226, 74, 59, 0.10);
  color: #E24A3B;
  font-weight: 800;
}

.danger-btn[disabled] {
  background: rgba(27, 26, 23, 0.08);
  border-color: rgba(27, 26, 23, 0.10);
  color: rgba(27, 26, 23, 0.45);
}

/* 响应式设计 */
@media (max-width: 480px) {
  .baby-avatar-large {
    width: 100px;
    height: 100px;
    border-radius: 50px;
  }
  
  .baby-name-large {
    font-size: 28px;
  }
  
  .total-amount-value {
    font-size: 56px;
  }
  
  .countdown-time-display {
    font-size: 32px;
  }
  
  .feed-button-large {
    width: 90px;
    height: 90px;
    border-radius: 45px;
  }
  
  .feed-button-text {
    font-size: 22px;
  }
}
</style>
