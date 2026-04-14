"""
backend/scripts/wait_for_db.py
───────────────────────────────
Standard health-check script to wait for the database to be reachable.
Retries every 2 seconds until successful or timeout (60s).
Useful for Docker / Azure startup sequences.
"""
import time
import sys
import os
from sqlalchemy import create_engine, text

# Add backend directory to sys.path to import core.config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Priority 1: Check os.environ directly (standard for Docker/Azure)
DATABASE_URL = os.getenv("DATABASE_URL")

# Priority 2: Fallback to core.config only if needed (handles local .env loading)
if not DATABASE_URL:
    try:
        from core.config import settings
        DATABASE_URL = getattr(settings, "DATABASE_URL", None)
    except Exception:
        # If settings initialization fails (e.g. ValidationError), we just move on
        # and handle the missing URL in wait_for_db()
        pass

def wait_for_db():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not found in environment variables.")
        print("Please ensure you are providing the database connection string at runtime.")
        print("Example: docker run -e DATABASE_URL='...' ...")
        sys.exit(1)

    print(f"Waiting for database at: {DATABASE_URL.split('@')[-1]}")
    
    # Handle PostgreSQL scheme normalization if needed
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)

    engine = create_engine(url)
    
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Database is READY!")
                return
        except Exception as e:
            print(f"Database not ready yet (Attempt {i+1}/{max_retries})...")
            print(f"Error: {str(e)}")
            time.sleep(retry_interval)
            
    print("CRITICAL: Database connection timed out!")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()
