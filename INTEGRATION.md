# distributed-ai-platform 통합 가이드

이 문서는 WireGuard VPN Manager를 distributed-ai-platform과 통합하는 방법을 설명합니다.

## 📋 전체 아키텍처

```
[인터넷]
    │
    ├── [VPN Manager Server] (공인 IP 필요)
    │    ├─ WireGuard Server
    │    ├─ Management API (8090)
    │    └─ Web Dashboard (5000)
    │
    ├── [Central Servers] (NAT 환경 가능)
    │    ├─ Central 1: VPN Client (10.100.0.2)
    │    ├─ Central 2: VPN Client (10.100.0.3)
    │    └─ ... (최대 5개)
    │
    └── [Worker Nodes] (NAT 환경 가능)
         ├─ Worker 1: VPN Client (10.100.1.2)
         ├─ Worker 2: VPN Client (10.100.1.3)
         └─ ... (최대 10개)
```

## 🚀 빠른 시작 (원클릭 설치)

### 1단계: VPN Manager 서버 배포

```bash
# VPN Manager 서버 (공인 IP 필요)
git clone https://github.com/your-org/wireguard-vpn-manager.git
cd wireguard-vpn-manager

# 환경 설정
cp .env.example .env
nano .env  # SERVERURL과 LOCAL_SERVER_IP 설정

# 서비스 시작
docker-compose up -d
```

### 2단계: 중앙서버 등록 및 설치

#### 방법 1: 웹 인터페이스 사용 (권장)

1. 웹 브라우저에서 접속: `http://<VPN_SERVER_IP>:5000`
2. "중앙서버 등록" 클릭
3. QR 코드 생성 또는 설치 URL 복사
4. 중앙서버에서 설치 페이지 접속
5. Windows `.bat` 파일 다운로드 및 실행

#### 방법 2: API 직접 사용

```bash
# 중앙서버 등록 페이지 접속
http://<VPN_SERVER_IP>:8090/central/setup

# QR 코드 생성 후 설치 페이지로 이동
# Windows 설치 파일(.bat) 다운로드 및 실행
```

### 3단계: 워커노드 등록 및 설치

#### 방법 1: 웹 인터페이스 사용 (권장)

1. 웹 브라우저에서 접속: `http://<VPN_SERVER_IP>:5000`
2. "워커노드 등록" 클릭
3. 노드 정보 입력 (ID, 설명, 중앙서버 IP)
4. QR 코드 생성 또는 설치 URL 복사
5. 워커노드에서 설치 페이지 접속
6. Windows `.bat` 파일 다운로드 및 실행

#### 방법 2: API 직접 사용

```bash
# 워커노드 등록 페이지 접속
http://<VPN_SERVER_IP>:8090/worker/setup

# QR 코드 생성 후 설치 페이지로 이동
# Windows 설치 파일(.bat) 다운로드 및 실행
```

## 🔧 수동 설치 (Linux/Mac)

### 중앙서버 수동 설치

```bash
# 1. WireGuard 설치
sudo apt update && sudo apt install -y wireguard

# 2. VPN Manager에서 설정 파일 다운로드
wget http://<VPN_SERVER_IP>:8090/api/clients/central-server-01/config -O wg0.conf
sudo mv wg0.conf /etc/wireguard/

# 3. VPN 연결
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0

# 4. Docker Compose 실행 (VPN 전용 모드)
cd distributed-ai-platform/central-server
docker-compose -f docker-compose.vpn.yml up -d
```

### 워커노드 수동 설치

```bash
# 1. WireGuard 설치
sudo apt update && sudo apt install -y wireguard

# 2. VPN Manager에서 설정 파일 다운로드
wget http://<VPN_SERVER_IP>:8090/api/clients/worker-01/config -O wg0.conf
sudo mv wg0.conf /etc/wireguard/

# 3. VPN 연결
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0

# 4. 워커노드 컨테이너 실행
docker run -d \
  --name worker-node \
  --cap-add NET_ADMIN \
  --env NODE_ID=worker-01 \
  --env CENTRAL_SERVER_IP=10.100.0.2 \
  --env HOST_IP=$(ip addr show wg0 | grep inet | awk '{print $2}' | cut -d/ -f1) \
  your-worker-image:tag
```

