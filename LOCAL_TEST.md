# 🚀 WireGuard VPN Manager 로컬 테스트 가이드

## 📋 목차
- [빠른 시작](#빠른-시작)
- [웹 기반 원클릭 연결](#웹-기반-원클릭-연결)
- [QR 코드로 연결](#qr-코드로-연결)
- [API 직접 테스트](#api-직접-테스트)
- [문제 해결](#문제-해결)

## 빠른 시작

### 1. 프로젝트 클론 및 준비
```bash
# 프로젝트 클론
git clone https://github.com/AhyunHeo/wireguard-vpn-manager.git
cd wireguard-vpn-manager

# 실행 권한 부여
chmod +x scripts/*.sh
```

### 2. 로컬 환경 실행
```bash
# 한 줄 실행!
./scripts/test-local.sh
```

이 명령어 하나로:
- ✅ PostgreSQL 데이터베이스 시작
- ✅ WireGuard 서버 시작
- ✅ VPN API 서버 시작
- ✅ 모든 서비스 자동 설정

### 3. 서비스 확인
```bash
# 헬스체크
curl http://localhost:8090/health

# 응답: {"status":"healthy","service":"vpn-manager"}
```

## 🌐 웹 기반 원클릭 연결

### 방법 1: QR 코드 생성 페이지 (추후 기능 테스트 완료 후 distrributed-ai-platform 노드 등록 페이지에서 생성하여 제공하도록 연결 필요함.)

1. **브라우저에서 QR 생성 페이지 접속**
   ```
   http://localhost:8090/vpn-qr
   ```

2. **노드 정보 입력**
   - 노드 ID: `worker-gpu-1` (원하는 이름)
   - 노드 타입: `worker` (기본값)
   - "QR 코드 생성" 클릭

3. **생성된 QR 코드 사용**
   - 📱 모바일: QR 코드 스캔
   - 💻 PC: URL 복사 후 브라우저 접속

### 방법 2: 직접 링크 생성

```bash
# API로 조인 링크 생성
curl -X POST http://localhost:8090/api/generate-qr \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "test-worker-1",
    "node_type": "worker"
  }'

# 응답 예시:
{
  "token": "abc123xyz",
  "join_url": "http://localhost:8090/join/abc123xyz",
  "qr_code": "data:image/png;base64,...",
  "expires_at": "2024-01-01T00:00:00Z"
}
```

생성된 `join_url`을 브라우저에서 열면 자동 설치 페이지로 이동!

## 📱 QR 코드로 연결

### 시나리오: 노트북(관리자) → 다른 컴퓨터(워커)

**관리자 노트북에서:**
1. QR 생성 페이지 접속: `http://localhost:8090/vpn-qr`
2. 노드 ID 입력: `worker-node-1`
3. QR 코드 생성

**워커 컴퓨터에서:**
1. 스마트폰으로 QR 스캔
2. 자동으로 설치 페이지 이동
3. OS 선택 (Linux/Windows/Mac)
4. 설치 명령어 자동 복사
5. 터미널에 붙여넣기 → Enter

**완료!** 🎉

## 🔧 API 직접 테스트

### 1. 노드 등록 (기존 방식)
```bash
# 중앙서버 등록
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "central-server",
    "node_type": "central",
    "hostname": "central.local",
    "public_ip": "192.168.1.100"
  }'

# 워커노드 등록
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-node-1",
    "node_type": "worker",
    "hostname": "worker1.local",
    "public_ip": "192.168.1.101"
  }'
```

### 2. 노드 목록 확인
```bash
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes | python3 -m json.tool
```

### 3. WireGuard 상태 확인
```bash
# API로 확인
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/status/wireguard | python3 -m json.tool

# Docker 컨테이너에서 직접 확인
docker exec wireguard-server wg show
```

## 📊 모니터링

### Python 모니터링 도구
```bash
# 일회성 상태 확인
python3 monitoring/vpn-status.py \
  --api-url http://localhost:8090 \
  --api-token test-token-123

# 실시간 모니터링 (5초마다 갱신)
python3 monitoring/vpn-status.py \
  --api-url http://localhost:8090 \
  --api-token test-token-123 \
  --watch
```

### WireGuard UI
```
브라우저: http://localhost:5000
Username: admin
Password: admin123
```

## 🎯 실제 사용 시나리오

### 시나리오 1: 로컬 개발 환경
```bash
# 1. VPN Manager 시작
./scripts/test-local.sh

# 2. QR 페이지에서 노드 등록
브라우저: http://localhost:8090/vpn-qr

# 3. 다른 로컬 VM이나 Docker 컨테이너에서 연결
curl -sSL http://host-ip:8090/join/YOUR_TOKEN | bash
```

### 시나리오 2: 팀 협업 환경
```bash
# 1. 팀장이 VPN Manager 실행
./scripts/test-local.sh

# 2. 각 팀원용 QR 코드 생성
- developer-1
- developer-2
- gpu-worker-1

# 3. Slack/카톡으로 QR 이미지 공유

# 4. 팀원들이 각자 연결
브라우저에서 URL 클릭 → 자동 설치
```

### 시나리오 3: 분산 GPU 클러스터
```bash
# 1. 중앙 서버에 VPN Manager 배포
docker-compose up -d

# 2. GPU 노드별 QR 생성
- gpu-node-1 (RTX 3090)
- gpu-node-2 (RTX 4090)
- gpu-node-3 (A100)

# 3. 각 GPU 서버에서 웹 페이지 접속
http://vpn-manager:8090/join/TOKEN

# 4. 자동 설치 후 VPN 네트워크로 통신
```

## 🛠️ 문제 해결

### 포트 충돌
```bash
# 사용 중인 포트 확인
sudo lsof -i :8090
sudo lsof -i :51820
sudo lsof -i :5433

# docker-compose.local.yml에서 포트 변경
ports:
  - "8091:8090"  # API 포트 변경
```

### 서비스가 시작되지 않을 때
```bash
# 완전 초기화
docker-compose -f docker-compose.local.yml down -v
rm -rf config/
./scripts/test-local.sh
```

### WireGuard 연결 실패
```bash
# WireGuard 로그 확인
docker logs wireguard-server

# API 로그 확인
docker logs vpn-api

# 네트워크 확인
docker network inspect wireguard-vpn-manager_vpn_net
```

### QR 코드가 생성되지 않을 때
```bash
# API 컨테이너 재빌드
docker-compose -f docker-compose.local.yml build vpn-api
docker-compose -f docker-compose.local.yml up -d
```

## 📚 API 문서

### Swagger UI
```
http://localhost:8090/docs
```

### ReDoc
```
http://localhost:8090/redoc
```

### 주요 엔드포인트
- `GET /vpn-qr` - QR 코드 생성 페이지
- `GET /join/{token}` - 웹 기반 설치 페이지
- `POST /api/generate-qr` - QR 코드 생성 API
- `GET /api/install/{token}` - 설치 스크립트 다운로드
- `POST /nodes/register` - 노드 등록 (기존 API)
- `GET /nodes` - 노드 목록 조회
- `GET /status/wireguard` - WireGuard 상태

## 🧹 정리

### 서비스 종료
```bash
docker-compose -f docker-compose.local.yml down
```

### 완전 정리 (데이터 포함)
```bash
docker-compose -f docker-compose.local.yml down -v
rm -rf config/
```

## 💡 팁

1. **QR 코드 유효시간**: 15분 (보안을 위해)
2. **동시 접속**: 여러 노드 동시 등록 가능
3. **자동 재연결**: systemd 서비스로 등록되어 재부팅 후에도 자동 연결
4. **방화벽**: 51820/UDP 포트 열기 필요 (실제 배포 시)

## 🎉 이제 시작하세요!

```bash
# 1단계: 실행
./scripts/test-local.sh

# 2단계: QR 생성
브라우저: http://localhost:8090/vpn-qr

# 3단계: 연결!
QR 스캔 or URL 클릭
```

**끝!** 이제 모든 노드가 안전한 VPN 네트워크로 연결됩니다! 🚀