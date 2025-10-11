#!/usr/bin/env python3
"""
Create Vendor User Script
Creates a vendor user account with vendor profile for testing the vendor panel.
"""

import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal, engine
from app.models import User, Vendor, UserRole, Base
from app.auth import get_password_hash

def create_vendor_user(email, password, business_name, contact_number, address=""):
    """
    Create a vendor user with vendor profile
    
    Args:
        email: Vendor email address
        password: Vendor password
        business_name: Business/store name
        contact_number: Contact phone number
        address: Business address (optional)
    """
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return False
        
        # Create vendor user
        vendor_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.VENDOR,
            is_active=True
        )
        db.add(vendor_user)
        db.commit()
        db.refresh(vendor_user)
        
        print(f"✅ Created vendor user: {email}")
        
        # Create vendor profile
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name=business_name,
            contact_email=email,
            contact_number=contact_number,
            address=address if address else f"Address for {business_name}",
            is_active=True
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        
        print(f"✅ Created vendor profile: {business_name}")
        print(f"\n📋 Login Credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n🏪 Store: {business_name}")
        print(f"   Vendor ID: {vendor.id}")
        print(f"   Status: {'Active' if vendor.is_active else 'Inactive'}")
        print(f"\n🌐 Access the vendor panel at: http://localhost:3000/vendor")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating vendor: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_sample_vendors():
    """Create sample vendor accounts for testing"""
    print("=" * 60)
    print("Creating Sample Vendor Accounts")
    print("=" * 60)
    print()
    
    vendors = [
        {
            "email": "vendor1@example.com",
            "password": "vendor123",
            "business_name": "Tech Gadgets Store",
            "contact_number": "+1-555-0101",
            "address": "123 Tech Street, Silicon Valley, CA 94025"
        },
        {
            "email": "vendor2@example.com",
            "password": "vendor123",
            "business_name": "Fashion Boutique",
            "contact_number": "+1-555-0102",
            "address": "456 Fashion Ave, New York, NY 10001"
        },
        {
            "email": "vendor3@example.com",
            "password": "vendor123",
            "business_name": "Home & Living",
            "contact_number": "+1-555-0103",
            "address": "789 Home Lane, Los Angeles, CA 90001"
        }
    ]
    
    success_count = 0
    for vendor_data in vendors:
        if create_vendor_user(**vendor_data):
            success_count += 1
        print()
    
    print("=" * 60)
    print(f"✅ Successfully created {success_count} out of {len(vendors)} vendor accounts")
    print("=" * 60)

def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("Vendor Account Creation Tool")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        create_sample_vendors()
    else:
        print("Create a single vendor account:")
        print("-" * 60)
        
        # Get vendor details
        email = input("Email address: ").strip()
        password = input("Password: ").strip()
        business_name = input("Business name: ").strip()
        contact_number = input("Contact number: ").strip()
        address = input("Address (optional): ").strip()
        
        print()
        print("Creating vendor account...")
        print()
        
        create_vendor_user(email, password, business_name, contact_number, address)
        
        print()
        print("=" * 60)
        print("Tip: Run with --sample flag to create 3 sample vendor accounts")
        print("     python create_vendor_user.py --sample")
        print("=" * 60)

if __name__ == "__main__":
    main()
