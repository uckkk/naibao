package models

import (
	"time"

	"github.com/lib/pq"
)

type FormulaBrand struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	NameCN      string    `gorm:"not null" json:"name_cn"`
	NameEN      string    `json:"name_en"`
	LogoURL     string    `json:"logo_url"`
	MarketShare *float64  `gorm:"type:decimal(5,2)" json:"market_share"`
	Features    pq.StringArray `gorm:"type:text[]" json:"features"`
	OfficialURL string    `json:"official_url"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type UserFormulaSelection struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	UserID      uint      `gorm:"not null;uniqueIndex:idx_user_baby" json:"user_id"`
	BabyID      uint      `gorm:"not null;uniqueIndex:idx_user_baby" json:"baby_id"`
	BrandID     uint      `gorm:"not null" json:"brand_id"`
	SeriesName  string    `json:"series_name"`
	AgeRange    string    `json:"age_range"`
	SelectedAt  time.Time `json:"selected_at"`
	IsActive    bool      `gorm:"default:true" json:"is_active"`
	
	Brand       FormulaBrand `gorm:"foreignKey:BrandID" json:"brand,omitempty"`
}
