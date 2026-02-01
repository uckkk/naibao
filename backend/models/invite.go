package models

import "time"

type InviteCode struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	Code      string    `gorm:"size:6;uniqueIndex;not null" json:"code"`
	BabyID    uint      `gorm:"not null" json:"baby_id"`
	CreatorID uint      `gorm:"not null" json:"creator_id"`

	ExpiresAt time.Time `json:"expires_at"`
	Used      bool      `gorm:"default:false" json:"used"`
	UsedBy    *uint     `json:"used_by"`
	UsedAt    *time.Time `json:"used_at"`
	CreatedAt time.Time `json:"created_at"`
}

