package handlers

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"naibao-backend/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// Avatar upload:
// - Minimal cost: store files on server disk (Docker volume) and save URL in DB by existing endpoints.
// - This handler only returns a stable URL; front-end can decide when to persist it.

const (
	maxAvatarBytes = 5 << 20 // 5MB
)

type AvatarUploadHandler struct {
	DB *gorm.DB
}

func NewAvatarUploadHandler(db *gorm.DB) *AvatarUploadHandler {
	return &AvatarUploadHandler{DB: db}
}

func uploadDir() string {
	v := strings.TrimSpace(os.Getenv("UPLOAD_DIR"))
	if v == "" {
		return "./uploads"
	}
	return v
}

func ensureDir(path string) error {
	return os.MkdirAll(path, 0o755)
}

func randHex(nBytes int) (string, error) {
	if nBytes <= 0 {
		nBytes = 8
	}
	b := make([]byte, nBytes)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func requestBaseURL(c *gin.Context) string {
	if c == nil || c.Request == nil {
		return ""
	}

	// Most reverse proxies / tunnels set these.
	proto := strings.TrimSpace(c.GetHeader("X-Forwarded-Proto"))
	host := strings.TrimSpace(c.GetHeader("X-Forwarded-Host"))

	if proto == "" {
		// Cloudflare may set Cf-Visitor: {"scheme":"https"} but X-Forwarded-Proto is more common.
		if c.Request.TLS != nil {
			proto = "https"
		} else {
			proto = "http"
		}
	}
	if host == "" {
		host = strings.TrimSpace(c.Request.Host)
	}
	if host == "" {
		return ""
	}

	// Safety: proxies may send comma-separated.
	host = strings.Split(host, ",")[0]
	proto = strings.Split(proto, ",")[0]
	return strings.TrimRight(proto, "/") + "://" + strings.TrimSpace(host)
}

func sniffImageExt(headerBytes []byte) (string, error) {
	ct := http.DetectContentType(headerBytes)
	switch ct {
	case "image/jpeg":
		return ".jpg", nil
	case "image/png":
		return ".png", nil
	case "image/webp":
		return ".webp", nil
	default:
		return "", fmt.Errorf("不支持的图片格式（仅支持 JPG/PNG/WebP），检测到：%s", ct)
	}
}

func saveAvatarFile(c *gin.Context, subdir string) (string, string, error) {
	if c == nil {
		return "", "", errors.New("invalid context")
	}

	// Hard limit request body size (protect server memory/disk).
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxAvatarBytes)

	fh, err := c.FormFile("file")
	if err != nil {
		return "", "", errors.New("缺少文件（字段名 file）")
	}

	src, err := fh.Open()
	if err != nil {
		return "", "", errors.New("读取文件失败")
	}
	defer src.Close()

	head := make([]byte, 512)
	n, _ := io.ReadFull(src, head)
	ext, err := sniffImageExt(head[:max(0, n)])
	if err != nil {
		return "", "", err
	}

	// Re-open file for full copy (multipart.File may not support Seek).
	_ = src.Close()
	src, err = fh.Open()
	if err != nil {
		return "", "", errors.New("读取文件失败")
	}
	defer src.Close()

	root := uploadDir()
	dstDir := filepath.Join(root, "avatars", subdir)
	if err := ensureDir(dstDir); err != nil {
		return "", "", errors.New("创建上传目录失败")
	}

	token, err := randHex(8)
	if err != nil {
		return "", "", errors.New("生成文件名失败")
	}
	name := fmt.Sprintf("%s_%s%s", time.Now().Format("20060102_150405"), token, ext)
	dstPath := filepath.Join(dstDir, name)

	dst, err := os.Create(dstPath)
	if err != nil {
		return "", "", errors.New("保存文件失败")
	}
	defer dst.Close()

	if _, err := io.Copy(dst, src); err != nil {
		_ = os.Remove(dstPath)
		return "", "", errors.New("保存文件失败")
	}

	// URL path is relative to the static mount "/uploads" -> UPLOAD_DIR.
	urlPath := "/uploads/avatars/" + strings.TrimLeft(filepath.ToSlash(filepath.Join(subdir, name)), "/")
	base := requestBaseURL(c)
	if base == "" {
		// Fallback: return path only (client can prefix).
		return urlPath, urlPath, nil
	}
	full := strings.TrimRight(base, "/") + urlPath
	return urlPath, full, nil
}

func max(a, b int) int {
	if a >= b {
		return a
	}
	return b
}

// UploadUserAvatar uploads an avatar image and returns a stable URL.
// Front-end should then call /user/profile or /user/avatar to persist it.
func (h *AvatarUploadHandler) UploadUserAvatar(c *gin.Context) {
	userID := c.GetUint("userID")
	if userID == 0 {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "请先登录"})
		return
	}

	// Ensure user exists (better error message for corrupted token).
	var user models.User
	if err := h.DB.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}

	_, full, err := saveAvatarFile(c, filepath.Join("users", fmt.Sprintf("%d", userID)))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"url": full})
}

// UploadBabyAvatar uploads an avatar image for a baby (admin only).
func (h *AvatarUploadHandler) UploadBabyAvatar(c *gin.Context) {
	userID := c.GetUint("userID")
	babyIDStr := c.Param("id")

	babyID, err := parseUintSafe(babyIDStr)
	if err != nil || babyID == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid baby_id"})
		return
	}

	var baby models.Baby
	if err := h.DB.Where("id = ?", babyID).First(&baby).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "宝宝不存在"})
		return
	}

	member, err := ensureBabyMember(h.DB, &baby, userID)
	if err != nil {
		if errors.Is(err, errForbidden) {
			c.JSON(http.StatusForbidden, gin.H{"error": "无权访问"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "查询失败"})
		return
	}
	if !isAdmin(member) {
		c.JSON(http.StatusForbidden, gin.H{"error": "仅管理员可修改宝宝头像"})
		return
	}

	_, full, err := saveAvatarFile(c, filepath.Join("babies", fmt.Sprintf("%d", babyID)))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"url": full})
}

