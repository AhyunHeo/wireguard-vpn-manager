"""
웹 기반 원클릭 VPN 설치 페이지
URL 접속만으로 VPN 자동 설정
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
import qrcode
import io
import base64
import uuid
import json
import os

router = APIRouter()

@router.get("/join/{token}", response_class=HTMLResponse)
async def join_vpn_page(token: str, request: Request):
    """
    브라우저에서 접속하면 자동으로 VPN 설정 스크립트를 다운로드/실행
    
    사용 예:
    1. 플랫폼에서 링크 생성: http://vpn-server:8090/join/abc123
    2. 워커노드에서 브라우저로 접속
    3. 자동으로 설치 스크립트 실행
    """
    
    # 토큰으로 노드 정보 조회 (실제로는 DB에서 조회)
    node_info = get_node_info_by_token(token)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN 자동 연결</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 90%;
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }}
            .emoji {{
                font-size: 60px;
                margin: 20px 0;
            }}
            .status {{
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 16px;
            }}
            .pending {{
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
            }}
            .success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 50px;
                font-size: 18px;
                cursor: pointer;
                transition: all 0.3s;
                margin: 10px;
                display: inline-block;
                text-decoration: none;
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
            .button:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .code-block {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                text-align: left;
                overflow-x: auto;
            }}
            .steps {{
                text-align: left;
                margin: 20px 0;
            }}
            .step {{
                display: flex;
                align-items: center;
                margin: 15px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                transition: all 0.3s;
            }}
            .step.active {{
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
            }}
            .step.completed {{
                background: #e8f5e9;
                border-left: 4px solid #4caf50;
            }}
            .step-number {{
                width: 30px;
                height: 30px;
                background: #667eea;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-weight: bold;
            }}
            .step.completed .step-number {{
                background: #4caf50;
            }}
            .spinner {{
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .download-section {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }}
            .os-buttons {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin: 20px 0;
            }}
            .os-button {{
                padding: 10px 20px;
                background: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
            }}
            .os-button:hover {{
                background: #667eea;
                color: white;
            }}
            .os-button.active {{
                background: #667eea;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🔐</div>
            <h1>VPN 자동 연결</h1>
            <p style="color: #666; margin-bottom: 20px;">노드 ID: <strong>{node_info.get('node_id', 'unknown')}</strong></p>
            
            <div id="status" class="status pending">
                <div class="spinner"></div>
                VPN 연결을 준비하고 있습니다...
            </div>

            <div class="steps">
                <div class="step" id="step1">
                    <div class="step-number">1</div>
                    <div>운영체제 확인 중...</div>
                </div>
                <div class="step" id="step2">
                    <div class="step-number">2</div>
                    <div>설치 스크립트 준비 중...</div>
                </div>
                <div class="step" id="step3">
                    <div class="step-number">3</div>
                    <div>VPN 설정 파일 생성 중...</div>
                </div>
            </div>

            <div class="download-section" style="display: none;" id="downloadSection">
                <h3>운영체제를 선택하세요:</h3>
                <div class="os-buttons">
                    <button class="os-button" onclick="selectOS('linux')">🐧 Linux</button>
                    <button class="os-button" onclick="selectOS('windows')">🪟 Windows</button>
                    <button class="os-button" onclick="selectOS('mac')">🍎 macOS</button>
                </div>
                
                <div id="installCommand" style="display: none;">
                    <h3 style="margin: 20px 0 10px 0;">설치 명령어:</h3>
                    <div class="code-block" id="commandBlock"></div>
                    <button class="button" onclick="copyCommand()">📋 명령어 복사</button>
                    <button class="button" onclick="downloadScript()">💾 스크립트 다운로드</button>
                </div>
            </div>

            <div id="successMessage" style="display: none;">
                <div class="status success">
                    ✅ VPN 설정이 완료되었습니다!<br>
                    VPN IP: <strong id="vpnIp"></strong>
                </div>
                <button class="button" onclick="checkConnection()">연결 상태 확인</button>
            </div>
        </div>

        <script>
            const TOKEN = '{token}';
            const API_URL = '{request.url.scheme}://{request.url.netloc}';
            const NODE_ID = '{node_info.get('node_id', 'worker-' + token[:8])}';
            let selectedOS = '';
            let vpnConfig = '';

            // 페이지 로드 시 자동 실행
            window.onload = async function() {{
                await detectAndSetup();
            }};

            async function detectAndSetup() {{
                // Step 1: OS 감지
                document.getElementById('step1').classList.add('active');
                await sleep(1000);
                
                const os = detectOS();
                document.getElementById('step1').classList.remove('active');
                document.getElementById('step1').classList.add('completed');
                
                // Step 2: 스크립트 준비
                document.getElementById('step2').classList.add('active');
                await sleep(1000);
                
                document.getElementById('step2').classList.remove('active');
                document.getElementById('step2').classList.add('completed');
                
                // Step 3: VPN 설정
                document.getElementById('step3').classList.add('active');
                
                try {{
                    // VPN 등록 API 호출
                    const response = await fetch(`${{API_URL}}/api/quick-register/${{TOKEN}}`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            client_info: {{
                                os: os,
                                browser: navigator.userAgent
                            }}
                        }})
                    }});
                    
                    const data = await response.json();
                    vpnConfig = data.config;
                    
                    document.getElementById('step3').classList.remove('active');
                    document.getElementById('step3').classList.add('completed');
                    
                    // 성공 메시지 표시
                    document.getElementById('status').style.display = 'none';
                    document.getElementById('downloadSection').style.display = 'block';
                    
                    // OS 자동 선택
                    selectOS(os);
                    
                }} catch (error) {{
                    document.getElementById('status').className = 'status error';
                    document.getElementById('status').innerHTML = '❌ 연결 실패: ' + error.message;
                }}
            }}

            function detectOS() {{
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.includes('win')) return 'windows';
                if (userAgent.includes('mac')) return 'mac';
                if (userAgent.includes('linux')) return 'linux';
                return 'linux';
            }}

            function selectOS(os) {{
                selectedOS = os;
                
                // 버튼 활성화
                document.querySelectorAll('.os-button').forEach(btn => {{
                    btn.classList.remove('active');
                }});
                event.target.classList.add('active');
                
                // 명령어 표시
                document.getElementById('installCommand').style.display = 'block';
                
                let command = '';
                if (os === 'linux') {{
                    command = `curl -sSL ${{API_URL}}/api/install/${{TOKEN}} | sudo bash`;
                }} else if (os === 'windows') {{
                    command = `Invoke-WebRequest -Uri "${{API_URL}}/api/install/${{TOKEN}}" | Invoke-Expression`;
                }} else if (os === 'mac') {{
                    command = `curl -sSL ${{API_URL}}/api/install/${{TOKEN}} | bash`;
                }}
                
                document.getElementById('commandBlock').textContent = command;
            }}

            function copyCommand() {{
                const command = document.getElementById('commandBlock').textContent;
                navigator.clipboard.writeText(command);
                alert('명령어가 복사되었습니다!');
            }}

            function downloadScript() {{
                window.location.href = `${{API_URL}}/api/download-script/${{TOKEN}}?os=${{selectedOS}}`;
            }}

            function checkConnection() {{
                window.open(`${{API_URL}}/api/status/${{NODE_ID}}`, '_blank');
            }}

            function sleep(ms) {{
                return new Promise(resolve => setTimeout(resolve, ms));
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content

@router.get("/api/install/{token}")
async def get_install_script(token: str, request: Request):
    """
    설치 스크립트 직접 반환
    curl로 바로 실행 가능
    """
    node_info = get_node_info_by_token(token)
    vpn_server = request.url.netloc
    
    script = f"""#!/bin/bash
