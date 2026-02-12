package handlers

import (
	"errors"
	"net/http"
	"naibao-backend/models"
	"naibao-backend/services"
	"naibao-backend/utils"
	ws "naibao-backend/websocket"
	"strconv"
	"strings"
	"time"
	
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FeedingHandler struct {
	DB           *gorm.DB
	MilkCalc     *services.MilkCalculator
	Hub          *ws.Hub
}

func NewFeedingHandler(db *gorm.DB, hub *ws.Hub) *FeedingHandler {
	return &FeedingHandler{
		DB:       db,
		MilkCalc: services.NewMilkCalculator(),
		Hub:      hub,
	}
}

type CreateFeedingRequest struct {
	BabyID          uint   `json:"baby_id" binding:"required"`
	Amount          int    `json:"amount" binding:"required,min=10,max=300"`
	FeedingTime     string `json:"feeding_time"` // ISO格式，为空则使用当前时间
	FormulaBrandID  *uint  `json:"formula_brand_id"`
	FormulaSeriesName string `json:"formula_series_name"`
	Scoops          *int   `json:"scoops"`
	InputMethod     string `json:"input_method"` // direct/quick/manual（可选，用于偏好记忆）
}

type UpdateFeedingRequest struct {
	Amount          int    `json:"amount"`
	FeedingTime     string `json:"feeding_time"`
	FormulaBrandID  *uint  `json:"formula_brand_id"`
	FormulaSeriesName string `json:"formula_series_name"`
	Scoops          *int   `json:"scoops"`
}

// CreateFeeding 创建喂养记录
func (h *FeedingHandler) CreateFeeding(c *gin.Context) {
	userID := c.GetUint("userID")
	
	var req CreateFeedingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	// 验证权限：家庭成员可记录喂养
	var baby models.Baby
	if err := h.DB.Where("id = ?", req.BabyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	if _, err := ensureBabyMember(h.DB, &baby, userID); err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}

	// 用于“偏好记忆”的当次推荐量（在写入前计算，避免被本次记录影响）
	baby.CalculateAge()
	fillBabyCurrentGrowth(h.DB, &baby)
	var pref models.UserPreference
	var userPrefAmount *int
	if err := h.DB.Where("user_id = ? AND baby_id = ?", userID, baby.ID).First(&pref).Error; err == nil {
		userPrefAmount = pref.DefaultAmount
	}

	dayStartHour := 6
	dayEndHour := 18
	dayInterval := 3
	nightInterval := 5
	var settings models.FeedingSettings
	if err := h.DB.Where("baby_id = ?", baby.ID).First(&settings).Error; err == nil {
		if settings.DayStartHour > 0 {
			dayStartHour = settings.DayStartHour
		}
		if settings.DayEndHour > 0 {
			dayEndHour = settings.DayEndHour
		}
		if settings.DayInterval > 0 {
			dayInterval = settings.DayInterval
		}
		if settings.NightInterval > 0 {
			nightInterval = settings.NightInterval
		}
	}

	now := time.Now()
	startOfDay := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())
	endOfDay := startOfDay.AddDate(0, 0, 1)
	var todayFeedings []models.Feeding
	_ = h.DB.Where("baby_id = ? AND feeding_time >= ? AND feeding_time < ?", baby.ID, startOfDay, endOfDay).
		Find(&todayFeedings).Error

	coef, _ := services.LookupMilkByWeightCoefficient(h.DB, 135.0)
	ageRef, _ := services.LookupMilkByAgeReferenceText(h.DB, baby.AgeInMonths)
	reco := h.MilkCalc.CalculateRecommendedAmountWithStandards(
		&baby,
		todayFeedings,
		userPrefAmount,
		now,
		dayStartHour,
		dayEndHour,
		dayInterval,
		nightInterval,
		coef,
		ageRef,
	)
	
	// 解析时间：默认使用服务端当前时间。
	// 说明：喂奶记录不应出现在“未来”。部分设备/脚本可能传错时间戳，
	// 会直接导致“下次喂奶倒计时”异常（例如显示十几个小时）。
	serverNow := time.Now()
	feedingTime := serverNow
	if req.FeedingTime != "" {
		if parsedTime, err := time.Parse(time.RFC3339, req.FeedingTime); err == nil {
			feedingTime = parsedTime
		}
	}
	// 统一落库为“北京时间墙钟时间”（DB 字段为 TIMESTAMP 无时区，避免跨环境解析偏移）
	feedingTime = feedingTime.In(utils.CNLocation())
	// 允许轻微时钟偏差（2分钟），超出则强制回落到服务端 now。
	if feedingTime.After(serverNow.Add(2 * time.Minute)) {
		feedingTime = serverNow.In(utils.CNLocation())
	}
	
	feeding := models.Feeding{
		BabyID:          req.BabyID,
		UserID:          userID,
		Amount:          req.Amount,
		FeedingTime:     feedingTime,
		FormulaBrandID:  req.FormulaBrandID,
		FormulaSeriesName: req.FormulaSeriesName,
		Scoops:          req.Scoops,
	}
	
	if err := h.DB.Create(&feeding).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}

	logOperation(h.DB, userID, "create", "feeding", feeding.ID, nil, feeding)
	broadcastEvent(h.Hub, feeding.BabyID, "feeding", "create", feeding.ID)

	// 偏好记忆：best-effort（不阻塞主流程）
	{
		delta := req.Amount - reco.Recommended
		if delta > 120 {
			delta = 120
		}
		if delta < -120 {
			delta = -120
		}

		method := strings.TrimSpace(req.InputMethod)
		if method == "" {
			if delta == 0 {
				method = "direct"
			} else {
				method = "quick"
			}
		}
		amount := req.Amount

		var up models.UserPreference
		if err := h.DB.Where("user_id = ? AND baby_id = ?", userID, feeding.BabyID).First(&up).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				up = models.UserPreference{
					UserID:            userID,
					BabyID:            feeding.BabyID,
					DefaultAmount:     &amount,
					AdjustmentPattern: delta,
					InputMethod:       method,
				}
				_ = h.DB.Create(&up).Error
			}
		} else {
			up.DefaultAmount = &amount
			up.AdjustmentPattern = delta
			up.InputMethod = method
			_ = h.DB.Save(&up).Error
		}
	}
	
	c.JSON(http.StatusOK, gin.H{"feeding": feeding})
}

