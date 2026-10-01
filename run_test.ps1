# 信贷测试一键运行脚本
param(
    [ValidateSet("all", "quick", "gate")]
    [string]$Scope = "all"
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 信贷测试一键运行" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. 探活 Mock 服务
Write-Host ""
Write-Host "[1/4] 检查 Mock 服务是否在线..."
$code = curl.exe -s -o NUL -w "%{http_code}" -X POST "http://127.0.0.1:5000/api/v1/_reset_db"
if ($code -ne "200") {
    Write-Host "Mock 服务未运行！请先启动：" -ForegroundColor Red
    Write-Host "   py app.py"
    exit 1
}
Write-Host "Mock 服务在线" -ForegroundColor Green

# 2. 清历史测试产物
Write-Host ""
Write-Host "[2/4] 清理历史产物..."
Remove-Item -Recurse -Force allure-results\* -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force test-results\* -ErrorAction SilentlyContinue

# 3. 跑测试
Write-Host ""
Write-Host "[3/4] 执行测试 (scope=$Scope)..."
switch ($Scope) {
    "quick" {
        py -m pytest tests -q -m "smoke"
    }
    "gate" {
        py -m pytest tests -q
        py scripts\quality_gate.py
    }
    default {
        py -m pytest tests -q
    }
}

# 4. 生成报告
Write-Host ""
Write-Host "[4/4] 生成 Allure 报告..."
allure generate allure-results --clean -o allure-report

Write-Host ""
Write-Host "完成！" -ForegroundColor Green
Write-Host "查看报告：allure open allure-report"
