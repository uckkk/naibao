package handlers

import (
	"errors"
	"naibao-backend/models"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FormulaSpecHandler struct {
	DB *gorm.DB
}

// GetSpecifications 获取某品牌的冲泡规格（可选按系列/段位过滤）
func (h *FormulaSpecHandler) GetSpecifications(c *gin.Context) {
	brandIDStr := c.Query("brand_id")
	if brandIDStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "brand_id is required"})
		return
	}
	brandID, err := parseUintSafe(brandIDStr)
	if err != nil || brandID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid brand_id"})
		return
	}

	series := c.Query("series_name")
	ageRange := c.Query("age_range")

	q := h.DB.Where("brand_id = ?", brandID)
	if series != "" {
		q = q.Where("series_name = ?", series)
	}
	if ageRange != "" {
		q = q.Where("age_range = ?", ageRange)
	}

	var specs []models.FormulaSpecification
	if err := q.Order("is_verified DESC, updated_at DESC").Find(&specs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"specifications": specs})
}

// GetCurrentSpecification 获取当前宝宝选择奶粉的冲泡规格（按 selection 匹配，找不到则返回 404）
func (h *FormulaSpecHandler) GetCurrentSpecification(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
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

	// 当前奶粉选择（按 baby 维度取最近一次 active）
	var sel models.UserFormulaSelection
	if err := h.DB.Where("baby_id = ? AND is_active = true", babyID).
		Order("selected_at DESC").
		First(&sel).Error; err != nil {
		// 对客户端来说，“未选择”属于正常空态，不应以 404 触发控制台报错/弱网误判。
		c.JSON(http.StatusOK, gin.H{"specification": nil})
		return
	}

	q := h.DB.Where("brand_id = ?", sel.BrandID)
	if sel.SeriesName != "" {
		q = q.Where("series_name = ?", sel.SeriesName)
	}
	if sel.AgeRange != "" {
		q = q.Where("age_range = ?", sel.AgeRange)
	}

	var spec models.FormulaSpecification
	if err := q.Order("is_verified DESC, updated_at DESC").Preload("Brand").First(&spec).Error; err != nil {
		// 找不到规格数据也视为正常空态：前端可以提示“暂无官方数据，以包装为准”。避免 404 造成误报。
		c.JSON(http.StatusOK, gin.H{"specification": nil})
		return
	}

	c.JSON(http.StatusOK, gin.H{"specification": spec})
}
