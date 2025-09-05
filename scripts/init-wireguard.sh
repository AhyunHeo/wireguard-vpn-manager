#!/bin/bash

# WireGuard 초기 설정 스크립트
# Docker 컨테이너 내부에서 WireGuard 인터페이스를 초기화합니다.

set -e

echo "WireGuard 초기 설정 시작..."

# WireGuard 컨테이너가 준비될 때까지 대기
echo "WireGuard 컨테이너 대기 중..."
for i in {1..30}; do
    if docker exec wireguard-server wg show wg0 &>/dev/null; then
        echo "WireGuard 인터페이스가 준비되었습니다."
        break
    fi
    echo "대기 중... ($i/30)"
    sleep 2
done

# 서버 공개키 확인
echo "서버 공개키 확인 중..."
SERVER_PUBKEY=$(docker exec wireguard-server wg show wg0 public-key 2>/dev/null || echo "")

if [ -z "$SERVER_PUBKEY" ]; then
    echo "경고: 서버 공개키를 찾을 수 없습니다."
    echo "WireGuard 설정을 확인해주세요."
else
    echo "서버 공개키: $SERVER_PUBKEY"
    
    # 공개키를 파일로 저장
    mkdir -p config/server
    echo "$SERVER_PUBKEY" > config/server/publickey
    echo "공개키가 config/server/publickey에 저장되었습니다."
fi

echo "WireGuard 초기 설정 완료!"