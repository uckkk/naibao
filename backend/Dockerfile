# 在部分网络环境中 Docker Hub 镜像源不稳定；使用 AWS Public ECR 的官方镜像镜像，提升可拉取性。
FROM public.ecr.aws/docker/library/golang:1.21-alpine AS builder

WORKDIR /app

ENV PATH="/usr/local/go/bin:$PATH"
ENV GOPROXY="https://goproxy.cn,direct"
ENV GOSUMDB="sum.golang.google.cn"

COPY go.mod go.sum ./
RUN go mod download

COPY . .

# CGO 关闭以得到更可移植的二进制；运行时镜像更小更稳定
RUN CGO_ENABLED=0 go build -o /naibao-server main.go


FROM public.ecr.aws/docker/library/alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata

# 默认业务时区（可在运行时通过 TZ 环境变量覆盖）
ENV TZ=Asia/Shanghai

COPY --from=builder /naibao-server /app/naibao-server

EXPOSE 8080
ENTRYPOINT ["/app/naibao-server"]
