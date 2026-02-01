package handlers

import (
	"errors"
	"naibao-backend/models"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FormulaHandler struct {
	DB *gorm.DB
}

// GetBrands 获取奶粉品牌列表
func (h *FormulaHandler) GetBrands(c *gin.Context) {
	var brands []models.FormulaBrand
	if err := h.DB.Order("market_share DESC").Find(&brands).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"brands": brands})
}

// SelectFormula 选择奶粉
func (h *FormulaHandler) SelectFormula(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var req struct {
		BrandID    uint   `json:"brand_id" binding:"required"`
		SeriesName string `json:"series_name"`
		AgeRange   string `json:"age_range"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 验证权限：仅管理员可选择奶粉（全局配置）
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
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可选择奶粉"})
		return
	}

	// 检查是否已存在
	var existing models.UserFormulaSelection
	result := h.DB.Where("baby_id = ? AND user_id = ?", babyID, userID).First(&existing)

	if result.Error == nil {
		// 更新现有选择
		before := existing
		existing.BrandID = req.BrandID
		existing.SeriesName = req.SeriesName
		existing.AgeRange = req.AgeRange
		existing.IsActive = true
		if err := h.DB.Save(&existing).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
			return
		}
		logOperation(h.DB, userID, "update", "formula_selection", existing.ID, before, existing)
		c.JSON(http.StatusOK, gin.H{"selection": existing})
		return
	}

	// 创建新选择
	selection := models.UserFormulaSelection{
		UserID:     userID,
		BabyID:     babyID,
		BrandID:    req.BrandID,
		SeriesName: req.SeriesName,
		AgeRange:   req.AgeRange,
		IsActive:   true,
	}

	if err := h.DB.Create(&selection).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}

	logOperation(h.DB, userID, "create", "formula_selection", selection.ID, nil, selection)
	c.JSON(http.StatusOK, gin.H{"selection": selection})
}

// GetCurrentFormula 获取当前选择的奶粉
func (h *FormulaHandler) GetCurrentFormula(c *gin.Context) {
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

	var selection models.UserFormulaSelection
	// 选择奶粉为“宝宝级配置”，只要找到该宝宝最近一次 active 选择即可
	if err := h.DB.Where("baby_id = ? AND is_active = true", babyID).
		Order("selected_at DESC").
		Preload("Brand").
		First(&selection).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "未选择奶粉"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"selection": selection})
}
