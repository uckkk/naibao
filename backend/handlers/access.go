package handlers

import (
	"errors"
	"naibao-backend/models"
	"time"

	"gorm.io/gorm"
)

var errForbidden = errors.New("forbidden")

// ensureBabyMember returns the caller's membership for the baby.
// - If membership exists: return it.
// - If membership missing but caller is baby owner: best-effort backfill admin membership.
// - Otherwise: errForbidden.
func ensureBabyMember(db *gorm.DB, baby *models.Baby, userID uint) (models.FamilyMember, error) {
	var member models.FamilyMember
	if baby == nil || baby.ID == 0 {
		return member, errors.New("invalid baby")
	}

	if err := db.Where("baby_id = ? AND user_id = ?", baby.ID, userID).First(&member).Error; err == nil {
		return member, nil
	} else if errors.Is(err, gorm.ErrRecordNotFound) {
		if baby.UserID != userID {
			return member, errForbidden
		}

		// Backfill for legacy data: old records may not have family_members rows.
		member = models.FamilyMember{
			BabyID:   baby.ID,
			UserID:   userID,
			Role:     "admin",
			JoinedAt: time.Now(),
		}
		_ = db.Create(&member).Error
		member.Role = "admin"
		return member, nil
	} else {
		return member, err
	}
}

func isAdmin(member models.FamilyMember) bool {
	return member.Role == "admin"
}

