package utils

import (
	"naibao-backend/config"
	"time"
	"github.com/golang-jwt/jwt/v5"
)

func GenerateToken(userID uint) (string, error) {
	cfg := config.Load()
	
	claims := jwt.MapClaims{
		"userID": userID,
		"exp":    time.Now().Add(time.Hour * time.Duration(cfg.JWT.Expiration)).Unix(),
		"iat":    time.Now().Unix(),
	}
	
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(cfg.JWT.Secret))
}

func ParseToken(tokenString string) (uint, error) {
	cfg := config.Load()
	
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		return []byte(cfg.JWT.Secret), nil
	})
	
	if err != nil {
		return 0, err
	}
	
	if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
		if userID, ok := claims["userID"].(float64); ok {
			return uint(userID), nil
		}
	}
	
	return 0, jwt.ErrSignatureInvalid
}

