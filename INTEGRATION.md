# distributed-ai-platform 통합 가이드

이 문서는 WireGuard VPN Manager를 distributed-ai-platform과 통합하는 방법을 설명합니다.

## 📋 전체 아키텍처

```
[인터넷]
    │
    ├── [VPN Manager Server] (독립 서버)
    │    ├─ WireGuard Server (10.100.0.254)
    │    └─ Management API (8090)
    │
    ├── [Central Server] (NAT 환경 가능)
    │    ├─ VPN Client (10.100.0.1)
    │    ├─ API Server (8000)
    │    └─ FL Server (5002)
    │
    └── [Worker Nodes] (NAT 환경 가능)
         ├─ Worker 1: VPN Client (10.100.1.1)
         ├─ Worker 2: VPN Client (10.100.1.2)
         └─ Worker N: VPN Client (10.100.1.N)
```

## 🚀 배포 단계

### 1단계: VPN Manager 서버 배포

#### 1.1 독립 서버 준비
```bash
# VPN Manager 전용 서버 (공인 IP 필요)
ssh vpn-server

# 프로젝트 클론
git clone https://github.com/your-org/wireguard-vpn-manager.git
cd wireguard-vpn-manager

# 실행 권한 부여
chmod +x scripts/*.sh
```

#### 1.2 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
# SERVERURL=your-public-ip-or-domain
# API_TOKEN=secure-random-token-here
```

#### 1.3 배포
```bash
./scripts/deploy.sh
```

#### 1.4 확인
```bash
# API 상태 확인
curl http://localhost:8090/health

# 환경변수 저장 (나중에 사용)
echo "VPN_API_URL=http://$(curl -s ifconfig.me):8090"
echo "API_TOKEN=$(grep API_TOKEN .env | cut -d= -f2)"
```

### 2단계: 중앙서버 VPN 통합

#### 2.1 중앙서버 접속
```bash
ssh central-server
cd distributed-ai-platform/central-server
```

#### 2.2 VPN 설정 스크립트 생성
```bash
cat > setup-vpn.sh << 'EOF'
#!/bin/bash

VPN_API_URL="${VPN_API_URL}"
API_TOKEN="${API_TOKEN}"

echo "[INFO] 중앙서버 VPN 설정 시작"

# VPN 관리 서버에 등록
RESPONSE=$(curl -s -X POST "$VPN_API_URL/nodes/register" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "node_id": "central-server",
        "node_type": "central",
        "hostname": "'$(hostname)'",
        "public_ip": "'$(curl -s ifconfig.me)'"
    }')

# 설정 추출
CONFIG_BASE64=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['config'])")
VPN_IP=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['vpn_ip'])")

# WireGuard 설정 저장
mkdir -p ./wireguard
echo "$CONFIG_BASE64" | base64 -d > ./wireguard/wg0.conf
chmod 600 ./wireguard/wg0.conf

echo "[SUCCESS] VPN IP: $VPN_IP"
EOF

chmod +x setup-vpn.sh
```

#### 2.3 VPN 설정 실행
```bash
export VPN_API_URL=http://vpn-server-ip:8090
export API_TOKEN=your-api-token
./setup-vpn.sh
```

#### 2.4 Docker Compose 수정
```yaml
# docker-compose.yml에 추가
services:
  wireguard-client:
    image: linuxserver/wireguard:latest
    container_name: central-wireguard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    volumes:
      - ./wireguard:/config
      - /lib/modules:/lib/modules
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
    restart: unless-stopped

  api:
    # 기존 설정...
    environment:
      - CENTRAL_SERVER_IP=10.100.0.1  # VPN IP 사용
    depends_on:
      - wireguard-client
    network_mode: "service:wireguard-client"  # VPN 네트워크 사용
```

#### 2.5 재시작
```bash
docker-compose down
docker-compose up -d
```

### 3단계: 워커노드 VPN 통합

#### 3.1 각 워커노드에서 실행
```bash
ssh worker-node-X
cd distributed-ai-platform/worker-node
```

#### 3.2 VPN 설정 스크립트 생성
```bash
cat > setup-vpn.sh << 'EOF'
#!/bin/bash

VPN_API_URL="${VPN_API_URL}"
API_TOKEN="${API_TOKEN}"
NODE_ID="${NODE_ID:-$(hostname)}"

echo "[INFO] 워커노드 VPN 설정 시작"

