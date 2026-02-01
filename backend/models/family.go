package models

import (
	"time"
)

type FamilyMember struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	BabyID    uint      `gorm:"not null;uniqueIndex:idx_baby_user" json:"baby_id"`
	UserID    uint      `gorm:"not null;uniqueIndex:idx_baby_user" json:"user_id"`
	Role      string    `gorm:"default:'member'" json:"role"` // 'admin', 'member', 'guest'
	JoinedAt  time.Time `json:"joined_at"`
	
	User      User      `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

