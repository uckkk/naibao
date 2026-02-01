package models

import (
	"time"
)

type Feeding struct {
	ID              uint      `gorm:"primarykey" json:"id"`
	BabyID          uint      `gorm:"not null;index" json:"baby_id"`
	UserID          uint      `gorm:"not null;index" json:"user_id"`
	Amount          int       `gorm:"not null" json:"amount"` // 奶量（ml）
	FeedingTime     time.Time `gorm:"not null;index" json:"feeding_time"`
	FormulaBrandID  *uint     `json:"formula_brand_id"`
	FormulaSeriesName string  `json:"formula_series_name"`
	Scoops          *int      `json:"scoops"` // 勺数
	DeviceID        string    `json:"device_id"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

type FeedingStat struct {
	TotalAmount    int     `json:"total_amount"`     // 总奶量
	DailyAmount    int     `json:"daily_amount"`     // 日均奶量
	TodayAmount    int     `json:"today_amount"`     // 今日奶量
	RemainingTimes int     `json:"remaining_times"` // 剩余喂养次数
	NextFeedingTime *time.Time `json:"next_feeding_time"` // 下次喂奶时间
}

