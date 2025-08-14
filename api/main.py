from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional
import os
import base64
import time
import tempfile
from pathlib import Path
from datetime import datetime

from database import SessionLocal, engine, Base
from models import Node, NodeCreate, NodeResponse, NodeStatus
from wireguard_manager import WireGuardManager

# DB 연결 재시도 함수
def wait_for_db(max_retries=30):
    """데이터베이스 연결이 준비될 때까지 대기"""
    for i in range(max_retries):
        try:
            # 연결 테스트
            conn = engine.connect()
            conn.close()
            print("Database connected successfully!")
            return True
        except OperationalError:
            print(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(2)
    raise Exception("Could not connect to database after 30 attempts")

# DB 연결 대기
wait_for_db()

# 데이터베이스 초기화
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WireGuard VPN Manager API",
    description="자체 호스팅 WireGuard VPN 관리 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
wg_manager = WireGuardManager()

# API 토큰 (환경변수에서 가져오기)
API_TOKEN = os.getenv("API_TOKEN", "test-token-123")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API 토큰 검증"""
    if credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return credentials.credentials

@app.get("/")
async def root():
    """API 루트"""
    return {
        "service": "WireGuard VPN Manager",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "healthy", "service": "vpn-manager"}

@app.post("/nodes/register", response_model=NodeResponse)
async def register_node(
    node: NodeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드 등록 및 WireGuard 설정 생성"""
    
    # 기존 노드 확인
    existing = db.query(Node).filter(Node.node_id == node.node_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="노드가 이미 등록되어 있습니다")
    
    # VPN IP 할당
    if node.node_type == "central":
        vpn_ip = "10.100.0.1"
    else:
        # 워커노드용 IP 할당
        import ipaddress
        last_worker = db.query(Node).filter(
            Node.node_type == "worker"
        ).order_by(Node.vpn_ip.desc()).first()
        
        if last_worker:
            last_ip = ipaddress.ip_address(last_worker.vpn_ip)
            next_ip = last_ip + 1
            if next_ip > ipaddress.ip_address("10.100.1.253"):
                raise HTTPException(status_code=400, detail="워커노드 IP 풀이 가득 찼습니다")
            vpn_ip = str(next_ip)
        else:
            vpn_ip = "10.100.1.1"
    
    # WireGuard 키 생성
    keys = wg_manager.generate_keypair()
    
    # 피어 설정 생성
    config = wg_manager.create_peer_config(
        node_id=node.node_id,
        vpn_ip=vpn_ip,
        private_key=keys['private_key'],
        public_key=keys['public_key']
    )
    
    # DB 저장
    db_node = Node(
        node_id=node.node_id,
        node_type=node.node_type,
        hostname=node.hostname,
        public_ip=node.public_ip,
        vpn_ip=vpn_ip,
        public_key=keys['public_key'],
        private_key=keys['private_key'],
        config=config,
        status="registered"
    )
    
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    
    # WireGuard 서버에 피어 추가
    try:
        wg_manager.add_peer_to_server(
            public_key=keys['public_key'],
            vpn_ip=vpn_ip,
            node_id=node.node_id
        )
    except Exception as e:
        # 실패 시 DB에서 제거
        db.delete(db_node)
        db.commit()
        raise HTTPException(status_code=500, detail=f"WireGuard 피어 추가 실패: {str(e)}")
    
    return NodeResponse(
        node_id=db_node.node_id,
        vpn_ip=db_node.vpn_ip,
        config=base64.b64encode(config.encode()).decode(),
        public_key=db_node.public_key,
        server_public_key=wg_manager.get_server_public_key(),
        server_endpoint=f"{os.getenv('SERVERURL', 'localhost')}:51820"
    )

@app.delete("/nodes/{node_id}")
async def unregister_node(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드 등록 해제"""
    
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="노드를 찾을 수 없습니다")
    
    # WireGuard 서버에서 피어 제거
    try:
        wg_manager.remove_peer_from_server(node.public_key)
    except Exception as e:
        print(f"[WARNING] 피어 제거 실패: {e}")
    
    # DB에서 제거
    db.delete(node)
    db.commit()
    
    return {"message": f"노드 {node_id}가 성공적으로 제거되었습니다"}

@app.get("/nodes", response_model=List[NodeStatus])
async def list_nodes(
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """등록된 모든 노드 목록 조회"""
    
    nodes = db.query(Node).all()
    node_statuses = []
    
    for node in nodes:
        # WireGuard 피어 상태 조회
        peer_status = wg_manager.get_peer_status(node.public_key)
        
        node_statuses.append(NodeStatus(
            node_id=node.node_id,
            node_type=node.node_type,
            hostname=node.hostname,
            public_ip=node.public_ip,
            vpn_ip=node.vpn_ip,
            status=node.status,
            connected=peer_status.get('connected', False),
            last_handshake=peer_status.get('last_handshake'),
            bytes_sent=peer_status.get('bytes_sent', 0),
            bytes_received=peer_status.get('bytes_received', 0),
            created_at=node.created_at,
            updated_at=node.updated_at
        ))
    
    return node_statuses

@app.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """특정 노드 정보 조회"""
    
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="노드를 찾을 수 없습니다")
    
    peer_status = wg_manager.get_peer_status(node.public_key)
    
    return NodeStatus(
        node_id=node.node_id,
        node_type=node.node_type,
        hostname=node.hostname,
        public_ip=node.public_ip,
        vpn_ip=node.vpn_ip,
        status=node.status,
        connected=peer_status.get('connected', False),
        last_handshake=peer_status.get('last_handshake'),
        bytes_sent=peer_status.get('bytes_sent', 0),
        bytes_received=peer_status.get('bytes_received', 0),
        created_at=node.created_at,
        updated_at=node.updated_at
    )

@app.get("/nodes/{node_id}/config")
async def get_node_config(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드의 WireGuard 설정 파일 조회"""
    
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="노드를 찾을 수 없습니다")
    
    return {
        "node_id": node.node_id,
        "config": base64.b64encode(node.config.encode()).decode(),
        "vpn_ip": node.vpn_ip,
        "server_endpoint": f"{os.getenv('SERVERURL', 'localhost')}:51820"
    }

@app.post("/nodes/{node_id}/regenerate-keys")
async def regenerate_node_keys(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드의 WireGuard 키 재생성"""
    
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="노드를 찾을 수 없습니다")
    
    # 기존 피어 제거
    try:
        wg_manager.remove_peer_from_server(node.public_key)
    except Exception as e:
        print(f"[WARNING] 기존 피어 제거 실패: {e}")
    
    # 새 키 생성
    keys = wg_manager.generate_keypair()
    config = wg_manager.create_peer_config(
        node_id=node.node_id,
        vpn_ip=node.vpn_ip,
        private_key=keys['private_key'],
        public_key=keys['public_key']
    )
    
    # DB 업데이트
    node.public_key = keys['public_key']
    node.private_key = keys['private_key']
    node.config = config
    node.updated_at = datetime.utcnow()
    
    db.commit()
    
    # 새 피어 추가
    try:
        wg_manager.add_peer_to_server(
            public_key=keys['public_key'],
            vpn_ip=node.vpn_ip,
            node_id=node.node_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"새 피어 추가 실패: {str(e)}")
    
    return {
        "message": "키가 성공적으로 재생성되었습니다",
        "config": base64.b64encode(config.encode()).decode(),
        "public_key": keys['public_key']
    }

@app.get("/status/wireguard")
async def get_wireguard_status(token: str = Depends(verify_token)):
    """WireGuard 서버 상태 조회"""
    
    try:
        status = wg_manager.get_server_status()
        return status
    except Exception as e:
        return {
            "error": str(e),
            "interface": {},
            "peers": [],
            "peer_count": 0
        }

# API 엔드포인트 추가
@app.post("/api/generate-config/{token}")
async def generate_config_for_token(
    token: str,
    db: Session = Depends(get_db)
):
    """토큰 기반 VPN 설정 생성"""
    # 간단한 구현 - 실제로는 토큰 검증 필요
    node_id = f"auto-node-{token[:8]}"
    
    # 기존 노드 확인
    existing_node = db.query(Node).filter(Node.node_id == node_id).first()
    if existing_node:
        return {
            "config": base64.b64encode(existing_node.config.encode()).decode(),
            "node_id": existing_node.node_id,
            "vpn_ip": existing_node.vpn_ip
        }
    
    # 새 노드 생성
    node_data = NodeCreate(
        node_id=node_id,
        node_type="worker",
        hostname=f"auto-{token[:8]}",
        public_ip="0.0.0.0"  # 자동 감지
    )
    
    # IP 할당
    vpn_ip = wg_manager.allocate_ip(node_data.node_type)
    if not vpn_ip:
        raise HTTPException(status_code=500, detail="VPN IP 할당 실패")
    
    # 키 생성
    keys = wg_manager.generate_keypair()
    
    # 설정 파일 생성
    config = wg_manager.generate_client_config(
        private_key=keys['private_key'],
        client_ip=vpn_ip,
        server_public_key=wg_manager.get_server_public_key()
    )
    
    # DB 저장
    db_node = Node(
        node_id=node_id,
        node_type="worker",
        hostname=f"auto-{token[:8]}",
        public_ip="0.0.0.0",
        vpn_ip=vpn_ip,
        public_key=keys['public_key'],
        private_key=keys['private_key'],
        config=config,
        status="registered",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_node)
    db.commit()
    
    # WireGuard 피어 추가
    try:
        wg_manager.add_peer_to_server(
            public_key=keys['public_key'],
            vpn_ip=vpn_ip,
            node_id=node_id
        )
    except Exception as e:
        db.delete(db_node)
        db.commit()
        raise HTTPException(status_code=500, detail=f"피어 추가 실패: {str(e)}")
    
    return {
        "config": base64.b64encode(config.encode()).decode(),
        "node_id": node_id,
        "vpn_ip": vpn_ip
    }

@app.get("/api/download/wireguard-windows/{token}")
async def download_wireguard_windows(token: str):
    """Windows용 WireGuard 설치 파일 다운로드"""
    # 실제로는 WireGuard 설치 파일을 제공해야 함
    # 여기서는 설치 안내 HTML을 반환
    html_content = f"""
    <html>
    <head><title>WireGuard 설치</title></head>
    <body>
        <h1>WireGuard Windows 설치</h1>
        <p>다음 링크에서 WireGuard를 다운로드하세요:</p>
        <a href="https://download.wireguard.com/windows-client/wireguard-installer.exe">
            WireGuard Windows 다운로드
        </a>
        <p>토큰: {token}</p>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")

@app.get("/api/download/wireguard-linux/{token}")
async def download_wireguard_linux(token: str):
    """Linux용 WireGuard 설치 스크립트"""
    script_content = f"""#!/bin/bash
# WireGuard Linux 자동 설치 스크립트
# 토큰: {token}

echo "WireGuard 설치 시작..."

# 패키지 매니저 확인 및 설치
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y wireguard
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y wireguard-tools
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm wireguard-tools
else
    echo "지원되지 않는 리눅스 배포판입니다."
    exit 1
fi

echo "WireGuard 설치 완료!"
echo "이제 설정 파일을 다운로드하세요."
"""
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=install-wireguard-{token}.sh"
        }
    )

# 웹 기반 설치 라우터 추가
from web_installer import router as web_installer_router
from qr_generator import router as qr_generator_router
from auto_installer import router as auto_installer_router

app.include_router(web_installer_router, tags=["Web Installer"])
app.include_router(qr_generator_router, tags=["QR Generator"])
app.include_router(auto_installer_router, tags=["Auto Installer"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)