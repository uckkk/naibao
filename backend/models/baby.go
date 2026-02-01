package models

import (
	"time"
)

type Baby struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	UserID    uint      `gorm:"not null;index" json:"user_id"`
	Nickname  string    `gorm:"not null" json:"nickname"`
	AvatarURL string    `json:"avatar_url"`
	BirthDate time.Time `gorm:"type:date;not null" json:"birth_date"`
	BirthTime string    `gorm:"type:time;not null" json:"birth_time"`
	Gender    string    `json:"gender"` // 'male' or 'female'
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	
	// 计算字段
	AgeInDays int `gorm:"-" json:"age_in_days,omitempty"`
	AgeInMonths float64 `gorm:"-" json:"age_in_months,omitempty"`
	CurrentWeight float64 `gorm:"-" json:"current_weight,omitempty"`
	CurrentHeight int `gorm:"-" json:"current_height,omitempty"`
}

func (b *Baby) CalculateAge() {
	if !b.BirthDate.IsZero() {
		now := time.Now()
		duration := now.Sub(b.BirthDate)
		b.AgeInDays = int(duration.Hours() / 24)
		b.AgeInMonths = float64(b.AgeInDays) / 30.0
	}
}

