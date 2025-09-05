"""
Central Server Integration API
VPN 등록과 중앙서버 플랫폼 등록을 통합하는 API
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models import Node, QRToken
from wireguard_manager import WireGuardManager
from typing import Optional
import json
import logging
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
import secrets
import os
from simple_central_docker_runner import generate_simple_central_runner

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CentralEnvironmentRequest(BaseModel):
    """중앙서버 환경변수 설정 요청"""
    node_id: str
    description: str
    api_port: Optional[int] = 8000
    fl_port: Optional[int] = 5002
    dashboard_port: Optional[int] = 5000
    db_port: Optional[int] = 5432
    mongo_port: Optional[int] = 27017

@router.get("/central/setup")
async def central_setup_page():
    """중앙서버 설정 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중앙서버 통합 설정</title>
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
                max-width: 600px;
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
            .port-group {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
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
                margin-top: 20px;
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
            .info-box {
                background: #e7f3ff;
                border-left: 4px solid #2196F3;
                padding: 12px;
                margin-top: 20px;
                border-radius: 4px;
                text-align: left;
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
            .advanced-toggle {
                color: #667eea;
                cursor: pointer;
                font-size: 14px;
                margin-top: 20px;
                text-align: center;
            }
            .advanced-toggle:hover {
                text-decoration: underline;
            }
            .advanced-settings {
                display: none;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌐 중앙서버 통합 설정</h1>
            <p class="subtitle">VPN 설치와 중앙서버 등록을 한 번에 완료합니다</p>
            
            <form id="centralForm">
                <div class="form-group">
                    <label for="node_id">서버 ID *</label>
                    <input type="text" id="node_id" name="node_id" required 
                           placeholder="예: central-server-01" pattern="[a-zA-Z0-9_\-]+">
                </div>
                
                <div class="form-group">
                    <label for="description">설명 *</label>
                    <input type="text" id="description" name="description" required 
                           placeholder="예: AI 플랫폼 중앙서버">
                </div>
                
                <div class="advanced-toggle" onclick="toggleAdvanced()">
                    ⚙️ 고급 설정 (포트 구성)
                </div>
                
                <div class="advanced-settings" id="advancedSettings">
                    <div class="port-group">
                        <div class="form-group">
                            <label for="api_port">API 포트</label>
                            <input type="number" id="api_port" name="api_port" 
                                   value="8000" min="1" max="65535">
                        </div>
                        
                        <div class="form-group">
                            <label for="fl_port">FL 서버 포트</label>
                            <input type="number" id="fl_port" name="fl_port" 
                                   value="5002" min="1" max="65535">
                        </div>
                        
                        <div class="form-group">
                            <label for="dashboard_port">대시보드 포트</label>
                            <input type="number" id="dashboard_port" name="dashboard_port" 
                                   value="5000" min="1" max="65535">
                        </div>
                        
                        <div class="form-group">
                            <label for="db_port">DB 포트</label>
                            <input type="number" id="db_port" name="db_port" 
                                   value="5432" min="1" max="65535">
                        </div>
                    </div>
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
                        3. VPN IP 자동 할당 (10.100.0.x)<br>
                        4. 중앙서버 Docker Compose 설정 생성<br>
                        5. VPN 전용 모드로 서비스 실행
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            function toggleAdvanced() {
                const advanced = document.getElementById('advancedSettings');
                advanced.style.display = advanced.style.display === 'none' ? 'block' : 'none';
            }
            
            document.getElementById('centralForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                
                // 숫자 타입 변환
                ['api_port', 'fl_port', 'dashboard_port', 'db_port', 'mongo_port'].forEach(key => {
                    if (data[key]) data[key] = parseInt(data[key]);
                });
                
                // 로딩 표시
                document.querySelector('.loading').style.display = 'block';
                document.querySelector('button[type="submit"]').disabled = true;
                
                try {
                    const response = await fetch('/central/generate-qr', {
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

@router.post("/central/generate-qr")
async def generate_central_qr(
    request: CentralEnvironmentRequest,
    db: Session = Depends(get_db)
):
    """중앙서버용 QR 코드 및 설치 링크 생성"""
    try:
        # 토큰 생성
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # 토큰 정보를 DB에 저장
        qr_token = QRToken(
            token=token,
            node_id=request.node_id,
            node_type="central",
            expires_at=expires_at,
            used=False
        )
        db.add(qr_token)
        
        # 중앙서버 메타데이터 저장
        metadata = {
            "description": request.description,
            "api_port": request.api_port or 8000,
            "fl_port": request.fl_port or 5002,
            "dashboard_port": request.dashboard_port or 5000,
            "db_port": request.db_port or 5432,
            "mongo_port": request.mongo_port or 27017
        }
        
        # Node 테이블에 예비 등록
        new_node = Node(
            node_id=request.node_id,
            node_type="central",
            hostname=request.node_id,
            description=request.description,
            central_server_ip="10.100.0.1",  # 중앙서버는 자기 자신
            docker_env_vars=json.dumps(metadata),
            status="pending",
            vpn_ip="0.0.0.0",  # 임시값
            public_key="pending",
            private_key="pending",
            config="pending"
        )
        
        # 중앙서버는 하나만 존재해야 함 - 기존 모든 중앙서버 제거
        existing_centrals = db.query(Node).filter(Node.node_type == "central").all()
        if existing_centrals:
            wg_manager = WireGuardManager()
            for central in existing_centrals:
                # WireGuard 서버에서 기존 중앙서버 피어 제거
                if central.public_key and central.public_key != "pending":
                    try:
                        wg_manager.remove_peer_from_server(central.public_key)
                        logger.info(f"Removed old central server peer {central.public_key} for {central.node_id}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old peer: {e}")
                
                # DB에서 삭제
                if central.node_id != request.node_id:
                    db.delete(central)
                    logger.info(f"Deleted old central server node {central.node_id}")
        
        # 현재 요청된 중앙서버 노드 처리
        existing = db.query(Node).filter(Node.node_id == request.node_id).first()
        if existing:
            # 기존 노드가 있고 이미 설정되어 있으면 메타데이터만 업데이트
            if existing.status != "pending" and existing.public_key != "pending":
                existing.description = request.description
                existing.docker_env_vars = json.dumps(metadata)
                existing.updated_at = datetime.now(timezone.utc)
                logger.info(f"Updated existing central node {request.node_id} metadata")
            else:
                # pending 상태면 메타데이터 업데이트
                existing.description = request.description
                existing.docker_env_vars = json.dumps(metadata)
                existing.updated_at = datetime.now(timezone.utc)
                existing.status = "pending"  # 명시적으로 pending 설정
        else:
            # 새 노드 추가 (임시로 pending 상태)
            db.add(new_node)
            logger.info(f"Added new central node {request.node_id} in pending status")
        
        db.commit()
        
        # 설치 URL 생성
        # SERVERURL 환경변수 사용 (docker-compose.yml에서 설정)
        server_host = os.getenv('SERVERURL', 'localhost')
        if server_host == 'auto' or not server_host or server_host == 'localhost':
            # LOCAL_SERVER_IP 사용 (우선순위)
            server_host = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
        
        server_url = f"http://{server_host}:8090"
        install_url = f"{server_url}/central/install/{token}"
        
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

@router.get("/central/config-file/{node_id}")
async def get_central_config_file(node_id: str, db: Session = Depends(get_db)):
    """중앙서버 WireGuard 설정 파일 직접 다운로드"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # 설정이 없는 경우 자세한 오류 메시지
    if not node.config:
        logger.error(f"Node {node_id} has no config. Status: {node.status}, VPN IP: {node.vpn_ip}")
        raise HTTPException(
            status_code=400, 
            detail=f"Node configuration not ready. Status: {node.status}. Please complete the installation process first."
        )
    
    if node.status == "pending":
        raise HTTPException(
            status_code=400,
            detail="Node registration pending. Please click 'Start Installation' button on the web page first."
        )
    
    # 설정 파일을 직접 반환
    return Response(
        content=node.config,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={node_id}.conf"
        }
    )

@router.get("/central/install/{token}")
async def central_install_page(token: str, db: Session = Depends(get_db)):
    """중앙서버 자동 설치 페이지"""
    
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
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중앙서버 자동 설치</title>
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
                max-width: 700px;
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
                max-height: 400px;
                overflow-y: auto;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌐 중앙서버 자동 설치</h1>
            
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">서버 ID:</span>
                    <span class="info-value">{qr_token.node_id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">설명:</span>
                    <span class="info-value">{metadata.get('description', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">API 포트:</span>
                    <span class="info-value">{metadata.get('api_port', 8000)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">FL 서버 포트:</span>
                    <span class="info-value">{metadata.get('fl_port', 5002)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">대시보드 포트:</span>
                    <span class="info-value">{metadata.get('dashboard_port', 5000)}</span>
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
                    <span>중앙서버 등록 준비 중...</span>
                </div>
                <div class="step" id="step4">
                    <div class="step-icon">4</div>
                    <span>Docker Compose 설정 생성 중...</span>
                </div>
                <div class="step" id="step5">
                    <div class="step-icon">5</div>
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
                        중앙서버 실행을 위해 <strong>Docker Desktop</strong>이 반드시 설치되어 있어야 합니다.
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
                
                <div style="margin: 20px 0; padding: 15px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px;">
                    <h4 style="color: #155724; margin-bottom: 10px;">📝 설치 순서</h4>
                    <ol style="color: #155724; font-size: 14px; line-height: 1.8; margin-left: 20px;">
                        <li><strong>VPN 설치 파일</strong>을 다운로드하여 실행 → WireGuard 설치 및 터널 설정</li>
                        <li>WireGuard에서 터널을 <strong>활성화</strong></li>
                        <li><strong>Docker 실행 파일</strong>을 다운로드하여 실행 → 중앙서버 컨테이너 시작</li>
                    </ol>
                </div>
                
                <div style="display: flex; gap: 20px; margin-top: 20px;">
                    <button class="btn btn-success" onclick="downloadWindowsInstaller()" style="flex: 1;">
                        🪟 1. VPN 설치 파일 (.bat)
                    </button>
                    <button class="btn" onclick="downloadDockerRunner()" style="flex: 1; background: #17a2b8;">
                        🐳 2. Docker 실행 파일 (.bat)
                    </button>
                </div>
                
                <div style="margin-top: 10px;">
                    <button class="btn" onclick="showLinuxScript()" style="width: 100%; background: #6c757d;">
                        🐧 Linux/Mac 스크립트 보기
                    </button>
                </div>
                
                <div class="code-block" id="installScript" style="display: none;">
                    # 설치 스크립트 로딩 중...
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px;">
                    <p style="color: #1976D2; font-size: 14px; line-height: 1.6;">
                        <strong>다음 단계:</strong><br>
                        1. 위 스크립트를 다운로드하여 중앙서버에서 실행<br>
                        2. 스크립트가 자동으로 VPN과 Docker Compose 환경을 설정<br>
                        3. VPN 전용 모드로 중앙서버가 자동 시작됨<br>
                        4. 워커노드들이 VPN IP({qr_token.node_id})로 접속 가능
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
            
            // 페이지 로드 시 노드 상태 확인
            document.addEventListener('DOMContentLoaded', async function() {{
                try {{
                    const response = await fetch('/api/nodes/{qr_token.node_id}/status');
                    if (response.ok) {{
                        const nodeData = await response.json();
                        if (nodeData.status !== 'pending') {{
                            // 이미 설치된 노드
                            document.getElementById('vpnIp').textContent = nodeData.vpn_ip || '{node.vpn_ip}';
                            document.getElementById('result').style.display = 'block';
                            document.querySelector('.status-icon').textContent = '✅';
                            document.querySelector('.status p').textContent = '이미 등록이 완료된 노드입니다. 아래에서 필요한 파일을 다운로드하세요.';
                            document.getElementById('startBtn').style.display = 'none';
                            
                            // 모든 단계를 완료 상태로 표시
                            for (let i = 1; i <= 5; i++) {{
                                const step = document.getElementById('step' + i);
                                step.classList.add('completed');
                                step.querySelector('.step-icon').textContent = '✓';
                            }}
                        }}
                    }}
                }} catch (error) {{
                    console.error('Failed to check node status:', error);
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
                    // API 호출하여 VPN 설정 및 중앙서버 등록
                    const response = await fetch('/central/process-installation/{qr_token.token}', {{
                        method: 'POST'
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('설치 실패');
                    }}
                    
                    installData = await response.json();
                    
                    // 단계 업데이트
                    for (let i = 1; i <= 5; i++) {{
                        await updateStep(i, i === 1, true);
                        if (i < 5) {{
                            await updateStep(i + 1, true);
                            await new Promise(r => setTimeout(r, 500));
                        }}
                    }}
                    
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
                    a.download = 'vpn-install-{qr_token.node_id}.bat';
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
            
            function downloadDockerRunner() {{
                // 직접 API에서 최신 Docker Runner 다운로드
                window.location.href = '/central/docker-runner/{qr_token.node_id}';
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
                            a.download = 'install-{qr_token.node_id}.sh';
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

@router.get("/central/docker-runner/{node_id}")
async def get_docker_runner(node_id: str, db: Session = Depends(get_db)):
    """Docker Runner 배치 파일 다운로드"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # 최신 Docker Runner 생성
    docker_runner = generate_simple_central_runner(node)
    
    return Response(
        content=docker_runner,
        media_type="application/x-msdos-program",
        headers={
            "Content-Disposition": f"attachment; filename=docker-runner-{node_id}.bat"
        }
    )

@router.post("/central/process-installation/{token}")
async def process_central_installation(
    token: str,
    db: Session = Depends(get_db)
):
    """중앙서버 설치 처리 - VPN 등록 및 설정 생성"""
    
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
        # 이미 VPN이 설정된 경우 - 재등록 처리
        if node.status != "pending" and node.public_key != "pending":
            logger.info(f"Re-registering existing node {node.node_id}")
            
            # WireGuard 매니저 초기화
            wg_manager = WireGuardManager()
            
            # 기존 피어 제거
            try:
                logger.info(f"Removing old peer {node.public_key[:8]}...")
                wg_manager.remove_peer_from_server(node.public_key)
            except Exception as e:
                logger.warning(f"Failed to remove old peer: {e}")
            
            # 새 키 생성
            keys = wg_manager.generate_keypair()
            
            # VPN 설정 재생성
            config = wg_manager.generate_client_config(
                private_key=keys['private_key'],
                client_ip=node.vpn_ip,  # 기존 IP 유지
                server_public_key=wg_manager.get_server_public_key()
            )
            
            # 노드 정보 업데이트
            node.public_key = keys['public_key']
            node.private_key = keys['private_key']
            node.config = config
            node.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # 새 피어 추가
            try:
                wg_manager.add_peer_to_server(
                    public_key=keys['public_key'],
                    vpn_ip=node.vpn_ip,
                    node_id=node.node_id
                )
                logger.info(f"Added new peer for {node.node_id}")
            except Exception as e:
                logger.error(f"Failed to add new peer: {e}")
            
            # Windows installer 생성 (VPN + Docker 두 개 파일)
            vpn_installer = generate_central_windows_installer(node)
            docker_runner = generate_simple_central_runner(node)
            
            return {
                "status": "re-registered",
                "node_id": node.node_id,
                "vpn_ip": node.vpn_ip,
                "install_script": generate_central_install_script(node),
                "windows_installer": vpn_installer,
                "docker_runner": docker_runner,
                "message": "Re-registered with new keys"
            }
        
        # WireGuard 매니저 초기화
        wg_manager = WireGuardManager()
        
        # 중앙서버는 항상 10.100.0.2 고정
        vpn_ip = "10.100.0.2"
        logger.info(f"Central server will use fixed IP: {vpn_ip}")
        
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
        metadata['vpn_ip'] = vpn_ip
        node.docker_env_vars = json.dumps(metadata)
        
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
        
        # 토큰을 사용됨으로 표시
        qr_token.used = True
        db.commit()
        
        # 설치 스크립트 생성 (Windows 배치 파일)
        vpn_installer = generate_central_windows_installer(node)
        docker_runner = generate_simple_central_runner(node)
        
        # Linux/Mac용 스크립트도 제공 (선택사항)
        install_script = generate_central_install_script(node)
        
        return {
            "status": "success",
            "node_id": node.node_id,
            "vpn_ip": vpn_ip,
            "windows_installer": vpn_installer,
            "docker_runner": docker_runner,
            "install_script": install_script,
            "config": base64.b64encode(config.encode()).decode()
        }
        
    except Exception as e:
        logger.error(f"Installation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_central_windows_installer(node: Node) -> str:
    """중앙서버용 Windows 설치 배치 파일 생성 - auto_vpn_installer.py 패턴 복사"""
    
    # 노드에 config가 없으면 오류
    if not node.config or node.config == "pending":
        logger.error(f"Cannot generate installer for {node.node_id}: no config available")
        return f"echo 오류: 노드 설정이 준비되지 않았습니다. 웹 페이지에서 '설치 시작' 버튼을 먼저 클릭하세요."
    
    # 서버 URL 구성
    server_host = os.getenv('SERVERURL', 'localhost')
    if server_host == 'auto' or not server_host or server_host == 'localhost':
        server_host = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
    server_url = f"http://{server_host}:8090"
    
    # PowerShell 스크립트 생성 (auto_vpn_installer.py와 동일한 패턴)
    powershell_script = f"""
# WireGuard VPN 자동 설치 스크립트
# Node ID: {node.node_id}
# VPN IP: {node.vpn_ip}

Write-Host "🚀 VPN 자동 설치를 시작합니다..." -ForegroundColor Green
Write-Host "노드 ID: {node.node_id}" -ForegroundColor Yellow
Write-Host "VPN IP: {node.vpn_ip}" -ForegroundColor Yellow

# 1. WireGuard 설치 상태 확인
$wireguardPath = "C:\\Program Files\\WireGuard\\wireguard.exe"
$isInstalled = Test-Path $wireguardPath

if (-not $isInstalled) {{
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
}} else {{
    Write-Host "📦 WireGuard가 이미 설치되어 있습니다." -ForegroundColor Yellow
}}

# 2. VPN 설정 파일 생성
Write-Host "⚙️ VPN 설정 생성 중..." -ForegroundColor Cyan
$configUrl = "{server_url}/central/config-file/{node.node_id}"

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

# 3. Windows 방화벽 규칙 추가 (워커노드와 동일하게 강화)
Write-Host "🔥 Windows 방화벽 설정 중..." -ForegroundColor Cyan
try {{
    # 기존 충돌 규칙 제거
    Remove-NetFirewallRule -DisplayName "WireGuard*" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "VPN*" -ErrorAction SilentlyContinue
    
    # WireGuard 포트
    New-NetFirewallRule -DisplayName "WireGuard VPN Port In" -Direction Inbound -Protocol UDP -LocalPort 41820 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "WireGuard VPN Port Out" -Direction Outbound -Protocol UDP -LocalPort 41820 -Action Allow -ErrorAction SilentlyContinue
    
    # VPN 서브넷 전체 허용
    New-NetFirewallRule -DisplayName "VPN Subnet In" -Direction Inbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN Subnet Out" -Direction Outbound -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    
    # ICMP (ping) 허용 - 중요!
    New-NetFirewallRule -DisplayName "VPN ICMP Echo Request In" -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN ICMP Echo Reply Out" -Direction Outbound -Protocol ICMPv4 -IcmpType 0 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN ICMP All In" -Direction Inbound -Protocol ICMPv4 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "VPN ICMP All Out" -Direction Outbound -Protocol ICMPv4 -RemoteAddress "10.100.0.0/16" -Action Allow -ErrorAction SilentlyContinue
    
    # 중앙서버 포트 허용 (Docker가 사용하는 포트들)
    New-NetFirewallRule -DisplayName "Central Server API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "Central Server FL" -Direction Inbound -Protocol TCP -LocalPort 5002 -Action Allow -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "Central Server Dashboard" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -ErrorAction SilentlyContinue
    
    # WireGuard 인터페이스에 대한 특별 규칙
    $wgInterface = Get-NetAdapter | Where-Object {{ $_.Name -like "*{node.node_id}*" -or $_.Name -like "*WireGuard*" -or $_.Name -like "*wg*" }} | Select-Object -First 1
    if ($wgInterface) {{
        New-NetFirewallRule -DisplayName "WireGuard Interface All Traffic" -Direction Inbound -InterfaceAlias $wgInterface.Name -Action Allow -ErrorAction SilentlyContinue
        Write-Host "✅ WireGuard 인터페이스 ($($wgInterface.Name))에 대한 규칙 추가" -ForegroundColor Green
    }}
    
    Write-Host "✅ 방화벽 규칙 추가 완료 (ICMP 및 서버 포트 포함)" -ForegroundColor Green
    
    # 방화벽 규칙 확인
    Write-Host ""
    Write-Host "📋 추가된 방화벽 규칙 확인:" -ForegroundColor Cyan
    Get-NetFirewallRule -DisplayName "*VPN*" | Where-Object {{ $_.Enabled -eq "True" }} | Select-Object DisplayName, Direction, Action | Format-Table -AutoSize
    
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
    
    # 연결 테스트
    Write-Host ""
    Write-Host "🔍 연결 테스트 중..." -ForegroundColor Cyan
    Write-Host "주의: 먼저 WireGuard에서 터널을 활성화해야 합니다!" -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # ping 테스트로 간단하게 확인
    $pingResult = ping -n 1 -w 2000 10.100.0.1 2>$null
    if ($LASTEXITCODE -eq 0) {{
        Write-Host "✅ VPN 서버와 연결 성공!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 VPN 설치가 완료되었습니다!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📁 다음 단계:" -ForegroundColor Yellow
        Write-Host "  1. WireGuard에서 터널을 활성화하세요" -ForegroundColor White
        Write-Host "  2. 동일 폴더에 있는 'docker-runner-{node.node_id}.bat' 파일을 실행하세요" -ForegroundColor White
        Write-Host "     (이 파일은 Docker 서버를 실행합니다)" -ForegroundColor Cyan
        
    }} else {{
        Write-Host "⚠️ VPN 서버에 연결할 수 없습니다." -ForegroundColor Yellow
        Write-Host "   WireGuard에서 터널이 활성화되어 있는지 확인하세요." -ForegroundColor Yellow
    }}
    
}} else {{
    Write-Host "⚠️ WireGuard가 설치되었지만 자동 연결에 실패했습니다." -ForegroundColor Yellow
    Write-Host "WireGuard를 수동으로 실행하고 설정 파일을 가져오세요:" -ForegroundColor Yellow
    Write-Host $configPath -ForegroundColor White
}}

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩 (auto_vpn_installer.py와 동일)
    encoded_script = base64.b64encode(powershell_script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성 (auto_vpn_installer.py와 동일한 패턴)
    batch_script = f"""@echo off
chcp 65001 > nul 2>&1
setlocal enabledelayedexpansion
color 0A
title VPN Auto Installer

echo ==========================================
echo    Central Server VPN Auto Installer
echo    Server ID: {node.node_id}
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

echo.
pause
"""
    
    return batch_script

def generate_central_install_script(node: Node) -> str:
    """중앙서버 설치 스크립트 생성"""
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    # docker-compose.vpn.yml 내용
    docker_compose_content = f"""# VPN 전용 접근 설정
# 중앙서버를 VPN IP로만 접근 가능하도록 설정
# 사용법: docker-compose -f docker-compose.vpn.yml up -d

services:
  api:
    build:
      context: ../
      dockerfile: central-server/Dockerfile
    container_name: central-server-api
    ports:
      # VPN IP에만 바인딩
      - "${{VPN_IP}}:{metadata.get('api_port', 8000)}:{metadata.get('api_port', 8000)}"
    volumes:
      - ./app:/app
      - ./config:/config
      - ./alembic.ini:/app/alembic.ini
      - ./migrations:/app/migrations
      - ./manage_db.py:/app/manage_db.py
      - ../shared/examples:/app/examples
      - ../shared:/app/shared
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

  fl-api:
    build:
      context: ../
      dockerfile: central-server/Dockerfile_fl
    container_name: fl-server-api
    ports:
      # VPN IP에만 바인딩
      - "${{VPN_IP}}:{metadata.get('fl_port', 5002)}:{metadata.get('fl_port', 5002)}"
    volumes:
      - ./app:/app
      - ./config:/config
      - ./alembic.ini:/app/alembic.ini
      - ./migrations:/app/migrations
      - ./manage_db.py:/app/manage_db.py
      - ../fl-client-agent/python:/app/python
      - ../shared/examples:/app/examples
      - ../shared:/app/shared
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${{JWT_SECRET_KEY}}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      - FL_SERVER_PORT={metadata.get('fl_port', 5002)}
    depends_on:
      - db
      - redis
      - mongo

  db:
    image: postgres:latest
    container_name: central-server-db
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
      TZ: Asia/Seoul
      PGTZ: Asia/Seoul
    ports:
      # 로컬호스트만 접근 가능 (보안)
      - "127.0.0.1:{metadata.get('db_port', 5432)}:5432"
    volumes:
      - db_data:/var/lib/postgresql/data

  mongo:
    image: mongo:latest
    container_name: central-server-mongo
    environment:
      TZ: Asia/Seoul
    ports:
      # 로컬호스트만 접근 가능 (보안)
      - "127.0.0.1:{metadata.get('mongo_port', 27017)}:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:latest
    container_name: central-server-redis
    # 내부 네트워크만 사용 (포트 노출 안함)

volumes:
  db_data:
  mongo_data:"""
    
    script = f"""#!/bin/bash
# Central Server Installation Script
# Generated for: {node.node_id}
# VPN IP: {node.vpn_ip}

set -e

echo "========================================="
echo "중앙서버 자동 설치 스크립트"
echo "서버 ID: {node.node_id}"
echo "VPN IP: {node.vpn_ip}"
echo "========================================="

# 1. WireGuard 설치
echo ""
echo "[1/6] WireGuard 설치 중..."
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
echo "[2/6] VPN 설정 파일 생성 중..."
sudo tee /etc/wireguard/wg0.conf > /dev/null << 'EOF'
{node.config}
EOF

sudo chmod 600 /etc/wireguard/wg0.conf
echo "✓ VPN 설정 파일 생성 완료"

# 3. WireGuard 시작
echo ""
echo "[3/6] VPN 연결 시작 중..."
sudo wg-quick down wg0 2>/dev/null || true
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0 2>/dev/null || true
echo "✓ VPN 연결 시작 완료"

# 4. VPN 연결 테스트
echo ""
echo "[4/6] VPN 연결 테스트 중..."
VPN_IP=$(ip -4 addr show wg0 | grep -oP '(?<=inet\s)\d+(\.\d+){{3}}')
echo "✓ VPN IP 확인: $VPN_IP"

# 5. Docker Compose 파일 생성
echo ""
echo "[5/6] Docker Compose VPN 설정 생성 중..."

# 프로젝트 디렉토리 확인
if [ ! -d "distributed-ai-platform" ]; then
    echo "distributed-ai-platform 디렉토리를 찾을 수 없습니다."
    echo "프로젝트를 먼저 클론해주세요:"
    echo "  git clone <repository-url> distributed-ai-platform"
    exit 1
fi

cd distributed-ai-platform/central-server

# docker-compose.vpn.yml 생성
cat > docker-compose.vpn.yml << 'COMPOSE_EOF'
{docker_compose_content}
COMPOSE_EOF

# .env 파일 생성
cat > .env << 'ENV_EOF'
# VPN 설정
VPN_IP={node.vpn_ip}

# 포트 설정
API_PORT={metadata.get('api_port', 8000)}
FL_PORT={metadata.get('fl_port', 5002)}
DASHBOARD_PORT={metadata.get('dashboard_port', 5000)}
DB_PORT={metadata.get('db_port', 5432)}
MONGO_PORT={metadata.get('mongo_port', 27017)}

# JWT 설정 (보안을 위해 변경 권장)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 기타 설정
PUID=1000
PGID=1000
TZ=Asia/Seoul
ENV_EOF

echo "✓ Docker Compose 설정 완료"

# 6. 서비스 시작
echo ""
echo "[6/6] 중앙서버 서비스 시작 중..."

# 기존 서비스 중지
docker-compose down 2>/dev/null || true

# VPN 전용 모드로 시작
docker-compose -f docker-compose.vpn.yml up -d

echo "✓ 중앙서버 서비스 시작 완료"

# 완료 메시지
echo ""
echo "========================================="
echo "✅ 설치 완료!"
echo "========================================="
echo ""
echo "중앙서버 정보:"
echo "  - 서버 ID: {node.node_id}"
echo "  - VPN IP: {node.vpn_ip}"
echo "  - API 주소: http://{node.vpn_ip}:{metadata.get('api_port', 8000)}"
echo "  - FL 서버: http://{node.vpn_ip}:{metadata.get('fl_port', 5002)}"
echo "  - 대시보드: http://{node.vpn_ip}:{metadata.get('dashboard_port', 5000)}"
echo ""
echo "서비스 상태 확인:"
echo "  docker-compose -f docker-compose.vpn.yml ps"
echo ""
echo "로그 확인:"
echo "  docker-compose -f docker-compose.vpn.yml logs -f"
echo ""
echo "VPN 상태 확인:"
echo "  sudo wg show"
echo ""
echo "워커노드 연결:"
echo "  워커노드들이 VPN IP({node.vpn_ip})로 접속 가능합니다."
echo "========================================="
"""
    
    return script

@router.get("/central/config-file/{node_id}")
async def get_central_config_file(node_id: str, db: Session = Depends(get_db)):
    """중앙서버 WireGuard 설정 파일 직접 다운로드"""
    
    # 노드 정보 조회
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node.status != "registered" or not node.config:
        raise HTTPException(status_code=400, detail="Node configuration not ready")
    
    # 설정 파일을 직접 반환
    return Response(
        content=node.config,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={node_id}.conf"
        }
    )

@router.get("/central/status/{node_id}")
async def get_central_status(node_id: str, db: Session = Depends(get_db)):
    """중앙서버 상태 조회"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    return {
        "node_id": node.node_id,
        "status": node.status,
        "vpn_ip": node.vpn_ip,
        "description": node.description,
        "ports": {
            "api": metadata.get('api_port', 8000),
            "fl": metadata.get('fl_port', 5002),
            "dashboard": metadata.get('dashboard_port', 5000),
            "db": metadata.get('db_port', 5432),
            "mongo": metadata.get('mongo_port', 27017)
        },
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }