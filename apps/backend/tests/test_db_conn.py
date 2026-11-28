import os
import sys
from pathlib import Path

import psycopg


def load_env(file_path=".env"):
    """
    Meticulously load environment variables from a .env file.
    Avoids dependency on potentially conflicted 'decouple' package.
    """
    env_path = Path(file_path)
    if not env_path.exists():
        print(f"Warning: {file_path} not found. Using system environment variables.")
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip().strip("'").strip('"')
                os.environ[key.strip()] = value

def test_database_connection():
    """
    Meticulously verify the database connection using environment variables.
    """
    # Ensure .env is loaded
    load_env()

    print("\n" + "="*60)
    print("📊 DATABASE CONNECTION STATUS REPORT")
    print("="*60)

    try:
        # Retrieve configuration
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")

        if not all([db_name, db_user, db_password]):
            missing = [k for k, v in {"DB_NAME": db_name, "DB_USER": db_user, "DB_PASSWORD": db_password}.items() if not v]
            print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
            sys.exit(1)

        print(f"🔹 Target   : {db_host}:{db_port}/{db_name}")
        print(f"🔹 User     : {db_user}")

        # Construct connection string
        # Using connect_timeout=5 to prevent hanging
        conn_info = (
            f"dbname={db_name} "
            f"user={db_user} "
            f"password={db_password} "
            f"host={db_host} "
            f"port={db_port} "
            f"connect_timeout=5"
        )

        print("🔄 Attempting connection...")

        with psycopg.connect(conn_info) as conn:
            # Connection metadata
            status = conn.info.status
            print(f"✅ Status   : {status} (CONNECTION_OK)")

            with conn.cursor() as cur:
                # 1. Server Version
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"🛡️  Server   : {version.split(',')[0]}")

                # 2. Session Info
                cur.execute("SELECT current_database(), current_user, inet_client_addr(), inet_server_addr();")
                db_actual, user_actual, client_addr, server_addr = cur.fetchone()
                print(f"📁 Database : {db_actual}")
                print(f"👤 Auth User: {user_actual}")
                print(f"🌐 Topology : Client({client_addr or 'local'}) -> Server({server_addr or 'local'})")

                # 3. Latency Check
                cur.execute("SELECT now();")
                db_time = cur.fetchone()[0]
                print(f"🕒 DB Time  : {db_time}")

        print("="*60)
        print("🎉 [SUCCESS] Database connectivity is optimal.")
        print("="*60 + "\n")

    except psycopg.OperationalError as e:
        print("\n" + "!"*60)
        print("🚨 [FAILURE] CONNECTION ERROR")
        print("!"*60)
        print(f"Detail: {e}")
        print("!"*60 + "\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 [CRITICAL] Unexpected error: {type(e).__name__}")
        print(f"Detail: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_database_connection()
