# 一键发布到 GitHub（需要 Personal Access Token，带 repo 权限）
#
# 用法：
#   $env:GITHUB_TOKEN = "ghp_xxx"
#   powershell -ExecutionPolicy Bypass -File tools\publish_github.ps1
#
# 做了什么：
#   1. 用 GitHub API 创建仓库 <Owner>/<Repo>（已存在则复用）
#   2. push main 分支与 v1.0.0 标签
#   3. 把 remote 换回不含 token 的地址
param(
  [string]$Owner = "SoCoolp",
  [string]$Repo  = "md2edrawmind",
  [string]$Token = $env:GITHUB_TOKEN,
  [string]$Description = "Turn Markdown notes with LaTeX formulas into Word files EdrawMind can import with formulas intact"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not $Token -or $Token.Trim() -eq "") {
  Write-Host ""
  Write-Host "[需要 token] 没有检测到 GITHUB_TOKEN。" -ForegroundColor Yellow
  Write-Host "  1) 打开 https://github.com/settings/tokens  ->  Generate new token (classic)"
  Write-Host "  2) 勾选 scope: repo"
  Write-Host "  3) 复制 token 后执行："
  Write-Host "       `$env:GITHUB_TOKEN = 'ghp_xxx'"
  Write-Host "       powershell -ExecutionPolicy Bypass -File tools\publish_github.ps1"
  Write-Host ""
  exit 1
}

$headers = @{
  Authorization = "token $Token"
  Accept        = "application/vnd.github+json"
  "User-Agent"  = "md2edrawmind-publish"
}

Write-Host "[1/3] 检查远端仓库 $Owner/$Repo ..."
$repoExists = $false
try {
  $null = Invoke-RestMethod -Uri "https://api.github.com/repos/$Owner/$Repo" -Headers $headers -Method Get
  $repoExists = $true
  Write-Host "      仓库已存在，直接推送"
} catch {
  $code = $null
  if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
  if ($code -eq 401) {
    Write-Host "[错误] token 无效或已过期（401）" -ForegroundColor Red
    exit 1
  }
  if ($code -eq 404) {
    Write-Host "      仓库不存在，准备创建"
  } else {
    Write-Host "      查询失败（$code），仍尝试创建"
  }
}

if (-not $repoExists) {
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
    $code = $null
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    Write-Host "[错误] 创建仓库失败（$code）：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "       常见原因：token 缺少 repo 权限；或仓库名已被占用"
    exit 1
  }
}

Write-Host "[2/3] 推送 main 与标签 ..."
$remote = "https://x-access-token:$Token@github.com/$Owner/$Repo.git"
git remote remove origin 2>$null | Out-Null
git remote add origin $remote
git push -u origin main
if ($LASTEXITCODE -ne 0) {
  Write-Host "[错误] push 失败（检查 token 权限或网络代理）" -ForegroundColor Red
  git remote set-url origin "https://github.com/$Owner/$Repo.git"
  exit 1
}
git push origin v1.0.0 2>$null

Write-Host "[3/3] 把 remote 换回不含 token 的地址"
git remote set-url origin "https://github.com/$Owner/$Repo.git"
git remote -v

Write-Host ""
Write-Host "完成 -> https://github.com/$Owner/$Repo" -ForegroundColor Green
Write-Host "提醒：请到 GitHub Settings 撤销刚才那个 token（本脚本不保存它）。"
