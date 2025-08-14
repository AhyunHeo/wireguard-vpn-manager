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
    
    html_content = """
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
                <input type="text" id="nodeType" placeholder="노드 타입 (worker/central)" value="worker" />
                <button class="button" onclick="generateQR()">QR 코드 생성</button>
            </div>
            
            <div class="qr-container" id="qrContainer" style="display: none;">
                <h2>📱 QR 코드</h2>
                <div id="qrCode"></div>
                <div class="url-display" id="joinUrl"></div>
                <button class="copy-btn" onclick="copyUrl()">URL 복사</button>
            </div>
            
            <div class="instructions">
                <h3>📖 사용 방법</h3>
                <ol>
                    <li>노드 ID를 입력하고 QR 코드 생성</li>
                    <li>워커 노드에서:</li>
                    <ul>
                        <li>모바일: QR 코드 스캔</li>
                        <li>PC: URL 복사 후 브라우저에서 접속</li>
                    </ul>
                    <li>자동으로 VPN 설정 페이지로 이동</li>
                    <li>페이지의 안내에 따라 설치 진행</li>
                </ol>
            </div>
            
            <div class="info-box">
                <strong>💡 팁:</strong> QR 코드는 15분간 유효합니다.<br>
                여러 노드를 등록하려면 각각 새로운 QR 코드를 생성하세요.
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
                    document.getElementById('qrCode').innerHTML = 
                        `<img src="${data.qr_code}" alt="QR Code" />`;
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
                            alert('복사 실패. URL을 수동으로 복사하세요:\n' + url);
                        }
                        document.body.removeChild(textArea);
                    }
                } catch (err) {
                    alert('복사 실패. URL을 수동으로 복사하세요:\n' + url);
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html_content

@router.post("/api/generate-qr")
async def generate_qr(request: Request, qr_request: QRGenerateRequest):
    """
    QR 코드 생성 API
    """
    # 고유 토큰 생성
    token = str(uuid.uuid4())[:12]
    
    # 토큰 정보 저장 (15분 유효)
    token_store[token] = {
        "node_id": qr_request.node_id,
        "node_type": qr_request.node_type,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=15)
    }
    
    # 조인 URL 생성
    base_url = str(request.url).split('/api')[0]
    join_url = f"{base_url}/join/{token}"
    
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

@router.get("/join/{token}", response_class=HTMLResponse)
async def join_page(token: str, request: Request):
    """
    VPN 연결 페이지 (QR 스캔 또는 URL 클릭 후 리다이렉트되는 페이지)
    """
    # 토큰 검증
    if token not in token_store:
        return HTMLResponse(content="<h1>유효하지 않은 토큰입니다</h1>", status_code=404)
    
    token_info = token_store[token]
    if datetime.now() > token_info["expires_at"]:
        del token_store[token]
        return HTMLResponse(content="<h1>만료된 토큰입니다</h1>", status_code=404)
    
    # 서버 URL 가져오기
    server_url = str(request.url).split('/join')[0]
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN 자동 설치</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 30px;
            }}
            .info-card {{
                background: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
                margin: 20px 0;
            }}
            .success {{
                color: #28a745;
                font-size: 60px;
                margin: 20px 0;
            }}
            .button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 18px;
                cursor: pointer;
                margin: 10px;
                display: inline-block;
                text-decoration: none;
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
            .code-block {{
                background: #333;
                color: #0f0;
                padding: 15px;
                border-radius: 10px;
                font-family: monospace;
                font-size: 14px;
                overflow-x: auto;
                margin: 15px 0;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success">✅</div>
            <h1>VPN 설치 준비 완료!</h1>
            
            <div class="info-card">
                <h3>노드 정보</h3>
                <p><strong>노드 ID:</strong> {token_info['node_id']}</p>
                <p><strong>노드 타입:</strong> {token_info['node_type']}</p>
                <p><strong>토큰:</strong> {token[:8]}...</p>
            </div>
            
            <h2>설치 방법을 선택하세요:</h2>
            
            <a href="{server_url}/one-click/{token}" class="button">
                🚀 원클릭 자동 설치
            </a>
            
            <div style="margin-top: 30px;">
                <h3>또는 수동 설치:</h3>
                <div class="code-block">
                    curl -X POST {server_url}/nodes/register \\<br>
                    &nbsp;&nbsp;-H "Authorization: Bearer test-token-123" \\<br>
                    &nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
                    &nbsp;&nbsp;-d '{{"node_id": "{token_info['node_id']}", "node_type": "{token_info['node_type']}"}}'
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@router.get("/mobile-join/{token}", response_class=HTMLResponse)
async def mobile_join_page(token: str):
    """
    모바일 최적화 VPN 연결 페이지
    QR 스캔 후 자동으로 이 페이지로 이동
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>VPN 연결</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .mobile-container {{
                background: white;
                border-radius: 20px;
                padding: 30px 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #333;
                font-size: 24px;
                text-align: center;
                margin-bottom: 20px;
            }}
            .big-button {{
                display: block;
                width: 100%;
                padding: 20px;
                margin: 15px 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                text-decoration: none;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            .status {{
                background: #f0f0f0;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }}
            .emoji {{
                font-size: 60px;
                text-align: center;
                margin: 20px 0;
            }}
            .info {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
            }}
            .step {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                display: flex;
                align-items: center;
            }}
            .step-number {{
                background: #667eea;
                color: white;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="mobile-container">
            <div class="emoji">🔐</div>
            <h1>VPN 간편 연결</h1>
            
            <div class="info">
                <strong>노드 정보</strong><br>
                토큰: {token[:8]}...
            </div>
            
            <div class="status">
                운영체제를 선택하세요
            </div>
            
            <a href="intent://join#{token}#Intent;scheme=vpnmanager;package=com.vpnmanager;end" 
               class="big-button">
                📱 모바일 앱으로 연결
            </a>
            
            <button onclick="installScript('linux')" class="big-button">
                🐧 Linux에서 설치
            </button>
            
            <button onclick="installScript('windows')" class="big-button">
                🪟 Windows에서 설치
            </button>
            
            <button onclick="installScript('mac')" class="big-button">
                🍎 macOS에서 설치
            </button>
            
            <div style="margin-top: 30px;">
                <h3>수동 설치 방법:</h3>
                <div class="step">
                    <div class="step-number">1</div>
                    <div>터미널 열기</div>
                </div>
                <div class="step">
                    <div class="step-number">2</div>
                    <div>아래 명령어 실행</div>
                </div>
                <div style="background: #333; color: #0f0; padding: 15px; border-radius: 10px; font-family: monospace; font-size: 12px; overflow-x: auto;">
                    curl -sSL http://vpn.server/join/{token} | bash
                </div>
            </div>
        </div>
        
        <script>
            function installScript(os) {{
                const commands = {{
                    linux: 'curl -sSL http://vpn.server/install/{token} | sudo bash',
                    windows: 'Invoke-WebRequest http://vpn.server/install/{token} | iex',
                    mac: 'curl -sSL http://vpn.server/install/{token} | bash'
                }};
                
                // 명령어 복사
                navigator.clipboard.writeText(commands[os]);
                alert('설치 명령어가 복사되었습니다! 터미널에 붙여넣기 하세요.');
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content