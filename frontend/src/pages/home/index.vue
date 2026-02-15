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

	    <view class="home-main">
	      <NbNetworkBanner />

        <NbLoadable
          :loading="pageLoading"
          :errorText="errorText"
          :empty="!currentBaby.id"
          emptyType="info"
          emptyTitle="还没有宝宝档案"
          emptyDesc="先创建宝宝，才能开始记录与计算下次喂奶"
          emptyActionText="去建档"
          @retry="onNbRetry"
          @emptyAction="goToBabyInfo"
        >
          <template #skeleton>
            <view class="home-skel">
              <view class="baby-profile-section">
                <view class="baby-avatar-large">
                  <NbSkeletonAvatar :size="84" shape="circle" />
                </view>
                <view class="baby-name-row">
                  <NbSkeleton :w="132" :h="22" :radius="11" />
                </view>
                <view class="baby-stats-row">
                  <NbSkeleton :w="210" :h="14" :radius="7" />
                </view>
              </view>

              <view class="home-focus">
                <view class="focus-card">
                  <view class="hero">
                    <view style="display:flex;justify-content:center;">
                      <NbSkeleton :w="72" :h="12" :radius="6" />
                    </view>
                    <view style="margin-top:8px;display:flex;justify-content:center;">
                      <NbSkeleton :w="260" :h="44" :radius="22" />
                    </view>
                    <view class="hero-meta">
                      <NbSkeleton :w="240" :h="14" :radius="7" />
                    </view>
                    <view class="hero-badges">
                      <NbSkeleton :w="140" :h="26" :radius="13" />
                    </view>
                  </view>
                </view>

                <view class="focus-card">
                  <view class="timeline">
                    <view class="timeline-track">
                      <NbSkeleton :w="'100%'" :h="26" :radius="13" />
                    </view>
                    <view class="timeline-axis">
                      <NbSkeleton :w="'100%'" :h="12" :radius="6" />
                    </view>
                    <view class="timeline-summary">
                      <NbSkeleton :w="120" :h="12" :radius="6" />
                    </view>
                  </view>
                </view>
              </view>
            </view>
          </template>
	      <!-- 宝宝信息区域 -->
	      <view class="baby-profile-section">
	        <view class="baby-avatar-large" @click="goToBabyInfo">
	          <image
            :src="currentBaby.avatar_url || '/static/default-avatar.png'"
            class="avatar-img-large"
            mode="aspectFill"
          />
        </view>

        <view class="baby-name-row" @click="goBabySwitch">
          <text class="baby-name-large">{{ currentBaby.nickname || '宝宝' }}</text>
          <text class="baby-switch-chev">›</text>
        </view>

        <view class="baby-stats-row">
          <text class="stat-text">{{ babyAgeText }}</text>
          <text v-if="zodiacText" class="stat-dot">·</text>
          <text v-if="zodiacText" class="stat-text">{{ zodiacText }}</text>
        </view>
      </view>

      <!-- Setup Nudge：轻量引导（可关闭），让首次上手更像“一个产品”而不是页面集合 -->
      <view v-if="setupNudge" class="setup-nudge" @click="handleSetupNudgeTap(setupNudge)">
        <view class="setup-nudge-left">
          <view class="setup-nudge-icon" :class="`t-${setupNudge.tone || 'info'}`" aria-hidden="true">
            <text class="setup-nudge-icon-text">{{ setupNudge.icon || 'i' }}</text>
          </view>
          <view class="setup-nudge-text">
            <text class="setup-nudge-title">{{ setupNudge.title }}</text>
            <text v-if="setupNudge.desc" class="setup-nudge-desc">{{ setupNudge.desc }}</text>
          </view>
        </view>

        <view class="setup-nudge-right">
          <text class="setup-nudge-cta">{{ setupNudge.actionText }}</text>
          <text class="setup-nudge-chev">›</text>
          <text class="setup-nudge-close" @click.stop="dismissSetupNudge(setupNudge.key)">×</text>
        </view>
      </view>

      <!-- 首页信息减法：主页只保留“下次喂奶 + 时间轴”，解释与明细下钻到抽屉 -->
      <view class="home-focus">
        <view class="focus-card">
          <view class="hero">
            <text class="hero-label">下次喂奶时间</text>

            <view class="hero-time-row" aria-hidden="true">
              <view v-if="nextFeedingDayLabel" class="hero-day-pill">
                <text class="hero-day-pill-text">{{ nextFeedingDayLabel }}</text>
              </view>
              <text class="hero-time">{{ nextFeedingClockText }}</text>
            </view>

            <view class="hero-countdown-row" :class="{ overdue: nextCountdownMode === 'overdue' }">
              <text v-if="hasNextFeeding && nextCountdownMode === 'overdue'" class="hero-countdown-prefix">已超时</text>
              <text class="hero-countdown-hm">{{ nextCountdownHMText }}</text>
              <text v-if="hasNextFeeding && nextCountdownMode !== 'overdue'" class="hero-countdown-suffix">后给宝宝喂奶</text>
            </view>

            <text v-if="sinceLastDurationHMText" class="hero-meta-line">
              距上次喂奶已过去 {{ sinceLastDurationHMText }}
            </text>

            <!-- 健康信号：收敛但醒目（alert/attention 显示强结论 + 单一 CTA） -->
            <view
              v-if="homeSignalBannerVisible"
              class="health-banner"
              :class="`lv-${insightLevel}`"
              @click="openExplainModal"
            >
              <view class="health-banner-main">
                <text class="health-banner-title">{{ homeSignalTitle }}</text>
                <text v-if="homeSignalDesc" class="health-banner-desc">{{ homeSignalDesc }}</text>
              </view>
              <text class="health-banner-chev" aria-hidden="true">›</text>
            </view>

            <view class="hero-badges">
              <view v-if="!homeSignalBannerVisible" class="health-pill" :class="`lv-${insightLevel}`" @click="openExplainModal">
                <text class="health-pill-text">{{ homeStatusText }}</text>
              </view>

              <view
                v-if="weaningPillText"
                class="weaning-pill"
                :class="weaningPillClass"
                @click="goWeaningPlan"
              >
                <text class="weaning-pill-text">{{ weaningPillText }}</text>
              </view>
            </view>
          </view>
        </view>

        <view class="focus-card">
          <FeedingTimeline24
            :marks="homeTimelineMarks"
            :selectedKey="selectedTimelineKey"
            :nowMs="nowTickMs"
            :nextMs="nextFeedingTimelineMs"
            :summaryText="timelineSummaryText"
            @open="openTodayModal"
            @select="handleHomeTimelineSelect"
          />

          <!-- 预估清单：把“后续时间点”用一句话讲清楚，并给出唯一入口去调整（更线性）。 -->
          <view
            v-if="timelinePlanFootTitle"
            class="timeline-plan"
            @click.stop="goToFeedingSettings(timelinePlanFootFocus)"
          >
            <view class="timeline-plan-left">
              <text class="timeline-plan-title">{{ timelinePlanFootTitle }}</text>
              <text v-if="timelinePlanFootSub" class="timeline-plan-sub">{{ timelinePlanFootSub }}</text>
              <text v-if="timelinePlanFootHint" class="timeline-plan-hint">{{ timelinePlanFootHint }}</text>
            </view>
            <text class="timeline-plan-chev">调整 ›</text>
          </view>
        </view>
      </view>
      </NbLoadable>
    </view>
    
    <!-- 投喂按钮 -->
    <view class="feed-button-large" @click="handleHomePrimaryAction">
      <view v-if="homePrimaryAction === 'record' && weaningFeedBadgeText" class="feed-badge" :class="weaningAutoSide">
        <text class="feed-badge-text">{{ weaningFeedBadgeText }}</text>
      </view>
      <text class="feed-button-text">{{ homePrimaryButtonText }}</text>
      <text v-if="homePrimarySubText" class="feed-button-sub">{{ homePrimarySubText }}</text>
    </view>

    <!-- 撤销条：保存后 3 秒内可撤销 -->
    <view v-if="undoVisible" class="undo-toast" :class="`tone-${undoTone}`" @click.stop>
      <view class="undo-left">
        <view class="undo-icon" aria-hidden="true">
          <text class="undo-icon-text">{{ undoIconText }}</text>
        </view>
        <view class="undo-lines">
          <text class="undo-title">{{ undoTitleText }}</text>
          <text v-if="undoSubText" class="undo-sub">{{ undoSubText }}</text>
        </view>
      </view>

      <view class="undo-actions">
        <view class="undo-btn primary" @click.stop="undoLastFeeding">撤销</view>
        <view class="undo-btn" @click.stop="viewUndoFeeding">查看</view>
      </view>
    </view>

    <!-- 状态说明（底部 Sheet）：解释不常驻首页，按需展开（更“苹果”） -->
    <view v-if="showExplainModal" class="modal-overlay sheet" @click.self="closeExplainModal">
      <view class="modal-content sheet" @click.stop @touchstart.stop>
        <view class="modal-header">
          <text class="modal-title">{{ homeStatusText }}</text>
          <text class="close-btn" @click="closeExplainModal">×</text>
        </view>

        <view class="today-sub">
          <text class="today-sub-strong">下次喂奶时间：{{ nextFeedingDayLabel ? (nextFeedingDayLabel + ' ') : '' }}{{ nextFeedingClockText }}</text>
          <text v-if="hasNextFeeding" class="today-sub-muted">
            <text v-if="nextCountdownMode === 'overdue'">已超时 {{ nextCountdownHMText }}</text>
            <text v-else>{{ nextCountdownHMText }} 后给宝宝喂奶</text>
          </text>
          <text v-if="sinceLastDurationHMText" class="today-sub-muted">距上次喂奶已过去 {{ sinceLastDurationHMText }}</text>
        </view>

        <!-- 信息减法：把“建议本次奶量”放到说明 Sheet（主屏不常驻堆字） -->
        <view v-if="nextSuggestedAmount > 0" class="suggest-card">
          <text class="suggest-k">建议</text>
          <text class="suggest-v">{{ nextSuggestedAmount }}ml</text>
          <text v-if="suggestScoopsText" class="suggest-sub">{{ suggestScoopsText }}</text>
          <text v-else-if="canShowScoopHint" class="suggest-sub suggest-link" @click="goToFormulaSpec">补充勺数换算</text>
        </view>

        <view class="today-progress" :class="`tone-${amountProgressTone}`" v-if="todayTargetMl > 0">
          <view class="today-progress-head">
            <text class="today-progress-left">今日 {{ todayConsumedMl }}ml</text>
            <text class="today-progress-right">参考 {{ todayTargetMl }}ml</text>
          </view>
          <view class="today-progress-bar">
            <view class="today-progress-fill" :style="{ width: todayConsumedPercent + '%' }"></view>
            <view v-if="expectedNowPercent" class="today-progress-marker" :style="{ left: expectedNowPercent + '%' }"></view>
          </view>
          <view v-if="todayDeltaText" class="today-progress-delta-row">
            <text class="today-progress-delta" :class="`d-${todayDeltaTone}`">{{ todayDeltaText }}</text>
          </view>
          <text v-if="expectedNowMl > 0" class="today-progress-text">按时间进度，此刻约 {{ expectedNowMl }}ml</text>
        </view>

        <view v-if="insightAdviceItems.length > 0" class="today-advice">
          <text class="today-advice-title">下一步</text>
          <text v-for="(it, idx) in insightAdviceItems.slice(0, 2)" :key="idx" class="today-advice-item">{{ it }}</text>
        </view>

        <text class="today-hint-disclaimer">仅供趋势参考，不替代医生建议</text>

        <view class="modal-actions">
          <button class="confirm-btn" @click="openTodayFromExplain">查看今日记录</button>
        </view>
      </view>
    </view>

    <!-- 今日喂奶详情（底部抽屉） -->
    <view v-if="showTodayModal" class="modal-overlay sheet" @click.self="closeTodayModal">
      <view class="modal-content sheet" @click.stop @touchstart.stop>
        <view class="modal-header">
          <text class="modal-title">今日喂奶记录</text>
          <text class="close-btn" @click="closeTodayModal">×</text>
        </view>

        <NbState v-if="todayModalLoading" embedded type="loading" title="加载中..." />

        <NbState
          v-else-if="todayModalError"
          embedded
          type="error"
          title="加载失败"
          :desc="todayModalError"
          actionText="重试"
          @action="reloadTodayModal"
        />

        <template v-else>
          <view v-if="formulaMetaText" class="today-modal-meta">
            <text class="today-modal-meta-text">{{ formulaMetaText }}</text>
          </view>

          <!-- 24小时喂奶时间轴：看分布 + 量差异 -->
          <view v-if="todayCount > 0" class="today-timeline-wrap">
            <FeedingTimeline24
              :marks="todayTimelineMarks"
              :selectedKey="selectedTimelineKey"
              :nowMs="nowTickMs"
              :summaryText="todayModalSummaryText"
              :showNext="false"
              @select="handleTodayTimelineSelect"
            />
          </view>

          <!-- 异常日原因提示 + 一键修复入口：不让用户猜“为什么为空/不对劲” -->
          <view v-if="todayFixRows.length > 0 && todayCount <= 0" class="today-fix">
            <view class="today-fix-head">
              <text class="today-fix-title">需要处理</text>
              <text class="today-fix-sub">修好后统计会更准</text>
            </view>
            <view
              v-for="it in todayFixRows"
              :key="it.key"
              class="today-fix-row"
              @click.stop="handleTodayFixRow(it)"
            >
              <view class="today-fix-left">
                <view class="today-fix-dot" :class="`t-${it.tone || 'warn'}`" aria-hidden="true"></view>
                <view class="today-fix-texts">
                  <text class="today-fix-main">{{ it.title }}</text>
                  <text v-if="it.desc" class="today-fix-desc">{{ it.desc }}</text>
                </view>
              </view>
              <text class="today-fix-cta">{{ it.actionText }} ›</text>
            </view>
          </view>

          <view v-if="todayCount <= 0" class="today-modal-empty">
            <text class="today-modal-empty-text">{{ todayEmptyTitle }}</text>
            <text class="today-modal-empty-sub">{{ todayEmptySub }}</text>
          </view>

          <scroll-view v-else class="today-modal-list" scroll-y>
            <view v-if="todayFixRows.length > 0" class="today-fix in-list">
              <view class="today-fix-head">
                <text class="today-fix-title">需要处理</text>
                <text class="today-fix-sub">修好后统计会更准</text>
              </view>
              <view
                v-for="it in todayFixRows"
                :key="it.key"
                class="today-fix-row"
                @click.stop="handleTodayFixRow(it)"
              >
                <view class="today-fix-left">
                  <view class="today-fix-dot" :class="`t-${it.tone || 'warn'}`" aria-hidden="true"></view>
                  <view class="today-fix-texts">
                    <text class="today-fix-main">{{ it.title }}</text>
                    <text v-if="it.desc" class="today-fix-desc">{{ it.desc }}</text>
                  </view>
                </view>
                <text class="today-fix-cta">{{ it.actionText }} ›</text>
              </view>
            </view>

            <view
              v-for="f in todayFeedings"
              :key="f.id"
              class="today-swipe"
              :class="{ open: swipeOpenFeedingKey === String(f.id) }"
              @touchstart="onFeedingSwipeStart($event, f)"
              @touchend="onFeedingSwipeEnd($event, f)"
              @touchcancel="onFeedingSwipeEnd($event, f)"
            >
              <!-- 默认不渲染操作区，避免“未左滑就露出编辑/删除”与内容重叠（更像 iOS 交互） -->
              <view
                v-if="canEditFeeding(f) && swipeOpenFeedingKey === String(f.id)"
                class="today-swipe-actions"
              >
                <view class="today-swipe-action edit" @click.stop="swipeEdit(f)">
                  <text class="today-swipe-action-text">编辑</text>
                </view>
                <view class="today-swipe-action delete" @click.stop="swipeDelete(f)">
                  <text class="today-swipe-action-text">删除</text>
                </view>
              </view>

              <view class="today-swipe-content">
                <view class="today-item" @click="handleFeedingRowTap(f)">
                  <view class="today-item-left">
                    <text class="today-item-time">{{ formatFeedingTime(f.feeding_time) }}</text>
                    <text class="today-item-amount">{{ Number(f.amount || 0) }}ml</text>
                    <view v-if="weaningTagTextForFeeding(f)" class="today-item-tag" :class="weaningTagClassForFeeding(f)">
                      <text class="today-item-tag-text">{{ weaningTagTextForFeeding(f) }}</text>
                    </view>
                  </view>
                  <text v-if="showFeedingUserName" class="today-item-user">{{ resolveMemberName(f.user_id) }}</text>
                </view>
              </view>
            </view>
          </scroll-view>

          <view class="modal-actions">
            <button class="cancel-btn" @click="closeTodayModal">关闭</button>
            <button class="confirm-btn" @click="goToDataDetail">查看数据</button>
          </view>
        </template>
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

        <view class="detail-row" :class="{ disabled: !canEditDetail }">
          <text class="detail-label">日期</text>
          <picker
            class="detail-picker-wrap"
            mode="date"
            :value="detailDate"
            :disabled="!canEditDetail"
            @change="onDetailDateChange"
          >
            <view class="detail-picker">
              <text class="detail-value">{{ detailDateText }}</text>
              <text v-if="canEditDetail" class="detail-chev">›</text>
            </view>
          </picker>
        </view>

        <view class="detail-row" :class="{ disabled: !canEditDetail }">
          <text class="detail-label">时间</text>
          <picker
            class="detail-picker-wrap"
            mode="time"
            :value="detailClock"
            :disabled="!canEditDetail"
            @change="onDetailTimeChange"
          >
            <view class="detail-picker">
              <text class="detail-value">{{ detailClockText }}</text>
              <text v-if="canEditDetail" class="detail-chev">›</text>
            </view>
          </picker>
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

	    <NbConfirmSheet
	      :visible="confirmSheetVisible"
	      :title="confirmSheetTitle"
	      :desc="confirmSheetDesc"
	      :confirmText="confirmSheetConfirmText"
	      :cancelText="confirmSheetCancelText"
	      :confirmVariant="confirmSheetVariant"
	      :loading="confirmSheetLoading"
        :showCancel="confirmSheetShowCancel"
	      @confirm="handleConfirmSheetConfirm"
	      @cancel="handleConfirmSheetCancel"
	    />
	  </view>
	</template>

	<script>
	import api from '@/utils/api'
  import config from '@/utils/config.js'
	import { useUserStore } from '@/stores/user'
