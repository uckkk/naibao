# SSH 密钥配置指南

> 目标：使用 SSH 密钥认证（推荐），并避免在仓库内保存明文密码/IP 等敏感信息。

## 1. 配置本机私有连接信息（推荐）

仓库内提供了脚本配置模板：

```bash
cp scripts/.env.example scripts/.env.local
$EDITOR scripts/.env.local
```

至少填写：

- `SSH_HOST`
- `SSH_USER`
- `SSH_PORT`（可选，默认 22）

## 2. 一键初始化（推荐）

```bash
./scripts/init_ssh.sh
```

说明：

- 如果服务器仍允许密码认证，并且你希望脚本自动化，可在 `scripts/.env.local` 中临时填写 `SSH_PASSWORD`（不推荐；建议尽快切换到密钥认证并禁用密码）。
- 默认会回退到交互式 `ssh-copy-id`，按提示输入密码即可（不会在仓库中留下密码）。

## 3. 手动配置（可选）

### 3.1 生成密钥

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### 3.2 写入服务器 authorized_keys

```bash
ssh-copy-id -p <SSH_PORT> <SSH_USER>@<SSH_HOST>
```

### 3.3 测试连接

```bash
ssh -p <SSH_PORT> <SSH_USER>@<SSH_HOST>
```

## 4. 生产环境安全建议

1. 配置密钥认证后，禁用密码认证（`/etc/ssh/sshd_config`：`PasswordAuthentication no`）。
2. 使用非 root 用户运行服务，最小化权限。
3. 限制 SSH 来源 IP，配合 fail2ban/安全组降低暴力破解风险。

