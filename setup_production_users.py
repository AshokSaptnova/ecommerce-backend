"""
Script to create initial admin and vendor users for production
Run this once after deployment to set up your first users
"""
import os
from app.database import SessionLocal
from app.models import User, Vendor
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user():
    """Create an admin user"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("❌ Admin user already exists!")
            return False
        
        admin = User(
            username="admin",
            email="admin@ecommerce.com",
            hashed_password=pwd_context.hash("admin123"),
            role="ADMIN",
            full_name="Admin User"
        )
        db.add(admin)
        db.commit()
        print("✅ Admin user created successfully!")
        print("   Username: admin")
        print("   Password: admin123")
        return True
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_vendor_user():
    """Create a vendor user"""
    db = SessionLocal()
    try:
        # Check if vendor already exists
        existing_vendor = db.query(User).filter(User.username == "vendor1").first()
        if existing_vendor:
            print("❌ Vendor user already exists!")
            return False
        
        vendor_user = User(
            username="vendor1",
            email="vendor1@example.com",
            hashed_password=pwd_context.hash("vendor123"),
            role="VENDOR",
            full_name="Test Vendor"
        )
        db.add(vendor_user)
        db.commit()
        
        vendor = Vendor(
            user_id=vendor_user.id,
            store_name="Test Store",
            description="Test vendor store",
            contact_email="vendor1@example.com"
        )
        db.add(vendor)
        db.commit()
        
        print("✅ Vendor user created successfully!")
        print("   Username: vendor1")
        print("   Password: vendor123")
        return True
    except Exception as e:
        print(f"❌ Error creating vendor: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Creating Production Users")
    print("=" * 50)
    print()
    
    create_admin_user()
    print()
    create_vendor_user()
    
    print()
    print("=" * 50)
    print("⚠️  IMPORTANT: Change these default passwords after first login!")
    print("=" * 50)
