"""
Central Server Docker Runner
중앙서버 Docker 실행 파일 생성 모듈
"""

import json
from models import Node

def generate_central_docker_runner(node: Node) -> str:
    """중앙서버 Docker 실행 배치 파일 생성"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # PowerShell 스크립트 생성 (Docker 실행만)
    powershell_script = f"""
# Central Server Docker Runner
# VPN 설치 후 실행하는 Docker 설정 스크립트
# Node ID: {node.node_id}
# VPN IP: {node.vpn_ip}

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  중앙서버 Docker 실행 프로그램" -ForegroundColor Green
Write-Host "  노드 ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "  VPN IP: {node.vpn_ip}" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. VPN 연결 확인
Write-Host "🔍 VPN 연결 확인 중..." -ForegroundColor Cyan
$pingResult = ping -n 1 -w 2000 10.100.0.1 2>$null
if ($LASTEXITCODE -ne 0) {{
    Write-Host "❌ VPN이 연결되지 않았습니다!" -ForegroundColor Red
    Write-Host "먼저 WireGuard에서 터널을 활성화하세요." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "엔터키를 누르면 종료합니다..."
    Read-Host
    exit 1
}}
Write-Host "✅ VPN 연결 확인" -ForegroundColor Green

# 2. Docker Desktop 확인
Write-Host ""
Write-Host "🐳 Docker Desktop 확인 중..." -ForegroundColor Cyan

$dockerRunning = $false
$maxRetries = 3
$retryCount = 0

while ($retryCount -lt $maxRetries -and -not $dockerRunning) {{
    try {{
        $dockerInfo = docker info 2>&1
        if ($dockerInfo -notmatch "error" -and $dockerInfo -notmatch "cannot connect") {{
            $dockerRunning = $true
        }}
    }} catch {{
        # docker 명령어가 없는 경우
    }}
    
    if (-not $dockerRunning) {{
        $retryCount++
        if ($retryCount -lt $maxRetries) {{
            Write-Host "Docker Desktop이 실행되지 않았습니다. 시작 시도 중... ($retryCount/$maxRetries)" -ForegroundColor Yellow
            
            # Docker Desktop 시작 시도
            $dockerPath = "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"
            if (Test-Path $dockerPath) {{
                Start-Process -FilePath $dockerPath
                Write-Host "Docker Desktop 시작 중... 30초 대기" -ForegroundColor Yellow
                Start-Sleep -Seconds 30
            }} else {{
                Write-Host "Docker Desktop이 설치되지 않았습니다!" -ForegroundColor Red
                Write-Host "https://www.docker.com/products/docker-desktop/ 에서 설치하세요." -ForegroundColor Yellow
                Write-Host ""
                Write-Host "엔터키를 누르면 종료합니다..."
                Read-Host
                exit 1
            }}
        }}
    }}
}}

if (-not $dockerRunning) {{
    Write-Host "❌ Docker Desktop을 시작할 수 없습니다." -ForegroundColor Red
    Write-Host "수동으로 Docker Desktop을 시작한 후 다시 실행하세요." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "엔터키를 누르면 종료합니다..."
    Read-Host
    exit 1
}}

Write-Host "✅ Docker가 실행 중입니다" -ForegroundColor Green

# 3. 작업 디렉토리 생성
Write-Host ""
Write-Host "📁 중앙서버 작업 디렉토리 설정 중..." -ForegroundColor Cyan

$workDir = "$env:USERPROFILE\\central-server-vpn"
if (-not (Test-Path $workDir)) {{
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
}}

Set-Location $workDir
Write-Host "✅ 작업 디렉토리: $workDir" -ForegroundColor Green

# 필요한 하위 디렉토리 생성
$dirs = @("config", "session_models", "uploads", "app\\data\\uploads")
foreach ($dir in $dirs) {{
    $fullPath = Join-Path $workDir $dir
    if (-not (Test-Path $fullPath)) {{
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }}
}}

# 4. .env 파일 생성
Write-Host ""
Write-Host "📝 환경 설정 파일 생성 중..." -ForegroundColor Cyan

$envContent = @"
# VPN 설정
VPN_IP={node.vpn_ip}

# 포트 설정  
API_PORT={metadata.get('api_port', 8000)}
FL_PORT={metadata.get('fl_port', 5002)}
DASHBOARD_PORT={metadata.get('dashboard_port', 5000)}
DB_PORT={metadata.get('db_port', 5432)}
MONGO_PORT={metadata.get('mongo_port', 27017)}

# JWT 설정
JWT_SECRET_KEY=2Yw1k3J8v3Qk1n2p5l6s7d3f9g0h1j2k3l4m5n6o7p3q9r0s1t2u3v4w5x6y7z3A9
"@

