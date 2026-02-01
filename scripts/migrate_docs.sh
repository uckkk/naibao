#!/usr/bin/env bash
set -euo pipefail

# 文档迁移脚本（默认 dry-run）
# 用法：
#   ./scripts/migrate_docs.sh            # 仅打印将要执行的操作
#   ./scripts/migrate_docs.sh --apply    # 实际执行移动

APPLY="0"
if [[ "${1-}" == "--apply" ]]; then
  APPLY="1"
fi

move_one() {
  local src="$1"
  local dst="$2"

  if [[ ! -f "$src" ]]; then
    echo "[skip] missing: $src"
    return 0
  fi

  echo "[move] $src -> $dst"
  if [[ "$APPLY" == "1" ]]; then
    mkdir -p "$(dirname "$dst")"
    if [[ -d ".git" ]] && command -v git >/dev/null 2>&1; then
      git mv -f "$src" "$dst"
    else
      mv -f "$src" "$dst"
    fi
  fi
}

echo "docs migration (apply=${APPLY})"

# product
move_one "产品分析报告.md" "docs/product/产品分析报告.md"
move_one "产品设计文档.md" "docs/product/产品设计文档.md"
move_one "核心算法设计.md" "docs/product/核心算法设计.md"
move_one "UI设计分析.md" "docs/product/UI设计分析.md"
move_one "UI体验优化方案.md" "docs/product/UI体验优化方案.md"
move_one "误操作处理方案.md" "docs/product/误操作处理方案.md"
move_one "数据分享方案.md" "docs/product/数据分享方案.md"
move_one "奶粉官方数据获取方案.md" "docs/product/奶粉官方数据获取方案.md"
move_one "奶粉官方要求与勺数提示.md" "docs/product/奶粉官方要求与勺数提示.md"
move_one "卫健委2025科学数据标准.md" "docs/product/卫健委2025科学数据标准.md"
move_one "卫健委数据更新机制.md" "docs/product/卫健委数据更新机制.md"
move_one "购买链接.md" "docs/product/购买链接.md"

# tech
move_one "技术选型调整方案.md" "docs/tech/技术选型调整方案.md"
move_one "最终方案总结.md" "docs/tech/最终方案总结.md"
move_one "最低成本数据库方案.md" "docs/tech/最低成本数据库方案.md"
move_one "腾讯云数据库选型建议.md" "docs/tech/腾讯云数据库选型建议.md"
move_one "Supabase国内访问分析.md" "docs/tech/Supabase国内访问分析.md"
move_one "CloudBase vs 轻量数据库对比.md" "docs/tech/CloudBase vs 轻量数据库对比.md"

# ops
move_one "快速开始.md" "docs/ops/快速开始.md"
move_one "部署指南.md" "docs/ops/部署指南.md"
move_one "README_部署.md" "docs/ops/README_部署.md"
move_one "轻量应用服务器购买指南.md" "docs/ops/轻量应用服务器购买指南.md"
move_one "安全组配置详细步骤.md" "docs/ops/安全组配置详细步骤.md"
move_one "服务器连接问题解决方案.md" "docs/ops/服务器连接问题解决方案.md"
move_one "服务器端修复命令.md" "docs/ops/服务器端修复命令.md"
move_one "服务器一键修复说明.md" "docs/ops/服务器一键修复说明.md"
move_one "SSH密钥配置指南.md" "docs/ops/SSH密钥配置指南.md"
move_one "SSH连接问题说明.md" "docs/ops/SSH连接问题说明.md"

# test
move_one "验收文档.md" "docs/test/验收文档.md"
move_one "快速开始测试.md" "docs/test/快速开始测试.md"
move_one "注册功能测试完成.md" "docs/test/注册功能测试完成.md"
move_one "手机测试快速开始.md" "docs/test/手机测试快速开始.md"
move_one "手机测试指南.md" "docs/test/手机测试指南.md"
move_one "手机测试正确步骤.md" "docs/test/手机测试正确步骤.md"
move_one "手机测试步骤.md" "docs/test/手机测试步骤.md"
move_one "数据库初始化指南.md" "docs/test/数据库初始化指南.md"
move_one "数据库配置指南.md" "docs/test/数据库配置指南.md"
move_one "数据库验证说明.md" "docs/test/数据库验证说明.md"
move_one "数据库验证成功报告.md" "docs/test/数据库验证成功报告.md"

# reports
move_one "项目实施状态.md" "docs/reports/项目实施状态.md"
move_one "开发计划.md" "docs/reports/开发计划.md"
move_one "实施计划.md" "docs/reports/实施计划.md"
move_one "开发完成总结.md" "docs/reports/开发完成总结.md"
move_one "设计图实施计划.md" "docs/reports/设计图实施计划.md"
move_one "设计图实施完成总结.md" "docs/reports/设计图实施完成总结.md"
move_one "后端部署完成报告.md" "docs/reports/后端部署完成报告.md"
move_one "3步计划执行报告.md" "docs/reports/3步计划执行报告.md"
move_one "3步计划完成报告.md" "docs/reports/3步计划完成报告.md"

echo "done"
