"""
Database migration: Add Razorpay payment fields to orders table
Run this script to add payment integration fields
"""

from sqlalchemy import create_engine, text
import os

# Try to load environment variables, but use default if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin@localhost:5432/saptnova_db")

def migrate_add_payment_fields():
    """Add Razorpay payment fields to orders table"""
    
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        """
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR(255);
        """,
        """
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR(255);
        """,
        """
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS razorpay_signature VARCHAR(500);
        """
    ]
    
    try:
        with engine.connect() as conn:
            for migration_sql in migrations:
                print(f"Executing: {migration_sql.strip()[:50]}...")
                conn.execute(text(migration_sql))
                conn.commit()
                print("✅ Success")
            
        print("\n🎉 All migrations completed successfully!")
        print("New columns added to orders table:")
        print("  - razorpay_order_id")
        print("  - razorpay_payment_id")
        print("  - razorpay_signature")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("Starting database migration...")
    print("Adding Razorpay payment fields to orders table\n")
    migrate_add_payment_fields()
