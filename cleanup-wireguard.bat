@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title WireGuard Cleanup Tool

echo ==========================================
echo    WireGuard 터널 정리 도구
echo ==========================================
echo.

:: Check for admin rights
net session >nul 2>&1
if !errorLevel! neq 0 (
    echo [!] 관리자 권한이 필요합니다.
    echo.
    echo 관리자 권한 요청 중...
    timeout /t 2 >nul
    
    :: Restart as admin
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [+] 관리자 권한 확인됨
echo.

:: Run PowerShell cleanup script
echo WireGuard 터널 정리 중...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Write-Host 'WireGuard 종료 중...' -ForegroundColor Yellow; ^
Stop-Process -Name 'wireguard' -Force -ErrorAction SilentlyContinue; ^
Start-Sleep -Seconds 2; ^
Write-Host '설정 파일 정리 중...' -ForegroundColor Yellow; ^
Remove-Item 'C:\Program Files\WireGuard\Data\Configurations\central-central-*.conf' -Force -ErrorAction SilentlyContinue; ^
Remove-Item 'C:\Program Files\WireGuard\Data\Configurations\worker-worker-*.conf' -Force -ErrorAction SilentlyContinue; ^
Remove-Item 'C:\Program Files\WireGuard\Data\Configurations\*.dpapi' -Force -ErrorAction SilentlyContinue; ^
Remove-Item '%USERPROFILE%\Downloads\central-central-*.conf' -Force -ErrorAction SilentlyContinue; ^
Remove-Item '%USERPROFILE%\Downloads\worker-worker-*.conf' -Force -ErrorAction SilentlyContinue; ^
Write-Host '서비스 정리 중...' -ForegroundColor Yellow; ^
Get-Service -Name 'WireGuardTunnel$*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Service $_.Name -Force -ErrorAction SilentlyContinue; sc.exe delete $_.Name }; ^
Write-Host ''; ^
Write-Host '✅ WireGuard 터널 정리 완료!' -ForegroundColor Green; ^
Write-Host ''; ^
Write-Host '이제 WireGuard를 다시 시작하고 새로운 설정을 추가할 수 있습니다.' -ForegroundColor Yellow"

echo.
echo [+] 정리 완료!
echo.
pause