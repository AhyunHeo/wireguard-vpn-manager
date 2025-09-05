-- 데이터베이스 마이그레이션: central_server_ip -> central_server_url
-- 실행: docker exec -i vpn-postgres psql -U vpn -d vpndb < migrate_central_url.sql

-- 1. central_server_url 컬럼이 없으면 추가
ALTER TABLE nodes 
ADD COLUMN IF NOT EXISTS central_server_url VARCHAR(255);

-- 2. 기존 central_server_ip 데이터가 있으면 마이그레이션
UPDATE nodes 
SET central_server_url = CONCAT('http://', central_server_ip, ':8000')
WHERE central_server_ip IS NOT NULL 
AND central_server_url IS NULL;

-- 3. 기본값 설정 (비어있는 경우)
UPDATE nodes 
SET central_server_url = 'http://192.168.0.88:8000'
WHERE central_server_url IS NULL;

-- 4. central_server_ip 컬럼 삭제 (선택사항 - 나중에 실행)
-- ALTER TABLE nodes DROP COLUMN IF EXISTS central_server_ip;

-- 5. 변경사항 확인
SELECT node_id, node_type, central_server_url FROM nodes;