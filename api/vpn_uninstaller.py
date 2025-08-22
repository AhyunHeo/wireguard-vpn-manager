"""
WireGuard 및 VPN 설정 제거 스크립트 생성
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database import SessionLocal
import base64

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/windows-uninstaller/{token}")
async def get_windows_uninstaller(token: str, request: Request):
    """
    Windows용 WireGuard 제거 스크립트
    """
    
    # PowerShell 스크립트 생성
    script = f"""
# WireGuard VPN 제거 스크립트
# Token: {token}

Write-Host "========================================" -ForegroundColor Red
Write-Host "   WireGuard VPN 제거 프로그램" -ForegroundColor Red
Write-Host "   Token: {token[:8]}" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

# 1. VPN 터널 제거
Write-Host "🔧 VPN 터널 제거 중..." -ForegroundColor Yellow

# 모든 WireGuard 터널 서비스 중지
Get-Service -Name "WireGuardTunnel*" -ErrorAction SilentlyContinue | ForEach-Object {{
    Write-Host "  - $($_.Name) 서비스 중지 중..." -ForegroundColor Cyan
    Stop-Service -Name $_.Name -Force -ErrorAction SilentlyContinue
    sc.exe delete $_.Name 2>$null
}}

# 2. 설정 파일 제거
Write-Host "📁 VPN 설정 파일 제거 중..." -ForegroundColor Yellow

$configPath = "$env:APPDATA\\WireGuard\\Configurations"
$vpnConfig = "$configPath\\vpn-{token[:8]}.conf"

if (Test-Path $vpnConfig) {{
    Remove-Item -Path $vpnConfig -Force
    Write-Host "  ✅ 설정 파일 삭제: vpn-{token[:8]}.conf" -ForegroundColor Green
}} else {{
    Write-Host "  ⚠️ 설정 파일을 찾을 수 없음" -ForegroundColor Yellow
}}

# 모든 VPN 설정 파일 목록 표시
$remainingConfigs = Get-ChildItem -Path $configPath -Filter "*.conf" -ErrorAction SilentlyContinue
if ($remainingConfigs) {{
    Write-Host ""
    Write-Host "📌 남아있는 설정 파일:" -ForegroundColor Cyan
    foreach ($config in $remainingConfigs) {{
        Write-Host "  - $($config.Name)" -ForegroundColor White
    }}
}}

# 3. WireGuard 제거 옵션
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "WireGuard 프로그램을 제거하시겠습니까?" -ForegroundColor Yellow
Write-Host "다른 VPN 연결을 사용 중이라면 N을 선택하세요." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
$response = Read-Host "WireGuard 완전 제거 (Y/N)"

if ($response -eq 'Y' -or $response -eq 'y') {{
    Write-Host ""
    Write-Host "🗑️ WireGuard 제거 중..." -ForegroundColor Red
    
    # WireGuard 프로세스 종료
    Stop-Process -Name "wireguard" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # 제거 프로그램 실행
    # 레지스트리에서 정확한 제거 경로 찾기
    $uninstallPath = $null
    
    # 64비트 레지스트리 확인
    $regPath = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\WireGuard"
    if (Test-Path $regPath) {{
        $uninstallString = (Get-ItemProperty -Path $regPath).UninstallString
        if ($uninstallString) {{
            $uninstallPath = $uninstallString.Replace('"', '')
        }}
    }}
    
    # 32비트 레지스트리 확인
    if (-not $uninstallPath) {{
        $regPath32 = "HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\WireGuard"
        if (Test-Path $regPath32) {{
            $uninstallString = (Get-ItemProperty -Path $regPath32).UninstallString
            if ($uninstallString) {{
                $uninstallPath = $uninstallString.Replace('"', '')
            }}
        }}
    }}
    
    # 기본 경로 확인
    if (-not $uninstallPath) {{
        $defaultPaths = @(
            "C:\\Program Files\\WireGuard\\uninstall.exe",
            "$env:ProgramFiles\\WireGuard\\uninstall.exe"
        )
        foreach ($path in $defaultPaths) {{
            if (Test-Path $path) {{
                $uninstallPath = $path
                break
            }}
        }}
    }}
    
    if ($uninstallPath -and (Test-Path $uninstallPath)) {{
        Write-Host "Uninstaller found: $uninstallPath" -ForegroundColor Yellow
        Write-Host "Removing WireGuard..." -ForegroundColor Red
        Start-Process -FilePath $uninstallPath -ArgumentList "/S" -Wait
        Write-Host "✅ WireGuard has been removed." -ForegroundColor Green
    }} else {{
        Write-Host "⚠️ WireGuard uninstaller not found." -ForegroundColor Yellow
        Write-Host "Opening Control Panel for manual removal..." -ForegroundColor Yellow
        Start-Process appwiz.cpl
    }}
    
    # 설정 폴더 정리
    $configFolder = "$env:APPDATA\\WireGuard"
    if (Test-Path $configFolder) {{
        $deleteFolder = Read-Host "모든 WireGuard 설정을 삭제하시겠습니까? (Y/N)"
        if ($deleteFolder -eq 'Y' -or $deleteFolder -eq 'y') {{
            Remove-Item -Path $configFolder -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "✅ 모든 설정이 삭제되었습니다." -ForegroundColor Green
        }}
    }}
}} else {{
    Write-Host "✅ VPN 설정만 제거되었습니다." -ForegroundColor Green
    Write-Host "WireGuard 프로그램은 유지됩니다." -ForegroundColor Yellow
}}

# 4. 네트워크 정리
Write-Host ""
Write-Host "🔄 네트워크 설정 초기화 중..." -ForegroundColor Cyan
ipconfig /flushdns 2>$null
Write-Host "✅ DNS 캐시 초기화 완료" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   제거가 완료되었습니다!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host
"""
    
    # PowerShell 스크립트를 Base64로 인코딩
    encoded_script = base64.b64encode(script.encode('utf-16-le')).decode()
    
    # 실행 가능한 배치 파일 생성
    batch_script = f"""@echo off
chcp 65001 > nul 2>nul
setlocal enabledelayedexpansion
color 0C
title WireGuard VPN Uninstaller

echo ==========================================
echo    WireGuard VPN Uninstaller
echo    Token: {token[:8]}
echo ==========================================
echo.
echo [WARNING] This will remove VPN settings!
echo.
echo Press any key to continue...
pause >nul

:: Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator rights required.
    echo.
    echo Getting admin rights...
    powershell -Command "Start-Process cmd -ArgumentList '/c, %~f0' -Verb RunAs -WindowStyle Normal" 2>nul
    exit /b
)

echo [+] Administrator rights confirmed
echo.

:: Run PowerShell script
echo Running uninstall script...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_script} 2>nul

echo.
echo Uninstall completed.
pause >nul
"""
    
    return Response(
        content=batch_script,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=vpn-uninstaller-{token[:8]}.bat"
        }
    )

@router.get("/api/clean-vpn/{node_id}")
async def clean_vpn_registration(node_id: str, db: Session = Depends(get_db)):
    """
    서버에서 노드 등록 정보 제거
    """
    from models import Node
    
    try:
        # 노드 찾기
        node = db.query(Node).filter(Node.node_id == node_id).first()
        if node:
            db.delete(node)
            db.commit()
            return {"status": "success", "message": f"노드 {node_id} 제거 완료"}
        else:
            return {"status": "not_found", "message": f"노드 {node_id}를 찾을 수 없음"}
    except Exception as e:
        return {"status": "error", "message": str(e)}