import { calcAgeInDays, diffYmd, formatBabyAgeText, parseBirthDateToLocal } from '@/utils/age'
import { formatZodiacText } from '@/utils/zodiac'
  import { parseAgeRangeToStage } from '@/utils/formula_stage'
  import { applyCustomSpecIfMissing, buildCustomFormulaSpecKey, readCustomFormulaSpec } from '@/utils/custom_formula_spec'
	import {
    canUseSystemNotify,
    getNotificationPermission,
    getSystemNotifyEnabled,
    isNotificationSupported,
    isPageHidden,
    isStandalonePwa,
    sendSystemNotify,
  } from '@/utils/system_notify'
	import NbConfirmSheet from '@/components/NbConfirmSheet.vue'
	import NbNetworkBanner from '@/components/NbNetworkBanner.vue'
  import NbState from '@/components/NbState.vue'
  import NbLoadable from '@/components/NbLoadable.vue'
  import NbSkeleton from '@/components/NbSkeleton.vue'
  import NbSkeletonAvatar from '@/components/NbSkeletonAvatar.vue'
  import FeedingTimeline24 from '@/components/FeedingTimeline24.vue'

	export default {
	  components: { NbConfirmSheet, NbNetworkBanner, NbState, NbLoadable, NbSkeleton, NbSkeletonAvatar, FeedingTimeline24 },
	  data() {
	    return {
      currentBaby: {},
      pageLoading: false,
      errorText: '',
      todayFeedings: [],
      futureFeedings: [],
      invalidTimeFeedings: [],
      feedingsMeta: {
        rawCount: 0,
        validCount: 0,
        futureCount: 0,
        invalidTimeCount: 0,
      },
      stats: {},
      familyMembers: [],
      selectedFormula: null,
      formulaSpec: null,
      // 自定义冲泡规格（v1：本机存储，用于补齐官方缺失字段）
      customFormulaSpecKey: '',
      customFormulaSpec: null,
      customWeaningOldKey: '',
      customWeaningOldSpec: null,
      customWeaningNewKey: '',
      customWeaningNewSpec: null,
      weaningPlan: null,
      weaningOldSpec: null,
      weaningNewSpec: null,
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
      nextCountdownText: '--',
      nextCountdownMode: 'remaining', // remaining | overdue
      showTodayModal: false,
      showExplainModal: false,
      lastFeedingTimestampMs: null,
      nextFeedingTimestampMs: null,
      countdownTimer: null,
      remindAdvanceFiredFor: null,
      remindDueFiredFor: null,
      nowTickMs: 0,
      recentFeedings: [],
      selectedTimelineKey: '',
      timelineSelectTimer: null,

      // iOS 左滑操作（编辑/删除）
      swipeOpenFeedingKey: '',
      swipeStartX: 0,
      swipeStartY: 0,
      swipeStartKey: '',

      // 撤销条（保存后 3 秒内）
      undoVisible: false,
      undoFeeding: null,
      undoMeta: null,
      undoTimer: null,

      // 详情/编辑
      showDetailModal: false,
      detailFeeding: null,
      detailAmount: '',
      detailDate: '', // YYYY-MM-DD（picker value）
      detailClock: '', // HH:mm（picker value）
      detailOriginalMs: null,
      detailSaving: false,

      // WebSocket（多设备/多成员实时同步）
      socketTask: null,
      wsRefreshTimer: null,

      // 生长趋势（用于首页“科学判断”）
      growthStats: null,

      // 投喂状态
      quickFeeding: false,
      lastFeedTapAtMs: 0,

      // 今日抽屉：打开时主动刷新，避免“偶发空白/旧数据”
      todayModalLoading: false,
      todayModalError: '',

      // 首页轻量引导（Setup Nudge）：按 baby 维度记忆已关闭的提示项
      dismissedNudgeKeys: [],

	      // 避免首次进入 onShow 重复请求（uni-app 生命周期：onLoad -> onShow）
	      hasLoaded: false,

	      // 统一 iOS 风格确认 Sheet（替代 uni.showModal）
	      confirmSheetVisible: false,
	      confirmSheetTitle: '',
	      confirmSheetDesc: '',
	      confirmSheetConfirmText: '确定',
	      confirmSheetCancelText: '取消',
	      confirmSheetVariant: 'primary', // primary | danger
	      confirmSheetLoading: false,
        confirmSheetShowCancel: true,
	      confirmSheetResolver: null,
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

    babyAgeMonthsInt() {
      const birth = parseBirthDateToLocal(this.currentBaby?.birth_date)
      if (!birth) return 0
      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (Number.isNaN(now.getTime())) return 0
      const { years, months } = diffYmd(birth, now)
      return Math.max(0, Number(years || 0) * 12 + Number(months || 0))
    },

    // 按月龄推算的“推荐段数”（以包装说明为准）：用于换段提醒与检查
    recommendedStageByAge() {
      const m = Number(this.babyAgeMonthsInt || 0)
      if (!Number.isFinite(m)) return 0
      if (m < 6) return 1
      if (m < 12) return 2
      if (m < 36) return 3
      return 4
    },

    // 当前绑定奶粉的“段数”（来自 selection.age_range）；0 表示未指定/无法解析
    currentFormulaStage() {
      const stage = parseAgeRangeToStage(this.selectedFormula?.age_range)
      return stage > 0 ? stage : 0
    },

    // 段数边界的“提前提醒”：例如快到 6/12/36 个月时，提前 10 天提醒准备换段（以包装为准）
    stageBoundarySoon() {
      const birth = parseBirthDateToLocal(this.currentBaby?.birth_date)
      if (!birth) return null
      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (Number.isNaN(now.getTime())) return null

      const leadDays = 10
      const dayMs = 24 * 60 * 60 * 1000
      const boundaries = [
        { boundaryMonths: 6, nextStage: 2 },
        { boundaryMonths: 12, nextStage: 3 },
        { boundaryMonths: 36, nextStage: 4 },
      ]

      let best = null
      for (const b of boundaries) {
        const atMs = new Date(
          birth.getFullYear(),
          birth.getMonth() + Number(b.boundaryMonths || 0),
          birth.getDate(),
          0,
          0,
          0,
          0
        ).getTime()
        if (!Number.isFinite(atMs) || atMs <= 0) continue
        const diffDays = Math.ceil((atMs - nowMs) / dayMs)
        if (!Number.isFinite(diffDays) || diffDays < 0 || diffDays > leadDays) continue
        if (!best || atMs < best.atMs) best = { ...b, atMs, diffDays }
      }
      return best
    },

    isBabyAdmin() {
      const userStore = useUserStore()
      const me = userStore.user?.id
      if (!me) return false
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(me))
      return m?.role === 'admin'
    },

    // 检测“已切换到新奶粉，但未开启转奶计划”的场景：给一个线性入口开始 7 天转奶
    weaningSuggestion() {
      if (this.hasWeaningPlan) return null

      const newId = Number(this.selectedFormula?.brand_id || 0)
      if (!Number.isFinite(newId) || newId <= 0) return null

      const nowMs = Number(this.nowTickMs || Date.now())
      const list = Array.isArray(this.recentFeedings) ? this.recentFeedings : []

      let oldFeeding = null
      for (const f of list) {
        const bid = Number(f?.formula_brand_id || 0)
        if (!Number.isFinite(bid) || bid <= 0) continue
        if (bid !== newId) {
          oldFeeding = f
          break
        }
      }
      if (!oldFeeding) return null

      const oldId = Number(oldFeeding?.formula_brand_id || 0)
      if (!Number.isFinite(oldId) || oldId <= 0 || oldId === newId) return null

      const oldMs = this.parseTimeToMs(oldFeeding?.feeding_time)
      // 太久远的“历史品牌”不再提示，避免误判（例如几个月前换过一次）
      const maxAgeMs = 45 * 24 * 60 * 60 * 1000
      if (Number.isFinite(oldMs) && oldMs > 0 && Number.isFinite(nowMs) && nowMs - oldMs > maxAgeMs) return null

      return {
        key: `weaning_${oldId}_${newId}`,
        oldBrandId: oldId,
        oldSeriesName: String(oldFeeding?.formula_series_name || ''),
        oldAtMs: Number.isFinite(oldMs) ? oldMs : 0,
        newBrandId: newId,
        newSeriesName: String(this.selectedFormula?.series_name || ''),
        newAgeRange: String(this.selectedFormula?.age_range || ''),
      }
    },
	    // 奶粉段位徽标：对 0-12 月场景，按月龄给出 1/2 段的轻提示
	    formulaStageBadge() {
	      // 优先使用用户已选择的段位（换段时更符合直觉）；缺失再用月龄兜底推断
	      const stage = parseAgeRangeToStage(this.selectedFormula?.age_range)
	      if (stage > 0) return String(stage)

	      const days = Number(this.babyAge || 0)
	      if (!Number.isFinite(days)) return '1'
	      return days < 180 ? '1' : '2'
	    },

      effectiveCurrentSpec() {
        // 当前奶粉的“有效规格”：官方优先，缺失字段用本机补充兜底。
        const formula = this.selectedFormula || null
        const official = this.formulaSpec || null
        const custom = this.customFormulaSpec || null
        if (!formula || !formula.brand_id) return official || custom || null
        return applyCustomSpecIfMissing(official, custom).spec || official || custom || null
      },

      effectiveCurrentScoopMl() {
        const ml = Number(this.effectiveCurrentSpec?.scoop_ml || 0)
        return Number.isFinite(ml) && ml > 0 ? ml : 0
      },

      // 转奶期（7天）：首页仅做“轻提示”，详细下钻到转奶页
      hasWeaningPlan() {
        return !!(this.weaningPlan && this.weaningPlan.id)
      },

      weaningDurationDays() {
        const d = Number(this.weaningPlan?.duration_days || 0)
        return Number.isFinite(d) && d > 0 ? d : 7
      },

      weaningStartMs() {
        const ms = this.parseTimeToMs(this.weaningPlan?.start_at)
        return Number.isFinite(ms) && ms > 0 ? ms : 0
      },

      weaningEndMs() {
        const start = this.weaningStartMs
        if (!start) return 0
        return start + this.weaningDurationDays * 24 * 60 * 60 * 1000
      },

      weaningCompleted() {
        const end = this.weaningEndMs
        if (!end) return false
        const now = Number(this.nowTickMs || Date.now())
        return Number.isFinite(now) && now >= end
      },

      weaningDayIndex() {
        const start = this.weaningStartMs
        if (!start) return 0
        const now = Number(this.nowTickMs || Date.now())
        if (!Number.isFinite(now) || now <= 0) return 0
        const diff = Math.max(0, now - start)
        const day = Math.floor(diff / (24 * 60 * 60 * 1000)) + 1
        return Math.min(this.weaningDurationDays, Math.max(1, day))
      },

      weaningAutoEnabled() {
        return this.hasWeaningPlan && this.weaningPlan?.status === 'active' && !this.weaningCompleted
      },

      weaningAutoSide() {
        if (!this.weaningAutoEnabled) return ''
        const plan = this.weaningPlan || null
        const startMs = this.weaningStartMs
        const oldId = Number(plan?.old_brand_id || 0)
        const newId = Number(plan?.new_brand_id || 0)
        if (!startMs || !oldId || !newId) return ''

        const list = Array.isArray(this.recentFeedings) ? this.recentFeedings : []
        const last = list.find((f) => {
          const t = this.parseTimeToMs(f?.feeding_time)
          if (!Number.isFinite(t) || t < startMs) return false
          const bid = Number(f?.formula_brand_id || 0)
          return bid === oldId || bid === newId
        })
        if (!last) return 'old'
        return Number(last?.formula_brand_id || 0) === oldId ? 'new' : 'old'
      },

      weaningFeedBadgeText() {
        if (!this.weaningAutoEnabled) return ''
        return this.weaningAutoSide === 'old' ? '旧' : this.weaningAutoSide === 'new' ? '新' : ''
      },

      weaningPillText() {
        if (!this.hasWeaningPlan) return ''
        if (this.weaningCompleted) return '转奶完成'
        if (this.weaningPlan?.status === 'paused') return '转奶已暂停'
        const d = this.weaningDurationDays
        const idx = this.weaningDayIndex
        if (!idx || !d) return '转奶中'
        return `转奶中 第${idx}/${d}天`
      },

      weaningPillClass() {
        if (!this.hasWeaningPlan) return ''
        if (this.weaningCompleted) return 'done'
        if (this.weaningPlan?.status === 'paused') return 'paused'
        return 'active'
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

    lastFeedingAmountText() {
      const last = Array.isArray(this.recentFeedings) ? this.recentFeedings[0] : null
      const n = Number(last?.amount || 0)
      if (!Number.isFinite(n) || n <= 0) return ''
      return `${Math.round(n)}ml`
    },

    lastFeedingClockText() {
      const lastMs = Number(this.lastFeedingTimestampMs || 0)
      if (!Number.isFinite(lastMs) || lastMs <= 0) return ''
      const t = this.formatClockText(lastMs)
      return t && t !== '--:--' ? t : ''
    },

    sinceLastDurationText() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const lastMs = Number(this.lastFeedingTimestampMs || 0)
      if (!Number.isFinite(nowMs) || !Number.isFinite(lastMs) || lastMs <= 0) return ''
      if (nowMs <= lastMs) return ''
      return this.formatDurationText(nowMs - lastMs)
    },

    hasNextFeeding() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const nextMs = Number(this.nextFeedingTimestampMs || 0)
      return Number.isFinite(nowMs) && nowMs > 0 && Number.isFinite(nextMs) && nextMs > 0
    },

    // 时间轴上的“下次”点位：若已超时，则贴近“现在”显示（更直观），避免 hollow dot 落在过去造成误读。
    nextFeedingTimelineMs() {
      const nextMs = Number(this.nextFeedingTimestampMs || 0)
      if (!Number.isFinite(nextMs) || nextMs <= 0) return 0
      const nowMs = Number(this.nowTickMs || Date.now())
      if (!Number.isFinite(nowMs) || nowMs <= 0) return nextMs
      if (nextMs < nowMs) return nowMs
      return nextMs
    },

    nextCountdownHMText() {
      if (!this.hasNextFeeding) return '--:--'
      const nowMs = Number(this.nowTickMs || Date.now())
      const nextMs = Number(this.nextFeedingTimestampMs || 0)
      if (!Number.isFinite(nowMs) || !Number.isFinite(nextMs) || nextMs <= 0) return '--:--'
      return this.formatDurationHMText(Math.abs(nextMs - nowMs))
    },

    sinceLastDurationHMText() {
      const nowMs = Number(this.nowTickMs || Date.now())
      const lastMs = Number(this.lastFeedingTimestampMs || 0)
      if (!Number.isFinite(nowMs) || !Number.isFinite(lastMs) || lastMs <= 0) return ''
      if (nowMs <= lastMs) return ''
      return this.formatDurationHMText(nowMs - lastMs)
    },

    homeStatusText() {
      if (this.todayCount <= 0) {
        const lv = String(this.emptyDayLevel || 'unknown')
        if (lv === 'alert') return '今天还没记录（警报）'
        if (lv === 'attention') return '今天还没记录（偏晚）'
        return '今天还没记录'
      }

      const interval = this.getIntervalInsight()
      if (interval?.status === 'overdue') return '该喂奶了'
      if (interval?.status === 'frequent') {
        if (interval.severity === 'severe') return '记录过密'
        return '间隔偏短'
      }
      if (interval?.status === 'sparse') return '间隔偏长'
      if (interval?.status === 'irregular') return '节奏波动'

      const feedingStatus = this.feedingStatusForHome()
      if (feedingStatus === 'low') return '今日偏少'
      if (feedingStatus === 'high') return '今日偏多'
      return '节奏正常'
    },

    // 首页健康信号（强结论 + 单一 CTA）：仅在需要用户立刻决策时出现，避免常驻制造焦虑。
    homeSignalBannerVisible() {
      const lv = String(this.insightLevel || '')
      return lv === 'alert' || lv === 'attention'
    },

    homeSignalTitle() {
      const lv = String(this.insightLevel || '')
      const interval = this.getIntervalInsight()

      if (this.todayCount <= 0) {
        if (lv === 'alert') return '警报：今天还没喂奶'
        if (lv === 'attention') return '提醒：今天还没喂奶'
        return '今天还没喂奶'
      }

      if (interval?.status === 'overdue') {
        return lv === 'alert' ? '警报：该喂奶了' : '提醒：该喂奶了'
      }

      if (interval?.status === 'frequent') {
        if (interval.severity === 'severe') return '警报：记录过密'
        return '提醒：间隔偏短'
      }

      const feedingStatus = this.feedingStatusForHome()
      if (feedingStatus === 'low') return '提醒：今日偏少'
      if (feedingStatus === 'high') return '提醒：今日偏多'
      return this.homeStatusText
    },

    homeSignalDesc() {
      if (!this.homeSignalBannerVisible) return ''

      if (this.todayCount <= 0) {
        const target = Number(this.todayTargetMl || 0)
        const expected = Number(this.expectedNowMl || 0)
        const ref = String(this.recommendedAmount?.age_reference || '').trim()
        const refText = ref ? `参考 ${ref}` : (target > 0 ? `参考 ${target}ml/天` : '')
        if (refText && expected > 0) return `${refText} · 此刻约 ${expected}ml`
        return refText
      }

      const interval = this.getIntervalInsight()
      if (interval?.text) return String(interval.text || '')

      const target = Number(this.todayTargetMl || 0)
      const consumed = Number(this.todayConsumedMl || 0)
      if (target > 0) return `今天 ${consumed}ml / ${target}ml`
      return ''
    },

    homeSignalCtaText() {
      if (!this.homeSignalBannerVisible) return ''
      if (this.todayCount <= 0) return '立即记录'
      const interval = this.getIntervalInsight()
      if (interval?.status === 'overdue') return '现在投喂'
      if (interval?.status === 'frequent' && interval.severity === 'severe') return '检查/撤销'
      return '查看建议'
    },

    homeSignalCtaAction() {
      if (!this.homeSignalBannerVisible) return ''
      if (this.todayCount <= 0) return 'record'
      const interval = this.getIntervalInsight()
      if (interval?.status === 'overdue') return 'record'
      if (interval?.status === 'frequent' && interval.severity === 'severe') return 'today'
      return 'explain'
    },

    // 首页唯一“主动作”：把处理路径收敛到一个按钮上（更线性、更像系统）。
    homePrimaryAction() {
      if (this.homeSignalBannerVisible) {
        const act = String(this.homeSignalCtaAction || '')
        if (act === 'record' || act === 'today' || act === 'explain') return act
      }
      return 'record'
    },

    homePrimaryButtonText() {
      const act = String(this.homePrimaryAction || 'record')
      if (act === 'record') {
        if (this.quickFeeding) return '记录中'
        // 有强信号时，用更明确的动词（立即记录/现在投喂）
        if (this.homeSignalBannerVisible) {
          const t = String(this.homeSignalCtaText || '').trim()
          if (t) return t
        }
        return '投喂'
      }
      if (act === 'today') return '检查/撤销'
      if (act === 'explain') return '查看建议'
      return '投喂'
    },

    homePrimarySubText() {
      const act = String(this.homePrimaryAction || 'record')
      if (act !== 'record') return ''
      if (this.quickFeeding) return ''
      const n = Number(this.nextSuggestedAmount || 0)
      if (!Number.isFinite(n) || n <= 0) return ''
      return `${Math.round(n)}ml`
    },

    nextSuggestedAmount() {
      const base = Number(this.recommendedAmount?.recommended || 0)
      if (!Number.isFinite(base) || base <= 0) return 0
      const delta = this.getSuggestedDelta()
      const v = base + delta
      return Number.isFinite(v) ? v : base
    },

    // 0 次喂奶的“强信号”口径：
    // - 告警阈值跟随用户设置的“白天结束/睡觉时间”，避免固定 18 点造成误报/过早打扰
    // - 在白天结束前 5 小时给一个温和提醒；到白天结束仍为 0 次则红色告警
    emptyDayLevel() {
      if (this.todayCount > 0) return ''
      const standard = Number(this.todayTargetMl || 0)
      if (!Number.isFinite(standard) || standard <= 0) return 'unknown'

      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (Number.isNaN(now.getTime())) return 'unknown'
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime()
      const dayMs = 24 * 60 * 60 * 1000
      const progress = dayMs > 0 ? Math.max(0, Math.min(1, (nowMs - start) / dayMs)) : 0

      const s = this.getFeedingSettingsSnapshot()
      const endHour = Math.max(0, Math.min(23, Number(s.dayEndHour)))
      const alertThreshold = endHour / 24
      const attentionThreshold = Math.max(0, (endHour - 5) / 24)

      if (progress >= alertThreshold) return 'alert'
      if (progress >= attentionThreshold) return 'attention'
      return 'unknown'
    },

    insightLevel() {
      if (this.todayCount <= 0) {
        // 没有任何记录时：早期不制造焦虑；但如果已经到“白天结束/睡觉时间”仍为 0，则给出红色告警。
        return this.emptyDayLevel || 'unknown'
      }

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
      const stage = this.formulaStageBadge
      const scoops = this.railScoopsText
      const parts = []

      const plan = this.weaningPlan || null
      if (plan) {
        const oldName = plan?.old_brand?.name_cn || ''
        const newName = plan?.new_brand?.name_cn || ''
        const label = (oldName || newName) ? `转奶：${oldName || '旧奶粉'}→${newName || '新奶粉'}` : '转奶期'
        parts.push(label)
        if (stage) parts.push(`${stage}段`)
        // 转奶期中勺数可能因旧/新规格不同而变化，这里不常驻展示，避免误导
        return parts.join(' · ')
      }

      const name = this.selectedFormula?.brand?.name_cn || this.selectedFormula?.brand_name || ''
      if (name) parts.push(`奶粉：${name}`)
      if (stage) parts.push(`${stage}段`)
      if (scoops) parts.push(scoops)
      return parts.join(' · ')
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

    todayConsumedPercent() {
      const standard = this.todayTargetMl
      const consumed = this.todayConsumedMl
      if (!standard || standard <= 0) return '0'
      const raw = (consumed / standard) * 100
      const clamped = Math.max(0, Math.min(100, raw))
      return clamped.toFixed(1)
    },

    todayDeltaTone() {
      const standard = this.todayTargetMl
      if (!standard || standard <= 0) return 'ok'
      const delta = this.todayConsumedMl - standard
      if (delta > 0) return 'high'
      if (delta < 0) return 'low'
      return 'ok'
    },

    todayDeltaText() {
      const standard = this.todayTargetMl
      if (!standard || standard <= 0) return ''
      const delta = this.todayConsumedMl - standard
      const abs = Math.abs(delta)
      if (!Number.isFinite(abs) || abs <= 0) return '与参考一致'
      return delta > 0 ? `超出参考 ${abs}ml` : `距参考还差 ${abs}ml`
    },

    amountProgressTone() {
      const s = this.feedingStatusForHome()
      if (s === 'low' || s === 'high') return s
      return 'ok'
    },

    timelineSummaryText() {
      return `${this.todayCount}次 · ${this.stats?.today_amount || 0}ml`
    },

    todayModalSummaryText() {
      return `${this.todayCount}次 · ${this.stats?.today_amount || 0}ml`
    },

    todayStatsMismatch() {
      const n = Number(this.todayCount || 0)
      const amt = Number(this.stats?.today_amount || 0)
      if (!Number.isFinite(n) || !Number.isFinite(amt)) return false
      if (n <= 0 && amt > 0) return true
      if (n > 0 && amt <= 0) return true
      return false
    },

    todayEmptyTitle() {
      if (this.todayStatsMismatch) return '今天列表为空，但统计有数据'
      return '今天还没有记录'
    },

    todayEmptySub() {
      if (this.todayStatsMismatch) return '可能是设备时间/时区不一致；先点上方“刷新数据”，再检查系统时间'
      return '点下方“投喂”开始（误触可撤销）'
    },

    todayFixRows() {
      const rows = []

      if (this.todayStatsMismatch) {
        rows.push({
          key: 'refresh_stats_mismatch',
          tone: 'warn',
          title: '刷新数据',
          desc: '修复“列表为空/统计不一致”等偶发问题',
          actionText: '刷新',
          action: 'refresh_today',
        })
      }

      const interval = this.getIntervalInsight()
      if (!this.undoVisible && interval?.status === 'frequent' && interval.severity === 'severe') {
        const last = Array.isArray(this.recentFeedings) ? this.recentFeedings[0] : null
        if (last && last.id) {
          const can = this.canEditFeeding(last)
          const burst = interval?.detail?.burst_10m
          const c = Number(burst?.count || 0)
          const t = Number(burst?.total_amount || 0)
          const extra = (c >= 2 && t > 0) ? `10分钟内${c}次共${t}ml` : ''
          rows.push({
            key: 'undo_last',
            tone: can ? 'danger' : 'warn',
            title: can ? '可能误触：记录过密，先撤销最近一次' : '记录过密：需要管理员处理',
            desc: extra || '短时间多次记录会影响倒计时/建议',
            actionText: can ? '撤销' : '查看',
            action: can ? 'undo_last' : 'open_today',
          })
        }
      }

      const future = Array.isArray(this.futureFeedings) ? this.futureFeedings : []
      const invalid = Array.isArray(this.invalidTimeFeedings) ? this.invalidTimeFeedings : []

      const maxFixRecords = 6
      for (const f of future.slice(0, maxFixRecords)) {
        const can = this.canEditFeeding(f)
        const ms = this.parseTimeToMs(f?.feeding_time)
        const dt = this.formatMDHMText(ms)
        const amount = Number(f?.amount || 0)
        const amountText = Number.isFinite(amount) && amount > 0 ? `${Math.round(amount)}ml` : '--ml'
        rows.push({
          key: `future_${f.id}`,
          tone: 'warn',
          title: `未来记录：${dt} · ${amountText}`,
          desc: '已自动忽略；请修正时间到“现在或过去”',
          actionText: can ? '修正' : '查看',
          action: can ? 'edit_feeding' : 'view_feeding',
          feeding: f,
        })
      }

      for (const f of invalid.slice(0, Math.max(0, maxFixRecords - future.length))) {
        const can = this.canEditFeeding(f)
        const raw = String(f?.__invalid_time_raw || f?.feeding_time || '').trim()
        const amount = Number(f?.amount || 0)
        const amountText = Number.isFinite(amount) && amount > 0 ? `${Math.round(amount)}ml` : '--ml'
        rows.push({
          key: `invalid_time_${f.id}`,
          tone: 'warn',
          title: `时间异常：${amountText}`,
          desc: raw ? `原始时间：${raw}` : '记录时间无法识别，已忽略',
          actionText: can ? '修正' : '查看',
          action: can ? 'edit_feeding' : 'view_feeding',
          feeding: f,
        })
      }

      return rows.slice(0, 8)
    },

    showFeedingUserName() {
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      return members.length > 1
    },

    latestFeedingLabel() {
      const list = Array.isArray(this.todayFeedings) ? this.todayFeedings : []
      const last = list[0] || null
      if (!last) return ''
      const ms = this.parseTimeToMs(last?.feeding_time)
      if (!Number.isFinite(ms) || ms <= 0) return ''
      const amount = Number(last?.amount || 0)
      const amountText = Number.isFinite(amount) && amount > 0 ? `${Math.round(amount)}ml` : ''
      const t = this.formatClockText(ms)
      if (!t || t === '--:--') return ''
      return amountText ? `${t} · ${amountText}` : t
    },

    // 时间轴：预估“今天后续应喂时间点”（辅助规划睡眠）
    // - 仅在今日已有记录时展示（避免“未记录但已喂”的误判）
    // - 预估点只做视觉辅助，不可点击/不参与统计
    todayPlanTimesMs() {
      const list = Array.isArray(this.todayFeedings) ? this.todayFeedings : []
      if (list.length <= 0) return []

      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (Number.isNaN(now.getTime())) return []
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime()
      const end = start + 24 * 60 * 60 * 1000

      // seed = 时间轴上的“下次喂奶”位置；若已超时则贴近“现在”，后续预估从此开始递推。
      const lastMs = Number(this.lastFeedingTimestampMs || 0)
      let seed = Number(this.nextFeedingTimelineMs || 0)
      if (!Number.isFinite(seed) || seed <= 0) {
        const calc = this.calcNextFeedingTimeMs(nowMs, lastMs)
        seed = Number.isFinite(calc) && calc > 0 ? calc : 0
      }

      if (!Number.isFinite(seed) || seed <= 0) return []
      if (seed < start || seed >= end) return []

      const times = []
      let t = seed
      const maxTimes = 16
      let guard = 0
      while (t < end && guard < maxTimes) {
        times.push(t)
        const next = this.calcNextFeedingTimeMs(t, t)
        if (!Number.isFinite(next) || next <= t) break
        t = next
        guard++
      }

      // 时间轴是 0-24：这里只返回“今天内”的时间点；跨天用首页的“明天/后天”提示即可。
      return times.filter((ms) => Number.isFinite(ms) && ms >= start && ms < end)
    },

    todayPlanFutureTimesMs() {
      const times = Array.isArray(this.todayPlanTimesMs) ? this.todayPlanTimesMs : []
      if (times.length <= 0) return []
      const nowMs = Number(this.nowTickMs || Date.now())
      return times.filter((ms) => Number.isFinite(ms) && ms >= nowMs - 60 * 1000)
    },

    todayPlanNightCount() {
      const future = Array.isArray(this.todayPlanFutureTimesMs) ? this.todayPlanFutureTimesMs : []
      if (future.length <= 0) return 0
      const s = this.getFeedingSettingsSnapshot()
      const dayStart = Number(s.dayStartHour)
      const dayEnd = Number(s.dayEndHour)
      return future.filter((ms) => {
        const d = new Date(ms)
        if (Number.isNaN(d.getTime())) return false
        const h = d.getHours()
        return !(h >= dayStart && h < dayEnd)
      }).length
    },

    timelinePlanFootTitle() {
      const future = Array.isArray(this.todayPlanFutureTimesMs) ? this.todayPlanFutureTimesMs : []
      if (future.length <= 0) return ''
      const nightCount = Number(this.todayPlanNightCount || 0)
      const total = future.length
      if (nightCount > 0) return `今天剩余 ${total} 次 · 夜间 ${nightCount} 次`
      return `今天剩余 ${total} 次`
    },

    timelinePlanFootSub() {
      const future = Array.isArray(this.todayPlanFutureTimesMs) ? this.todayPlanFutureTimesMs : []
      if (future.length <= 0) return ''
      const show = future
        .slice(0, 4)
        .map((ms) => this.formatClockText(ms))
        .filter((t) => t && t !== '--:--')
      if (show.length <= 0) return ''
      const suffix = future.length > show.length ? '…' : ''
      const list = `${show.join('、')}${suffix}`
      return list ? `后续：${list}` : ''
    },

    timelinePlanFootHint() {
      const nightCount = Number(this.todayPlanNightCount || 0)
      if (!Number.isFinite(nightCount) || nightCount <= 0) return ''
      return '想少夜醒：去调整白天结束/夜间间隔'
    },

    timelinePlanFootFocus() {
      // 线性体验：从“夜间次数”直接定位到最相关的设置（时间段）
      const nightCount = Number(this.todayPlanNightCount || 0)
      if (Number.isFinite(nightCount) && nightCount > 0) return 'time'
      return ''
    },

    todayPlanTimelineMarks() {
      const times = Array.isArray(this.todayPlanTimesMs) ? this.todayPlanTimesMs : []
      // 预估点不包含“下次喂奶”（已用 hollow dot 表示），避免重叠误读
      if (times.length <= 1) return []

      const nowMs = Number(this.nowTickMs || Date.now())
      const now = new Date(nowMs)
      if (Number.isNaN(now.getTime())) return []
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime()
      const end = start + 24 * 60 * 60 * 1000

      const marks = []
      for (const t of times.slice(1)) {
        if (t < nowMs - 60 * 1000) continue
        if (!Number.isFinite(t) || t < start || t >= end) continue
        const d = new Date(t)
        if (Number.isNaN(d.getTime())) continue
        const minutes = d.getHours() * 60 + d.getMinutes()
        const leftPercent = Math.max(0, Math.min(100, (Number(minutes) / 1440) * 100))
        marks.push({
          key: `p-${t}`,
          kind: 'plan',
          leftPercent: leftPercent.toFixed(2),
        })
      }

      return marks
    },

    homeTimelineMarks() {
      const real = Array.isArray(this.todayTimelineMarks) ? this.todayTimelineMarks : []
      const plan = Array.isArray(this.todayPlanTimelineMarks) ? this.todayPlanTimelineMarks : []
      return plan.length ? real.concat(plan) : real
    },

    todayTimelineMarks() {
      const list = Array.isArray(this.todayFeedings) ? this.todayFeedings : []
      if (list.length <= 0) return []

      const showUser = Array.isArray(this.familyMembers) && this.familyMembers.length > 1

      // 以“分钟”为粒度：更贴近真实分布；同一分钟多次记录用 badge 聚合，气泡里展示多行。
      const buckets = new Map()
      let latestMs = 0
      for (const f of list) {
        const ms = this.parseTimeToMs(f?.feeding_time)
        if (!Number.isFinite(ms) || ms <= 0) continue
        if (ms > latestMs) latestMs = ms
        const d = new Date(ms)
        if (Number.isNaN(d.getTime())) continue
        const minutes = d.getHours() * 60 + d.getMinutes()
        const arr = buckets.get(minutes) || []
        arr.push({ feeding: f, ms })
        buckets.set(minutes, arr)
      }

      const marks = []
      const sortedBuckets = Array.from(buckets.keys()).sort((a, b) => a - b)
      for (const minutes of sortedBuckets) {
        const arr = (buckets.get(minutes) || []).sort((x, y) => x.ms - y.ms)
        if (arr.length <= 0) continue
        const leftPercent = Math.max(0, Math.min(100, (Number(minutes) / 1440) * 100))
        const isLatest = arr.some((it) => it?.ms === latestMs)

        const items = arr.map((it, idx) => {
          const f = it.feeding || {}
          const amount = Number(f.amount || 0)
          const timeText = this.formatClockText(it.ms)
          const amountText = `${Number.isFinite(amount) ? Math.round(amount) : 0}ml`
          const userText = showUser ? (this.resolveMemberName(f.user_id) || '') : ''
          const tagText = this.weaningTagTextForFeeding(f) || ''
          return {
            key: f?.id ? String(f.id) : `${minutes}-${idx}`,
            timeText,
            amountText,
            userText,
            tagText,
          }
        })

        marks.push({
          key: `m-${minutes}`,
          leftPercent: leftPercent.toFixed(2),
          count: items.length,
          items,
          isLatest,
        })
      }

      return marks
    },

    undoFeedingAmount() {
      const n = Number(this.undoFeeding?.amount || 0)
      return Number.isFinite(n) ? n : 0
    },

    undoTone() {
      const t = String(this.undoMeta?.tone || 'ok')
      return t === 'warn' || t === 'danger' ? t : 'ok'
    },

    undoIconText() {
      const t = this.undoTone
      if (t === 'danger') return '!'
      if (t === 'warn') return '!'
      return '✓'
    },

    undoTitleText() {
      const title = String(this.undoMeta?.title || '').trim()
      if (title) return title
      const n = this.undoFeedingAmount
      return n > 0 ? `已记录 ${n}ml` : '已记录'
    },

    undoSubText() {
      const sub = String(this.undoMeta?.sub || '').trim()
      return sub || ''
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

    detailDateText() {
      const s = String(this.detailDate || '').trim()
      if (!s) return '--'
      const m = s.match(/^(\\d{4})-(\\d{2})-(\\d{2})$/)
      if (!m) return s
      const y = Number(m[1])
      const mo = Number(m[2])
      const da = Number(m[3])
      if (![y, mo, da].every((x) => Number.isFinite(x))) return s
      const now = new Date()
      if (y !== now.getFullYear()) return `${y}年${mo}月${da}日`
      return `${mo}月${da}日`
    },

    detailClockText() {
      const s = String(this.detailClock || '').trim()
      if (!s) return '--:--'
      const m = s.match(/^(\\d{1,2}):(\\d{1,2})$/)
      if (!m) return s
      const hh = String(Math.max(0, Math.min(23, Number(m[1])))).padStart(2, '0')
      const mm = String(Math.max(0, Math.min(59, Number(m[2])))).padStart(2, '0')
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
      const ml = Number(this.effectiveCurrentScoopMl || 0)
      const amount = Number(this.recommendedAmount?.recommended || 0)
      if (!ml || ml <= 0 || !amount || amount <= 0) return ''
      const raw = amount / ml
      const rounded = Math.round(raw * 2) / 2
      return `${rounded}勺/次`
    },

    suggestScoopsText() {
      const amount = Number(this.nextSuggestedAmount || 0)
      if (!Number.isFinite(amount) || amount <= 0) return ''
      const t = this.formatScoopsForAmount(amount)
      return t ? `约 ${t}` : ''
    },

    canShowScoopHint() {
      // 仅在“已绑定奶粉但缺少勺数换算”时提示补充入口（放在二级说明 Sheet，避免首页噪音）。
      const hasFormula = !!(this.selectedFormula && this.selectedFormula.brand_id)
      if (!hasFormula) return false
      return Number(this.effectiveCurrentScoopMl || 0) <= 0
    },

    // 首页轻量引导（Setup Nudge）：只显示“下一步最短路径”中的一条，且可关闭。
    setupNudge() {
      const babyId = this.currentBaby?.id
      if (!babyId) return null

      const dismissed = new Set((Array.isArray(this.dismissedNudgeKeys) ? this.dismissedNudgeKeys : []).map(String))
      const items = []

      // 1) 先把“提醒”打开（否则用户会以为产品不工作）
      const fs = this.feedingSettings || null
      if (fs && fs.reminder_enabled === false) {
        items.push({
          key: 'reminder_on',
          tone: 'info',
          icon: '!',
          title: '开启提醒',
          desc: '到点会提示你下次喂奶（应用内）',
          actionText: '去开启',
          action: 'feeding_settings',
          focus: 'reminder',
        })
      }

      // 2) 系统通知：退到后台也能弹（受浏览器/系统限制）
      const reminderOn = !fs || fs.reminder_enabled !== false
      if (reminderOn && isNotificationSupported()) {
        const perm = String(getNotificationPermission() || 'default')
        const enabled = !!getSystemNotifyEnabled()
        const effective = enabled && perm === 'granted'
        if (!effective) {
          const ios = this.isIOSPlatform()
          const standalone = isStandalonePwa()
          if (perm === 'denied') {
            items.push({
              key: 'system_notify',
              tone: 'warn',
              icon: '!',
              title: '通知权限已关闭',
              desc: '需要在系统/浏览器的站点设置里重新允许',
              actionText: '查看',
              action: 'help_notify',
            })
          } else if (ios && !standalone) {
            items.push({
              key: 'system_notify',
              tone: 'info',
              icon: 'i',
              title: '后台提醒更稳定',
              desc: 'iPhone 通常需先“添加到主屏幕”再开启系统通知',
              actionText: '查看',
              action: 'help_notify',
            })
          } else {
            items.push({
              key: 'system_notify',
              tone: 'info',
              icon: 'i',
              title: '允许系统通知',
              desc: '退到后台也能提醒你',
              actionText: '去开启',
              action: 'feeding_settings',
              focus: 'notify',
            })
          }
        }
      }

      // 2.5) 转奶期提醒：检测到“已切换到新奶粉”但未开启转奶计划时，给出线性入口
      // 说明：此提醒优先级高于“勺数换算/偏好”，因为它影响后续每次投喂与记录的口径。
      const ws = this.weaningSuggestion
      if (ws && ws.oldBrandId && ws.newBrandId && !this.hasWeaningPlan) {
        if (this.isBabyAdmin) {
          items.push({
            key: ws.key,
            tone: 'warn',
            icon: '!',
            title: '建议开启转奶期',
            desc: '已检测到切换奶粉；7天交替喂次（不混合），更稳妥',
            actionText: '开始',
            action: 'start_weaning',
          })
        } else {
          items.push({
            key: ws.key,
            tone: 'warn',
            icon: '!',
            title: '建议开启转奶期',
            desc: '需要管理员确认后才能开启',
            actionText: '家庭共享',
            action: 'family',
          })
        }
      }

      // 2.55) 生长数据：身高/体重用于更准确的参考奶量与健康信号（缺失时先给一个轻提示）
      const cw = Number(this.currentBaby?.current_weight || 0)
      const ch = Number(this.currentBaby?.current_height || 0)
      const missingGrowth = !(Number.isFinite(cw) && cw > 0 && Number.isFinite(ch) && ch > 0)
      if (missingGrowth) {
        if (this.isBabyAdmin) {
          items.push({
            key: 'growth_fill',
            tone: 'info',
            icon: 'i',
            title: '补充身高体重',
            desc: '用于更准确的参考奶量与健康信号',
            actionText: '去填写',
            action: 'baby_info',
          })
        } else {
          items.push({
            key: 'growth_fill',
            tone: 'info',
            icon: 'i',
            title: '补充身高体重',
            desc: '需要管理员补充后，参考会更准确',
            actionText: '家庭共享',
            action: 'family',
          })
        }
      }

      // 2.6) 换段提醒：按月龄推算段数（以包装为准），提前提醒避免临时手忙脚乱
      const stage = Number(this.currentFormulaStage || 0)
      const soon = this.stageBoundarySoon
      if (this.selectedFormula?.brand_id) {
        if (!stage) {
          items.push({
            key: 'formula_stage',
            tone: 'info',
            icon: 'i',
            title: '补充奶粉段数',
            desc: '用于换段提醒（以包装为准）',
            actionText: '去设置',
            action: 'formula_select',
          })
        } else if (soon && stage === Number(soon.nextStage || 0) - 1) {
          const d = Number(soon.diffDays || 0)
          const desc = Number.isFinite(d) && d > 0
            ? `还有${d}天到${soon.boundaryMonths}个月（以包装为准）`
            : `已到${soon.boundaryMonths}个月（以包装为准）`
          items.push({
            key: `stage_soon_${soon.nextStage}`,
            tone: 'info',
            icon: 'i',
            title: `准备换到${soon.nextStage}段？`,
            desc,
            actionText: '去设置',
            action: 'formula_select',
          })
        } else {
          const rec = Number(this.recommendedStageByAge || 0)
          if (rec && stage && rec !== stage) {
            items.push({
              key: `stage_check_${stage}_${rec}`,
              tone: 'warn',
              icon: '!',
              title: '段数可能不匹配',
              desc: `宝宝已${this.babyAgeText}，按月龄通常用${rec}段（以包装为准）`,
              actionText: '去设置',
              action: 'formula_select',
            })
          }
        }
      }

      // 3) 已绑定但缺“勺数换算”：把入口提前到首页（仍然很轻）
      if (this.canShowScoopHint) {
        items.push({
          key: 'scoop_hint',
          tone: 'info',
          icon: 'i',
          title: '补充勺数换算',
          desc: '用于显示“约几勺”与更准确记录',
          actionText: '去补充',
          action: 'formula_spec',
        })
      }

      // 4) 绑定奶粉（可选）：让“勺数/冲泡要求”更完整
      if (!(this.selectedFormula && this.selectedFormula.brand_id)) {
        items.push({
          key: 'pick_formula',
          tone: 'info',
          icon: 'i',
          title: '选择奶粉（可选）',
          desc: '显示段数、冲泡要求与勺数换算',
          actionText: '去选择',
          action: 'formula_select',
        })
      }

      // 5) 投喂偏好：微调推荐量（低风险、可随时改）
      if (!this.userPreference) {
        items.push({
          key: 'preference',
          tone: 'info',
          icon: 'i',
          title: '设置投喂偏好',
          desc: '让推荐量更贴合你们的习惯',
          actionText: '去设置',
          action: 'preference',
        })
      }

      const next = items.find((it) => it && it.key && !dismissed.has(String(it.key)))
      return next || null
    },
  },
  
  onLoad() {
    const userStore = useUserStore()
    if (!userStore.token) {
      // H5 可能出现“直接打开首页路由”的情况；未登录时不发起受保护请求，直接回登录页。
      try {
        const msg = uni.getStorageSync('nb_auth_notice')
        if (!msg) uni.setStorageSync('nb_auth_notice', '请先登录')
      } catch {}
      uni.reLaunch({ url: '/pages/login/index' })
      return
    }
    this.onNbRetry()
    this.startCountdown()
  },

  async onShow() {
    const userStore = useUserStore()
    if (!userStore.token) {
      try {
        const msg = uni.getStorageSync('nb_auth_notice')
        if (!msg) uni.setStorageSync('nb_auth_notice', '请先登录')
      } catch {}
      uni.reLaunch({ url: '/pages/login/index' })
      return
    }

    // 首次进入由 onLoad 拉取；后续从设置/详情返回时再刷新，确保口径一致
    if (!this.hasLoaded) {
      this.hasLoaded = true
      return
    }
    const baby = userStore.currentBaby || null
    if (baby?.id && String(baby.id) !== String(this.currentBaby?.id || '')) {
      this.currentBaby = baby
      this.syncDismissedHomeNudges()
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
	      this.loadWeaningPlan(),
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
    if (this.timelineSelectTimer) {
      clearTimeout(this.timelineSelectTimer)
      this.timelineSelectTimer = null
    }
    this.closeWs()
  },
  
  methods: {
    async onNbRetry() {
      if (this.pageLoading) return
      this.pageLoading = true
      this.errorText = ''
      try {
        await this.loadData({ critical: true })
      } catch (e) {
        this.errorText = e?.message || '加载失败'
      } finally {
        this.pageLoading = false
      }
    },

    // -------- Setup Nudge（按 baby 维度记忆已关闭的提示项）--------
    getHomeNudgeStorageKey(babyId) {
      const id = String(babyId || this.currentBaby?.id || '').trim()
      if (!id) return ''
      return `nb_home_nudge_dismissed_v1:${id}`
    },

    syncDismissedHomeNudges() {
      const babyId = this.currentBaby?.id
      const key = this.getHomeNudgeStorageKey(babyId)
      if (!key) {
        this.dismissedNudgeKeys = []
        return
      }
      let raw = ''
      try {
        raw = uni.getStorageSync(key)
      } catch {
        raw = ''
      }
      let arr = []
      if (Array.isArray(raw)) {
        arr = raw
      } else if (typeof raw === 'string' && raw.trim()) {
        try {
          const parsed = JSON.parse(raw)
          if (Array.isArray(parsed)) arr = parsed
        } catch {
          arr = raw.split(',')
        }
      }
      const next = Array.from(new Set(arr.map((x) => String(x || '').trim()).filter(Boolean)))
      this.dismissedNudgeKeys = next
    },

    persistDismissedHomeNudges() {
      const babyId = this.currentBaby?.id
      const key = this.getHomeNudgeStorageKey(babyId)
      if (!key) return
      const arr = Array.isArray(this.dismissedNudgeKeys) ? this.dismissedNudgeKeys : []
      try {
        uni.setStorageSync(key, JSON.stringify(arr))
      } catch {}
    },

    dismissSetupNudge(key) {
      const k = String(key || '').trim()
      if (!k) return
      const set = new Set((Array.isArray(this.dismissedNudgeKeys) ? this.dismissedNudgeKeys : []).map(String))
      set.add(k)
      this.dismissedNudgeKeys = Array.from(set)
      this.persistDismissedHomeNudges()
    },

    handleSetupNudgeTap(nudge) {
      const n = nudge || {}
      const action = String(n.action || '')
      if (action === 'start_weaning') {
        this.startSuggestedWeaningPlan()
        return
      }
      if (action === 'family') {
        this.goFamily()
        return
      }
      if (action === 'feeding_settings') {
        this.goToFeedingSettings(n.focus)
        return
      }
      if (action === 'baby_info') {
        this.goToBabyInfo()
        return
      }
      if (action === 'formula_select') {
        this.goToFormulaSelect()
        return
      }
      if (action === 'formula_spec') {
        this.goToFormulaSpec()
        return
      }
      if (action === 'preference') {
        this.goToPreference()
        return
      }
      if (action === 'help_notify') {
        this.goToHelp('notify')
        return
      }
    },

    isIOSPlatform() {
      try {
        const sys = uni.getSystemInfoSync()
        const p = String(sys?.platform || sys?.osName || '').toLowerCase()
        return p.includes('ios') || p.includes('iphone') || p.includes('ipad')
      } catch {
        return false
      }
    },

    goToFeedingSettings(focus) {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      const f = String(focus || '').trim()
      const q = f ? `&focus=${encodeURIComponent(f)}` : ''
      uni.navigateTo({ url: `/pages/feeding-settings/index?babyId=${babyId}${q}` })
    },

    goToFormulaSelect() {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      uni.navigateTo({ url: `/pages/formula-select/index?babyId=${babyId}` })
    },

    goToPreference() {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      uni.navigateTo({ url: `/pages/preference/index?babyId=${babyId}` })
    },

    goToHelp(topic) {
      const t = String(topic || '').trim()
      const q = t ? `?topic=${encodeURIComponent(t)}` : ''
      uni.navigateTo({ url: `/pages/help/index${q}` })
    },

    goFamily() {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      uni.navigateTo({ url: `/pages/family/index?babyId=${encodeURIComponent(String(babyId))}` })
    },

    async startSuggestedWeaningPlan() {
      const babyId = this.currentBaby?.id
      const ws = this.weaningSuggestion
      if (!babyId || !ws || !ws.oldBrandId || !ws.newBrandId) {
        uni.showToast({ title: '未检测到可开启的转奶场景', icon: 'none' })
        return
      }

      if (!this.isBabyAdmin) {
        uni.showToast({ title: '仅管理员可开启转奶期', icon: 'none' })
        return
      }

      const ok = await this.openConfirmSheet({
        title: '开始 7 天转奶期？',
        desc: '按“旧奶粉 ↔ 新奶粉”交替喂次（不混合）。\n如宝宝出现明显不适，请暂停并咨询医生。',
        cancelText: '暂不',
        confirmText: '开始',
        variant: 'primary',
      })
      if (!ok) return

      try {
        await api.post(`/babies/${babyId}/weaning-plan`, {
          mode: 'alternate',
          duration_days: 7,
          old_brand_id: ws.oldBrandId,
          old_series_name: String(ws.oldSeriesName || ''),
          old_age_range: '',
          new_brand_id: ws.newBrandId,
          new_series_name: String(ws.newSeriesName || ''),
          new_age_range: String(ws.newAgeRange || ''),
        })

        // 立刻刷新：首页投喂将自动按“旧/新”切换
        await this.loadWeaningPlan()
        this.dismissSetupNudge(ws.key)
        uni.showToast({ title: '已开启转奶期', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e?.message || '开启转奶期失败', icon: 'none' })
      }
    },

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

    formatMDHMText(ms) {
      if (!Number.isFinite(ms) || ms <= 0) return '--.-- --:--'
      const d = new Date(ms)
      if (Number.isNaN(d.getTime())) return '--.-- --:--'
      const mo = String(d.getMonth() + 1).padStart(2, '0')
      const da = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${mo}.${da} ${hh}:${mm}`
    },

	    formatDayLabel(targetMs, nowMs) {
	      if (!Number.isFinite(targetMs) || !Number.isFinite(nowMs)) return ''
	      const t = new Date(targetMs)
	      const n = new Date(nowMs)
	      if (Number.isNaN(t.getTime()) || Number.isNaN(n.getTime())) return ''
	      const tUTC = Date.UTC(t.getFullYear(), t.getMonth(), t.getDate())
	      const nUTC = Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())
	      const diffDays = Math.round((tUTC - nUTC) / 86400000)
	      // iOS 风格信息减法：今天不重复显示“今天”，仅在跨天时提示“明天/后天”。
	      if (diffDays === 0) return ''
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

    formatDurationHMText(ms) {
      const sec = Math.max(0, Math.floor(Number(ms || 0) / 1000))
      if (!Number.isFinite(sec)) return '--:--'
      const totalMin = Math.floor(sec / 60)
      const hours = Math.floor(totalMin / 60)
      const minutes = totalMin % 60
      const hh = String(hours).padStart(2, '0')
      const mm = String(minutes).padStart(2, '0')
      return `${hh}:${mm}`
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
      // 转奶期进行中：勺数按“本次建议的旧/新奶粉规格”计算，缺失字段用本机补充兜底。
      let formula = this.selectedFormula || null
      let official = this.formulaSpec || null
      if (this.weaningAutoEnabled && this.weaningPlan) {
        const plan = this.weaningPlan
        const side = this.weaningAutoSide
        if (side === 'old') {
          formula = { brand_id: plan.old_brand_id, series_name: plan.old_series_name || '', age_range: plan.old_age_range || '' }
          official = this.weaningOldSpec || null
        } else if (side === 'new') {
          formula = { brand_id: plan.new_brand_id, series_name: plan.new_series_name || '', age_range: plan.new_age_range || '' }
          official = this.weaningNewSpec || this.formulaSpec || null
        }
      }
      const spec = this.getEffectiveSpecForFormula(formula, official)
      const ml = Number(spec?.scoop_ml || 0)
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

    async loadData(opts = {}) {
      const critical = !!opts.critical
      const userStore = useUserStore()
      this.currentBaby = userStore.currentBaby || {}
      this.syncDismissedHomeNudges()

      // 兜底：若本地未选择宝宝，但账号下已有宝宝，则自动选择第一个（降低首次登录/换设备成本）
      if (!this.currentBaby.id) {
        try {
          const res = await api.get('/babies')
          const first = Array.isArray(res.babies) ? res.babies[0] : null
          if (first && first.id) {
            this.currentBaby = first
            userStore.setCurrentBaby(first)
            this.syncDismissedHomeNudges()
          }
        } catch (e) {
          if (critical) throw e
        }
      }
      
      if (!this.currentBaby.id) {
        return
      }
      
	      await Promise.all([
	        this.loadFeedings({ critical }),
	        this.loadStats({ critical }),
	        this.loadGrowthStats(),
	        this.loadFamilyMembers(),
	        this.loadFeedingSettings(),
	        this.loadSelectedFormula(),
	        this.loadFormulaSpec(),
	        this.loadWeaningPlan(),
	      ])

      this.connectWs()
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
        const res = await api.get(`/babies/${this.currentBaby.id}/formula`, {}, { silent: true })
        this.selectedFormula = res?.selection || null
        this.loadCustomFormulaSpec()
      } catch {
        this.selectedFormula = null
        this.loadCustomFormulaSpec()
      }
    },

    async loadFormulaSpec() {
      try {
        const res = await api.get(`/babies/${this.currentBaby.id}/formula/specification`, {}, { silent: true })
        this.formulaSpec = res?.specification || null
      } catch {
        this.formulaSpec = null
      }
    },

    buildCustomSpecKeyForFormula(formula) {
      const babyId = this.currentBaby?.id
      const f = formula || null
      if (!babyId || !f?.brand_id) return ''
      return buildCustomFormulaSpecKey({
        babyId,
        brandId: f.brand_id,
        seriesName: f.series_name || '',
        ageRange: f.age_range || '',
      })
    },

    loadCustomFormulaSpec() {
      const key = this.buildCustomSpecKeyForFormula(this.selectedFormula || null)
      this.customFormulaSpecKey = key
      this.customFormulaSpec = key ? readCustomFormulaSpec(key) : null
    },

    loadCustomWeaningSpecs() {
      const plan = this.weaningPlan || null
      if (!plan) {
        this.customWeaningOldKey = ''
        this.customWeaningNewKey = ''
        this.customWeaningOldSpec = null
        this.customWeaningNewSpec = null
        return
      }
      const oldFormula = { brand_id: plan.old_brand_id, series_name: plan.old_series_name || '', age_range: plan.old_age_range || '' }
      const newFormula = { brand_id: plan.new_brand_id, series_name: plan.new_series_name || '', age_range: plan.new_age_range || '' }

      const oldKey = this.buildCustomSpecKeyForFormula(oldFormula)
      const newKey = this.buildCustomSpecKeyForFormula(newFormula)
      this.customWeaningOldKey = oldKey
      this.customWeaningNewKey = newKey
      this.customWeaningOldSpec = oldKey ? readCustomFormulaSpec(oldKey) : null
      this.customWeaningNewSpec = newKey ? readCustomFormulaSpec(newKey) : null
    },

    getCustomSpecForFormula(formula) {
      const key = this.buildCustomSpecKeyForFormula(formula)
      if (!key) return null
      if (key === this.customFormulaSpecKey) return this.customFormulaSpec
      if (key === this.customWeaningOldKey) return this.customWeaningOldSpec
      if (key === this.customWeaningNewKey) return this.customWeaningNewSpec
      // 兜底：极少数场景（不应在每秒 tick 中触发）。保持接口完整性。
      return readCustomFormulaSpec(key)
    },

    getEffectiveSpecForFormula(formula, officialSpec) {
      const custom = this.getCustomSpecForFormula(formula)
      return applyCustomSpecIfMissing(officialSpec, custom).spec || officialSpec || custom || null
    },

    async loadWeaningPlan() {
      try {
        const babyId = this.currentBaby?.id
        if (!babyId) {
          this.weaningPlan = null
          this.weaningOldSpec = null
          this.weaningNewSpec = null
          return
        }
        const res = await api.get(`/babies/${babyId}/weaning-plan`, {}, { silent: true })
        this.weaningPlan = res?.plan || null
      } catch {
        this.weaningPlan = null
      } finally {
        // best-effort: prefetch specs so the “投喂”按钮可自动带勺数
        this.loadWeaningSpecs()
        this.loadCustomWeaningSpecs()
      }
    },

    async loadWeaningSpecs() {
      const plan = this.weaningPlan || null
      if (!plan) {
        this.weaningOldSpec = null
        this.weaningNewSpec = null
        return
      }

      const oldId = Number(plan.old_brand_id || 0)
      const newId = Number(plan.new_brand_id || 0)
      const curBrandId = Number(this.selectedFormula?.brand_id || 0)

      const tasks = []
      // old spec: always fetch (may differ from current selection)
      tasks.push(this.fetchBrandSpec(oldId, plan.old_series_name, plan.old_age_range).catch(() => null))

      // new spec: prefer current spec if matches current selection; else fetch
      if (newId && curBrandId && newId === curBrandId) {
        tasks.push(Promise.resolve(this.formulaSpec || null))
      } else {
        tasks.push(this.fetchBrandSpec(newId, plan.new_series_name, plan.new_age_range).catch(() => null))
      }

      const [oldSpec, newSpec] = await Promise.all(tasks)
      this.weaningOldSpec = oldSpec || null
      this.weaningNewSpec = newSpec || null
    },

    async fetchBrandSpec(brandId, seriesName, ageRange) {
      const bid = Number(brandId || 0)
      if (!bid) return null
      const res = await api.get('/formula/specifications', { brand_id: bid }, { silent: true })
      const list = Array.isArray(res.specifications) ? res.specifications : []
      if (list.length <= 0) return null

      const series = String(seriesName || '').trim()
      const range = String(ageRange || '').trim()
      if (series || range) {
        const hit = list.find((s) => {
          const sSeries = String(s?.series_name || '').trim()
          const sRange = String(s?.age_range || '').trim()
          if (series && sSeries !== series) return false
          if (range && sRange !== range) return false
          return true
        })
        if (hit) return hit
      }
      return list[0]
    },

    connectWs() {
      // WebSocket：尽量使用“API Base URL”的 origin（dev: 同源 + vite 反代；prod: api.naibao.me）
      this.closeWs()

      const babyId = this.currentBaby?.id
      const token = uni.getStorageSync('token')
      if (!babyId || !token) return

      let origin = 'http://127.0.0.1:8080'
      try {
        const base = String(config?.baseURL || '').trim()
        if (base) origin = base
      } catch {}
      // api.js 会在 baseURL 后追加 /api；这里要取真正 origin
      origin = origin.replace(/\/api\/?$/, '')
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
        await Promise.all([this.loadFeedings(), this.loadStats(), this.loadWeaningPlan()])
      }, 300)
    },

    async loadFeedings(opts = {}) {
      const critical = !!opts.critical
      try {
        const res = await api.get('/feedings', {
          baby_id: this.currentBaby.id
        })
        const rawList = Array.isArray(res.feedings) ? res.feedings : []
        // 兜底：忽略“未来记录”（常见于设备时间错误/脚本误传），否则会把倒计时推到十几个小时。
        // 但“忽略”不等于“看不见”：把未来/异常时间记录单独收集出来，提供修复入口。
        const nowMs = Date.now()
        const graceMs = 2 * 60 * 1000
        const list = []
        const future = []
        const invalid = []
        for (const f of rawList) {
          const ms = this.parseTimeToMs(f?.feeding_time)
          if (!Number.isFinite(ms) || ms <= 0) {
            invalid.push({ ...f, __invalid_time_raw: String(f?.feeding_time || '') })
            continue
          }
          if (ms > nowMs + graceMs) {
            future.push(f)
            continue
          }
          list.push(f)
        }
        this.futureFeedings = future.slice(0, 30)
        this.invalidTimeFeedings = invalid.slice(0, 30)
        this.feedingsMeta = {
          rawCount: rawList.length,
          validCount: list.length,
          futureCount: future.length,
          invalidTimeCount: invalid.length,
        }
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
        if (critical) throw error
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
    
    async loadStats(opts = {}) {
      const critical = !!opts.critical
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
        if (critical) throw error
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
	
	        // 转奶期：若进行中，则本次投喂按“旧/新”自动切换（不做同次混合，降低误差与风险）
	        const plan = this.weaningPlan || null
	        let formula = this.selectedFormula || null
	        let spec = this.formulaSpec || null
	        if (this.weaningAutoEnabled && plan) {
	          const side = this.weaningAutoSide
	          if (side === 'old') {
	            formula = {
	              brand_id: plan.old_brand_id,
	              series_name: plan.old_series_name || '',
	              age_range: plan.old_age_range || '',
	            }
	            spec = this.weaningOldSpec || null
	          } else if (side === 'new') {
	            formula = {
	              brand_id: plan.new_brand_id,
	              series_name: plan.new_series_name || '',
	              age_range: plan.new_age_range || '',
	            }
	            spec = this.weaningNewSpec || this.formulaSpec || null
	          }
	        }

	        if (formula?.brand_id) payload.formula_brand_id = formula.brand_id
	        if (formula?.series_name) payload.formula_series_name = formula.series_name
	        if (inputMethod) payload.input_method = inputMethod
	
	        // 记录时把“勺数”也存下来，便于回看/家庭协作交接（规格缺失则跳过）
	        const effSpec = this.getEffectiveSpecForFormula(formula, spec)
	        const scoopMl = Number(effSpec?.scoop_ml || 0)
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
          const meta = this.buildUndoMeta(res.feeding)
          this.showUndo(res.feeding, meta)
        }
      } catch (error) {
        uni.showToast({ title: error.message || '记录失败', icon: 'none' })
      }
    },

	    confirmLargeAmount(amount) {
	      const n = Number(amount || 0)
	      return this.openConfirmSheet({
	        title: '确认奶量',
	        desc: `单次奶量通常不建议超过200ml，你输入的是 ${n}ml。\n确定记录吗？`,
	        cancelText: '返回修改',
	        confirmText: '确定记录',
	        variant: 'primary',
	      })
	    },

	    confirmRapidFeedingIfNeeded(amount) {
	      const lastMs = Number(this.lastFeedingTimestampMs || 0)
	      if (!Number.isFinite(lastMs) || lastMs <= 0) return Promise.resolve(true)

      const nowMs = Date.now()
      const diffMs = Math.max(0, nowMs - lastMs)

      const burst10 = this.getFeedingBurstSummary(10 * 60 * 1000)
      const diffText = this.formatDurationText(diffMs)
      const n = Number(amount || 0)
      const amountText = Number.isFinite(n) && n > 0 ? `${n}ml` : ''

      // 信息减法：只在“明显不合理”的间隔上打断用户（其余情况用记录后的“智能撤销条”温和提醒）
      const severe = diffMs <= 2 * 60 * 1000 || (burst10.count >= 2 && diffMs <= 5 * 60 * 1000)
      if (!severe) return Promise.resolve(true)

      const title = diffMs <= 2 * 60 * 1000 ? '可能误触' : '间隔很短'
      const extra = (burst10.count >= 2 && burst10.total_amount > 0)
        ? `（10分钟内${burst10.count}次共${burst10.total_amount}ml）`
        : ''

      const content = `距离上次仅 ${diffText}${extra ? ` ${extra}` : ''}。\n通常不建议这么频繁。你仍可继续记录；记录后也可点“撤销”撤回。${amountText ? `\n本次：${amountText}` : ''}`

	      return this.openConfirmSheet({
	        title,
	        desc: content,
	        cancelText: '先去核对',
	        confirmText: '继续记录',
	        variant: 'primary',
	      }).then((ok) => {
	        if (!ok) this.openTodayModal()
	        return ok
	      })
	    },

    openDetail(feeding) {
      this.undoVisible = false
      this.showTodayModal = false
      this.detailFeeding = feeding
      this.detailAmount = String(feeding?.amount ?? '')
      const ms = this.parseTimeToMs(feeding?.feeding_time)
      const d = Number.isFinite(ms) && ms > 0 ? new Date(ms) : new Date()
      const y = d.getFullYear()
      const mo = String(d.getMonth() + 1).padStart(2, '0')
      const da = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      this.detailDate = `${y}-${mo}-${da}`
      this.detailClock = `${hh}:${mm}`
      this.detailOriginalMs = Number.isFinite(ms) && ms > 0 ? ms : null
      this.detailSaving = false
      this.showDetailModal = true
    },

    closeDetailModal() {
      this.showDetailModal = false
      this.detailFeeding = null
      this.detailAmount = ''
      this.detailDate = ''
      this.detailClock = ''
      this.detailOriginalMs = null
      this.detailSaving = false
    },

    onDetailDateChange(e) {
      const v = e?.detail?.value
      if (!v) return
      this.detailDate = String(v)
    },

    onDetailTimeChange(e) {
      const v = e?.detail?.value
      if (!v) return
      this.detailClock = String(v)
    },

    buildDetailFeedingTime() {
      const ymd = String(this.detailDate || '').trim()
      const hm = String(this.detailClock || '').trim()
      const m1 = ymd.match(/^(\\d{4})-(\\d{2})-(\\d{2})$/)
      const m2 = hm.match(/^(\\d{1,2}):(\\d{1,2})$/)
      if (!m1 || !m2) return { ms: null, iso: '' }

      const y = Number(m1[1])
      const mo = Number(m1[2])
      const da = Number(m1[3])
      const hh = Number(m2[1])
      const mm = Number(m2[2])
      if (![y, mo, da, hh, mm].every((x) => Number.isFinite(x))) return { ms: null, iso: '' }

      const d = new Date(y, mo - 1, da, hh, mm, 0, 0)
      const ms = d.getTime()
      if (!Number.isFinite(ms)) return { ms: null, iso: '' }
      return { ms, iso: d.toISOString() }
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
        const payload = { amount: n }
        const t = this.buildDetailFeedingTime()
        if (t && t.iso && Number.isFinite(t.ms)) {
          // 与后端口径一致：不允许“未来喂奶时间”（允许 2 分钟误差）
          if (t.ms > Date.now() + 2 * 60 * 1000) {
            uni.showToast({ title: '时间不能在未来', icon: 'none' })
            return
          }

          const prev = Number(this.detailOriginalMs || 0)
          const sameMinute = prev > 0 && Math.floor(prev / 60000) === Math.floor(t.ms / 60000)
          if (!sameMinute) payload.feeding_time = t.iso
        }

        await api.put(`/feedings/${feeding.id}`, payload)
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

	    async deleteDetail() {
	      const feeding = this.detailFeeding
	      if (!feeding || !feeding.id || this.detailSaving || !this.canEditDetail) return
	      const ok = await this.openConfirmSheet({
	        title: '确认删除',
	        desc: '删除后不可恢复。',
	        cancelText: '取消',
	        confirmText: '删除',
	        variant: 'danger',
	      })
	      if (!ok) return
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
	    },

	    openConfirmSheet({ title, desc, confirmText, cancelText, variant }) {
	      // 统一确认交互：返回 Promise<boolean>
	      if (this.confirmSheetVisible) return Promise.resolve(false)
	      this.confirmSheetTitle = String(title || '')
	      this.confirmSheetDesc = String(desc || '')
	      this.confirmSheetConfirmText = String(confirmText || '确定')
        this.confirmSheetShowCancel = cancelText !== false
	      this.confirmSheetCancelText = cancelText === false ? '取消' : String(cancelText || '取消')
	      this.confirmSheetVariant = variant === 'danger' ? 'danger' : 'primary'
	      this.confirmSheetLoading = false
	      this.confirmSheetVisible = true
	      return new Promise((resolve) => {
	        this.confirmSheetResolver = resolve
	      })
	    },

	    closeConfirmSheet(ok) {
	      const r = this.confirmSheetResolver
	      this.confirmSheetVisible = false
	      this.confirmSheetTitle = ''
	      this.confirmSheetDesc = ''
	      this.confirmSheetResolver = null
        this.confirmSheetShowCancel = true
	      try {
	        if (typeof r === 'function') r(!!ok)
	      } catch {}
	    },

	    handleConfirmSheetConfirm() {
	      this.closeConfirmSheet(true)
	    },

	    handleConfirmSheetCancel() {
	      this.closeConfirmSheet(false)
	    },

    buildUndoMeta(feeding) {
      const amount = Number(feeding?.amount || 0)
      const amountText = Number.isFinite(amount) && amount > 0 ? `${Math.round(amount)}ml` : ''

      // 1) 明显异常的间隔：优先提示“可能误触/记录过密”
      const interval = this.getIntervalInsight()
      if (interval?.status === 'frequent' && (interval.severity === 'severe' || interval.severity === 'moderate')) {
        const diffMs = Number(interval?.detail?.last_interval_ms || 0)
        const diffText = Number.isFinite(diffMs) && diffMs > 0 ? this.formatDurationText(diffMs) : ''
        const burst = interval?.detail?.burst_10m || null
        const burstText = burst && Number(burst.count || 0) >= 2
          ? ` · 10分钟内${burst.count}次`
          : ''

        if (interval.severity === 'severe') {
          return {
            tone: 'danger',
            title: '可能误触',
            sub: `${diffText ? `间隔仅 ${diffText}` : '间隔极短'}${amountText ? ` · ${amountText}` : ''}${burstText}`,
          }
        }
        return {
          tone: 'warn',
          title: '间隔偏短',
          sub: `${diffText ? `距上次 ${diffText}` : '距上次很短'}${amountText ? ` · ${amountText}` : ''}${burstText}`,
        }
      }

      // 2) 超喂（趋势）：按“时间进度”口径的偏快，给温和提醒（不在按钮上提示）
      const feedingStatus = this.feedingStatusForHome()
      if (feedingStatus === 'high') {
        const delta = this.todayDeltaText
        return {
          tone: 'warn',
          title: '今日偏多',
          sub: `${this.todayConsumedMl}ml${delta ? `（${delta}）` : ''}${amountText ? ` · 本次${amountText}` : ''}`,
        }
      }

      // 默认：只提示“已记录”，保持克制
      return {
        tone: 'ok',
        title: amountText ? `已记录 ${amountText}` : '已记录',
        sub: '',
      }
    },

    showUndo(feeding, meta) {
      if (!feeding || !feeding.id) return
      this.undoFeeding = feeding
      this.undoMeta = meta || null
      this.undoVisible = true
      if (this.undoTimer) clearTimeout(this.undoTimer)
      const tone = String(meta?.tone || 'ok')
      const ms = (tone === 'warn' || tone === 'danger') ? 6500 : 3000
      this.undoTimer = setTimeout(() => {
        this.undoVisible = false
        this.undoFeeding = null
        this.undoMeta = null
      }, ms)
    },

    async undoLastFeeding() {
      const feeding = this.undoFeeding
      if (!feeding || !feeding.id) return
      this.undoVisible = false
      this.undoFeeding = null
      this.undoMeta = null
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

    openExplainModal() {
      this.selectedTimelineKey = ''
      this.showTodayModal = false
      this.showExplainModal = true
    },

    async handleHomePrimaryAction() {
      const act = String(this.homePrimaryAction || 'record')
      if (act === 'record') {
        await this.recordNextSuggested()
        return
      }
      if (act === 'today') {
        await this.openTodayModal()
        return
      }
      if (act === 'explain') {
        this.openExplainModal()
        return
      }
      await this.recordNextSuggested()
    },

    closeExplainModal() {
      this.showExplainModal = false
    },

    openTodayFromExplain() {
      this.showExplainModal = false
      this.openTodayModal()
    },

    async openTodayModal() {
      this.selectedTimelineKey = ''
      this.showExplainModal = false
      this.showTodayModal = true
      await this.reloadTodayModal()
    },

    closeTodayModal() {
      this.showTodayModal = false
      this.todayModalError = ''
    },

    async reloadTodayModal() {
      if (!this.currentBaby?.id || this.todayModalLoading) return
      this.todayModalLoading = true
      this.todayModalError = ''
      try {
        await Promise.all([
          this.loadFeedings({ critical: true }),
          this.loadStats({ critical: true }),
          this.loadFamilyMembers(),
        ])
      } catch (e) {
        this.todayModalError = e?.message || '加载失败'
      } finally {
        this.todayModalLoading = false
      }
    },

    formatFeedingTime(raw) {
      if (!raw) return '--:--'
      const ms = this.parseTimeToMs(raw)
      if (!Number.isFinite(ms) || ms <= 0) return String(raw).slice(11, 16) || '--:--'
      return this.formatClockText(ms)
    },

    resolveMemberName(userId) {
      if (!userId) return '成员'
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(userId))
      return (m && (m.nickname || '成员')) || '成员'
    },

    weaningTagTextForFeeding(feeding) {
      const plan = this.weaningPlan || null
      if (!plan) return ''
      const bid = Number(feeding?.formula_brand_id || 0)
      if (!bid) return ''
      const oldId = Number(plan.old_brand_id || 0)
      const newId = Number(plan.new_brand_id || 0)
      if (oldId && bid === oldId) return '旧'
      if (newId && bid === newId) return '新'
      return ''
    },

    weaningTagClassForFeeding(feeding) {
      const plan = this.weaningPlan || null
      if (!plan) return ''
      const bid = Number(feeding?.formula_brand_id || 0)
      if (!bid) return ''
      const oldId = Number(plan.old_brand_id || 0)
      const newId = Number(plan.new_brand_id || 0)
      if (oldId && bid === oldId) return 'old'
      if (newId && bid === newId) return 'new'
      return ''
    },

    canEditFeeding(feeding) {
      if (!feeding) return false
      const userStore = useUserStore()
      const me = userStore.user?.id
      if (!me) return false
      if (String(feeding.user_id) === String(me)) return true
      const members = Array.isArray(this.familyMembers) ? this.familyMembers : []
      const m = members.find((x) => String(x.user_id) === String(me))
      return m?.role === 'admin'
    },

    handleFeedingRowTap(feeding) {
      if (!feeding) return
      // iOS 交互：如果当前有左滑打开的操作区，优先关闭，而不是直接进入详情
      if (this.swipeOpenFeedingKey) {
        this.swipeOpenFeedingKey = ''
        return
      }
      this.openDetail(feeding)
    },

    getTouchPoint(e) {
      const t =
        (e && e.touches && e.touches[0]) ||
        (e && e.changedTouches && e.changedTouches[0]) ||
        (e && e.detail && e.detail.touches && e.detail.touches[0]) ||
        (e && e.detail && e.detail.changedTouches && e.detail.changedTouches[0]) ||
        null
      const x = t ? (t.clientX ?? t.pageX) : null
      const y = t ? (t.clientY ?? t.pageY) : null
      const nx = Number(x)
      const ny = Number(y)
      return {
        x: Number.isFinite(nx) ? nx : 0,
        y: Number.isFinite(ny) ? ny : 0,
      }
    },

    onFeedingSwipeStart(e, feeding) {
      if (!feeding || !feeding.id) return
      const p = this.getTouchPoint(e)
      this.swipeStartX = p.x
      this.swipeStartY = p.y
      this.swipeStartKey = String(feeding.id)

      // 只允许同时打开一个
      const key = String(feeding.id)
      if (this.swipeOpenFeedingKey && this.swipeOpenFeedingKey !== key) {
        this.swipeOpenFeedingKey = ''
      }
    },

    onFeedingSwipeEnd(e, feeding) {
      if (!feeding || !feeding.id) return
      const key = String(feeding.id)
      if (this.swipeStartKey && this.swipeStartKey !== key) return

      const p = this.getTouchPoint(e)
      const dx = p.x - Number(this.swipeStartX || 0)
      const dy = p.y - Number(this.swipeStartY || 0)

      // 更偏纵向：视为滚动，不触发左滑
      if (Math.abs(dy) > Math.max(12, Math.abs(dx) * 1.2)) {
        this.swipeStartKey = ''
        return
      }

      const openThreshold = -45
      const closeThreshold = 45

      if (dx <= openThreshold && this.canEditFeeding(feeding)) {
        this.swipeOpenFeedingKey = key
      } else if (dx >= closeThreshold) {
        this.swipeOpenFeedingKey = ''
      }
      this.swipeStartKey = ''
    },

    swipeEdit(feeding) {
      if (!feeding) return
      this.swipeOpenFeedingKey = ''
      this.openDetail(feeding)
    },

    async swipeDelete(feeding) {
      if (!feeding || !feeding.id) return
      if (!this.canEditFeeding(feeding)) {
        uni.showToast({ title: '仅可删除自己创建的记录', icon: 'none' })
        return
      }
      this.swipeOpenFeedingKey = ''

      const timeText = this.formatFeedingTime(feeding.feeding_time)
      const amount = Number(feeding.amount || 0)
      const amountText = Number.isFinite(amount) ? `${Math.round(amount)}ml` : '--ml'

      const ok = await this.openConfirmSheet({
        title: '删除记录？',
        desc: `将删除 ${timeText} · ${amountText} 的记录，删除后不可恢复。`,
        cancelText: '取消',
        confirmText: '删除',
        variant: 'danger',
      })
      if (!ok) return

      try {
        await api.delete(`/feedings/${feeding.id}`)
        uni.showToast({ title: '已删除', icon: 'success' })
        await Promise.all([this.loadFeedings(), this.loadStats()])
      } catch (e) {
        uni.showToast({ title: e?.message || '删除失败', icon: 'none' })
      }
    },

    async handleTodayFixRow(it) {
      if (!it) return
      const act = String(it.action || '')

      if (act === 'refresh_today') {
        await this.reloadTodayModal()
        if (!this.todayModalError) uni.showToast({ title: '已刷新', icon: 'success' })
        return
      }

      if (act === 'undo_last') {
        const last = Array.isArray(this.recentFeedings) ? this.recentFeedings[0] : null
        if (!last || !last.id) return
        if (!this.canEditFeeding(last)) {
          uni.showToast({ title: '需要管理员处理', icon: 'none' })
          return
        }
        const timeText = this.formatFeedingTime(last.feeding_time)
        const amount = Number(last.amount || 0)
        const amountText = Number.isFinite(amount) ? `${Math.round(amount)}ml` : '--ml'
        const ok = await this.openConfirmSheet({
          title: '撤销最近一次记录？',
          desc: `将删除 ${timeText} · ${amountText} 的记录（删除后不可恢复）。`,
          cancelText: '取消',
          confirmText: '撤销',
          variant: 'danger',
        })
        if (!ok) return
        try {
          await api.delete(`/feedings/${last.id}`)
          uni.showToast({ title: '已撤销', icon: 'success' })
          await Promise.all([this.loadFeedings(), this.loadStats()])
        } catch (e) {
          uni.showToast({ title: e?.message || '撤销失败', icon: 'none' })
        }
        return
      }

      if (act === 'edit_feeding' || act === 'view_feeding') {
        const feeding = it.feeding
        if (!feeding) return
        this.openDetail(feeding)
        return
      }

      if (act === 'open_today') {
        if (this.showTodayModal) return
        await this.openTodayModal()
      }
    },

    handleHomeTimelineSelect(key) {
      const k = String(key || '')
      if (!k) return
      if (this.selectedTimelineKey === k) {
        this.openTodayModal()
        return
      }
      this.selectedTimelineKey = k
      if (this.timelineSelectTimer) clearTimeout(this.timelineSelectTimer)
      this.timelineSelectTimer = setTimeout(() => {
        this.selectedTimelineKey = ''
        this.timelineSelectTimer = null
      }, 6000)
    },

    handleTodayTimelineSelect(key) {
      const k = String(key || '')
      if (!k) return
      // 今日抽屉内：再次点同一点 -> 关闭气泡（不再“重复打开”抽屉）
      if (this.selectedTimelineKey === k) {
        this.selectedTimelineKey = ''
        return
      }
      this.selectedTimelineKey = k
      if (this.timelineSelectTimer) clearTimeout(this.timelineSelectTimer)
      this.timelineSelectTimer = setTimeout(() => {
        this.selectedTimelineKey = ''
        this.timelineSelectTimer = null
      }, 6000)
    },

    goToDataDetail() {
      // 数据详情：从首页下钻
      this.showTodayModal = false
      uni.navigateTo({ url: '/pages/data-detail/index' })
    },

    goToFormulaSpec() {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      this.showExplainModal = false
      uni.navigateTo({ url: `/pages/formula-spec/index?babyId=${babyId}` })
    },

    goWeaningPlan() {
      const babyId = this.currentBaby?.id
      if (!babyId) return
      uni.navigateTo({ url: `/pages/weaning-plan/index?babyId=${babyId}` })
    },
    
    goToBabyInfo() {
      uni.navigateTo({
        url: '/pages/baby-info/index'
      })
    },

    goBabySwitch() {
      uni.navigateTo({ url: '/pages/baby-switch/index' })
    },
    
    showMenu() {
      // 统一入口：进入“设置”页（更像系统设置，信息与入口集中，不再用 ActionSheet 堆选项）
      uni.navigateTo({ url: '/pages/settings/index' })
    },
    
    startCountdown() {
      if (this.countdownTimer) clearInterval(this.countdownTimer)

      const tick = () => {
        const nowMs = Date.now()
        this.nowTickMs = nowMs

        // 下次喂奶：严格以服务端 timestamp 为准（与喂奶设置口径一致）
        const nextMs = this.nextFeedingTimestampMs
        if (Number.isFinite(nextMs) && nextMs > 0) {
          this.nextFeedingClockText = this.formatClockText(nextMs)
          this.nextFeedingDayLabel = this.formatDayLabel(nextMs, nowMs)
          const diff = nextMs - nowMs
          if (Number.isFinite(diff) && diff >= 0) {
            this.nextCountdownMode = 'remaining'
            this.nextCountdownText = this.formatDurationText(diff)
          } else if (Number.isFinite(diff)) {
            this.nextCountdownMode = 'overdue'
            this.nextCountdownText = this.formatDurationText(Math.abs(diff))
          } else {
            this.nextCountdownMode = 'remaining'
            this.nextCountdownText = '--'
          }
          this.maybeFireInAppReminder(nextMs, nowMs)
        } else {
          this.nextFeedingClockText = '--:--'
          this.nextFeedingDayLabel = ''
          this.nextCountdownMode = 'remaining'
          this.nextCountdownText = '--'
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

      const useSystem = canUseSystemNotify() && isPageHidden()

      // 每个“下次喂奶时间”最多触发一次提前提示 + 一次到点提示
      if (advMin > 0 && this.remindAdvanceFiredFor !== targetMs) {
        const advAt = targetMs - advMs
        if (nowMs >= advAt && nowMs < targetMs) {
          this.remindAdvanceFiredFor = targetMs
          const title = `还有${advMin}分钟到下次喂奶`
          if (useSystem) {
            const n = sendSystemNotify('奶宝提醒', {
              body: title,
              icon: '/static/naiping1.svg',
              tag: `naibao-adv-${String(targetMs)}`,
            })
            try {
              if (n) n.onclick = () => { try { window.focus() } catch {} }
            } catch {}
          } else {
            uni.showToast({ title, icon: 'none' })
          }
        }
      }
      if (this.remindDueFiredFor !== targetMs && nowMs >= targetMs) {
        this.remindDueFiredFor = targetMs
        const title = '该喂奶了'
        if (useSystem) {
          const n = sendSystemNotify('奶宝提醒', {
            body: title,
            icon: '/static/naiping1.svg',
            tag: `naibao-due-${String(targetMs)}`,
          })
          try {
            if (n) n.onclick = () => { try { window.focus() } catch {} }
          } catch {}
        } else {
          try { uni.vibrateShort() } catch {}
          uni.showToast({ title, icon: 'none' })
        }
      }
    }
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  width: 100%;
  /* 强约束：避免某些 WebView 在运行期丢失/覆盖全局 CSS 变量，导致卡片列宽度“变窄”。 */
  --nb-content-max: 680px;
  /* 兜底：有些 WebView/浏览器对 page 背景渲染不一致，导致顶部出现“白色标题栏/白块”观感。
     首页容器自己再铺一层同款背景，确保从最顶端开始是奶油渐变而不是白底。 */
  background:
    linear-gradient(180deg, rgba(27, 26, 23, 0.12) 0%, rgba(27, 26, 23, 0) 140px),
    radial-gradient(1200px 600px at 20% -10%, rgba(255, 216, 136, 0.35), rgba(255, 216, 136, 0) 60%),
    radial-gradient(900px 500px at 90% 0%, rgba(255, 155, 92, 0.22), rgba(255, 155, 92, 0) 55%),
    #fffaf2;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  /* 预留底部主按钮 + 撤销条 + 安全区 */
  padding-bottom: calc(170px + env(safe-area-inset-bottom, 0px));
  position: relative;
  box-sizing: border-box;
}

.home-main {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  /* 关键：不要用 center，让子内容随内容“缩起来”。这里必须 stretch，才能避免
     时间轴说明卡片显隐导致整列卡片宽度抖动（更符合 iOS 的稳定布局）。 */
  align-items: stretch;
  justify-content: flex-start;
  /* 顶部不要再“空一大块”：主内容从安全区后直接开始（更像 iOS 信息布局） */
  padding: calc(var(--nb-safe-top)) var(--nb-page-x) 48px;
  box-sizing: border-box;
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
  gap: 4px;
  cursor: pointer;
  width: 40px;
  height: 40px;
  justify-content: center;
  align-items: center;
  border-radius: 20px; /* 正圆按钮 */
  background: var(--nb-card-bg-2);
  border: 1px solid var(--nb-border);
  box-shadow: var(--nb-shadow-card-strong);
  backdrop-filter: blur(10px);
}

.menu-line {
  display: block;
  width: 18px;
  height: 2px;
  background-color: rgba(var(--nb-ink-rgb), 0.82);
  border-radius: 2px;
}

/* 宝宝信息区域 */
.baby-profile-section {
  width: 100%;
  max-width: var(--nb-content-max, 520px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 0 14px;
  box-sizing: border-box;
}

.baby-avatar-large {
  width: 84px;
  height: 84px;
  border-radius: 42px;
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

.baby-name-row:active {
  opacity: 0.86;
}

.baby-name-large {
  font-size: 30px;
  font-weight: 800;
  color: var(--nb-text);
  text-align: center;
  line-height: 1.2;
}

.baby-switch-chev {
  font-size: 22px;
  font-weight: 900;
  color: var(--nb-faint);
  line-height: 1;
  transform: translateY(-1px);
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
  color: var(--nb-muted);
  white-space: nowrap;
}

.stat-dot {
  font-size: 14px;
  color: rgba(var(--nb-ink-rgb), 0.40);
}

/* 首页轻量引导（Setup Nudge）：一条即可，避免面板化 */
.setup-nudge {
  width: 100%;
  max-width: var(--nb-content-max, 520px);
  margin: 0 auto 14px;
  padding: 10px 12px;
  border-radius: 18px;
  border: 1px solid var(--nb-border);
  background: var(--nb-card-bg-soft);
  box-shadow: var(--nb-shadow-card);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-sizing: border-box;
  user-select: none;
}

.setup-nudge:active {
  transform: scale(0.995);
}

.setup-nudge-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.setup-nudge-icon {
  width: 30px;
  height: 30px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--nb-fill);
  border: 1px solid var(--nb-line);
  flex: 0 0 30px;
}

.setup-nudge-icon.t-info {
  background: rgba(247, 201, 72, 0.18);
  border-color: rgba(247, 201, 72, 0.30);
}

.setup-nudge-icon.t-warn {
  background: rgba(226, 74, 59, 0.12);
  border-color: rgba(226, 74, 59, 0.22);
}

.setup-nudge-icon-text {
  font-size: 16px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.78);
}

.setup-nudge-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setup-nudge-title {
  font-size: 13px;
  font-weight: 900;
  color: var(--nb-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setup-nudge-desc {
  font-size: 12px;
  color: var(--nb-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setup-nudge-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.setup-nudge-cta {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.92);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.setup-nudge-chev {
  font-size: 16px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.38);
}

.setup-nudge-close {
  font-size: 18px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.42);
  padding-left: 6px;
}

/* 首页信息减法：弱说明、强主线（下次喂奶 + 24h 时间轴） */
.home-focus {
  width: 100%;
  max-width: var(--nb-content-max, 520px);
  margin: 0 auto;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
}

.focus-card {
  width: 100%;
  border-radius: 22px;
  border: 1px solid var(--nb-border);
  background: var(--nb-card-bg-soft);
  box-shadow: var(--nb-shadow-card);
  backdrop-filter: blur(10px);
  padding: 16px 14px;
  box-sizing: border-box;
}

.timeline-plan {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid var(--nb-line);
  background: rgba(var(--nb-ink-rgb), 0.04);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  box-sizing: border-box;
  user-select: none;
}

.timeline-plan:active {
  transform: scale(0.995);
}

.timeline-plan-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.timeline-plan-title {
  font-size: 13px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.86);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-plan-sub {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.62);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}

.timeline-plan-hint {
  font-size: 12px;
  font-weight: 800;
  color: rgba(181, 83, 29, 0.92);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-plan-chev {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.50);
  white-space: nowrap;
}

.hero {
  text-align: center;
}

.hero-label {
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: var(--nb-muted-2);
  letter-spacing: 0.3px;
}

.hero-time-row {
  margin-top: 6px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.hero-day-pill {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(var(--nb-ink-rgb), 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-day-pill-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.66);
  line-height: 1;
}

.hero-time {
  font-size: 22px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.86);
  letter-spacing: -0.2px;
  font-variant-numeric: tabular-nums;
}

.hero-countdown-row {
  margin-top: 10px;
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hero-countdown-prefix {
  font-size: 14px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.70);
}

.hero-countdown-hm {
  font-size: 40px;
  font-weight: 900;
  letter-spacing: -0.8px;
  color: var(--nb-text);
  line-height: 1.08;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.hero-countdown-suffix {
  font-size: 14px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.70);
  white-space: nowrap;
}

.hero-countdown-row.overdue .hero-countdown-prefix,
.hero-countdown-row.overdue .hero-countdown-hm,
.hero-countdown-row.overdue .hero-countdown-suffix {
  color: var(--nb-danger);
}

.hero-meta-line {
  margin-top: 10px;
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: rgba(var(--nb-ink-rgb), 0.70);
}

.health-banner {
  margin-top: 12px;
  width: 100%;
  border-radius: 18px;
  border: 1px solid var(--nb-border-2);
  background: var(--nb-fill);
  padding: 10px 10px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  box-sizing: border-box;
  user-select: none;
  text-align: left;
}

.health-banner:active {
  transform: scale(0.995);
}

.health-banner-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.health-banner-title {
  font-size: 13px;
  font-weight: 1000;
  color: rgba(var(--nb-ink-rgb), 0.90);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.health-banner-desc {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.66);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}

.health-banner-chev {
  flex: 0 0 auto;
  font-size: 22px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.32);
  line-height: 1;
  transform: translateY(-1px);
}

.health-banner.lv-attention .health-banner-title {
  color: rgba(181, 83, 29, 0.95);
}

.health-banner.lv-alert .health-banner-title {
  color: var(--nb-danger);
}

.hero-badges {
  margin-top: 14px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.health-pill {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--nb-border-2);
  background: var(--nb-fill);
}

.health-pill-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.72);
}

.weaning-pill {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--nb-border-2);
  background: rgba(247, 201, 72, 0.16);
}

.weaning-pill.active {
  background: rgba(247, 201, 72, 0.18);
  border-color: rgba(247, 201, 72, 0.28);
}

.weaning-pill.paused {
  background: var(--nb-fill);
  border-color: var(--nb-border-2);
}

.weaning-pill.done {
  background: rgba(82, 196, 26, 0.12);
  border-color: rgba(82, 196, 26, 0.18);
}

.weaning-pill-text {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.72);
}

.weaning-pill.paused .weaning-pill-text {
  color: rgba(var(--nb-ink-rgb), 0.66);
}

.weaning-pill.done .weaning-pill-text {
  color: rgba(var(--nb-ink-rgb), 0.78);
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
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.today-sub-strong {
  font-size: 14px;
  font-weight: 900;
  color: var(--nb-text);
}

.today-sub-dot {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.38);
}

.today-sub-muted {
  font-size: 13px;
  color: var(--nb-muted);
  font-variant-numeric: tabular-nums;
}

.suggest-card {
  margin-top: 12px;
  border-radius: 18px;
  border: 1px solid var(--nb-border);
  background:
    radial-gradient(720px 260px at 18% 0%, rgba(247, 201, 72, 0.20), rgba(247, 201, 72, 0) 60%),
    radial-gradient(520px 260px at 100% 30%, rgba(255, 138, 61, 0.14), rgba(255, 138, 61, 0) 62%),
    var(--nb-card-bg);
  padding: 12px 12px 10px;
  box-shadow: var(--nb-shadow-card-strong);
  text-align: center;
}

.suggest-k {
  display: block;
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.58);
}

.suggest-v {
  margin-top: 6px;
  display: block;
  font-size: 34px;
  font-weight: 900;
  color: var(--nb-text);
  letter-spacing: -0.8px;
  line-height: 1.05;
}

.suggest-sub {
  margin-top: 6px;
  display: block;
  font-size: 12px;
  font-weight: 900;
  color: var(--nb-muted-2);
}

.suggest-link {
  color: rgba(var(--nb-ink-rgb), 0.72);
  text-decoration: underline;
  text-underline-offset: 4px;
}

.suggest-link:active {
  opacity: 0.7;
}

.today-progress {
  margin-top: 12px;
  border-radius: 18px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.72);
  padding: 12px 12px 10px;
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
  color: rgba(var(--nb-ink-rgb), 0.70);
}

.today-progress-bar {
  width: 100%;
  height: 8px;
  border-radius: 6px;
  background: var(--nb-border);
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
  background: var(--nb-muted-2);
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
  color: var(--nb-muted);
}

.today-progress-delta-row {
  margin-top: 10px;
  text-align: center;
}

.today-progress-delta {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--nb-border);
  background: rgba(var(--nb-ink-rgb), 0.05);
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.72);
}

.d-low {
  background: rgba(255, 138, 61, 0.14);
  border-color: rgba(255, 138, 61, 0.22);
  color: rgba(181, 83, 29, 0.95);
}

.d-high {
  background: rgba(226, 74, 59, 0.12);
  border-color: rgba(226, 74, 59, 0.22);
  color: var(--nb-danger);
}

.today-advice {
  margin-top: 2px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--nb-border);
  background: rgba(255, 255, 255, 0.70);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.today-advice-title {
  font-size: 12px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.78);
}

.today-advice-item {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.70);
  line-height: 1.55;
}

.today-hint-disclaimer {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.50);
}

.today-meta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--nb-border);
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.today-meta-text {
  font-size: 12px;
  color: var(--nb-muted);
}

.today-meta-link {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.72);
  text-decoration: underline;
  text-underline-offset: 4px;
}

/* 投喂按钮 */
.feed-button-large {
  position: fixed;
  /* 贴底需考虑手势条安全区 */
  bottom: calc(24px + var(--nb-safe-bottom));
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 100px;
  border-radius: 50px;
  background-color: #333;
  border: 3px solid #FFD700;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.feed-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 30px;
  height: 30px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(var(--nb-ink-rgb), 0.14);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(10px);
}

.feed-badge.old {
  background: rgba(255, 255, 255, 0.92);
}

.feed-badge.new {
  background: rgba(247, 201, 72, 0.26);
  border-color: rgba(247, 201, 72, 0.36);
}

.feed-badge-text {
  font-size: 12px;
  font-weight: 1000;
  color: rgba(var(--nb-ink-rgb), 0.82);
}

.feed-button-large:active {
  transform: translateX(-50%) scale(0.95);
}

.feed-button-text {
  color: #fff;
  font-size: 24px;
  font-weight: 600;
}

.feed-button-sub {
  margin-top: -2px;
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: -0.2px;
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

.today-modal-meta {
  margin-top: 0;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.70);
  border: 1px solid var(--nb-border);
}

.today-modal-meta-text {
  font-size: 12px;
  color: var(--nb-muted);
  line-height: 1.5;
}

.today-timeline-wrap {
  margin-bottom: 12px;
}

.today-fix {
  margin-bottom: 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--nb-border);
  overflow: hidden;
}

.today-fix.in-list {
  margin-bottom: 0;
  border-radius: 0;
  border: none;
  background: transparent;
  border-bottom: 1px solid var(--nb-line);
}

.today-fix-head {
  padding: 10px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--nb-line);
}

.today-fix.in-list .today-fix-head {
  background: rgba(255, 255, 255, 0.55);
}

.today-fix-title {
  font-size: 13px;
  font-weight: 900;
  color: var(--nb-text);
}

.today-fix-sub {
  font-size: 12px;
  color: var(--nb-muted);
}

.today-fix-row {
  padding: 10px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--nb-line);
  user-select: none;
}

.today-fix-row:active {
  background: rgba(27, 26, 23, 0.04);
}

.today-fix-row:last-child {
  border-bottom: none;
}

.today-fix-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 10px;
}

.today-fix-dot {
  width: 10px;
  height: 10px;
  border-radius: 5px;
  margin-top: 5px;
  flex: 0 0 10px;
  background: rgba(255, 138, 61, 0.85);
}

.today-fix-dot.t-warn {
  background: rgba(255, 138, 61, 0.85);
}

.today-fix-dot.t-danger {
  background: rgba(226, 74, 59, 0.88);
}

.today-fix-dot.t-info {
  background: rgba(247, 201, 72, 0.85);
}

.today-fix-texts {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.today-fix-main {
  font-size: 13px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.80);
  line-height: 1.25;
}

.today-fix-desc {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.56);
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.today-fix-cta {
  flex: none;
  font-size: 13px;
  font-weight: 900;
  color: rgba(var(--nb-ink-rgb), 0.70);
  white-space: nowrap;
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
  color: rgba(var(--nb-ink-rgb), 0.72);
}

.today-modal-empty-sub {
  font-size: 13px;
  color: rgba(var(--nb-ink-rgb), 0.58);
}

.today-modal-list {
  height: 44vh;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--nb-border);
  overflow: hidden;
}

.today-swipe {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: transparent;
}

.today-swipe-actions {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  justify-content: flex-end;
  width: 140px;
  /* 让操作区在 H5 上可点击：避免被内容容器覆盖 */
  z-index: 3;
  pointer-events: none;
}

.today-swipe.open .today-swipe-actions {
  pointer-events: auto;
}

.today-swipe-action {
  width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.today-swipe-action.edit {
  background: rgba(255, 138, 61, 0.92);
}

.today-swipe-action.delete {
  background: rgba(226, 74, 59, 0.92);
}

.today-swipe-action-text {
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.today-swipe-content {
  position: relative;
  z-index: 2;
  box-sizing: border-box;
}

.today-item {
  padding: 12px 12px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--nb-line);
  transform: translateX(0);
  transition: transform 180ms ease;
  will-change: transform;
}

.today-swipe.open .today-item {
  transform: translateX(-140px);
}

.today-item:last-child {
  border-bottom: none;
}

.today-item-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 10px;
}

.today-item-time {
  width: 46px;
  font-size: 13px;
  color: rgba(var(--nb-ink-rgb), 0.66);
  font-family: 'Courier New', monospace;
  white-space: nowrap;
}

.today-item-amount {
  font-size: 16px;
  font-weight: 900;
  color: var(--nb-text);
  text-align: left;
  white-space: nowrap;
}

.today-item-tag {
  padding: 2px 6px;
  border-radius: 999px;
  border: 1px solid var(--nb-border-2);
  background: var(--nb-fill);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.today-item-tag.old {
  background: var(--nb-fill);
}

.today-item-tag.new {
  background: rgba(247, 201, 72, 0.18);
  border-color: rgba(247, 201, 72, 0.26);
}

.today-item-tag-text {
  font-size: 11px;
  font-weight: 1000;
  color: rgba(var(--nb-ink-rgb), 0.72);
}

.today-item-user {
  flex: none;
  max-width: 40%;
  text-align: right;
  font-size: 12px;
  color: var(--nb-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  bottom: calc(148px + var(--nb-safe-bottom));
  border: 1px solid var(--nb-border);
  border-radius: var(--nb-radius-lg);
  padding: 12px 14px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--nb-card-bg);
  box-shadow: 0 10px 28px rgba(var(--nb-ink-rgb), 0.12);
  z-index: 998;
}

.undo-toast.tone-warn {
  border-color: rgba(255, 138, 61, 0.26);
  background:
    radial-gradient(720px 260px at 20% 0%, rgba(255, 138, 61, 0.10), rgba(255, 138, 61, 0) 60%),
    rgba(255, 255, 255, 0.94);
}

.undo-toast.tone-danger {
  border-color: rgba(226, 74, 59, 0.26);
  background:
    radial-gradient(720px 260px at 20% 0%, rgba(226, 74, 59, 0.10), rgba(226, 74, 59, 0) 60%),
    rgba(255, 255, 255, 0.94);
}

.undo-left {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.undo-icon {
  width: 32px;
  height: 32px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--nb-fill);
  border: 1px solid var(--nb-border);
  flex: none;
}

.tone-warn .undo-icon {
  background: rgba(255, 138, 61, 0.14);
  border-color: rgba(255, 138, 61, 0.22);
}

.tone-danger .undo-icon {
  background: rgba(226, 74, 59, 0.12);
  border-color: rgba(226, 74, 59, 0.22);
}

.undo-icon-text {
  font-size: 16px;
  color: rgba(var(--nb-ink-rgb), 0.72);
  font-weight: 900;
  line-height: 1;
}

.tone-warn .undo-icon-text {
  color: rgba(181, 83, 29, 0.95);
}

.tone-danger .undo-icon-text {
  color: var(--nb-danger);
}

.undo-lines {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.undo-title {
  font-size: 14px;
  color: var(--nb-text);
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.undo-sub {
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.58);
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.undo-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  flex: none;
}

.undo-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--nb-border-2);
  background: rgba(var(--nb-ink-rgb), 0.04);
  color: rgba(var(--nb-ink-rgb), 0.86);
  font-size: 13px;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

.undo-btn.primary {
  border: none;
  background: rgba(var(--nb-ink-rgb), 0.92);
  color: rgba(255, 255, 255, 0.92);
}

.tone-warn .undo-btn.primary {
  background: rgba(255, 138, 61, 0.92);
}

.tone-danger .undo-btn.primary {
  background: rgba(226, 74, 59, 0.92);
}

/* 详情弹窗补充样式（复用 modal-* 基础结构） */
.detail-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--nb-line);
}

.detail-row.disabled {
  opacity: 0.78;
}

.detail-label {
  font-size: 14px;
  color: var(--nb-muted);
}

.detail-picker-wrap {
  flex: 1;
}

.detail-picker {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-width: 0;
}

.detail-value {
  font-size: 14px;
  color: #333;
  font-weight: 700;
}

.detail-chev {
  font-size: 18px;
  color: rgba(var(--nb-ink-rgb), 0.38);
  font-weight: 900;
  line-height: 1;
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
  border: 2px solid var(--nb-border);
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
  color: var(--nb-muted-3);
  font-size: 14px;
  font-weight: 700;
}

.detail-hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: rgba(var(--nb-ink-rgb), 0.52);
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
  background: var(--nb-line);
  border-color: var(--nb-border);
  color: var(--nb-muted-3);
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
