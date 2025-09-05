"""
Worker Node Docker Runner
워커노드 Docker 실행 파일 생성 모듈
"""

import json
from models import Node

def generate_worker_docker_runner(node: Node) -> str:
    """워커노드 Docker 실행 배치 파일 생성"""
    
    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # PowerShell 스크립트 생성 (Docker 실행만)
    powershell_script = f"""
# Worker Node Docker Runner
# Node ID: {node.node_id}
# VPN IP: {node.vpn_ip}

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  워커노드 Docker 실행 프로그램" -ForegroundColor Green
Write-Host "  노드 ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "  VPN IP: {node.vpn_ip}" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. VPN 연결 확인
Write-Host "🔍 VPN 연결 테스트 중..." -ForegroundColor Cyan
$pingResult = ping -n 2 -w 3000 10.100.0.1 2>$null
if ($LASTEXITCODE -eq 0) {{
    Write-Host "✅ VPN 서버와 연결 성공!" -ForegroundColor Green
}} else {{
    Write-Host "⚠️ VPN 연결을 확인하세요!" -ForegroundColor Yellow
    Write-Host "계속하시겠습니까? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne 'Y' -and $response -ne 'y') {{
        exit 0
    }}
}}

# 2. Docker Desktop 확인
Write-Host ""
Write-Host "🐳 Docker Desktop 확인 중..." -ForegroundColor Cyan

$dockerRunning = $false
try {{
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ Docker가 실행 중입니다" -ForegroundColor Green
        $dockerRunning = $true
    }}
}} catch {{}}

if (-not $dockerRunning) {{
    Write-Host "Docker Desktop을 시작해주세요..." -ForegroundColor Yellow
    Write-Host "Docker Desktop을 시작하고 Enter를 누르세요..." -ForegroundColor Cyan
    Read-Host
    
    # 다시 확인
    try {{
        docker ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {{
            $dockerRunning = $true
        }}
    }} catch {{}}
}}

if (-not $dockerRunning) {{
    Write-Host "❌ Docker Desktop을 시작할 수 없습니다." -ForegroundColor Red
    Write-Host "수동으로 Docker Desktop을 시작한 후 다시 실행하세요." -ForegroundColor Yellow
    Read-Host
    exit 1
}}

# 3. 작업 디렉토리 생성
Write-Host ""
Write-Host "📁 워커노드 작업 디렉토리 설정 중..." -ForegroundColor Cyan

$workDir = "$env:USERPROFILE\\intown-worker"
if (-not (Test-Path $workDir)) {{
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
}}

Set-Location $workDir
Write-Host "✅ 작업 디렉토리: $workDir" -ForegroundColor Green

# 4. .env 파일 생성
Write-Host ""
Write-Host "📝 환경 설정 파일 생성 중..." -ForegroundColor Cyan

$envContent = @"
# Worker Node Configuration
NODE_ID={node.node_id}
DESCRIPTION={docker_env.get('description', 'Worker Node')}
CENTRAL_SERVER_IP={docker_env.get('central_server_ip', '10.100.0.2')}
HOST_IP={node.vpn_ip}
API_TOKEN={docker_env.get('api_token', 'worker-token')}

# Docker Image
REGISTRY=docker.io
IMAGE_NAME=heoaa/worker-node-prod
TAG=v1.0

# Resource Limits
MEMORY_LIMIT=24g
"@

Set-Content -Path "$workDir\\.env" -Value $envContent -Encoding UTF8
Write-Host "✅ .env 파일 생성 완료" -ForegroundColor Green

# 5. docker-compose.yml 파일 생성
Write-Host ""
Write-Host "📝 Docker Compose 설정 파일 생성 중..." -ForegroundColor Cyan

$composeContent = @'
version: '3.8'
services:
  server:
    image: heoaa/worker-node-prod:v1.0
    container_name: worker-node-${{NODE_ID}}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - NODE_ID=${{NODE_ID}}
      - DESCRIPTION=${{DESCRIPTION}}
      - CENTRAL_SERVER_IP=${{CENTRAL_SERVER_IP}}
      - HOST_IP=${{HOST_IP}}
      - API_TOKEN=${{API_TOKEN}}
      - DOCKER_CONTAINER=true
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
    volumes:
      - ~/.cache/torch:/root/.cache/torch
      - ~/.cache/huggingface:/root/.cache/huggingface
      - /tmp/ray:/tmp/ray
      - //var/run/docker.sock:/var/run/docker.sock
    ports:
      - "8001:8001"    # Flask API 서버
      - "6379:6379"    # Redis / GCS
      - "10001:10001"  # Ray Client Server
      - "8265:8265"    # Ray Dashboard
    deploy:
      resources:
        limits:
          memory: ${{MEMORY_LIMIT:-24g}}
    restart: unless-stopped
'@

Set-Content -Path "$workDir\\docker-compose.yml" -Value $composeContent -Encoding UTF8
Write-Host "✅ Docker Compose 파일 생성 완료" -ForegroundColor Green

# 6. 기존 컨테이너 확인 및 정리
Write-Host ""
Write-Host "🔄 기존 컨테이너 확인 중..." -ForegroundColor Cyan

$existingContainers = docker ps -a --filter "name=worker-node" --format "table {{{{.Names}}}}" 2>$null
if ($existingContainers -and $existingContainers -match "worker-node") {{
    Write-Host "기존 워커노드 컨테이너가 있습니다." -ForegroundColor Yellow
    Write-Host "재시작하시겠습니까? (Y/N)" -ForegroundColor Cyan
    $restart = Read-Host
    
    if ($restart -eq 'Y' -or $restart -eq 'y') {{
        Write-Host "기존 컨테이너 중지 중..." -ForegroundColor Yellow
        docker-compose down 2>$null
        Start-Sleep -Seconds 2
        Write-Host "✅ 기존 컨테이너 정리 완료" -ForegroundColor Green
    }}
}}

# 7. 이미지 Pull
Write-Host ""
Write-Host "📥 Docker 이미지 다운로드 중..." -ForegroundColor Cyan
Write-Host "처음 실행 시 시간이 걸릴 수 있습니다..." -ForegroundColor Yellow

# Docker Hub 로그인 시도 (이미 로그인되어 있으면 스킵)
docker pull heoaa/worker-node-prod:v1.0
if ($LASTEXITCODE -ne 0) {{
    Write-Host "⚠️ 이미지를 찾을 수 없습니다. Docker Hub 로그인이 필요할 수 있습니다." -ForegroundColor Yellow
    Write-Host "docker login 후 다시 시도하거나, 이미지 이름을 확인하세요." -ForegroundColor Yellow
    Write-Host "계속 진행하시겠습니까? (Y/N)" -ForegroundColor Cyan
    $continue = Read-Host
    if ($continue -ne 'Y' -and $continue -ne 'y') {{
        exit 1
    }}
}}

# 8. 컨테이너 시작
Write-Host ""
Write-Host "🚀 워커노드 시작 중..." -ForegroundColor Cyan

docker-compose up -d

if ($LASTEXITCODE -eq 0) {{
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ✅ 워커노드가 성공적으로 시작되었습니다!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📍 워커노드 정보:" -ForegroundColor Yellow
    Write-Host "  - 노드 ID: {node.node_id}" -ForegroundColor White
    Write-Host "  - VPN IP: {node.vpn_ip}" -ForegroundColor White
    Write-Host "  - 중앙서버 IP: {docker_env.get('central_server_ip', '10.100.0.2')}" -ForegroundColor White
    Write-Host "  - API 포트: 8001" -ForegroundColor White
    Write-Host ""
    Write-Host "📁 작업 디렉토리: $workDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "유용한 명령어:" -ForegroundColor Yellow
    Write-Host "  상태 확인: docker-compose ps" -ForegroundColor White
    Write-Host "  로그 확인: docker-compose logs -f" -ForegroundColor White
    Write-Host "  재시작: docker-compose restart" -ForegroundColor White
    Write-Host "  중지: docker-compose down" -ForegroundColor White
}} else {{
    Write-Host ""
    Write-Host "❌ 워커노드 시작 실패" -ForegroundColor Red
    Write-Host "docker-compose logs 명령으로 오류를 확인하세요." -ForegroundColor Yellow
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩
    import base64
    encoded_script = base64.b64encode(powershell_script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title Worker Node Docker Runner - {node.node_id}

echo ==========================================
echo    Worker Node Docker Runner
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
echo Starting Docker containers...
echo.

:: Execute PowerShell script with encoded command
powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand "{encoded_script}"

if !errorLevel! equ 0 (
    echo.
    echo [+] Docker execution completed!
) else (
    echo.
    echo [!] Docker execution encountered some issues.
)

pause
exit /b
"""
    
    return batch_script