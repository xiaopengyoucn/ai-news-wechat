# 一键部署脚本（Windows PowerShell）
# 等价于 deploy.sh，供 Windows 原生用户使用（无需 git-bash）

$ErrorActionPreference = 'Stop'

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Die($msg)  { Write-Host "  [X] $msg" -ForegroundColor Red; exit 1 }

Step "1/6  环境检查"

try { $null = Get-Command gh -ErrorAction Stop }
catch { Die "gh CLI 未安装。安装: https://cli.github.com" }
Ok "gh CLI 已安装"

try {
    $null = & gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) { throw "not authed" }
} catch { Die "gh 未登录。运行: gh auth login" }
Ok "gh 已登录"

try { $null = Get-Command git -ErrorAction Stop }
catch { Die "git 未安装" }
Ok "git 已安装"

if (-not (Test-Path -LiteralPath ".git")) {
    Die "当前目录不是 git 仓库。请在项目根目录运行此脚本。"
}
Ok "git 仓库存在"

Step "2/6  配置仓库"

$repoName = Read-Host "  仓库名 [默认 ai-news-wechat]"
if ([string]::IsNullOrWhiteSpace($repoName)) { $repoName = "ai-news-wechat" }

$visibility = Read-Host "  公开性 (public/private) [默认 public]"
if ([string]::IsNullOrWhiteSpace($visibility)) { $visibility = "public" }
if ($visibility -notin @("public", "private")) { Die "公开性必须是 public 或 private" }

$repoDesc = Read-Host "  仓库描述 [默认 'AI news digest to personal WeChat']"
if ([string]::IsNullOrWhiteSpace($repoDesc)) { $repoDesc = "AI news digest to personal WeChat" }

$ghUser = (& gh api user --jq .login).Trim()
Ok "GitHub 用户: $ghUser"
Ok "目标仓库: https://github.com/$ghUser/$repoName"

Step "3/6  创建/推送仓库"

$repoExists = $false
try {
    $null = & gh repo view "$ghUser/$repoName" 2>&1
    if ($LASTEXITCODE -eq 0) { $repoExists = $true }
} catch { $repoExists = $false }

if ($repoExists) {
    Warn "仓库 $repoName 已存在。直接 push。"
    $originUrl = & git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        & git remote add origin "https://github.com/$ghUser/$repoName.git"
    }
    & git push -u origin main
    if ($LASTEXITCODE -ne 0) { Die "git push 失败" }
} else {
    & gh repo create $repoName `
        --$visibility `
        --description $repoDesc `
        --source=. `
        --remote=origin `
        --push
    if ($LASTEXITCODE -ne 0) { Die "gh repo create 失败" }
}
Ok "代码已 push 到 main 分支"

Step "4/6  配置 GitHub Secrets"

function Configure-Secret($name, $prompt) {
    $secure = Read-Host "  $prompt (留空跳过)" -AsSecureString
    $value = ""
    if ($secure) {
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    }
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        $value | & gh secret set $name --repo "$ghUser/$repoName"
        if ($LASTEXITCODE -eq 0) {
            Ok "已设置 $name"
        } else {
            Warn "设置 $name 失败"
        }
    } else {
        Warn "跳过 $name (可在 GitHub 网页手动配置)"
    }
}

Configure-Secret "DEEPSEEK_API_KEY" "DEEPSEEK_API_KEY (https://platform.deepseek.com)"
Configure-Secret "PUSHPLUS_TOKEN"   "PUSHPLUS_TOKEN (https://pushplus.plus 微信扫码)"

$needTopic = Read-Host "  可选: 配置 PUSHPLUS_TOPIC (多人接收推送)? [y/N]"
if ($needTopic -match '^[Yy]$') {
    Configure-Secret "PUSHPLUS_TOPIC" "PUSHPLUS_TOPIC"
}

$needModel = Read-Host "  可选: 配置 LLM_MODEL (默认 deepseek-chat)? [y/N]"
if ($needModel -match '^[Yy]$') {
    Configure-Secret "LLM_MODEL" "LLM_MODEL"
}

Step "5/6  启用 GitHub Actions"

& gh repo edit "$ghUser/$repoName" --enable-actions 2>$null
Ok "GitHub Actions 已启用"

Step "6/6  试跑 (可选)"

$runNow = Read-Host "  立即触发一次 workflow 测试推送? [y/N]"
if ($runNow -match '^[Yy]$') {
    & gh workflow run daily.yml --repo "$ghUser/$repoName"
    if ($LASTEXITCODE -eq 0) {
        Ok "Workflow 已触发。查看: https://github.com/$ghUser/$repoName/actions"
    } else {
        Warn "Workflow 触发失败"
    }
} else {
    Warn "未触发。定时任务将在 08:00 / 20:00 Asia/Shanghai 自动运行。"
}

Write-Host "`n=== 部署完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "  仓库:   https://github.com/$ghUser/$repoName"
Write-Host "  Actions: https://github.com/$ghUser/$repoName/actions"
Write-Host "  README:  https://github.com/$ghUser/$repoName#部署5-分钟"
Write-Host ""
Write-Host "提示:" -ForegroundColor Cyan
Write-Host "  - 第一次推送可能因 LLM/PushPlus 调用失败，多看几次 Actions 日志"
Write-Host "  - 想本地试跑: .\setup.ps1 创建 venv 后, python main.py --mode morning"