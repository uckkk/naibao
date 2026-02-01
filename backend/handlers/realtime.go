package handlers

import (
	"encoding/json"
	"time"

	ws "naibao-backend/websocket"
)

type realtimeEvent struct {
	Type      string `json:"type"`
	BabyID    uint   `json:"baby_id"`
	Entity    string `json:"entity"`
	Action    string `json:"action"`
	ID        uint   `json:"id,omitempty"`
	Timestamp int64  `json:"timestamp"`
}

func broadcastEvent(hub *ws.Hub, babyID uint, entity string, action string, id uint) {
	if hub == nil || babyID == 0 {
		return
	}
	b, err := json.Marshal(realtimeEvent{
		Type:      "event",
		BabyID:    babyID,
		Entity:    entity,
		Action:    action,
		ID:        id,
		Timestamp: time.Now().Unix(),
	})
	if err != nil {
		return
	}
	hub.BroadcastToBaby(babyID, b)
}

