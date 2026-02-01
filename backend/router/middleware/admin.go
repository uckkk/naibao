package middleware

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
)

var (
	adminOnce sync.Once
	adminSet  map[uint]struct{}
)

func loadAdminSet() {
	adminSet = make(map[uint]struct{})
	raw := strings.TrimSpace(os.Getenv("ADMIN_USER_IDS"))
	if raw == "" {
		return
	}
	for _, part := range strings.Split(raw, ",") {
		s := strings.TrimSpace(part)
		if s == "" {
			continue
		}
		n, err := strconv.ParseUint(s, 10, 32)
		if err != nil || n == 0 {
			continue
		}
		adminSet[uint(n)] = struct{}{}
	}
}

func isAdminUser(userID uint) bool {
	adminOnce.Do(loadAdminSet)
	_, ok := adminSet[userID]
	return ok
}

func AdminOnly() gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := c.GetUint("userID")
		if userID == 0 || !isAdminUser(userID) {
			c.JSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
			c.Abort()
			return
		}
		
		c.Next()
	}
}
