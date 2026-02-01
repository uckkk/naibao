package services

import (
	"testing"
	"time"
)

func mustLocal(t *testing.T) *time.Location {
	t.Helper()
	loc, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		// 兜底：测试环境不一定有 tzdata，但仍可用 Local 做相对判断
		return time.Local
	}
	return loc
}

func TestCalculateNextFeedingTime_UsesDayIntervalWhenLastFeedingInDay(t *testing.T) {
	loc := mustLocal(t)
	mc := NewMilkCalculator()

	dayStart := 6
	dayEnd := 18
	dayInterval := 3
	nightInterval := 5

	last := time.Date(2026, 2, 1, 16, 0, 0, 0, loc) // 白天
	now := time.Date(2026, 2, 1, 16, 0, 1, 0, loc)

	got := mc.CalculateNextFeedingTime(now, last, dayStart, dayEnd, dayInterval, nightInterval)
	want := time.Date(2026, 2, 1, 19, 0, 0, 0, loc)
	if !got.Equal(want) {
		t.Fatalf("expected next=%v, got=%v", want, got)
	}
}

func TestCalculateNextFeedingTime_UsesNightIntervalWhenLastFeedingAtNight(t *testing.T) {
	loc := mustLocal(t)
	mc := NewMilkCalculator()

	dayStart := 6
	dayEnd := 18
	dayInterval := 3
	nightInterval := 5

	last := time.Date(2026, 2, 1, 20, 0, 0, 0, loc) // 夜间
	now := time.Date(2026, 2, 1, 20, 0, 1, 0, loc)

	got := mc.CalculateNextFeedingTime(now, last, dayStart, dayEnd, dayInterval, nightInterval)
	want := time.Date(2026, 2, 2, 1, 0, 0, 0, loc)
	if !got.Equal(want) {
		t.Fatalf("expected next=%v, got=%v", want, got)
	}
}

func TestCalculateNextFeedingTime_FallsBackToCurrentTimeWhenComputedTimeAlreadyPassed(t *testing.T) {
	loc := mustLocal(t)
	mc := NewMilkCalculator()

	dayStart := 6
	dayEnd := 18
	dayInterval := 3
	nightInterval := 5

	last := time.Date(2026, 2, 1, 9, 0, 0, 0, loc)
	now := time.Date(2026, 2, 1, 20, 0, 0, 0, loc) // 当前是夜间

	got := mc.CalculateNextFeedingTime(now, last, dayStart, dayEnd, dayInterval, nightInterval)
	want := time.Date(2026, 2, 2, 1, 0, 0, 0, loc) // now + 5h
	if !got.Equal(want) {
		t.Fatalf("expected next=%v, got=%v", want, got)
	}
}

