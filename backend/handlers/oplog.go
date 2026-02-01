package handlers

import (
	"encoding/json"
	"naibao-backend/models"

	"gorm.io/gorm"
)

func jsonBytes(v any) []byte {
	if v == nil {
		return nil
	}
	b, err := json.Marshal(v)
	if err != nil {
		return nil
	}
	return b
}

// logOperation best-effort 写入审计日志；失败不影响主流程。
func logOperation(db *gorm.DB, userID uint, action string, entityType string, entityID uint, before any, after any) {
	if db == nil {
		return
	}
	_ = db.Create(&models.OperationLog{
		UserID:     userID,
		Action:     action,
		EntityType: entityType,
		EntityID:   entityID,
		BeforeData: jsonBytes(before),
		AfterData:  jsonBytes(after),
	}).Error
}
