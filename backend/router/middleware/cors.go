package middleware

import (
	"os"
	"strings"
	"github.com/gin-gonic/gin"
)

func parseCORSAllowOrigins() []string {
	raw := strings.TrimSpace(os.Getenv("CORS_ALLOW_ORIGINS"))
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		v := strings.TrimSpace(p)
		if v == "" {
			continue
		}
		out = append(out, v)
	}
	return out
}

func isReleaseMode() bool {
	return strings.ToLower(strings.TrimSpace(os.Getenv("GIN_MODE"))) == "release"
}

func originAllowed(origin string, allow []string) bool {
	o := strings.TrimSpace(origin)
	if o == "" {
		return false
	}
	for _, a := range allow {
		if a == "*" {
			return true
		}
		if a == o {
			return true
		}
	}
	return false
}

func CORS() gin.HandlerFunc {
	allow := parseCORSAllowOrigins()
	release := isReleaseMode()

	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		allowedOrigin := ""
		switch {
		case origin == "":
			// Non-browser clients or same-origin fetch without Origin header.
			allowedOrigin = "*"
		case len(allow) > 0:
			if originAllowed(origin, allow) {
				allowedOrigin = origin
			}
		case !release:
			// Dev default: reflect Origin to keep local dev easy.
			allowedOrigin = origin
		default:
			// Release default: no CORS headers unless explicitly allowed.
			allowedOrigin = ""
		}

		if allowedOrigin != "" {
			c.Writer.Header().Set("Access-Control-Allow-Origin", allowedOrigin)
			// Prevent cache poisoning when allowlist is used.
			c.Writer.Header().Add("Vary", "Origin")
		}

		// Note: Using "*" is incompatible with credentials; we do not use cookies.
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "false")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
		c.Writer.Header().Set("Access-Control-Max-Age", "86400") // 24小时
		
		if c.Request.Method == "OPTIONS" {
			// If Origin provided but not allowed, fail fast in release.
			if origin != "" && len(allow) > 0 && allowedOrigin == "" {
				c.AbortWithStatus(403)
				return
			}
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	}
}
