"""
Enhanced Connection Manager for reliable node activation/deactivation
Provides retry logic, health checks, and automatic reconnection
"""

import asyncio
import logging
import subprocess
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session
from models import Node
from wireguard_manager import WireGuardManager
import json

logger = logging.getLogger(__name__)

class ConnectionState:
    """Connection state tracking for nodes"""
    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEACTIVATED = "deactivated"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class ConnectionManager:
    """
    Manages VPN connections with automatic retry and health monitoring
    """
    
    def __init__(self):
        self.wg_manager = WireGuardManager()
        self.retry_attempts = 3
        self.retry_delay = 5  # seconds
        self.health_check_interval = 30  # seconds
        self.connection_states: Dict[str, str] = {}
        self.last_health_check: Dict[str, datetime] = {}
        
    async def activate_node_with_retry(self, node: Node, db: Session) -> Dict[str, Any]:
        """
        Activate a node with automatic retry on failure
        """
        attempt = 0
        last_error = None
        
        # Update connection state
        self.connection_states[node.node_id] = ConnectionState.CONNECTING
        
        while attempt < self.retry_attempts:
            attempt += 1
            logger.info(f"Activation attempt {attempt}/{self.retry_attempts} for node {node.node_id}")
            
            try:
                # Step 1: Ensure clean state by removing existing peer
                try:
                    self.wg_manager.remove_peer_from_server(node.public_key)
                    await asyncio.sleep(1)  # Brief pause for cleanup
                except Exception as e:
                    logger.debug(f"Cleanup before activation: {e}")
                
                # Step 2: Add peer to WireGuard
                self.wg_manager.add_peer_to_server(
                    public_key=node.public_key,
                    vpn_ip=node.vpn_ip,
                    node_id=node.node_id
                )
                
                # Step 3: Wait for connection establishment
                await asyncio.sleep(2)
                
                # Step 4: Test connectivity
                is_connected = await self.test_node_connectivity(node.vpn_ip)
                
                if is_connected:
                    # Update node status
                    node.status = "registered"
                    node.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Update connection state
                    self.connection_states[node.node_id] = ConnectionState.CONNECTED
                    self.last_health_check[node.node_id] = datetime.now(timezone.utc)
                    
                    logger.info(f"Successfully activated node {node.node_id} on attempt {attempt}")
                    
                    return {
                        "success": True,
                        "node_id": node.node_id,
                        "status": "registered",
                        "attempts": attempt,
                        "message": f"Node {node.node_id} activated successfully"
                    }
                else:
                    raise Exception("Connectivity test failed after adding peer")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Activation attempt {attempt} failed for {node.node_id}: {e}")
                
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay)
                    self.retry_delay *= 1.5  # Exponential backoff
        
        # All attempts failed
        self.connection_states[node.node_id] = ConnectionState.ERROR
        node.status = "error"
        db.commit()
        
        return {
            "success": False,
            "node_id": node.node_id,
            "status": "error",
            "attempts": attempt,
            "error": last_error,
            "message": f"Failed to activate node {node.node_id} after {attempt} attempts"
        }
    
    async def deactivate_node_safely(self, node: Node, db: Session) -> Dict[str, Any]:
        """
        Safely deactivate a node with proper cleanup
        """
        try:
            # Update connection state
            self.connection_states[node.node_id] = ConnectionState.DEACTIVATED
            
            # Step 1: Remove from WireGuard
            try:
                self.wg_manager.remove_peer_from_server(node.public_key)
                logger.info(f"Removed peer {node.public_key} from WireGuard")
            except Exception as e:
                logger.warning(f"Failed to remove peer from WireGuard: {e}")
            
            # Step 2: Update database status
            node.status = "deactivated"
            node.updated_at = datetime.now(timezone.utc)
            
            # Store deactivation metadata
            metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
            metadata['deactivated_at'] = datetime.now(timezone.utc).isoformat()
            metadata['last_vpn_ip'] = node.vpn_ip
            node.docker_env_vars = json.dumps(metadata)
            
            db.commit()
            
            # Clean up tracking
            if node.node_id in self.last_health_check:
                del self.last_health_check[node.node_id]
            
            logger.info(f"Successfully deactivated node {node.node_id}")
            
            return {
                "success": True,
                "node_id": node.node_id,
                "status": "deactivated",
                "message": f"Node {node.node_id} deactivated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deactivate node {node.node_id}: {e}")
            db.rollback()
            
            return {
                "success": False,
                "node_id": node.node_id,
                "error": str(e),
                "message": f"Failed to deactivate node {node.node_id}"
            }
    
    async def test_node_connectivity(self, vpn_ip: str, timeout: int = 2) -> bool:
        """
        Test if a node is reachable via ping
        """
        try:
            # Docker 환경에서는 WireGuard 컨테이너를 통해 ping
            if os.path.exists("/var/run/docker.sock"):
                process = await asyncio.create_subprocess_exec(
                    'docker', 'exec', 'wireguard-server',
                    'ping', '-c', '1', '-W', str(timeout), vpn_ip,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # 로컬 환경에서는 직접 ping
                process = await asyncio.create_subprocess_exec(
                    'ping', '-c', '1', '-W', str(timeout), vpn_ip,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Connectivity test failed for {vpn_ip}: {e}")
            return False
    
    async def health_check_node(self, node: Node, db: Session) -> Dict[str, Any]:
        """
        Perform health check on a single node
        """
        # Skip if recently checked
        if node.node_id in self.last_health_check:
            last_check = self.last_health_check[node.node_id]
            if (datetime.now(timezone.utc) - last_check).seconds < self.health_check_interval:
                return {
                    "node_id": node.node_id,
                    "status": "skipped",
                    "message": "Recently checked"
                }
        
        # Test connectivity
        is_reachable = await self.test_node_connectivity(node.vpn_ip)
        
        # Update tracking
        self.last_health_check[node.node_id] = datetime.now(timezone.utc)
        
        # Update node status based on result
        old_status = node.status
        if is_reachable:
            if node.status == "registered" or node.status == "connected":
                node.status = "connected"
                self.connection_states[node.node_id] = ConnectionState.CONNECTED
        else:
            if node.status == "connected":
                node.status = "disconnected"
                self.connection_states[node.node_id] = ConnectionState.DISCONNECTED
                
                # Auto-reconnection disabled for worker nodes
                # Workers should reconnect manually or via their own health checks
        
        node.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "node_id": node.node_id,
            "vpn_ip": node.vpn_ip,
            "reachable": is_reachable,
            "old_status": old_status,
            "new_status": node.status,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def auto_reconnect_node(self, node: Node, db: Session) -> bool:
        """
        Attempt to automatically reconnect a disconnected node
        """
        if node.status == "deactivated":
            return False
        
        logger.info(f"Attempting auto-reconnection for node {node.node_id}")
        self.connection_states[node.node_id] = ConnectionState.RECONNECTING
        
        # Use activation logic with retry
        result = await self.activate_node_with_retry(node, db)
        
        if result["success"]:
            logger.info(f"Successfully auto-reconnected node {node.node_id}")
            return True
        else:
            logger.error(f"Failed to auto-reconnect node {node.node_id}")
            return False
    
    async def batch_health_check(self, db: Session, node_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform health checks on multiple nodes
        """
        query = db.query(Node).filter(Node.status != "deactivated")
        if node_type:
            query = query.filter(Node.node_type == node_type)
        
        nodes = query.all()
        results = []
        
        # Run health checks concurrently
        tasks = [self.health_check_node(node, db) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_checks = [r for r in results if isinstance(r, dict) and not isinstance(r, Exception)]
        failed_checks = [r for r in results if isinstance(r, Exception)]
        
        connected_count = sum(1 for r in successful_checks if r.get("reachable", False))
        disconnected_count = sum(1 for r in successful_checks if not r.get("reachable", False))
        
        return {
            "total_nodes": len(nodes),
            "checks_performed": len(successful_checks),
            "connected": connected_count,
            "disconnected": disconnected_count,
            "failed_checks": len(failed_checks),
            "results": successful_checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_connection_state(self, node_id: str) -> str:
        """
        Get current connection state for a node
        """
        return self.connection_states.get(node_id, ConnectionState.DISCONNECTED)
    
    def get_all_connection_states(self) -> Dict[str, str]:
        """
        Get all current connection states
        """
        return self.connection_states.copy()

# Global instance
connection_manager = ConnectionManager()