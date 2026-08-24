#!/usr/bin/env bash
# One-time setup: print the curl commands for EasyCron
# Usage: bash setup-easycron.sh

set -euo pipefail

REPO="xiaopengyoucn/ai-news-wechat"
WORKFLOW="daily.yml"

cat <<EOF
================================================================
 EasyCron 设置步骤（约 3 分钟）
================================================================

1. 注册 https://easycron.com （免费层每天 10 次触发，足够用）

2. 申请 GitHub PAT（repo + workflow 权限）:
   https://github.com/settings/tokens/new
   - Note: easycron-trigger
   - Expiration: No expiration（或自定义）
   - Scopes: 勾选 "repo" 和 "workflow"

3. 下面给你 2 个 cron 任务（UTC 0:00 和 12:00 = Beijing 8:00 和 20:00）:
EOF

# Show literal templates, user substitutes $TOKEN
echo ""
echo "=== Cron #1 (Morning, Beijing 08:00) ==="
echo "URL:    POST https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches"
echo "Header: Authorization: Bearer <PAT>"
echo "Header: Accept: application/vnd.github+json"
echo "Body:   {\"ref\":\"main\"}"
echo ""
echo "=== Cron #2 (Evening, Beijing 20:00) ==="
echo "URL:    POST https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches"
echo "Header: Authorization: Bearer <PAT>"
echo "Header: Accept: application/vnd.github+json"
echo "Body:   {\"ref\":\"main\"}"
echo ""

cat <<EOF

4. 在 EasyCron 添加 Cron Job：
   - URL: https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches
   - Method: POST
   - Headers:
       Authorization: Bearer <YOUR_PAT_HERE>
       Accept: application/vnd.github+json
   - Body: {"ref":"main"}
   - Cron: 0 0 * * *   (Beijing 08:00)
   - Cron: 0 12 * * *  (Beijing 20:00)

5. 测试一次（手动点击 EasyCron 的 "Run Now"），然后查看：
   https://github.com/${REPO}/actions

================================================================
 验证：手动测试 trigger 命令（替换 <PAT>）
================================================================

EOF

read -p "粘贴你的 GitHub PAT 测试（输入隐藏）: " -s PAT
echo ""

if [ -z "$PAT" ]; then
    echo "未输入 PAT，跳过测试。"
    exit 0
fi

# Test trigger
RESP=$(curl -s -X POST \
    -H "Authorization: Bearer $PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
    -d '{"ref":"main"}' \
    -w "\nHTTP %{http_code}")

echo ""
echo "GitHub API 响应:"
echo "$RESP"

if echo "$RESP" | grep -q "204"; then
    echo ""
    echo "✓ 测试触发成功！等待 30 秒后查看："
    echo "  https://github.com/${REPO}/actions"
fi