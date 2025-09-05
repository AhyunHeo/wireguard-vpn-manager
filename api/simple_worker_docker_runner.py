"""
Simplified Worker Node Docker Runner
워커노드용 간소화된 Docker Runner
"""
import json
from models import Node

def generate_simple_worker_runner_wsl(node: Node) -> str:
    """WSL용 워커노드 Docker Runner 생성 (Windows에서 WSL2 사용)"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # Docker 이미지 태그 설정
    DOCKER_TAG = "latest"
    
    # 서버 설정
    import os
    server_ip = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
    vpn_manager_url = f"http://{server_ip}:8090"
    
    if metadata.get('central_server_ip'):
        central_ip = metadata.get('central_server_ip')
    else:
        central_url = metadata.get('central_server_url') or node.central_server_url or os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
        import re
        central_ip_match = re.search(r'://([^:]+)', central_url)
        central_ip = central_ip_match.group(1) if central_ip_match else "192.168.0.88"
    
    # 자동 설치 기능이 포함된 배치 파일
    wsl_batch_script = r"""@echo off
setlocal enabledelayedexpansion

REM Auto-elevate to Administrator if needed
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ==========================================
echo    WSL Docker Runner for Worker Node
echo ==========================================
echo.
echo [+] Running with Administrator privileges
echo.

REM Check and install WSL
wsl --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] WSL is not installed. Installing WSL2...
    echo.
    echo This will install WSL2 with Ubuntu.
    echo Press Ctrl+C to cancel, or
    pause
    
    REM Install WSL2 with Ubuntu
    wsl --install -d Ubuntu
    
    echo.
    echo [IMPORTANT] WSL2 installation initiated!
    echo.
    echo Please:
    echo 1. Restart your computer after installation completes
    echo 2. Open Ubuntu from Start Menu and create a user
    echo 3. Run this script again
    echo.
    pause
    exit /b 0
)

echo [+] WSL is installed
echo.

REM Check Docker in WSL and auto-install if missing
echo Checking Docker in WSL...
wsl docker version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Docker is not installed in WSL. Installing Docker...
    echo.
    
    REM Install Docker in WSL (includes Docker Compose v2)
    wsl bash -c "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sudo sh /tmp/get-docker.sh && sudo usermod -aG docker $USER"
    
    echo.
    echo [INFO] Docker installation completed!
    echo [WARNING] You may need to restart WSL for Docker group changes to take effect
    echo.
    echo Restarting WSL...
    wsl --shutdown
    timeout /t 5 /nobreak >nul
    
    REM Test Docker again
    wsl docker version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Docker may require WSL restart. Please run:
        echo   1. wsl --shutdown
        echo   2. Run this script again
        echo.
        pause
        exit /b 1
    )
)

echo [+] Docker is ready in WSL
echo.

""" + f"""
REM Check if Windows VPN is connected
echo Checking VPN connection...
ipconfig | findstr /C:"{node.vpn_ip}" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] VPN IP {node.vpn_ip} not found!
    echo.
    echo Please connect to VPN first using:
    echo   1. Run the VPN installer ^(vpn-installer-{node.node_id}.bat^)
    echo   2. Or use WireGuard GUI to connect
    echo.
    echo After connecting VPN, run this script again.
    echo.
    pause
    exit /b 1
)

echo [+] VPN is connected with IP: {node.vpn_ip}
echo.

REM Get WSL2 IP address
echo Getting WSL2 IP address...
for /f "tokens=*" %%i in ('wsl hostname -I') do set WSL_IP=%%i
set WSL_IP=%WSL_IP: =%
echo [+] WSL2 IP: %WSL_IP%
echo.

REM Setup port forwarding from VPN IP to WSL2
echo Setting up port forwarding from VPN to WSL2...
echo.

REM Remove existing port forwarding rules
echo Cleaning up existing port forwarding...
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=8001 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=8265 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=6379 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=8076 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=8077 >nul 2>&1
netsh interface portproxy delete v4tov4 listenaddress={node.vpn_ip} listenport=10001 >nul 2>&1

REM Add new port forwarding rules
echo Adding port forwarding rules...

REM Worker API
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=8001 connectaddress=%WSL_IP% connectport=8001
echo [+] Worker API: {node.vpn_ip}:8001 -^> WSL2:8001

REM Ray Dashboard
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=8265 connectaddress=%WSL_IP% connectport=8265
echo [+] Ray Dashboard: {node.vpn_ip}:8265 -^> WSL2:8265

REM Redis
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=6379 connectaddress=%WSL_IP% connectport=6379
echo [+] Redis: {node.vpn_ip}:6379 -^> WSL2:6379

REM Ray ports
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=8076 connectaddress=%WSL_IP% connectport=8076
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=8077 connectaddress=%WSL_IP% connectport=8077
echo [+] Ray GCS: {node.vpn_ip}:8076-8077 -^> WSL2:8076-8077

REM Ray object manager
netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=10001 connectaddress=%WSL_IP% connectport=10001
echo [+] Ray Object Manager: {node.vpn_ip}:10001 -^> WSL2:10001

REM Add port ranges for distributed training
echo Adding port ranges for distributed training...
for /L %%p in (29500,1,29510) do (
    netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=%%p connectaddress=%WSL_IP% connectport=%%p >nul 2>&1
)
echo [+] PyTorch DDP ports: {node.vpn_ip}:29500-29510 -^> WSL2

