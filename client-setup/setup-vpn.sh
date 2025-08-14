#!/bin/bash

# WireGuard VPN 클라이언트 설정 스크립트
# 중앙서버와 워커노드에서 사용

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 환경변수 확인
VPN_API_URL="${VPN_API_URL:-http://localhost:8090}"
API_TOKEN="${API_TOKEN:-test-token-123}"
NODE_ID="${NODE_ID:-$(hostname)}"
NODE_TYPE="${NODE_TYPE:-worker}"
PUBLIC_IP="${PUBLIC_IP:-$(curl -s ifconfig.me 2>/dev/null || echo "unknown")}"

echo "======================================"
echo "WireGuard VPN 클라이언트 설정"
echo "======================================"
echo ""
echo "설정 정보:"
echo "  VPN API URL: $VPN_API_URL"
echo "  노드 ID: $NODE_ID"
echo "  노드 타입: $NODE_TYPE"
echo "  공인 IP: $PUBLIC_IP"
echo ""

# WireGuard 설치 확인
if ! command -v wg &> /dev/null; then
    echo -e "${YELLOW}[INFO] WireGuard 설치 중...${NC}"
    
    # OS 감지
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        apt-get update
        apt-get install -y wireguard wireguard-tools
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        yum install -y epel-release
        yum install -y wireguard-tools
    else
        echo -e "${RED}[ERROR] 지원하지 않는 OS입니다.${NC}"
        exit 1
    fi
fi

# VPN 관리 서버에 노드 등록
echo -e "${GREEN}[INFO] VPN 관리 서버에 노드 등록 중...${NC}"

RESPONSE=$(curl -s -X POST "$VPN_API_URL/nodes/register" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"node_id\": \"$NODE_ID\",
        \"node_type\": \"$NODE_TYPE\",
        \"hostname\": \"$(hostname)\",
        \"public_ip\": \"$PUBLIC_IP\"
    }")

# 응답 확인
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] 노드 등록 실패${NC}"
    exit 1
fi

# JSON 파싱 (Python 사용)
if command -v python3 &> /dev/null; then
    CONFIG_BASE64=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('config', ''))
except:
    print('')
")
    
    VPN_IP=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('vpn_ip', ''))
except:
    print('')
")
else
    echo -e "${RED}[ERROR] Python3가 필요합니다.${NC}"
    exit 1
fi

if [ -z "$CONFIG_BASE64" ]; then
    echo -e "${RED}[ERROR] 설정 파일을 받지 못했습니다.${NC}"
    echo "응답: $RESPONSE"
    exit 1
fi

# WireGuard 설정 디렉토리 생성
mkdir -p /etc/wireguard

# WireGuard 설정 파일 생성
echo -e "${GREEN}[INFO] WireGuard 설정 파일 생성 중...${NC}"
echo "$CONFIG_BASE64" | base64 -d > /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/wg0.conf

# WireGuard 인터페이스 시작
echo -e "${GREEN}[INFO] WireGuard 인터페이스 시작 중...${NC}"

# 기존 인터페이스가 있으면 중지
wg-quick down wg0 2>/dev/null || true

# 인터페이스 시작
wg-quick up wg0

# systemd 서비스 활성화 (있는 경우)
if command -v systemctl &> /dev/null; then
    systemctl enable wg-quick@wg0 2>/dev/null || true
    systemctl start wg-quick@wg0 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}[SUCCESS] VPN 클라이언트 설정 완료!${NC}"
echo ""
echo "노드 정보:"
echo "  노드 ID: $NODE_ID"
echo "  VPN IP: $VPN_IP"
echo ""

# 연결 테스트
echo -e "${GREEN}[INFO] 연결 테스트 중...${NC}"
sleep 3

# WireGuard 상태 확인
echo "WireGuard 상태:"
wg show

# Ping 테스트 (VPN 서버)
echo ""
if ping -c 1 -W 2 10.100.0.254 &> /dev/null; then
    echo -e "${GREEN}[SUCCESS] VPN 서버와 연결 성공${NC}"
else
    echo -e "${YELLOW}[WARNING] VPN 서버와 연결 실패. 네트워크 설정을 확인하세요.${NC}"
fi

# 중앙서버인 경우 추가 테스트
if [ "$NODE_TYPE" = "central" ]; then
    echo ""
    echo "중앙서버 VPN IP: 10.100.0.1"
fi

echo ""
echo "다음 명령으로 상태를 확인할 수 있습니다:"
echo "  wg show"
echo "  ip addr show wg0"
echo "  ping 10.100.0.254"
echo ""