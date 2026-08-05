# 本地首次设置（Windows PowerShell）
# 等价于 setup.sh

$ErrorActionPreference = 'Stop'

Write-Host "==> 创建 Python 虚拟环境" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1

Write-Host "==> 升级 pip" -ForegroundColor Cyan
python -m pip install --upgrade pip -q

Write-Host "==> 安装依赖" -ForegroundColor Cyan
pip install -r requirements.txt -q

Write-Host "==> 跑测试" -ForegroundColor Cyan
pytest -q

Write-Host "`n[OK] 设置完成" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 申请 DEEPSEEK_API_KEY: https://platform.deepseek.com"
Write-Host "  2. 申请 PUSHPLUS_TOKEN: https://pushplus.plus (微信扫码)"
Write-Host "  3. 试跑一次:"
Write-Host '     $env:DEEPSEEK_API_KEY="..."'
Write-Host '     $env:PUSHPLUS_TOKEN="..."'
Write-Host '     python main.py --mode morning'