package handlers

import (
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"naibao-backend/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type ReportHandler struct {
	DB *gorm.DB
}

type babyReportDay struct {
	Date          string   `json:"date"`
	FeedingsCount int      `json:"feedings_count"`
	TotalAmount   int      `json:"total_amount"` // ml
	Weight        *float64 `json:"weight,omitempty"`
	Height        *int     `json:"height,omitempty"`
}

// GetBabyReport 导出指定宝宝在某一日期范围内的数据摘要。
// - 默认范围：最近 30 天（含今天）
// - query: from=YYYY-MM-DD, to=YYYY-MM-DD, format=json|csv
func (h *ReportHandler) GetBabyReport(c *gin.Context) {
	userID := c.GetUint("userID")
	babyID, err := parseUintSafe(strings.TrimSpace(c.Param("id")))
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var baby models.Baby
	if err := h.DB.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}
	if _, err := ensureBabyMember(h.DB, &baby, userID); err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}

	now := time.Now()
	toDate := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.Local)
	fromDate := toDate.AddDate(0, 0, -29)

	if s := strings.TrimSpace(c.Query("to")); s != "" {
		d, err := time.ParseInLocation("2006-01-02", s, time.Local)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "to 格式错误，应为 YYYY-MM-DD"})
			return
		}
		toDate = time.Date(d.Year(), d.Month(), d.Day(), 0, 0, 0, 0, time.Local)
	}
	if s := strings.TrimSpace(c.Query("from")); s != "" {
		d, err := time.ParseInLocation("2006-01-02", s, time.Local)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "from 格式错误，应为 YYYY-MM-DD"})
			return
		}
		fromDate = time.Date(d.Year(), d.Month(), d.Day(), 0, 0, 0, 0, time.Local)
	}
	if fromDate.After(toDate) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "from 不能晚于 to"})
		return
	}
	// 保护：避免一次导出过大范围
	if days := int(toDate.Sub(fromDate).Hours()/24) + 1; days > 366 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "导出范围过大（最多 366 天）"})
		return
	}

	start := fromDate
	endExclusive := toDate.AddDate(0, 0, 1)

	// feedings
	var feedings []models.Feeding
	if err := h.DB.
		Where("baby_id = ? AND feeding_time >= ? AND feeding_time < ?", babyID, start, endExclusive).
		Order("feeding_time ASC").
		Find(&feedings).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询喂养记录失败"})
		return
	}

	// growth records
	var growth []models.GrowthRecord
	if err := h.DB.
		Where("baby_id = ? AND record_date >= ? AND record_date < ?", babyID, start, endExclusive).
		Order("record_date ASC").
		Find(&growth).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询生长记录失败"})
		return
	}

	// build daily map (inclusive)
	days := map[string]*babyReportDay{}
	for d := start; !d.After(toDate); d = d.AddDate(0, 0, 1) {
		key := d.Format("2006-01-02")
		days[key] = &babyReportDay{Date: key}
	}

	// apply growth
	for _, gr := range growth {
		key := gr.RecordDate.Format("2006-01-02")
		if day, ok := days[key]; ok {
			if gr.Weight != nil {
				w := *gr.Weight
				day.Weight = &w
			}
			if gr.Height != nil {
				hh := *gr.Height
				day.Height = &hh
			}
		}
	}

	// apply feedings + per-member
	memberAgg := map[string]map[string]int{} // user_id -> {count,total_amount}
	totalAmount := 0
	for _, f := range feedings {
		key := f.FeedingTime.In(time.Local).Format("2006-01-02")
		if day, ok := days[key]; ok {
			day.FeedingsCount += 1
			day.TotalAmount += f.Amount
		}
		totalAmount += f.Amount

		uid := strconv.FormatUint(uint64(f.UserID), 10)
		if _, ok := memberAgg[uid]; !ok {
			memberAgg[uid] = map[string]int{"count": 0, "total_amount": 0}
		}
		memberAgg[uid]["count"] += 1
		memberAgg[uid]["total_amount"] += f.Amount
	}

	// build list (stable order)
	var dayList []babyReportDay
	maxDaily := 0
	maxDailyDate := ""
	minDaily := -1
	minDailyDate := ""
	for d := start; !d.After(toDate); d = d.AddDate(0, 0, 1) {
		key := d.Format("2006-01-02")
		day := days[key]
		if day == nil {
			continue
		}
		dayList = append(dayList, *day)
		if day.TotalAmount > maxDaily {
			maxDaily = day.TotalAmount
			maxDailyDate = key
		}
		if minDaily == -1 || day.TotalAmount < minDaily {
			minDaily = day.TotalAmount
			minDailyDate = key
		}
	}

	daysCount := len(dayList)
	feedingsCount := len(feedings)
	avgPerDay := 0
	if daysCount > 0 {
		avgPerDay = totalAmount / daysCount
	}
	avgPerFeeding := 0
	if feedingsCount > 0 {
		avgPerFeeding = totalAmount / feedingsCount
	}

	format := strings.ToLower(strings.TrimSpace(c.Query("format")))
	if format == "csv" {
		filename := fmt.Sprintf("naibao-report-baby-%d-%s-%s.csv", babyID, start.Format("20060102"), toDate.Format("20060102"))
		c.Header("Content-Type", "text/csv; charset=utf-8")
		c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filename))
		c.String(http.StatusOK, buildCSV(dayList))
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"baby": baby,
		"range": gin.H{
			"from": start.Format("2006-01-02"),
			"to":   toDate.Format("2006-01-02"),
			"days": daysCount,
		},
		"summary": gin.H{
			"feedings_count":  feedingsCount,
			"total_amount":    totalAmount,
			"avg_per_day":     avgPerDay,
			"avg_per_feeding": avgPerFeeding,
			"max_daily":       maxDaily,
			"max_daily_date":  maxDailyDate,
			"min_daily":       minDaily,
			"min_daily_date":  minDailyDate,
		},
		"by_member": memberAgg,
		"days":      dayList,
	})
}

func buildCSV(days []babyReportDay) string {
	var b strings.Builder
	b.WriteString("date,total_amount_ml,feedings_count,weight_kg,height_cm\n")
	for _, d := range days {
		b.WriteString(d.Date)
		b.WriteString(",")
		b.WriteString(strconv.Itoa(d.TotalAmount))
		b.WriteString(",")
		b.WriteString(strconv.Itoa(d.FeedingsCount))
		b.WriteString(",")
		if d.Weight != nil {
			b.WriteString(strconv.FormatFloat(*d.Weight, 'f', -1, 64))
		}
		b.WriteString(",")
		if d.Height != nil {
			b.WriteString(strconv.Itoa(*d.Height))
		}
		b.WriteString("\n")
	}
	return b.String()
}

