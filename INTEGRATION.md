# distributed-ai-platform 통합 가이드

이 문서는 WireGuard VPN Manager를 distributed-ai-platform의 워커노드 네트워크와 통합하는 방법을 설명합니다.

## 📋 전체 아키텍처

### 시스템 구성도
```
[인터넷/공개망]
    │
    ├── [중앙서버] (공인 IP: 예: 192.168.0.88)
    │    ├─ API Server (8000) ← 워커노드 직접 접속
    │    ├─ Dashboard (3000) ← 관리자 접속
    │    └─ Database & Services
    │
    └── [VPN Manager Server] (워커노드 전용)
         ├─ WireGuard Server (10.100.0.1)
         ├─ Management API (8090)
         └─ Web Dashboard (5000)
         
[VPN 네트워크] (10.100.0.0/16)
    └── [Worker Nodes] (NAT 환경 가능)
         ├─ Worker 1: VPN Client (10.100.1.2)
         ├─ Worker 2: VPN Client (10.100.1.3)
         └─ ... (최대 100개)
```

### 핵심 설계 원칙

1. **중앙서버는 VPN 불필요**
   - 이미 공개 접근 가능한 IP/도메인 보유
   - 모든 워커노드가 직접 HTTP/HTTPS로 접속
   - VPN 복잡도 제거로 안정성 향상

2. **워커노드만 VPN 사용**
   - 워커노드 간 P2P 작업 연동
   - NAT/방화벽 환경 우회
   - 중앙서버는 공개 IP로 직접 접속

3. **독립적 운영**
   - 중앙서버와 VPN 서버 독립 배포/확장
   - 중앙서버 장애 시에도 워커노드 간 통신 유지

## 🚀 빠른 시작 (워커노드 전용)

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

### 2단계: 워커노드 등록 및 설치

#### 방법 1: 웹 인터페이스 사용 (권장)

1. 웹 브라우저에서 접속: `http://<VPN_SERVER_IP>:5000`
2. "워커노드 등록" 클릭
3. 노드 정보 입력:
   - Node ID: worker-01
   - Description: GPU Server #1
   - Central Server URL: http://192.168.0.88:8000 (공개 IP)
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
  --env CENTRAL_SERVER_URL=http://192.168.0.88:8000 \
  --env VPN_IP=$(ip addr show wg0 | grep inet | awk '{print $2}' | cut -d/ -f1) \
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

### 워커노드에서

```bash
# 다른 워커노드 연결 확인 (VPN)
ping -c 1 10.100.1.3  # 다른 Worker

# 중앙서버 API 연결 테스트 (공개 IP)
curl http://192.168.0.88:8000/health
```

## 📝 환경변수 설정

### VPN Manager (.env)

```env
# 서버 설정
SERVERURL=192.168.0.68  # 실제 서버 IP 또는 도메인
LOCAL_SERVER_IP=192.168.0.68
SERVERPORT=41820

# API 설정
API_TOKEN=test-token-123

# 네트워크 설정
INTERNAL_SUBNET=10.100.0.0/16
```

### 중앙서버 (.env)

```env
# 서버 설정 (VPN 불필요)
SERVER_URL=http://192.168.0.88:8000  # 공개 접근 가능 주소

# 포트 설정
API_PORT=8000
FL_PORT=5002
DASHBOARD_PORT=3000
DB_PORT=5432
MONGO_PORT=27017

# JWT 설정
JWT_SECRET_KEY=your-secret-key
```

### 워커노드 환경변수

```env
NODE_ID=worker-01
DESCRIPTION=GPU Server #1
CENTRAL_SERVER_URL=http://192.168.0.88:8000  # 중앙서버 공개 주소
VPN_IP=10.100.1.2  # VPN Manager에서 할당받은 IP
```

## 🚨 주의사항

### Windows 방화벽 설정

설치 스크립트가 자동으로 추가하는 규칙:
- WireGuard UDP 41820
- VPN 서브넷 (10.100.0.0/16)
- ICMP (ping)
- 필요한 서비스 포트

### IP 할당 정책

- **VPN 서버**: 10.100.0.1 (고정)
- **워커노드**: 10.100.1.2 ~ 10.100.1.254 (최대 253개)
- **중앙서버**: VPN 불필요 (공개 IP 사용)

### Docker 네트워크

중앙서버 (공개 접근):
```yaml
ports:
  - "0.0.0.0:8000:8000"  # 모든 인터페이스에서 접근 가능
  - "0.0.0.0:3000:3000"  # Dashboard
```

워커노드 (VPN 전용):
```yaml
extra_hosts:
  - "central-server:192.168.0.88"  # 중앙서버 공개 IP
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
http://<VPN_SERVER_IP>:8090/worker/setup
```

## 📚 추가 문서

- [README.md](./README.md) - 프로젝트 개요
- [QUICK_START.md](./QUICK_START.md) - 빠른 시작 가이드
- [WORKER_NODE_DEPLOYMENT.md](./WORKER_NODE_DEPLOYMENT.md) - 워커노드 배포 가이드

## 🆘 지원

문제가 발생하면:
1. VPN Manager 대시보드에서 노드 상태 확인
2. 로그 확인: `docker-compose logs -f`
3. GitHub Issues에 문의