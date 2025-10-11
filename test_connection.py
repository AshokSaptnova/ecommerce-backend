#!/usr/bin/env python3
"""
Database connection test script
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def test_connection():
    """Test PostgreSQL database connection"""
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin@localhost:5432/saptnova_db")
    
    print(f"🔍 Testing connection to: {DATABASE_URL}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connection successful!")
            print(f"📊 PostgreSQL version: {version}")
            
            # Test if tables exist
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"📋 Found tables: {', '.join(tables)}")
                
                # Count products
                try:
                    result = connection.execute(text("SELECT COUNT(*) FROM products"))
                    count = result.fetchone()[0]
                    print(f"🛍️  Products in database: {count}")
                except:
                    print("ℹ️  Products table exists but may be empty")
            else:
                print("⚠️  No tables found. Run setup_db.py to initialize.")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure PostgreSQL is running: brew services start postgresql")
        print("2. Check if database exists: psql -U admin -d saptnova_db")
        print("3. Create database if needed: createdb -U admin saptnova_db")
        print("4. Verify connection string in .env file")

if __name__ == "__main__":
    test_connection()