package main

import (
	"log"
	"naibao-backend/config"
	"naibao-backend/database"
	"naibao-backend/router"
	"naibao-backend/websocket"
)

func main() {
	// 加载配置
	cfg := config.Load()
	
	// 初始化数据库
	db, err := database.InitDB(cfg.Database)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	
	// 初始化Redis（可选）
	rdb, err := database.InitRedis(cfg.Redis)
	if err != nil {
		log.Printf("Warning: Redis not available: %v (continuing without Redis)", err)
		rdb = nil // 允许在没有Redis的情况下继续运行
	}
	
	// 初始化WebSocket Hub
	hub := websocket.NewHub()
	go hub.Run()
	
	// 初始化路由
	r := router.SetupRouter(db, rdb, hub, cfg)
	
	// 启动服务器
	addr := ":" + cfg.Server.Port
	log.Printf("Server starting on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

