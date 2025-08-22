"""
Worker Node Windows Installer Generator
워커노드용 Windows 설치 배치 파일 생성 모듈
"""

import json
import base64
from models import Node

def generate_worker_windows_installer(node: Node) -> str:
    """워커노드용 Windows 설치 배치 파일 생성"""
    
    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # 서버 URL 구성
    import os
    server_host = os.getenv('SERVERURL', 'localhost')
    if server_host == 'auto' or not server_host or server_host == 'localhost':
        server_host = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
    server_url = f"http://{server_host}:8090"
    
    # PowerShell 스크립트 생성 (간소화 버전)
    powershell_script = f"""
# Worker Node VPN Auto Installer
# Generated for: {node.node_id}
# VPN IP: {node.vpn_ip}

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  워커노드 VPN 자동 설치 프로그램" -ForegroundColor Green
Write-Host "  노드 ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "  VPN IP: {node.vpn_ip}" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. WireGuard 설치 확인
Write-Host "🔍 WireGuard 설치 확인 중..." -ForegroundColor Cyan
$wireguardPath = "C:\\Program Files\\WireGuard\\wireguard.exe"
if (-not (Test-Path $wireguardPath)) {{
    Write-Host "📥 WireGuard를 다운로드하고 설치 중..." -ForegroundColor Yellow
    
    $installerUrl = "https://download.wireguard.com/windows-client/wireguard-installer.exe"
    $installerPath = "$env:TEMP\\wireguard-installer.exe"
    
    try {{
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        Start-Process -FilePath $installerPath -ArgumentList "/qn" -Wait
        Write-Host "✅ WireGuard 설치 완료" -ForegroundColor Green
    }} catch {{
        Write-Host "❌ WireGuard 자동 설치 실패. 수동으로 설치해주세요." -ForegroundColor Red
        Write-Host "다운로드 URL: $installerUrl" -ForegroundColor Yellow
        exit 1
    }}
}} else {{
    Write-Host "✅ WireGuard가 이미 설치되어 있습니다" -ForegroundColor Green
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
    # WireGuard 포트
    New-NetFirewallRule -DisplayName "WireGuard VPN" -Direction Inbound -Protocol UDP -LocalPort 51820 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "WireGuard VPN" -Direction Outbound -Protocol UDP -LocalPort 51820 -Action Allow -ErrorAction SilentlyContinue
    
    # VPN 서브넷 허용
    New-NetFirewallRule -DisplayName "VPN Subnet Access" -Direction Inbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN Subnet Access" -Direction Outbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    
    # ICMP 허용
    New-NetFirewallRule -DisplayName "VPN ICMP In" -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN ICMP Out" -Direction Outbound -Protocol ICMPv4 -IcmpType 0 -Action Allow -ErrorAction SilentlyContinue
    
    # 워커노드 포트 (필요시)
    New-NetFirewallRule -DisplayName "Worker Node Port" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -ErrorAction SilentlyContinue
    
    Write-Host "✅ 방화벽 규칙 추가 완료" -ForegroundColor Green
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
    
    # 기존 충돌 터널 제거
    Write-Host "🔄 기존 터널 정리 중..." -ForegroundColor Yellow
    try {{
        # 기존 {node.node_id} 터널 서비스 중지 및 삭제
        $existingService = Get-Service -Name "WireGuardTunnel`${node.node_id}" -ErrorAction SilentlyContinue
        if ($existingService) {{
            Stop-Service -Name "WireGuardTunnel`${node.node_id}" -Force -ErrorAction SilentlyContinue
            sc.exe delete "WireGuardTunnel`${node.node_id}" 2>$null
            Write-Host "✅ 기존 터널 서비스 제거" -ForegroundColor Green
        }}
        
        # 기존 설정 파일 삭제
        $wireguardConfigDir = "C:\\Program Files\\WireGuard\\Data\\Configurations"
        if (Test-Path $wireguardConfigDir) {{
            Remove-Item "$wireguardConfigDir\\{node.node_id}.conf*" -Force -ErrorAction SilentlyContinue
            Remove-Item "$wireguardConfigDir\\{node.node_id}_*.conf*" -Force -ErrorAction SilentlyContinue
        }}
    }} catch {{
        Write-Host "⚠️ 기존 터널 정리 중 일부 오류 (무시 가능)" -ForegroundColor Yellow
    }}
    
    # 설정 파일을 WireGuard 디렉토리로 복사
    if (-not (Test-Path $wireguardConfigDir)) {{
        New-Item -ItemType Directory -Path $wireguardConfigDir -Force | Out-Null
    }}
    
    # 설정 파일 복사
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
    Write-Host "  노드가 네트워크에 연결되었습니다." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
}} else {{
    Write-Host "⚠️ WireGuard가 설치되었지만 자동 연결에 실패했습니다." -ForegroundColor Yellow
    Write-Host "WireGuard를 수동으로 실행하고 설정 파일을 가져오세요:" -ForegroundColor Yellow
    Write-Host $configPath -ForegroundColor White
}}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ VPN 설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 연결 테스트
Write-Host "🔍 연결 테스트 중..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

$pingResult = ping -n 1 -w 2000 10.100.0.1 2>$null
if ($LASTEXITCODE -eq 0) {{
    Write-Host "✅ VPN 서버와 연결 성공!" -ForegroundColor Green
    
    # 중앙서버 연결 테스트
    $centralPing = ping -n 1 -w 2000 {docker_env.get('CENTRAL_SERVER_IP', '10.100.0.2')} 2>$null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ 중앙서버와 연결 성공!" -ForegroundColor Green
    }} else {{
        Write-Host "⚠️ 중앙서버에 연결할 수 없습니다. 중앙서버가 실행 중인지 확인하세요." -ForegroundColor Yellow
    }}
    
    # 5. Docker Desktop 확인 및 워커노드 실행
    Write-Host ""
    Write-Host "🐳 Docker Desktop 확인 중..." -ForegroundColor Cyan
    
    try {{
        # Docker 실행 상태 확인 (더 신뢰할 수 있는 방법)
        $dockerRunning = $false
        try {{
            $dockerInfo = docker info 2>&1
            if ($dockerInfo -notmatch "error" -and $dockerInfo -notmatch "cannot connect") {{
                $dockerRunning = $true
            }}
        }} catch {{
            # docker 명령어가 없는 경우
        }}
        
        if (-not $dockerRunning) {{
            # docker-desktop.exe 프로세스 확인
            $dockerDesktop = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
            if ($dockerDesktop) {{
                Write-Host "⏳ Docker Desktop이 시작 중입니다. 잠시 기다려주세요..." -ForegroundColor Yellow
                Start-Sleep -Seconds 10
                
                # 다시 확인
                try {{
                    $dockerInfo = docker info 2>&1
                    if ($dockerInfo -notmatch "error" -and $dockerInfo -notmatch "cannot connect") {{
                        $dockerRunning = $true
                    }}
                }} catch {{}}
            }}
        }}
        
        if ($dockerRunning) {{
            Write-Host "✅ Docker가 실행 중입니다" -ForegroundColor Green
        }} else {{
            throw "Docker is not running"
        }}
        
        # 작업 디렉토리 생성
        Write-Host ""
        Write-Host "📁 워커노드 작업 디렉토리 생성 중..." -ForegroundColor Cyan
        
        $workDir = "$env:USERPROFILE\\{node.node_id}"
        if (-not (Test-Path $workDir)) {{
            New-Item -ItemType Directory -Path $workDir -Force | Out-Null
        }}
        
        Set-Location $workDir
        Write-Host "✅ 작업 디렉토리: $workDir" -ForegroundColor Green
        
        # .env 파일 생성
        Write-Host ""
        Write-Host "📝 환경 설정 파일 생성 중..." -ForegroundColor Cyan
        
        $envContent = @"
# Worker Node Environment Variables
NODE_ID={docker_env.get('NODE_ID', node.node_id)}
DESCRIPTION={docker_env.get('DESCRIPTION', '')}
CENTRAL_SERVER_IP={docker_env.get('CENTRAL_SERVER_IP', '10.100.0.2')}
HOST_IP={node.vpn_ip}
API_TOKEN=test-token-123
REGISTRY=docker.io
IMAGE_NAME=worker-node-protected
TAG=latest
MEMORY_LIMIT=24g
"@
        
        Set-Content -Path "$workDir\\.env" -Value $envContent -Encoding UTF8
        Write-Host "✅ .env 파일 생성 완료" -ForegroundColor Green
        
        # docker-compose.yml 파일 생성
        Write-Host ""
        Write-Host "📝 Docker Compose 설정 파일 생성 중..." -ForegroundColor Cyan
        
        $composeContent = @"
version: '3.8'
services:
  server:
    # 보호된 이미지 사용 (레지스트리에서 pull)
    image: ${{REGISTRY:-docker.io}}/${{IMAGE_NAME:-worker-node-protected}}:${{TAG:-latest}}
    container_name: {node.node_id}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - NODE_ID=${{NODE_ID}}
      - DESCRIPTION=${{DESCRIPTION}}
      - CENTRAL_SERVER_IP=${{CENTRAL_SERVER_IP}}
      - HOST_IP=${{HOST_IP}}
      - API_TOKEN=${{API_TOKEN}}
      - DOCKER_CONTAINER=true
      - NCCL_DEBUG=INFO
      - NCCL_DEBUG_SUBSYS=ALL
      - TORCH_DISTRIBUTED_DEBUG=DETAIL
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
      - NCCL_SOCKET_FAMILY=AF_INET
      - NCCL_ASYNC_ERROR_HANDLING=1
      - NCCL_TIMEOUT=600
      - NCCL_RETRY_COUNT=10
      - NCCL_TREE_THRESHOLD=0
      - NCCL_BUFFSIZE=8388608
      - NCCL_IB_DISABLE=1
      - NCCL_P2P_DISABLE=1
      - NCCL_NSOCKS_PERTHREAD=4
      - NCCL_SOCKET_NTHREADS=1
      - NCCL_MAX_NCHANNELS=16
      - NCCL_MIN_NCHANNELS=4
      - NCCL_NET_GDR_LEVEL=0
      - NCCL_CHECKS_DISABLE=0
      - OMP_NUM_THREADS=1
      - MKL_NUM_THREADS=1
      - RAY_DISABLE_DASHBOARD=1
    volumes:
      # 캐시와 임시 파일만 마운트 (소스코드 마운트 없음)
      - ~/.cache/torch:/root/.cache/torch
      - ~/.cache/huggingface:/root/.cache/huggingface
      - /tmp/ray:/tmp/ray
      - /var/run/docker.sock:/var/run/docker.sock
    runtime: nvidia
    shm_size: '14gb'
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    privileged: false
    sysctls:
      net.ipv6.conf.all.disable_ipv6: "1"
      net.ipv6.conf.default.disable_ipv6: "1"
      net.ipv6.conf.lo.disable_ipv6: "1"
    ports:
      - "8001:8001"    # Flask API 서버
      - "6379:6379"    # Redis / GCS
      - "10001:10001"  # Ray Client Server
      - "8265:8265"    # Ray Dashboard
      - "8076:8076"    # ObjectManager
      - "8077:8077"    # NodeManager
      - "52365:52365"  # dashboard_agent_http
      - "52366:52366"  # dashboard_agent_grpc
      - "52367:52367"  # runtime_env_agent
      - "8090:8090"    # Metrics Export
      - "29500-29509:29500-29509"  # DDP TCPStore
      - "29510:29510"  # nccl_socket
      - "11000-11049:11000-11049"  # Ray Worker
      - "30000-30049:30000-30049"  # Ephemeral
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
              count: all
        limits:
          memory: ${{MEMORY_LIMIT:-24g}}
    ulimits:
      memlock:
        soft: -1
        hard: -1
      stack:
        soft: 67108864
        hard: 67108864
    restart: unless-stopped
"@
        
        Set-Content -Path "$workDir\\docker-compose.yml" -Value $composeContent -Encoding UTF8
        Write-Host "✅ Docker Compose 파일 생성 완료" -ForegroundColor Green
        
        # NVIDIA GPU 확인
        Write-Host ""
        Write-Host "🎮 GPU 확인 중..." -ForegroundColor Cyan
        
        $hasGPU = $false
        try {{
            nvidia-smi | Out-Null
            if ($LASTEXITCODE -eq 0) {{
                Write-Host "✅ NVIDIA GPU가 감지되었습니다" -ForegroundColor Green
                $hasGPU = $true
            }}
        }} catch {{
            Write-Host "⚠️ NVIDIA GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다." -ForegroundColor Yellow
        }}
        
        # Docker Compose 실행
        Write-Host ""
        Write-Host "🚀 워커노드 실행 중..." -ForegroundColor Cyan
        
        # 기존 컨테이너 중지
        docker-compose down 2>$null
        
        # 보호된 이미지 pull 및 실행
        Write-Host "보호된 이미지를 다운로드합니다..." -ForegroundColor Yellow
        
        if ($hasGPU) {{
            # GPU가 있는 경우
            docker-compose pull
            docker-compose up -d
        }} else {{
            # GPU가 없는 경우 runtime 제거
            $composeNoGPU = $composeContent -replace 'runtime: nvidia', '# runtime: nvidia (GPU not available)'
            $composeNoGPU = $composeNoGPU -replace '    deploy:[\s\S]*?    restart:', '    restart:'
            Set-Content -Path "$workDir\\docker-compose.yml" -Value $composeNoGPU -Encoding UTF8
            docker-compose pull
            docker-compose up -d
        }}
        
        Write-Host ""
        Write-Host "✅ 워커노드가 성공적으로 시작되었습니다!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📍 워커노드 정보:" -ForegroundColor Yellow
        Write-Host "  - 노드 ID: {node.node_id}" -ForegroundColor White
        Write-Host "  - VPN IP: {node.vpn_ip}" -ForegroundColor White
        Write-Host "  - 중앙서버: {docker_env.get('CENTRAL_SERVER_IP', '10.100.0.2')}" -ForegroundColor White
        Write-Host "  - API 포트: 8001" -ForegroundColor White
        Write-Host ""
        Write-Host "📁 작업 디렉토리: $workDir" -ForegroundColor Cyan
        Write-Host "상태 확인: docker-compose ps" -ForegroundColor Cyan
        Write-Host "로그 확인: docker-compose logs -f" -ForegroundColor Cyan
        
    }} catch {{
        Write-Host "⚠️ Docker Desktop이 실행되지 않았거나 설치되지 않았습니다" -ForegroundColor Yellow
        Write-Host "Docker Desktop 상태를 확인하세요:" -ForegroundColor Yellow
        Write-Host "  1. Docker Desktop이 설치되어 있는지 확인" -ForegroundColor White
        Write-Host "  2. Docker Desktop이 실행 중인지 확인 (시스템 트레이 확인)" -ForegroundColor White
        Write-Host "  3. Docker Desktop이 완전히 시작될 때까지 기다리기 (1-2분 소요)" -ForegroundColor White
        Write-Host ""
        Write-Host "Docker Desktop 실행 후 다음 단계를 진행하세요:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. 작업 디렉토리 생성: mkdir %USERPROFILE%\\{node.node_id}" -ForegroundColor White
        Write-Host "2. 해당 디렉토리로 이동: cd %USERPROFILE%\\{node.node_id}" -ForegroundColor White
        Write-Host "3. .env 파일 생성 (위 내용 참조)" -ForegroundColor White
        Write-Host "4. docker-compose.yml 파일 생성 (위 내용 참조)" -ForegroundColor White
        Write-Host "5. docker-compose up -d 실행" -ForegroundColor White
    }}
    
}} else {{
    Write-Host "⚠️ VPN 서버에 연결할 수 없습니다." -ForegroundColor Yellow
    Write-Host "   WireGuard에서 터널이 활성화되어 있는지 확인하세요." -ForegroundColor Yellow
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩
    encoded_script = base64.b64encode(powershell_script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title Worker Node VPN Installer - {node.node_id}

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

pause
exit /b
"""
    
    return batch_script