# 前端项目启动指南

## ✅ 已修复的问题

1. ✅ npm install 报错 - 已修复（清理了package.json）
2. ✅ uni命令不存在 - 已修复（改用vite）
3. ✅ 依赖安装 - 已完成
4. ✅ 端口配置 - 已改为5173（8080被占用）

---

## 🚀 启动步骤

### 1. 启动开发服务器

```bash
cd /Users/stonem2/Documents/AiCode/naibao/frontend
npm run dev:h5
```

### 2. 查看Network地址

启动后会显示：
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### 3. 手机访问

在手机浏览器输入Network地址（例如：`http://192.168.1.100:5173`）

---

## 📋 配置说明

- **API地址**：通过 `VITE_API_BASE_URL` 配置（参考 `frontend/.env.example`，本机放 `frontend/.env.local`）
- **开发端口**：5173（vite默认端口）
- **服务器地址**：允许外部访问（host: '0.0.0.0'）

---

## 🐛 常见问题

### 端口被占用

如果5173也被占用，修改 `vite.config.js`：
```javascript
server: {
  port: 3000, // 改为其他端口
}
```

### 手机无法访问

确保：
- 手机和Mac在同一WiFi
- Mac防火墙允许该端口
- Network地址正确

---

**现在运行 `npm run dev:h5` 即可！** 🎉

