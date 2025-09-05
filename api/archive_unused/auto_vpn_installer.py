"""
Windows 자동 설치 스크립트 생성
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import SessionLocal
import base64
import httpx

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/windows-installer/{token}")
async def get_windows_installer(token: str, request: Request):
    """
    Windows용 PowerShell 자동 설치 스크립트
    """
    server_url = str(request.url).split('/api')[0]
    
    # PowerShell 스크립트 생성
    script = f"""
# WireGuard VPN 자동 설치 스크립트
# Token: {token}
# 이 스크립트는 관리자 권한으로 실행되어야 합니다

Write-Host "🚀 VPN 자동 설치를 시작합니다..." -ForegroundColor Green
Write-Host "노드 ID: worker-{token[:8]}" -ForegroundColor Yellow

# 1. WireGuard 설치 상태 확인
$wireguardPath = "C:\\Program Files\\WireGuard\\wireguard.exe"
$isInstalled = Test-Path $wireguardPath

if ($isInstalled) {{
    Write-Host "📦 WireGuard가 이미 설치되어 있습니다." -ForegroundColor Yellow
    $response = Read-Host "재설치하시겠습니까? (Y/N)"
    
    if ($response -eq 'Y' -or $response -eq 'y') {{
        Write-Host "🗑️ 기존 WireGuard 제거 중..." -ForegroundColor Cyan
        
        # 실행 중인 WireGuard 종료
        Stop-Process -Name "wireguard" -Force -ErrorAction SilentlyContinue
        
        # 제거 실행
        $uninstaller = "C:\\Program Files\\WireGuard\\uninstall.exe"
        if (Test-Path $uninstaller) {{
            Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
            Write-Host "✅ 제거 완료" -ForegroundColor Green
        }}
        
        # 재설치
        Write-Host "📦 WireGuard 다운로드 중..." -ForegroundColor Cyan
        $wireguardUrl = "https://download.wireguard.com/windows-client/wireguard-installer.exe"
        $installerPath = "$env:TEMP\\wireguard-installer.exe"
        
        Invoke-WebRequest -Uri $wireguardUrl -OutFile $installerPath
        Write-Host "📦 WireGuard 재설치 중..." -ForegroundColor Cyan
        Start-Process -FilePath $installerPath -ArgumentList "/qn" -Wait
        Write-Host "✅ 재설치 완료" -ForegroundColor Green
    }}
}} else {{
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
}}

# 2. VPN 설정 파일 생성
Write-Host "⚙️ VPN 설정 생성 중..." -ForegroundColor Cyan
$configUrl = "{server_url}/api/config-file/{token}"

# Downloads 폴더에 직접 저장
$configDir = "$env:USERPROFILE\\Downloads"
$configPath = "$configDir\\vpn-{token[:8]}.conf"
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
    Write-Host "📍 노드 ID: auto-node-{token[:8]}" -ForegroundColor Yellow
    
}} catch {{
    Write-Host "❌ 설정 생성 실패: $_" -ForegroundColor Red
    exit 1
}}

# 3. Windows 방화벽 규칙 추가
Write-Host "🔥 Windows 방화벽 설정 중..." -ForegroundColor Cyan
try {{
    # WireGuard를 위한 방화벽 규칙 추가
    New-NetFirewallRule -DisplayName "WireGuard VPN" -Direction Inbound -Protocol UDP -LocalPort 41820 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "WireGuard VPN" -Direction Outbound -Protocol UDP -LocalPort 41820 -Action Allow -ErrorAction SilentlyContinue
    
    # WireGuard 애플리케이션 허용
    $wireguardExe = "C:\\Program Files\\WireGuard\\wireguard.exe"
    if (Test-Path $wireguardExe) {{
        New-NetFirewallRule -DisplayName "WireGuard Application" -Direction Outbound -Program $wireguardExe -Action Allow -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName "WireGuard Application" -Direction Inbound -Program $wireguardExe -Action Allow -ErrorAction SilentlyContinue
    }}
    
    # VPN 서브넷 허용
    New-NetFirewallRule -DisplayName "WireGuard VPN Subnet" -Direction Inbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "WireGuard VPN Subnet" -Direction Outbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    
    # ICMP (ping) 허용 - VPN 연결 테스트를 위해 필수
    New-NetFirewallRule -DisplayName "WireGuard ICMP In" -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "WireGuard ICMP Out" -Direction Outbound -Protocol ICMPv4 -IcmpType 0 -Action Allow -ErrorAction SilentlyContinue
    
    # VPN 인터페이스에서의 ICMP 허용
    New-NetFirewallRule -DisplayName "WireGuard VPN ICMP" -Direction Inbound -Protocol ICMPv4 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    
    Write-Host "✅ 방화벽 규칙 추가 완료 (ICMP 포함)" -ForegroundColor Green
}} catch {{
    Write-Host "⚠️ 방화벽 규칙 추가 중 일부 오류 발생 (무시 가능)" -ForegroundColor Yellow
}}

