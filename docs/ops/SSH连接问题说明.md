# SSH连接问题说明

> 目标：快速定位 SSH 无法连接/无法免密登录的原因，并给出最小操作集的修复方案。

## 常见原因

1. 服务器禁用密码认证，仅允许密钥认证（推荐的安全配置）。
2. 客户端公钥未写入服务器 `~/.ssh/authorized_keys`，或权限不正确。
3. `known_hosts` 中的主机指纹不匹配（换机/重装系统常见）。
4. 端口/用户名不正确，或安全组/防火墙未放行 22（或自定义端口）。

## 排查步骤（建议按顺序）

1) 确认连接参数（用户名/端口/主机）

```bash
ssh -p <SSH_PORT> <SSH_USER>@<SSH_HOST>
```

2) 打开调试日志（看认证失败点）

```bash
ssh -vvv -p <SSH_PORT> <SSH_USER>@<SSH_HOST>
```

3) 写入客户端公钥（推荐）

```bash
ssh-copy-id -p <SSH_PORT> <SSH_USER>@<SSH_HOST>
```

如果 `ssh-copy-id` 不可用，手动方式如下（需能通过控制台/其他手段登录服务器）：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "<你的客户端公钥内容>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

4) 处理 known_hosts 指纹问题（仅在确认服务器可信时）

```bash
ssh-keygen -R "<SSH_HOST>"
ssh-keyscan -H -p <SSH_PORT> "<SSH_HOST>" >> ~/.ssh/known_hosts
```

## 概念澄清：服务器公钥 vs 客户端公钥

- `known_hosts` 保存的是“服务器主机指纹”（用于验证服务器身份，防止中间人攻击）。
- `authorized_keys` 保存的是“客户端公钥”（用于让服务器信任你的客户端，从而免密登录）。

