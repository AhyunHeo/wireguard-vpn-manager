"""
Simplified Central Server Docker Runner
템플릿 파일을 사용하는 간소화된 Docker Runner
"""
import json
from models import Node

def generate_simple_central_runner(node: Node) -> str:
    """간소화된 중앙서버 Docker Runner 생성"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # JWT 키 생성 (보안)
    jwt_key = metadata.get('jwt_secret_key', '2Yw1k3J8v3Qk1n2p5l6s7d3f9g0h1j2k3l4m5n6o7p3q9r0s1t2u3v4w5x6y7z3A9')
    
    # API 서버 주소 (실제 호스트)
    import os
    api_server = os.getenv("LOCAL_SERVER_IP", "192.168.0.68")
    
    # VPN 서버 IP (게이트웨이)
    vpn_parts = node.vpn_ip.split('.')
    vpn_gateway = f"{vpn_parts[0]}.{vpn_parts[1]}.{vpn_parts[2]}.1"
    
    # 간단한 배치 파일
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
title Central Server Docker Runner - {node.node_id}
color 0A

echo ==========================================
echo    Central Server Docker Runner
echo    Node ID: {node.node_id}
echo    VPN IP: {node.vpn_ip}
echo ==========================================
echo.

:: Check Docker installation
echo Checking Docker installation...
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo.
    echo Please install Docker Desktop from:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

:: Check Docker service
echo Checking Docker service...
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running!
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [+] Docker is ready
echo.

:: Check VPN connection (optional)
echo Checking VPN connection...
ping -n 1 {vpn_gateway} >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Cannot reach VPN gateway at {vpn_gateway}
    echo Make sure WireGuard VPN is connected
    echo Continuing with local setup...
) else (
    echo [+] VPN connection verified
)
echo.

:: Create work directory
set WORK_DIR=%USERPROFILE%\\intown-central
echo Creating work directory: %WORK_DIR%
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"

:: Create subdirectories
if not exist "config" mkdir config
if not exist "session_models" mkdir session_models
if not exist "uploads" mkdir uploads
if not exist "app\\data\\uploads" mkdir "app\\data\\uploads"

echo [+] Work directory ready: %CD%
echo.

:: Download docker-compose.yml from templates
echo Downloading docker-compose.yml...
curl -o docker-compose.yml "http://{api_server}:8090/api/templates/docker-compose-central.yml"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to download docker-compose.yml
    echo.
    echo Please ensure:
    echo   1. WireGuard VPN is connected
    echo   2. VPN Manager API is running on {api_server}:8090
    echo.
    echo Or download manually from:
    echo   http://{api_server}:8090/api/templates/docker-compose-central.yml
    echo.
    pause
    exit /b 1
)

:: Create .env file
echo Creating .env file...
(
echo # Auto-generated environment file
echo # Node: {node.node_id}
echo.
echo # VPN Configuration
echo VPN_IP={node.vpn_ip}
echo.
echo # Port Configuration
echo API_PORT={metadata.get('api_port', 8000)}
echo FL_PORT={metadata.get('fl_port', 5002)}
echo DB_PORT={metadata.get('db_port', 5432)}
echo MONGO_PORT={metadata.get('mongo_port', 27017)}
echo.
echo # Security
echo JWT_SECRET_KEY={jwt_key}
echo JWT_ALGORITHM=HS256
echo JWT_EXPIRE_MINUTES=240
echo.
echo # System
echo PYTHONUNBUFFERED=1
echo WS_MESSAGE_QUEUE_SIZE=100
) > .env

echo [+] Configuration files ready
echo.

:: Clean up existing containers
echo Cleaning up existing containers...
docker compose down 2>nul
echo.

:: Pull Docker images
echo Pulling Docker images...
docker compose pull
echo.

:: Start containers
echo Starting containers...
docker compose up -d

:: Check result
timeout /t 5 /nobreak >nul
echo.

:: Check if containers are running
docker compose ps

echo.
echo ==========================================
echo    Docker Runner Completed
echo ==========================================
echo.
echo Services should be available at:
echo   - API Server: http://{node.vpn_ip}:{metadata.get('api_port', 8000)}
echo   - FL Server:  http://{node.vpn_ip}:{metadata.get('fl_port', 5002)}
echo.
echo Useful commands:
echo   - View logs:    docker compose logs -f
echo   - Stop:         docker compose down
echo   - Restart:      docker compose restart
echo   - Status:       docker compose ps
echo.
pause
"""
    
    return batch_script