# VPN 자동 설치 스크립트
# 생성된 토큰: {token}

set -e

echo "🔐 VPN 자동 설치 시작..."
echo "노드 ID: {node_info.get('node_id', 'auto-' + token[:8])}"

# WireGuard 설치
if ! command -v wg &> /dev/null; then
    echo "📦 WireGuard 설치 중..."
    if [ -f /etc/debian_version ]; then
        sudo apt-get update && sudo apt-get install -y wireguard
    elif [ -f /etc/redhat-release ]; then
        sudo yum install -y wireguard-tools
    fi
fi

# VPN 설정 다운로드
echo "⚙️ VPN 설정 파일 다운로드 중..."
curl -sSL http://{vpn_server}/api/config/{token} -o /tmp/wg0.conf

# VPN 연결
echo "🔗 VPN 연결 중..."
sudo cp /tmp/wg0.conf /etc/wireguard/wg0.conf
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0

echo "✅ VPN 연결 완료!"
echo "VPN IP: $(ip -4 addr show wg0 | grep inet | awk '{{print $2}}')"
"""
    
    return Response(content=script, media_type="text/plain")

@router.post("/api/quick-register/{token}")
async def quick_register(token: str, request: Request):
    """
    토큰 기반 빠른 등록
    """
    # 토큰으로 사전 생성된 노드 정보 조회
    node_info = get_node_info_by_token(token)
    
    # 실제 등록 로직
    # ... (기존 register_node 로직 활용)
    
    return {
        "status": "success",
        "node_id": node_info["node_id"],
        "vpn_ip": "10.100.1.x",  # 실제 할당된 IP
        "config": "base64_encoded_config"
    }

@router.get("/generate-join-link")
async def generate_join_link(node_id: str = None):
    """
    새로운 조인 링크 생성
    
    플랫폼에서 호출:
    GET /generate-join-link?node_id=worker-gpu-1
    
    응답:
    {
        "join_url": "http://vpn-server:8090/join/abc123xyz",
        "qr_code": "data:image/png;base64,...",
        "token": "abc123xyz",
        "expires": "2024-01-01T00:00:00Z"
    }
    """
    # 고유 토큰 생성
    token = str(uuid.uuid4())[:12]
    
    # 토큰 정보 저장 (실제로는 DB에)
    save_token_info(token, node_id)
    
    # QR 코드 생성
    join_url = f"http://your-vpn-server.com:8090/join/{token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(join_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()
    
    return {
        "join_url": join_url,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "token": token,
        "expires": "2024-01-01T00:00:00Z"
    }

# 헬퍼 함수들
def get_node_info_by_token(token: str) -> dict:
    """토큰으로 노드 정보 조회"""
    # 실제로는 DB에서 조회
    return {
        "node_id": f"worker-{token[:8]}",
        "node_type": "worker"
    }

def save_token_info(token: str, node_id: str):
    """토큰 정보 저장"""
    # 실제로는 DB에 저장
    pass