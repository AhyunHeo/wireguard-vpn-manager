# 🔧 워커 노드 VPN 연결 실전 테스트 가이드

## 📋 테스트 준비

### VPN Manager 서버 (Windows 노트북)
- IP: 192.168.0.68
- 실행 중: `docker-compose -f docker-compose.external.yml up -d`
- 방화벽: 8090(TCP), 51820(UDP) 열림

### 워커 노드 (테스트할 컴퓨터)
- IP: 192.168.0.30 (또는 다른 IP)
- OS: Linux/Windows

---

## 🚀 Step 1: 워커 노드 등록

### 옵션 1: 웹 브라우저로 간편 등록 (추천)

**VPN Manager 서버에서:**
1. 브라우저 열기: `http://192.168.0.68:8090/vpn-qr`
2. 노드 ID 입력: `worker-gpu-001`
3. 노드 타입: `worker` 유지
4. "QR 코드 생성" 클릭
5. "자동 설치 URL 복사" 클릭

**워커 노드에서:**
1. 복사한 URL을 브라우저에 붙여넣기
2. 자동 설치 페이지에서 운영체제 선택
3. 설정 파일 다운로드

### 옵션 2: API로 직접 등록

```bash
# 워커 노드에서 실행
curl -X POST http://192.168.0.68:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-gpu-001",
    "node_type": "worker",
    "hostname": "'$(hostname)'",
    "public_ip": "0.0.0.0"
  }' -o response.json

# 설정 파일 추출
cat response.json | jq -r '.config' | base64 -d > wg0.conf

# 확인
cat wg0.conf
```

예상 출력:
```ini
[Interface]
PrivateKey = <생성된_개인키>
Address = 10.100.1.1/32
DNS = 8.8.8.8

[Peer]
PublicKey = <서버_공개키>
Endpoint = 192.168.0.68:51820
AllowedIPs = 10.100.0.0/16
PersistentKeepalive = 25
```

---

## 🔌 Step 2: WireGuard 설치 및 연결

### Linux 워커

```bash
# 1. WireGuard 설치
sudo apt update
sudo apt install -y wireguard

# 2. 설정 파일 이동
sudo cp wg0.conf /etc/wireguard/
sudo chmod 600 /etc/wireguard/wg0.conf

# 3. VPN 연결
sudo wg-quick up wg0

# 4. 상태 확인
sudo wg show
ip addr show wg0
```

### Windows 워커

