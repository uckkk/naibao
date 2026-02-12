# 生产一体化镜像：构建 H5 静态站点 + Caddy 反代 /api 与 /ws
#
# 目标：
# - 前端：纯静态托管，所有交互/计算尽量在客户端完成
# - 后端：只处理用户数据 API（同源 /api），避免跨域

FROM node:20-alpine AS frontend_builder

WORKDIR /app

# 先拷 package-lock 提升缓存命中
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN npm --prefix frontend ci

COPY frontend ./frontend
RUN npm --prefix frontend run build:h5


FROM caddy:2.8-alpine

WORKDIR /srv

COPY --from=frontend_builder /app/frontend/dist/build/h5 /srv
COPY deploy/web/Caddyfile /etc/caddy/Caddyfile

EXPOSE 80 443

