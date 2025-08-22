from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from database import Base

# SQLAlchemy 모델
class Node(Base):
    """노드 정보 DB 모델"""
    __tablename__ = "nodes"
    
    node_id = Column(String, primary_key=True, index=True)
    node_type = Column(String)  # central, worker
    hostname = Column(String)
    public_ip = Column(String)
    vpn_ip = Column(String, unique=True, index=True)
    public_key = Column(String, unique=True)
    private_key = Column(Text)  # 암호화 권장
    config = Column(Text)
    status = Column(String, default="registered")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 워커노드 플랫폼 관련 필드
    description = Column(String)  # 워커노드 설명 (예: "2080-test")
    central_server_ip = Column(String)  # 중앙서버 IP (VPN 네트워크 내)
    docker_env_vars = Column(Text)  # Docker Compose 환경변수 저장

class QRToken(Base):
    """QR 코드 토큰 저장"""
    __tablename__ = "qr_tokens"
    
    token = Column(String, primary_key=True, index=True)
    node_id = Column(String, nullable=False)
    node_type = Column(String, default="worker")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)

# Pydantic 모델
class NodeCreate(BaseModel):
    """노드 생성 요청 모델"""
    node_id: str = Field(..., description="노드 고유 ID")
    node_type: str = Field(..., description="노드 타입 (central/worker)")
    hostname: str = Field(..., description="호스트명")
    public_ip: Optional[str] = Field(None, description="공인 IP (선택)")
    description: Optional[str] = Field(None, description="워커노드 설명")
    central_server_ip: Optional[str] = Field(None, description="중앙서버 IP (VPN 내부)")

    class Config:
        schema_extra = {
            "example": {
                "node_id": "NODE-20250710-865",
                "node_type": "worker",
                "hostname": "worker01.example.com",
                "public_ip": "203.0.113.1",
                "description": "2080-test",
                "central_server_ip": "10.100.0.1"
            }
        }

class NodeResponse(BaseModel):
    """노드 등록 응답 모델"""
    node_id: str
    vpn_ip: str
    config: str  # base64 encoded
    public_key: str
    server_public_key: str
    server_endpoint: str

    class Config:
        schema_extra = {
            "example": {
                "node_id": "worker-node-1",
                "vpn_ip": "10.100.1.1",
                "config": "W0ludGVyZmFjZV0K...",
                "public_key": "abcd1234...",
                "server_public_key": "xyz789...",
                "server_endpoint": "vpn.example.com:51820"
            }
        }

class NodeStatus(BaseModel):
    """노드 상태 정보 모델"""
    node_id: str
    node_type: str
    hostname: str
    public_ip: Optional[str]
    vpn_ip: str
    status: str
    connected: bool
    last_handshake: Optional[datetime]
    bytes_sent: int
    bytes_received: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        schema_extra = {
            "example": {
                "node_id": "worker-node-1",
                "node_type": "worker",
                "hostname": "worker01.example.com",
                "public_ip": "203.0.113.1",
                "vpn_ip": "10.100.1.1",
                "status": "registered",
                "connected": True,
                "last_handshake": "2024-01-01T12:00:00Z",
                "bytes_sent": 1024000,
                "bytes_received": 2048000,
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }