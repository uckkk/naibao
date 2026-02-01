package handlers

import (
	"errors"
	"net/http"
	"naibao-backend/models"
	"time"
	
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type BabyHandler struct {
	DB *gorm.DB
}

func NewBabyHandler(db *gorm.DB) *BabyHandler {
	return &BabyHandler{DB: db}
}

type CreateBabyRequest struct {
	Nickname  string `json:"nickname" binding:"required"`
	AvatarURL string `json:"avatar_url"`
	BirthDate string `json:"birth_date" binding:"required"`
	BirthTime string `json:"birth_time" binding:"required"`
	Gender    string `json:"gender"`
	// 可选：创建时同时写入当天的生长记录（用于首页/数据页展示“当前身高体重”）
	CurrentWeight *float64 `json:"current_weight"`
	CurrentHeight *int     `json:"current_height"`
}

type UpdateBabyRequest struct {
	Nickname  string `json:"nickname"`
	AvatarURL string `json:"avatar_url"`
	BirthDate string `json:"birth_date"`
	BirthTime string `json:"birth_time"`
	Gender    string `json:"gender"`
	// 可选：更新时同时写入当天的生长记录
	CurrentWeight *float64 `json:"current_weight"`
	CurrentHeight *int     `json:"current_height"`
}

// CreateBaby 创建宝宝
func (h *BabyHandler) CreateBaby(c *gin.Context) {
	userID := c.GetUint("userID")
	
	var req CreateBabyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	birthDate, err := time.Parse("2006-01-02", req.BirthDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "出生日期格式错误，应为 YYYY-MM-DD"})
		return
	}
	
	baby := models.Baby{
		UserID:    userID,
		Nickname:  req.Nickname,
		AvatarURL: req.AvatarURL,
		BirthDate: birthDate,
		BirthTime: req.BirthTime,
		Gender:    req.Gender,
	}

	// 确保“宝宝”与“家庭成员(owner/admin)”一致写入，避免后续接口鉴权失败
	if err := h.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(&baby).Error; err != nil {
			return err
		}
		member := models.FamilyMember{
			BabyID:   baby.ID,
			UserID:   userID,
			Role:     "admin",
			JoinedAt: time.Now(),
		}
		if err := tx.Create(&member).Error; err != nil {
			return err
		}

		logOperation(tx, userID, "create", "baby", baby.ID, nil, baby)

		// 可选：把“当前身高体重”落到 growth_records（当天）
		if req.CurrentWeight != nil || req.CurrentHeight != nil {
			record, created, before, err := upsertGrowthRecordForDate(tx, baby.ID, todayDate(), req.CurrentWeight, req.CurrentHeight)
			if err != nil {
				return err
			}
			if created {
				logOperation(tx, userID, "create", "growth", record.ID, nil, record)
			} else {
				logOperation(tx, userID, "update", "growth", record.ID, before, record)
			}
		}

		return nil
	}); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}
	
	baby.CalculateAge()
	fillBabyCurrentGrowth(h.DB, &baby)
	c.JSON(http.StatusOK, gin.H{"baby": baby})
}

// GetBabies 获取宝宝列表
func (h *BabyHandler) GetBabies(c *gin.Context) {
	userID := c.GetUint("userID")
	
	var babies []models.Baby
	// 支持家庭协作：我创建的宝宝 + 我作为成员加入的宝宝
	if err := h.DB.Model(&models.Baby{}).
		Distinct("babies.*").
		Joins("LEFT JOIN family_members fm ON fm.baby_id = babies.id").
		Where("babies.user_id = ? OR fm.user_id = ?", userID, userID).
		Find(&babies).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	
	// 计算年龄
	for i := range babies {
		babies[i].CalculateAge()
		fillBabyCurrentGrowth(h.DB, &babies[i])
	}
	
	c.JSON(http.StatusOK, gin.H{"babies": babies})
}

// GetBaby 获取单个宝宝信息
func (h *BabyHandler) GetBaby(c *gin.Context) {
	userID := c.GetUint("userID")
	babyIDStr := c.Param("id")
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

	// 鉴权：成员可查看
	if _, err := ensureBabyMember(h.DB, &baby, userID); err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	
	baby.CalculateAge()
	fillBabyCurrentGrowth(h.DB, &baby)
	c.JSON(http.StatusOK, gin.H{"baby": baby})
}

