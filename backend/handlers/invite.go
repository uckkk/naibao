package handlers

import (
	"crypto/rand"
	"errors"
	"fmt"
	"math/big"
	"naibao-backend/models"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type InviteHandler struct {
	DB *gorm.DB
}

func randomInviteCode6() (string, error) {
	// 6 位数字：100000-999999
	n, err := rand.Int(rand.Reader, big.NewInt(900000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()+100000), nil
}

// Generate 生成邀请码（仅管理员）
func (h *InviteHandler) Generate(c *gin.Context) {
	userID := c.GetUint("userID")

	var req struct {
		BabyID uint `json:"baby_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.BabyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "baby_id is required"})
		return
	}

	var baby models.Baby
	if err := h.DB.Where("id = ?", req.BabyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}

	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "生成失败"})
		return
	}
	if !isAdmin(member) {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可生成邀请码"})
		return
	}

	now := time.Now()

	// 优先复用未过期且未使用的邀请码，减少用户困惑
	var existing models.InviteCode
	if err := h.DB.Where("baby_id = ? AND creator_id = ? AND used = false AND expires_at > ?", req.BabyID, userID, now).
		Order("created_at DESC").
		First(&existing).Error; err == nil {
		c.JSON(http.StatusOK, gin.H{
			"code":       existing.Code,
			"expires_at": existing.ExpiresAt.Format(time.RFC3339),
		})
		return
	}

	// 生成新邀请码（最多重试几次避免偶发碰撞）
	var invite models.InviteCode
	var lastErr error
	for i := 0; i < 5; i++ {
		code, err := randomInviteCode6()
		if err != nil {
			lastErr = err
			continue
		}
		invite = models.InviteCode{
			Code:      code,
			BabyID:    req.BabyID,
			CreatorID: userID,
			ExpiresAt: now.Add(7 * 24 * time.Hour),
			Used:      false,
		}
		if err := h.DB.Create(&invite).Error; err != nil {
			lastErr = err
			continue
		}
		logOperation(h.DB, userID, "create", "invite_code", invite.ID, nil, invite)

		c.JSON(http.StatusOK, gin.H{
			"code":       invite.Code,
			"expires_at": invite.ExpiresAt.Format(time.RFC3339),
		})
		return
	}

	_ = lastErr
	c.JSON(http.StatusInternalServerError, gin.H{"error": "生成失败"})
}

// Use 使用邀请码加入家庭
func (h *InviteHandler) Use(c *gin.Context) {
	userID := c.GetUint("userID")

	var req struct {
		Code string `json:"code" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "code is required"})
		return
	}
	code := strings.TrimSpace(req.Code)
	if len(code) != 6 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "邀请码格式错误"})
		return
	}

	now := time.Now()

	var baby models.Baby
	if err := h.DB.Transaction(func(tx *gorm.DB) error {
		var invite models.InviteCode
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).
			Where("code = ?", code).
			First(&invite).Error; err != nil {
			return err
		}
		beforeInvite := invite
		if invite.Used {
			return fmt.Errorf("邀请码已使用")
		}
		if !invite.ExpiresAt.After(now) {
			return fmt.Errorf("邀请码已过期")
		}

		// 读取宝宝信息（用于返回）
		if err := tx.Where("id = ?", invite.BabyID).First(&baby).Error; err != nil {
			return err
		}

		// 已经是成员：直接成功返回（幂等）
		var existing models.FamilyMember
		if err := tx.Where("baby_id = ? AND user_id = ?", invite.BabyID, userID).First(&existing).Error; err == nil {
			return nil
		} else if !errors.Is(err, gorm.ErrRecordNotFound) {
			return err
		}

		member := models.FamilyMember{
			BabyID:   invite.BabyID,
			UserID:   userID,
			Role:     "member",
			JoinedAt: now,
		}
		if err := tx.Create(&member).Error; err != nil {
			return err
		}
		logOperation(tx, userID, "create", "family_member", member.ID, nil, member)

		usedAt := now
		invite.Used = true
		invite.UsedBy = &userID
		invite.UsedAt = &usedAt
		if err := tx.Save(&invite).Error; err != nil {
			return err
		}
		logOperation(tx, userID, "update", "invite_code", invite.ID, beforeInvite, invite)
		return nil
	}); err != nil {
		// 区分“可预期错误”与系统错误
		msg := err.Error()
		if strings.Contains(msg, "record not found") {
			c.JSON(http.StatusNotFound, gin.H{"error": "邀请码不存在"})
			return
		}
		if strings.Contains(msg, "邀请码已使用") || strings.Contains(msg, "邀请码已过期") || strings.Contains(msg, "邀请码格式错误") {
			c.JSON(http.StatusBadRequest, gin.H{"error": msg})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "加入失败"})
		return
	}

	// 返回宝宝信息，方便前端直接切换到该宝宝
	baby.CalculateAge()
	fillBabyCurrentGrowth(h.DB, &baby)

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"baby":    baby,
		"message": "已成功加入家庭",
	})
}
