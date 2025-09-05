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

# 1. VPN 연결 확인 - 더 정확한 방법 사용
Write-Host "🔍 VPN 연결 확인 중..." -ForegroundColor Cyan

# WireGuard 인터페이스 직접 확인
$wgInterfaces = Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -match "WireGuard" }}

if ($wgInterfaces) {{
    Write-Host "✅ WireGuard 인터페이스 발견" -ForegroundColor Green
    
    # 할당된 IP 확인
    $vpnIpFound = $false
    foreach ($iface in $wgInterfaces) {{
        $ipAddresses = Get-NetIPAddress -InterfaceAlias $iface.Name -ErrorAction SilentlyContinue
        foreach ($ip in $ipAddresses) {{
            if ($ip.IPAddress -match "10\.100\." -or $ip.IPAddress -eq "{node.vpn_ip}") {{
                Write-Host "✅ VPN IP 확인: $($ip.IPAddress)" -ForegroundColor Green
                $vpnIpFound = $true
                break
            }}
        }}
        if ($vpnIpFound) {{ break }}
    }}
    
    if (-not $vpnIpFound) {{
        Write-Host "⚠️ VPN IP가 아직 할당되지 않았습니다." -ForegroundColor Yellow
        Write-Host "잠시 대기 중... (10초)" -ForegroundColor Cyan
        Start-Sleep -Seconds 10
        
        # 재확인
        foreach ($iface in $wgInterfaces) {{
            $ipAddresses = Get-NetIPAddress -InterfaceAlias $iface.Name -ErrorAction SilentlyContinue
            foreach ($ip in $ipAddresses) {{
                if ($ip.IPAddress -match "10\.100\." -or $ip.IPAddress -eq "{node.vpn_ip}") {{
                    Write-Host "✅ VPN IP 확인: $($ip.IPAddress)" -ForegroundColor Green
                    $vpnIpFound = $true
                    break
                }}
            }}
            if ($vpnIpFound) {{ break }}
        }}
    }}
    
    # VPN 서버 연결 테스트 (여러 방법 시도)
    $vpnConnected = $false
    
    # 방법 1: Test-NetConnection 사용 (더 정확)
    Write-Host "VPN 서버 연결 테스트 중..." -ForegroundColor Cyan
    try {{
        $testResult = Test-NetConnection -ComputerName 10.100.0.1 -Port 8090 -WarningAction SilentlyContinue
        if ($testResult.TcpTestSucceeded) {{
            Write-Host "✅ VPN 서버 포트 연결 성공 (10.100.0.1:8090)" -ForegroundColor Green
            $vpnConnected = $true
        }}
    }} catch {{
        # Test-NetConnection 실패 시 ping 시도
    }}
    
    # 방법 2: ping으로 재시도
    if (-not $vpnConnected) {{
        $pingResult = ping -n 2 -w 3000 10.100.0.1 2>$null
        if ($LASTEXITCODE -eq 0) {{
            Write-Host "✅ VPN 서버 ping 성공 (10.100.0.1)" -ForegroundColor Green
            $vpnConnected = $true
        }}
    }}
    
    if ($vpnConnected) {{
        Write-Host "✅ VPN 연결 완전히 확인됨!" -ForegroundColor Green
    }} else {{
        Write-Host "⚠️ VPN 인터페이스는 활성화되었으나 서버 연결 실패" -ForegroundColor Yellow
        Write-Host "   방화벽이나 라우팅 문제일 수 있습니다." -ForegroundColor Yellow
    }}
}} else {{
    Write-Host "⚠️ WireGuard 인터페이스를 찾을 수 없습니다." -ForegroundColor Yellow
    Write-Host "   WireGuard에서 터널을 활성화해주세요." -ForegroundColor Yellow
    
    # 그래도 ping 시도
    Write-Host "직접 연결 테스트 중..." -ForegroundColor Cyan
    $pingResult = ping -n 2 -w 3000 10.100.0.1 2>$null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ VPN 서버와 통신 가능 (다른 경로)" -ForegroundColor Green
        $vpnConnected = $true
    }}
}}

