package services

import (
	"naibao-backend/models"
	"time"
)

type MilkCalculator struct{}

func NewMilkCalculator() *MilkCalculator {
	return &MilkCalculator{}
}

// CalculateDailyStandard 计算标准日均奶量（按体重）- 卫健委2025标准
func (mc *MilkCalculator) CalculateDailyStandard(weight float64) float64 {
	// 卫健委2025标准：每公斤体重120-150ml/天，推荐值135ml/kg/天
	recommendedCoefficient := 135.0
	return weight * recommendedCoefficient
}

// GetAgeReference 获取月龄参考范围（卫健委2025标准）
func (mc *MilkCalculator) GetAgeReference(ageMonths float64) (min, max int, text string) {
	if ageMonths < 1 {
		return 600, 700, "600-700ml/天"
	} else if ageMonths < 3 {
		return 700, 900, "700-900ml/天"
	} else if ageMonths < 6 {
		return 800, 1000, "800-1000ml/天"
	} else {
		return 900, 1100, "900-1100ml/天"
	}
}

// CalculateRemainingFeedingTimes 计算今日剩余喂养次数
func (mc *MilkCalculator) CalculateRemainingFeedingTimes(
	currentTime time.Time,
	dayStartTime, dayEndTime, dayInterval, nightInterval int,
) int {
	hour := currentTime.Hour()
	currentMinutes := hour*60 + currentTime.Minute()
	
	var remainingTimes int
	
	if hour >= dayStartTime && hour < dayEndTime {
		// 白天时段
		dayEndMinutes := dayEndTime * 60
		remainingMinutes := dayEndMinutes - currentMinutes
		remainingTimes = remainingMinutes / (dayInterval * 60)
		
		// 加上晚上时段
		nightStartMinutes := dayEndTime * 60
		nightEndMinutes := (24 + dayStartTime) * 60
		nightMinutes := nightEndMinutes - nightStartMinutes
		remainingTimes += nightMinutes / (nightInterval * 60)
	} else {
		// 晚上时段
		dayStartMinutes := (24 + dayStartTime) * 60
		remainingMinutes := dayStartMinutes - currentMinutes
		remainingTimes = remainingMinutes / (nightInterval * 60)
	}
	
	if remainingTimes < 1 {
		return 1 // 至少1次
	}
	
	return remainingTimes
}

// CalculateRecommendedAmount 计算推荐奶量
type RecommendedAmount struct {
	Recommended    int    `json:"recommended"`     // 推荐奶量
	DailyStandard  int    `json:"daily_standard"`  // 日均标准量
	DailyConsumed  int    `json:"daily_consumed"`  // 今日已摄入
	RemainingTimes int    `json:"remaining_times"` // 剩余喂养次数
	Warning        string `json:"warning"`         // 预警状态：normal, low, high
	AgeReference   string `json:"age_reference"`   // 月龄参考范围
}

func (mc *MilkCalculator) CalculateRecommendedAmount(
	baby *models.Baby,
	todayFeedings []models.Feeding,
	userPreference *int,
	currentTime time.Time,
	dayStartHour, dayEndHour, dayInterval, nightInterval int,
) RecommendedAmount {
	coef := 135.0
	_, _, ageReference := mc.GetAgeReference(baby.AgeInMonths)
	return mc.CalculateRecommendedAmountWithStandards(
		baby,
		todayFeedings,
		userPreference,
		currentTime,
		dayStartHour,
		dayEndHour,
		dayInterval,
		nightInterval,
		coef,
		ageReference,
	)
}

