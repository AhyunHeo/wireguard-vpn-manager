#!/usr/bin/env python3
"""
워커 노드 라우트 복구 스크립트
컨테이너 재시작 시 실행하여 10.100.1.x 대역의 라우트를 복구합니다.
"""

import subprocess
import os
import logging
import psycopg2
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_worker_nodes() -> List[str]:
    """데이터베이스에서 워커 노드 IP 목록 조회"""
    worker_ips = []
    try:
        # 데이터베이스 연결
        db_url = os.getenv("DATABASE_URL", "postgresql://vpn:vpnpass@postgres:5432/vpndb")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # 10.100.1.x 대역의 노드 조회
        cur.execute("""
            SELECT vpn_ip FROM nodes 
            WHERE vpn_ip LIKE '10.100.1.%' 
            AND status = 'active'
        """)
        
        for row in cur.fetchall():
            worker_ips.append(row[0])
        
        cur.close()
        conn.close()
        
        logger.info(f"발견된 워커 노드: {worker_ips}")
        return worker_ips
        
    except Exception as e:
        logger.error(f"데이터베이스 조회 실패: {e}")
        return []

def add_route(vpn_ip: str, interface: str = "wg0"):
    """WireGuard 인터페이스에 라우트 추가"""
    try:
        # Docker 환경인지 확인
        if os.path.exists("/var/run/docker.sock"):
            cmd = [
                "docker", "exec", "wireguard-server",
                "ip", "route", "add", f"{vpn_ip}/32", "dev", interface
            ]
        else:
            cmd = ["ip", "route", "add", f"{vpn_ip}/32", "dev", interface]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"라우트 추가 성공: {vpn_ip}")
        elif "File exists" in result.stderr:
            logger.info(f"라우트 이미 존재: {vpn_ip}")
        else:
            logger.warning(f"라우트 추가 실패 ({vpn_ip}): {result.stderr}")
            
    except Exception as e:
        logger.error(f"라우트 추가 중 오류 ({vpn_ip}): {e}")

def check_wireguard_interface():
    """WireGuard 인터페이스 상태 확인"""
    try:
        if os.path.exists("/var/run/docker.sock"):
            cmd = ["docker", "exec", "wireguard-server", "ip", "link", "show", "wg0"]
        else:
            cmd = ["ip", "link", "show", "wg0"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("WireGuard 인터페이스 활성화 확인")
            return True
        else:
            logger.error("WireGuard 인터페이스를 찾을 수 없습니다")
            return False
            
    except Exception as e:
        logger.error(f"인터페이스 확인 중 오류: {e}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("워커 노드 라우트 복구 시작...")
    
    # WireGuard 인터페이스 확인
    if not check_wireguard_interface():
        logger.error("WireGuard가 실행 중이 아닙니다. 종료합니다.")
        return
    
    # 워커 노드 목록 조회
    worker_ips = get_worker_nodes()
    
    if not worker_ips:
        logger.info("등록된 워커 노드가 없습니다.")
        return
    
    # 각 워커 노드에 대해 라우트 추가
    for ip in worker_ips:
        add_route(ip)
    
    logger.info(f"라우트 복구 완료: {len(worker_ips)}개 노드")

if __name__ == "__main__":
    main()