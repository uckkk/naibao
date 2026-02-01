package models

import "time"

// UserPreference 记录用户在某个宝宝上的“投喂输入偏好”，用于降低高频操作成本。
// 对应表：user_preferences（注意：该表没有 created_at，仅有 updated_at）。
type UserPreference struct {
	ID uint `gorm:"primarykey" json:"id"`

	UserID uint `gorm:"not null;index;uniqueIndex:idx_user_baby" json:"user_id"`
	BabyID uint `gorm:"not null;index;uniqueIndex:idx_user_baby" json:"baby_id"`

	DefaultAmount    *int   `json:"default_amount,omitempty"` // 常用单次奶量（ml）
	AdjustmentPattern int    `gorm:"default:0" json:"adjustment_pattern"` // 习惯性相对推荐量的调整（ml，可正可负）
	InputMethod      string `gorm:"size:20" json:"input_method"`          // direct/quick/manual

	UpdatedAt time.Time `json:"updated_at"`
}

