package models

import (
	"encoding/json"
	"time"
)

// OperationLog 用于审计：记录关键数据的增删改，便于“误操作可追溯/可解释”。
type OperationLog struct {
	ID         uint            `gorm:"primarykey" json:"id"`
	UserID     uint            `gorm:"not null;index" json:"user_id"`
	Action     string          `gorm:"size:50;not null" json:"action"`       // create/update/delete
	EntityType string          `gorm:"size:50;not null" json:"entity_type"`  // feeding/growth/baby...
	EntityID   uint            `gorm:"not null" json:"entity_id"`
	BeforeData json.RawMessage `gorm:"type:jsonb" json:"before_data,omitempty"`
	AfterData  json.RawMessage `gorm:"type:jsonb" json:"after_data,omitempty"`
	CreatedAt  time.Time       `json:"created_at"`
}
