package handlers

import (
	"net/http"
	"strings"
	"time"

	"naibao-backend/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AdminFormulaSpecHandler struct {
	DB *gorm.DB
}

func (h *AdminFormulaSpecHandler) List(c *gin.Context) {
	brandIDStr := strings.TrimSpace(c.Query("brand_id"))
	series := strings.TrimSpace(c.Query("series_name"))
	ageRange := strings.TrimSpace(c.Query("age_range"))

	q := h.DB.Model(&models.FormulaSpecification{}).Preload("Brand")
	if brandIDStr != "" {
		brandID, err := parseUintSafe(brandIDStr)
		if err != nil || brandID == 0 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid brand_id"})
			return
		}
		q = q.Where("brand_id = ?", brandID)
	}
	if series != "" {
		q = q.Where("series_name = ?", series)
	}
	if ageRange != "" {
		q = q.Where("age_range = ?", ageRange)
	}

	var specs []models.FormulaSpecification
	if err := q.Order("updated_at DESC, id DESC").Find(&specs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"specifications": specs})
}

func (h *AdminFormulaSpecHandler) Create(c *gin.Context) {
	var req struct {
		BrandID          uint    `json:"brand_id" binding:"required"`
		SeriesName       string  `json:"series_name" binding:"required"`
		AgeRange         string  `json:"age_range" binding:"required"`
		ScoopWeightGram  float64 `json:"scoop_weight_gram" binding:"required"`
		ScoopML          float64 `json:"scoop_ml" binding:"required"`
		WaterTempMin     *int    `json:"water_temp_min"`
		WaterTempMax     *int    `json:"water_temp_max"`
		MixingMethod     string  `json:"mixing_method"`
		FeedingFrequency string  `json:"feeding_frequency"`
		DailyAmountMin   *int    `json:"daily_amount_min"`
		DailyAmountMax   *int    `json:"daily_amount_max"`
		DataSource       string  `json:"data_source"`
		IsVerified       *bool   `json:"is_verified"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.BrandID == 0 || strings.TrimSpace(req.SeriesName) == "" || strings.TrimSpace(req.AgeRange) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "brand_id/series_name/age_range 必填"})
		return
	}
	if req.ScoopWeightGram <= 0 || req.ScoopML <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "scoop_weight_gram/scoop_ml 必须大于 0"})
		return
	}

	spec := models.FormulaSpecification{
		BrandID:          req.BrandID,
		SeriesName:       strings.TrimSpace(req.SeriesName),
		AgeRange:         strings.TrimSpace(req.AgeRange),
		ScoopWeightGram:  req.ScoopWeightGram,
		ScoopML:          req.ScoopML,
		WaterTempMin:     req.WaterTempMin,
		WaterTempMax:     req.WaterTempMax,
		MixingMethod:     req.MixingMethod,
		FeedingFrequency: req.FeedingFrequency,
		DailyAmountMin:   req.DailyAmountMin,
		DailyAmountMax:   req.DailyAmountMax,
		DataSource:       req.DataSource,
	}
	if req.IsVerified != nil {
		spec.IsVerified = *req.IsVerified
		if spec.IsVerified {
			now := time.Now()
			spec.VerifiedAt = &now
		}
	}

	if err := h.DB.Create(&spec).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}
	_ = h.DB.Preload("Brand").Where("id = ?", spec.ID).First(&spec).Error
	c.JSON(http.StatusOK, gin.H{"specification": spec})
}

func (h *AdminFormulaSpecHandler) Update(c *gin.Context) {
	id, err := parseUintSafe(strings.TrimSpace(c.Param("id")))
	if err != nil || id == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var spec models.FormulaSpecification
	if err := h.DB.Where("id = ?", id).First(&spec).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "记录不存在"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 白名单更新：避免无意覆盖 gorm 关联字段
	allowed := map[string]struct{}{
		"series_name":         {},
		"age_range":           {},
		"scoop_weight_gram":   {},
		"scoop_ml":            {},
		"water_temp_min":      {},
		"water_temp_max":      {},
		"mixing_method":       {},
		"feeding_frequency":   {},
		"daily_amount_min":    {},
		"daily_amount_max":    {},
		"data_source":         {},
		"is_verified":         {},
		"verified_at":         {},
	}
	updates := map[string]interface{}{}
	for k, v := range req {
		if _, ok := allowed[k]; ok {
			updates[k] = v
		}
	}
	if len(updates) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无可更新字段"})
		return
	}

	if err := h.DB.Model(&spec).Updates(updates).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	_ = h.DB.Preload("Brand").Where("id = ?", id).First(&spec).Error
	c.JSON(http.StatusOK, gin.H{"specification": spec})
}

func (h *AdminFormulaSpecHandler) Verify(c *gin.Context) {
	id, err := parseUintSafe(strings.TrimSpace(c.Param("id")))
	if err != nil || id == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var spec models.FormulaSpecification
	if err := h.DB.Where("id = ?", id).First(&spec).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "记录不存在"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	now := time.Now()
	spec.IsVerified = true
	spec.VerifiedAt = &now

	if err := h.DB.Save(&spec).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	_ = h.DB.Preload("Brand").Where("id = ?", id).First(&spec).Error
	c.JSON(http.StatusOK, gin.H{"specification": spec})
}
