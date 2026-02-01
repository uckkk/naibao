package handlers

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"naibao-backend/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AdminHealthStandardsHandler struct {
	DB *gorm.DB
}

func (h *AdminHealthStandardsHandler) ListVersions(c *gin.Context) {
	type row struct {
		Version     string `json:"version"`
		ActiveCount int    `json:"active_count"`
		TotalCount  int    `json:"total_count"`
	}
	var rows []row

	if err := h.DB.Model(&models.HealthStandard{}).
		Select("version, SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_count, COUNT(*) AS total_count").
		Group("version").
		Order("version DESC").
		Scan(&rows).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	activeVersion := ""
	for _, r := range rows {
		if r.ActiveCount > 0 {
			activeVersion = r.Version
			break
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"active_version": activeVersion,
		"versions":       rows,
	})
}

func (h *AdminHealthStandardsHandler) List(c *gin.Context) {
	version := strings.TrimSpace(c.Query("version"))
	typ := strings.TrimSpace(c.Query("type"))
	active := strings.TrimSpace(c.Query("active"))

	q := h.DB.Model(&models.HealthStandard{})
	if version != "" {
		q = q.Where("version = ?", version)
	}
	if typ != "" {
		q = q.Where("type = ?", typ)
	}
	if active != "" {
		if active == "true" || active == "1" {
			q = q.Where("is_active = true")
		} else if active == "false" || active == "0" {
			q = q.Where("is_active = false")
		}
	}

	var items []models.HealthStandard
	if err := q.Order("version DESC, type ASC, month_min ASC NULLS FIRST, month_max ASC NULLS FIRST, id ASC").
		Find(&items).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"standards": items})
}

type adminHealthStandardInput struct {
	ID       *uint           `json:"id,omitempty"`
	Version  string          `json:"version"`
	Type     string          `json:"type"`
	MonthMin *int            `json:"month_min"`
	MonthMax *int            `json:"month_max"`
	Data     json.RawMessage `json:"data"`
	IsActive *bool           `json:"is_active"`
}

func (h *AdminHealthStandardsHandler) Create(c *gin.Context) {
	raw, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "读取请求失败"})
		return
	}

	var batch struct {
		Standards []adminHealthStandardInput `json:"standards"`
	}
	_ = json.Unmarshal(raw, &batch)

	inputs := batch.Standards
	if len(inputs) == 0 {
		var one adminHealthStandardInput
		if err := json.Unmarshal(raw, &one); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "参数格式错误"})
			return
		}
		inputs = []adminHealthStandardInput{one}
	}

	creator := c.GetUint("userID")
	creatorPtr := (*uint)(nil)
	if creator > 0 {
		creatorPtr = &creator
	}

	// 默认：导入“新版本”时先保持为非激活，避免无意切换线上标准；
	// 若导入的是当前激活版本，则保持 active=true。
	currentActiveVersion := ""
	{
		var row struct{ Version string }
		_ = h.DB.Model(&models.HealthStandard{}).
			Select("version").
			Where("is_active = true").
			Group("version").
			Order("version DESC").
			Limit(1).
			Scan(&row).Error
		currentActiveVersion = strings.TrimSpace(row.Version)
	}

	var created []models.HealthStandard
	for _, in := range inputs {
		version := strings.TrimSpace(in.Version)
		typ := strings.TrimSpace(in.Type)
		if version == "" || typ == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "version/type 必填"})
			return
		}
		if len(in.Data) == 0 || !json.Valid(in.Data) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "data 必须为合法 JSON"})
			return
		}

		active := false
		if in.IsActive != nil {
			active = *in.IsActive
		} else if currentActiveVersion == "" || version == currentActiveVersion {
			active = true
		}

		item := models.HealthStandard{
			Version:   version,
			Type:      typ,
			MonthMin:  in.MonthMin,
			MonthMax:  in.MonthMax,
			Data:      in.Data,
			IsActive:  active,
			CreatedBy: creatorPtr,
		}
		created = append(created, item)
	}

	// 强制写入 is_active（即使为 false），避免数据库默认值（历史为 TRUE）导致“导入新版本意外激活”。
	if err := h.DB.
		Select("Version", "Type", "MonthMin", "MonthMax", "Data", "IsActive", "CreatedBy").
		Create(&created).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"created": created})
}

func (h *AdminHealthStandardsHandler) Update(c *gin.Context) {
	idStr := strings.TrimSpace(c.Param("id"))
	id, err := parseUintSafe(idStr)
	if err != nil || id == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var item models.HealthStandard
	if err := h.DB.Where("id = ?", id).First(&item).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{"error": "记录不存在"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	var req struct {
		Version  *string          `json:"version"`
		Type     *string          `json:"type"`
		MonthMin *int             `json:"month_min"`
		MonthMax *int             `json:"month_max"`
		Data     json.RawMessage  `json:"data"`
		IsActive *bool            `json:"is_active"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	updates := map[string]interface{}{}
	if req.Version != nil {
		v := strings.TrimSpace(*req.Version)
		if v == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "version 不能为空"})
			return
		}
		updates["version"] = v
	}
	if req.Type != nil {
		t := strings.TrimSpace(*req.Type)
		if t == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "type 不能为空"})
			return
		}
		updates["type"] = t
	}
	if req.MonthMin != nil {
		updates["month_min"] = req.MonthMin
	}
	if req.MonthMax != nil {
		updates["month_max"] = req.MonthMax
	}
	if req.IsActive != nil {
		updates["is_active"] = *req.IsActive
	}
	if len(req.Data) > 0 {
		if !json.Valid(req.Data) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "data 必须为合法 JSON"})
			return
		}
		updates["data"] = req.Data
	}

	if len(updates) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无可更新字段"})
		return
	}

	if err := h.DB.Model(&item).Updates(updates).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新失败"})
		return
	}

	// 重新读取，返回更新后结果
	_ = h.DB.Where("id = ?", id).First(&item).Error
	c.JSON(http.StatusOK, gin.H{"standard": item})
}

func (h *AdminHealthStandardsHandler) ActivateVersion(c *gin.Context) {
	var req struct {
		Version string `json:"version" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	version := strings.TrimSpace(req.Version)
	if version == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "version 不能为空"})
		return
	}

	var count int64
	if err := h.DB.Model(&models.HealthStandard{}).Where("version = ?", version).Count(&count).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	if count == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "该版本不存在"})
		return
	}

	if err := h.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Model(&models.HealthStandard{}).Where("version <> ?", version).Update("is_active", false).Error; err != nil {
			return err
		}
		if err := tx.Model(&models.HealthStandard{}).Where("version = ?", version).Update("is_active", true).Error; err != nil {
			return err
		}
		return nil
	}); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "启用失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "启用成功", "version": version})
}
