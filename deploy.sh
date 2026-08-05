#!/usr/bin/env bash
# 一键部署脚本：创建 GitHub 仓库 + push + 配置 Secrets + 试跑
# 适用于 git-bash (Windows) / WSL / macOS / Linux

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}==>${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
die()  { echo -e "${RED}✗${NC} $1"; exit 1; }

step "1/6  环境检查"

command -v gh >/dev/null 2>&1 || die "gh CLI 未安装。安装: https://cli.github.com"
ok "gh CLI 已安装"

gh auth status >/dev/null 2>&1 || die "gh 未登录。运行: gh auth login"
ok "gh 已登录"

command -v git >/dev/null 2>&1 || die "git 未安装"
ok "git 已安装"

[ -d .git ] || die "当前目录不是 git 仓库。请在项目根目录运行此脚本。"
ok "git 仓库存在"

step "2/6  配置仓库"

read -p "  仓库名 [默认 ai-news-wechat]: " REPO_NAME
REPO_NAME=${REPO_NAME:-ai-news-wechat}

read -p "  公开性 (public/private) [默认 public]: " VISIBILITY
VISIBILITY=${VISIBILITY:-public}
if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  die "公开性必须是 public 或 private"
fi

read -p "  仓库描述 [默认 'AI news digest to personal WeChat']: " REPO_DESC
REPO_DESC=${REPO_DESC:-AI news digest to personal WeChat}

GH_USER=$(gh api user --jq .login)
ok "GitHub 用户: $GH_USER"
ok "目标仓库: https://github.com/$GH_USER/$REPO_NAME"

step "3/6  创建/推送仓库"

if gh repo view "$GH_USER/$REPO_NAME" >/dev/null 2>&1; then
  warn "仓库 $REPO_NAME 已存在。直接 push。"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/$GH_USER/$REPO_NAME.git"
  fi
  git push -u origin main
else
  gh repo create "$REPO_NAME" \
    --$VISIBILITY \
    --description "$REPO_DESC" \
    --source=. \
    --remote=origin \
    --push
fi
ok "代码已 push 到 main 分支"

step "4/6  配置 GitHub Secrets"

configure_secret() {
  local name="$1"
  local prompt="$2"
  read -s -p "  $prompt (留空跳过): " value
  echo ""
  if [ -n "$value" ]; then
    echo "$value" | gh secret set "$name" --repo "$GH_USER/$REPO_NAME"
    ok "已设置 $name"
  else
    warn "跳过 $name (可在 GitHub 网页手动配置)"
  fi
}

configure_secret "DEEPSEEK_API_KEY" "DEEPSEEK_API_KEY (https://platform.deepseek.com)"
configure_secret "PUSHPLUS_TOKEN"   "PUSHPLUS_TOKEN (https://pushplus.plus 微信扫码)"

echo ""
read -p "  可选: 配置 PUSHPLUS_TOPIC (多人接收推送)? [y/N]: " NEED_TOPIC
if [[ "$NEED_TOPIC" =~ ^[Yy]$ ]]; then
  read -p "  PUSHPLUS_TOPIC: " TOPIC_VALUE
  if [ -n "$TOPIC_VALUE" ]; then
    echo "$TOPIC_VALUE" | gh secret set PUSHPLUS_TOPIC --repo "$GH_USER/$REPO_NAME"
    ok "已设置 PUSHPLUS_TOPIC"
  fi
fi

read -p "  可选: 配置 LLM_MODEL (默认 deepseek-chat)? [y/N]: " NEED_MODEL
if [[ "$NEED_MODEL" =~ ^[Yy]$ ]]; then
  read -p "  LLM_MODEL: " MODEL_VALUE
  if [ -n "$MODEL_VALUE" ]; then
    echo "$MODEL_VALUE" | gh secret set LLM_MODEL --repo "$GH_USER/$REPO_NAME"
    ok "已设置 LLM_MODEL"
  fi
fi

step "5/6  启用 GitHub Actions"

gh repo edit "$GH_USER/$REPO_NAME" --enable-actions || warn "Actions 可能已启用"
ok "GitHub Actions 已启用"

step "6/6  试跑 (可选)"

read -p "  立即触发一次 workflow 测试推送? [y/N]: " RUN_NOW
if [[ "$RUN_NOW" =~ ^[Yy]$ ]]; then
  gh workflow run daily.yml --repo "$GH_USER/$REPO_NAME"
  ok "Workflow 已触发。查看: https://github.com/$GH_USER/$REPO_NAME/actions"
else
  warn "未触发。定时任务将在 08:00 / 20:00 Asia/Shanghai 自动运行。"
fi

echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo ""
echo "  仓库:   https://github.com/$GH_USER/$REPO_NAME"
echo "  Actions: https://github.com/$GH_USER/$REPO_NAME/actions"
echo "  README:  https://github.com/$GH_USER/$REPO_NAME#部署5-分钟"
echo ""
echo -e "${BLUE}提示:${NC}"
echo "  - 第一次推送可能因 LLM/PushPlus 调用失败，多看几次 Actions 日志"
echo "  - 想本地试跑: ./setup.sh 创建 venv 后, python main.py --mode morning"
echo ""