package models

import (
	"encoding/json"
	"time"
)

// HealthStandard 对应数据库表 health_standards，用于存储“卫健委/WHO 等标准”的版本化配置。
// 说明：month_min/month_max 允许为 NULL，用于表达“按月龄分段”的区间。
type HealthStandard struct {
	ID       uint   `gorm:"primarykey" json:"id"`
	Version  string `gorm:"size:20;not null;index" json:"version"`
	Type     string `gorm:"size:50;not null;index" json:"type"`
	MonthMin *int   `json:"month_min"`
	MonthMax *int   `json:"month_max"`
	Data     json.RawMessage `gorm:"type:jsonb;not null" json:"data"`

	// 默认不激活：避免导入新版本时意外切换线上口径；启用由管理员显式操作完成。
	IsActive  bool  `gorm:"default:false" json:"is_active"`
	CreatedBy *uint `json:"created_by,omitempty"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