# 연결 실패 시 처리
if (-not $vpnConnected) {{
    Write-Host ""
    Write-Host "⚠️ VPN 서버에 연결할 수 없습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "문제 해결 방법:" -ForegroundColor Yellow
    Write-Host "1. WireGuard에서 터널이 활성화되어 있는지 확인" -ForegroundColor White
    Write-Host "2. Windows 방화벽에서 WireGuard 허용 확인" -ForegroundColor White
    Write-Host "3. VPN 서버(10.100.0.1)가 실행 중인지 확인" -ForegroundColor White
    Write-Host ""
    
    Write-Host "VPN 연결 없이도 Docker를 실행하시겠습니까? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -ne 'Y' -and $response -ne 'y') {{
        Write-Host ""
        Write-Host "Docker 실행을 취소합니다." -ForegroundColor Red
        Write-Host ""
        Write-Host "엔터키를 누르면 종료합니다..."
        Read-Host
        exit 0
    }}
    
    Write-Host "⚠️ VPN 없이 계속 진행합니다..." -ForegroundColor Yellow
}}

# 2. Docker Desktop 확인
Write-Host ""
Write-Host "🐳 Docker Desktop 확인 중..." -ForegroundColor Cyan

$dockerRunning = $false

# 먼저 Docker가 이미 실행 중인지 빠르게 확인
try {{
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ Docker가 이미 실행 중입니다" -ForegroundColor Green
        $dockerRunning = $true
    }}
}} catch {{
    # Docker 명령어 없음
}}

