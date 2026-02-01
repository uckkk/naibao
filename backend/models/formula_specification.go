package models

import "time"

type FormulaSpecification struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	BrandID   uint      `gorm:"not null;index" json:"brand_id"`
	SeriesName string   `json:"series_name"`
	AgeRange  string    `json:"age_range"`

	ScoopWeightGram float64 `gorm:"type:decimal(5,2)" json:"scoop_weight_gram"`
	ScoopML         float64 `gorm:"type:decimal(5,2)" json:"scoop_ml"`

	WaterTempMin *int   `json:"water_temp_min"`
	WaterTempMax *int   `json:"water_temp_max"`
	MixingMethod string `json:"mixing_method"`

	FeedingFrequency string `json:"feeding_frequency"`
	DailyAmountMin   *int   `json:"daily_amount_min"`
	DailyAmountMax   *int   `json:"daily_amount_max"`

	DataSource  string     `json:"data_source"`
	VerifiedAt  *time.Time `json:"verified_at"`
	IsVerified  bool       `gorm:"default:false" json:"is_verified"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`

	Brand FormulaBrand `gorm:"foreignKey:BrandID" json:"brand,omitempty"`
}