Set-Content -Path "$workDir\\.env" -Value $envContent -Encoding UTF8
Write-Host "✅ .env 파일 생성 완료" -ForegroundColor Green

# 5. docker-compose.yml 파일 생성
Write-Host ""
Write-Host "📝 Docker Compose 설정 파일 생성 중..." -ForegroundColor Cyan

$composeContent = @'
# 중앙서버 VPN 전용 모드
version: '3.8'

services:
  api:
    image: heoaa/central-server:v1.0
    container_name: central-server-api
    ports:
      - "${{VPN_IP:-10.100.0.2}}:${{API_PORT:-8000}}:8000"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
      - ./app/data/uploads:/app/data/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${{JWT_SECRET_KEY}}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  fl-api:
    image: heoaa/central-server-fl:v1.0
    container_name: fl-server-api
    ports:
      - "${{VPN_IP:-10.100.0.2}}:${{FL_PORT:-5002}}:5002"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${{JWT_SECRET_KEY}}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      - FL_SERVER_PORT=${{FL_PORT:-5002}}
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  dashboard:
    image: heoaa/central-server-dashboard:v1.0
    container_name: central-dashboard
    ports:
      - "${{VPN_IP:-10.100.0.2}}:${{DASHBOARD_PORT:-5000}}:3000"
    environment:
      - REACT_APP_API_URL=http://${{VPN_IP:-10.100.0.2}}:${{API_PORT:-8000}}
      - REACT_APP_FL_API_URL=http://${{VPN_IP:-10.100.0.2}}:${{FL_PORT:-5002}}
    depends_on:
      - api
      - fl-api
    restart: unless-stopped

  db:
    image: postgres:latest
    container_name: central-server-db
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${{VPN_IP:-10.100.0.2}}:${{DB_PORT:-5432}}:5432"
    restart: unless-stopped

  redis:
    image: redis:latest
    container_name: central-server-redis
    ports:
      - "${{VPN_IP:-10.100.0.2}}:6379:6379"
    restart: unless-stopped

  mongo:
    image: mongo:latest
    container_name: central-server-mongo
    environment:
      MONGO_INITDB_DATABASE: ai_logs
    volumes:
      - mongo_data:/data/db
    ports:
      - "${{VPN_IP:-10.100.0.2}}:${{MONGO_PORT:-27017}}:27017"
    restart: unless-stopped

volumes:
  postgres_data:
  mongo_data:
'@

Set-Content -Path "$workDir\\docker-compose.yml" -Value $composeContent -Encoding UTF8
Write-Host "✅ Docker Compose 파일 생성 완료" -ForegroundColor Green

# 6. 기존 컨테이너 정리
Write-Host ""
Write-Host "🔄 기존 컨테이너 정리 중..." -ForegroundColor Cyan

docker-compose down 2>$null
if ($LASTEXITCODE -eq 0) {{
    Write-Host "✅ 기존 컨테이너 정리 완료" -ForegroundColor Green
}} else {{
    Write-Host "새로운 설치입니다." -ForegroundColor Yellow
}}

# 7. 이미지 Pull
Write-Host ""
Write-Host "📥 Docker 이미지 다운로드 중..." -ForegroundColor Cyan
Write-Host "처음 실행 시 시간이 걸릴 수 있습니다..." -ForegroundColor Yellow

docker-compose pull
if ($LASTEXITCODE -ne 0) {{
    Write-Host "⚠️ 일부 이미지 다운로드 실패 (계속 진행)" -ForegroundColor Yellow
}}

# 8. 컨테이너 시작
Write-Host ""
Write-Host "🚀 중앙서버 시작 중..." -ForegroundColor Cyan

docker-compose up -d

if ($LASTEXITCODE -eq 0) {{
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ✅ 중앙서버가 성공적으로 시작되었습니다!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📍 중앙서버 정보:" -ForegroundColor Yellow
    Write-Host "  - 서버 ID: {node.node_id}" -ForegroundColor White
    Write-Host "  - VPN IP: {node.vpn_ip}" -ForegroundColor White
    Write-Host "  - API: http://{node.vpn_ip}:{metadata.get('api_port', 8000)}" -ForegroundColor White
    Write-Host "  - FL Server: http://{node.vpn_ip}:{metadata.get('fl_port', 5002)}" -ForegroundColor White
    Write-Host "  - Dashboard: http://{node.vpn_ip}:{metadata.get('dashboard_port', 5000)}" -ForegroundColor White
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
    Write-Host "❌ 중앙서버 시작 실패" -ForegroundColor Red
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
title Central Server Docker Runner - {node.node_id}

echo ==========================================
echo    Central Server Docker Runner
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