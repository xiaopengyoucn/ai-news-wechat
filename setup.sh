#!/usr/bin/env bash
# 本地首次设置：创建 venv + 装依赖 + 跑测试
# 适用于 git-bash (Windows) / WSL / macOS / Linux

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==>${NC} 创建 Python 虚拟环境"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo -e "${BLUE}==>${NC} 升级 pip"
python -m pip install --upgrade pip -q

echo -e "${BLUE}==>${NC} 安装依赖"
pip install -r requirements.txt -q

echo -e "${BLUE}==>${NC} 跑测试"
pytest -q

echo ""
echo -e "${GREEN}✓ 设置完成${NC}"
echo ""
echo "下一步："
echo "  1. 申请 DEEPSEEK_API_KEY: https://platform.deepseek.com"
echo "  2. 申请 PUSHPLUS_TOKEN: https://pushplus.plus (微信扫码)"
echo "  3. 试跑一次: DEEPSEEK_API_KEY=... PUSHPLUS_TOKEN=... python main.py --mode morning"
echo ""