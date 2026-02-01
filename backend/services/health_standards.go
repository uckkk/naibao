package services

import (
	"encoding/json"
	"errors"
	"fmt"
	"naibao-backend/models"
	"strconv"
	"strings"

	"gorm.io/gorm"
)

// health_standards 表的 data 字段常用结构：{min,max,recommended,unit}
type standardRangeData struct {
	Min         json.Number `json:"min"`
	Max         json.Number `json:"max"`
	Recommended json.Number `json:"recommended"`
	Unit        string      `json:"unit"`
}

func getActiveStandardsVersion(db *gorm.DB) (string, error) {
	if db == nil {
		return "", errors.New("nil db")
	}

	var row struct{ Version string }
	// 约定：active 版本由 health_standards.is_active 决定；若存在多版本同时 active，则取版本号最大的。
	if err := db.Model(&models.HealthStandard{}).
		Select("version").
		Where("is_active = true").
		Group("version").
		Order("version DESC").
		Limit(1).
		Scan(&row).Error; err != nil {
		return "", err
	}
	if strings.TrimSpace(row.Version) == "" {
		return "", gorm.ErrRecordNotFound
	}
	return row.Version, nil
}

func loadActiveStandardsByType(db *gorm.DB, typ string) (string, []models.HealthStandard, error) {
	version, err := getActiveStandardsVersion(db)
	if err != nil {
		return "", nil, err
	}

	var items []models.HealthStandard
	if err := db.
		Where("version = ? AND type = ? AND is_active = true", version, typ).
		Order("month_min ASC NULLS FIRST, month_max ASC NULLS FIRST, id ASC").
		Find(&items).Error; err != nil {
		return "", nil, err
	}
	if len(items) == 0 {
		return version, nil, gorm.ErrRecordNotFound
	}
	return version, items, nil
}

func parseRangeData(raw json.RawMessage) (min, max, recommended float64, unit string, ok bool) {
	if len(raw) == 0 || !json.Valid(raw) {
		return 0, 0, 0, "", false
	}

	var d standardRangeData
	if err := json.Unmarshal(raw, &d); err != nil {
		return 0, 0, 0, "", false
	}
	unit = strings.TrimSpace(d.Unit)

	if d.Min != "" {
		if v, err := d.Min.Float64(); err == nil {
			min = v
		}
	}
	if d.Max != "" {
		if v, err := d.Max.Float64(); err == nil {
			max = v
		}
	}
	if d.Recommended != "" {
		if v, err := d.Recommended.Float64(); err == nil {
			recommended = v
		}
	}
	return min, max, recommended, unit, true
}

func pickByAgeRange(items []models.HealthStandard, ageMonths float64) *models.HealthStandard {
	if len(items) == 0 {
		return nil
	}
	if ageMonths < 0 {
		ageMonths = 0
	}

	// items 已按 month_min ASC 排序：优先命中更精确的段位。
	for i := range items {
		minOK := true
		maxOK := true
		if items[i].MonthMin != nil {
			minOK = ageMonths >= float64(*items[i].MonthMin)
		}
		// 约定：month_max 为右开区间上界（避免边界月龄重叠）。
		if items[i].MonthMax != nil {
			maxOK = ageMonths < float64(*items[i].MonthMax)
		}
		if minOK && maxOK {
			return &items[i]
		}
	}

	// 未命中（如大于最大月龄）：回退到最后一个分段
	return &items[len(items)-1]
}

func formatRangeText(min, max float64, unit string) string {
	u := strings.TrimSpace(unit)
	if strings.Contains(u, "ml/day") {
		return fmt.Sprintf("%d-%dml/天", int(min+0.5), int(max+0.5))
	}
	if strings.Contains(u, "mm/day") {
		return fmt.Sprintf("%s-%smm/天", trimFloat(min), trimFloat(max))
	}
	if strings.Contains(u, "kg/day") {
		return fmt.Sprintf("%s-%skg/天", trimFloat(min), trimFloat(max))
	}
	if u != "" {
		return fmt.Sprintf("%s-%s%s", trimFloat(min), trimFloat(max), u)
	}
	return fmt.Sprintf("%s-%s", trimFloat(min), trimFloat(max))
}

func trimFloat(v float64) string {
	// 以最短形式输出（避免 0.030000）
	return strconv.FormatFloat(v, 'f', -1, 64)
}

// LookupMilkByWeightCoefficient 从 health_standards 获取“按体重奶量”推荐系数（ml/kg/day 的 recommended）。
// 若缺失或解析失败，返回 fallback。
func LookupMilkByWeightCoefficient(db *gorm.DB, fallback float64) (coef float64, ok bool) {
	_, items, err := loadActiveStandardsByType(db, "milk_by_weight")
	if err != nil || len(items) == 0 {
		return fallback, false
	}

	_, _, recommended, _, parsed := parseRangeData(items[0].Data)
	if !parsed || recommended <= 0 {
		return fallback, false
	}
	return recommended, true
}

// LookupMilkByAgeReferenceText 返回当前 active 版本下，按月龄分段的奶量参考范围文案。
func LookupMilkByAgeReferenceText(db *gorm.DB, ageMonths float64) (text string, ok bool) {
	_, items, err := loadActiveStandardsByType(db, "milk_by_age")
	if err != nil {
		return "", false
	}
	hit := pickByAgeRange(items, ageMonths)
	if hit == nil {
		return "", false
	}
	min, max, _, unit, parsed := parseRangeData(hit.Data)
	if !parsed {
		return "", false
	}
	return formatRangeText(min, max, unit), true
}

func LookupWeightGainReferenceText(db *gorm.DB, ageMonths float64) (text string, ok bool) {
	_, items, err := loadActiveStandardsByType(db, "weight_gain")
	if err != nil {
		return "", false
	}
	hit := pickByAgeRange(items, ageMonths)
	if hit == nil {
		return "", false
	}
	min, max, _, unit, parsed := parseRangeData(hit.Data)
	if !parsed {
		return "", false
	}
	return formatRangeText(min, max, unit), true
}

func LookupHeightGainReferenceText(db *gorm.DB, ageMonths float64) (text string, ok bool) {
	_, items, err := loadActiveStandardsByType(db, "height_gain")
	if err != nil {
		return "", false
	}
	hit := pickByAgeRange(items, ageMonths)
	if hit == nil {
		return "", false
	}
	min, max, _, unit, parsed := parseRangeData(hit.Data)
	if !parsed {
		return "", false
	}
	return formatRangeText(min, max, unit), true
}