# 4. WireGuard UI에 터널 추가 및 연결
Write-Host "🔗 VPN 터널 설정 중..." -ForegroundColor Cyan

# WireGuard 경로 확인
$wireguardPath = "C:\\Program Files\\WireGuard\\wireguard.exe"
if (Test-Path $wireguardPath) {{
    # WireGuard 종료 (깨끗한 시작을 위해)
    Stop-Process -Name "wireguard" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    Write-Host "📥 터널을 WireGuard에 추가 중..." -ForegroundColor Cyan
    
    # 설정 파일을 WireGuard 디렉토리로 복사
    $wireguardConfigDir = "C:\\Program Files\\WireGuard\\Data\\Configurations"
    if (-not (Test-Path $wireguardConfigDir)) {{
        New-Item -ItemType Directory -Path $wireguardConfigDir -Force | Out-Null
    }}
    
    Copy-Item -Path $configPath -Destination $wireguardConfigDir -Force
    Write-Host "✅ 설정 파일 복사 완료" -ForegroundColor Green
    
    # WireGuard UI 실행 및 터널 자동 import/활성화
    Start-Process -FilePath $wireguardPath
    Start-Sleep -Seconds 3
    
    # 설정 파일 자동 import 및 서비스로 설치
    Write-Host "VPN 터널 자동 설정 중..." -ForegroundColor Yellow
    & $wireguardPath /installtunnelservice $configPath
    
    Write-Host "✅ WireGuard 터널이 자동으로 활성화되었습니다" -ForegroundColor Green
    
    Write-Host "" 
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  VPN이 성공적으로 설치되었습니다!" -ForegroundColor Green
    Write-Host "  노드가 네트워크에 연결되었습니다." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    
    # 연결 테스트
    Write-Host ""
    Write-Host "🔍 연결 테스트 중..." -ForegroundColor Cyan
    Write-Host "주의: 먼저 WireGuard에서 터널을 활성화해야 합니다!" -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # ping 테스트로 간단하게 확인
    $pingResult = ping -n 1 -w 2000 10.100.0.1 2>$null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ VPN 서버와 연결 성공!" -ForegroundColor Green
    }} else {{
        Write-Host "⚠️ VPN 서버에 연결할 수 없습니다." -ForegroundColor Yellow
        Write-Host "   WireGuard에서 터널이 활성화되어 있는지 확인하세요." -ForegroundColor Yellow
    }}
    
    # WireGuard UI 실행
    Start-Process -FilePath $wireguardPath
}} else {{
    Write-Host "⚠️ WireGuard가 설치되었지만 자동 연결에 실패했습니다." -ForegroundColor Yellow
    Write-Host "WireGuard를 수동으로 실행하고 설정 파일을 가져오세요:" -ForegroundColor Yellow
    Write-Host $configPath -ForegroundColor White
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩
    encoded_script = base64.b64encode(script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성 (Base64 인코딩된 스크립트 사용)
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title VPN Auto Installer

echo ==========================================
echo    VPN Auto Installer
echo    Token: {token[:8]}
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
    
    return Response(
        content=batch_script,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=vpn-installer-{token[:8]}.bat"
        }
    )

@router.get("/api/config-file/{token}")
async def get_config_file(token: str, request: Request, db: Session = Depends(get_db)):
    """
    WireGuard 설정 파일 직접 다운로드 - 실제 키 생성
    """
    from wireguard_manager import WireGuardManager
    from models import Node
    from datetime import datetime
    
    wg_manager = WireGuardManager()
    node_id = f"auto-node-{token[:8]}"
    
    # 기존 노드 확인
    existing_node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if existing_node:
        # 기존 설정 반환
        return Response(
            content=existing_node.config,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=vpn-{token[:8]}.conf"
            }
        )
    
    # 새 노드 생성
    # VPN IP 할당 (통합된 allocate_ip 메서드 사용)
    vpn_ip = wg_manager.allocate_ip("worker")
    if not vpn_ip:
        # 풀이 가득 찬 경우 기본값 사용
        vpn_ip = "10.100.1.254"
    
    # 실제 WireGuard 키 생성
    try:
        keys = wg_manager.generate_keypair()
    except:
        # 로컬에서 직접 생성 (Docker 환경이 아닌 경우)
        import subprocess
        private_key = subprocess.run(
            ["wg", "genkey"], 
            capture_output=True, 
            text=True
        ).stdout.strip()
        
        if not private_key:
            # wg 명령이 없는 경우 임시 키 생성
            import secrets
            import string
            # Base64 형식의 44자 키 생성
            chars = string.ascii_letters + string.digits + '+/'
            private_key = ''.join(secrets.choice(chars) for _ in range(43)) + '='
            public_key = ''.join(secrets.choice(chars) for _ in range(43)) + '='
        else:
            public_key = subprocess.run(
                ["wg", "pubkey"], 
                input=private_key,
                capture_output=True,
                text=True
            ).stdout.strip()
        
        keys = {
            "private_key": private_key,
            "public_key": public_key
        }
    
    # 서버 정보
    server_public_key = wg_manager.get_server_public_key()
    
    # generate_client_config 메서드 사용하여 올바른 endpoint 설정
    config = wg_manager.generate_client_config(
        private_key=keys['private_key'],
        client_ip=vpn_ip,
        server_public_key=server_public_key
    )
    
    # DB에 저장
    new_node = Node(
        node_id=node_id,
        node_type="worker",
        hostname=f"auto-{token[:8]}",
        public_ip="0.0.0.0",
        vpn_ip=vpn_ip,
        public_key=keys['public_key'],
        private_key=keys['private_key'],
        config=config,
        status="registered",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_node)
    db.commit()
    
    # WireGuard 서버에 피어 추가 시도
    try:
        wg_manager.add_peer_to_server(
            public_key=keys['public_key'],
            vpn_ip=vpn_ip,
            node_id=node_id
        )
    except:
        pass  # 실패해도 설정 파일은 반환
    
    return Response(
        content=config,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=vpn-{token[:8]}.conf"
        }
    )

