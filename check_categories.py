#!/usr/bin/env python3
"""Check categories in database"""
import sys
sys.path.insert(0, '/Users/admin/Documents/eCommerce/backend')

from app.database import SessionLocal
from app.models import Category

def main():
    db = SessionLocal()
    try:
        categories = db.query(Category).all()
        print(f"\n{'='*60}")
        print(f"Total Categories: {len(categories)}")
        print(f"{'='*60}\n")
        
        for cat in categories:
            print(f"ID: {cat.id}")
            print(f"Name: {cat.name}")
            print(f"Slug: {cat.slug}")
            print(f"Is Active: {cat.is_active}")
            print(f"Sort Order: {cat.sort_order}")
            print("-" * 60)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
