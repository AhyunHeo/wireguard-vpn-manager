#!/usr/bin/env python3

"""
WireGuard VPN 상태 모니터링 도구
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import time

class VPNMonitor:
    """VPN 모니터링 클래스"""
    
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {api_token}"}
    
    def get_nodes(self) -> List[Dict]:
        """등록된 모든 노드 조회"""
        try:
            response = requests.get(
                f"{self.api_url}/nodes",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 노드 목록 조회 실패: {e}")
            return []
    
    def get_wireguard_status(self) -> Dict:
        """WireGuard 서버 상태 조회"""
        try:
            response = requests.get(
                f"{self.api_url}/status/wireguard",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] WireGuard 상태 조회 실패: {e}")
            return {}
    
    def format_bytes(self, bytes_value: int) -> str:
        """바이트를 읽기 쉬운 형식으로 변환"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def format_time_diff(self, timestamp: Optional[str]) -> str:
        """시간 차이를 읽기 쉬운 형식으로 변환"""
        if not timestamp:
            return "Never"
        
        try:
            # ISO 형식 파싱
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            diff = datetime.now() - dt.replace(tzinfo=None)
            
            if diff.days > 0:
                return f"{diff.days}일 전"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600}시간 전"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60}분 전"
            else:
                return f"{diff.seconds}초 전"
        except:
            return "Unknown"
    
    def print_status(self):
        """VPN 상태 출력"""
        print("\n" + "="*70)
        print(" WireGuard VPN 상태 모니터링")
        print("="*70)
        
        # WireGuard 서버 상태
        wg_status = self.get_wireguard_status()
        if wg_status and not wg_status.get("error"):
            print("\n[서버 정보]")
            interface = wg_status.get('interface', {})
            print(f"  인터페이스: {interface.get('interface', 'wg0')}")
            print(f"  포트: {interface.get('port', '51820')}")
            print(f"  연결된 피어: {wg_status.get('peer_count', 0)}개")
            print(f"  상태: {wg_status.get('status', 'unknown')}")
        else:
            print("\n[서버 정보]")
            print(f"  상태: 오류 - {wg_status.get('error', 'Unknown error')}")
        
        # 노드 상태
        nodes = self.get_nodes()
        if nodes:
            print("\n[노드 상태]")
            print("-"*70)
            
            # 헤더
            print(f"{'노드 ID':<20} {'타입':<8} {'VPN IP':<15} {'상태':<10} {'연결':<8}")
            print("-"*70)
            
            # 노드별 정보
            for node in nodes:
                node_id = node['node_id']
                if len(node_id) > 18:
                    node_id = node_id[:16] + ".."
                
                connected = "✓ 연결" if node.get('connected') else "✗ 끊김"
                status_color = "\033[92m" if node.get('connected') else "\033[91m"
                reset_color = "\033[0m"
                
                print(f"{node_id:<20} {node['node_type']:<8} {node['vpn_ip']:<15} "
                      f"{node['status']:<10} {status_color}{connected}{reset_color}")
                
                # 상세 정보
                if node.get('connected'):
                    last_handshake = self.format_time_diff(node.get('last_handshake'))
                    bytes_sent = self.format_bytes(node.get('bytes_sent', 0))
                    bytes_recv = self.format_bytes(node.get('bytes_received', 0))
                    
                    print(f"  └─ 마지막 핸드셰이크: {last_handshake}")
                    print(f"     전송: {bytes_sent}, 수신: {bytes_recv}")
        else:
            print("\n[노드 상태]")
            print("  등록된 노드가 없습니다.")
        
        print("\n" + "="*70)
    
    def continuous_monitor(self, interval: int = 5):
        """지속적인 모니터링"""
        try:
            while True:
                # 화면 지우기
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # 상태 출력
                self.print_status()
                
                # 갱신 정보
                print(f"\n{interval}초마다 갱신 중... (Ctrl+C로 종료)")
                print(f"마지막 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 대기
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n모니터링 종료")
            sys.exit(0)

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='WireGuard VPN 상태 모니터링 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 일회성 상태 확인
  python3 vpn-status.py
  
  # 지속적인 모니터링 (5초 간격)
  python3 vpn-status.py --watch
  
  # 사용자 정의 설정
  python3 vpn-status.py --api-url http://vpn.example.com:8090 --api-token your-token
        """
    )
    
    parser.add_argument(
        '--api-url',
        default=os.getenv('VPN_API_URL', 'http://localhost:8090'),
        help='VPN 관리 API URL (기본값: $VPN_API_URL 또는 http://localhost:8090)'
    )
    
    parser.add_argument(
        '--api-token',
        default=os.getenv('API_TOKEN', 'test-token-123'),
        help='API 인증 토큰 (기본값: $API_TOKEN)'
    )
    
    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='지속적인 모니터링 모드'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='모니터링 갱신 주기 (초, 기본값: 5)'
    )
    
    args = parser.parse_args()
    
    # 모니터 생성
    monitor = VPNMonitor(args.api_url, args.api_token)
    
    # 실행
    if args.watch:
        monitor.continuous_monitor(args.interval)
    else:
        monitor.print_status()

if __name__ == "__main__":
    main()