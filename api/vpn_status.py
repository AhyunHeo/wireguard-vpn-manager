"""
VPN 연결 상태 확인 페이지
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/vpn-status/{node_id}", response_class=HTMLResponse)
async def vpn_status_page(node_id: str, request: Request):
    """
    VPN 연결 상태 확인 페이지
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN 상태 확인</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 90%;
            }}
            h1 {{
                text-align: center;
                color: #333;
            }}
            .status-item {{
                background: #f8f9fa;
                padding: 15px;
                margin: 15px 0;
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .status-label {{
                font-weight: bold;
                color: #495057;
            }}
            .status-value {{
                color: #007bff;
                font-family: monospace;
            }}
            .connected {{
                background: #d4edda;
                color: #155724;
            }}
            .disconnected {{
                background: #f8d7da;
                color: #721c24;
            }}
            .check-button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
                margin-top: 20px;
            }}
            .check-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 VPN 연결 상태</h1>
            
            <div class="status-item">
                <span class="status-label">노드 ID:</span>
                <span class="status-value">{node_id}</span>
            </div>
            
            <div class="status-item" id="vpn-ip">
                <span class="status-label">VPN IP:</span>
                <span class="status-value">확인 중...</span>
            </div>
            
            <div class="status-item" id="connection-status">
                <span class="status-label">연결 상태:</span>
                <span class="status-value">확인 중...</span>
            </div>
            
            <div class="status-item" id="last-check">
                <span class="status-label">마지막 확인:</span>
                <span class="status-value">-</span>
            </div>
            
            <button class="check-button" onclick="checkStatus()">상태 새로고침</button>
            
            <div style="margin-top: 30px; padding: 20px; background: #e3f2fd; border-radius: 10px;">
                <h3>📋 수동 확인 방법</h3>
                <ol style="text-align: left; margin: 10px 0;">
                    <li>PowerShell 열기</li>
                    <li><code>ipconfig | findstr "10.100"</code> 실행</li>
                    <li>IP 주소가 표시되면 연결 성공</li>
                </ol>
            </div>
        </div>
        
        <script>
            async function checkStatus() {{
                const nodeId = '{node_id}';
                
                // 현재 시간 업데이트
                document.getElementById('last-check').querySelector('.status-value').textContent = 
                    new Date().toLocaleTimeString();
                
                try {{
                    // API 호출하여 상태 확인
                    const response = await fetch(`/nodes/${{nodeId}}`, {{
                        headers: {{
                            'Authorization': 'Bearer test-token-123'
                        }}
                    }});
                    
                    if (response.ok) {{
                        const data = await response.json();
                        
                        document.getElementById('vpn-ip').querySelector('.status-value').textContent = 
                            data.vpn_ip || '할당되지 않음';
                        
                        const statusEl = document.getElementById('connection-status');
                        if (data.connected) {{
                            statusEl.className = 'status-item connected';
                            statusEl.querySelector('.status-value').textContent = '✅ 연결됨';
                        }} else {{
                            statusEl.className = 'status-item disconnected';
                            statusEl.querySelector('.status-value').textContent = '❌ 연결 안됨';
                        }}
                    }} else {{
                        // 노드를 찾을 수 없는 경우
                        document.getElementById('vpn-ip').querySelector('.status-value').textContent = 
                            '10.100.1.1 (예상)';
                        document.getElementById('connection-status').querySelector('.status-value').textContent = 
                            '서버에서 확인 불가';
                    }}
                }} catch (error) {{
                    console.error('상태 확인 실패:', error);
                    document.getElementById('connection-status').querySelector('.status-value').textContent = 
                        '확인 실패';
                }}
            }}
            
            // 페이지 로드 시 자동 확인
            window.onload = checkStatus;
            
            // 5초마다 자동 새로고침
            setInterval(checkStatus, 5000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)