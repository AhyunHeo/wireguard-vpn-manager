# 로컬 테스트 가이드

## 🚀 빠른 시작 (로컬 테스트)

### 1. 프로젝트 클론
```bash
# 프로젝트를 /home/intown/ 디렉토리로 이동
cd /home/intown/
cp -r distributed-ai-platform/wireguard-vpn-manager ./
cd wireguard-vpn-manager
```

### 2. 실행 권한 부여
```bash
chmod +x scripts/*.sh
chmod +x client-setup/*.sh
chmod +x monitoring/*.py
```

### 3. 로컬 테스트 환경 실행
```bash
./scripts/test-local.sh
```

## 📝 테스트 시나리오

### 시나리오 1: 노드 등록 테스트

#### 1. 중앙서버 등록
```bash
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "central-server",
    "node_type": "central",
    "hostname": "central.local",
    "public_ip": "192.168.1.100"
  }'
```

#### 2. 워커노드 등록
```bash
# 워커노드 1
curl -X POST http://localhost:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-node-1",
    "node_type": "worker",
    "hostname": "worker1.local",
    "public_ip": "192.168.1.101"
  }'

# 워커노드 2
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

#### 3. 노드 목록 확인
```bash
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes | python3 -m json.tool
```

### 시나리오 2: 모니터링 테스트

#### 1. Python 모니터링 도구
```bash
# 일회성 상태 확인
python3 monitoring/vpn-status.py \
  --api-url http://localhost:8090 \
  --api-token test-token-123

# 지속적인 모니터링
python3 monitoring/vpn-status.py \
  --api-url http://localhost:8090 \
  --api-token test-token-123 \
  --watch
```

#### 2. WireGuard UI 접속
브라우저에서 http://localhost:5000 접속
- Username: admin
- Password: admin123

### 시나리오 3: 설정 파일 다운로드

#### 특정 노드의 설정 조회
```bash
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes/worker-node-1/config | \
  python3 -c "import sys, json, base64; \
    data = json.load(sys.stdin); \
    print(base64.b64decode(data['config']).decode())"
```

### 시나리오 4: 노드 제거 테스트
```bash
# 노드 제거
curl -X DELETE \
  -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes/worker-node-2

# 확인
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8090/nodes
```

## 🔍 디버깅

### 로그 확인
```bash
# 모든 서비스 로그
docker-compose -f docker-compose.local.yml logs

# API 서버 로그만
docker-compose -f docker-compose.local.yml logs vpn-api

# 실시간 로그
docker-compose -f docker-compose.local.yml logs -f
```

### 컨테이너 상태 확인
```bash
docker-compose -f docker-compose.local.yml ps
```

### WireGuard 상태 확인
```bash
# WireGuard 인터페이스 상태
docker exec wireguard-server wg show

# 설정 파일 확인
docker exec wireguard-server cat /config/wg0.conf
```

### PostgreSQL 접속
```bash
# psql로 직접 접속
docker exec -it vpn-postgres psql -U vpn -d vpndb

# 노드 테이블 확인
docker exec vpn-postgres psql -U vpn -d vpndb -c "SELECT * FROM nodes;"
```

## 🛠️ 문제 해결

### 1. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep -E "8090|51820|5433|5000"

# 포트 변경이 필요한 경우 docker-compose.local.yml 수정
```

### 2. WireGuard 커널 모듈 문제
```bash
# 커널 모듈 확인
lsmod | grep wireguard

# 모듈 로드
sudo modprobe wireguard
```

### 3. API 연결 실패
```bash
# 방화벽 확인
sudo iptables -L -n

# Docker 네트워크 확인
docker network ls
docker network inspect wireguard-vpn-manager_vpn_net
```

## 🧹 정리

### 테스트 환경 종료
```bash
docker-compose -f docker-compose.local.yml down
```

### 완전 정리 (볼륨 포함)
```bash
docker-compose -f docker-compose.local.yml down -v
rm -rf config/
```

## 📚 API 문서

로컬 테스트 환경 실행 후:
- Swagger UI: http://localhost:8090/docs
- ReDoc: http://localhost:8090/redoc

## 다음 단계

로컬 테스트가 완료되면:

1. **실제 서버에 배포**
   - 공인 IP가 있는 서버에 VPN Manager 배포
   - `./scripts/deploy.sh` 사용

2. **중앙서버 연동**
   - distributed-ai-platform의 중앙서버에 VPN 클라이언트 설정
   - `central-server/setup-vpn.sh` 스크립트 사용

3. **워커노드 연동**
   - 각 워커노드에 VPN 클라이언트 설정
   - `worker-node/setup-vpn.sh` 스크립트 사용