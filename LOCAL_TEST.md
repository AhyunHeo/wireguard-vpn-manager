# 🚀 WireGuard VPN Manager 실제 테스트 가이드

## 📋 테스트 시나리오
1. [로컬에서 VPN Manager 실행](#1-로컬에서-vpn-manager-실행)
2. [중앙서버 등록 테스트](#2-중앙서버-등록-테스트)
3. [워커노드 등록 테스트](#3-워커노드-등록-테스트)
4. [VPN 연결 확인](#4-vpn-연결-확인)
5. [플랫폼 통합 테스트](#5-플랫폼-통합-테스트)

---

## 1. 로컬에서 VPN Manager 실행

### Step 1: 프로젝트 준비
```bash
# 프로젝트 클론
git clone https://github.com/AhyunHeo/wireguard-vpn-manager.git
cd wireguard-vpn-manager

# 실행 권한 부여
chmod +x scripts/*.sh
```

### Step 2: Docker 환경 시작
```bash
# 모든 서비스 한 번에 시작
./scripts/test-local.sh
```

### Step 3: 서비스 확인
```bash
# 헬스체크 (Linux/Mac 또는 Docker 직접 설치)
curl http://localhost:8090/health

# Windows Docker Desktop 사용 시 (본인 IP 사용)
# ipconfig로 확인한 IP 사용 (예: 192.168.1.100)
curl http://192.168.1.100:8090/health

# 정상 응답 확인
# {"status":"healthy","service":"vpn-manager"}
```

### Step 4: 실행 중인 서비스 확인
```bash
# Docker 컨테이너 상태
docker ps

# 다음 컨테이너들이 실행 중이어야 함:
# - wireguard-server (포트 51820)
# - vpn-api (포트 8090)
# - vpn-postgres (포트 5433)
# - wireguard-ui (포트 5000)
```

---

## 2. 중앙서버 등록 테스트

### 방법 A: API로 직접 등록
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

# 성공 응답 예시:
{
  "node_id": "central-server",
  "vpn_ip": "10.100.0.1",
  "config": "Base64로 인코딩된 WireGuard 설정",
  "public_key": "생성된 공개키",
  "server_public_key": "서버 공개키",
  "server_endpoint": "localhost:51820"
}
```

### 방법 B: 웹 UI로 등록 (개발 중)
```
1. 브라우저: http://localhost:8090/vpn-qr
2. 노드 ID: central-server
3. 노드 타입: central
4. QR 코드 생성
```

---

## 3. 워커노드 등록 테스트

### 시나리오 1: 동일 컴퓨터에서 테스트

```bash
# 워커노드 1 등록
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-node-1",
    "node_type": "worker",
    "hostname": "worker1.local",
    "public_ip": "192.168.1.101"
  }'

# 워커노드 2 등록
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-node-2",
    "node_type": "worker",
    "hostname": "worker2.local",
    "public_ip": "192.168.1.102"
  }'
```

### 시나리오 2: 다른 컴퓨터에서 실제 연결

**VPN Manager 서버 (노트북):**
```bash
# 1. VPN Manager 실행
./scripts/test-local.sh

# 2. 자신의 IP 확인
ip addr show  # Linux/Mac
ipconfig      # Windows

# 예: 192.168.1.100
```

**워커 컴퓨터에서:**

#### 옵션 1: URL 클릭 방식 (비전공자용)
```
1. 브라우저 열기
2. URL 입력: http://192.168.1.100:8090/one-click/test-token
3. "지금 시작하기" 클릭
4. 자동 설치 진행
```

#### 옵션 2: 수동 설정 (개발자용)
```bash
# 설정 받기
curl -X POST http://192.168.1.100:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "real-worker-1",
    "node_type": "worker",
    "hostname": "'$(hostname)'",
    "public_ip": "'$(curl -s ifconfig.me)'"
  }' | jq -r '.config' | base64 -d > wg0.conf

# WireGuard 설치 (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y wireguard

# VPN 연결
sudo wg-quick up ./wg0.conf
```

---

## 4. VPN 연결 확인

### 등록된 노드 목록 확인
```bash
# 모든 노드 조회
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes | python3 -m json.tool

# 응답 예시:
[
  {
    "node_id": "central-server",
    "node_type": "central",
    "vpn_ip": "10.100.0.1",
    "status": "registered",
    "connected": false  # 아직 실제 연결 전
  },
  {
    "node_id": "worker-node-1",
    "node_type": "worker",
    "vpn_ip": "10.100.1.1",
    "status": "registered",
    "connected": false
  }
]
```

### WireGuard 상태 확인
```bash
# API로 확인
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/status/wireguard | python3 -m json.tool

# Docker에서 직접 확인
docker exec wireguard-server wg show

# WireGuard UI 확인
브라우저: http://localhost:5000
ID: admin / PW: admin123
```

### 실제 VPN 연결 테스트
```bash
# 워커 노드에서 VPN IP로 ping 테스트
ping 10.100.0.1  # VPN 서버
ping 10.100.1.1  # 다른 워커 노드

# 연결 상태 재확인
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes

# connected: true로 변경되었는지 확인
```

---

## 5. 플랫폼 통합 테스트

### distributed-ai-platform과 연동

**Step 1: 중앙서버에 VPN 클라이언트 설정**
```bash
# distributed-ai-platform/central-server에서
cd distributed-ai-platform/central-server

# VPN 설정 추가 (docker-compose.yml 수정)
# networks 섹션에 추가:
networks:
  default:
    external:
      name: wireguard-vpn-manager_vpn_net
```

**Step 2: 워커노드 설정**
```bash
# distributed-ai-platform/worker-node에서
cd distributed-ai-platform/worker-node

# config.yaml 수정
central_server_url: http://10.100.0.1:8000  # VPN IP 사용
```

**Step 3: 통신 테스트**
```bash
# 워커노드에서 중앙서버 API 호출
curl http://10.100.0.1:8000/api/v1/health

# 중앙서버에서 워커노드 상태 확인
curl http://10.100.0.1:8000/api/v1/nodes
```

---

## 🔍 실제 테스트 체크리스트

### ✅ 기본 기능
- [ ] VPN Manager 시작
- [ ] 헬스체크 응답 확인
- [ ] PostgreSQL 연결 확인
- [ ] WireGuard 컨테이너 실행 확인

### ✅ 노드 등록
- [ ] 중앙서버 등록 성공
- [ ] 워커노드 1개 등록 성공
- [ ] 워커노드 2개 이상 등록 성공
- [ ] 노드 목록 조회 가능

### ✅ VPN 연결
- [ ] WireGuard 설정 파일 생성됨
- [ ] VPN IP 할당 확인 (10.100.x.x)
- [ ] 실제 WireGuard 연결 성공
- [ ] 노드 간 ping 테스트 성공

### ✅ 웹 기반 설치
- [ ] QR 코드 생성 페이지 접속
- [ ] 원클릭 URL 동작 확인
- [ ] 자동 설치 프로세스 완료

### ✅ 플랫폼 통합
- [ ] 중앙서버가 VPN 네트워크 사용
- [ ] 워커노드가 VPN IP로 중앙서버 접속
- [ ] 실제 AI 작업 할당 가능
- [ ] 작업 결과 전송 성공

---

## 🛠️ 문제 해결

### 1. "Connection refused" 에러
```bash
# 서비스 재시작
docker-compose -f docker-compose.local.yml restart

# 로그 확인
docker logs vpn-api
docker logs wireguard-server
```

### 2. 노드 등록은 되는데 연결이 안 될 때
```bash
# 방화벽 확인
sudo iptables -L -n | grep 51820

# UDP 포트 열기
sudo ufw allow 51820/udp  # Ubuntu
```

### 3. VPN IP 충돌
```bash
# 모든 노드 삭제 후 재등록
curl -X DELETE \
  -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes/worker-node-1

# DB 초기화
docker-compose -f docker-compose.local.yml down -v
./scripts/test-local.sh
```

### 4. 실제 서버 간 연결 실패
```bash
# NAT 환경 확인
# 공인 IP가 필요한 경우 클라우드 서버 사용 권장

# AWS/GCP에서 테스트
# Security Group에서 51820/UDP 포트 열기
```

---

## 📊 모니터링

### Python 모니터링 스크립트
```bash
# 실시간 상태 모니터링
python3 monitoring/vpn-status.py \
  --api-url http://localhost:8090 \
  --api-token test-token-123 \
  --watch
```

### 로그 확인
```bash
# 실시간 로그 스트리밍
docker-compose -f docker-compose.local.yml logs -f

# 특정 서비스 로그
docker logs -f vpn-api
docker logs -f wireguard-server
```

---

## 🎯 성공 기준

테스트가 성공적이려면:

1. **노드 등록**: 중앙서버 + 워커노드 2개 이상 등록
2. **VPN 연결**: 모든 노드가 `connected: true` 상태
3. **통신 확인**: 노드 간 ping 및 API 호출 성공
4. **플랫폼 연동**: distributed-ai-platform이 VPN 네트워크로 통신

---

## 💡 다음 단계

테스트 성공 후:

1. **프로덕션 배포**
   - 공인 IP 서버에 배포
   - 도메인 설정
   - SSL 인증서 적용

2. **플랫폼 통합**
   - distributed-ai-platform에 VPN 자동 연결 기능 추가
   - 노드 등록 시 자동으로 VPN 설정

3. **관리 도구**
   - 웹 대시보드 개발
   - 모니터링 시스템 구축
   - 자동 장애 복구

---

## 📞 지원

문제가 있으면:
- GitHub Issues: https://github.com/AhyunHeo/wireguard-vpn-manager/issues
- 로그 첨부: `docker-compose logs > debug.log`