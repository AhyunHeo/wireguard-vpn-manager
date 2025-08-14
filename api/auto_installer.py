"""
완전 자동 VPN 설치 - 터미널 없이 브라우저만으로!
"""

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
import subprocess
import platform
import tempfile
import os
import base64
from pathlib import Path

router = APIRouter()

@router.get("/auto-install/{token}", response_class=HTMLResponse)
async def auto_install_page(token: str, request: Request):
    """
    브라우저 접속만으로 자동 설치!
    터미널 지식 전혀 필요 없음
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN 자동 설치</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
                max-width: 600px;
                width: 90%;
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 32px;
            }}
            .big-button {{
                display: inline-block;
                background: linear-gradient(135deg, #48c774 0%, #3ec46d 100%);
                color: white;
                padding: 20px 50px;
                border-radius: 50px;
                font-size: 24px;
                font-weight: bold;
                text-decoration: none;
                margin: 20px 0;
                cursor: pointer;
                border: none;
                box-shadow: 0 10px 30px rgba(72, 199, 116, 0.3);
                transition: all 0.3s;
            }}
            .big-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 15px 40px rgba(72, 199, 116, 0.4);
            }}
            .status {{
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 18px;
            }}
            .success {{
                background: #d4edda;
                color: #155724;
                border: 2px solid #c3e6cb;
            }}
            .warning {{
                background: #fff3cd;
                color: #856404;
                border: 2px solid #ffeeba;
            }}
            .error {{
                background: #f8d7da;
                color: #721c24;
                border: 2px solid #f5c6cb;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .icon {{
                font-size: 80px;
                margin: 20px 0;
            }}
            .steps {{
                text-align: left;
                margin: 30px 0;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
            }}
            .step {{
                display: flex;
                align-items: center;
                margin: 15px 0;
                opacity: 0.5;
                transition: all 0.3s;
            }}
            .step.active {{
                opacity: 1;
                font-weight: bold;
            }}
            .step.completed {{
                opacity: 1;
                color: #28a745;
            }}
            .step-icon {{
                font-size: 24px;
                margin-right: 15px;
            }}
            .hidden {{
                display: none;
            }}
            .download-frame {{
                display: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- 초기 화면 -->
            <div id="startScreen">
                <div class="icon">🔐</div>
                <h1>VPN 연결 준비</h1>
                <p style="font-size: 18px; color: #666; margin: 20px 0;">
                    클릭 한 번으로 VPN에 연결됩니다!<br>
                    기술 지식이 전혀 필요 없습니다.
                </p>
                <button class="big-button" onclick="startInstallation()">
                    🚀 지금 시작하기
                </button>
                <p style="color: #999; font-size: 14px; margin-top: 20px;">
                    약 1분 정도 소요됩니다
                </p>
            </div>

            <!-- 설치 진행 화면 -->
            <div id="installScreen" class="hidden">
                <div class="icon">⚙️</div>
                <h1>자동 설치 중...</h1>
                <div class="spinner"></div>
                
                <div class="steps">
                    <div class="step" id="step1">
                        <span class="step-icon">1️⃣</span>
                        <span>운영체제 확인 중...</span>
                    </div>
                    <div class="step" id="step2">
                        <span class="step-icon">2️⃣</span>
                        <span>VPN 프로그램 다운로드 중...</span>
                    </div>
                    <div class="step" id="step3">
                        <span class="step-icon">3️⃣</span>
                        <span>설정 파일 생성 중...</span>
                    </div>
                    <div class="step" id="step4">
                        <span class="step-icon">4️⃣</span>
                        <span>VPN 연결 중...</span>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    창을 닫지 마세요. 자동으로 진행됩니다.
                </p>
            </div>

            <!-- 완료 화면 -->
            <div id="successScreen" class="hidden">
                <div class="icon">✅</div>
                <h1>VPN 연결 완료!</h1>
                <div class="status success">
                    성공적으로 VPN에 연결되었습니다.<br>
                    이제 안전하게 통신할 수 있습니다.
                </div>
                <p style="margin: 20px 0; font-size: 16px;">
                    <strong>VPN IP:</strong> <span id="vpnIp">10.100.1.1</span>
                </p>
                <button class="big-button" onclick="window.close()">
                    완료
                </button>
            </div>

            <!-- 오류 화면 -->
            <div id="errorScreen" class="hidden">
                <div class="icon">❌</div>
                <h1>설치 실패</h1>
                <div class="status error" id="errorMessage">
                    설치 중 문제가 발생했습니다.
                </div>
                <button class="big-button" onclick="location.reload()">
                    다시 시도
                </button>
            </div>
        </div>

        <!-- 숨겨진 다운로드 프레임 -->
        <iframe id="downloadFrame" class="download-frame"></iframe>

        <script>
            const TOKEN = '{token}';
            const API_URL = window.location.origin;
            let currentStep = 0;

            async function startInstallation() {{
                // 화면 전환
                document.getElementById('startScreen').classList.add('hidden');
                document.getElementById('installScreen').classList.remove('hidden');
                
                try {{
                    // Step 1: OS 감지
                    await updateStep(1);
                    const os = detectOS();
                    
                    // Step 2: 설치 파일 다운로드
                    await updateStep(2);
                    await downloadInstaller(os);
                    
                    // Step 3: 설정 파일 생성
                    await updateStep(3);
                    await createConfig();
                    
                    // Step 4: VPN 연결
                    await updateStep(4);
                    await connectVPN();
                    
                    // 완료!
                    showSuccess();
                    
                }} catch (error) {{
                    showError(error.message);
                }}
            }}

            function detectOS() {{
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.includes('win')) return 'windows';
                if (userAgent.includes('mac')) return 'macos';
                if (userAgent.includes('linux')) return 'linux';
                return 'unknown';
            }}

            async function updateStep(step) {{
                // 이전 단계 완료 표시
                if (step > 1) {{
                    document.getElementById(`step${{step-1}}`).classList.remove('active');
                    document.getElementById(`step${{step-1}}`).classList.add('completed');
                    document.querySelector(`#step${{step-1}} .step-icon`).textContent = '✅';
                }}
                
                // 현재 단계 활성화
                document.getElementById(`step${{step}}`).classList.add('active');
                
                // 약간의 지연 (사용자가 진행상황을 볼 수 있도록)
                await new Promise(resolve => setTimeout(resolve, 1000));
            }}

            async function downloadInstaller(os) {{
                // 운영체제별 설치 파일 자동 다운로드
                let downloadUrl = '';
                
                if (os === 'windows') {{
                    // Windows용 WireGuard 설치 파일 다운로드
                    downloadUrl = `${{API_URL}}/api/download/wireguard-windows/${{TOKEN}}`;
                    
                    // 자동 다운로드 시작
                    const link = document.createElement('a');
                    link.href = downloadUrl;
                    link.download = 'wireguard-installer.exe';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    // 설치 파일 실행 안내 (Windows는 자동 실행 불가)
                    await new Promise(resolve => {{
                        setTimeout(() => {{
                            if (confirm('다운로드가 완료되면 설치 파일을 실행해주세요.\\n실행하셨나요?')) {{
                                resolve();
                            }}
                        }}, 3000);
                    }});
                    
                }} else if (os === 'linux') {{
                    // Linux는 백그라운드에서 자동 설치
                    const response = await fetch(`${{API_URL}}/api/auto-setup-linux/${{TOKEN}}`, {{
                        method: 'POST'
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('Linux 설치 실패');
                    }}
                }}
                
                await new Promise(resolve => setTimeout(resolve, 2000));
            }}

            async function createConfig() {{
                // VPN 설정 파일 생성
                const response = await fetch(`${{API_URL}}/api/generate-config/${{TOKEN}}`, {{
                    method: 'POST'
                }});
                
                const data = await response.json();
                
                // Windows의 경우 설정 파일 다운로드
                if (detectOS() === 'windows') {{
                    const configBlob = new Blob([atob(data.config)], {{ type: 'text/plain' }});
                    const url = URL.createObjectURL(configBlob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = 'vpn-config.conf';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    alert('설정 파일이 다운로드되었습니다.\\nWireGuard를 열고 이 파일을 가져오기 해주세요.');
                }}
                
                return data;
            }}

            async function connectVPN() {{
                // VPN 연결 시도
                const response = await fetch(`${{API_URL}}/api/connect/${{TOKEN}}`, {{
                    method: 'POST'
                }});
                
                if (!response.ok) {{
                    throw new Error('VPN 연결 실패');
                }}
                
                const data = await response.json();
                document.getElementById('vpnIp').textContent = data.vpn_ip;
            }}

            function showSuccess() {{
                document.getElementById('installScreen').classList.add('hidden');
                document.getElementById('successScreen').classList.remove('hidden');
                
                // 축하 애니메이션
                confetti({{
                    particleCount: 100,
                    spread: 70,
                    origin: {{ y: 0.6 }}
                }});
            }}

            function showError(message) {{
                document.getElementById('installScreen').classList.add('hidden');
                document.getElementById('errorScreen').classList.remove('hidden');
                document.getElementById('errorMessage').textContent = message;
            }}

            // Confetti 효과 (성공 시 축하)
            !function(e,t){{(t=document.createElement("script")).src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js",t.onload=()=>{{window.confetti=window.confetti}},document.head.appendChild(t)}}();
        </script>
    </body>
    </html>
    """
    
    return html_content

