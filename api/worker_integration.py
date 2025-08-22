"""
Worker Node Integration API
VPN 등록과 워커노드 플랫폼 등록을 통합하는 API
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models import Node, QRToken
from wireguard_manager import WireGuardManager
from worker_windows_installer import generate_worker_windows_installer
from typing import Optional
import json
import logging
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
import secrets
import os

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class WorkerEnvironmentRequest(BaseModel):
    """워커노드 환경변수 설정 요청"""
    node_id: str
    description: str
    central_server_ip: Optional[str] = "10.100.0.1"
    hostname: Optional[str] = None

@router.get("/worker/setup")
async def worker_setup_page():
    """워커노드 설정 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>워커노드 통합 설정</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 100%;
                padding: 40px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }
            input, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .btn:active {
                transform: translateY(0);
            }
            .result {
                display: none;
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                text-align: center;
            }
            .qr-code {
                margin: 20px 0;
            }
            .qr-code img {
                max-width: 256px;
                border: 4px solid white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .install-link {
                display: inline-block;
                margin-top: 15px;
                padding: 10px 20px;
                background: #28a745;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
            }
            .install-link:hover {
                background: #218838;
            }
            .info-box {
                background: #e7f3ff;
                border-left: 4px solid #2196F3;
                padding: 12px;
                margin-top: 20px;
                border-radius: 4px;
            }
            .info-box p {
                color: #1976D2;
                font-size: 14px;
                line-height: 1.5;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 워커노드 통합 설정</h1>
            <p class="subtitle">VPN 설치와 워커노드 등록을 한 번에 완료합니다</p>
            
            <form id="workerForm">
                <div class="form-group">
                    <label for="node_id">노드 ID *</label>
                    <input type="text" id="node_id" name="node_id" required 
                           placeholder="예: worker-001" pattern="[a-zA-Z0-9_\-]+">
                </div>
                
                <div class="form-group">
                    <label for="description">설명 *</label>
                    <input type="text" id="description" name="description" required 
                           placeholder="예: GPU 서버 #1">
                </div>
                
                <div class="form-group">
                    <label for="hostname">호스트명</label>
                    <input type="text" id="hostname" name="hostname" 
                           placeholder="선택사항 (기본값: 노드 ID)">
                </div>
                
                <div class="form-group">
                    <label for="central_server_ip">중앙서버 VPN IP</label>
                    <input type="text" id="central_server_ip" name="central_server_ip" 
                           value="10.100.0.1" pattern="[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+">
                </div>
                
                <button type="submit" class="btn">QR 코드 생성</button>
            </form>
            
            <div class="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: #666;">QR 코드 생성 중...</p>
            </div>
            
            <div id="result" class="result">
                <h2 style="color: #333; margin-bottom: 20px;">✅ QR 코드 생성 완료</h2>
                <div class="qr-code" id="qrCode"></div>
                <p style="color: #666; margin-bottom: 10px;">또는 이 링크를 사용하세요:</p>
                <div>
                    <input type="text" id="installUrl" readonly 
                           style="margin-bottom: 10px; font-size: 14px;">
                    <button onclick="copyUrl()" class="btn" style="background: #28a745;">
                        📋 링크 복사
                    </button>
                </div>
                <div class="info-box">
                    <p>
                        <strong>설치 프로세스:</strong><br>
                        1. QR 코드 스캔 또는 링크 접속<br>
                        2. 자동으로 VPN 설치 시작<br>
                        3. VPN IP 자동 할당<br>
                        4. 워커노드 자동 등록<br>
                        5. Docker 환경변수 자동 설정
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('workerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                
                // 빈 값 제거
                Object.keys(data).forEach(key => {
                    if (!data[key]) delete data[key];
                });
                
                // 로딩 표시
                document.querySelector('.loading').style.display = 'block';
                document.querySelector('button[type="submit"]').disabled = true;
                
                try {
                    const response = await fetch('/worker/generate-qr', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (!response.ok) {
                        throw new Error('QR 코드 생성 실패');
                    }
                    
                    const result = await response.json();
                    
                    // QR 코드 표시
                    document.getElementById('qrCode').innerHTML = 
                        '<img src="' + result.qr_code + '" alt="QR Code">';
                    
                    // 설치 URL 표시
                    document.getElementById('installUrl').value = result.install_url;
                    
                    // 결과 표시
                    document.getElementById('result').style.display = 'block';
                    
                } catch (error) {
                    alert('오류: ' + error.message);
                } finally {
                    document.querySelector('.loading').style.display = 'none';
                    document.querySelector('button[type="submit"]').disabled = false;
                }
            });
            
            function copyUrl() {
                const urlInput = document.getElementById('installUrl');
                urlInput.select();
                document.execCommand('copy');
                
                // 복사 완료 피드백
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✅ 복사됨!';
                btn.style.background = '#28a745';
                
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.post("/worker/generate-qr")
async def generate_worker_qr(
    request: WorkerEnvironmentRequest,
    db: Session = Depends(get_db)
):
    """워커노드용 QR 코드 및 설치 링크 생성"""
    try:
        # 토큰 생성
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # 토큰 정보를 DB에 저장
        qr_token = QRToken(
            token=token,
            node_id=request.node_id,
            node_type="worker",
            expires_at=expires_at,
            used=False
        )
        db.add(qr_token)
        
        # 워커노드 메타데이터도 토큰과 함께 저장 (JSON 형태로)
        metadata = {
            "description": request.description,
            "central_server_ip": request.central_server_ip or "10.100.0.1",
            "hostname": request.hostname or request.node_id
        }
        
        # Node 테이블에 예비 등록 (config는 나중에 생성)
        new_node = Node(
            node_id=request.node_id,
            node_type="worker",
            hostname=request.hostname or request.node_id,
            description=request.description,
            central_server_ip=request.central_server_ip or "10.100.0.1",
            docker_env_vars=json.dumps(metadata),
            status="pending",  # 아직 VPN 설정 전
            vpn_ip="0.0.0.0",  # 임시값
            public_key="pending",
            private_key="pending",
            config="pending"
        )
        
        # 중복 체크 및 업데이트
        existing = db.query(Node).filter(Node.node_id == request.node_id).first()
        if existing:
            # 기존 노드가 있으면 메타데이터 업데이트
            existing.description = request.description
            existing.central_server_ip = request.central_server_ip or "10.100.0.1"
            existing.hostname = request.hostname or request.node_id
            existing.docker_env_vars = json.dumps(metadata)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # 새 노드 추가
            db.add(new_node)
        
        db.commit()
        
        # 설치 URL 생성
        # SERVERURL 환경변수 사용 (docker-compose.yml에서 설정)
        server_host = os.getenv('SERVERURL', 'localhost')
        if server_host == 'auto' or not server_host or server_host == 'localhost':
            # LOCAL_SERVER_IP 사용 (우선순위)
            server_host = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
        
        server_url = f"http://{server_host}:8090"
        install_url = f"{server_url}/worker/install/{token}"
        
        # QR 코드 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(install_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "token": token,
            "install_url": install_url,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "expires_at": expires_at.isoformat(),
            "node_id": request.node_id
        }
        
    except Exception as e:
        logger.error(f"Failed to generate QR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/worker/install/{token}")
async def worker_install_page(token: str, db: Session = Depends(get_db)):
    """워커노드 자동 설치 페이지"""
    
    # 토큰 확인
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        return HTMLResponse(content="<h1>❌ 유효하지 않은 토큰입니다</h1>", status_code=404)
    
    if datetime.now(timezone.utc) > qr_token.expires_at:
        return HTMLResponse(content="<h1>⏰ 만료된 토큰입니다</h1>", status_code=400)
    
    # 노드 정보 가져오기
    node = db.query(Node).filter(Node.node_id == qr_token.node_id).first()
    if not node:
        return HTMLResponse(content="<h1>❌ 노드 정보를 찾을 수 없습니다</h1>", status_code=404)
    
    # Node 테이블의 값 우선, 없으면 metadata에서 가져오기
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>워커노드 자동 설치</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                max-width: 600px;
                width: 100%;
                padding: 40px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            .info-card {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid #e0e0e0;
            }}
            .info-row:last-child {{
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }}
            .info-label {{
                font-weight: 600;
                color: #555;
            }}
            .info-value {{
                color: #333;
            }}
            .status {{
                text-align: center;
                margin: 30px 0;
            }}
            .status-icon {{
                font-size: 48px;
                margin-bottom: 10px;
            }}
            .btn {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }}
            .btn-success {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            }}
            .steps {{
                margin: 30px 0;
            }}
            .step {{
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                opacity: 0.5;
                transition: opacity 0.3s;
            }}
            .step.active {{
                opacity: 1;
            }}
            .step.completed {{
                opacity: 1;
            }}
            .step-icon {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: #e0e0e0;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-size: 14px;
            }}
            .step.active .step-icon {{
                background: #667eea;
                color: white;
                animation: pulse 1.5s infinite;
            }}
            .step.completed .step-icon {{
                background: #28a745;
                color: white;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
                100% {{ transform: scale(1); }}
            }}
            .code-block {{
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                overflow-x: auto;
            }}
            .loading {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-left: 10px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 워커노드 자동 설치</h1>
            
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">노드 ID:</span>
                    <span class="info-value">{qr_token.node_id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">설명:</span>
                    <span class="info-value">{node.description or metadata.get('description', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">중앙서버 IP:</span>
                    <span class="info-value">{node.central_server_ip or metadata.get('central_server_ip', '10.100.0.1')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">호스트명:</span>
                    <span class="info-value">{node.hostname or metadata.get('hostname', qr_token.node_id)}</span>
                </div>
            </div>
            
            <div class="steps" id="steps">
                <div class="step" id="step1">
                    <div class="step-icon">1</div>
                    <span>VPN 설정 생성 중...</span>
                </div>
                <div class="step" id="step2">
                    <div class="step-icon">2</div>
                    <span>VPN IP 할당 중...</span>
                </div>
                <div class="step" id="step3">
                    <div class="step-icon">3</div>
                    <span>워커노드 등록 준비 중...</span>
                </div>
                <div class="step" id="step4">
                    <div class="step-icon">4</div>
                    <span>설치 스크립트 생성 중...</span>
                </div>
            </div>
            
            <div class="status" id="statusSection">
                <div class="status-icon">⏳</div>
                <p>아래 버튼을 클릭하여 설치를 시작하세요</p>
            </div>
            
            <button class="btn" id="startBtn" onclick="startInstallation()">설치 시작</button>
            
            <div id="result" style="display: none; margin-top: 30px;">
                <h2 style="color: #28a745; margin-bottom: 20px;">✅ 설치 준비 완료!</h2>
                
                <div class="info-card">
                    <div class="info-row">
                        <span class="info-label">VPN IP:</span>
                        <span class="info-value" id="vpnIp">-</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">상태:</span>
                        <span class="info-value" style="color: #28a745;">등록 완료</span>
                    </div>
                </div>
                
                <h3 style="margin-top: 30px; margin-bottom: 10px;">설치 방법을 선택하세요:</h3>
                
                <div style="margin: 20px 0; padding: 15px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px;">
                    <h4 style="color: #856404; margin-bottom: 10px;">⚠️ 사전 설치 요구사항</h4>
                    <p style="color: #856404; font-size: 14px; line-height: 1.6; margin-bottom: 10px;">
                        워커노드 실행을 위해 <strong>Docker Desktop</strong>이 반드시 설치되어 있어야 합니다.
                    </p>
                    <div style="margin-top: 10px;">
                        <a href="https://www.docker.com/products/docker-desktop/" target="_blank" 
                           style="display: inline-block; padding: 8px 16px; background: #0066cc; color: white; 
                                  text-decoration: none; border-radius: 4px; font-size: 14px;">
                            🐳 Docker Desktop 다운로드
                        </a>
                        <span style="margin-left: 10px; color: #856404; font-size: 12px;">
                            (설치 후 Docker Desktop을 실행한 상태에서 진행하세요)
                        </span>
                    </div>
                </div>
                
                <div style="display: flex; gap: 20px; margin-top: 20px;">
                    <button class="btn btn-success" onclick="downloadWindowsInstaller()" style="flex: 1;">
                        🪟 Windows 설치 파일 다운로드 (.bat)
                    </button>
                    <button class="btn" onclick="showLinuxScript()" style="flex: 1; background: #6c757d;">
                        🐧 Linux/Mac 스크립트 보기
                    </button>
                </div>
                
                <div class="code-block" id="installScript" style="display: none;">
                    # 설치 스크립트 로딩 중...
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px;">
                    <p style="color: #1976D2; font-size: 14px; line-height: 1.6;">
                        <strong>다음 단계:</strong><br>
                        1. 위 스크립트를 다운로드하여 워커노드에서 실행<br>
                        2. 스크립트가 자동으로 VPN과 Docker 환경을 설정<br>
                        3. 워커노드 컨테이너가 자동으로 시작됨
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            let installData = null;
            
            // 페이지 로드 시 자동으로 설치 시작 여부 확인
            window.addEventListener('DOMContentLoaded', () => {{
                // URL 파라미터로 자동 시작 여부 확인 (선택사항)
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('autostart') === 'true') {{
                    setTimeout(() => startInstallation(), 1000);
                }}
            }});
            
            async function startInstallation() {{
                const btn = document.getElementById('startBtn');
                // 버튼 비활성화
                btn.disabled = true;
                btn.textContent = '설치 진행 중...';
                
                // 단계별 진행
                await updateStep(1, true);
                
                try {{
                    // API 호출하여 VPN 설정 및 워커노드 등록
                    const response = await fetch('/worker/process-installation/{qr_token.token}', {{
                        method: 'POST'
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('설치 실패');
                    }}
                    
                    installData = await response.json();
                    
                    // 단계 업데이트
                    await updateStep(1, false, true);
                    await updateStep(2, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(2, false, true);
                    await updateStep(3, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(3, false, true);
                    await updateStep(4, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(4, false, true);
                    
                    // 결과 표시
                    showResult(installData);
                    
                }} catch (error) {{
                    alert('설치 중 오류 발생: ' + error.message);
                    const btn = document.getElementById('startBtn');
                    btn.disabled = false;
                    btn.textContent = '설치 재시도';
                }}
            }}
            
            async function updateStep(stepNum, active, completed = false) {{
                const step = document.getElementById('step' + stepNum);
                if (active) {{
                    step.classList.add('active');
                }} else {{
                    step.classList.remove('active');
                }}
                if (completed) {{
                    step.classList.add('completed');
                    step.querySelector('.step-icon').textContent = '✓';
                }}
                await new Promise(r => setTimeout(r, 300));
            }}
            
            function showResult(data) {{
                document.getElementById('vpnIp').textContent = data.vpn_ip;
                if (data.install_script) {{
                    document.getElementById('installScript').textContent = data.install_script;
                }}
                document.getElementById('result').style.display = 'block';
                
                // 상태 업데이트
                document.querySelector('.status-icon').textContent = '✅';
                document.querySelector('.status p').textContent = '설치 준비가 완료되었습니다!';
                
                // 설치 시작 버튼 숨기기
                document.getElementById('startBtn').style.display = 'none';
            }}
            
            function downloadWindowsInstaller() {{
                if (!installData || !installData.windows_installer) {{
                    alert('아직 설치 프로세스가 완료되지 않았습니다.\\n\\n"설치 시작" 버튼을 먼저 클릭하여 설치 프로세스를 완료한 후 다운로드하세요.');
                    // 설치 시작 버튼이 숨겨진 경우 다시 표시
                    const btn = document.getElementById('startBtn');
                    if (btn && btn.style.display === 'none') {{
                        btn.style.display = 'block';
                    }}
                    if (btn) {{
                        btn.scrollIntoView({{ behavior: 'smooth' }});
                    }}
                    return;
                }}
                
                try {{
                    // 배치 파일용 MIME 타입 설정
                    const blob = new Blob([installData.windows_installer], {{ 
                        type: 'application/x-msdos-program' 
                    }});
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'install-worker-{qr_token.node_id}.bat';
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    
                    // 클린업
                    setTimeout(() => {{
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    }}, 100);
                }} catch (error) {{
                    console.error('Download error:', error);
                    alert('다운로드 중 오류가 발생했습니다: ' + error.message);
                }}
            }}
            
            function showLinuxScript() {{
                if (!installData || !installData.install_script) return;
                
                const scriptDiv = document.getElementById('installScript');
                const isVisible = scriptDiv.style.display === 'block';
                scriptDiv.style.display = isVisible ? 'none' : 'block';
                
                // 다운로드 버튼 관리
                const existingBtn = document.getElementById('linuxDownloadBtn');
                
                if (!isVisible) {{
                    // 스크립트를 보여줄 때만 다운로드 버튼 추가
                    if (!existingBtn) {{
                        const downloadBtn = document.createElement('button');
                        downloadBtn.id = 'linuxDownloadBtn';
                        downloadBtn.className = 'btn';
                        downloadBtn.style.marginTop = '10px';
                        downloadBtn.textContent = '📥 .sh 파일 다운로드';
                        downloadBtn.onclick = function() {{
                            const blob = new Blob([installData.install_script], {{ type: 'text/plain;charset=utf-8' }});
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = 'install-worker-{qr_token.node_id}.sh';
                            a.style.display = 'none';
                            document.body.appendChild(a);
                            a.click();
                            
                            setTimeout(() => {{
                                window.URL.revokeObjectURL(url);
                                document.body.removeChild(a);
                            }}, 100);
                        }};
                        scriptDiv.parentNode.insertBefore(downloadBtn, scriptDiv.nextSibling);
                    }}
                }} else {{
                    // 스크립트를 숨길 때 다운로드 버튼도 제거
                    if (existingBtn) {{
                        existingBtn.remove();
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/worker/process-installation/{token}")
async def process_worker_installation(
    token: str,
    db: Session = Depends(get_db)
):
    """워커노드 설치 처리 - VPN 등록 및 설정 생성"""
    
    # 토큰 확인
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    if datetime.now(timezone.utc) > qr_token.expires_at:
        raise HTTPException(status_code=400, detail="Token expired")
    
    # 노드 정보 가져오기
    node = db.query(Node).filter(Node.node_id == qr_token.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    try:
        # 이미 VPN이 설정된 경우
        if node.status != "pending":
            # Windows installer 생성
            windows_installer = generate_worker_windows_installer(node)
            
            return {
                "status": "existing",
                "node_id": node.node_id,
                "vpn_ip": node.vpn_ip,
                "install_script": generate_install_script(node),
                "windows_installer": windows_installer,
                "message": "Already configured"
            }
        
        # WireGuard 매니저 초기화
        wg_manager = WireGuardManager()
        
        # VPN IP 할당
        vpn_ip = wg_manager.allocate_ip("worker")
        if not vpn_ip:
            raise HTTPException(status_code=500, detail="Failed to allocate VPN IP")
        
        # WireGuard 키 생성
        keys = wg_manager.generate_keypair()
        
        # VPN 설정 생성
        config = wg_manager.generate_client_config(
            private_key=keys['private_key'],
            client_ip=vpn_ip,
            server_public_key=wg_manager.get_server_public_key()
        )
        
        # 노드 정보 업데이트
        node.vpn_ip = vpn_ip
        node.public_key = keys['public_key']
        node.private_key = keys['private_key']
        node.config = config
        node.status = "registered"
        node.updated_at = datetime.now(timezone.utc)
        
        # Docker 환경변수 업데이트
        metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
        docker_env = {
            "NODE_ID": node.node_id,
            "DESCRIPTION": node.description or metadata.get('description', ''),
            "CENTRAL_SERVER_IP": node.central_server_ip or metadata.get('central_server_ip', '10.100.0.1'),
            "HOST_IP": vpn_ip
        }
        node.docker_env_vars = json.dumps(docker_env)
        
        db.commit()
        
        # WireGuard 서버에 피어 추가
        try:
            wg_manager.add_peer_to_server(
                public_key=keys['public_key'],
                vpn_ip=vpn_ip,
                node_id=qr_token.node_id
            )
        except Exception as e:
            logger.error(f"Failed to add peer to server: {e}")
            # 서버 추가 실패해도 계속 진행 (나중에 sync 가능)
        
        # 토큰을 사용됨으로 표시
        qr_token.used = True
        db.commit()
        
        # 설치 스크립트 생성 (Windows 배치 파일)
        windows_installer = generate_worker_windows_installer(node)
        
        # Linux/Mac용 스크립트도 제공 (선택사항)
        install_script = generate_install_script(node)
        
        return {
            "status": "success",
            "node_id": node.node_id,
            "vpn_ip": vpn_ip,
            "docker_env": docker_env,
            "windows_installer": windows_installer,
            "install_script": install_script,
            "config": base64.b64encode(config.encode()).decode()
        }
        
    except Exception as e:
        logger.error(f"Installation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_install_script(node: Node) -> str:
    """워커노드 설치 스크립트 생성"""
    
    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    script = f"""#!/bin/bash
# Worker Node Installation Script
# Generated for: {node.node_id}
# VPN IP: {node.vpn_ip}

set -e

echo "========================================="
echo "워커노드 자동 설치 스크립트"
echo "노드 ID: {node.node_id}"
echo "VPN IP: {node.vpn_ip}"
echo "========================================="

# 1. WireGuard 설치
echo ""
echo "[1/5] WireGuard 설치 중..."
if ! command -v wg &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y wireguard
    elif command -v yum &> /dev/null; then
        sudo yum install -y wireguard-tools
    else
        echo "지원되지 않는 시스템입니다."
        exit 1
    fi
else
    echo "WireGuard가 이미 설치되어 있습니다."
fi

# 2. WireGuard 설정 파일 생성
echo ""
echo "[2/5] VPN 설정 파일 생성 중..."
sudo tee /etc/wireguard/wg0.conf > /dev/null << 'EOF'
{node.config}
EOF

sudo chmod 600 /etc/wireguard/wg0.conf
echo "✓ VPN 설정 파일 생성 완료"

# 3. WireGuard 시작
echo ""
echo "[3/5] VPN 연결 시작 중..."
sudo wg-quick down wg0 2>/dev/null || true
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0 2>/dev/null || true
echo "✓ VPN 연결 시작 완료"

# 4. VPN 연결 테스트
echo ""
echo "[4/5] VPN 연결 테스트 중..."
if ping -c 2 {docker_env.get('CENTRAL_SERVER_IP', '10.100.0.1')} > /dev/null 2>&1; then
    echo "✓ VPN 연결 성공: 중앙서버와 통신 가능"
else
    echo "⚠ VPN 연결 확인 필요"
fi

# 5. Docker 환경변수 파일 생성
echo ""
echo "[5/5] Docker 환경 설정 중..."
cat > worker-node.env << 'EOF'
# Worker Node Environment Variables
NODE_ID={docker_env.get('NODE_ID', node.node_id)}
DESCRIPTION={docker_env.get('DESCRIPTION', '')}
CENTRAL_SERVER_IP={docker_env.get('CENTRAL_SERVER_IP', '10.100.0.1')}
HOST_IP={docker_env.get('HOST_IP', node.vpn_ip)}
EOF

echo "✓ Docker 환경변수 파일 생성 완료"

# 완료 메시지
echo ""
echo "========================================="
echo "✅ 설치 완료!"
echo "========================================="
echo ""
echo "워커노드 정보:"
echo "  - 노드 ID: {node.node_id}"
echo "  - VPN IP: {node.vpn_ip}"
echo "  - 중앙서버: {docker_env.get('CENTRAL_SERVER_IP', '10.100.0.1')}"
echo ""
echo "Docker 컨테이너 실행 방법:"
echo "  source worker-node.env"
echo "  docker run -d \\"
echo "    --name worker-{node.node_id} \\"
echo "    --cap-add NET_ADMIN \\"
echo "    --device /dev/net/tun \\"
echo "    -e NODE_ID=\\$NODE_ID \\"
echo "    -e DESCRIPTION=\\\"\\$DESCRIPTION\\\" \\"
echo "    -e CENTRAL_SERVER_IP=\\$CENTRAL_SERVER_IP \\"
echo "    -e HOST_IP=\\$HOST_IP \\"
echo "    -p 8080:8080 \\"
echo "    --restart unless-stopped \\"
echo "    your-image:tag"
echo ""
echo "VPN 상태 확인:"
echo "  sudo wg show"
echo ""
echo "VPN 재시작:"
echo "  sudo wg-quick down wg0 && sudo wg-quick up wg0"
echo "========================================="
"""
    
    return script

@router.get("/worker/status/{node_id}")
async def get_worker_status(node_id: str, db: Session = Depends(get_db)):
    """워커노드 상태 조회"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    return {
        "node_id": node.node_id,
        "status": node.status,
        "vpn_ip": node.vpn_ip,
        "description": node.description,
        "central_server_ip": node.central_server_ip,
        "docker_env": docker_env,
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }