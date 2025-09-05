# WireGuard VPN Manager

워커노드 간 P2P 통신을 위한 WireGuard VPN 관리 시스템

## 📋 개요

이 프로젝트는 분산 AI 플랫폼의 **워커노드들 간 안전한 P2P 통신**을 위한 WireGuard 기반 VPN 관리 시스템입니다. 중앙서버는 공개 IP로 직접 접근 가능하며, 워커노드들만 VPN을 통해 서로 통신합니다.

## 🏗️ 시스템 아키텍처

### 전체 구조
```
[인터넷/공개망]
    │
    ├── [중앙서버] (공인 IP 또는 도메인) - 192.168.0.88
    │    ├─ API Server (Port 8000) - 모든 워커노드가 직접 접속
    │    ├─ Dashboard (Port 3000) - 관리자 웹 인터페이스
    │    └─ Database & Services
    │    
    └── [VPN Server] (워커노드 전용) 192.168.0.68
         ├── WireGuard Server (10.100.0.1)
         ├── Management API (Port 8090)
         └── Web Dashboard (Port 5000)
         
[VPN 네트워크] (10.100.0.0/16)
    └── Worker Nodes (10.100.1.x) (worker끼리 서로 통신 문제없이 되어야함)
         ├── Worker #1 (A컴퓨터 VPN Server의 wireguard 등록 - 10.100.1.2)
         ├── Worker #2  (B컴퓨터 VPN Server의 wireguard 등록 - 10.100.1.2)
         └── Worker #N

    *A 컴퓨터: 192.168.0.88, B 컴퓨터: 192.168.0.30     
```

### 핵심 설계 원칙

1. **중앙서버**
   - VPN 불필요 (이미 공개 접근 가능)
   - 고정 IP 또는 도메인으로 운영
   - 모든 워커노드가 직접 HTTP/HTTPS로 접속
   - 작업 할당, 모니터링, 관리 기능 제공

2. **워커노드**
   - VPN 클라이언트로만 동작
   - 중앙서버: 공개 IP로 직접 접속
   - 다른 워커노드: VPN을 통한 P2P 통신
   - NAT/방화벽 환경에서도 작동

3. **VPN 서버**
   - 워커노드 전용 네트워크 관리
   - 중앙서버와 독립적으로 운영
   - 자동 IP 할당 및 키 관리

## 🚀 빠른 시작

### 1. 프로젝트 클론
```bash
git clone https://github.com/AhyunHeo/wireguard-vpn-manager.git
cd wireguard-vpn-manager
```

### 2. 방화벽 설정 (VPN Manager 서버)

VPN Manager를 실행할 서버에서 다음 포트를 열어야 합니다:

#### Windows 서버
```powershell
# PowerShell 관리자 권한으로 실행
# API 서버 포트 (필수) - 개인 및 공용 네트워크 모두 허용
New-NetFirewallRule -DisplayName "VPN Manager API" -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -Profile Any

# WireGuard VPN 포트 (필수) - 개인 및 공용 네트워크 모두 허용
New-NetFirewallRule -DisplayName "WireGuard VPN" -Direction Inbound -Protocol UDP -LocalPort 41820 -Action Allow -Profile Any

# ICMP 규칙 추가 (필수) - ping 응답 허용
New-NetFirewallRule -DisplayName "WireGuard ICMP In" -Direction Inbound -Protocol ICMPv4 -IcmpType 8 -Action Allow

# WireGuard UI 포트 (선택사항) - 개인 및 공용 네트워크 모두 허용
New-NetFirewallRule -DisplayName "WireGuard UI" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Any

# 중요: Windows가 네트워크를 "공용"으로 인식하는 경우가 많습니다!
# 확인 방법: 설정 > 네트워크 및 인터넷 > 상태 > 속성에서 네트워크 프로필 확인
```

#### Linux 서버
```bash
# UFW 사용 시
sudo ufw allow 8090/tcp comment 'VPN Manager API'
sudo ufw allow 41820/udp comment 'WireGuard VPN'
sudo ufw allow 5000/tcp comment 'WireGuard UI (optional)'
sudo ufw reload

# iptables 사용 시
sudo iptables -A INPUT -p tcp --dport 8090 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 41820 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

#### 클라우드 환경 (AWS/GCP/Azure)
Security Group 또는 방화벽 규칙에서 다음 포트 허용:
- TCP 8090 (API)
- UDP 41820 (VPN)
- TCP 5000 (UI, 선택사항)

### 3. 로컬 테스트
```bash
# 실행 권한 부여
chmod +x scripts/*.sh

# 로컬 테스트 환경 실행
./scripts/test-local.sh
```

#### ⚠️ Windows Docker Desktop 사용 시 주의사항
Windows에서 Docker Desktop을 사용하는 경우:
- `localhost:8090` 대신 `본인IP:8090` 사용 필요 (예: `192.168.1.100:8090`)
- WSL2 백엔드를 사용하면 Docker가 별도 가상 네트워크에서 실행됩니다
- 확인 방법: `ipconfig`로 IPv4 주소 확인 후 해당 IP 사용

### 4. 프로덕션 배포
```bash
# 환경 설정
cp .env.example .env
# .env 파일 편집하여 설정

# 배포
./scripts/deploy.sh
```

## 📁 프로젝트 구조

```
wireguard-vpn-manager/
├── api/                    # FastAPI 관리 서버
│   ├── main.py            # API 엔드포인트
│   ├── models.py          # 데이터 모델
│   ├── database.py        # DB 연결
│   └── wireguard_manager.py # WireGuard 제어
├── client-setup/          # 클라이언트 설정 스크립트
├── monitoring/            # 모니터링 도구
├── docker-compose.yml     # 프로덕션 설정
├── docker-compose.local.yml # 로컬 테스트 설정
└── deploy.sh             # 배포 스크립트
```

## 🔧 주요 기능

- ✅ **원클릭 VPN 연결** - URL 접속만으로 자동 설치
- ✅ **QR 코드 지원** - 모바일에서 QR 스캔으로 간편 연결
- ✅ 자동 키 생성 및 배포
- ✅ RESTful API로 노드 관리
- ✅ 동적 IP 할당 (중앙서버: 10.100.0.x, 워커: 10.100.1.x)
- ✅ 실시간 연결 상태 모니터링
- ✅ Docker 기반 쉬운 배포
- ✅ NAT/방화벽 우회

## 🌐 웹 기반 원클릭 설치

### 비전공자도 쉽게!
```
1. 관리자가 링크 생성
2. 워커 운영자가 브라우저에서 링크 클릭
3. 자동으로 VPN 설치 및 연결 완료!
```

터미널이나 명령어 지식이 전혀 필요 없습니다.

## 🔐 보안

- API 토큰 기반 인증
- WireGuard의 강력한 암호화
- 자동 키 순환 지원
- 최소 권한 원칙 적용

## 📊 모니터링

```bash
# API로 노드 목록 조회
curl -H "Authorization: Bearer test-token-123" http://localhost:8090/nodes

# WireGuard 서버 상태 확인
curl -H "Authorization: Bearer test-token-123" http://localhost:8090/status/wireguard

# WireGuard UI 접속
# 브라우저: http://localhost:5000
```

## ⚠️ 네트워크 요구사항

### 필수 포트
| 포트 | 프로토콜 | 용도 | 필수 여부 |
|------|---------|------|----------|
| 8090 | TCP | VPN Manager API | ✅ 필수 |
| 41820 | UDP | WireGuard VPN | ✅ 필수 |
| 5000 | TCP | WireGuard UI | 선택 |
| 5433 | TCP | PostgreSQL (로컬) | 로컬만 |

### 네트워크 설정 확인
```bash
# 포트 열림 확인 (VPN Manager 서버에서)
netstat -an | grep -E "8090|41820"

# 외부에서 접근 테스트 (워커 노드에서)
curl http://VPN_MANAGER_IP:8090/health
```
