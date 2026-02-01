package websocket

import (
	"log"
)

type Hub struct {
	clients    map[*Client]bool
	broadcast  chan broadcastMessage
	register   chan *Client
	unregister chan *Client
}

type broadcastMessage struct {
	babyID uint
	data   []byte
}

func NewHub() *Hub {
	return &Hub{
		clients:    make(map[*Client]bool),
		broadcast:  make(chan broadcastMessage),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

// BroadcastToBaby 只给订阅了同一 baby_id 的连接推送。
// babyID=0 表示广播给所有连接（慎用）。
func (h *Hub) BroadcastToBaby(babyID uint, data []byte) {
	if h == nil {
		return
	}
	h.broadcast <- broadcastMessage{babyID: babyID, data: data}
}

func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
			log.Printf("Client connected. Total: %d", len(h.clients))
			
		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
				log.Printf("Client disconnected. Total: %d", len(h.clients))
			}
			
		case msg := <-h.broadcast:
			for client := range h.clients {
				if msg.babyID != 0 && client.babyID != msg.babyID {
					continue
				}
				select {
				case client.send <- msg.data:
				default:
					close(client.send)
					delete(h.clients, client)
				}
			}
		}
	}
}