// GetFeedings 获取喂养记录列表
func (h *FeedingHandler) GetFeedings(c *gin.Context) {
	userID := c.GetUint("userID")
	babyID := c.Query("baby_id")

	// 默认：要求传 baby_id（家庭协作时需要返回“所有成员”的记录）；兼容旧逻辑：不传则仅返回本人记录
	query := h.DB
	if babyID != "" {
		bid, err := parseUintSafe(babyID)
		if err != nil || bid == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
			return
		}

		var baby models.Baby
		if err := h.DB.Where("id = ?", bid).First(&baby).Error; err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
			return
		}
		if _, err := ensureBabyMember(h.DB, &baby, userID); err != nil {
			if errors.Is(err, errForbidden) {
				c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
				return
			}
			c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
			return
		}

		query = query.Where("baby_id = ?", bid)
	} else {
		query = query.Where("user_id = ?", userID)
	}
	
	// 时间范围
	startDate := c.Query("start_date")
	endDate := c.Query("end_date")
	if startDate != "" && endDate != "" {
		query = query.Where("feeding_time >= ? AND feeding_time <= ?", startDate, endDate)
	}
	
	var feedings []models.Feeding
	if err := query.Order("feeding_time DESC").Limit(100).Find(&feedings).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	// 修正 TIMESTAMP(无时区) 的解析：避免被驱动当作 UTC 导致整体 +8h 偏移
	for i := range feedings {
		feedings[i].FeedingTime = utils.ReinterpretAsCNWallClock(feedings[i].FeedingTime)
	}
	
	c.JSON(http.StatusOK, gin.H{"feedings": feedings})
}

