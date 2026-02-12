package middleware

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// In-memory rate limiting (single instance).
// For the current "lowest cost" deployment, a single server is the default,
// so an in-memory limiter is sufficient and avoids a Redis dependency.
// If you later scale out to multiple instances, move these limiters to Redis.

type counterEntry struct {
	count       int
	windowStart time.Time
	lastSeen    time.Time
}

type counterStore struct {
	mu          sync.Mutex
	entries     map[string]*counterEntry
	limit       int
	window      time.Duration
	ttl         time.Duration
	lastCleanup time.Time
}

func newCounterStore(limit int, window time.Duration, ttl time.Duration) *counterStore {
	l := limit
	if l <= 0 {
		l = 1
	}
	w := window
	if w <= 0 {
		w = time.Minute
	}
	return &counterStore{
		entries: make(map[string]*counterEntry),
		limit:   l,
		window:  w,
		ttl:     ttl,
	}
}

func (s *counterStore) allow(key string) bool {
	k := strings.TrimSpace(key)
	if k == "" {
		// If we can't identify the key, don't block.
		return true
	}

	now := time.Now()

	s.mu.Lock()
	defer s.mu.Unlock()

	// Lazy cleanup to avoid a dedicated goroutine (keeps ops simple).
	if s.lastCleanup.IsZero() || now.Sub(s.lastCleanup) > 60*time.Second {
		for kk, e := range s.entries {
			if s.ttl > 0 && now.Sub(e.lastSeen) > s.ttl {
				delete(s.entries, kk)
			}
		}
		s.lastCleanup = now
	}

	e := s.entries[k]
	if e == nil {
		e = &counterEntry{
			count:       0,
			windowStart: now,
			lastSeen:    now,
		}
		s.entries[k] = e
	}

	// New window -> reset
	if now.Sub(e.windowStart) >= s.window {
		e.count = 0
		e.windowStart = now
	}

	e.lastSeen = now
	if e.count >= s.limit {
		return false
	}
	e.count++
	return true
}

type phoneCarrier struct {
	Phone string `json:"phone"`
}

func readPhoneFromJSONBody(c *gin.Context) string {
	if c == nil || c.Request == nil || c.Request.Body == nil {
		return ""
	}

	// Read raw body (best-effort), then restore it for downstream handlers.
	raw, err := io.ReadAll(c.Request.Body)
	if err != nil {
		return ""
	}
	c.Request.Body = io.NopCloser(bytes.NewBuffer(raw))

	var p phoneCarrier
	if err := json.Unmarshal(raw, &p); err != nil {
		return ""
	}
	return strings.TrimSpace(p.Phone)
}

// AuthRateLimit applies conservative limits to public auth endpoints to reduce
// brute-force / credential-stuffing risk on the public Internet.
//
// Limits (roughly):
// - per IP: 30 req/min
// - per phone: 10 req/min
func AuthRateLimit() gin.HandlerFunc {
	ipLimiter := newCounterStore(30, time.Minute, 15*time.Minute)
	phoneLimiter := newCounterStore(10, time.Minute, 30*time.Minute)

	return func(c *gin.Context) {
		ip := c.ClientIP()
		if !ipLimiter.allow(ip) {
			c.JSON(http.StatusTooManyRequests, gin.H{"error": "请求过于频繁，请稍后再试"})
			c.Abort()
			return
		}

		phone := readPhoneFromJSONBody(c)
		if phone != "" && !phoneLimiter.allow(phone) {
			c.JSON(http.StatusTooManyRequests, gin.H{"error": "请求过于频繁，请稍后再试"})
			c.Abort()
			return
		}

		c.Next()
	}
}
