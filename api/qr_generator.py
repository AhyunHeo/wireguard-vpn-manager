"""
QR 코드 기반 VPN 연결
모바일이나 브라우저에서 QR 스캔으로 즉시 연결
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import qrcode
import io
import base64
import json
import uuid
from datetime import datetime, timedelta
import os

router = APIRouter()

class QRGenerateRequest(BaseModel):
    node_id: str
    node_type: str = "worker"

# 임시 토큰 저장소 (실제로는 Redis나 DB 사용)
token_store = {}

@router.get("/vpn-qr", response_class=HTMLResponse)
async def vpn_qr_page(request: Request):
    """
    QR 코드 생성 페이지
    플랫폼 관리자가 접속해서 QR 코드를 생성
    """
    
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN QR 코드 생성</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 90%;
                text-align: center;
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
            }
            .qr-container {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 30px;
                margin: 20px 0;
            }
            #qrCode {
                margin: 20px auto;
            }
            .info-box {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
                border-radius: 5px;
            }
            .button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 16px;
                cursor: pointer;
                margin: 10px;
                transition: all 0.3s;
            }
            .button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }
            input {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            input:focus {
                outline: none;
                border-color: #667eea;
            }
            .url-display {
                background: #f5f5f5;
                padding: 10px;
                border-radius: 8px;
                margin: 10px 0;
                word-break: break-all;
                font-family: monospace;
                font-size: 14px;
            }
            .copy-btn {
                background: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }
            .instructions {
                background: #fff3cd;
                border: 1px solid #ffeeba;
                color: #856404;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: left;
            }
            .instructions h3 {
                margin-top: 0;
            }
            .instructions ol {
                margin: 10px 0;
                padding-left: 20px;
            }
            .instructions li {
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 VPN 연결 QR 코드</h1>
            
            <div>
                <input type="text" id="nodeId" placeholder="노드 ID (예: worker-gpu-1)" />
                <select id="nodeType" style="width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px;">
                    <option value="worker" selected>워커 노드 (Worker Node)</option>
                    <option value="central">중앙 서버 (Central Server)</option>
                </select>
                <button class="button" onclick="generateQR()">QR 코드 생성</button>
            </div>
            
            <div class="qr-container" id="qrContainer" style="display: none;">
                <h2>📱 QR 코드</h2>
                <div id="qrCode"></div>
                <div class="url-display" id="joinUrl"></div>
                <button class="copy-btn" onclick="copyUrl()">자동 설치 URL 복사</button>
            </div>
            
            <div class="instructions">
                <h3>📖 사용 방법</h3>
                <ol>
                    <li>노드 ID 입력 및 노드 타입 선택</li>
                    <li>QR 코드 생성 버튼 클릭</li>
                    <li>대상 장치에서:</li>
                    <ul>
                        <li>모바일: QR 코드 스캔</li>
                        <li>PC: URL 복사 후 브라우저에서 접속</li>
                    </ul>
                    <li>자동으로 VPN 설정 페이지로 이동</li>
                    <li>페이지의 안내에 따라 설치 진행</li>
                </ol>
            </div>
            
            <div class="info-box">
                <strong>💡 팁:</strong> 
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>QR 코드는 15분간 유효합니다</li>
                    <li>워커 노드: 10.100.1.x 대역 IP 할당</li>
                    <li>중앙 서버: 10.100.0.x 대역 IP 할당</li>
                    <li>노드 ID는 중복되지 않도록 고유하게 설정하세요</li>
                </ul>
            </div>
        </div>
        
        <script>
            async function generateQR() {
                const nodeId = document.getElementById('nodeId').value;
                const nodeType = document.getElementById('nodeType').value;
                
                if (!nodeId) {
                    alert('노드 ID를 입력하세요!');
                    return;
                }
                
                try {
                    const response = await fetch('/api/generate-qr', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            node_id: nodeId,
                            node_type: nodeType
                        })
                    });
                    
                    const data = await response.json();
                    
                    // QR 코드 표시
                    var qrImage = document.createElement('img');
                    qrImage.src = data.qr_code;
                    qrImage.alt = 'QR Code';
                    
                    var qrContainer = document.getElementById('qrCode');
                    qrContainer.innerHTML = '';
                    qrContainer.appendChild(qrImage);
                    
                    document.getElementById('joinUrl').textContent = data.join_url;
                    document.getElementById('qrContainer').style.display = 'block';
                    
                } catch (error) {
                    alert('QR 코드 생성 실패: ' + error.message);
                }
            }
            
            async function copyUrl() {
                const url = document.getElementById('joinUrl').textContent;
                try {
                    // HTTPS가 아닌 경우를 위한 fallback
                    if (navigator.clipboard && window.isSecureContext) {
                        await navigator.clipboard.writeText(url);
                        alert('URL이 복사되었습니다!');
                    } else {
                        // 구형 브라우저 또는 HTTP 환경용 fallback
                        const textArea = document.createElement("textarea");
                        textArea.value = url;
                        textArea.style.position = "fixed";
                        textArea.style.left = "-999999px";
                        textArea.style.top = "-999999px";
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        try {
                            document.execCommand('copy');
                            alert('URL이 복사되었습니다!');
                        } catch (err) {
                            alert('복사 실패. URL을 수동으로 복사하세요: ' + url);
                        }
                        document.body.removeChild(textArea);
                    }
                } catch (err) {
                    alert('복사 실패. URL을 수동으로 복사하세요: ' + url);
                }
            }
        </script>
    </body>
    </html>
    """)

