package models

import "time"

// WeaningPlan represents a formula transition ("转奶") plan for a baby.
// Product principle: the server stores user data/state only; calculation/UX is done on the client.
//
// Status:
// - active: running
// - paused: temporarily stopped
// - ended: manually ended (or replaced by a newer plan)
type WeaningPlan struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	BabyID    uint      `gorm:"not null;index" json:"baby_id"`
	CreatedBy uint      `gorm:"not null" json:"created_by"`

	Mode         string `gorm:"type:varchar(20);default:'alternate'" json:"mode"` // alternate (MVP), mix (future)
	DurationDays int    `gorm:"default:7" json:"duration_days"`

	OldBrandID     uint   `gorm:"not null" json:"old_brand_id"`
	OldSeriesName  string `json:"old_series_name"`
	OldAgeRange    string `json:"old_age_range"`
	NewBrandID     uint   `gorm:"not null" json:"new_brand_id"`
	NewSeriesName  string `json:"new_series_name"`
	NewAgeRange    string `json:"new_age_range"`

	StartAt  time.Time  `gorm:"not null" json:"start_at"`
	PausedAt *time.Time `json:"paused_at,omitempty"`
	EndedAt  *time.Time `json:"ended_at,omitempty"`
	Status   string     `gorm:"type:varchar(20);default:'active';index" json:"status"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`

	OldBrand FormulaBrand `gorm:"foreignKey:OldBrandID" json:"old_brand,omitempty"`
	NewBrand FormulaBrand `gorm:"foreignKey:NewBrandID" json:"new_brand,omitempty"`
}

