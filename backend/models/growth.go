package models

import (
	"time"
)

type GrowthRecord struct {
	ID              uint      `gorm:"primarykey" json:"id"`
	BabyID          uint      `gorm:"not null;index" json:"baby_id"`
	RecordDate      time.Time `gorm:"type:date;not null;uniqueIndex:idx_baby_date" json:"record_date"`
	Weight          *float64  `json:"weight"`          // 体重（kg）
	Height          *int      `json:"height"`          // 身高（cm）
	DailyMilkAmount *int      `json:"daily_milk_amount"` // 日总奶量（ml）
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

type GrowthStat struct {
	DailyWeightGain float64 `json:"daily_weight_gain"` // 日均增重（kg/天）
	DailyHeightGain float64 `json:"daily_height_gain"` // 日均增高（mm/天）
	DailyMilkAvg    int     `json:"daily_milk_avg"`    // 日均奶量（ml）
	CurrentWeight   float64 `json:"current_weight"`    // 当前体重
	CurrentHeight   int     `json:"current_height"`    // 当前身高
}