@router.post("/api/download/wireguard-windows/{token}")
async def download_wireguard_windows(token: str):
    """
    Windows용 WireGuard 설치 파일 제공
    실제로는 공식 다운로드 링크로 리다이렉트
    """
    # WireGuard 공식 다운로드 URL로 리다이렉트
    return {
        "download_url": "https://download.wireguard.com/windows-client/wireguard-installer.exe",
        "instructions": "다운로드 후 실행하여 설치해주세요"
    }

@router.post("/api/auto-setup-linux/{token}")
async def auto_setup_linux(token: str, background_tasks: BackgroundTasks):
    """
    Linux에서 백그라운드 자동 설치
    """
    def install_wireguard():
        # 자동 설치 스크립트
        script = """
        #!/bin/bash
        # WireGuard 자동 설치
        if command -v apt-get >/dev/null; then
            sudo apt-get update && sudo apt-get install -y wireguard
        elif command -v yum >/dev/null; then
            sudo yum install -y wireguard-tools
        fi
        """
        
        # 스크립트 실행
        subprocess.run(script, shell=True)
    
    # 백그라운드에서 설치
    background_tasks.add_task(install_wireguard)
    
    return {"status": "installing", "message": "백그라운드에서 설치 중"}

@router.get("/one-click/{token}", response_class=HTMLResponse)
async def one_click_install(token: str):
    """
    궁극의 원클릭 설치!
    브라우저 열자마자 자동 시작
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>VPN 자동 연결 중...</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .container {{
                text-align: center;
                color: white;
            }}
            .loader {{
                border: 5px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                border-top: 5px solid white;
                width: 60px;
                height: 60px;
                animation: spin 1s linear infinite;
                margin: 0 auto 30px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            h1 {{
                font-size: 32px;
                margin-bottom: 10px;
            }}
            p {{
                font-size: 18px;
                opacity: 0.9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="loader"></div>
            <h1>VPN 자동 연결 중...</h1>
            <p>잠시만 기다려주세요</p>
            <p style="font-size: 14px; opacity: 0.7;">아무것도 하지 않으셔도 됩니다</p>
        </div>
        
        <script>
            // 페이지 로드되자마자 자동 실행!
            window.onload = function() {{
                // 2초 후 자동으로 설치 페이지로 이동
                setTimeout(() => {{
                    window.location.href = '/auto-install/{token}';
                }}, 2000);
            }};
        </script>
    </body>
    </html>
    """
    
    return html_content