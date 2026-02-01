package models

import (
	"time"
)

type FeedingSettings struct {
	ID              uint      `gorm:"primarykey" json:"id"`
	BabyID         uint      `gorm:"not null;uniqueIndex" json:"baby_id"`
	UserID         uint      `gorm:"not null;index" json:"user_id"`
	DayInterval    int       `gorm:"default:3" json:"day_interval"`        // 白天间隔（小时）
	NightInterval  int       `gorm:"default:5" json:"night_interval"`     // 晚上间隔（小时）
	ReminderEnabled bool     `gorm:"default:true" json:"reminder_enabled"` // 提醒开关
	AdvanceMinutes int       `gorm:"default:15" json:"advance_minutes"`    // 提前提醒分钟数
	DayStartHour   int       `gorm:"default:6" json:"day_start_hour"`      // 白天开始时间（默认6点）
	DayEndHour     int       `gorm:"default:18" json:"day_end_hour"`       // 白天结束时间（默认18点）
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

