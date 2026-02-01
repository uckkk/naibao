package config

import (
	"os"
	"sync"
	"github.com/joho/godotenv"
)

type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	JWT      JWTConfig
}

type ServerConfig struct {
	Port string
	Mode string // debug, release
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	DBName   string
	SSLMode  string
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

type JWTConfig struct {
	Secret     string
	Expiration int // hours
}

var (
	loadedConfig *Config
	loadOnce     sync.Once
)

func Load() *Config {
	loadOnce.Do(func() {
		// 尝试加载 .env 文件（如果存在）
		godotenv.Load()

		loadedConfig = &Config{
			Server: ServerConfig{
				Port: getEnv("SERVER_PORT", "8080"),
				Mode: getEnv("GIN_MODE", "debug"),
			},
			Database: DatabaseConfig{
				Host:     getEnv("DB_HOST", "localhost"),
				Port:     getEnv("DB_PORT", "5432"),
				User:     getEnv("DB_USER", "postgres"),
				Password: getEnv("DB_PASSWORD", ""),
				DBName:   getEnv("DB_NAME", "naibao"),
				SSLMode:  getEnv("DB_SSLMODE", "disable"),
			},
			Redis: RedisConfig{
				Host:     getEnv("REDIS_HOST", "localhost"),
				Port:     getEnv("REDIS_PORT", "6379"),
				Password: getEnv("REDIS_PASSWORD", ""),
				DB:       0,
			},
			JWT: JWTConfig{
				Secret:     getEnv("JWT_SECRET", "naibao-secret-key-change-in-production"),
				Expiration: 24, // 24 hours
			},
		}
	})

	return loadedConfig
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
