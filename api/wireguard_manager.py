import subprocess
import os
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WireGuardManager:
    """WireGuard 서버 관리 클래스"""
    
    def __init__(self):
        self.config_path = os.getenv("WIREGUARD_CONFIG_PATH", "/config")
        self.interface = "wg0"
        self.server_config = f"{self.config_path}/wg0.conf"
        
    def generate_keypair(self) -> Dict[str, str]:
        """WireGuard 키 쌍 생성"""
        try:
            # 개인키 생성
            private_key = subprocess.check_output(
                ["wg", "genkey"], 
                stderr=subprocess.PIPE
            ).decode().strip()
            
            # 공개키 생성
            public_key = subprocess.check_output(
                ["wg", "pubkey"], 
                input=private_key.encode(),
                stderr=subprocess.PIPE
            ).decode().strip()
            
            return {
                "private_key": private_key,
                "public_key": public_key
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"키 생성 실패: {e}")
            raise Exception(f"WireGuard 키 생성 실패: {str(e)}")
    
    def get_server_public_key(self) -> str:
        """서버의 공개키 조회"""
        try:
            # 서버 공개키 파일 확인
            pubkey_file = f"{self.config_path}/server/publickey"
            if os.path.exists(pubkey_file):
                with open(pubkey_file, "r") as f:
                    return f.read().strip()
            
            # Docker 컨테이너에서 실행하는 경우
            if os.path.exists("/var/run/docker.sock"):
                result = subprocess.run(
                    ["docker", "exec", "wireguard-server", "wg", "show", self.interface, "public-key"],
                    capture_output=True,
                    text=True
                )
            else:
                # 로컬 환경에서 직접 실행
                result = subprocess.run(
                    ["wg", "show", self.interface, "public-key"],
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            # 실패 시 기본값 반환
            logger.warning(f"서버 공개키 조회 실패, 기본값 사용")
            return "SERVER_PUBLIC_KEY_NOT_FOUND"
            
        except Exception as e:
            logger.error(f"서버 공개키 조회 실패: {e}")
            return "SERVER_PUBLIC_KEY_NOT_FOUND"
    
    def create_peer_config(self, node_id: str, vpn_ip: str, 
                          private_key: str, public_key: str) -> str:
        """피어용 WireGuard 설정 파일 생성"""
        server_public_key = self.get_server_public_key()
        server_endpoint = os.getenv("SERVERURL", "localhost")
        
        config = f"""[Interface]
# Node ID: {node_id}
PrivateKey = {private_key}
Address = {vpn_ip}/16
DNS = 8.8.8.8, 8.8.4.4
MTU = 1420

[Peer]
# VPN Server
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:51820
AllowedIPs = 10.100.0.0/16
PersistentKeepalive = 25
"""
        return config
    
    def add_peer_to_server(self, public_key: str, vpn_ip: str, node_id: str):
        """서버에 피어 추가"""
        try:
            # Docker 컨테이너에서 실행하는 경우 docker exec 사용
            if os.path.exists("/var/run/docker.sock"):
                cmd = [
                    "docker", "exec", "wireguard-server",
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "allowed-ips", f"{vpn_ip}/32"
                ]
            else:
                # 로컬 환경에서 직접 실행
                cmd = [
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "allowed-ips", f"{vpn_ip}/32"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"wg set 실패: {result.stderr}")
            
            # 설정 저장 (에러 무시)
            try:
                if os.path.exists("/var/run/docker.sock"):
                    save_cmd = ["docker", "exec", "wireguard-server", "wg-quick", "save", self.interface]
                else:
                    save_cmd = ["wg-quick", "save", self.interface]
                subprocess.run(save_cmd, capture_output=True, text=True, timeout=5)
            except:
                pass  # 저장 실패는 무시
            
            logger.info(f"피어 추가 성공: {node_id} ({vpn_ip})")
            
        except Exception as e:
            logger.error(f"피어 추가 실패: {e}")
            raise Exception(f"피어 추가 실패: {str(e)}")
    
    def remove_peer_from_server(self, public_key: str):
        """서버에서 피어 제거"""
        try:
            # Docker 컨테이너에서 실행하는 경우
            if os.path.exists("/var/run/docker.sock"):
                cmd = [
                    "docker", "exec", "wireguard-server",
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "remove"
                ]
            else:
                cmd = [
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "remove"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"wg set 실패: {result.stderr}")
            
            # 설정 저장 (에러 무시)
            try:
                if os.path.exists("/var/run/docker.sock"):
                    save_cmd = ["docker", "exec", "wireguard-server", "wg-quick", "save", self.interface]
                else:
                    save_cmd = ["wg-quick", "save", self.interface]
                subprocess.run(save_cmd, capture_output=True, text=True, timeout=5)
            except:
                pass
            
            logger.info(f"피어 제거 성공: {public_key[:8]}...")
            
        except Exception as e:
            logger.error(f"피어 제거 실패: {e}")
            raise Exception(f"피어 제거 실패: {str(e)}")
    
    def get_peer_status(self, public_key: str) -> Dict:
        """특정 피어의 상태 조회"""
        try:
            # Docker 컨테이너에서 실행하는 경우
            if os.path.exists("/var/run/docker.sock"):
                result = subprocess.run(
                    ["docker", "exec", "wireguard-server", "wg", "show", self.interface, "dump"],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["wg", "show", self.interface, "dump"],
                    capture_output=True,
                    text=True
                )
            
            # dump 형식 파싱
            for line in result.stdout.strip().split('\n')[1:]:  # 첫 줄은 인터페이스 정보
                parts = line.split('\t')
                if len(parts) >= 8 and parts[0] == public_key:
                    last_handshake_ts = int(parts[4]) if parts[4] != '0' else 0
                    return {
                        "connected": last_handshake_ts > 0,
                        "last_handshake": datetime.fromtimestamp(last_handshake_ts) if last_handshake_ts > 0 else None,
                        "bytes_received": int(parts[5]),
                        "bytes_sent": int(parts[6])
                    }
            
            # 피어를 찾지 못한 경우
            return {
                "connected": False,
                "last_handshake": None,
                "bytes_received": 0,
                "bytes_sent": 0
            }
            
        except Exception as e:
            logger.error(f"피어 상태 조회 실패: {e}")
            return {
                "connected": False,
                "last_handshake": None,
                "bytes_received": 0,
                "bytes_sent": 0
            }
    
    def get_server_status(self) -> Dict:
        """WireGuard 서버 전체 상태 조회"""
        try:
            # Docker 컨테이너에서 실행하는 경우
            if os.path.exists("/var/run/docker.sock"):
                result = subprocess.run(
                    ["docker", "exec", "wireguard-server", "wg", "show", self.interface],
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ["wg", "show", self.interface],
                    capture_output=True,
                    text=True
                )
            
            interface_info = {}
            peers = []
            current_peer = None
            
            # 출력 파싱
            for line in result.stdout.strip().split('\n'):
                if line.startswith('interface:'):
                    interface_info['interface'] = line.split(':')[1].strip()
                elif line.startswith('  public key:'):
                    interface_info['public_key'] = line.split(':')[1].strip()
                elif line.startswith('  private key:'):
                    interface_info['private_key'] = '(hidden)'
                elif line.startswith('  listening port:'):
                    interface_info['port'] = line.split(':')[1].strip()
                elif line.startswith('peer:'):
                    if current_peer:
                        peers.append(current_peer)
                    current_peer = {'public_key': line.split(':')[1].strip()}
                elif current_peer:
                    if line.startswith('  endpoint:'):
                        current_peer['endpoint'] = line.split(':', 1)[1].strip()
                    elif line.startswith('  allowed ips:'):
                        current_peer['allowed_ips'] = line.split(':', 1)[1].strip()
                    elif line.startswith('  latest handshake:'):
                        current_peer['latest_handshake'] = line.split(':', 1)[1].strip()
                    elif line.startswith('  transfer:'):
                        current_peer['transfer'] = line.split(':', 1)[1].strip()
            
            if current_peer:
                peers.append(current_peer)
            
            return {
                "interface": interface_info,
                "peers": peers,
                "peer_count": len(peers),
                "status": "running"
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"서버 상태 조회 실패: {e}")
            return {
                "error": f"WireGuard 상태 조회 실패: {str(e)}",
                "interface": {},
                "peers": [],
                "peer_count": 0,
                "status": "error"
            }
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return {
                "error": f"오류 발생: {str(e)}",
                "interface": {},
                "peers": [],
                "peer_count": 0,
                "status": "error"
            }