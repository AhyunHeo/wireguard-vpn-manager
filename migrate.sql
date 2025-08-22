-- VPN Manager 데이터베이스 마이그레이션
-- nodes 테이블에 새로운 컬럼 추가

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS description VARCHAR(255);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS central_server_ip VARCHAR(50);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS docker_env_vars TEXT;