#!/usr/bin/env bash
set -e
cd /c/Users/Administrator/AppData/Local/Temp/opencode/ai-news-wechat
pytest -q 2>&1 | tail -3
git add -A
git commit -m "feat: 7 new chemistry/materials sources + boost keywords + EasyCron setup"
git push