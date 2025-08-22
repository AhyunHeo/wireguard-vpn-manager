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

# 개발 모드에서는 볼륨 마운트를 사용하므로 COPY 생략 가능
# 프로덕션 빌드를 위해서는 유지
COPY . .

# 스크립트 복사 및 실행 권한 부여
COPY setup_routes.sh /app/setup_routes.sh
COPY restore_routes.py /app/restore_routes.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/setup_routes.sh /app/restore_routes.py /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
# CMD는 docker-compose.yml에서 오버라이드됨
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]