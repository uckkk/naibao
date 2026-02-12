package handlers

import (
	"errors"
	"net/http"
	"naibao-backend/models"
	"naibao-backend/utils"
	ws "naibao-backend/websocket"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type WeaningPlanHandler struct {
	DB  *gorm.DB
	Hub *ws.Hub
}

// GetCurrent returns the latest plan that is active/paused (baby-level).
func (h *WeaningPlanHandler) GetCurrent(c *gin.Context) {
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

	var plan models.WeaningPlan
	if err := h.DB.Where("baby_id = ? AND status IN ?", babyID, []string{"active", "paused"}).
		Order("start_at DESC").
		Preload("OldBrand").
		Preload("NewBrand").
		First(&plan).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			c.JSON(http.StatusOK, gin.H{"plan": nil})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	plan.StartAt = utils.ReinterpretAsCNWallClock(plan.StartAt)
	if plan.PausedAt != nil {
		t := utils.ReinterpretAsCNWallClock(*plan.PausedAt)
		plan.PausedAt = &t
	}
	if plan.EndedAt != nil {
		t := utils.ReinterpretAsCNWallClock(*plan.EndedAt)
		plan.EndedAt = &t
	}

	c.JSON(http.StatusOK, gin.H{"plan": plan})
}

// Create creates a new weaning plan. If an active/paused plan exists, it is ended first.
func (h *WeaningPlanHandler) Create(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var req struct {
		Mode         string `json:"mode"` // alternate (default)
		DurationDays int    `json:"duration_days"`

		OldBrandID    uint   `json:"old_brand_id" binding:"required"`
		OldSeriesName string `json:"old_series_name"`
		OldAgeRange   string `json:"old_age_range"`

		NewBrandID    uint   `json:"new_brand_id" binding:"required"`
		NewSeriesName string `json:"new_series_name"`
		NewAgeRange   string `json:"new_age_range"`

		StartAt string `json:"start_at"` // RFC3339 optional
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.OldBrandID == 0 || req.NewBrandID == 0 || req.OldBrandID == req.NewBrandID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "奶粉品牌不正确"})
		return
	}

	mode := strings.TrimSpace(req.Mode)
	if mode == "" {
		mode = "alternate"
	}
	if mode != "alternate" {
		// MVP：只支持“喂次交替”，避免同次混合的高风险与高误差
		c.JSON(http.StatusBadRequest, gin.H{"error": "暂不支持该模式"})
		return
	}

	days := req.DurationDays
	if days <= 0 {
		days = 7
	}
	if days < 3 {
		days = 3
	}
	if days > 14 {
		days = 14
	}

	// 权限：仅管理员可创建/变更（宝宝级配置）
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}
	if !isAdmin(member) {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可创建转奶计划"})
		return
	}

	startAt := time.Now().In(utils.CNLocation())
	if strings.TrimSpace(req.StartAt) != "" {
		if t, err := time.Parse(time.RFC3339, strings.TrimSpace(req.StartAt)); err == nil {
			startAt = t.In(utils.CNLocation())
		}
	}

	var plan models.WeaningPlan
	err = h.DB.Transaction(func(tx *gorm.DB) error {
		// end existing active/paused plan (keep history)
		var existing models.WeaningPlan
		if err := tx.Where("baby_id = ? AND status IN ?", babyID, []string{"active", "paused"}).
			Order("start_at DESC").
			First(&existing).Error; err == nil {
			before := existing
			now := time.Now().In(utils.CNLocation())
			existing.Status = "ended"
			existing.EndedAt = &now
			if err := tx.Save(&existing).Error; err != nil {
				return err
			}
			logOperation(tx, userID, "update", "weaning_plan", existing.ID, before, existing)
			broadcastEvent(h.Hub, babyID, "weaning_plan", "end", existing.ID)
		} else if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
			return err
		}

		plan = models.WeaningPlan{
			BabyID:        babyID,
			CreatedBy:     userID,
			Mode:          mode,
			DurationDays:  days,
			OldBrandID:    req.OldBrandID,
			OldSeriesName: req.OldSeriesName,
			OldAgeRange:   req.OldAgeRange,
			NewBrandID:    req.NewBrandID,
			NewSeriesName: req.NewSeriesName,
			NewAgeRange:   req.NewAgeRange,
			StartAt:       startAt,
			Status:        "active",
		}

		if err := tx.Create(&plan).Error; err != nil {
			return err
		}
		logOperation(tx, userID, "create", "weaning_plan", plan.ID, nil, plan)
		broadcastEvent(h.Hub, babyID, "weaning_plan", "create", plan.ID)
		return nil
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}

	// Preload brand names for client convenience
	_ = h.DB.Preload("OldBrand").Preload("NewBrand").First(&plan, plan.ID).Error
	plan.StartAt = utils.ReinterpretAsCNWallClock(plan.StartAt)

	c.JSON(http.StatusOK, gin.H{"plan": plan})
}

// UpdateStatus pauses/resumes/ends the current plan.
func (h *WeaningPlanHandler) UpdateStatus(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var req struct {
		Action string `json:"action" binding:"required"` // pause|resume|end
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	action := strings.ToLower(strings.TrimSpace(req.Action))
	if action != "pause" && action != "resume" && action != "end" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid action"})
		return
	}

	// 权限：仅管理员可变更（宝宝级配置）
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
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可修改转奶计划"})
		return
	}

	var plan models.WeaningPlan
	if err := h.DB.Where("baby_id = ? AND status IN ?", babyID, []string{"active", "paused"}).
		Order("start_at DESC").
		First(&plan).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "没有进行中的转奶计划"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	before := plan
	now := time.Now().In(utils.CNLocation())
	switch action {
	case "pause":
		if plan.Status == "active" {
			plan.Status = "paused"
			plan.PausedAt = &now
		}
	case "resume":
		if plan.Status == "paused" {
			plan.Status = "active"
			plan.PausedAt = nil
		}
	case "end":
		plan.Status = "ended"
		plan.EndedAt = &now
		plan.PausedAt = nil
	}

	if err := h.DB.Save(&plan).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
		return
	}

	logOperation(h.DB, userID, "update", "weaning_plan", plan.ID, before, plan)
	broadcastEvent(h.Hub, babyID, "weaning_plan", "update", plan.ID)

	_ = h.DB.Preload("OldBrand").Preload("NewBrand").First(&plan, plan.ID).Error
	plan.StartAt = utils.ReinterpretAsCNWallClock(plan.StartAt)
	if plan.PausedAt != nil {
		t := utils.ReinterpretAsCNWallClock(*plan.PausedAt)
		plan.PausedAt = &t
	}
	if plan.EndedAt != nil {
		t := utils.ReinterpretAsCNWallClock(*plan.EndedAt)
		plan.EndedAt = &t
	}

	c.JSON(http.StatusOK, gin.H{"plan": plan})
}

