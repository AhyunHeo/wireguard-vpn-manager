"""
원클릭 자동 설치 페이지 - 기존 API 활용
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/test-join/{token}", response_class=HTMLResponse)
async def test_join_page(token: str, request: Request):
    """
    자동 설치 페이지 - 기존 generate-config API 활용
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN 자동 설치</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
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
            .info {{
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
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
            .button {{
                background: linear-gradient(135deg, #48c774 0%, #3ec46d 100%);
                color: white;
                padding: 15px 30px;
                border-radius: 30px;
                border: none;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                margin: 10px;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(72, 199, 116, 0.3);
            }}
            .hidden {{
                display: none;
            }}
            .code-block {{
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 8px;
                font-family: monospace;
                margin: 15px 0;
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 VPN 자동 설치</h1>
            <p>토큰: <strong>{token}</strong></p>
            
            <!-- 초기 로딩 화면 -->
            <div id="loading-screen">
                <div class="status pending">
                    <div class="spinner"></div>
                    자동 설치를 준비하고 있습니다...
                </div>
                
                <div class="steps" style="text-align: left; margin: 20px 0;">
                    <div class="step" id="step1">
                        <div class="step-number">1</div>
                        <div>운영체제 확인 중...</div>
                    </div>
                    <div class="step" id="step2">
                        <div class="step-number">2</div>
                        <div>VPN 설정 생성 중...</div>
                    </div>
                    <div class="step" id="step3">
                        <div class="step-number">3</div>
                        <div>설치 파일 다운로드 중...</div>
                    </div>
                </div>
            </div>
            
            <!-- Windows 설치 화면 -->
            <div id="windows-screen" class="hidden">
                <h2>🪟 Windows VPN 설치</h2>
                
                <div class="status success">
                    🎉 자동 설치 프로그램이 다운로드됩니다!
                </div>
                
                <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3>📥 다운로드 후 실행 방법:</h3>
                    <ol style="text-align: left; margin: 15px 0;">
                        <li><strong>vpn-installer-${{TOKEN.substring(0,8)}}.bat</strong> 파일 실행</li>
                        <li>관리자 권한 승인 (UAC 창에서 "예" 클릭)</li>
                        <li>자동으로 WireGuard 설치 및 VPN 연결!</li>
                    </ol>
                </div>
                
                <div id="download-buttons">
                    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <strong>⚠️ 자동 다운로드가 시작되지 않았나요?</strong>
                    </div>
                    
                    <!-- 다시 다운로드 버튼 -->
                    <button class="button" onclick="downloadAutoInstaller()" style="background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);">
                        🔄 자동 설치 프로그램 다시 다운로드
                    </button>
                    
                    <div style="margin: 20px 0; color: #666;">──────── 또는 ────────</div>
                    
                    <!-- 수동 설치 옵션 -->
                    <details style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 15px 0;">
                        <summary style="cursor: pointer; font-weight: bold;">📋 수동 설치 옵션 보기</summary>
                        <div style="margin-top: 15px;">
                            <p style="color: #666;">WireGuard를 수동으로 설치하려면:</p>
                            <div style="display: flex; gap: 10px; justify-content: center; margin: 15px 0;">
                                <button class="button" onclick="downloadWireGuard()" style="background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);">
                                    1️⃣ WireGuard 다운로드
                                </button>
                                <button class="button" onclick="downloadConfigFile()" style="background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);">
                                    2️⃣ 설정 파일 다운로드
                                </button>
                            </div>
                        </div>
                    </details>
                    
                    <!-- 제거 옵션 -->
                    <details style="background: #fff5f5; padding: 20px; border-radius: 10px; margin: 15px 0; border: 1px solid #ffdddd;">
                        <summary style="cursor: pointer; font-weight: bold; color: #dc3545;">🗑️ VPN 제거</summary>
                        <div style="margin-top: 15px;">
                            <p style="color: #dc3545; font-weight: bold;">⚠️ 주의: VPN 설정이 삭제됩니다!</p>
                            <button class="button" onclick="downloadUninstaller()" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);">
                                🗑️ 제거 프로그램 다운로드
                            </button>
                            <p style="color: #666; margin-top: 10px; font-size: 14px;">
                                • VPN 설정 파일 제거<br>
                                • WireGuard 프로그램 제거 선택 가능<br>
                                • 네트워크 설정 초기화
                            </p>
                        </div>
                    </details>
                </div>
                
                <div class="status success hidden" id="download-complete">
                    ✅ 다운로드가 완료되었습니다!<br>
                    위의 안내에 따라 설치를 진행하세요.
                </div>
            </div>
            
            <!-- Linux/Mac 설치 화면 -->
            <div id="unix-screen" class="hidden">
                <h2 id="os-title">🐧 Linux VPN 설치</h2>
                
                <div class="status info">
                    터미널에서 아래 명령어를 실행하면 자동으로 설치됩니다:
                </div>
                
                <div class="code-block">
                    <code id="unix-command"></code>
                </div>
                
                <button class="button" onclick="copyCommand()">📋 명령어 복사</button>
                
                <div class="status success" style="margin-top: 20px;">
                    명령어를 실행하면 자동으로:<br>
                    1. WireGuard 설치<br>
                    2. VPN 설정<br>
                    3. 자동 연결<br>
                    이 진행됩니다.
                </div>
            </div>
            
            <!-- 에러 화면 -->
            <div id="error-screen" class="hidden">
                <div class="status error">
                    <h2>❌ 설치 중 오류 발생</h2>
                    <p id="error-message"></p>
                </div>
                <button class="button" onclick="location.reload()">다시 시도</button>
            </div>
        </div>
        
        <!-- 숨겨진 iframe (다운로드용) -->
        <iframe id="download-frame" style="display: none;"></iframe>
        
        <script>
            const TOKEN = '{token}';
            const API_URL = window.location.origin;
            let detectedOS = '';
            let vpnConfig = null;
            
            window.onload = function() {{
                startAutoInstall();
            }};
            
            async function startAutoInstall() {{
                try {{
                    // Step 1: OS 감지
                    updateStep(1);
                    await sleep(1000);
                    
                    detectedOS = detectOS();
                    console.log('감지된 OS:', detectedOS);
                    
                    // Step 2: VPN 설정 생성 (기존 API 호출)
                    updateStep(2);
                    await sleep(500);
                    
                    const configResponse = await fetch(`${{API_URL}}/api/generate-config/${{TOKEN}}`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer test-token-123'
                        }}
                    }});
                    
                    if (configResponse.ok) {{
                        vpnConfig = await configResponse.json();
                        console.log('VPN 설정 생성 완료:', vpnConfig);
                    }} else {{
                        console.log('VPN 설정 생성 - 더미 데이터 사용');
                        // 실패 시 더미 데이터 사용
                        vpnConfig = {{
                            config: btoa(`[Interface]
PrivateKey = dummy_private_key
Address = 10.100.1.1/32
DNS = 8.8.8.8

[Peer]
PublicKey = dummy_public_key
Endpoint = 192.168.0.68:51820
AllowedIPs = 10.100.0.0/16
PersistentKeepalive = 25`),
                            node_id: `auto-node-${{TOKEN.substring(0, 8)}}`,
                            vpn_ip: '10.100.1.1'
                        }};
                    }}
                    
                    // Step 3: OS별 설치 화면 표시
                    updateStep(3);
                    await sleep(500);
                    
                    document.getElementById('loading-screen').classList.add('hidden');
                    
                    if (detectedOS === 'windows') {{
                        await showWindowsInstall();
                    }} else {{
                        showUnixInstall();
                    }}
                    
                }} catch (error) {{
                    console.error('설치 중 오류:', error);
                    showError(error.message);
                }}
            }}
            
            function detectOS() {{
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.includes('win')) return 'windows';
                if (userAgent.includes('mac')) return 'macos';
                if (userAgent.includes('linux')) return 'linux';
                if (userAgent.includes('android')) return 'android';
                if (userAgent.includes('iphone') || userAgent.includes('ipad')) return 'ios';
                return 'linux';
            }}
            
            function updateStep(stepNum) {{
                for (let i = 1; i < stepNum; i++) {{
                    document.getElementById(`step${{i}}`).classList.remove('active');
                    document.getElementById(`step${{i}}`).classList.add('completed');
                }}
                document.getElementById(`step${{stepNum}}`).classList.add('active');
            }}
            
            async function showWindowsInstall() {{
                document.getElementById('windows-screen').classList.remove('hidden');
                
                // 원클릭 자동 설치 파일 자동 다운로드
                setTimeout(() => {{
                    // 자동 설치 배치 파일 다운로드
                    console.log('자동 설치 파일 다운로드 시작...');
                    downloadAutoInstaller();
                }}, 1500);
            }}
            
            function downloadAutoInstaller() {{
                // 자동 설치 배치 파일 다운로드
                window.location.href = `${{API_URL}}/api/windows-installer/${{TOKEN}}`;
                document.getElementById('auto-install-steps').style.display = 'block';
                document.getElementById('download-complete').classList.remove('hidden');
            }}
            
            function downloadWireGuard() {{
                // WireGuard 설치 파일 다운로드
                window.open('https://download.wireguard.com/windows-client/wireguard-installer.exe', '_blank');
                document.getElementById('manual-install-steps').style.display = 'block';
            }}
            
            function downloadConfigFile() {{
                // 설정 파일만 다운로드
                window.location.href = `${{API_URL}}/api/config-file/${{TOKEN}}`;
                document.getElementById('manual-install-steps').style.display = 'block';
                document.getElementById('download-complete').classList.remove('hidden');
            }}
            
            function downloadUninstaller() {{
                // 제거 프로그램 다운로드
                if (confirm('VPN 설정을 제거하시겠습니까?\\n\\n이 작업은 되돌릴 수 없습니다.')) {{
                    window.location.href = `${{API_URL}}/api/windows-uninstaller/${{TOKEN}}`;
                }}
            }}
            
            function downloadConfig() {{
                if (!vpnConfig) {{
                    alert('VPN 설정이 아직 생성되지 않았습니다. 잠시 후 다시 시도하세요.');
                    return;
                }}
                
                // Base64 디코딩
                const configContent = atob(vpnConfig.config);
                
                // Blob 생성 및 다운로드
                const blob = new Blob([configContent], {{ type: 'text/plain' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `vpn-config-${{TOKEN.substring(0, 8)}}.conf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                // 완료 메시지 표시
                document.getElementById('download-complete').classList.remove('hidden');
            }}
            
            function showUnixInstall() {{
                document.getElementById('unix-screen').classList.remove('hidden');
                
                // OS별 설정 - 자동 설치 스크립트 사용
                let command = '';
                if (detectedOS === 'macos') {{
                    document.getElementById('os-title').textContent = '🍎 macOS VPN 설치';
                    command = `curl -sSL ${{API_URL}}/api/linux-installer/${{TOKEN}} | bash`;
                }} else {{
                    command = `curl -sSL ${{API_URL}}/api/linux-installer/${{TOKEN}} | sudo bash`;
                }}
                
                document.getElementById('unix-command').textContent = command;
            }}
            
            function copyCommand() {{
                const command = document.getElementById('unix-command').textContent;
                navigator.clipboard.writeText(command).then(() => {{
                    alert('명령어가 복사되었습니다!');
                }}).catch(() => {{
                    // Fallback
                    const textarea = document.createElement('textarea');
                    textarea.value = command;
                    textarea.style.position = 'fixed';
                    textarea.style.opacity = '0';
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    alert('명령어가 복사되었습니다!');
                }});
            }}
            
            function showError(message) {{
                document.getElementById('loading-screen').classList.add('hidden');
                document.getElementById('windows-screen').classList.add('hidden');
                document.getElementById('unix-screen').classList.add('hidden');
                document.getElementById('error-screen').classList.remove('hidden');
                document.getElementById('error-message').textContent = message;
            }}
            
            function sleep(ms) {{
                return new Promise(resolve => setTimeout(resolve, ms));
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)