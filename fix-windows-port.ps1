# Windows 포트 포워딩 및 방화벽 설정 스크립트
# 관리자 권한으로 실행 필요

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Windows VPN 포트 및 방화벽 설정" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 관리자 권한 확인
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ 이 스크립트는 관리자 권한이 필요합니다." -ForegroundColor Red
    Write-Host "PowerShell을 관리자 권한으로 다시 실행하세요." -ForegroundColor Yellow
    pause
    exit
}

Write-Host "✅ 관리자 권한 확인됨" -ForegroundColor Green
Write-Host ""

# 1. Windows Defender 방화벽 규칙 추가
Write-Host "📋 방화벽 규칙 설정 중..." -ForegroundColor Cyan

# WireGuard UDP 포트
Write-Host "  - WireGuard UDP 포트 (41820) 허용..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "WireGuard VPN UDP" `
    -Direction Inbound `
    -Protocol UDP `
    -LocalPort 41820 `
    -Action Allow `
    -ErrorAction SilentlyContinue

New-NetFirewallRule -DisplayName "WireGuard VPN UDP Out" `
    -Direction Outbound `
    -Protocol UDP `
    -LocalPort 41820 `
    -Action Allow `
    -ErrorAction SilentlyContinue

# VPN 서브넷 전체 허용
Write-Host "  - VPN 서브넷 (10.100.0.0/16) 허용..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "VPN Subnet Inbound" `
    -Direction Inbound `
    -RemoteAddress "10.100.0.0/16" `
    -Action Allow `
    -ErrorAction SilentlyContinue

New-NetFirewallRule -DisplayName "VPN Subnet Outbound" `
    -Direction Outbound `
    -RemoteAddress "10.100.0.0/16" `
    -Action Allow `
    -ErrorAction SilentlyContinue

# API 포트
Write-Host "  - API 포트 (8090) 허용..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "WireGuard API" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8090 `
    -Action Allow `
    -ErrorAction SilentlyContinue

# WireGuard 프로그램 자체 허용
Write-Host "  - WireGuard 프로그램 허용..." -ForegroundColor Yellow
$wgPath = "C:\Program Files\WireGuard\wireguard.exe"
if (Test-Path $wgPath) {
    New-NetFirewallRule -DisplayName "WireGuard Application" `
        -Direction Inbound `
        -Program $wgPath `
        -Action Allow `
        -ErrorAction SilentlyContinue
        
    New-NetFirewallRule -DisplayName "WireGuard Application Out" `
        -Direction Outbound `
        -Program $wgPath `
        -Action Allow `
        -ErrorAction SilentlyContinue
}

Write-Host "✅ 방화벽 규칙 설정 완료" -ForegroundColor Green
Write-Host ""

# 2. WSL2 포트 포워딩 (WSL2 환경인 경우)
Write-Host "🔧 WSL2 포트 포워딩 확인 중..." -ForegroundColor Cyan

# WSL2 IP 확인
$wslIP = bash.exe -c "hostname -I" 2>$null
if ($wslIP) {
    $wslIP = $wslIP.Trim().Split()[0]
    Write-Host "  WSL2 IP 감지: $wslIP" -ForegroundColor Yellow
    
    # 기존 포트 포워딩 제거
    Write-Host "  기존 포트 포워딩 제거 중..." -ForegroundColor Yellow
    netsh interface portproxy delete v4tov4 listenport=41820 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy delete v4tov4 listenport=8090 listenaddress=0.0.0.0 2>$null
    
    # 새 포트 포워딩 추가
    Write-Host "  새 포트 포워딩 추가 중..." -ForegroundColor Yellow
    netsh interface portproxy add v4tov4 listenport=41820 listenaddress=0.0.0.0 connectport=41820 connectaddress=$wslIP
    netsh interface portproxy add v4tov4 listenport=8090 listenaddress=0.0.0.0 connectport=8090 connectaddress=$wslIP
    
    Write-Host "✅ WSL2 포트 포워딩 설정 완료" -ForegroundColor Green
} else {
    Write-Host "  WSL2 환경이 아닙니다." -ForegroundColor Gray
}

Write-Host ""

# 3. 네트워크 인터페이스 최적화
Write-Host "🚀 네트워크 최적화 중..." -ForegroundColor Cyan

# WireGuard 인터페이스 찾기
$wgInterface = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "WireGuard" }

if ($wgInterface) {
    Write-Host "  WireGuard 인터페이스 발견: $($wgInterface.Name)" -ForegroundColor Yellow
    
    # MTU 설정
    Set-NetIPInterface -InterfaceAlias $wgInterface.Name -NlMtuBytes 1420 -ErrorAction SilentlyContinue
    Write-Host "  ✅ MTU 1420 설정" -ForegroundColor Green
    
    # 메트릭 우선순위 조정
    Set-NetIPInterface -InterfaceAlias $wgInterface.Name -InterfaceMetric 5 -ErrorAction SilentlyContinue
    Write-Host "  ✅ 인터페이스 우선순위 설정" -ForegroundColor Green
} else {
    Write-Host "  WireGuard 인터페이스가 아직 활성화되지 않았습니다." -ForegroundColor Gray
}

Write-Host ""

# 4. 라우팅 테이블 확인
Write-Host "📊 라우팅 테이블 확인..." -ForegroundColor Cyan
$routes = Get-NetRoute | Where-Object { $_.DestinationPrefix -match "10.100." }
if ($routes) {
    Write-Host "  ✅ VPN 라우트 확인됨:" -ForegroundColor Green
    $routes | ForEach-Object {
        Write-Host "     - $($_.DestinationPrefix) via $($_.InterfaceAlias)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⚠️ VPN 라우트가 설정되지 않았습니다." -ForegroundColor Yellow
    Write-Host "     WireGuard 터널 활성화 후 자동 생성됩니다." -ForegroundColor Gray
}

Write-Host ""

# 5. DNS 설정 확인
Write-Host "🔍 DNS 설정 확인..." -ForegroundColor Cyan
if ($wgInterface) {
    $dnsServers = Get-DnsClientServerAddress -InterfaceAlias $wgInterface.Name -ErrorAction SilentlyContinue
    if ($dnsServers) {
        Write-Host "  DNS 서버:" -ForegroundColor Yellow
        $dnsServers.ServerAddresses | ForEach-Object {
            Write-Host "    - $_" -ForegroundColor Gray
        }
    }
}

Write-Host ""

# 6. 연결 테스트 함수
Write-Host "🧪 연결 테스트 준비 완료" -ForegroundColor Cyan
Write-Host ""
Write-Host "테스트 명령어:" -ForegroundColor Yellow
Write-Host "  VPN 서버 ping: ping 10.100.0.1" -ForegroundColor White
Write-Host "  API 서버 확인: curl http://10.100.0.1:8090/health" -ForegroundColor White
Write-Host "  피어 상태 확인: wg show" -ForegroundColor White

Write-Host ""

# 7. 문제 해결 도구
Write-Host "🛠️ 문제 발생 시 확인사항:" -ForegroundColor Cyan
Write-Host "  1. WireGuard 터널이 활성화되어 있는지 확인" -ForegroundColor White
Write-Host "  2. 서버의 WireGuard가 실행 중인지 확인" -ForegroundColor White
Write-Host "  3. 서버 공개키가 올바른지 확인" -ForegroundColor White
Write-Host "  4. Windows Defender 실시간 보호가 차단하지 않는지 확인" -ForegroundColor White

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  ✅ 설정 완료!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 현재 포트 포워딩 규칙 표시
Write-Host "현재 포트 포워딩 규칙:" -ForegroundColor Yellow
netsh interface portproxy show all

Write-Host ""
Write-Host "엔터키를 누르면 종료합니다..."
Read-Host