// CalculateRecommendedAmountWithStandards 允许外部注入“按体重奶量系数”和“按月龄参考文案”，
// 用于支持从数据库动态读取卫健委标准（无则回退到默认常量）。
func (mc *MilkCalculator) CalculateRecommendedAmountWithStandards(
	baby *models.Baby,
	todayFeedings []models.Feeding,
	userPreference *int,
	currentTime time.Time,
	dayStartHour, dayEndHour, dayInterval, nightInterval int,
	milkByWeightRecommendedCoefficient float64,
	ageReferenceText string,
) RecommendedAmount {
	// 1. 计算标准日均奶量（按体重）
	// 假设有当前体重数据，这里先用默认值
	currentWeight := baby.CurrentWeight
	if currentWeight == 0 {
		// 如果没有体重数据，使用月龄估算
		currentWeight = mc.estimateWeightByAge(baby.AgeInMonths)
	}

	if milkByWeightRecommendedCoefficient <= 0 {
		milkByWeightRecommendedCoefficient = 135.0
	}
	dailyStandard := int(currentWeight * milkByWeightRecommendedCoefficient)

	// 2. 获取月龄参考范围（允许注入）
	ageReference := ageReferenceText
	if ageReference == "" {
		_, _, fallback := mc.GetAgeReference(baby.AgeInMonths)
		ageReference = fallback
	}
	
	// 3. 计算今日已摄入量
	dailyConsumed := 0
	for _, feeding := range todayFeedings {
		dailyConsumed += feeding.Amount
	}
	
	// 4. 计算剩余喂养次数
	remainingTimes := mc.CalculateRemainingFeedingTimes(currentTime, dayStartHour, dayEndHour, dayInterval, nightInterval)
	
	// 5. 计算单次推荐量
	var recommended int
	if remainingTimes > 0 && dailyConsumed < dailyStandard {
		remainingStandard := dailyStandard - dailyConsumed
		recommended = remainingStandard / remainingTimes
		
		// 限制范围：50-200ml
		if recommended < 50 {
			recommended = 50
		}
		if recommended > 200 {
			recommended = 200
		}
	} else {
		if userPreference != nil {
			recommended = *userPreference
		} else {
			recommended = dailyStandard / 6 // 默认一天6次
		}
	}
	
	// 6. 预警判断
	warningRatio := float64(dailyConsumed) / float64(dailyStandard)
	warning := "normal"
	if warningRatio > 1.2 {
		warning = "high"
	} else if warningRatio < 0.8 {
		warning = "low"
	}
	
	return RecommendedAmount{
		Recommended:    recommended,
		DailyStandard:   dailyStandard,
		DailyConsumed:   dailyConsumed,
		RemainingTimes: remainingTimes,
		Warning:        warning,
		AgeReference:   ageReference,
	}
}

// CalculateNextFeedingTime 计算下次喂奶时间
func (mc *MilkCalculator) CalculateNextFeedingTime(
	currentTime time.Time,
	lastFeedingTime time.Time,
	dayStartHour, dayEndHour, dayInterval, nightInterval int,
) time.Time {
	// 如果没有上次喂奶记录，使用当前时间
	if lastFeedingTime.IsZero() {
		lastFeedingTime = currentTime
	}

	// 规则（以用户直觉为准，避免“白天显示夜间间隔”的困惑）：
	// - 喂奶发生在白天时段 => 下次 = 上次时间 + 白天间隔
	// - 喂奶发生在夜间时段 => 下次 = 上次时间 + 夜间间隔
	// 不做跨时段“平滑”调整（例如 16:00 + 3h = 19:00 即使已进入夜间，也仍按白天间隔）。
	lastHour := lastFeedingTime.Hour()
	interval := nightInterval
	if lastHour >= dayStartHour && lastHour < dayEndHour {
		interval = dayInterval
	}
	if interval <= 0 {
		interval = 3
	}
	nextTime := lastFeedingTime.Add(time.Duration(interval) * time.Hour)

	// 确保下次时间不早于当前时间
	if nextTime.Before(currentTime) {
		currentHour := currentTime.Hour()
		interval2 := nightInterval
		if currentHour >= dayStartHour && currentHour < dayEndHour {
			interval2 = dayInterval
		}
		if interval2 <= 0 {
			interval2 = interval
			if interval2 <= 0 {
				interval2 = 3
			}
		}
		nextTime = currentTime.Add(time.Duration(interval2) * time.Hour)
	}

	return nextTime
}

// estimateWeightByAge 根据月龄估算体重（WHO标准）
func (mc *MilkCalculator) estimateWeightByAge(ageMonths float64) float64 {
	if ageMonths < 1 {
		return 4.1
	} else if ageMonths < 2 {
		return 5.0
	} else if ageMonths < 3 {
		return 6.0
	} else if ageMonths < 4 {
		return 6.5
	} else if ageMonths < 5 {
		return 7.0
	} else if ageMonths < 6 {
		return 7.5
	} else if ageMonths < 7 {
		return 8.0
	} else if ageMonths < 8 {
		return 8.5
	} else if ageMonths < 9 {
		return 9.0
	} else if ageMonths < 10 {
		return 9.5
	} else if ageMonths < 11 {
		return 10.0
	} else {
		return 10.5
	}
}