1. **WireGuard 설치:**
   - [다운로드](https://download.wireguard.com/windows-client/wireguard-installer.exe)
   - 설치 실행

2. **설정 추가:**
   - WireGuard 앱 실행
   - "Add Tunnel" → "Import from file"
   - `wg0.conf` 선택

3. **연결:**
   - "Activate" 버튼 클릭
   - Status: Active 확인

---

## ✅ Step 3: 연결 확인

### 워커 노드에서 확인

```bash
# VPN IP 확인
ip addr show wg0  # Linux
ipconfig /all     # Windows에서 WireGuard 어댑터 확인

# VPN 서버로 ping
ping 10.100.0.254

# 예상 결과:
# 64 bytes from 10.100.0.254: icmp_seq=1 ttl=64 time=1.23 ms
```

### VPN Manager 서버에서 확인

```bash
# 1. 등록된 노드 목록
curl -H "Authorization: Bearer test-token-123" \
  http://192.168.0.68:8090/nodes | python3 -m json.tool

# 예상 출력:
[
  {
    "node_id": "worker-gpu-001",
    "node_type": "worker",
    "vpn_ip": "10.100.1.1",
    "status": "registered",
    "connected": true,  # ← 연결됨!
    "last_handshake": "2024-01-15T10:30:45"
  }
]

# 2. WireGuard 실시간 상태
docker exec wireguard-server wg show

# 예상 출력:
interface: wg0
  public key: <서버_공개키>
  private key: (hidden)
  listening port: 51820

peer: <워커_공개키>
  endpoint: 192.168.0.30:xxxxx
  allowed ips: 10.100.1.1/32
  latest handshake: 10 seconds ago
  transfer: 1.23 KiB received, 2.34 KiB sent

# 3. 워커로 ping 테스트
docker exec wireguard-server ping -c 3 10.100.1.1
```

---

## 📊 Step 4: 상세 모니터링

### 실시간 연결 상태 모니터링

```bash
# 1초마다 갱신
watch -n 1 'docker exec wireguard-server wg show'
```

### API로 상세 정보 조회

```bash
# 특정 노드 상세 정보
curl -H "Authorization: Bearer test-token-123" \
  http://192.168.0.68:8090/nodes/worker-gpu-001 | python3 -m json.tool

# WireGuard 서버 전체 상태
curl -H "Authorization: Bearer test-token-123" \
  http://192.168.0.68:8090/status/wireguard | python3 -m json.tool
```

---

## 🎯 Step 5: 다중 워커 테스트

### 두 번째 워커 추가

```bash
# 워커2에서 실행
curl -X POST http://192.168.0.68:8090/nodes/register \
  -H "Authorization: Bearer test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-gpu-002",
    "node_type": "worker",
    "hostname": "worker2",
    "public_ip": "0.0.0.0"
  }' | jq -r '.config' | base64 -d > wg0.conf

sudo wg-quick up ./wg0.conf
```

### 워커 간 통신 테스트

```bash
# 워커1 (10.100.1.1)에서
ping 10.100.1.2  # 워커2로 ping

# 워커2 (10.100.1.2)에서  
ping 10.100.1.1  # 워커1로 ping
```

---

## 🔍 문제 해결

### 연결이 안 될 때

1. **방화벽 확인:**
```bash
# VPN Manager 서버
netstat -an | grep 51820  # UDP 51820 LISTENING 확인
```

2. **WireGuard 로그 확인:**
```bash
# 워커에서
sudo journalctl -u wg-quick@wg0 -f  # Linux
# Windows는 WireGuard 앱에서 Log 탭 확인
```

3. **핸드셰이크 확인:**
```bash
# latest handshake 시간 확인
docker exec wireguard-server wg show
```

### 연결은 되는데 ping이 안 될 때

```bash
# IP 포워딩 확인
docker exec wireguard-server sysctl net.ipv4.ip_forward
# 1이어야 함

# 라우팅 테이블 확인
ip route show  # 워커에서
```

---

## ✅ 성공 기준

1. ✅ 워커 노드가 VPN IP(10.100.1.x) 할당받음
2. ✅ `wg show`에서 handshake 확인
3. ✅ 워커 ↔ VPN 서버 ping 성공
4. ✅ API에서 `"connected": true` 상태
5. ✅ 다중 워커 간 통신 가능

---

## 📝 테스트 체크리스트

- [ ] 워커1 등록 및 VPN 연결
- [ ] 워커1 → VPN 서버 ping 성공
- [ ] VPN 서버 → 워커1 ping 성공
- [ ] API에서 워커1 connected 상태 확인
- [ ] 워커2 등록 및 VPN 연결
- [ ] 워커1 ↔ 워커2 ping 성공
- [ ] 5분 이상 연결 유지 확인
- [ ] 재부팅 후 자동 연결 설정

---

## 🚨 주의사항

1. **IP 충돌 방지:** 각 워커마다 고유한 node_id 사용
2. **보안:** 실제 운영 시 test-token-123 대신 강력한 토큰 사용
3. **네트워크:** NAT 환경에서는 PersistentKeepalive 필수

---

## 💡 다음 단계

연결 성공 후:
1. distributed-ai-platform과 통합
2. GPU 작업 할당 테스트
3. 대용량 데이터 전송 테스트
4. 장애 복구 시나리오 테스트