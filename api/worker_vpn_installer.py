"""
Worker Node VPN Installer
워커노드용 VPN 설치 모듈
"""

import base64
from models import Node
import json
import os
import logging

logger = logging.getLogger(__name__)

def generate_worker_vpn_installer(node: Node) -> str:
    """워커노드용 Windows 설치 배치 파일 생성 - central과 동일한 패턴"""
    
    # 노드에 config가 없으면 오류
    if not node.config or node.config == "pending":
        logger.error(f"Cannot generate installer for {node.node_id}: no config available")
        return f"echo 오류: 노드 설정이 준비되지 않았습니다. 웹 페이지에서 '설치 시작' 버튼을 먼저 클릭하세요."
    
    # 서버 URL 구성
    server_host = os.getenv('SERVERURL', 'localhost')
    if server_host == 'auto' or not server_host or server_host == 'localhost':
        server_host = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
    server_url = f"http://{server_host}:8090"
    
    # PowerShell 스크립트 생성 (central과 동일한 패턴)
    powershell_script = f"""
# WireGuard VPN 자동 설치 스크립트
# Node ID: {node.node_id}
# VPN IP: {node.vpn_ip}

Write-Host "🚀 VPN 자동 설치를 시작합니다..." -ForegroundColor Green
Write-Host "노드 ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "VPN IP: {node.vpn_ip}" -ForegroundColor Yellow

# 1. WireGuard 설치 상태 확인
$wireguardPath = "C:\\Program Files\\WireGuard\\wireguard.exe"
$isInstalled = Test-Path $wireguardPath

if (-not $isInstalled) {{
    # 신규 설치
    Write-Host "📦 WireGuard 다운로드 중..." -ForegroundColor Cyan
    $wireguardUrl = "https://download.wireguard.com/windows-client/wireguard-installer.exe"
    $installerPath = "$env:TEMP\\wireguard-installer.exe"
    
    try {{
        Invoke-WebRequest -Uri $wireguardUrl -OutFile $installerPath
        Write-Host "✅ 다운로드 완료" -ForegroundColor Green
    }} catch {{
        Write-Host "❌ 다운로드 실패: $_" -ForegroundColor Red
        exit 1
    }}
    
    Write-Host "📦 WireGuard 설치 중..." -ForegroundColor Cyan
    Start-Process -FilePath $installerPath -ArgumentList "/qn" -Wait
    Write-Host "✅ 설치 완료" -ForegroundColor Green
}} else {{
    Write-Host "📦 WireGuard가 이미 설치되어 있습니다." -ForegroundColor Yellow
}}

# 2. VPN 설정 파일 생성
Write-Host "⚙️ VPN 설정 생성 중..." -ForegroundColor Cyan
$configUrl = "{server_url}/api/worker-config/{node.node_id}"

# Downloads 폴더에 직접 저장
$configDir = "$env:USERPROFILE\\Downloads"
$configPath = "$configDir\\{node.node_id}.conf"
Write-Host "📁 설정 파일 경로: $configPath" -ForegroundColor Yellow

try {{
    # 설정 파일 직접 다운로드
    Invoke-WebRequest -Uri $configUrl -OutFile $configPath
    Write-Host "✅ 설정 파일 생성 완료: $configPath" -ForegroundColor Green
    
    # 설정 파일 내용에서 정보 추출
    $configContent = Get-Content $configPath -Raw
    if ($configContent -match "Address = ([\d\.]+)") {{
        Write-Host "📍 VPN IP: $($matches[1])" -ForegroundColor Yellow
    }}
    Write-Host "📍 노드 ID: {node.node_id}" -ForegroundColor Yellow
    
}} catch {{
    Write-Host "❌ 설정 생성 실패: $_" -ForegroundColor Red
    exit 1
}}

# 3. Windows 방화벽 규칙 추가
Write-Host "🔥 Windows 방화벽 설정 중..." -ForegroundColor Cyan
try {{
    # 모든 관련 기존 규칙 완전히 제거 (와일드카드 사용)
    Write-Host "  기존 방화벽 규칙 정리 중..." -ForegroundColor Yellow
    Get-NetFirewallRule -DisplayName "WireGuard*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "VPN*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "Worker API" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "Ray*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "DDP*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "NCCL*" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Write-Host "  기존 규칙 제거 완료" -ForegroundColor Green
    
    # WireGuard 포트
    New-NetFirewallRule -DisplayName "WireGuard VPN Port In" -Direction Inbound -Protocol UDP -LocalPort 51820 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "WireGuard VPN Port Out" -Direction Outbound -Protocol UDP -LocalPort 51820 -Action Allow -ErrorAction Stop
    
    # VPN 서브넷 전체 허용
    New-NetFirewallRule -DisplayName "VPN Subnet In" -Direction Inbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "VPN Subnet Out" -Direction Outbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    
    # ICMP (ping) 허용 - 중요!
    New-NetFirewallRule -DisplayName "VPN ICMP Echo Request In" -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "VPN ICMP Echo Reply Out" -Direction Outbound -Protocol ICMPv4 -IcmpType 0 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "VPN ICMP All In" -Direction Inbound -Protocol ICMPv4 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "VPN ICMP All Out" -Direction Outbound -Protocol ICMPv4 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction Stop
    
    # 워커노드 포트 허용
    New-NetFirewallRule -DisplayName "Worker API" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -ErrorAction Stop
    
    # Ray 분산학습 포트 허용 (중요!)
    # Ray Core 포트
    New-NetFirewallRule -DisplayName "Ray GCS/Redis" -Direction Inbound -Protocol TCP -LocalPort 6379 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray GCS/Redis Out" -Direction Outbound -Protocol TCP -LocalPort 6379 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Client Server" -Direction Inbound -Protocol TCP -LocalPort 10001 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Client Server Out" -Direction Outbound -Protocol TCP -LocalPort 10001 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray ObjectManager" -Direction Inbound -Protocol TCP -LocalPort 8076 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray ObjectManager Out" -Direction Outbound -Protocol TCP -LocalPort 8076 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray NodeManager" -Direction Inbound -Protocol TCP -LocalPort 8077 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray NodeManager Out" -Direction Outbound -Protocol TCP -LocalPort 8077 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Dashboard" -Direction Inbound -Protocol TCP -LocalPort 8265 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Metrics Export" -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -ErrorAction Stop
    
    # Ray 추가 포트 (ray_port_config.py 참조)
    New-NetFirewallRule -DisplayName "Ray Runtime Env Agent" -Direction Inbound -Protocol TCP -LocalPort 52367 -Action Allow -ErrorAction Stop
    
    # DDP/NCCL 포트 범위
    New-NetFirewallRule -DisplayName "DDP TCPStore" -Direction Inbound -Protocol TCP -LocalPort 29500-29509 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "DDP TCPStore Out" -Direction Outbound -Protocol TCP -LocalPort 29500-29509 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "NCCL Socket" -Direction Inbound -Protocol TCP -LocalPort 29510 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "NCCL Socket Out" -Direction Outbound -Protocol TCP -LocalPort 29510 -Action Allow -ErrorAction Stop
    
    # Ray Worker 포트 범위
    New-NetFirewallRule -DisplayName "Ray Workers" -Direction Inbound -Protocol TCP -LocalPort 11000-11049 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Workers Out" -Direction Outbound -Protocol TCP -LocalPort 11000-11049 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Ephemeral" -Direction Inbound -Protocol TCP -LocalPort 30000-30049 -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "Ray Ephemeral Out" -Direction Outbound -Protocol TCP -LocalPort 30000-30049 -Action Allow -ErrorAction Stop
    
    # VPN 서브넷 간 모든 TCP 통신 허용 (워커 노드 간 통신)
    New-NetFirewallRule -DisplayName "VPN Worker TCP All In" -Direction Inbound -Protocol TCP -RemoteAddress "10.100.1.0/24" -Action Allow -ErrorAction Stop
    New-NetFirewallRule -DisplayName "VPN Worker TCP All Out" -Direction Outbound -Protocol TCP -RemoteAddress "10.100.1.0/24" -Action Allow -ErrorAction Stop
    
    Write-Host "✅ 방화벽 규칙 추가 완료 (중복 없이)" -ForegroundColor Green
    
    # 추가된 규칙 수 확인
    $vpnRuleCount = @(Get-NetFirewallRule -DisplayName "VPN*" -ErrorAction SilentlyContinue).Count
    $rayRuleCount = @(Get-NetFirewallRule -DisplayName "Ray*" -ErrorAction SilentlyContinue).Count
    Write-Host "  - VPN 규칙: $vpnRuleCount개" -ForegroundColor Cyan
    Write-Host "  - Ray 규칙: $rayRuleCount개" -ForegroundColor Cyan
}} catch {{
    if ($_.Exception.Message -like "*already exists*") {{
        Write-Host "⚠️ 일부 방화벽 규칙이 이미 존재함 (정상)" -ForegroundColor Yellow
    }} else {{
        Write-Host "⚠️ 방화벽 설정 오류 (계속 진행): $_" -ForegroundColor Yellow
    }}
}}

# 4. WireGuard UI에 터널 추가
Write-Host "📥 터널을 WireGuard에 추가 중..." -ForegroundColor Cyan
if (Test-Path $wireguardPath) {{
    # WireGuard 종료 (깨끗한 시작을 위해)
    Stop-Process -Name "wireguard" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # 설정 파일을 WireGuard 디렉토리로 복사
    $wireguardConfigDir = "C:\\Program Files\\WireGuard\\Data\\Configurations"
    if (-not (Test-Path $wireguardConfigDir)) {{
        New-Item -ItemType Directory -Path $wireguardConfigDir -Force | Out-Null
    }}
    
    Copy-Item -Path $configPath -Destination $wireguardConfigDir -Force
    Write-Host "✅ 설정 파일 복사 완료" -ForegroundColor Green
    
    # WireGuard UI 실행 (자동으로 설정 파일 감지)
    Start-Process -FilePath $wireguardPath
    Start-Sleep -Seconds 3
    
    Write-Host "✅ WireGuard가 실행되었습니다" -ForegroundColor Green
    Write-Host "📌 WireGuard 창에서 터널을 활성화하세요" -ForegroundColor Yellow
    
    Write-Host "" 
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  VPN이 성공적으로 설치되었습니다!" -ForegroundColor Green
    Write-Host "  워커 노드가 네트워크에 준비되었습니다." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    
    # 연결 테스트 안내
    Write-Host ""
    Write-Host "📋 다음 단계:" -ForegroundColor Yellow
    Write-Host "  1. WireGuard 창에서 '{node.node_id}' 터널 활성화" -ForegroundColor White
    Write-Host "  2. 활성화 후 VPN 연결 확인" -ForegroundColor White
    Write-Host "  3. docker-runner-{node.node_id}.bat 실행" -ForegroundColor White
    
    Write-Host ""
    Write-Host "🔍 연결 테스트 (터널 활성화 후):" -ForegroundColor Cyan
    Write-Host "  VPN 게이트웨이: ping 10.100.1.1" -ForegroundColor White
    Write-Host "  워커간: ping 10.100.1.x" -ForegroundColor White
}} else {{
    Write-Host "⚠️ WireGuard 실행 실패" -ForegroundColor Red
    Write-Host "수동으로 WireGuard를 실행하고 설정 파일을 가져오세요:" -ForegroundColor Yellow
    Write-Host $configPath -ForegroundColor White
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩 (central과 동일)
    encoded_script = base64.b64encode(powershell_script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성 (central과 동일한 패턴)
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title Worker VPN Auto Installer

echo ==========================================
echo    Worker Node VPN Auto Installer
echo    Node ID: {node.node_id}
echo    VPN IP: {node.vpn_ip}
echo ==========================================
echo.

:: Check for admin rights
net session >nul 2>&1
if !errorLevel! neq 0 (
    echo [!] Administrator rights required.
    echo.
    echo Requesting administrator rights...
    timeout /t 2 >nul
    
    :: Restart as admin
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [+] Administrator rights confirmed
echo.

:: Run PowerShell script using Base64 encoding
echo Running installation script...
echo.

:: Execute PowerShell script with encoded command
powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand "{encoded_script}"

if !errorLevel! equ 0 (
    echo.
    echo [+] Installation completed successfully!
) else (
    echo.
    echo [!] Installation encountered some issues.
)

echo.
pause
"""
    
    return batch_script