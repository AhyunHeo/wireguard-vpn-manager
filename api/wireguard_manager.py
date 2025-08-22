import subprocess
import os
from typing import Dict, Optional
from datetime import datetime
import logging
import ipaddress

logger = logging.getLogger(__name__)

class WireGuardManager:
    """WireGuard 서버 관리 클래스"""
    
    def __init__(self):
        self.config_path = os.getenv("WIREGUARD_CONFIG_PATH", "/config")
        self.interface = "wg0"
        # LinuxServer WireGuard 이미지는 /config/wg_confs/wg0.conf 사용
        self.server_config = f"{self.config_path}/wg_confs/wg0.conf"
        self.used_ips = set()  # 사용 중인 IP 관리
        
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
    
    def allocate_ip(self, node_type: str) -> Optional[str]:
        """노드 타입에 따라 IP 자동 할당"""
        try:
            from database import SessionLocal
            from models import Node
            
            db = SessionLocal()
            
            if node_type == "central":
                # 중앙서버용 IP 할당 (10.100.0.x 대역의 낮은 번호)
                # 현재 사용 중인 모든 중앙서버 IP 조회
                used_ips = db.query(Node.vpn_ip).filter(
                    Node.node_type == "central"
                ).all()
                
                used_ip_set = set([ip[0] for ip in used_ips if ip[0]])
                
                # 10.100.0.2부터 10.100.0.6까지 중앙서버용으로 예약 (최대 5개)
                for i in range(2, 7):
                    candidate_ip = f"10.100.0.{i}"
                    if candidate_ip not in used_ip_set:
                        db.close()
                        return candidate_ip
                
                db.close()
                logger.error("중앙서버용 IP 풀이 가득 찼습니다")
                return None
            
            # 워커 노드용 IP 할당 (10.100.1.x 대역)
            # 현재 사용 중인 모든 IP 조회
            used_ips = db.query(Node.vpn_ip).filter(
                Node.node_type == "worker"
            ).all()
            
            used_ip_set = set([ip[0] for ip in used_ips if ip[0]])
            
            # 10.100.1.2부터 10.100.1.11까지 순차 할당 (최대 10개)
            for i in range(2, 12):
                candidate_ip = f"10.100.1.{i}"
                if candidate_ip not in used_ip_set:
                    db.close()
                    return candidate_ip
            
            db.close()
            logger.error("워커 노드용 IP 풀이 가득 찼습니다")
            return None
            
        except Exception as e:
            logger.error(f"IP 할당 실패: {e}")
            return None
    
    def generate_client_config(self, private_key: str, client_ip: str, 
                              server_public_key: str = None, client_network: str = None) -> str:
        """클라이언트용 WireGuard 설정 생성"""
        if not server_public_key:
            server_public_key = self.get_server_public_key()
        
        server_endpoint = os.getenv("SERVERURL", "localhost")
        local_server_ip = os.getenv("LOCAL_SERVER_IP", "localhost")
        
        # SERVERURL이 "auto"인 경우 LOCAL_SERVER_IP 사용
        if server_endpoint == "auto":
            # 로컬 네트워크에서는 항상 LOCAL_SERVER_IP 사용
            if local_server_ip and local_server_ip != "localhost":
                server_endpoint = local_server_ip
                logger.info(f"Using LOCAL_SERVER_IP for local network: {server_endpoint}")
            else:
                # LOCAL_SERVER_IP가 설정되지 않은 경우에만 외부 IP 감지 시도
                try:
                    import urllib.request
                    response = urllib.request.urlopen('https://api.ipify.org', timeout=5)
                    detected_ip = response.read().decode('utf-8').strip()
                    # 감지된 IP가 사설 IP 대역이면 그대로 사용
                    if detected_ip.startswith(('192.168.', '10.', '172.')):
                        server_endpoint = detected_ip
                    else:
                        # 공인 IP인 경우 LOCAL_SERVER_IP 우선 사용
                        server_endpoint = local_server_ip if local_server_ip != "localhost" else detected_ip
                    logger.info(f"Auto-detected IP: {server_endpoint}")
                except:
                    # 폴백: localhost 사용
                    server_endpoint = "localhost"
                    logger.warning("Could not detect server IP, using localhost")
        
        config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = 8.8.8.8, 8.8.4.4