@router.post("/api/generate-qr")
async def generate_qr(request: Request, qr_request: QRGenerateRequest):
    """
    QR 코드 생성 API - 토큰을 DB에 저장
    """
    from database import SessionLocal
    from models import QRToken
    
    # 고유 토큰 생성
    token = str(uuid.uuid4())[:12]
    
    # DB에 토큰 저장
    db = SessionLocal()
    try:
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # DB에 저장
        db_token = QRToken(
            token=token,
            node_id=qr_request.node_id,
            node_type=qr_request.node_type,
            expires_at=expires_at,
            used=False
        )
        db.add(db_token)
        db.commit()
        
        # 메모리 캐시에도 저장 (이전 버전 호환성)
        token_store[token] = {
            "node_id": qr_request.node_id,
            "node_type": qr_request.node_type,
            "created_at": datetime.now(),
            "expires_at": expires_at
        }
    finally:
        db.close()
    
    # 조인 URL 생성 - qr-join 경로 사용
    base_url = str(request.url).split('/api')[0]
    join_url = f"{base_url}/qr-join/{token}"
    
    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(join_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 이미지를 Base64로 변환
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()
    
    return {
        "token": token,
        "join_url": join_url,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "expires_at": token_store[token]["expires_at"].isoformat()
    }

@router.get("/qr-join/{token}", response_class=HTMLResponse)
async def qr_join_page(token: str, request: Request):
    """
    QR 코드 전용 연결 페이지 - web_installer의 /join/{token}과 충돌 방지
    """
    # 토큰 검증
    if token not in token_store:
        return HTMLResponse(content="<h1>유효하지 않은 토큰입니다</h1>", status_code=404)
    
    token_info = token_store[token]
    if datetime.now() > token_info["expires_at"]:
        del token_store[token]
        return HTMLResponse(content="<h1>만료된 토큰입니다</h1>", status_code=404)
    
    # 서버 URL 가져오기
    server_url = str(request.url).split('/qr-join')[0]
    
    # 테스트 페이지로 리다이렉트 (디버깅용)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="0; url={server_url}/test-join/{token}">
        <title>VPN 설치 페이지로 이동 중...</title>
    </head>
    <body>
        <p>VPN 설치 페이지로 이동 중입니다...</p>
        <p>자동으로 이동되지 않으면 <a href="{server_url}/test-join/{token}">여기를 클릭</a>하세요.</p>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)