# Docker가 실행 중이 아니면 재시도
if (-not $dockerRunning) {{
    $maxRetries = 3
    $retryCount = 0
    
    while ($retryCount -lt $maxRetries -and -not $dockerRunning) {{
        $retryCount++
        Write-Host "Docker 상태 확인 중... ($retryCount/$maxRetries)" -ForegroundColor Cyan
        
        # docker 명령어로 직접 확인
        try {{
            docker version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {{
                Write-Host "✅ Docker 실행 확인" -ForegroundColor Green
                $dockerRunning = $true
            }}
        }} catch {{
            # docker 명령어 실패
        }}
        
        # 방법 2: Docker Desktop 프로세스 확인
        if (-not $dockerRunning) {{
            $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
            if ($dockerProcess) {{
                Write-Host "Docker Desktop 프로세스가 실행 중입니다. 초기화 대기 중..." -ForegroundColor Yellow
                
                # Docker 엔진이 준비될 때까지 대기
                $waitCount = 0
                while ($waitCount -lt 6 -and -not $dockerRunning) {{
                    Start-Sleep -Seconds 5
                    $waitCount++
                    
                    try {{
                        $dockerInfo = docker info 2>&1
                        if ($LASTEXITCODE -eq 0) {{
                            Write-Host "✅ Docker 엔진 준비 완료" -ForegroundColor Green
                            $dockerRunning = $true
                        }} else {{
                            Write-Host "  Docker 엔진 초기화 중... ($($waitCount*5)/30초)" -ForegroundColor Yellow
                        }}
                    }} catch {{
                        # 계속 대기
                    }}
                }}
            }}
        }}
        
        # Docker가 여전히 실행되지 않은 경우
        if (-not $dockerRunning -and $retryCount -lt $maxRetries) {{
        Write-Host "Docker Desktop 시작 시도 중..." -ForegroundColor Yellow
        
        # Docker Desktop 경로 확인 (여러 가능한 경로)
        $dockerPaths = @(
            "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
            "$env:ProgramFiles\\Docker\\Docker\\Docker Desktop.exe",
            "$env:LOCALAPPDATA\\Docker\\Docker Desktop.exe"
        )
        
        $dockerFound = $false
        foreach ($path in $dockerPaths) {{
            if (Test-Path $path) {{
                Write-Host "Docker Desktop 실행: $path" -ForegroundColor Cyan
                Start-Process -FilePath $path
                $dockerFound = $true
                Write-Host "Docker Desktop 시작 중... 45초 대기" -ForegroundColor Yellow
                Start-Sleep -Seconds 45
                break
            }}
        }}
        
        if (-not $dockerFound) {{
            Write-Host "⚠️ Docker Desktop 실행 파일을 찾을 수 없습니다." -ForegroundColor Yellow
            Write-Host "수동으로 Docker Desktop을 시작해주세요." -ForegroundColor Yellow
            
            # 사용자가 수동으로 시작할 시간을 줌
            Write-Host "Docker Desktop을 시작하고 Enter를 누르세요..." -ForegroundColor Cyan
            Read-Host
            
            # 다시 확인
            try {{
                $dockerInfo = docker info 2>&1
                if ($LASTEXITCODE -eq 0) {{
                    $dockerRunning = $true
                }}
            }} catch {{}}
        }}
    }}
    }} # while 루프 종료
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
# 중앙서버 VPN 전용 모드 (프론트엔드는 별도 실행)
version: '3.8'

services:
  api:
    image: heoaa/central-server:v1.0
    container_name: central-server-api
    ports:
      - "${{API_PORT:-8000}}:8000"
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
      - "${{FL_PORT:-5002}}:5002"
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

  db:
    image: postgres:latest
    container_name: central-server-db
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
      TZ: Asia/Seoul
      PGTZ: Asia/Seoul
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:${{DB_PORT:-5432}}:5432"
    restart: unless-stopped

  redis:
    image: redis:latest
    container_name: central-server-redis
    restart: unless-stopped

  mongo:
    image: mongo:latest
    container_name: central-server-mongo
    environment:
      MONGO_INITDB_DATABASE: ai_logs
      TZ: Asia/Seoul
    volumes:
      - mongo_data:/data/db
    ports:
      - "127.0.0.1:${{MONGO_PORT:-27017}}:27017"
    restart: unless-stopped

volumes:
  postgres_data:
  mongo_data:
'@

Set-Content -Path "$workDir\\docker-compose.yml" -Value $composeContent -Encoding UTF8
Write-Host "✅ Docker Compose 파일 생성 완료" -ForegroundColor Green

# 6. 기존 컨테이너 확인 및 정리
Write-Host ""
Write-Host "🔄 기존 컨테이너 확인 중..." -ForegroundColor Cyan

# 기존 중앙서버 컨테이너가 실행 중인지 확인
$existingContainers = docker ps --filter "name=central-server" --format "table {{.Names}}" 2>$null
if ($existingContainers -and $existingContainers -match "central-server") {{
    Write-Host "기존 중앙서버 컨테이너가 실행 중입니다." -ForegroundColor Yellow
    Write-Host "재시작하시겠습니까? (Y/N)" -ForegroundColor Cyan
    $restart = Read-Host
    
    if ($restart -eq 'Y' -or $restart -eq 'y') {{
        Write-Host "기존 컨테이너 중지 중..." -ForegroundColor Yellow
        docker compose down 2>$null
        Start-Sleep -Seconds 2
        Write-Host "✅ 기존 컨테이너 정리 완료" -ForegroundColor Green
    }} else {{
        Write-Host "기존 컨테이너를 유지합니다." -ForegroundColor Green
        Write-Host ""
        Write-Host "완료! 엔터키를 누르면 종료합니다..."
        Read-Host
        exit 0
    }}
}} else {{
    Write-Host "새로운 설치를 진행합니다." -ForegroundColor Green
}}

# 7. 이미지 Pull
Write-Host ""
Write-Host "📥 Docker 이미지 다운로드 중..." -ForegroundColor Cyan
Write-Host "처음 실행 시 시간이 걸릴 수 있습니다..." -ForegroundColor Yellow

docker compose pull
if ($LASTEXITCODE -ne 0) {{
    Write-Host "⚠️ 일부 이미지 다운로드 실패 (계속 진행)" -ForegroundColor Yellow
}}

# 8. 컨테이너 시작
Write-Host ""
Write-Host "🚀 중앙서버 시작 중..." -ForegroundColor Cyan

docker compose up -d

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
    Write-Host "  - Frontend: 별도 실행 필요 (npm run dev)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📁 작업 디렉토리: $workDir" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "⚠️ 프론트엔드 실행:" -ForegroundColor Yellow
    Write-Host "  1. frontend 디렉토리로 이동" -ForegroundColor White
    Write-Host "  2. npm install (최초 1회)" -ForegroundColor White
    Write-Host "  3. npm run dev" -ForegroundColor White
    Write-Host "  4. http://localhost:3000 접속" -ForegroundColor White
    Write-Host ""
    Write-Host "유용한 명령어:" -ForegroundColor Yellow
    Write-Host "  상태 확인: docker compose ps" -ForegroundColor White
    Write-Host "  로그 확인: docker compose logs -f" -ForegroundColor White
    Write-Host "  재시작: docker compose restart" -ForegroundColor White
    Write-Host "  중지: docker compose down" -ForegroundColor White
}} else {{
    Write-Host ""
    Write-Host "❌ 중앙서버 시작 실패" -ForegroundColor Red
    Write-Host "docker compose logs 명령으로 오류를 확인하세요." -ForegroundColor Yellow
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # 실행 가능한 배치 파일 생성 (PowerShell 스크립트를 파일로 저장)
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

:: Check Docker installation
where docker >nul 2>&1
if !errorLevel! neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

:: Check if Docker is running
docker version >nul 2>&1
if !errorLevel! neq 0 (
    echo [ERROR] Docker Desktop is not running.
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [+] Docker is installed and running
echo.

:: Save PowerShell script to temp file
set "PS_SCRIPT=%TEMP%\docker_runner_{node.node_id}.ps1"
echo Creating Docker runner script...

(
echo # Docker Runner PowerShell Script
echo # Node: {node.node_id}
echo # Generated at: {datetime.now().isoformat()}
echo.
echo Write-Host "========================================" -ForegroundColor Cyan
echo Write-Host "   Central Server Docker Setup" -ForegroundColor Cyan  
echo Write-Host "   Node ID: {node.node_id}" -ForegroundColor White
echo Write-Host "   VPN IP: {node.vpn_ip}" -ForegroundColor White
echo Write-Host "========================================" -ForegroundColor Cyan
echo.
echo # Change to work directory
echo $workDir = "{metadata.get('work_dir', 'C:\\intown-central')}"
echo if ^(^!^(Test-Path $workDir^)^) {{
echo     Write-Host "Creating work directory: $workDir" -ForegroundColor Yellow
echo     New-Item -ItemType Directory -Path $workDir -Force ^| Out-Null
echo }}
echo Set-Location $workDir
echo Write-Host "Work directory: $workDir" -ForegroundColor Green
echo.
echo # Check for existing containers
echo Write-Host "Checking for existing containers..." -ForegroundColor Cyan
echo $existing = docker ps -a --format "table {{{{.Names}}}}" ^| Select-String "central"
echo.
echo if ^($existing^) {{
echo     Write-Host "Found existing containers. Stopping..." -ForegroundColor Yellow
echo     docker compose down
echo     Start-Sleep -Seconds 2
echo }}
echo.
echo # Create docker-compose.yml
echo Write-Host "Creating docker-compose.yml..." -ForegroundColor Cyan
echo @"
echo {docker_compose_content}
echo "@ ^| Out-File -FilePath "docker-compose.yml" -Encoding UTF8
echo.
echo # Create .env file
echo Write-Host "Creating .env file..." -ForegroundColor Cyan
echo @"
echo {env_content}
echo "@ ^| Out-File -FilePath ".env" -Encoding UTF8
echo.
echo # Pull images
echo Write-Host "Pulling Docker images..." -ForegroundColor Cyan
echo docker compose pull
echo.
echo # Start containers
echo Write-Host "Starting containers..." -ForegroundColor Cyan
echo docker compose up -d
echo.
echo if ^($LASTEXITCODE -eq 0^) {{
echo     Write-Host "" 
echo     Write-Host "✅ Central server started successfully!" -ForegroundColor Green
echo     Write-Host "API: http://{node.vpn_ip}:{metadata.get('api_port', 8000)}" -ForegroundColor White
echo     Write-Host "FL Server: http://{node.vpn_ip}:{metadata.get('fl_port', 5002)}" -ForegroundColor White
echo }} else {{
echo     Write-Host "❌ Failed to start containers" -ForegroundColor Red
echo }}
) > "%PS_SCRIPT%"

:: Execute PowerShell script
echo.
echo Starting Docker containers...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: Clean up temp file
del "%PS_SCRIPT%" >nul 2>&1

echo.
echo [+] Docker Runner completed!
echo.
pause
exit /b
"""
    
    return batch_script