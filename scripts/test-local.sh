#!/bin/bash

# 로컬 테스트 스크립트

set -e

echo "======================================"
echo "WireGuard VPN Manager 로컬 테스트"
echo "======================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 로컬 환경변수 설정
export SERVERURL=localhost
export API_TOKEN=test-token-123

echo -e "${GREEN}[INFO] 로컬 테스트 환경 설정${NC}"
echo "  API URL: http://localhost:8090"
echo "  API Token: test-token-123"
echo ""

# 설정 디렉토리 생성
mkdir -p config

# 기존 컨테이너 정리
echo -e "${GREEN}[INFO] 기존 컨테이너 정리 중...${NC}"
docker-compose -f docker-compose.local.yml down 2>/dev/null || true

# Docker 이미지 빌드
echo -e "${GREEN}[INFO] Docker 이미지 빌드 중...${NC}"
docker-compose -f docker-compose.local.yml build

# 컨테이너 시작
echo -e "${GREEN}[INFO] 컨테이너 시작 중...${NC}"
docker-compose -f docker-compose.local.yml up -d

# 서비스 시작 대기
echo -e "${GREEN}[INFO] 서비스 시작 대기 중...${NC}"
sleep 15

# API 헬스체크
echo -e "${GREEN}[INFO] API 서버 상태 확인 중...${NC}"
if curl -s -f http://localhost:8090/health > /dev/null; then
    echo -e "${GREEN}[SUCCESS] API 서버가 정상적으로 실행 중입니다.${NC}"
else
    echo -e "${RED}[ERROR] API 서버 시작 실패${NC}"
    docker-compose -f docker-compose.local.yml logs vpn-api
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}로컬 테스트 환경 준비 완료!${NC}"
echo "======================================"
echo ""
echo "API 문서: http://localhost:8090/docs"
echo "WireGuard UI: http://localhost:5000 (admin/admin123)"
echo ""
echo "테스트 노드 등록:"
echo '  curl -X POST http://localhost:8090/nodes/register \'
echo '    -H "Authorization: Bearer test-token-123" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d "{"node_id":"test-node-1","node_type":"worker","hostname":"test-host"}"'
echo ""
echo "노드 목록 조회:"
echo '  curl -H "Authorization: Bearer test-token-123" \'
echo '    http://localhost:8090/nodes'
echo ""
echo "로그 확인:"
echo "  docker-compose -f docker-compose.local.yml logs -f"
echo ""
echo "종료:"
echo "  docker-compose -f docker-compose.local.yml down"
echo ""