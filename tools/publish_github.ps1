# 一键发布到 GitHub（需要 Personal Access Token，带 repo 权限）
#
# 用法：
#   $env:GITHUB_TOKEN = "ghp_xxx"
#   powershell -ExecutionPolicy Bypass -File tools\publish_github.ps1
#
# 做了什么：
#   1. 用 GitHub API 创建仓库 SoCoolp/md2edrawmind（已存在则跳过）
#   2. 配置 remote origin（带 token，仅本次使用，不写进 .git/config 的明文？——会写，用后请撤销 token）
#   3. push main 分支与 v1.0.0 标签
param(
  [string]$Owner = "SoCoolp",
  [string]$Repo  = "md2edrawmind",
  [string]$Token = $env:GITHUB_TOKEN,
  [string]$Description = "Turn Markdown notes with LaTeX formulas into Word files EdrawMind can import with formulas intact"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not $Token) {
  Write-Host "[错误] 没有 token。请先设置：`$env:GITHUB_TOKEN = 'ghp_xxx'" -ForegroundColor Red
  exit 1
}

$headers = @{
  Authorization = "token $Token"
  Accept        = "application/vnd.github+json"
  "User-Agent"  = "md2edrawmind-publish"
}

Write-Host "[1/3] 检查/创建仓库 $Owner/$Repo ..."
$exists = $true
try {
  Invoke-RestMethod -Uri "https://api.github.com/repos/$Owner/$Repo" -Headers $headers -Method Get | Out-Null
  Write-Host "      仓库已存在，跳过创建"
} catch {
  $exists = $false
}

if (-not $exists) {
  $body = @{
    name        = $Repo
    description = $Description
    private     = $false
    has_issues  = $true
    has_wiki    = $false
    auto_init   = $false
  } | ConvertTo-Json
  try {
    $created = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Headers $headers -Method Post `
      -Body $body -ContentType "application/json"
    Write-Host "      已创建：$($created.html_url)" -ForegroundColor Green
  } catch {
    Write-Host "[错误] 创建仓库失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "       常见原因：token 缺少 repo 权限，或仓库名已被占用"
    exit 1
  }
}

Write-Host "[2/3] 配置 remote 并推送 ..."
$remote = "https://x-access-token:$Token@github.com/$Owner/$Repo.git"
git remote remove origin 2>$null | Out-Null
git remote add origin $remote
git push -u origin main
if ($LASTEXITCODE -ne 0) {
  Write-Host "[错误] push 失败" -ForegroundColor Red
  exit 1
}
git push origin v1.0.0 2>$null

Write-Host "[3/3] 收尾：把 remote 换成不含 token 的地址"
git remote set-url origin "https://github.com/$Owner/$Repo.git"
git remote -v

Write-Host ""
Write-Host "完成 → https://github.com/$Owner/$Repo" -ForegroundColor Green
Write-Host "提醒：请到 GitHub Settings 撤销刚才那个 token（本脚本不会保存它）。"
