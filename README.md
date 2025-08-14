# WireGuard VPN Manager

자체 호스팅 WireGuard VPN 관리 시스템 - 분산 AI 플랫폼용

## 📋 개요

이 프로젝트는 분산 AI 플랫폼의 중앙서버와 워커노드들을 안전하게 연결하기 위한 WireGuard 기반 VPN 관리 시스템입니다. SaaS 의존성 없이 완전히 자체 호스팅 가능합니다.

## 🏗️ 아키텍처

```
[VPN Manager Server]
    ├── WireGuard Server (10.100.0.254)
    ├── Management API (Port 8090)
    └── PostgreSQL Database
    
[Connected Nodes]
    ├── Central Server (10.100.0.1)
    └── Worker Nodes (10.100.1.x)
```

## 🚀 빠른 시작

### 1. 프로젝트 클론
```bash
git clone https://github.com/your-org/wireguard-vpn-manager.git
cd wireguard-vpn-manager
```

### 2. 로컬 테스트
```bash
# 로컬 테스트 환경 실행
docker-compose -f docker-compose.local.yml up -d

# API 토큰 확인
cat .env.local
```

### 3. 프로덕션 배포
```bash
# 프로덕션 환경 설정
cp .env.example .env
# .env 파일 편집하여 설정

# 배포
./deploy.sh
```

## 📁 프로젝트 구조

```
wireguard-vpn-manager/
├── api/                    # FastAPI 관리 서버
│   ├── main.py            # API 엔드포인트
│   ├── models.py          # 데이터 모델
│   ├── database.py        # DB 연결
│   └── wireguard_manager.py # WireGuard 제어
├── client-setup/          # 클라이언트 설정 스크립트
├── monitoring/            # 모니터링 도구
├── docker-compose.yml     # 프로덕션 설정
├── docker-compose.local.yml # 로컬 테스트 설정
└── deploy.sh             # 배포 스크립트
```

## 🔧 주요 기능

- ✅ 자동 키 생성 및 배포
- ✅ RESTful API로 노드 관리
- ✅ 동적 IP 할당
- ✅ 실시간 연결 상태 모니터링
- ✅ Docker 기반 쉬운 배포
- ✅ NAT/방화벽 우회

## 🔐 보안

- API 토큰 기반 인증
- WireGuard의 강력한 암호화
- 자동 키 순환 지원
- 최소 권한 원칙 적용

## 📊 모니터링

```bash
# 상태 확인
python3 monitoring/vpn-status.py --watch

# API로 조회
curl -H "Authorization: Bearer $API_TOKEN" http://localhost:8090/nodes
```

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!