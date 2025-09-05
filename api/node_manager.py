"""
Node management endpoints for viewing and cleaning up nodes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Node
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from connection_manager import connection_manager
import asyncio
import logging

logger = logging.getLogger(__name__)

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

@router.post("/api/nodes/{node_id}/deactivate")
async def deactivate_node(
    node_id: str,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    노드를 안전하게 비활성화 (WireGuard 설정에서 제거하되 DB는 유지)
    Enhanced with connection state management
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node.status == "deactivated":
        return {
            "message": f"Node {node_id} is already deactivated",
            "status": "deactivated"
        }
    
    # Use enhanced connection manager for safe deactivation
    result = await connection_manager.deactivate_node_safely(node, db)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    # Schedule cleanup tasks in background
    background_tasks.add_task(cleanup_node_resources, node_id)
    
    logger.info(f"Node {node_id} deactivated: {result}")
    return result

@router.post("/api/nodes/{node_id}/activate")
async def activate_node(
    node_id: str,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    비활성화된 노드를 재활성화 (WireGuard 설정 복원)
    Enhanced with automatic retry and connection verification
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Check current status
    if node.status not in ["deactivated", "disconnected", "error"]:
        current_state = connection_manager.get_connection_state(node.node_id)
        return {
            "message": f"Node {node_id} is already active",
            "status": node.status,
            "connection_state": current_state
        }
    
    # Use enhanced connection manager with retry logic
    result = await connection_manager.activate_node_with_retry(node, db)
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate node after {result['attempts']} attempts: {result.get('error')}"
        )
    
    # Schedule health check in background
    background_tasks.add_task(monitor_node_health, node_id, db)
    
    logger.info(f"Node {node_id} activated: {result}")
    return result

@router.post("/api/nodes/test-connectivity")
async def test_node_connectivity(
    node_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Test connectivity to nodes with enhanced health checking
    """
    # Use connection manager for comprehensive health checks
    result = await connection_manager.batch_health_check(db, node_type)
    
    logger.info(f"Connectivity test completed: {result['connected']}/{result['total_nodes']} nodes connected")
    
    return result

@router.post("/api/nodes/{node_id}/health-check")
async def health_check_single_node(
    node_id: str,
    db: Session = Depends(get_db)
):
    """
    Perform health check on a single node
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    result = await connection_manager.health_check_node(node, db)
    return result

@router.get("/api/nodes/connection-states")
async def get_connection_states():
    """
    Get current connection states for all tracked nodes
    """
    states = connection_manager.get_all_connection_states()
    return {
        "total": len(states),
        "states": states,
        "summary": {
            "connected": sum(1 for s in states.values() if s == "connected"),
            "disconnected": sum(1 for s in states.values() if s == "disconnected"),
            "deactivated": sum(1 for s in states.values() if s == "deactivated"),
            "error": sum(1 for s in states.values() if s == "error"),
            "reconnecting": sum(1 for s in states.values() if s == "reconnecting")
        }
    }

@router.post("/api/nodes/auto-reconnect")
async def trigger_auto_reconnect(
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Trigger auto-reconnection for all disconnected nodes
    """
    disconnected_nodes = db.query(Node).filter(
        Node.status.in_(["disconnected", "error"])
    ).all()
    
    if not disconnected_nodes:
        return {
            "message": "No disconnected nodes found",
            "reconnected": 0
        }
    
    # Schedule reconnection attempts in background
    for node in disconnected_nodes:
        background_tasks.add_task(
            connection_manager.auto_reconnect_node,
            node,
            db
        )
    
    return {
        "message": f"Scheduled reconnection for {len(disconnected_nodes)} nodes",
        "nodes": [n.node_id for n in disconnected_nodes]
    }

# Background task functions
async def cleanup_node_resources(node_id: str):
    """Clean up resources after node deactivation"""
    await asyncio.sleep(5)  # Wait for deactivation to complete
    logger.info(f"Cleaned up resources for node {node_id}")

async def monitor_node_health(node_id: str, db: Session):
    """Monitor node health after activation"""
    await asyncio.sleep(10)  # Wait for connection to stabilize
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if node:
        result = await connection_manager.health_check_node(node, db)
        logger.info(f"Health check for {node_id}: {result}")