for /L %%p in (11000,1,11020) do (
    netsh interface portproxy add v4tov4 listenaddress={node.vpn_ip} listenport=%%p connectaddress=%WSL_IP% connectport=%%p >nul 2>&1
)
echo [+] Ray worker ports: {node.vpn_ip}:11000-11020 -^> WSL2

echo.
echo [SUCCESS] Port forwarding configured!
echo.

""" + f"""
REM Create directory
wsl mkdir -p ~/worker-{node.node_id}

REM Clean up
wsl bash -c "cd ~/worker-{node.node_id} && docker compose down 2>/dev/null || true"

REM Download docker-compose.yml (bridge mode for WSL2)
echo Downloading docker-compose.yml...
wsl bash -c "cd ~/worker-{node.node_id} && wget -O docker-compose.yml '{vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}'"

REM Create .env file
echo Creating .env file...
wsl bash -c "cd ~/worker-{node.node_id} && echo 'NODE_ID={node.node_id}' > .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'DESCRIPTION={metadata.get('description', 'Worker Node')}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'CENTRAL_SERVER_IP={central_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'CENTRAL_SERVER_URL=http://{central_ip}:8000' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'VPN_IP={node.vpn_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'HOST_IP={node.vpn_ip}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'API_TOKEN={metadata.get('api_token', 'your-api-token')}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'REGISTRY=docker.io' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'IMAGE_NAME=heoaa/worker-node-prod' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'TAG={DOCKER_TAG}' >> .env"
wsl bash -c "cd ~/worker-{node.node_id} && echo 'MEMORY_LIMIT=24g' >> .env"

REM Start Docker Compose
echo Starting Docker Compose...
wsl bash -c "cd ~/worker-{node.node_id} && docker compose up -d"

REM Check status
timeout /t 5 /nobreak
wsl bash -c "cd ~/worker-{node.node_id} && docker compose ps"

echo.
echo ==========================================
echo    SETUP COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo Node ID: {node.node_id}
echo VPN IP: {node.vpn_ip}
echo.
echo [SUCCESS] Port forwarding is active!
echo.
echo Other VPN nodes can now access this worker at:
echo   - Worker API: http://{node.vpn_ip}:8001
echo   - Ray Dashboard: http://{node.vpn_ip}:8265
echo   - Redis: {node.vpn_ip}:6379
echo   - Ray GCS: {node.vpn_ip}:8076-8077
echo   - PyTorch DDP: {node.vpn_ip}:29500-29510
echo.
echo Local access from Windows:
echo   - Worker API: http://localhost:8001
echo   - Ray Dashboard: http://localhost:8265
echo.
echo Management commands:
echo   - View logs: wsl bash -c "cd ~/worker-{node.node_id} && docker compose logs -f"
echo   - Stop: wsl bash -c "cd ~/worker-{node.node_id} && docker compose down"
echo   - Restart: wsl bash -c "cd ~/worker-{node.node_id} && docker compose restart"
echo.
echo To view port forwarding rules:
echo   netsh interface portproxy show v4tov4
echo.
echo To remove port forwarding (when stopping):
echo   Run this script again to clean up old rules
echo.
pause
"""
    
    return wsl_batch_script


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

:: Detect OS type and download appropriate docker-compose.yml
echo Detecting OS type for appropriate network mode...

:: Windows doesn't support host network mode, use bridge mode with port mapping
echo [INFO] Windows detected - using bridge mode with port mapping
echo Downloading docker-compose.yml from VPN Manager...
echo URL: {vpn_manager_url}/api/templates/docker-compose-worker.yml?worker_id={node.node_id}
echo.

:: Try to download using curl (bridge mode for Windows)
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
echo [INFO] Using bridge mode (Windows limitation - host mode not supported)

:: Check for VPN config file and encode it
echo Checking for VPN configuration file...
set VPN_CONFIG_FILE=%USERPROFILE%\\Downloads\\{node.node_id}.conf
if exist "%VPN_CONFIG_FILE%" (
    echo [+] VPN config found: %VPN_CONFIG_FILE%
    echo Encoding VPN configuration...
    
    :: Base64 encode the VPN config file
    powershell -Command "[Convert]::ToBase64String([System.IO.File]::ReadAllBytes('%VPN_CONFIG_FILE%'))" > vpn_config_base64.txt
    set /p VPN_CONFIG_BASE64=<vpn_config_base64.txt
    del vpn_config_base64.txt
    
    echo [+] VPN config encoded for container use
) else (
    echo [WARNING] VPN config not found at: %VPN_CONFIG_FILE%
    echo Container will run without internal VPN
    set VPN_CONFIG_BASE64=
)
echo.

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
echo.
echo # VPN Configuration for Container
echo VPN_CONFIG_BASE64=%VPN_CONFIG_BASE64%
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
echo [+] Using latest docker-compose.yml from VPN Manager (bridge mode for Windows)
echo [+] Node ID: {node.node_id}
echo [+] VPN IP: {node.vpn_ip}
if exist "%VPN_CONFIG_FILE%" (
    echo [+] VPN Config: Injected into container (will auto-connect)
) else (
    echo [!] VPN Config: Not found (using host network only)
)
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