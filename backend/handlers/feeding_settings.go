package handlers

import (
	"errors"
	"naibao-backend/models"
	"naibao-backend/services"
	"naibao-backend/utils"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FeedingSettingsHandler struct {
	DB *gorm.DB
}

// GetSettings 获取喂奶间隔设置
func (h *FeedingSettingsHandler) GetSettings(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	// 权限：家庭成员可读设置
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

	var settings models.FeedingSettings
	result := h.DB.Where("baby_id = ?", babyID).First(&settings)
	
	if result.Error == gorm.ErrRecordNotFound {
		// 如果没有设置，返回默认值
		settings = models.FeedingSettings{
			BabyID:         babyID,
			UserID:         userID,
			DayInterval:    3,
			NightInterval:  5,
			ReminderEnabled: true,
			AdvanceMinutes: 15,
			DayStartHour:   6,
			DayEndHour:     18,
		}
	} else if result.Error != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": result.Error.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"settings": settings})
}

// UpdateSettings 更新喂奶间隔设置
func (h *FeedingSettingsHandler) UpdateSettings(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	// 权限：仅管理员可改设置（避免多人乱改）
	var baby models.Baby
	if err := h.DB.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
		return
	}
	if !isAdmin(member) {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可修改设置"})
		return
	}

	var req struct {
		DayInterval    *int  `json:"day_interval"`
		NightInterval  *int  `json:"night_interval"`
		ReminderEnabled *bool `json:"reminder_enabled"`
		AdvanceMinutes *int  `json:"advance_minutes"`
		DayStartHour   *int  `json:"day_start_hour"`
		DayEndHour     *int  `json:"day_end_hour"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 验证数据
	if req.DayInterval != nil && (*req.DayInterval < 1 || *req.DayInterval > 5) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "白天间隔应在1-5小时之间"})
		return
	}
	if req.NightInterval != nil && (*req.NightInterval < 3 || *req.NightInterval > 7) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "晚上间隔应在3-7小时之间"})
		return
	}
	if req.AdvanceMinutes != nil && (*req.AdvanceMinutes < 5 || *req.AdvanceMinutes > 30) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "提前提醒应在5-30分钟之间"})
		return
	}

	var settings models.FeedingSettings
	result := h.DB.Where("baby_id = ?", babyID).First(&settings)
	created := false
	before := settings

	if result.Error == gorm.ErrRecordNotFound {
		// 创建新设置
		settings = models.FeedingSettings{
			BabyID:         babyID,
			UserID:         userID,
			DayInterval:    3,
			NightInterval:  5,
			ReminderEnabled: true,
			AdvanceMinutes: 15,
			DayStartHour:   6,
			DayEndHour:     18,
		}
		created = true
	}

	// 更新字段
	if req.DayInterval != nil {
		settings.DayInterval = *req.DayInterval
	}
	if req.NightInterval != nil {
		settings.NightInterval = *req.NightInterval
	}
	if req.ReminderEnabled != nil {
		settings.ReminderEnabled = *req.ReminderEnabled
	}
	if req.AdvanceMinutes != nil {
		settings.AdvanceMinutes = *req.AdvanceMinutes
	}
	if req.DayStartHour != nil {
		settings.DayStartHour = *req.DayStartHour
	}
	if req.DayEndHour != nil {
		settings.DayEndHour = *req.DayEndHour
	}

	if created {
		if err := h.DB.Create(&settings).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
		logOperation(h.DB, userID, "create", "feeding_settings", settings.ID, nil, settings)
	} else {
		if err := h.DB.Save(&settings).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
		logOperation(h.DB, userID, "update", "feeding_settings", settings.ID, before, settings)
	}

	c.JSON(http.StatusOK, gin.H{"settings": settings})
}

// GetNextFeedingTime 计算下次喂奶时间
func (h *FeedingSettingsHandler) GetNextFeedingTime(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	// 权限：家庭成员可查看
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

	// 获取设置
	var settings models.FeedingSettings
	result := h.DB.Where("baby_id = ?", babyID).First(&settings)
	if result.Error == gorm.ErrRecordNotFound {
		// 使用默认值
		settings = models.FeedingSettings{
			DayInterval:    3,
			NightInterval:  5,
			DayStartHour:   6,
			DayEndHour:     18,
		}
	}

	// 获取最后一次喂奶记录（忽略未来时间的异常记录，避免倒计时失真）
	var lastFeeding models.Feeding
	now := time.Now().In(utils.CNLocation())
	futureGrace := 2 * time.Minute
	_ = h.DB.Where("baby_id = ? AND feeding_time <= ?", babyID, now.Add(futureGrace)).
		Order("feeding_time DESC").
		First(&lastFeeding).Error
	lastFeeding.FeedingTime = utils.ReinterpretAsCNWallClock(lastFeeding.FeedingTime)

	// 计算下次喂奶时间
	calculator := services.NewMilkCalculator()
	nextTime := calculator.CalculateNextFeedingTime(
		now,
		lastFeeding.FeedingTime,
		settings.DayStartHour,
		settings.DayEndHour,
		settings.DayInterval,
		settings.NightInterval,
	)

	c.JSON(http.StatusOK, gin.H{
		"next_feeding_time": nextTime.Format("2006-01-02 15:04:05"),
		"next_feeding_timestamp": nextTime.Unix(),
	})
}
