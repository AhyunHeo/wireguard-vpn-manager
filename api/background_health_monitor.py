"""
Background Health Monitor Service
Continuously monitors node health and maintains stable connections
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Node
from connection_manager import connection_manager
import signal
import sys

logger = logging.getLogger(__name__)

class HealthMonitorService:
    """
    Background service for continuous health monitoring
    """
    
    def __init__(self):
        self.running = False
        self.check_interval = 30  # seconds
        self.critical_check_interval = 10  # seconds for critical nodes
        self.tasks = []
        
    async def start(self):
        """Start the health monitoring service"""
        if self.running:
            logger.warning("Health monitor service is already running")
            return
        
        self.running = True
        logger.info("Starting health monitor service")
        
        # Start monitoring tasks (worker nodes only)
        self.tasks = [
            asyncio.create_task(self.monitor_worker_nodes()),
            asyncio.create_task(self.cleanup_stale_connections())
        ]
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Health monitor tasks cancelled")
        
    async def stop(self):
        """Stop the health monitoring service"""
        self.running = False
        logger.info("Stopping health monitor service")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Health monitor service stopped")
    
    # Removed: monitor_critical_nodes - central servers don't use VPN anymore
    
    async def monitor_worker_nodes(self):
        """Monitor worker nodes with standard frequency"""
        while self.running:
            try:
                db = SessionLocal()
                try:
                    # Get all worker nodes
                    worker_nodes = db.query(Node).filter(
                        Node.node_type == "worker",
                        Node.status.in_(["registered", "connected", "disconnected"])
                    ).all()
                    
                    # Batch health check
                    for node in worker_nodes:
                        if not self.running:
                            break
                        
                        await connection_manager.health_check_node(node, db)
                    
                    db.commit()
                    
                    # Log summary
                    connected = sum(1 for n in worker_nodes if n.status == "connected")
                    total = len(worker_nodes)
                    logger.info(f"Worker node health check: {connected}/{total} connected")
                    
                finally:
                    db.close()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in worker node monitoring: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections and update states"""
        while self.running:
            try:
                db = SessionLocal()
                try:
                    # Find nodes with stale states
                    stale_time = datetime.now(timezone.utc)
                    stale_nodes = db.query(Node).filter(
                        Node.status == "connecting",
                        Node.updated_at < stale_time
                    ).all()
                    
                    for node in stale_nodes:
                        logger.warning(f"Found stale node {node.node_id} in connecting state")
                        node.status = "error"
                        connection_manager.connection_states[node.node_id] = "error"
                    
                    if stale_nodes:
                        db.commit()
                        logger.info(f"Cleaned up {len(stale_nodes)} stale connections")
                    
                finally:
                    db.close()
                
                # Wait longer for cleanup task
                await asyncio.sleep(self.check_interval * 2)
                
            except Exception as e:
                logger.error(f"Error in stale connection cleanup: {e}")
                await asyncio.sleep(self.check_interval * 2)

# Global service instance
health_monitor = HealthMonitorService()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down health monitor")
    asyncio.create_task(health_monitor.stop())
    sys.exit(0)

async def start_background_monitor():
    """Start the background health monitoring service"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Initializing background health monitor service")
    
    try:
        await health_monitor.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Health monitor service error: {e}")
    finally:
        await health_monitor.stop()

if __name__ == "__main__":
    # Run as standalone service
    asyncio.run(start_background_monitor())