// GetFeedingStats 获取喂养统计
func (h *FeedingHandler) GetFeedingStats(c *gin.Context) {
	userID := c.GetUint("userID")
	babyIDStr := c.Query("baby_id")
	if babyIDStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "baby_id is required"})
		return
	}
	
	babyID, err := strconv.ParseUint(babyIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}
	
	// 验证权限：家庭成员可查看统计
	var baby models.Baby
	if err := h.DB.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	if _, err := ensureBabyMember(h.DB, &baby, userID); err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	
	baby.CalculateAge()
	// 用最新的生长记录回填体重/身高，推荐算法会优先使用体重计算日标准奶量
	fillBabyCurrentGrowth(h.DB, &baby)

	// 用户偏好（可选）
	var pref models.UserPreference
	var userPrefAmount *int
	if err := h.DB.Where("user_id = ? AND baby_id = ?", userID, uint(babyID)).First(&pref).Error; err == nil {
		userPrefAmount = pref.DefaultAmount
	} else {
		pref = models.UserPreference{UserID: userID, BabyID: uint(babyID), AdjustmentPattern: 0}
	}

	// 读取喂奶间隔设置（没有则使用默认值）
	dayStartHour := 6
	dayEndHour := 18
	dayInterval := 3
	nightInterval := 5
	var settings models.FeedingSettings
	if err := h.DB.Where("baby_id = ?", babyID).First(&settings).Error; err == nil {
		if settings.DayStartHour > 0 {
			dayStartHour = settings.DayStartHour
		}
		if settings.DayEndHour > 0 {
			dayEndHour = settings.DayEndHour
		}
		if settings.DayInterval > 0 {
			dayInterval = settings.DayInterval
		}
		if settings.NightInterval > 0 {
			nightInterval = settings.NightInterval
		}
	}

	now := time.Now().In(utils.CNLocation())
	futureGrace := 2 * time.Minute
	startOfDay := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, now.Location())
	endOfDay := startOfDay.AddDate(0, 0, 1)

	// 获取今日喂养记录（限定当天范围，避免混入未来数据）
	var todayFeedings []models.Feeding
	upperBound := endOfDay
	if now.Add(futureGrace).Before(upperBound) {
		upperBound = now.Add(futureGrace)
	}

	h.DB.Where("baby_id = ? AND feeding_time >= ? AND feeding_time < ?", babyID, startOfDay, upperBound).
		Find(&todayFeedings)

	// 最近 7 天（含今天）：用于计算日均
	periodStart := startOfDay.AddDate(0, 0, -6)
	var recentFeedings []models.Feeding
	h.DB.Where("baby_id = ? AND feeding_time >= ? AND feeding_time < ?", babyID, periodStart, upperBound).
		Find(&recentFeedings)

	// 修正时间字段（见 utils.ReinterpretAsCNWallClock 注释）
	for i := range todayFeedings {
		todayFeedings[i].FeedingTime = utils.ReinterpretAsCNWallClock(todayFeedings[i].FeedingTime)
	}
	for i := range recentFeedings {
		recentFeedings[i].FeedingTime = utils.ReinterpretAsCNWallClock(recentFeedings[i].FeedingTime)
	}
	
	// 计算今日总奶量
	todayAmount := 0
	for _, f := range todayFeedings {
		todayAmount += f.Amount
	}
	
	// 计算日均奶量（最近7天）
	dailyAmount := 0
	if len(recentFeedings) > 0 {
		totalAmount := 0
		for _, f := range recentFeedings {
			totalAmount += f.Amount
		}
		dailyAmount = totalAmount / 7
	}
	
	// 计算推荐奶量
	coef, _ := services.LookupMilkByWeightCoefficient(h.DB, 135.0)
	ageRef, _ := services.LookupMilkByAgeReferenceText(h.DB, baby.AgeInMonths)
	recommended := h.MilkCalc.CalculateRecommendedAmountWithStandards(
		&baby,
		todayFeedings,
		userPrefAmount,
		now,
		dayStartHour,
		dayEndHour,
		dayInterval,
		nightInterval,
		coef,
		ageRef,
	)
	
	stats := models.FeedingStat{
		TotalAmount:    todayAmount,
		DailyAmount:    dailyAmount,
		TodayAmount:    todayAmount,
		RemainingTimes: recommended.RemainingTimes,
	}
	
	// 计算下次喂奶时间
	if recommended.RemainingTimes > 0 {
		// 以“上次喂奶时间 + 时段间隔”计算，体验更符合用户预期
		var lastFeeding models.Feeding
		// 兜底：忽略未来时间的异常记录，避免把“未来记录”当作上次喂奶导致倒计时失真
		_ = h.DB.Where("baby_id = ? AND feeding_time <= ?", babyID, now.Add(futureGrace)).
			Order("feeding_time DESC").
			First(&lastFeeding).Error
		lastFeeding.FeedingTime = utils.ReinterpretAsCNWallClock(lastFeeding.FeedingTime)

		nextTime := h.MilkCalc.CalculateNextFeedingTime(
			now,
			lastFeeding.FeedingTime,
			dayStartHour,
			dayEndHour,
			dayInterval,
			nightInterval,
		)
		stats.NextFeedingTime = &nextTime
	}
	
	resp := gin.H{
		"stats":      stats,
		"recommended": recommended,
		"preference": gin.H{
			"default_amount":     pref.DefaultAmount,
			"adjustment_pattern": pref.AdjustmentPattern,
			"input_method":       pref.InputMethod,
		},
	}
	if stats.NextFeedingTime != nil {
		resp["next_feeding_timestamp"] = stats.NextFeedingTime.Unix()
	}
	c.JSON(http.StatusOK, resp)
}

