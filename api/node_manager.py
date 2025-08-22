"""
Node management endpoints for viewing and cleaning up nodes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Node
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class NodeInfo(BaseModel):
    node_id: str
    node_type: str
    hostname: str
    vpn_ip: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
class NodeDeleteRequest(BaseModel):
    node_ids: List[str]

@router.get("/api/nodes/list")
async def list_nodes(
    node_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all nodes with optional filtering
    """
    query = db.query(Node)
    
    if node_type:
        query = query.filter(Node.node_type == node_type)
    if status:
        query = query.filter(Node.status == status)
    
    nodes = query.order_by(Node.vpn_ip).all()
    
    return {
        "total": len(nodes),
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "hostname": node.hostname,
                "vpn_ip": node.vpn_ip,
                "status": node.status,
                "created_at": node.created_at.isoformat() if node.created_at else None,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None
            }
            for node in nodes
        ]
    }

@router.delete("/api/nodes/cleanup")
async def cleanup_nodes(
    request: NodeDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete specified nodes from the database
    """
    deleted_count = 0
    failed_nodes = []
    
    for node_id in request.node_ids:
        try:
            node = db.query(Node).filter(Node.node_id == node_id).first()
            if node:
                # Remove from WireGuard server if possible
                try:
                    from wireguard_manager import WireGuardManager
                    wg_manager = WireGuardManager()
                    wg_manager.remove_peer_from_server(node.public_key)
                except:
                    pass  # Continue even if WireGuard removal fails
                
                db.delete(node)
                deleted_count += 1
            else:
                failed_nodes.append({"node_id": node_id, "reason": "not found"})
        except Exception as e:
            failed_nodes.append({"node_id": node_id, "reason": str(e)})
    
    db.commit()
    
    return {
        "deleted": deleted_count,
        "failed": failed_nodes
    }

@router.delete("/api/nodes/cleanup-disconnected")
async def cleanup_disconnected_nodes(db: Session = Depends(get_db)):
    """
    Delete all nodes that are not currently connected
    """
    disconnected_nodes = db.query(Node).filter(
        Node.status != "connected"
    ).all()
    
    deleted_count = 0
    for node in disconnected_nodes:
        try:
            # Remove from WireGuard server if possible
            try:
                from wireguard_manager import WireGuardManager
                wg_manager = WireGuardManager()
                wg_manager.remove_peer_from_server(node.public_key)
            except:
                pass
            
            db.delete(node)
            deleted_count += 1
        except:
            continue
    
    db.commit()
    
    return {
        "deleted": deleted_count,
        "message": f"Deleted {deleted_count} disconnected nodes"
    }

@router.get("/api/nodes/{node_id}/status")
async def get_node_status(node_id: str, db: Session = Depends(get_db)):
    """
    Get detailed status of a specific node
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Try to get real-time status from WireGuard
    wg_status = "unknown"
    try:
        from wireguard_manager import WireGuardManager
        wg_manager = WireGuardManager()
        peers = wg_manager.get_peer_status()
        
        for peer in peers:
            if peer.get("public_key") == node.public_key:
                wg_status = "connected" if peer.get("latest_handshake") else "configured"
                break
    except:
        pass
    
    return {
        "node_id": node.node_id,
        "node_type": node.node_type,
        "hostname": node.hostname,
        "vpn_ip": node.vpn_ip,
        "public_ip": node.public_ip,
        "status": node.status,
        "wireguard_status": wg_status,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "config_exists": bool(node.config)
    }

@router.post("/api/nodes/test-connectivity")
async def test_node_connectivity(db: Session = Depends(get_db)):
    """
    Test connectivity to all registered nodes
    """
    import subprocess
    
    nodes = db.query(Node).filter(Node.node_type == "worker").all()
    results = []
    
    for node in nodes:
        try:
            # Ping test
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", node.vpn_ip],
                capture_output=True,
                text=True
            )
            
            is_reachable = result.returncode == 0
            
            results.append({
                "node_id": node.node_id,
                "vpn_ip": node.vpn_ip,
                "reachable": is_reachable,
                "status": "connected" if is_reachable else "unreachable"
            })
            
            # Update node status
            if is_reachable:
                node.status = "connected"
                node.updated_at = datetime.utcnow()
            else:
                node.status = "disconnected"
            
        except Exception as e:
            results.append({
                "node_id": node.node_id,
                "vpn_ip": node.vpn_ip,
                "reachable": False,
                "error": str(e)
            })
    
    db.commit()
    
    return {
        "tested": len(results),
        "connected": sum(1 for r in results if r.get("reachable")),
        "results": results
    }