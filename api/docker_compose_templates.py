"""
Docker Compose Templates for Central and Worker Nodes
"""

def get_worker_docker_compose_host(worker_id: str) -> str:
    """워커노드용 docker-compose.yml 템플릿 반환 (Host 네트워크 모드 - Linux 전용)"""
    DOCKER_TAG = "latest"
    
    return f"""version: '3.8'

services:
  server:
    # 빌드된 이미지 사용 (레지스트리에서 pull)
    image: ${{REGISTRY:-docker.io}}/${{IMAGE_NAME:-heoaa/worker-node-prod}}:${{TAG:-{DOCKER_TAG}}}
    container_name: node-server
    network_mode: host
    environment:
      - NODE_ID=${{NODE_ID}}
      - DESCRIPTION=${{DESCRIPTION}}
      - CENTRAL_SERVER_IP=${{CENTRAL_SERVER_IP}}
      - CENTRAL_SERVER_URL=${{CENTRAL_SERVER_URL}}
      - VPN_IP=${{VPN_IP:-}}
      - HOST_IP=${{VPN_IP:-${{HOST_IP:-}}}}
      - API_TOKEN=${{API_TOKEN}}
      - VPN_CONFIG_BASE64=${{VPN_CONFIG_BASE64:-}}
      - DOCKER_CONTAINER=true
      - NCCL_DEBUG=INFO
      - TORCH_DISTRIBUTED_DEBUG=DETAIL
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
      - NCCL_SOCKET_FAMILY=AF_INET
      - NCCL_ASYNC_ERROR_HANDLING=1
      - NCCL_TIMEOUT=600
      - NCCL_IB_DISABLE=1
      - NCCL_P2P_DISABLE=1
      - OMP_NUM_THREADS=1
      - MKL_NUM_THREADS=1
      - RAY_DISABLE_DASHBOARD=1
      # Ray가 VPN IP 사용하도록 명시
      - RAY_NODE_IP_ADDRESS=${{VPN_IP}}
      - RAY_RAYLET_NODE_IP_ADDRESS=${{VPN_IP}}
      # Ray 네트워크 설정 (host 모드에서 중요)
      - RAY_USE_TLS=0
      - RAY_DISABLE_DOCKER_CPU_WARNING=1
      - RAY_IGNORE_DOCKER_INTERNAL_IP=1
      # IPv6 비활성화 (VPN은 IPv4만 사용)
      - RAY_DISABLE_IPV6=1
      - GRPC_IPV6=0
      - GRPC_ENABLE_IPV6=0
    volumes:
      # 캐시와 임시 파일만 마운트 (소스코드 마운트 없음)
      - ~/.cache/torch:/root/.cache/torch
      - ~/.cache/huggingface:/root/.cache/huggingface
      - /tmp/ray:/tmp/ray
      - /var/run/docker.sock:/var/run/docker.sock
    runtime: nvidia
    shm_size: '14gb'
    cap_add:
      - NET_ADMIN      # WireGuard 인터페이스 생성에 필요
      - SYS_MODULE     # WireGuard 커널 모듈 로드에 필요  
    privileged: true    # WireGuard가 컨테이너 내부에서 작동하려면 필요
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
              count: all
        limits:
          memory: ${{MEMORY_LIMIT:-24g}}
    ulimits:
      memlock:
        soft: -1
        hard: -1
      stack:
        soft: 67108864
        hard: 67108864
    restart: unless-stopped
"""


def get_worker_docker_compose(worker_id: str) -> str:
    """워커노드용 docker-compose.yml 템플릿 반환"""
    # Docker 이미지 태그 설정 (한 곳에서 관리)
    DOCKER_TAG = "latest"  # v1.2, v1.3 등으로 변경 가능
    
    return f"""version: '3.8'

services:
  server:
    # 빌드된 이미지 사용 (레지스트리에서 pull)
    image: ${{REGISTRY:-docker.io}}/${{IMAGE_NAME:-heoaa/worker-node-prod}}:${{TAG:-{DOCKER_TAG}}}
    container_name: node-server
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - NODE_ID=${{NODE_ID}}
      - DESCRIPTION=${{DESCRIPTION}}
      - CENTRAL_SERVER_IP=${{CENTRAL_SERVER_IP}}
      - CENTRAL_SERVER_URL=${{CENTRAL_SERVER_URL}}
      - VPN_IP=${{VPN_IP:-}}
      - HOST_IP=${{VPN_IP:-${{HOST_IP:-}}}}
      - API_TOKEN=${{API_TOKEN}}
      - VPN_CONFIG_BASE64=${{VPN_CONFIG_BASE64:-}}
      - DOCKER_CONTAINER=true
      - NCCL_DEBUG=INFO
      - NCCL_DEBUG_SUBSYS=ALL
      - TORCH_DISTRIBUTED_DEBUG=DETAIL
      - PYTHONUNBUFFERED=1
      - PYTHONPATH=/app
      - PYTHONDONTWRITEBYTECODE=1
      - NCCL_SOCKET_FAMILY=AF_INET
      - NCCL_ASYNC_ERROR_HANDLING=1
      - NCCL_TIMEOUT=600
      - NCCL_RETRY_COUNT=10
      - NCCL_TREE_THRESHOLD=0
      - NCCL_BUFFSIZE=8388608
      - NCCL_IB_DISABLE=1
      - NCCL_P2P_DISABLE=1
      - NCCL_NSOCKS_PERTHREAD=4
      - NCCL_SOCKET_NTHREADS=1
      - NCCL_MAX_NCHANNELS=16
      - NCCL_MIN_NCHANNELS=4
      - NCCL_NET_GDR_LEVEL=0
      - NCCL_CHECKS_DISABLE=0
      - OMP_NUM_THREADS=1
      - MKL_NUM_THREADS=1
      - RAY_DISABLE_DASHBOARD=1
      # Ray가 VPN IP 사용하도록 명시
      - RAY_NODE_IP_ADDRESS=${{VPN_IP}}
      - RAY_RAYLET_NODE_IP_ADDRESS=${{VPN_IP}}
      # Ray 네트워크 설정
      - RAY_USE_TLS=0
      - RAY_DISABLE_DOCKER_CPU_WARNING=1
      - RAY_IGNORE_DOCKER_INTERNAL_IP=1
      # IPv6 비활성화 (VPN은 IPv4만 사용)
      - RAY_DISABLE_IPV6=1
      - GRPC_IPV6=0
      - GRPC_ENABLE_IPV6=0
    volumes:
      # 캐시와 임시 파일만 마운트 (소스코드 마운트 없음)
      - ~/.cache/torch:/root/.cache/torch
      - ~/.cache/huggingface:/root/.cache/huggingface
      - /tmp/ray:/tmp/ray
      - /var/run/docker.sock:/var/run/docker.sock
    runtime: nvidia
    shm_size: '14gb'
    cap_add:
      - NET_ADMIN      # WireGuard 인터페이스 생성에 필요
      - SYS_MODULE     # WireGuard 커널 모듈 로드에 필요  
    privileged: true    # WireGuard가 컨테이너 내부에서 작동하려면 필요
    sysctls:
      net.ipv6.conf.all.disable_ipv6: "1"
      net.ipv6.conf.default.disable_ipv6: "1"
      net.ipv6.conf.lo.disable_ipv6: "1"
    ports:
      - "8001:8001"    # Flask API 서버
      - "6379:6379"    # Redis / GCS
      - "10001:10001"  # Ray Client Server
      - "8265:8265"    # Ray Dashboard
      - "8076:8076"    # ObjectManager
      - "8077:8077"    # NodeManager
      - "8090:8090"    # Metrics Export
      - "29500-29509:29500-29509"  # DDP TCPStore
      - "29510:29510"  # nccl_socket
      - "11000-11049:11000-11049"  # Ray Worker
      - "30000-30049:30000-30049"  # Ephemeral
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
              count: all
        limits:
          memory: ${{MEMORY_LIMIT:-24g}}
    ulimits:
      memlock:
        soft: -1
        hard: -1
      stack:
        soft: 67108864
        hard: 67108864
    restart: unless-stopped
"""

def get_central_docker_compose() -> str:
    """중앙서버용 docker-compose.yml 템플릿 반환 (하이브리드 모드)"""
    return """# 하이브리드 모드: 중앙서버는 외부 접근 가능, 워커노드는 VPN 통신
# 사용법: HOST_IP=192.168.0.88 docker-compose up -d

services:
  api:
    image: heoaa/central-server:v1.0
    container_name: central-server-api
    ports:
      # 모든 인터페이스에서 접근 가능 (관리자 외부 접속용)
      - "0.0.0.0:8000:8000"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
      - ./app/data/uploads:/app/data/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-2Yw1k3J8v3Qk1n2p5l6s7d3f9g0h1j2k3l4m5n6o7p3q9r0s1t2u3v4w5x6y7z3A9}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      # 워커노드 접속용 VPN IP 설정
      # 10.100.0.0/16 = 10.100.0.0 ~ 10.100.255.255 (10.100.1.x 포함)
      - WORKER_VPN_NETWORK=10.100.0.0/16
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network

  fl-api:
    image: heoaa/central-server-fl:v1.0
    container_name: fl-server-api
    ports:
      # 모든 인터페이스에서 접근 가능
      - "0.0.0.0:5002:5002"
    volumes:
      - ./config:/app/config:ro
      - ./session_models:/app/session_models
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-2Yw1k3J8v3Qk1n2p5l6s7d3f9g0h1j2k3l4m5n6o7p3q9r0s1t2u3v4w5x6y7z3A9}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      - FL_SERVER_PORT=5002
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped
    networks:
      - app-network

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile.dev
    container_name: central-server-frontend
    ports:
      # 모든 인터페이스에서 접근 가능
      - "0.0.0.0:3000:3000"
    environment:
      # 브라우저에서 접근할 실제 IP 사용
      # HOST_IP 환경변수로 설정 (예: HOST_IP=192.168.0.88)
      - NEXT_PUBLIC_API_URL=http://${HOST_IP:-localhost}:8000
      - NEXT_PUBLIC_WS_URL=ws://${HOST_IP:-localhost}:8000
      - NEXT_PUBLIC_FL_API_URL=http://${HOST_IP:-localhost}:5002
      - NEXT_PUBLIC_FL_WS_URL=ws://${HOST_IP:-localhost}:5002
      - NEXT_PUBLIC_ENV=hybrid
    volumes:
      - ../frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - api
      - fl-api
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15
    container_name: central-server-db
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
      TZ: Asia/Seoul
      PGTZ: Asia/Seoul
    ports:
      # 로컬만 접근 (보안)
      - "127.0.0.1:5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - app-network

  mongo:
    image: mongo:latest
    container_name: central-server-mongo
    environment:
      TZ: Asia/Seoul
    ports:
      # 로컬만 접근 (보안)
      - "127.0.0.1:27017:27017"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:latest
    container_name: central-server-redis
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  db_data:
  mongo_data:
"""