## 📊 관리 및 모니터링

### VPN Manager 대시보드

- URL: `http://<VPN_SERVER_IP>:5000`
- 기능:
  - 실시간 노드 상태 모니터링
  - 노드 등록/삭제
  - QR 코드 생성
  - 연결 상태 확인

### API 엔드포인트

```bash
# 노드 목록 조회
curl -H "X-API-Key: test-token-123" http://<VPN_SERVER_IP>:8090/api/nodes/list

# 노드 상태 확인
curl -H "X-API-Key: test-token-123" http://<VPN_SERVER_IP>:8090/api/nodes/status/<node-id>

# VPN 상태 모니터링
curl http://<VPN_SERVER_IP>:8090/api/vpn/status
```

## 🔍 연결 테스트

### 중앙서버에서

```bash
# VPN 연결 확인
ping -c 1 10.100.0.1  # VPN 서버

# 워커노드 연결 확인
ping -c 1 10.100.1.2  # Worker 1
ping -c 1 10.100.1.3  # Worker 2
```

### 워커노드에서

```bash
# 중앙서버 연결 확인
ping -c 1 10.100.0.2  # Central Server

# API 연결 테스트
curl http://10.100.0.2:8000/health
```

## 📝 환경변수 설정

### VPN Manager (.env)

```env
# 서버 설정
SERVERURL=192.168.0.68  # 실제 서버 IP 또는 도메인
LOCAL_SERVER_IP=192.168.0.68
SERVERPORT=51820

# API 설정
API_TOKEN=test-token-123

# 네트워크 설정
INTERNAL_SUBNET=10.100.0.0/16
```

### 중앙서버 (.env)

```env
# VPN 설정
VPN_IP=10.100.0.2  # VPN Manager에서 할당받은 IP

# 포트 설정
API_PORT=8000
FL_PORT=5002
DASHBOARD_PORT=5000
DB_PORT=5432
MONGO_PORT=27017

# JWT 설정
JWT_SECRET_KEY=your-secret-key
```

### 워커노드 환경변수

```env
NODE_ID=worker-01
DESCRIPTION=GPU Server #1
CENTRAL_SERVER_IP=10.100.0.2
HOST_IP=10.100.1.2  # VPN Manager에서 할당받은 IP
```

## 🚨 주의사항

### Windows 방화벽 설정

설치 스크립트가 자동으로 추가하는 규칙:
- WireGuard UDP 51820
- VPN 서브넷 (10.100.0.0/16)
- ICMP (ping)
- 필요한 서비스 포트

### IP 할당 정책

- **중앙서버**: 10.100.0.2 ~ 10.100.0.6 (최대 5개)
- **워커노드**: 10.100.1.2 ~ 10.100.1.11 (최대 10개)

### Docker 네트워크

중앙서버 VPN 전용 모드:
```yaml
ports:
  - "${VPN_IP}:8000:8000"  # VPN IP에만 바인딩
```

## 🔧 문제 해결

### VPN 연결 실패

```bash
# WireGuard 상태 확인
sudo wg show

# 로그 확인
sudo journalctl -u wg-quick@wg0
```

### Windows에서 설치 실패

1. 관리자 권한으로 실행 확인
2. Windows Defender 임시 비활성화
3. 수동으로 WireGuard 설치: https://www.wireguard.com/install/

### 노드 재등록

```bash
# 기존 노드 삭제
curl -X DELETE -H "X-API-Key: test-token-123" \
  http://<VPN_SERVER_IP>:8090/api/nodes/<node-id>

# 새로 등록
http://<VPN_SERVER_IP>:8090/central/setup  # 또는 /worker/setup
```

## 📚 추가 문서

- [QUICK_START.md](./QUICK_START.md) - 빠른 시작 가이드
- [WORKER_NODE_DEPLOYMENT.md](./WORKER_NODE_DEPLOYMENT.md) - 워커노드 배포 가이드
- [README.md](./README.md) - 프로젝트 개요

## 🆘 지원

문제가 발생하면:
1. VPN Manager 대시보드에서 노드 상태 확인
2. 로그 확인: `docker-compose logs -f`
3. GitHub Issues에 문의