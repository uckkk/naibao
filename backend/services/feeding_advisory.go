package services

import (
	"fmt"
	"time"
)

// FeedingAdvisory 是服务端给前端/多端输出的“科学提醒”统一口径：
// - machine-readable: level/code
// - human-readable: title/detail/suggestions
//
// level: unknown | good | attention | alert
// code: 具体原因编码（便于前端做不同样式/埋点/跳转）
type FeedingAdvisory struct {
	Level       string   `json:"level"`
	Code        string   `json:"code"`
	Title       string   `json:"title"`
	Detail      string   `json:"detail"`
	Suggestions []string `json:"suggestions,omitempty"`
}

func formatDurationCN(d time.Duration) string {
	sec := int(d.Seconds())
	if sec < 0 {
		sec = 0
	}
	days := sec / 86400
	hours := (sec % 86400) / 3600
	mins := (sec % 3600) / 60
	secs := sec % 60

	if days > 0 {
		return fmt.Sprintf("%d天%d小时%d分", days, hours, mins)
	}
	if hours > 0 {
		return fmt.Sprintf("%d小时%d分", hours, mins)
	}
	if mins > 0 {
		return fmt.Sprintf("%d分", mins)
	}
	return fmt.Sprintf("%d秒", secs)
}
