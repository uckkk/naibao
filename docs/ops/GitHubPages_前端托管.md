# GitHub Pages 托管前端（naibao.me）

目标：前端完全静态化，免费托管在 GitHub Pages，通过自定义域名 `naibao.me` 访问。

> 说明：本项目已内置 GitHub Actions 工作流：`.github/workflows/pages.yml`  
> 它会构建 `frontend` 并发布到 Pages，同时写入 `CNAME=naibao.me`。

## 1) GitHub 仓库设置

进入你的 GitHub 仓库：

- Settings -> Pages
- Source 选择 **GitHub Actions**
- Custom domain 填：`naibao.me`
- 等 DNS 生效后，打开 **Enforce HTTPS**

## 2) DNS（推荐：在 Cloudflare 里配）

因为你后端会用 Cloudflare Tunnel（`api.naibao.me`），所以建议把 `naibao.me` 的 DNS 也统一放在 Cloudflare 管理：

1) 在 Spaceship 把域名的 **Nameservers** 改成 Cloudflare 给你的那两条 NS  
2) 在 Cloudflare DNS 里添加（Apex 域名用 A 记录）：

`naibao.me`（A 记录，四条）：

- 185.199.108.153
- 185.199.109.153
- 185.199.110.153
- 185.199.111.153

`www.naibao.me`：

- CNAME -> `naibao.me`

> 若 GitHub Pages 的 IP 有更新，以 GitHub 官方文档为准。

## 3) 验证

DNS 生效后：

- 打开 `https://naibao.me` 能看到登录页（标题“奶宝”）
- 控制台 Network 里请求会指向 `https://api.naibao.me/api/...`（后端还没通的话会报错，下一步去配 Tunnel）

