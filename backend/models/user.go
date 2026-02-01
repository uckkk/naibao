package models

import (
	"time"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

type User struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	Phone       string    `gorm:"uniqueIndex;not null" json:"phone"`
	Nickname    string    `json:"nickname"`
	AvatarURL   string    `json:"avatar_url"`
	PasswordHash string    `gorm:"column:password_hash" json:"-"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

func (u *User) SetPassword(password string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	u.PasswordHash = string(hash)
	return nil
}

func (u *User) CheckPassword(password string) bool {
	err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password))
	return err == nil
}

func (u *User) BeforeCreate(tx *gorm.DB) error {
	if u.Nickname == "" {
		if len(u.Phone) >= 4 {
			u.Nickname = "用户" + u.Phone[len(u.Phone)-4:]
		} else {
			u.Nickname = "新用户"
		}
	}
	return nil
}
