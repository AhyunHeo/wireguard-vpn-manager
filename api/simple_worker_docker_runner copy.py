"""
Simplified Worker Node Docker Runner
워커노드용 간소화된 Docker Runner
"""
import json
from models import Node

# def generate_simple_worker_runner_linux(node: Node) -> str:
#     """Linux용 워커노드 Docker Runner 생성 (Host 네트워크 모드)"""
#     
#     metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
#     
#     # Docker 이미지 태그 설정
#     DOCKER_TAG = "latest"
#     
#     # 서버 설정
#     import os
#     server_ip = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
#     vpn_manager_url = f"http://{server_ip}:8090"
#     
#     if metadata.get('central_server_ip'):
#         central_ip = metadata.get('central_server_ip')
#         central_url = f"http://{central_ip}:8000"
#     else:
#         central_url = metadata.get('central_server_url') or node.central_server_url or os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
#         import re
#         central_ip_match = re.search(r'://([^:]+)', central_url)
#         central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
#     
#     # Linux bash 스크립트
#     bash_script = f"""#!/bin/bash
# set -e
# 
# echo "=========================================="
# echo "   Worker Node Docker Runner (Linux)"
# echo "   Node ID: {node.node_id}"
# echo "   VPN IP: {node.vpn_ip}"
# echo "=========================================="
# echo
# 
# # Clean up existing containers
# echo "Cleaning up existing containers..."
# docker stop node-server 2>/dev/null || true
# docker rm node-server 2>/dev/null || true
# docker compose down 2>/dev/null || true
# 
# # Kill any remaining Ray processes
# echo "Cleaning up Ray processes..."
# pkill -9 -f ray 2>/dev/null || true
# pkill -9 -f gcs_server 2>/dev/null || true
# pkill -9 -f raylet 2>/dev/null || true
# 
# # Download docker-compose.yml (Host network mode)
# echo "Downloading docker-compose.yml..."
# curl -o docker-compose.yml \\
#   "{vpn_manager_url}/api/templates/docker-compose-worker-host.yml?worker_id={node.node_id}" \\
#   || wget -O docker-compose.yml \\
#   "{vpn_manager_url}/api/templates/docker-compose-worker-host.yml?worker_id={node.node_id}"
# 
# # Set environment variables
# export NODE_ID={node.node_id}
# export DESCRIPTION="{metadata.get('description', 'Worker Node')}"
# export CENTRAL_SERVER_IP={central_ip}
# export CENTRAL_SERVER_URL=http://{central_ip}:8000
# export VPN_IP={node.vpn_ip}
# export HOST_IP={node.vpn_ip}
# export API_TOKEN={metadata.get('api_token', 'your-api-token')}
# export REGISTRY=docker.io
# export IMAGE_NAME=heoaa/worker-node-prod
# export TAG={DOCKER_TAG}
# export MEMORY_LIMIT=24g
# 
# # Create .env file
# cat > .env <<EOF
# NODE_ID={node.node_id}
# DESCRIPTION={metadata.get('description', 'Worker Node')}
# CENTRAL_SERVER_IP={central_ip}
# CENTRAL_SERVER_URL=http://{central_ip}:8000
# VPN_IP={node.vpn_ip}
# HOST_IP={node.vpn_ip}
# API_TOKEN={metadata.get('api_token', 'your-api-token')}
# REGISTRY=docker.io
# IMAGE_NAME=heoaa/worker-node-prod
# TAG={DOCKER_TAG}
# MEMORY_LIMIT=24g
# EOF
# 
# echo "Starting container with host network mode..."
# docker compose up -d
# 
# # Wait and check status
# sleep 5
# docker compose ps
# 
# echo
# echo "Container started successfully!"
# echo "Logs: docker compose logs -f"
# """
#     
#     return bash_script

