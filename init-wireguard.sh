#!/bin/bash
# WireGuard VPN 초기화 및 설정 스크립트

set -e

echo "========================================="
echo "   WireGuard VPN 서버 초기화"
echo "========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Docker 및 Docker Compose 확인
echo -e "${YELLOW}Docker 환경 확인 중...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker가 설치되지 않았습니다.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose가 설치되지 않았습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 환경 확인 완료${NC}"

# 2. 설정 디렉토리 생성
echo -e "${YELLOW}설정 디렉토리 생성 중...${NC}"
mkdir -p ./config/wg_confs
mkdir -p ./config/server
chmod -R 755 ./config

echo -e "${GREEN}✓ 디렉토리 생성 완료${NC}"

# 3. 서버 IP 감지
echo -e "${YELLOW}서버 IP 주소 감지 중...${NC}"

# 로컬 IP 감지
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "로컬 IP: $LOCAL_IP"

# 공인 IP 감지 (선택적)
PUBLIC_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "감지 실패")
echo "공인 IP: $PUBLIC_IP"

# 사용할 IP 선택
if [[ "$LOCAL_IP" =~ ^192\.168\.|^10\.|^172\. ]]; then
    SERVER_IP=$LOCAL_IP
    echo -e "${GREEN}사설망 환경 감지 - 로컬 IP 사용: $SERVER_IP${NC}"
else
    SERVER_IP=$PUBLIC_IP
    echo -e "${GREEN}공인망 환경 감지 - 공인 IP 사용: $SERVER_IP${NC}"
fi

# 4. .env 파일 생성
echo -e "${YELLOW}.env 파일 생성 중...${NC}"

cat > .env << EOF
# WireGuard VPN 설정 (워커 노드용)
SERVERURL=$SERVER_IP
LOCAL_SERVER_IP=$LOCAL_IP
WIREGUARD_CONFIG_PATH=./config

# 중앙서버 URL (VPN 없이 직접 접속)
CENTRAL_SERVER_URL=http://$SERVER_IP:8000

# PostgreSQL 설정
DB_USER=vpnuser
DB_PASSWORD=vpnpass123
DB_NAME=wireguard_vpn

# API 설정
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=240

# Network 설정 (워커 노드용)
VPN_SUBNET=10.100.0.0/16
VPN_SERVER_IP=10.100.1.1
EOF

echo -e "${GREEN}✓ .env 파일 생성 완료${NC}"

# 5. WireGuard 서버 키 생성
echo -e "${YELLOW}WireGuard 서버 키 생성 중...${NC}"

# 키 생성
PRIVATE_KEY=$(wg genkey)
PUBLIC_KEY=$(echo $PRIVATE_KEY | wg pubkey)

# 서버 설정 파일 생성
cat > ./config/wg_confs/wg0.conf << EOF
[Interface]
Address = 10.100.1.1/16
ListenPort = 41820
PrivateKey = $PRIVATE_KEY
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
SaveConfig = false

# 피어들은 API를 통해 동적으로 추가됩니다
EOF

# 공개키 저장
echo $PUBLIC_KEY > ./config/server/publickey-server
echo $PUBLIC_KEY > ./config/server/publickey

echo -e "${GREEN}✓ 서버 키 생성 완료${NC}"
echo "서버 공개키: $PUBLIC_KEY"

# 6. Docker 컨테이너 시작
echo -e "${YELLOW}Docker 컨테이너 시작 중...${NC}"

# 기존 컨테이너 정지 및 제거
docker-compose down 2>/dev/null || true

# 컨테이너 시작
docker-compose up -d

# 상태 확인
sleep 5
if docker ps | grep -q wireguard-server; then
    echo -e "${GREEN}✓ WireGuard 서버 시작 성공${NC}"
else
    echo -e "${RED}WireGuard 서버 시작 실패${NC}"
    docker-compose logs wireguard-server
    exit 1
fi

if docker ps | grep -q wireguard-api; then
    echo -e "${GREEN}✓ API 서버 시작 성공${NC}"
else
    echo -e "${RED}API 서버 시작 실패${NC}"
    docker-compose logs api
    exit 1
fi

# 7. 네트워크 설정 확인
echo -e "${YELLOW}네트워크 설정 확인 중...${NC}"

# WireGuard 인터페이스 확인
docker exec wireguard-server wg show wg0 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ WireGuard 인터페이스 활성화 확인${NC}"
else
    echo -e "${RED}WireGuard 인터페이스 활성화 실패${NC}"
fi

# 8. 방화벽 규칙 설정 (선택적)
echo -e "${YELLOW}방화벽 규칙 설정 중...${NC}"

# UFW가 설치되어 있는 경우
if command -v ufw &> /dev/null; then
    sudo ufw allow 41820/udp
    sudo ufw allow 8090/tcp
    echo -e "${GREEN}✓ UFW 방화벽 규칙 추가 완료${NC}"
fi

# iptables 직접 설정 (필요시)
if command -v iptables &> /dev/null; then
    # IP 포워딩 활성화
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p > /dev/null 2>&1
    echo -e "${GREEN}✓ IP 포워딩 활성화 완료${NC}"
fi

# 9. 테스트 노드 생성
echo -e "${YELLOW}테스트 노드 생성 중...${NC}"

# API가 준비될 때까지 대기
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8090/health > /dev/null 2>&1; then
        break
    fi
    echo "API 서버 대기 중... ($WAIT_COUNT/$MAX_WAIT)"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${RED}API 서버 응답 없음${NC}"
else
    # 테스트 중앙서버 노드 생성
    curl -X POST http://localhost:8090/api/nodes \
        -H "Content-Type: application/json" \
        -d '{
            "node_id": "test-worker-001",
            "node_type": "worker",
            "name": "테스트 워커",
            "description": "초기 설정 테스트용 워커 노드"
        }' > /dev/null 2>&1
    
    echo -e "${GREEN}✓ 테스트 노드 생성 완료${NC}"
fi

# 10. 완료 메시지
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   WireGuard VPN 서버 초기화 완료!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "접속 정보:"
echo "  - API 서버: http://$SERVER_IP:8090"
echo "  - WireGuard 포트: 41820/UDP"
echo "  - VPN 서브넷 (워커용): 10.100.0.0/16"
echo "  - VPN 게이트웨이: 10.100.1.1"
echo ""
echo "유용한 명령어:"
echo "  상태 확인: docker-compose ps"
echo "  로그 확인: docker-compose logs -f"
echo "  피어 상태: docker exec wireguard-server wg show"
echo "  재시작: docker-compose restart"
echo ""
echo "노드 등록:"
echo "  1. http://$SERVER_IP:8090 접속"
echo "  2. '노드 등록' 메뉴 선택"
echo "  3. QR 코드 스캔 또는 설치 파일 다운로드"
echo ""