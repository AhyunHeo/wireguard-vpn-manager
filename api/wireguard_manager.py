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
    
    def allocate_ip(self, node_type: str = "worker") -> Optional[str]:
        """워커노드용 IP 자동 할당 (중앙서버는 VPN 사용 안함)"""
        try:
            from database import SessionLocal
            from models import Node
            
            db = SessionLocal()
            
            # 워커 노드용 IP 할당 (10.100.1.x 대역)
            # 현재 사용 중인 모든 워커노드 IP 조회
            used_ips = db.query(Node.vpn_ip).all()
            used_ip_set = set([ip[0] for ip in used_ips if ip[0]])
            
            # 10.100.1.2부터 10.100.1.254까지 순차 할당 (최대 253개)
            for i in range(2, 255):
                candidate_ip = f"10.100.1.{i}"
                if candidate_ip not in used_ip_set:
                    db.close()
                    logger.info(f"IP 할당 완료: {candidate_ip}")
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
Address = {client_ip}/16
DNS = 8.8.8.8, 8.8.4.4
MTU = 1420

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:41820
AllowedIPs = 10.100.0.1/16
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
Endpoint = {server_endpoint}:41820
AllowedIPs = 10.100.0.1/16
PersistentKeepalive = 25
"""
        return config
    
    def add_peer_to_server(self, public_key: str, vpn_ip: str, node_id: str):
        """서버에 피어 추가 및 설정 파일 업데이트"""
        logger.info(f"=== Starting add_peer_to_server ===")
        logger.info(f"Node ID: {node_id}, VPN IP: {vpn_ip}")
        logger.info(f"Public Key: {public_key[:20]}...")
        
        try:
            # 0. 서버 설정 파일 서브넷 마스크 확인 및 수정
            self._ensure_server_subnet()
            
            # 1. 먼저 같은 IP를 가진 기존 피어가 있는지 확인하고 제거
            logger.info(f"Checking for docker socket at /var/run/docker.sock")
            if os.path.exists("/var/run/docker.sock"):
                # 현재 피어 목록 확인
                logger.info("Docker socket found, trying to get peer list")
                dump_cmd = [
                    "docker", "exec", "wireguard-server",
                    "wg", "show", self.interface, "dump"
                ]
                logger.info(f"Running command: {' '.join(dump_cmd)}")
                result = subprocess.run(dump_cmd, capture_output=True, text=True)
                
                # 실패 시 로그 출력
                if result.returncode != 0:
                    logger.warning(f"Failed to get WireGuard peer list: {result.stderr}")
                    logger.info("Trying alternative approach...")
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n')[1:]:
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            existing_key = parts[0]
                            allowed_ips = parts[3]
                            # 같은 IP를 가진 다른 피어가 있으면 먼저 제거
                            if f"{vpn_ip}/32" in allowed_ips and existing_key != public_key:
                                logger.info(f"기존 피어 제거 중: {existing_key[:8]}... (IP: {vpn_ip})")
                                self.remove_peer_from_server(existing_key)
            
            # 2. 설정 파일에 피어 추가 (먼저 파일 업데이트)
            # 3. 설정 파일에 피어 추가 전에 중복 확인
            config_path = "/config/wg_confs/wg0.conf"
            logger.info(f"Checking config file at {config_path}")
            if os.path.exists("/var/run/docker.sock"):
                # 현재 설정 읽기
                read_cmd = [
                    "docker", "exec", "wireguard-server",
                    "cat", config_path
                ]
                result = subprocess.run(read_cmd, capture_output=True, text=True)
                
                # 실패 시 로그 출력
                if result.returncode != 0:
                    logger.error(f"Failed to read config file: {result.stderr}")
                    logger.info(f"Command was: {' '.join(read_cmd)}")
                    # 설정 파일 직접 접근 시도
                    config_mount_path = "./config/wg_confs/wg0.conf"
                    if os.path.exists(config_mount_path):
                        logger.info("Trying direct file access...")
                        with open(config_mount_path, 'r') as f:
                            config_content = f.read()
                            if public_key not in config_content:
                                # 직접 파일에 추가
                                with open(config_mount_path, 'a') as f:
                                    f.write(f"\n[Peer]\n")
                                    f.write(f"# {node_id}\n")
                                    f.write(f"PublicKey = {public_key}\n")
                                    f.write(f"AllowedIPs = {vpn_ip}/32\n")
                                logger.info("Added peer directly to config file")
                    return
                
                # PublicKey가 이미 있는지 확인
                if result.returncode == 0 and public_key not in result.stdout:
                    # 설정 파일에 피어 추가 (각 줄을 개별적으로 추가)
                    logger.info(f"Adding peer {node_id} to config file...")
                    # 피어의 AllowedIPs 설정 (해당 피어의 고유 IP만)
                    allowed_ips = f"{vpn_ip}/32"
                    append_cmds = [
                        ["docker", "exec", "wireguard-server", "sh", "-c", f"echo '' >> {config_path}"],
                        ["docker", "exec", "wireguard-server", "sh", "-c", f"echo '[Peer]' >> {config_path}"],
                        ["docker", "exec", "wireguard-server", "sh", "-c", f"echo '# {node_id}' >> {config_path}"],
                        ["docker", "exec", "wireguard-server", "sh", "-c", f"echo 'PublicKey = {public_key}' >> {config_path}"],
                        ["docker", "exec", "wireguard-server", "sh", "-c", f"echo 'AllowedIPs = {allowed_ips}' >> {config_path}"]
                    ]
                    for cmd in append_cmds:
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode != 0:
                            logger.error(f"Failed to append to config: {result.stderr}")
                    
                    # WireGuard에 피어 추가 (wg set 명령 사용)
                    logger.info(f"WireGuard에 피어 추가 중...")
                    
                    # 먼저 기존 피어 제거 (있을 경우)
                    remove_cmd = [
                        "docker", "exec", "wireguard-server",
                        "wg", "set", self.interface,
                        "peer", public_key,
                        "remove"
                    ]
                    subprocess.run(remove_cmd, capture_output=True, text=True)
                    
                    # 새로 피어 추가
                    wg_cmd = [
                        "docker", "exec", "wireguard-server",
                        "wg", "set", self.interface,
                        "peer", public_key,
                        "allowed-ips", allowed_ips
                    ]
                    wg_result = subprocess.run(wg_cmd, capture_output=True, text=True)
                    
                    if wg_result.returncode != 0:
                        logger.warning(f"wg set 실패: {wg_result.stderr}")
                        # wg set 실패 시 인터페이스 재시작
                        logger.info("WireGuard 인터페이스 재시작 중...")
                        restart_cmds = [
                            ["docker", "exec", "wireguard-server", "wg-quick", "down", "wg0"],
                            ["docker", "exec", "wireguard-server", "wg-quick", "up", "wg0"]
                        ]
                        for cmd in restart_cmds:
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            if result.returncode != 0:
                                logger.error(f"재시작 명령 실패: {result.stderr}")
                    else:
                        logger.info(f"피어 추가 성공: {public_key[:8]}...")
                        
                        # 설정 파일과 동기화
                        sync_cmd = [
                            "docker", "exec", "wireguard-server",
                            "wg", "syncconf", self.interface, config_path
                        ]
                        sync_result = subprocess.run(sync_cmd, capture_output=True, text=True)
                        if sync_result.returncode != 0:
                            logger.warning(f"Config sync failed: {sync_result.stderr}")
                else:
                    logger.info(f"피어가 이미 설정에 존재함: {public_key[:8]}...")
            else:
                # 로컬 환경에서 직접 파일 수정
                logger.info(f"No Docker socket found, trying local file access at {self.server_config}")
                if not os.path.exists(self.server_config):
                    logger.error(f"Config file not found at {self.server_config}")
                    return
                    
                with open(self.server_config, 'r') as f:
                    if public_key not in f.read():
                        # 피어의 AllowedIPs 설정
                        allowed_ips = f"{vpn_ip}/16"
                        with open(self.server_config, 'a') as f:
                            f.write(f"\n[Peer]\n# {node_id}\nPublicKey = {public_key}\nAllowedIPs = {allowed_ips}\n")
                
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
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"피어 추가 실패: {str(e)}")
    
    def remove_peer_from_server(self, public_key: str):
        """서버에서 피어 제거 및 설정 파일에서도 완전히 삭제"""
        try:
            # 1. 런타임에서 피어 제거
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
                logger.warning(f"wg set remove 경고: {result.stderr}")
            
            # 2. 설정 파일에서 피어 섹션 완전히 제거
            config_path = "/config/wg_confs/wg0.conf"
            if os.path.exists("/var/run/docker.sock"):
                # Docker 환경: 설정 파일 읽기
                read_cmd = [
                    "docker", "exec", "wireguard-server",
                    "cat", config_path
                ]
                result = subprocess.run(read_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    config_lines = result.stdout.splitlines()
                    new_config = []
                    skip_peer = False
                    
                    for line in config_lines:
                        # 해당 PublicKey를 가진 [Peer] 섹션 찾기
                        if line.strip() == "[Peer]":
                            # 다음 줄들을 확인하여 이 피어인지 확인
                            peer_section = [line]
                            for i in range(config_lines.index(line) + 1, len(config_lines)):
                                next_line = config_lines[i]
                                if next_line.strip().startswith("PublicKey") and public_key in next_line:
                                    skip_peer = True
                                    break
                                elif next_line.strip() == "[Peer]" or next_line.strip().startswith("["):
                                    break
                                peer_section.append(next_line)
                            
                            if not skip_peer:
                                new_config.extend(peer_section)
                        elif skip_peer:
                            # 이 피어 섹션 건너뛰기
                            if line.strip() == "" or line.strip().startswith("["):
                                skip_peer = False
                                if line.strip() != "":
                                    new_config.append(line)
                        else:
                            new_config.append(line)
                    
                    # 새 설정을 파일에 쓰기
                    new_config_str = "\n".join(new_config)
                    write_cmd = [
                        "docker", "exec", "wireguard-server",
                        "sh", "-c",
                        f"echo '{new_config_str}' > {config_path}"
                    ]
                    subprocess.run(write_cmd, capture_output=True, text=True)
                    
                    # WireGuard 재시작으로 설정 적용
                    restart_cmd = [
                        "docker", "exec", "wireguard-server",
                        "wg-quick", "down", "wg0"
                    ]
                    subprocess.run(restart_cmd, capture_output=True, text=True)
                    
                    restart_cmd = [
                        "docker", "exec", "wireguard-server",
                        "wg-quick", "up", "wg0"
                    ]
                    subprocess.run(restart_cmd, capture_output=True, text=True)
            
            logger.info(f"피어 완전 제거 성공: {public_key[:8]}...")
            
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
    
    def _ensure_server_subnet(self):
        """서버 설정의 서브넷 마스크가 올바른지 확인하고 수정"""
        try:
            if os.path.exists("/var/run/docker.sock"):
                # 설정 파일 읽기
                read_cmd = [
                    "docker", "exec", "wireguard-server",
                    "cat", "/config/wg_confs/wg0.conf"
                ]
                result = subprocess.run(read_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    config_content = result.stdout
                    
                    # Address 라인에 /16이 없으면 추가
                    if "Address = 10.100.0.1\n" in config_content or "Address = 10.100.0.1 " in config_content:
                        logger.info("Fixing server subnet mask to /16")
                        
                        # sed로 수정
                        fix_cmd = [
                            "docker", "exec", "wireguard-server", "sh", "-c",
                            "sed -i 's/^Address = 10.100.0.1$/Address = 10.100.0.1\/16/' /config/wg_confs/wg0.conf"
                        ]
                        subprocess.run(fix_cmd, capture_output=True, text=True)
                        
                        # WireGuard 재시작
                        restart_cmds = [
                            ["docker", "exec", "wireguard-server", "wg-quick", "down", "wg0"],
                            ["docker", "exec", "wireguard-server", "wg-quick", "up", "wg0"]
                        ]
                        for cmd in restart_cmds:
                            subprocess.run(cmd, capture_output=True, text=True)
                        
                        logger.info("Server subnet mask fixed and WireGuard restarted")
        except Exception as e:
            logger.warning(f"Failed to ensure server subnet: {e}")
    
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
    
    def fix_peer_allowed_ips(self):
        """기존 피어들의 AllowedIPs를 /16에서 /32로 수정"""
        try:
            fixed_count = 0
            config_path = "/config/wg_confs/wg0.conf"
            
            if os.path.exists("/var/run/docker.sock"):
                # 1. 현재 설정 파일 읽기
                read_cmd = ["docker", "exec", "wireguard-server", "cat", config_path]
                result = subprocess.run(read_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to read config: {result.stderr}")
                    return {"error": "Failed to read config", "fixed": 0}
                
                # 2. 설정 파일 내용 수정
                lines = result.stdout.split('\n')
                new_lines = []
                
                for line in lines:
                    if line.strip().startswith('AllowedIPs'):
                        # AllowedIPs 라인 파싱
                        parts = line.split('=')
                        if len(parts) == 2:
                            ips = parts[1].strip()
                            # /16을 /32로 변경
                            if '/16' in ips:
                                # IP 주소 추출
                                ip_addr = ips.split('/')[0].strip()
                                new_line = f"AllowedIPs = {ip_addr}/32"
                                new_lines.append(new_line)
                                fixed_count += 1
                                logger.info(f"Fixed AllowedIPs: {ips} -> {ip_addr}/32")
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                # 3. 수정된 내용을 파일에 쓰기
                if fixed_count > 0:
                    new_content = '\n'.join(new_lines)
                    
                    # 임시 파일에 쓰기
                    write_cmd = [
                        "docker", "exec", "wireguard-server", "sh", "-c",
                        f"cat > {config_path}.tmp << 'EOF'\n{new_content}\nEOF"
                    ]
                    result = subprocess.run(write_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        # 원본 파일 교체
                        mv_cmd = [
                            "docker", "exec", "wireguard-server",
                            "mv", f"{config_path}.tmp", config_path
                        ]
                        subprocess.run(mv_cmd, capture_output=True, text=True)
                        
                        # 4. WireGuard 설정 다시 로드
                        reload_cmd = [
                            "docker", "exec", "wireguard-server",
                            "wg", "syncconf", "wg0", config_path
                        ]
                        reload_result = subprocess.run(reload_cmd, capture_output=True, text=True)
                        
                        if reload_result.returncode != 0:
                            # syncconf 실패 시 재시작
                            logger.warning("syncconf failed, restarting interface...")
                            restart_cmds = [
                                ["docker", "exec", "wireguard-server", "wg-quick", "down", "wg0"],
                                ["docker", "exec", "wireguard-server", "wg-quick", "up", "wg0"]
                            ]
                            for cmd in restart_cmds:
                                subprocess.run(cmd, capture_output=True, text=True)
                        
                        logger.info(f"Fixed {fixed_count} peer(s) AllowedIPs configuration")
                        return {"success": True, "fixed": fixed_count}
                    else:
                        logger.error(f"Failed to write new config: {result.stderr}")
                        return {"error": "Failed to write config", "fixed": 0}
                else:
                    logger.info("No peers with /16 subnet found, all configs are correct")
                    return {"success": True, "fixed": 0, "message": "All peers already have correct AllowedIPs"}
            else:
                # 로컬 파일 시스템 직접 접근
                config_mount_path = "./config/wg_confs/wg0.conf"
                if os.path.exists(config_mount_path):
                    with open(config_mount_path, 'r') as f:
                        content = f.read()
                    
                    # /16을 /32로 변경
                    import re
                    pattern = r'AllowedIPs\s*=\s*(\d+\.\d+\.\d+\.\d+)/16'
                    matches = re.findall(pattern, content)
                    
                    if matches:
                        for ip in matches:
                            old_pattern = f"{ip}/16"
                            new_pattern = f"{ip}/32"
                            content = content.replace(old_pattern, new_pattern)
                            fixed_count += 1
                            logger.info(f"Fixed: {old_pattern} -> {new_pattern}")
                        
                        # 파일 저장
                        with open(config_mount_path, 'w') as f:
                            f.write(content)
                        
                        return {"success": True, "fixed": fixed_count}
                    else:
                        return {"success": True, "fixed": 0, "message": "No /16 subnets found"}
                else:
                    return {"error": "Config file not found", "fixed": 0}
                    
        except Exception as e:
            logger.error(f"Error fixing peer AllowedIPs: {e}")
            return {"error": str(e), "fixed": 0}