def generate_simple_worker_runner(node: Node) -> str:
    """Windows용 워커노드 Docker Runner 생성"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # Docker 이미지 태그 설정 (한 곳에서 관리)
    DOCKER_TAG = "latest"  # v1.2, v1.3 등으로 변경 가능
    
    # API 서버 주소 (실제 호스트)
    import os
    # VPN Manager 서버 주소 - 호스트의 실제 IP 사용
    # VPN 연결 후에도 호스트 IP로 접속 (VPN은 라우팅용)
    server_ip = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
    vpn_manager_url = f"http://{server_ip}:8090"
    # 중앙서버 설정
    # metadata에 central_server_ip가 있으면 사용, 없으면 URL에서 추출
    if metadata.get('central_server_ip'):
        central_ip = metadata.get('central_server_ip')
        central_url = f"http://{central_ip}:8000"
    else:
        # 기존 방식: URL에서 IP 추출
        central_url = metadata.get('central_server_url') or node.central_server_url or os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
        import re
        central_ip_match = re.search(r'://([^:]+)', central_url)
        central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
    
    # VPN 서버 IP (게이트웨이)
    vpn_parts = node.vpn_ip.split('.')
    vpn_gateway = f"{vpn_parts[0]}.{vpn_parts[1]}.{vpn_parts[2]}.1"
    
    # 간단한 배치 파일
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
title Worker Node Docker Runner - {node.node_id}
color 0A

echo ==========================================
echo    Worker Node Docker Runner
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
set WORK_DIR=%USERPROFILE%\\intown-worker
echo Creating work directory: %WORK_DIR%
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"

:: Create subdirectories
if not exist "cache" mkdir cache
if not exist "cache\\torch" mkdir cache\\torch
if not exist "cache\\huggingface" mkdir cache\\huggingface
if not exist "data" mkdir data
if not exist "models" mkdir models

echo [+] Work directory ready: %CD%
echo.

:: Download latest docker-compose.yml from VPN Manager
echo Downloading latest docker-compose.yml from VPN Manager...
echo URL: {vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}
echo.

:: Try to download using curl
curl -o docker-compose.yml "{vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}" 2>nul
if errorlevel 1 (
    echo [WARNING] curl failed, trying PowerShell...
    :: Fallback to PowerShell if curl is not available
    powershell -Command "Invoke-WebRequest -Uri '{vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}' -OutFile 'docker-compose.yml' -UseBasicParsing" 2>nul
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to download docker-compose.yml
        echo.
        echo Please ensure:
        echo   1. VPN Manager API is running at {vpn_manager_url}
        echo   2. Node {node.node_id} is registered in the system
        echo.
        echo You can manually download from:
        echo   {vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}
        echo.
        pause
        exit /b 1
    )
)

echo [+] Successfully downloaded latest docker-compose.yml for node {node.node_id}

:: Create .env file
echo Creating .env file...
(
echo # Auto-generated environment file
echo # Node: {node.node_id}
echo.
echo # Node Configuration
echo NODE_ID={node.node_id}
echo DESCRIPTION={metadata.get('description', 'Worker Node')}
echo CENTRAL_SERVER_IP={central_ip}
echo CENTRAL_SERVER_URL=http://{central_ip}:8000
echo HOST_IP={node.vpn_ip}
echo VPN_IP={node.vpn_ip}
echo.
echo # API Token for authentication
echo API_TOKEN={metadata.get('api_token', 'your-api-token')}
echo.
echo # Docker Registry ^(optional^)
echo REGISTRY=docker.io
echo IMAGE_NAME=heoaa/worker-node-prod
echo TAG={DOCKER_TAG}
echo.
echo # Resource Limits
echo MEMORY_LIMIT=24g
echo.
echo # System
echo PYTHONUNBUFFERED=1
) > .env

echo [+] Configuration files ready
echo.

:: Clean up existing containers
echo Cleaning up existing containers...
docker compose down 2>nul
echo.

:: Login to Docker registry if needed
echo Checking Docker registry...
docker pull heoaa/worker-node-prod:{DOCKER_TAG} 2>nul
if errorlevel 1 (
    echo [WARNING] Cannot pull image. Make sure you have access to the registry.
    echo You may need to run: docker login
)
echo.

:: Start containers
echo Starting containers...
set NODE_ID={node.node_id}
set CENTRAL_SERVER_IP={central_ip}
set HOST_IP={node.vpn_ip}
set VPN_IP={node.vpn_ip}
set DESCRIPTION={metadata.get('description', 'Worker Node')}
set IMAGE_NAME=heoaa/worker-node-prod
set TAG={DOCKER_TAG}

echo Running docker compose up -d with environment variables...
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
echo [+] Using latest docker-compose.yml from VPN Manager
echo [+] Node ID: {node.node_id}
echo [+] VPN IP: {node.vpn_ip}
echo.
echo Services should be available at:
echo   - Worker API: http://{node.vpn_ip}:8001
echo   - Ray Dashboard: http://{node.vpn_ip}:8265
echo   - Redis: {node.vpn_ip}:6379
echo   - Central Server: http://{central_ip}:8000
echo.
echo Useful commands:
echo   - View logs:    docker compose logs -f
echo   - Stop:         docker compose down
echo   - Restart:      docker compose restart
echo   - Status:       docker compose ps
echo   - Update:       Re-run this script to get latest config
echo.
pause
"""
    
    return batch_script