// UpdateBaby 更新宝宝信息
func (h *BabyHandler) UpdateBaby(c *gin.Context) {
	userID := c.GetUint("userID")
	babyIDStr := c.Param("id")
	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}
	
	var req UpdateBabyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	var baby models.Baby
	if err := h.DB.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}

	// 只有管理员可更新宝宝基础信息（避免成员误改全局信息）
	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	if member.Role != "admin" {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可编辑宝宝信息"})
		return
	}

	before := baby
	
	// 更新字段
	if req.Nickname != "" {
		baby.Nickname = req.Nickname
	}
	if req.AvatarURL != "" {
		baby.AvatarURL = req.AvatarURL
	}
	if req.BirthDate != "" {
		birthDate, err := time.Parse("2006-01-02", req.BirthDate)
		if err == nil {
			baby.BirthDate = birthDate
		}
	}
	if req.BirthTime != "" {
		baby.BirthTime = req.BirthTime
	}
	if req.Gender != "" {
		baby.Gender = req.Gender
	}

	if err := h.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Save(&baby).Error; err != nil {
			return err
		}
		if req.CurrentWeight != nil || req.CurrentHeight != nil {
			record, created, beforeGrowth, err := upsertGrowthRecordForDate(tx, baby.ID, todayDate(), req.CurrentWeight, req.CurrentHeight)
			if err != nil {
				return err
			}
			if created {
				logOperation(tx, userID, "create", "growth", record.ID, nil, record)
			} else {
				logOperation(tx, userID, "update", "growth", record.ID, beforeGrowth, record)
			}
		}
		logOperation(tx, userID, "update", "baby", baby.ID, before, baby)
		return nil
	}); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}
	
	baby.CalculateAge()
	fillBabyCurrentGrowth(h.DB, &baby)
	c.JSON(http.StatusOK, gin.H{"baby": baby})
}

// DeleteBaby 删除宝宝
func (h *BabyHandler) DeleteBaby(c *gin.Context) {
	userID := c.GetUint("userID")
	babyIDStr := c.Param("id")
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

	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}
	if member.Role != "admin" {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可删除宝宝"})
		return
	}

	if err := h.DB.Where("id = ?", babyID).Delete(&models.Baby{}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败"})
		return
	}

	logOperation(h.DB, userID, "delete", "baby", baby.ID, baby, nil)
	
	c.JSON(http.StatusOK, gin.H{"message": "删除成功"})
}

func todayDate() time.Time {
	now := time.Now()
	return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.Local)
}

func fillBabyCurrentGrowth(db *gorm.DB, baby *models.Baby) {
	if baby == nil || baby.ID == 0 {
		return
	}

	var latest models.GrowthRecord
	if err := db.Where("baby_id = ?", baby.ID).
		Order("record_date DESC").
		First(&latest).Error; err != nil {
		return
	}

	if latest.Weight != nil {
		baby.CurrentWeight = *latest.Weight
	}
	if latest.Height != nil {
		baby.CurrentHeight = *latest.Height
	}
}

func upsertGrowthRecordForDate(tx *gorm.DB, babyID uint, recordDate time.Time, weight *float64, height *int) (models.GrowthRecord, bool, *models.GrowthRecord, error) {
	var existing models.GrowthRecord
	err := tx.Where("baby_id = ? AND record_date = ?", babyID, recordDate).First(&existing).Error
	if err == nil {
		before := existing
		if weight != nil {
			w := *weight
			existing.Weight = &w
		}
		if height != nil {
			h := *height
			existing.Height = &h
		}
		if err := tx.Save(&existing).Error; err != nil {
			return models.GrowthRecord{}, false, nil, err
		}
		return existing, false, &before, nil
	}

	if !errors.Is(err, gorm.ErrRecordNotFound) {
		return models.GrowthRecord{}, false, nil, err
	}

	record := models.GrowthRecord{
		BabyID:     babyID,
		RecordDate: recordDate,
	}
	if weight != nil {
		w := *weight
		record.Weight = &w
	}
	if height != nil {
		h := *height
		record.Height = &h
	}
	if err := tx.Create(&record).Error; err != nil {
		return models.GrowthRecord{}, false, nil, err
	}
	return record, true, nil, nil
}
