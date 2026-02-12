package database

import (
	"fmt"
	"naibao-backend/config"
	"naibao-backend/models"
	"os"
	"strings"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func shouldAutoMigrate() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv("DB_AUTO_MIGRATE")))
	if v == "" {
		// 默认：开发环境开启，生产(release)关闭，避免无意的结构漂移
		mode := strings.ToLower(strings.TrimSpace(os.Getenv("GIN_MODE")))
		return mode != "release"
	}
	return v == "1" || v == "true" || v == "yes" || v == "on"
}

func InitDB(cfg config.DatabaseConfig) (*gorm.DB, error) {
	dsn := fmt.Sprintf(
		"host=%s user=%s password=%s dbname=%s port=%s sslmode=%s TimeZone=Asia/Shanghai",
		cfg.Host, cfg.User, cfg.Password, cfg.DBName, cfg.Port, cfg.SSLMode,
	)
	
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}
	
	// 自动迁移表结构（仅建议开发环境使用，生产环境默认关闭）
	if shouldAutoMigrate() {
		err = db.AutoMigrate(
			&models.User{},
			&models.Baby{},
			&models.Feeding{},
			&models.GrowthRecord{},
			&models.FeedingSettings{},
			&models.FamilyMember{},
			&models.InviteCode{},
			&models.FormulaBrand{},
			&models.FormulaSpecification{},
			&models.UserFormulaSelection{},
			&models.OperationLog{},
			&models.WeaningPlan{},
		)
		if err != nil {
			return nil, fmt.Errorf("failed to auto migrate: %w", err)
		}
	}
	
	return db, nil
}