# VPN 관리 서버에 등록
RESPONSE=$(curl -s -X POST "$VPN_API_URL/nodes/register" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "node_id": "'$NODE_ID'",
        "node_type": "worker",
        "hostname": "'$(hostname)'",
        "public_ip": "'$(curl -s ifconfig.me)'"
    }')

# 설정 추출
CONFIG_BASE64=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['config'])")
VPN_IP=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['vpn_ip'])")

# WireGuard 설정 저장
mkdir -p ./wireguard
echo "$CONFIG_BASE64" | base64 -d > ./wireguard/wg0.conf
chmod 600 ./wireguard/wg0.conf

# 환경변수 파일 생성
cat > .env << EOL
NODE_ID=$NODE_ID
VPN_IP=$VPN_IP
HOST_IP=$VPN_IP
CENTRAL_SERVER_IP=10.100.0.1
API_TOKEN=secure_token_123
EOL

echo "[SUCCESS] VPN IP: $VPN_IP"
EOF

chmod +x setup-vpn.sh
```

#### 3.3 VPN 설정 실행
```bash
export VPN_API_URL=http://vpn-server-ip:8090
export API_TOKEN=your-api-token
export NODE_ID=worker-node-1  # 각 노드별로 고유하게 설정
./setup-vpn.sh
```

#### 3.4 Docker Compose 수정
```yaml
# docker-compose.yml에 추가
services:
  wireguard-client:
    image: linuxserver/wireguard:latest
    container_name: worker-wireguard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    volumes:
      - ./wireguard:/config
      - /lib/modules:/lib/modules
    sysctls:
      - net.ipv4.conf.all.src_valid_mark=1
    restart: unless-stopped

  worker-api:
    # 기존 설정...
    environment:
      - CENTRAL_SERVER_IP=10.100.0.1  # VPN IP 사용
      - HOST_IP=${VPN_IP}
    depends_on:
      - wireguard-client
    network_mode: "service:wireguard-client"  # VPN 네트워크 사용
```

#### 3.5 재시작
```bash
docker-compose down
docker-compose up -d
```

## 🔍 통합 확인

### 1. VPN Manager에서 전체 노드 상태 확인
```bash
# VPN Manager 서버에서
cd wireguard-vpn-manager
python3 monitoring/vpn-status.py --watch
```

### 2. 중앙서버에서 워커노드 연결 테스트
```bash
# 중앙서버 컨테이너에서
docker exec central-server-api ping -c 1 10.100.1.1  # Worker 1
docker exec central-server-api ping -c 1 10.100.1.2  # Worker 2
```

### 3. 워커노드에서 중앙서버 API 테스트
```bash
# 워커노드 컨테이너에서
docker exec worker-node-client curl http://10.100.0.1:8000/health
```

## 📝 환경변수 정리

### VPN Manager (.env)
```env
SERVERURL=vpn.example.com
API_TOKEN=secure-random-token
```

### 중앙서버 (docker-compose.yml)
```yaml
environment:
  - VPN_ENABLED=true
  - VPN_IP=10.100.0.1
```

### 워커노드 (.env)
```env
NODE_ID=worker-node-1
VPN_IP=10.100.1.1
HOST_IP=10.100.1.1
CENTRAL_SERVER_IP=10.100.0.1
```

## 🚨 주의사항

1. **방화벽 설정**
   - VPN Manager: UDP 51820, TCP 8090 개방
   - 다른 서버: UDP 51820 아웃바운드만 허용

2. **DNS 설정**
   - 컨테이너 내부에서 VPN IP 사용
   - 외부에서는 공인 IP 사용

3. **네트워크 모드**
   - `network_mode: "service:wireguard-client"` 필수
   - 모든 서비스가 VPN 네트워크 사용

4. **재시작 정책**
   - WireGuard 컨테이너는 항상 먼저 시작
   - `depends_on` 설정 확인

## 🔧 문제 해결

### VPN 연결 실패
```bash
# WireGuard 로그 확인
docker logs worker-wireguard

# 인터페이스 상태 확인
docker exec worker-wireguard wg show
```

### API 통신 실패
```bash
# 라우팅 테이블 확인
docker exec worker-node-api ip route

# DNS 확인
docker exec worker-node-api nslookup central-server
```

### 노드 재등록
```bash
# VPN Manager API로 기존 노드 삭제
curl -X DELETE -H "Authorization: Bearer $API_TOKEN" \
  http://vpn-server:8090/nodes/worker-node-1

# 다시 setup-vpn.sh 실행
./setup-vpn.sh
```