MTU = 1420

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:51820
AllowedIPs = 10.100.0.0/16
PersistentKeepalive = 25
"""
        return config
    
    def get_server_public_key(self) -> str:
        """서버의 공개키 조회"""
        try:
            # 1. 서버 공개키 파일 확인 (캐시)
            pubkey_file = f"{self.config_path}/server/publickey"
            if os.path.exists(pubkey_file):
                with open(pubkey_file, "r") as f:
                    key = f.read().strip()
                    if key and key != "SERVER_PUBLIC_KEY_NOT_FOUND":
                        return key
            
            # 2. LinuxServer WireGuard 컨테이너의 경우
            server_pubkey_paths = [
                f"{self.config_path}/server/publickey-server",  # 실제 파일명
                f"{self.config_path}/server/server.publickey"
            ]
            for server_pubkey_path in server_pubkey_paths:
                if os.path.exists(server_pubkey_path):
                    with open(server_pubkey_path, "r") as f:
                        key = f.read().strip()
                        if key:
                            # 캐시에 저장
                            os.makedirs(f"{self.config_path}/server", exist_ok=True)
                            with open(pubkey_file, "w") as f:
                                f.write(key)
                            logger.info(f"서버 공개키 찾음: {server_pubkey_path}")
                            return key
            
            # 3. wg0.conf에서 PrivateKey 찾아서 공개키 계산
            wg_conf_path = f"{self.config_path}/wg0.conf"
            if os.path.exists(wg_conf_path):
                with open(wg_conf_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("PrivateKey"):
                            private_key = line.split("=")[1].strip()
                            # wg pubkey로 공개키 생성
                            result = subprocess.run(
                                ["echo", private_key, "|", "wg", "pubkey"],
                                shell=True,
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                public_key = result.stdout.strip()
                                # 캐시에 저장
                                os.makedirs(f"{self.config_path}/server", exist_ok=True)
                                with open(pubkey_file, "w") as f:
                                    f.write(public_key)
                                return public_key
            
            # 4. Docker 컨테이너에서 직접 조회
            if os.path.exists("/var/run/docker.sock"):
                result = subprocess.run(
                    ["docker", "exec", "wireguard-server", "wg", "show", self.interface, "public-key"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    public_key = result.stdout.strip()
                    # 캐시에 저장
                    os.makedirs(f"{self.config_path}/server", exist_ok=True)
                    with open(pubkey_file, "w") as f:
                        f.write(public_key)
                    return public_key
            
            # 실패 시 에러 메시지
            logger.error("서버 공개키를 찾을 수 없습니다. WireGuard 서버가 실행 중인지 확인하세요.")
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
        """서버에 피어 추가 및 설정 파일 업데이트"""
        try:
            # 1. 먼저 wg 명령으로 런타임에 피어 추가
            if os.path.exists("/var/run/docker.sock"):
                cmd = [
                    "docker", "exec", "wireguard-server",
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "allowed-ips", f"{vpn_ip}/32"
                ]
            else:
                cmd = [
                    "wg", "set", self.interface,
                    "peer", public_key,
                    "allowed-ips", f"{vpn_ip}/32"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"wg set 경고: {result.stderr}")
            
            # 2. 설정 파일에 직접 피어 추가 (영구 저장)
            peer_config = f"""
[Peer]
# {node_id}
PublicKey = {public_key}
AllowedIPs = {vpn_ip}/32
"""
            
            # Docker 환경에서 설정 파일 업데이트
            if os.path.exists("/var/run/docker.sock"):
                # 설정 파일에 피어 추가
                append_cmd = [
                    "docker", "exec", "wireguard-server",
                    "sh", "-c",
                    f"echo '{peer_config}' >> /config/wg_confs/wg0.conf"
                ]
                subprocess.run(append_cmd, capture_output=True, text=True)
                
                # WireGuard 재시작으로 설정 적용
                reload_cmd = [
                    "docker", "exec", "wireguard-server",
                    "sh", "-c",
                    "wg syncconf wg0 <(wg-quick strip wg0)"
                ]
                subprocess.run(reload_cmd, capture_output=True, text=True)
            else:
                # 로컬 환경에서 직접 파일 수정
                with open(self.server_config, 'a') as f:
                    f.write(peer_config)
                
                # 설정 재로드
                subprocess.run(["wg", "syncconf", self.interface, self.server_config], 
                             capture_output=True, text=True)
            
            # 3. 워커 노드(10.100.1.x)인 경우 라우트 추가
            ip_obj = ipaddress.IPv4Address(vpn_ip)
            if ip_obj in ipaddress.IPv4Network('10.100.1.0/24'):
                logger.info(f"워커 노드 감지: {vpn_ip}, 라우트 추가 중...")
                if os.path.exists("/var/run/docker.sock"):
                    route_cmd = [
                        "docker", "exec", "wireguard-server",
                        "ip", "route", "add", f"{vpn_ip}/32", "dev", self.interface
                    ]
                else:
                    route_cmd = [
                        "ip", "route", "add", f"{vpn_ip}/32", "dev", self.interface
                    ]
                
                route_result = subprocess.run(route_cmd, capture_output=True, text=True)
                if route_result.returncode == 0:
                    logger.info(f"라우트 추가 성공: {vpn_ip}")
                elif "File exists" in route_result.stderr:
                    logger.info(f"라우트 이미 존재: {vpn_ip}")
                else:
                    logger.warning(f"라우트 추가 실패: {route_result.stderr}")
            
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