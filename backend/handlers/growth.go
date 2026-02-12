package handlers

import (
	"errors"
	"naibao-backend/models"
	"naibao-backend/services"
	"naibao-backend/utils"
	ws "naibao-backend/websocket"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type GrowthHandler struct {
	DB *gorm.DB
	Hub *ws.Hub
}

// GetGrowthStats 获取生长统计数据
func (h *GrowthHandler) GetGrowthStats(c *gin.Context) {
	babyID := c.Param("id")
	userID := c.GetUint("userID")

	// 验证权限：家庭成员可查看
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

	// 获取最新的生长记录
	var latestGrowth models.GrowthRecord
	h.DB.Where("baby_id = ?", babyID).
		Order("record_date DESC").
		First(&latestGrowth)

	// 获取最早的生长记录（用于计算日均增重/增高）
	var earliestGrowth models.GrowthRecord
	h.DB.Where("baby_id = ?", babyID).
		Order("record_date ASC").
		First(&earliestGrowth)

	// 计算日均增重和增高
	var dailyWeightGain, dailyHeightGain float64
	if !latestGrowth.RecordDate.IsZero() && !earliestGrowth.RecordDate.IsZero() {
		daysDiff := latestGrowth.RecordDate.Sub(earliestGrowth.RecordDate).Hours() / 24
		if daysDiff > 0 {
			if latestGrowth.Weight != nil && earliestGrowth.Weight != nil && *latestGrowth.Weight > 0 && *earliestGrowth.Weight > 0 {
				dailyWeightGain = (*latestGrowth.Weight - *earliestGrowth.Weight) / daysDiff
			}
			if latestGrowth.Height != nil && earliestGrowth.Height != nil && *latestGrowth.Height > 0 && *earliestGrowth.Height > 0 {
				// height 以 cm 存储；前端展示单位为 mm/day，因此这里换算为 mm/day
				dailyHeightGain = float64((*latestGrowth.Height - *earliestGrowth.Height) * 10) / daysDiff
			}
		}
	}
	
	// 获取当前身高和体重
	var currentHeight, currentWeight interface{}
	if latestGrowth.Height != nil {
		currentHeight = *latestGrowth.Height
	} else {
		currentHeight = 0
	}
	if latestGrowth.Weight != nil {
		currentWeight = *latestGrowth.Weight
	} else {
		currentWeight = 0.0
	}

	// 计算日均奶量（最近7天）
	sevenDaysAgo := time.Now().AddDate(0, 0, -7)
	var recentFeedings []models.Feeding
	h.DB.Where("baby_id = ? AND feeding_time >= ?", babyID, sevenDaysAgo).
		Find(&recentFeedings)

	var totalAmount int
	for _, f := range recentFeedings {
		totalAmount += f.Amount
	}
	dailyAvgMilk := float64(totalAmount) / 7.0

	// 获取参考值（优先从 health_standards 读取，缺失则回退到常量）
	calculator := services.NewMilkCalculator()
	_, _, fallbackMilk := calculator.GetAgeReference(baby.AgeInMonths)
	milkReference := fallbackMilk
	if t, ok := services.LookupMilkByAgeReferenceText(h.DB, baby.AgeInMonths); ok && t != "" {
		milkReference = t
	}

	weightGainRef := "0.025-0.035kg/天"
	if baby.AgeInMonths >= 3 && baby.AgeInMonths < 6 {
		weightGainRef = "0.015-0.025kg/天"
	}
	if baby.AgeInMonths >= 6 {
		weightGainRef = "0.01-0.015kg/天"
	}
	if t, ok := services.LookupWeightGainReferenceText(h.DB, baby.AgeInMonths); ok && t != "" {
		weightGainRef = t
	}

	heightGainRef := "8-11mm/天"
	if baby.AgeInMonths >= 3 && baby.AgeInMonths < 6 {
		heightGainRef = "6-9mm/天"
	}
	if baby.AgeInMonths >= 6 {
		heightGainRef = "4-6mm/天"
	}
	if t, ok := services.LookupHeightGainReferenceText(h.DB, baby.AgeInMonths); ok && t != "" {
		heightGainRef = t
	}

	c.JSON(http.StatusOK, gin.H{
		"age_in_days": baby.AgeInDays,
		"current_height": currentHeight,
		"current_weight": currentWeight,
		"daily_weight_gain": dailyWeightGain,
		"daily_height_gain": dailyHeightGain,
		"daily_avg_milk": dailyAvgMilk,
		"reference": gin.H{
			"weight_gain": weightGainRef,
			"height_gain": heightGainRef,
			"milk":        milkReference,
		},
	})
}

// GetDailyRecords 获取每日记录（支持月份筛选）
func (h *GrowthHandler) GetDailyRecords(c *gin.Context) {
	babyID := c.Param("id")
	userID := c.GetUint("userID")
	month := c.Query("month") // 格式：2025-10

	// 验证权限：家庭成员可查看
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

	// 解析月份
	var startDate, endDate time.Time
	loc := utils.CNLocation()
	if month != "" {
		parsedMonth, err := time.Parse("2006-01", month)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "月份格式错误，应为 YYYY-MM"})
			return
		}
		startDate = time.Date(parsedMonth.Year(), parsedMonth.Month(), 1, 0, 0, 0, 0, loc)
		endDate = startDate.AddDate(0, 1, 0).Add(-time.Second)
	} else {
		// 默认当前月
		now := time.Now().In(loc)
		startDate = time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, loc)
		endDate = startDate.AddDate(0, 1, 0).Add(-time.Second)
	}

	// 获取该月的生长记录
	var growthRecords []models.GrowthRecord
	h.DB.Where("baby_id = ? AND record_date >= ? AND record_date <= ?", babyID, startDate, endDate).
		Order("record_date ASC").
		Find(&growthRecords)

	// 获取该月的喂养记录（计算日总奶量）
	var feedings []models.Feeding
	h.DB.Where("baby_id = ? AND feeding_time >= ? AND feeding_time <= ?", babyID, startDate, endDate).
		Find(&feedings)
	for i := range feedings {
		feedings[i].FeedingTime = utils.ReinterpretAsCNWallClock(feedings[i].FeedingTime)
	}

	// 按日期组织数据
	type DailyRecord struct {
		Date        string  `json:"date"`
		Weight      *float64 `json:"weight"`
		Height      *int    `json:"height"`
		DailyAmount int     `json:"daily_amount"`
	}

	recordsMap := make(map[string]*DailyRecord)
	
	// 初始化该月所有日期
	currentDate := startDate
	for currentDate.Before(endDate) || currentDate.Equal(endDate) {
		dateStr := currentDate.Format("2006-01-02")
		recordsMap[dateStr] = &DailyRecord{
			Date:        dateStr,
			Weight:      nil,
			Height:      nil,
			DailyAmount: 0,
		}
		currentDate = currentDate.AddDate(0, 0, 1)
	}

		// 填充生长记录
	for _, gr := range growthRecords {
		dateStr := gr.RecordDate.Format("2006-01-02")
		if record, ok := recordsMap[dateStr]; ok {
			if gr.Weight != nil && *gr.Weight > 0 {
				weight := *gr.Weight
				record.Weight = &weight
			}
			if gr.Height != nil && *gr.Height > 0 {
				height := *gr.Height
				record.Height = &height
			}
			if gr.DailyMilkAmount != nil {
				record.DailyAmount = *gr.DailyMilkAmount
			}
		}
	}

	// 填充喂养记录（计算日总奶量）
	for _, f := range feedings {
		dateStr := f.FeedingTime.Format("2006-01-02")
		if record, ok := recordsMap[dateStr]; ok {
			record.DailyAmount += f.Amount
		}
	}

	// 转换为数组
	var records []DailyRecord
	currentDate = startDate
	for currentDate.Before(endDate) || currentDate.Equal(endDate) {
		dateStr := currentDate.Format("2006-01-02")
		if record, ok := recordsMap[dateStr]; ok {
			records = append(records, *record)
		}
		currentDate = currentDate.AddDate(0, 0, 1)
	}

	c.JSON(http.StatusOK, gin.H{
		"month": month,
		"records": records,
	})
}

