#!/bin/bash
# API 컨테이너 시작 스크립트

echo "API 컨테이너 시작..."

# 라우팅 설정 (API -> WireGuard 네트워크)
if [ -f /app/setup_routes.sh ]; then
    echo "라우팅 설정 중..."
    bash /app/setup_routes.sh
fi

# WireGuard가 준비될 때까지 대기
echo "WireGuard 서버 대기 중..."
sleep 10

# 워커 노드 라우트 복구
if [ -f /app/restore_routes.py ]; then
    echo "워커 노드 라우트 복구 중..."
    python3 /app/restore_routes.py
fi

# FastAPI 서버 시작
echo "FastAPI 서버 시작..."
exec uvicorn main:app --host 0.0.0.0 --port 8090 --reload