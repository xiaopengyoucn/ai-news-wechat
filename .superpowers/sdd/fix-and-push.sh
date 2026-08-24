#!/usr/bin/env bash
set -e
cd /c/Users/Administrator/AppData/Local/Temp/opencode/ai-news-wechat
pytest -q 2>&1 | tail -3
git add main.py
git commit -m "fix(main): empty LLM_MODEL env falls back to deepseek-v4-flash default"
git push
