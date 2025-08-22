#!/bin/bash
# WireGuard 서버 정리 스크립트
# Docker 컨테이너 내부 또는 호스트에서 실행

echo "========================================="
echo "  WireGuard 서버 정리 도구"
echo "========================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 1. 현재 WireGuard 상태 확인
echo -e "${CYAN}현재 WireGuard 상태 확인 중...${NC}"
if command -v wg &> /dev/null; then
    sudo wg show
    echo ""
fi

# 2. 잘못된 피어 제거
echo -e "${YELLOW}잘못된 피어 설정 정리 중...${NC}"

# Docker 컨테이너 내부인지 확인
if [ -f /.dockerenv ]; then
    echo -e "${CYAN}Docker 환경 감지됨${NC}"
    CONFIG_FILE="/etc/wireguard/wg0.conf"
else
    echo -e "${CYAN}호스트 환경${NC}"
    CONFIG_FILE="/etc/wireguard/wg0.conf"
fi

# 3. 백업 생성
if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${CYAN}설정 파일 백업 중: $BACKUP_FILE${NC}"
    sudo cp "$CONFIG_FILE" "$BACKUP_FILE"
fi

# 4. 중복된 피어 제거 (중복된 central-central, worker-worker 패턴)
echo -e "${YELLOW}중복된 피어 설정 제거 중...${NC}"

# 임시 파일 생성
TEMP_FILE="/tmp/wg0_cleaned.conf"

# Interface 섹션만 추출
sudo awk '/\[Interface\]/,/\[Peer\]/{if(/\[Peer\]/)exit;print}' "$CONFIG_FILE" > "$TEMP_FILE"

# 정상적인 피어만 추가 (central-central, worker-worker 제외)
sudo awk '/\[Peer\]/,/\[Peer\]|$/{
    if(/# central-central-/ || /# worker-worker-/) {
        # 잘못된 피어 발견, 다음 피어까지 스킵
        while(getline && !/\[Peer\]/){}
        if(/\[Peer\]/) print
    } else {
        print
    }
}' "$CONFIG_FILE" >> "$TEMP_FILE"

# 5. 설정 파일 교체
echo -e "${CYAN}정리된 설정 파일 적용 중...${NC}"
sudo mv "$TEMP_FILE" "$CONFIG_FILE"
sudo chmod 600 "$CONFIG_FILE"

# 6. WireGuard 재시작
echo -e "${YELLOW}WireGuard 재시작 중...${NC}"
sudo wg-quick down wg0 2>/dev/null || true
sudo wg-quick up wg0

# 7. 데이터베이스 정리 (Docker 컨테이너 내부에서만)
if [ -f /.dockerenv ]; then
    echo -e "${YELLOW}데이터베이스 정리 중...${NC}"
    python3 << EOF
import sys
sys.path.append('/app')
from database import SessionLocal
from models import Node

db = SessionLocal()

# 잘못된 노드 ID 패턴 삭제
bad_nodes = db.query(Node).filter(
    (Node.node_id.like('central-central-%')) |
    (Node.node_id.like('worker-worker-%'))
).all()

for node in bad_nodes:
    print(f"  - 삭제: {node.node_id}")
    db.delete(node)

db.commit()
db.close()
print("✅ 데이터베이스 정리 완료")
EOF
fi

# 8. 상태 확인
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  ✅ WireGuard 서버 정리 완료!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

echo -e "${CYAN}현재 WireGuard 상태:${NC}"
sudo wg show

echo ""
echo -e "${YELLOW}정리 완료! 이제 새로운 노드를 등록할 수 있습니다.${NC}"