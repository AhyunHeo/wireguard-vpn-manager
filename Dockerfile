FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wireguard-tools \
    iproute2 \
    iptables \
    qrencode \
    curl \
    docker.io \
    iputils-ping \
    net-tools \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API 소스 코드 복사
COPY api /app

# 스크립트 복사 및 실행 권한 부여
COPY scripts/setup_routes.sh /app/setup_routes.sh
COPY scripts/restore_routes.py /app/restore_routes.py
RUN chmod +x /app/setup_routes.sh /app/restore_routes.py

# ENTRYPOINT는 docker-compose.yml에서 설정
# CMD는 docker-compose.yml에서 오버라이드됨
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]