package utils

import (
	"sync"
	"time"
)

var (
	cnLocOnce sync.Once
	cnLoc     *time.Location
)

// CNLocation returns the product's canonical timezone.
// We intentionally pin to Asia/Shanghai because the app's "day/night interval"
// and "daily stats" are designed for China users.
func CNLocation() *time.Location {
	cnLocOnce.Do(func() {
		loc, err := time.LoadLocation("Asia/Shanghai")
		if err != nil {
			// Fallback: China does not use DST in modern times; fixed +08 is acceptable here.
			loc = time.FixedZone("CST", 8*3600)
		}
		cnLoc = loc
	})
	return cnLoc
}

// ReinterpretAsCNWallClock fixes the classic "timestamp without timezone" pitfall:
// Postgres TIMESTAMP (without tz) is a naive wall-clock value. Some drivers parse it
// as UTC, which shifts the absolute instant by +8h for CN users and breaks countdowns.
//
// This function keeps Y/M/D/H/M/S fields, but sets location to Asia/Shanghai,
// so the absolute instant matches the intended wall-clock semantics.
func ReinterpretAsCNWallClock(t time.Time) time.Time {
	if t.IsZero() {
		return t
	}
	loc := CNLocation()

	// If already in CN timezone (or same offset), do nothing.
	_, off := t.Zone()
	_, offCN := time.Now().In(loc).Zone()
	if t.Location() == loc || off == offCN {
		return t
	}

	return time.Date(
		t.Year(),
		t.Month(),
		t.Day(),
		t.Hour(),
		t.Minute(),
		t.Second(),
		t.Nanosecond(),
		loc,
	)
}

