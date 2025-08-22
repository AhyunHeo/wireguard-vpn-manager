#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 스크립트
기존 테이블에 새로운 컬럼 추가
"""

import psycopg2
from psycopg2 import sql
import os
import sys

# 데이터베이스 연결 정보
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vpn:vpnpass@postgres:5432/vpndb")

def parse_database_url(url):
    """DATABASE_URL 파싱"""
    # postgresql://user:password@host:port/database
    url = url.replace("postgresql://", "")
    auth, host_db = url.split("@")
    user, password = auth.split(":")
    host_port, database = host_db.split("/")
    host, port = host_port.split(":")
    
    return {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password
    }

def migrate_database():
    """데이터베이스 마이그레이션 실행"""
    
    db_config = parse_database_url(DATABASE_URL)
    
    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("데이터베이스 연결 성공")
        
        # 현재 테이블 구조 확인
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'nodes'
        """)
        existing_columns = [col[0] for col in cursor.fetchall()]
        print(f"현재 컬럼: {existing_columns}")
        
        # 새로운 컬럼 추가 (이미 존재하면 스킵)
        columns_to_add = [
            ("description", "VARCHAR(255)"),
            ("central_server_ip", "VARCHAR(50)"),
            ("docker_env_vars", "TEXT")
        ]
        
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE nodes 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    print(f"✓ 컬럼 추가됨: {column_name}")
                except psycopg2.errors.DuplicateColumn:
                    print(f"- 컬럼 이미 존재: {column_name}")
                    conn.rollback()
                    continue
            else:
                print(f"- 컬럼 이미 존재: {column_name}")
        
        # 변경사항 커밋
        conn.commit()
        print("\n✅ 데이터베이스 마이그레이션 완료!")
        
        # 업데이트된 테이블 구조 확인
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'nodes'
            ORDER BY ordinal_position
        """)
        
        print("\n업데이트된 테이블 구조:")
        for col_name, col_type in cursor.fetchall():
            print(f"  - {col_name}: {col_type}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ 데이터베이스 에러: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=== VPN Manager 데이터베이스 마이그레이션 ===\n")
    migrate_database()