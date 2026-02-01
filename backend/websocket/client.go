package websocket

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"naibao-backend/models"
	"naibao-backend/utils"
	"strconv"
	"strings"
	"time"
	
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"gorm.io/gorm"
)

const (
	writeWait  = 10 * time.Second
	pongWait   = 60 * time.Second
	pingPeriod = (pongWait * 9) / 10
	maxMessageSize = 512
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		// WebSocket 本身不携带 CORS；这里用 token 鉴权兜底跨域需求。
		return true
	},
}

type Client struct {
	hub    *Hub
	conn   *websocket.Conn
	send   chan []byte
	userID uint
	babyID uint
	db     *gorm.DB
}

func HandleWebSocket(hub *Hub, c *gin.Context, db *gorm.DB) {
	if hub == nil || db == nil {
		c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "server not ready"})
		return
	}

	// 鉴权：优先 query token（浏览器原生 WS 不能自定义 header），其次 Authorization header
	token := strings.TrimSpace(c.Query("token"))
	if token == "" {
		auth := strings.TrimSpace(c.GetHeader("Authorization"))
		if strings.HasPrefix(strings.ToLower(auth), "bearer ") {
			token = strings.TrimSpace(auth[7:])
		}
	}
	if token == "" {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing token"})
		return
	}

	userID, err := utils.ParseToken(token)
	if err != nil || userID == 0 {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid token"})
		return
	}

	babyIDStr := strings.TrimSpace(c.Query("baby_id"))
	if babyIDStr == "" {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "baby_id is required"})
		return
	}
	bid64, err := strconv.ParseUint(babyIDStr, 10, 32)
	if err != nil || bid64 == 0 {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}
	babyID := uint(bid64)

	// 权限：必须是该宝宝的家庭成员（兼容旧数据：owner 自动补 admin 成员）
	var baby models.Baby
	if err := db.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.AbortWithStatusJSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}

	var member models.FamilyMember
	if err := db.Where("baby_id = ? AND user_id = ?", babyID, userID).First(&member).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			if baby.UserID != userID {
				c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "无权访问"})
				return
			}
			// backfill admin 成员
			_ = db.Create(&models.FamilyMember{
				BabyID:   babyID,
				UserID:   userID,
				Role:     "admin",
				JoinedAt: time.Now(),
			}).Error
		} else {
			c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "db error"})
			return
		}
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	client := &Client{
		hub:    hub,
		conn:   conn,
		send:   make(chan []byte, 256),
		userID: userID,
		babyID: babyID,
		db:     db,
	}
	client.conn.SetReadLimit(maxMessageSize)

	client.hub.register <- client

	go client.writePump()
	go client.readPump()
}

func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		c.conn.Close()
	}()
	
	c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		c.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})
	
	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}
		
		var msg map[string]interface{}
		if err := json.Unmarshal(message, &msg); err != nil {
			log.Printf("Invalid message format: %v", err)
			continue
		}
		
		// 处理消息
		c.handleMessage(msg)
	}
}

func (c *Client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()
	
	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			
			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)
			
			n := len(c.send)
			for i := 0; i < n; i++ {
				w.Write([]byte{'\n'})
				w.Write(<-c.send)
			}
			
			if err := w.Close(); err != nil {
				return
			}
			
		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (c *Client) handleMessage(msg map[string]interface{}) {
	// 当前最小实现：服务端只负责推送，客户端无需上行。
	_ = msg
}
