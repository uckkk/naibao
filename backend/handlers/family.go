package handlers

import (
	"errors"
	"naibao-backend/models"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FamilyHandler struct {
	DB *gorm.DB
}

// GetFamilyMembers 获取家庭成员列表
func (h *FamilyHandler) GetFamilyMembers(c *gin.Context) {
	babyIDStr := c.Param("id")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	// 验证权限（用户必须是该宝宝的成员；兼容 owner-only 旧数据）
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

	// 获取所有家庭成员
	var members []models.FamilyMember
	h.DB.Where("baby_id = ?", babyID).
		Preload("User").
		Find(&members)

	// 格式化返回数据
	type MemberInfo struct {
		UserID   uint   `json:"user_id"`
		Nickname string `json:"nickname"`
		AvatarURL string `json:"avatar_url"`
		Role     string `json:"role"`
	}

	var memberInfos []MemberInfo
	for _, m := range members {
		memberInfos = append(memberInfos, MemberInfo{
			UserID:    m.UserID,
			Nickname:  m.User.Nickname,
			AvatarURL: m.User.AvatarURL,
			Role:      m.Role,
		})
	}

	c.JSON(http.StatusOK, gin.H{"members": memberInfos})
}

// RemoveFamilyMember 移除家庭成员（仅管理员）
func (h *FamilyHandler) RemoveFamilyMember(c *gin.Context) {
	babyIDStr := c.Param("id")
	targetUserIDStr := c.Param("userId")
	userID := c.GetUint("userID")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}
	targetUserID, err := parseUintSafe(targetUserIDStr)
	if err != nil || targetUserID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
		return
	}
	if targetUserID == userID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "不能移除自己"})
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
		c.JSON(http.StatusInternalServerError, gin.H{"error": "移除失败"})
		return
	}
	if !isAdmin(member) {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可移除成员"})
		return
	}

	var target models.FamilyMember
	err = h.DB.Where("baby_id = ? AND user_id = ?", babyID, targetUserID).First(&target).Error
	if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "移除失败"})
		return
	}

	if err := h.DB.Where("baby_id = ? AND user_id = ?", babyID, targetUserID).
		Delete(&models.FamilyMember{}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "移除失败"})
		return
	}

	if target.ID != 0 {
		logOperation(h.DB, userID, "delete", "family_member", target.ID, target, nil)
	}

	c.JSON(http.StatusOK, gin.H{"message": "移除成功"})
}