// CreateGrowthRecord 创建生长记录
func (h *GrowthHandler) CreateGrowthRecord(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var req struct {
		RecordDate string   `json:"record_date" binding:"required"`
		Weight     *float64 `json:"weight"`
		Height     *int     `json:"height"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	recordDate, err := time.Parse("2006-01-02", req.RecordDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "日期格式错误"})
		return
	}

	// 验证权限：家庭成员可录入（共享同一宝宝）
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
		return
	}

	// 检查是否已存在
	var existing models.GrowthRecord
	result := h.DB.Where("baby_id = ? AND record_date = ?", babyID, recordDate).First(&existing)
	
	if result.Error == nil {
		// 更新现有记录
		before := existing
		if req.Weight != nil {
			weight := *req.Weight
			existing.Weight = &weight
		}
		if req.Height != nil {
			height := *req.Height
			existing.Height = &height
		}
		if err := h.DB.Save(&existing).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
		logOperation(h.DB, userID, "update", "growth", existing.ID, before, existing)
		broadcastEvent(h.Hub, babyID, "growth", "upsert", existing.ID)
		c.JSON(http.StatusOK, gin.H{"record": existing})
		return
	}

	// 创建新记录
	record := models.GrowthRecord{
		BabyID:     babyID,
		RecordDate: recordDate,
	}
	if req.Weight != nil {
		weight := *req.Weight
		record.Weight = &weight
	}
	if req.Height != nil {
		height := *req.Height
		record.Height = &height
	}

	if err := h.DB.Create(&record).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}

	logOperation(h.DB, userID, "create", "growth", record.ID, nil, record)
	broadcastEvent(h.Hub, babyID, "growth", "create", record.ID)
	c.JSON(http.StatusOK, gin.H{"record": record})
}