// UpdateFeeding 更新喂养记录
func (h *FeedingHandler) UpdateFeeding(c *gin.Context) {
	userID := c.GetUint("userID")
	feedingID := c.Param("id")
	
	var req UpdateFeedingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	var feeding models.Feeding
	if err := h.DB.Where("id = ?", feedingID).First(&feeding).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "记录不存在"})
		return
	}
	feeding.FeedingTime = utils.ReinterpretAsCNWallClock(feeding.FeedingTime)

	// 权限：管理员可编辑任意记录；成员仅可编辑自己创建的记录
	var baby models.Baby
	if err := h.DB.Where("id = ?", feeding.BabyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	if !isAdmin(member) && feeding.UserID != userID {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅可编辑自己创建的记录"})
		return
	}

	before := feeding
	
	// 更新字段
	if req.Amount > 0 {
		feeding.Amount = req.Amount
	}
	if req.FeedingTime != "" {
		parsedTime, err := time.Parse(time.RFC3339, req.FeedingTime)
		if err == nil {
			loc := utils.CNLocation()
			t := parsedTime.In(loc)
			// 不允许“未来喂奶时间”，避免破坏倒计时/统计（允许轻微时钟偏差）
			serverNow := time.Now().In(loc)
			if t.After(serverNow.Add(2 * time.Minute)) {
				t = serverNow
			}
			feeding.FeedingTime = t
		}
	}
	if req.FormulaBrandID != nil {
		feeding.FormulaBrandID = req.FormulaBrandID
	}
	if req.FormulaSeriesName != "" {
		feeding.FormulaSeriesName = req.FormulaSeriesName
	}
	if req.Scoops != nil {
		feeding.Scoops = req.Scoops
	}
	
	if err := h.DB.Save(&feeding).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	feeding.FeedingTime = utils.ReinterpretAsCNWallClock(feeding.FeedingTime)

	logOperation(h.DB, userID, "update", "feeding", feeding.ID, before, feeding)
	broadcastEvent(h.Hub, feeding.BabyID, "feeding", "update", feeding.ID)
	
	c.JSON(http.StatusOK, gin.H{"feeding": feeding})
}

// DeleteFeeding 删除喂养记录
func (h *FeedingHandler) DeleteFeeding(c *gin.Context) {
	userID := c.GetUint("userID")
	feedingID := c.Param("id")

	var feeding models.Feeding
	if err := h.DB.Where("id = ?", feedingID).First(&feeding).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "记录不存在"})
		return
	}

	// 权限：管理员可删除任意记录；成员仅可删除自己创建的记录
	var baby models.Baby
	if err := h.DB.Where("id = ?", feeding.BabyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}
	if !isAdmin(member) && feeding.UserID != userID {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅可删除自己创建的记录"})
		return
	}

	before := feeding
	
	if err := h.DB.Where("id = ?", feedingID).Delete(&models.Feeding{}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}

	logOperation(h.DB, userID, "delete", "feeding", feeding.ID, before, nil)
	broadcastEvent(h.Hub, feeding.BabyID, "feeding", "delete", feeding.ID)
	
	c.JSON(http.StatusOK, gin.H{"message": "删除成功"})
}
