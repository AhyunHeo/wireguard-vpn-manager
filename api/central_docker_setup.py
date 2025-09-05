"""
Central Server Docker Setup (VPN 없이 독립 실행)
중앙서버는 공개 IP를 사용하므로 VPN 설정 없이 Docker만 실행
"""

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/central/docker-setup")
async def central_docker_setup_page():
    """중앙서버 Docker 설정 페이지 (VPN 없음)"""
    
    # 환경변수에서 중앙서버 URL 가져오기
    central_url = os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중앙서버 Docker 설정</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }}
            h1 {{
                color: #2a5298;
                margin-bottom: 10px;
                font-size: 32px;
            }}
            .subtitle {{
                color: #666;
                margin-bottom: 30px;
                font-size: 16px;
            }}
            .section {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .section-title {{
                color: #333;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }}
            .section-title span {{
                margin-right: 10px;
            }}
            .code-block {{
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 8px;
                overflow-x: auto;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                position: relative;
                margin: 10px 0;
            }}
            .copy-btn {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
            }}
            .copy-btn:hover {{
                background: #45a049;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .info {{
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .download-btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 50px;
                font-size: 16px;
                cursor: pointer;
                margin: 20px 0;
                width: 100%;
                transition: transform 0.3s;
            }}
            .download-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
            .step {{
                display: flex;
                align-items: flex-start;
                margin: 15px 0;
            }}
            .step-number {{
                background: #2a5298;
                color: white;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                flex-shrink: 0;
                font-weight: bold;
            }}
            .env-vars {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }}
            .env-var {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }}
            .env-var:last-child {{
                border-bottom: none;
            }}
            .env-var-name {{
                font-weight: 600;
                color: #495057;
            }}
            .env-var-value {{
                color: #6c757d;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖥️ 중앙서버 Docker 설정</h1>
            <div class="subtitle">VPN 없이 독립적으로 실행되는 중앙서버 설정</div>
            
            <div class="warning">
                <strong>⚠️ 주의:</strong> 중앙서버는 공개 IP를 사용하므로 VPN 설정이 필요 없습니다.
            </div>
            
            <div class="section">
                <div class="section-title">
                    <span>📋</span> 서버 정보
                </div>
                <div class="env-vars">
                    <div class="env-var">
                        <span class="env-var-name">중앙서버 URL:</span>
                        <span class="env-var-value">{central_url}</span>
                    </div>
                    <div class="env-var">
                        <span class="env-var-name">API 포트:</span>
                        <span class="env-var-value">8000</span>
                    </div>
                    <div class="env-var">
                        <span class="env-var-name">Dashboard 포트:</span>
                        <span class="env-var-value">3000</span>
                    </div>
                    <div class="env-var">
                        <span class="env-var-name">네트워크 모드:</span>
                        <span class="env-var-value">Public IP (VPN 불필요)</span>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">
                    <span>🚀</span> 빠른 설치 (Windows)
                </div>
                <button class="download-btn" onclick="downloadInstaller()">
                    ⬇️ Windows 설치 스크립트 다운로드
                </button>
            </div>
            
            <div class="section">
                <div class="section-title">
                    <span>📝</span> Docker Compose 설정
                </div>
                <div class="code-block">
                    <button class="copy-btn" onclick="copyCode('docker-compose')">복사</button>
                    <pre id="docker-compose">version: '3.8'

services:
  api:
    image: heoaa/central-server:v1.0
    container_name: central-server-api
    ports:
      - "0.0.0.0:8000:8000"
      - "0.0.0.0:3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${{JWT_SECRET_KEY:-your-secret-key}}
      - PUBLIC_URL={central_url}
    volumes:
      - ./config:/app/config
      - ./uploads:/app/uploads
    depends_on:
      - db
      - mongo
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    container_name: central-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=ai_db
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped

  mongo:
    image: mongo:latest
    container_name: central-mongo
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  redis:
    image: redis:latest
    container_name: central-redis
    restart: unless-stopped

volumes:
  db_data:
  mongo_data:</pre>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">
                    <span>⚙️</span> 수동 설치 단계
                </div>
                <div class="step">
                    <div class="step-number">1</div>
                    <div>
                        <strong>Docker & Docker Compose 설치</strong>
                        <div class="code-block">
                            <button class="copy-btn" onclick="copyCode('install-docker')">복사</button>
                            <pre id="install-docker"># Windows: Docker Desktop 설치
# https://www.docker.com/products/docker-desktop/

# Linux:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh</pre>
                        </div>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <div>
                        <strong>작업 디렉토리 생성</strong>
                        <div class="code-block">
                            <button class="copy-btn" onclick="copyCode('create-dir')">복사</button>
                            <pre id="create-dir">mkdir central-server
cd central-server</pre>
                        </div>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">3</div>
                    <div>
                        <strong>환경변수 파일 생성</strong>
                        <div class="code-block">
                            <button class="copy-btn" onclick="copyCode('env-file')">복사</button>
                            <pre id="env-file">cat > .env << EOF
JWT_SECRET_KEY=your-secret-key-here
PUBLIC_URL={central_url}
DB_PASSWORD=your-secure-password
EOF</pre>
                        </div>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">4</div>
                    <div>
                        <strong>Docker Compose 실행</strong>
                        <div class="code-block">
                            <button class="copy-btn" onclick="copyCode('run-docker')">복사</button>
                            <pre id="run-docker">docker-compose up -d</pre>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="info">
                <strong>💡 접속 정보:</strong>
                <ul style="margin-top: 10px; margin-left: 20px;">
                    <li>API Server: {central_url}</li>
                    <li>Dashboard: http://[서버IP]:3000</li>
                    <li>워커노드는 이 URL로 직접 접속합니다</li>
                </ul>
            </div>
        </div>
        
        <script>
            function copyCode(id) {{
                const element = document.getElementById(id);
                const text = element.textContent;
                navigator.clipboard.writeText(text).then(() => {{
                    const btn = element.previousElementSibling;
                    const originalText = btn.textContent;
                    btn.textContent = '✓ 복사됨';
                    setTimeout(() => {{
                        btn.textContent = originalText;
                    }}, 2000);
                }});
            }}
            
            function downloadInstaller() {{
                window.location.href = '/api/central/download-installer';
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/api/central/download-installer")
async def download_central_installer():
    """중앙서버 Windows 설치 스크립트 다운로드"""
    
    central_url = os.getenv("CENTRAL_SERVER_URL", "http://192.168.0.88:8000")
    
    script_content = f"""@echo off
chcp 65001 > nul
echo ====================================
echo   중앙서버 Docker 설치 프로그램
echo   (VPN 설정 불필요)
echo ====================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 관리자 권한이 필요합니다!
    echo 마우스 오른쪽 클릭 → "관리자 권한으로 실행"
    pause
    exit /b 1
)

echo [1/4] Docker Desktop 확인 중...
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Docker Desktop이 설치되지 않았습니다.
    echo https://www.docker.com/products/docker-desktop/ 에서 설치하세요.
    pause
    exit /b 1
)
echo ✅ Docker Desktop 확인 완료

echo.
echo [2/4] 작업 디렉토리 생성 중...
cd /d %USERPROFILE%
if not exist central-server mkdir central-server
cd central-server
echo ✅ 작업 디렉토리: %CD%

echo.
echo [3/4] Docker Compose 파일 생성 중...
(
echo version: '3.8'
echo.
echo services:
echo   api:
echo     image: heoaa/central-server:v1.0
echo     container_name: central-server-api
echo     ports:
echo       - "0.0.0.0:8000:8000"
echo       - "0.0.0.0:3000:3000"
echo     environment:
echo       - DATABASE_URL=postgresql://user:password@db:5432/ai_db
echo       - MONGODB_URL=mongodb://mongo:27017/ai_logs
echo       - JWT_SECRET_KEY=your-secret-key-here
echo       - PUBLIC_URL={central_url}
echo     volumes:
echo       - ./config:/app/config
echo       - ./uploads:/app/uploads
echo     depends_on:
echo       - db
echo       - mongo
echo       - redis
echo     restart: unless-stopped
echo.
echo   db:
echo     image: postgres:15
echo     container_name: central-db
echo     environment:
echo       - POSTGRES_USER=user
echo       - POSTGRES_PASSWORD=password
echo       - POSTGRES_DB=ai_db
echo     volumes:
echo       - db_data:/var/lib/postgresql/data
echo     restart: unless-stopped
echo.
echo   mongo:
echo     image: mongo:latest
echo     container_name: central-mongo
echo     volumes:
echo       - mongo_data:/data/db
echo     restart: unless-stopped
echo.
echo   redis:
echo     image: redis:latest
echo     container_name: central-redis
echo     restart: unless-stopped
echo.
echo volumes:
echo   db_data:
echo   mongo_data:
) > docker-compose.yml
echo ✅ Docker Compose 파일 생성 완료

echo.
echo [4/4] Docker 컨테이너 시작 중...
docker-compose down >nul 2>&1
docker-compose up -d

if %errorLevel% eq 0 (
    echo.
    echo ====================================
    echo ✅ 중앙서버 설치 완료!
    echo ====================================
    echo.
    echo 접속 정보:
    echo   - API Server: {central_url}
    echo   - Dashboard: http://localhost:3000
    echo.
    echo 서비스 상태 확인:
    docker ps --filter "name=central"
    echo.
) else (
    echo.
    echo ❌ Docker 컨테이너 시작 실패
    echo 로그 확인: docker-compose logs
)

pause
"""
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={{
            "Content-Disposition": "attachment; filename=install-central-server.bat"
        }}
    )