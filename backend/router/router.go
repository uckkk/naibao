package router

import (
	"naibao-backend/config"
	"naibao-backend/handlers"
	"naibao-backend/router/middleware"
	"naibao-backend/websocket"
	"os"
	"strings"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"
)

func SetupRouter(db *gorm.DB, rdb *redis.Client, hub *websocket.Hub, cfg *config.Config) *gin.Engine {
	if cfg.Server.Mode == "release" {
		gin.SetMode(gin.ReleaseMode)
	}
	
	r := gin.Default()
	// File upload (avatars etc.). Keep small to reduce memory footprint.
	r.MaxMultipartMemory = 8 << 20 // 8MB

	// 中间件
	r.Use(middleware.CORS())
	r.Use(middleware.ErrorHandler())

	// Static uploads: mount UPLOAD_DIR (default ./uploads) at /uploads
	uploadDir := strings.TrimSpace(os.Getenv("UPLOAD_DIR"))
	if uploadDir == "" {
		uploadDir = "./uploads"
	}
	_ = os.MkdirAll(uploadDir, 0o755)
	r.Static("/uploads", uploadDir)
	
	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})
	
	// API路由
	api := r.Group("/api")
	{
		// 兼容：前端默认以 /api 作为前缀（同源反代/跨平台统一）
		api.GET("/health", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		// 公开接口
		{
			authHandler := handlers.NewAuthHandler(db)
			public := api.Group("/public")
			// 公网必做：登录/注册限流（IP + 账号维度），降低暴力尝试风险
			public.Use(middleware.AuthRateLimit())
			public.POST("/register", authHandler.Register)
			public.POST("/login", authHandler.Login)
		}
		
		// 需要认证的接口
		auth := api.Group("/")
		auth.Use(middleware.JWTAuth(cfg.JWT))
		{
			// 用户相关
			userHandler := handlers.NewUserHandler(db)
			auth.GET("/user/profile", userHandler.GetProfile)
			auth.PUT("/user/profile", userHandler.UpdateProfile)
			auth.PUT("/user/avatar", userHandler.UpdateAvatar)
			auth.PUT("/user/password", userHandler.UpdatePassword)

			// 头像上传（自定义照片 -> 返回可用 URL；再通过 profile/avatar 接口保存）
			avatarUpload := handlers.NewAvatarUploadHandler(db)
			auth.POST("/user/avatar/upload", avatarUpload.UploadUserAvatar)
			
			// 宝宝相关
			babyHandler := handlers.NewBabyHandler(db)
			auth.GET("/babies", babyHandler.GetBabies)
			auth.POST("/babies", babyHandler.CreateBaby)
			auth.GET("/babies/:id", babyHandler.GetBaby)
			auth.PUT("/babies/:id", babyHandler.UpdateBaby)
			auth.DELETE("/babies/:id", babyHandler.DeleteBaby)

			// 宝宝头像上传（管理员）
			auth.POST("/babies/:id/avatar/upload", avatarUpload.UploadBabyAvatar)
			
			// 喂养记录相关
			feedingHandler := handlers.NewFeedingHandler(db, hub)
			auth.POST("/feedings", feedingHandler.CreateFeeding)
			auth.GET("/feedings", feedingHandler.GetFeedings)
			auth.GET("/feedings/stats", feedingHandler.GetFeedingStats)
			auth.PUT("/feedings/:id", feedingHandler.UpdateFeeding)
			auth.DELETE("/feedings/:id", feedingHandler.DeleteFeeding)
			
			// 喂奶间隔设置
			settingsHandler := &handlers.FeedingSettingsHandler{DB: db}
			auth.GET("/babies/:id/settings", settingsHandler.GetSettings)
			auth.PUT("/babies/:id/settings", settingsHandler.UpdateSettings)
			auth.GET("/babies/:id/next-feeding-time", settingsHandler.GetNextFeedingTime)
			
			// 生长数据相关
			growthHandler := &handlers.GrowthHandler{DB: db, Hub: hub}
			auth.GET("/babies/:id/growth-stats", growthHandler.GetGrowthStats)
			auth.GET("/babies/:id/daily-records", growthHandler.GetDailyRecords)
			// 录入/更新生长记录（按日期 upsert）
			auth.POST("/babies/:id/growth-records", growthHandler.CreateGrowthRecord)

			// 用户偏好（投喂输入偏好）
			prefHandler := &handlers.PreferenceHandler{DB: db}
			auth.GET("/babies/:id/preferences", prefHandler.GetPreference)
			auth.PUT("/babies/:id/preferences", prefHandler.UpdatePreference)

			// 数据导出/报告（按日期范围）
			reportHandler := &handlers.ReportHandler{DB: db}
			auth.GET("/babies/:id/report", reportHandler.GetBabyReport)
			
			// 奶粉品牌相关
			formulaHandler := &handlers.FormulaHandler{DB: db}
			auth.GET("/formula/brands", formulaHandler.GetBrands)
			specHandler := &handlers.FormulaSpecHandler{DB: db}
			auth.GET("/formula/specifications", specHandler.GetSpecifications)
			auth.POST("/babies/:id/formula", formulaHandler.SelectFormula)
			auth.GET("/babies/:id/formula", formulaHandler.GetCurrentFormula)
			auth.GET("/babies/:id/formula/specification", specHandler.GetCurrentSpecification)
			
			// 家庭成员相关
			familyHandler := &handlers.FamilyHandler{DB: db}
			auth.GET("/babies/:id/family-members", familyHandler.GetFamilyMembers)
			auth.DELETE("/babies/:id/family-members/:userId", familyHandler.RemoveFamilyMember)

			// 转奶计划（宝宝级配置）
			weaningHandler := &handlers.WeaningPlanHandler{DB: db, Hub: hub}
			auth.GET("/babies/:id/weaning-plan", weaningHandler.GetCurrent)
			auth.POST("/babies/:id/weaning-plan", weaningHandler.Create)
			auth.PUT("/babies/:id/weaning-plan", weaningHandler.UpdateStatus)

			// 邀请码：生成/使用
			inviteHandler := &handlers.InviteHandler{DB: db}
			auth.POST("/invite/generate", inviteHandler.Generate)
			auth.POST("/invite/use", inviteHandler.Use)
		}
		
		// 管理员接口
		admin := api.Group("/admin")
		admin.Use(middleware.JWTAuth(cfg.JWT))
		admin.Use(middleware.AdminOnly())
		{
			// 卫健委标准数据管理
			hsAdmin := &handlers.AdminHealthStandardsHandler{DB: db}
			admin.GET("/health-standards/versions", hsAdmin.ListVersions)
			admin.GET("/health-standards", hsAdmin.List)
			admin.POST("/health-standards", hsAdmin.Create)
			admin.PUT("/health-standards/:id", hsAdmin.Update)
			admin.POST("/health-standards/activate", hsAdmin.ActivateVersion)

			// 奶粉规格管理
			fsAdmin := &handlers.AdminFormulaSpecHandler{DB: db}
			admin.GET("/formula/specifications", fsAdmin.List)
			admin.POST("/formula/specifications", fsAdmin.Create)
			admin.PUT("/formula/specifications/:id", fsAdmin.Update)
			admin.POST("/formula/specifications/:id/verify", fsAdmin.Verify)

			// 数据更新任务：暂未实现（可后续加入导入/对比/回滚等）
		}
	}
	
	// WebSocket路由
	r.GET("/ws", func(c *gin.Context) {
		websocket.HandleWebSocket(hub, c, db)
	})
	
	return r
}
