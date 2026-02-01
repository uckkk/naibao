package handlers

import (
	"errors"
	"net/http"
	"strings"

	"naibao-backend/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type PreferenceHandler struct {
	DB *gorm.DB
}

func (h *PreferenceHandler) GetPreference(c *gin.Context) {
	userID := c.GetUint("userID")
	babyID, err := parseUintSafe(strings.TrimSpace(c.Param("id")))
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

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

	var pref models.UserPreference
	if err := h.DB.Where("user_id = ? AND baby_id = ?", userID, babyID).First(&pref).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			c.JSON(http.StatusOK, gin.H{"preference": gin.H{
				"user_id":            userID,
				"baby_id":            babyID,
				"default_amount":     nil,
				"adjustment_pattern": 0,
				"input_method":       "",
			}})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"preference": pref})
}

func (h *PreferenceHandler) UpdatePreference(c *gin.Context) {
	userID := c.GetUint("userID")
	babyID, err := parseUintSafe(strings.TrimSpace(c.Param("id")))
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

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

	var req struct {
		DefaultAmount     *int   `json:"default_amount"`
		AdjustmentPattern *int   `json:"adjustment_pattern"`
		InputMethod       string `json:"input_method"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var pref models.UserPreference
	err = h.DB.Where("user_id = ? AND baby_id = ?", userID, babyID).First(&pref).Error
	if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
		return
	}
	if errors.Is(err, gorm.ErrRecordNotFound) {
		pref = models.UserPreference{UserID: userID, BabyID: babyID}
	}

	if req.DefaultAmount != nil {
		// 允许清空：传 0 或负数则置为 nil
		if *req.DefaultAmount > 0 {
			v := *req.DefaultAmount
			pref.DefaultAmount = &v
		} else {
			pref.DefaultAmount = nil
		}
	}
	if req.AdjustmentPattern != nil {
		pref.AdjustmentPattern = *req.AdjustmentPattern
	}
	if strings.TrimSpace(req.InputMethod) != "" {
		pref.InputMethod = strings.TrimSpace(req.InputMethod)
	}

	if pref.ID == 0 {
		if err := h.DB.Create(&pref).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
	} else {
		if err := h.DB.Save(&pref).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{"preference": pref})
}

