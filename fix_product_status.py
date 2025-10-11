#!/usr/bin/env python3
"""
Fix ProductStatus enum values in database
"""
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

def fix_product_status_values():
    """Fix product status values to match enum expectations"""
    engine = create_engine(DATABASE_URL)
    
    print("🔧 Fixing product status values...")
    
    with engine.connect() as connection:
        # Start transaction
        trans = connection.begin()
        
        try:
            # Update all product status values to uppercase
            connection.execute(
                text("UPDATE products SET status = UPPER(status) WHERE status IS NOT NULL")
            )
            
            # Check what values we have now
            result = connection.execute(
                text("SELECT DISTINCT status FROM products")
            )
            statuses = [row[0] for row in result]
            print(f"✅ Current product status values: {statuses}")
            
            trans.commit()
            print("🎉 Product status values fixed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Error fixing product status values: {e}")
            raise

if __name__ == "__main__":
    fix_product_status_values()