#!/usr/bin/env python3
import sys
sys.path.append('/Users/admin/Documents/eCommerce/backend')

from app.database import SessionLocal
from app.models import Product

db = SessionLocal()
try:
    products = db.query(Product).all()
    print('📊 Product Status Check:')
    print('=' * 70)
    for p in products[:10]:  # First 10 products
        status_value = p.status.value if hasattr(p.status, 'value') else p.status
        print(f'ID: {p.id:3d} | Name: {p.name[:35]:35s} | Status: {status_value}')
    print('=' * 70)
    print(f'Total products: {len(products)}')
    
    active_count = 0
    inactive_count = 0
    for p in products:
        status_value = p.status.value if hasattr(p.status, 'value') else p.status
        if status_value == 'active':
            active_count += 1
        elif status_value == 'inactive':
            inactive_count += 1
    
    print(f'Active: {active_count}')
    print(f'Inactive: {inactive_count}')
finally:
    db.close()