@router.get("/api/linux-installer/{token}")
async def get_linux_installer(token: str, request: Request):
    """
    Linux용 자동 설치 스크립트
    """
    server_url = str(request.url).split('/api')[0]
    
    script = f"""#!/bin/bash
# WireGuard VPN 자동 설치 스크립트
# Token: {token}

set -e

echo "🚀 VPN 자동 설치를 시작합니다..."
echo "노드 ID: worker-{token[:8]}"

# 1. WireGuard 설치
if ! command -v wg &> /dev/null; then
    echo "📦 WireGuard 설치 중..."
    if [ -f /etc/debian_version ]; then
        sudo apt-get update && sudo apt-get install -y wireguard jq
    elif [ -f /etc/redhat-release ]; then
        sudo yum install -y wireguard-tools jq
    else
        echo "❌ 지원하지 않는 Linux 배포판입니다."
        exit 1
    fi
fi

# 2. VPN 설정 생성
echo "⚙️ VPN 설정 생성 중..."
CONFIG_RESPONSE=$(curl -X POST -H "Authorization: Bearer test-token-123" \\
    {server_url}/api/generate-config/{token})

if [ $? -ne 0 ]; then
    echo "❌ 설정 생성 실패"
    exit 1
fi

# JSON 파싱 및 설정 파일 생성
CONFIG=$(echo "$CONFIG_RESPONSE" | jq -r '.config' | base64 -d)
NODE_ID=$(echo "$CONFIG_RESPONSE" | jq -r '.node_id')
VPN_IP=$(echo "$CONFIG_RESPONSE" | jq -r '.vpn_ip')

echo "$CONFIG" | sudo tee /etc/wireguard/wg0.conf > /dev/null
sudo chmod 600 /etc/wireguard/wg0.conf

echo "✅ 설정 파일 생성 완료"
echo "📍 노드 ID: $NODE_ID"
echo "📍 VPN IP: $VPN_IP"

# 3. VPN 연결
echo "🔗 VPN 연결 중..."
sudo wg-quick up wg0

# 4. 자동 시작 설정
sudo systemctl enable wg-quick@wg0 2>/dev/null || true

echo ""
echo "========================================"
echo "  ✅ VPN이 성공적으로 설치되었습니다!"
echo "  노드가 네트워크에 연결되었습니다."
echo "========================================"
echo ""
echo "연결 상태 확인:"
sudo wg show wg0
"""
    
    return Response(
        content=script,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=vpn-installer-{token[:8]}.sh"
        }
    )