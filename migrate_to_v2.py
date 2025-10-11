#!/usr/bin/env python3
"""
Database migration script for eCommerce platform v2.0
Migrates existing data to new multi-vendor schema
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import DATABASE_URL
from app import models

def migrate_database():
    """Migrate existing database to new schema"""
    
    print("🚀 Starting eCommerce v2.0 database migration...")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Step 1: Create all new tables
        print("📋 Creating new database tables...")
        models.Base.metadata.create_all(bind=engine)
        print("✅ New tables created successfully!")
        
        # Step 2: Create default admin user
        print("👤 Creating default admin user...")
        from app.auth import get_password_hash
        
        admin_user = models.User(
            email="admin@ecommerce.com",
            username="admin",
            full_name="Administrator",
            phone="+91-9999999999",
            role=models.UserRole.ADMIN,
            hashed_password=get_password_hash("admin123"[:72]),  # Truncate to 72 bytes
            is_active=True,
            is_verified=True
        )
        
        # Check if admin already exists
        existing_admin = db.query(models.User).filter(models.User.email == "admin@ecommerce.com").first()
        if not existing_admin:
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("✅ Admin user created! Email: admin@ecommerce.com, Password: admin123")
        else:
            admin_user = existing_admin
            print("ℹ️  Admin user already exists")
        
        # Step 3: Create default vendor
        print("🏪 Creating default vendor profile...")
        
        vendor_user = models.User(
            email="saptnova@vendor.com",
            username="saptnova",
            full_name="SAPTNOVA Healthcare",
            phone="+91-9876543210",
            role=models.UserRole.VENDOR,
            hashed_password=get_password_hash("vendor123"[:72]),  # Truncate to 72 bytes
            is_active=True,
            is_verified=True
        )
        
        # Check if vendor user already exists
        existing_vendor_user = db.query(models.User).filter(models.User.email == "saptnova@vendor.com").first()
        if not existing_vendor_user:
            db.add(vendor_user)
            db.commit()
            db.refresh(vendor_user)
        else:
            vendor_user = existing_vendor_user
        
        # Create vendor profile
        existing_vendor = db.query(models.Vendor).filter(models.Vendor.user_id == vendor_user.id).first()
        if not existing_vendor:
            vendor_profile = models.Vendor(
                user_id=vendor_user.id,
                business_name="SAPTNOVA Healthcare Pvt Ltd",
                business_description="Leading provider of Ayurvedic and herbal healthcare products",
                business_email="business@saptnova.com",
                business_phone="+91-9876543210",
                gst_number="GST123456789",
                pan_number="PAN123456",
                business_address="123 Healthcare Street, Wellness City, India",
                is_verified=True,
                is_active=True,
                commission_rate=10.0
            )
            db.add(vendor_profile)
            db.commit()
            db.refresh(vendor_profile)
            print("✅ Default vendor created! Email: saptnova@vendor.com, Password: vendor123")
        else:
            vendor_profile = existing_vendor
            print("ℹ️  Vendor profile already exists")
        
        # Step 4: Create default categories
        print("📂 Creating default categories...")
        
        categories_data = [
            {"name": "General Health", "slug": "general-health", "description": "Products for overall health and wellness"},
            {"name": "Diabetes Care", "slug": "diabetes-care", "description": "Products for diabetes management"},
            {"name": "Heart Health", "slug": "heart-health", "description": "Cardiovascular health products"},
            {"name": "Liver Health", "slug": "liver-health", "description": "Liver care and detox products"},
            {"name": "Multi Vitamins", "slug": "multi-vitamins", "description": "Vitamin and mineral supplements"},
            {"name": "Ayurvedic", "slug": "ayurvedic", "description": "Traditional Ayurvedic medicines"},
            {"name": "Herbal", "slug": "herbal", "description": "Natural herbal products"}
        ]
        
        created_categories = {}
        for cat_data in categories_data:
            existing_cat = db.query(models.Category).filter(models.Category.slug == cat_data["slug"]).first()
            if not existing_cat:
                category = models.Category(**cat_data)
                db.add(category)
                db.commit()
                db.refresh(category)
                created_categories[cat_data["slug"]] = category
            else:
                created_categories[cat_data["slug"]] = existing_cat
        
        print(f"✅ Created {len(created_categories)} categories")
        
        # Step 5: Add missing columns to existing products table
        print("🔧 Updating existing products table schema...")
        
        # Add new columns if they don't exist
        try:
            # Core new columns
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS vendor_id INTEGER"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id INTEGER"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS slug VARCHAR"))
            
            # Product details
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS short_description TEXT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS specifications JSONB"))
            
            # Pricing
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS price FLOAT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS compare_price FLOAT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS cost_price FLOAT"))
            
            # Inventory
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 100"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS low_stock_threshold INTEGER DEFAULT 10"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS track_inventory BOOLEAN DEFAULT TRUE"))
            
            # Physical attributes
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS weight FLOAT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS dimensions JSONB"))
            
            # SEO & Marketing
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_title VARCHAR"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_description TEXT"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS tags JSONB"))
            
            # Status & Features
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_digital BOOLEAN DEFAULT FALSE"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS requires_shipping BOOLEAN DEFAULT TRUE"))
            
            # Timestamps
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"))
            
            db.commit()
            print("✅ Product table schema updated")
        except Exception as e:
            print(f"ℹ️  Schema update note: {e}")
        
        # Step 6: Migrate existing products if any
        print("🛍️  Migrating existing products...")
        
        # Check if there are old products to migrate
        old_products = db.execute(text("""
            SELECT * FROM products 
            WHERE vendor_id IS NULL OR category_id IS NULL
            LIMIT 10
        """)).fetchall()
        
        migrated_count = 0
        for old_product in old_products:
            try:
                # Update old product with vendor and category
                db.execute(text("""
                    UPDATE products 
                    SET vendor_id = :vendor_id, 
                        category_id = :category_id,
                        sku = :sku,
                        slug = :slug,
                        price = COALESCE(mrp, 0),
                        compare_price = COALESCE(old_mrp, mrp),
                        short_description = tagline,
                        description = dosage,
                        status = 'active',
                        stock_quantity = 100,
                        updated_at = NOW()
                    WHERE id = :product_id
                """), {
                    'vendor_id': vendor_profile.id,
                    'category_id': created_categories['general-health'].id,
                    'sku': old_product.product_id or f"SKU-{old_product.id}",
                    'slug': (old_product.name or f"product-{old_product.id}").lower().replace(' ', '-'),
                    'product_id': old_product.id
                })
                migrated_count += 1
            except Exception as e:
                print(f"⚠️  Warning: Could not migrate product {old_product.id}: {e}")
        
        db.commit()
        print(f"✅ Migrated {migrated_count} existing products")
        
        # Step 7: Create sample new products
        print("🆕 Creating sample products...")
        
        sample_products = [
            {
                "vendor_id": vendor_profile.id,
                "category_id": created_categories['diabetes-care'].id,
                "sku": "DIAB-001",
                "name": "DiabetoCare Plus",
                "slug": "diabetocare-plus",
                "short_description": "Advanced diabetes management supplement",
                "description": "Comprehensive formula for blood sugar management with natural ingredients",
                "price": 899.0,
                "compare_price": 1099.0,
                "stock_quantity": 50,
                "is_featured": True,
            },
            {
                "vendor_id": vendor_profile.id,
                "category_id": created_categories['heart-health'].id,
                "sku": "HEART-001",
                "name": "CardioShield",
                "slug": "cardioshield",
                "short_description": "Heart health protection formula",
                "description": "Natural ingredients to support cardiovascular health and circulation",
                "price": 1299.0,
                "compare_price": 1499.0,
                "stock_quantity": 30,
                "is_featured": True,
            }
        ]
        
        for product_data in sample_products:
            existing_product = db.query(models.Product).filter(models.Product.sku == product_data["sku"]).first()
            if not existing_product:
                product = models.Product(**product_data)
                db.add(product)
                db.commit()
                db.refresh(product)
                
                # Add sample images
                sample_image = models.ProductImage(
                    product_id=product.id,
                    image_url=f"/images/{product.slug}.jpg",
                    alt_text=product.name,
                    is_primary=True
                )
                db.add(sample_image)
        
        db.commit()
        print("✅ Sample products created")
        
        # Step 8: Create sample customer
        print("👥 Creating sample customer...")
        
        customer = models.User(
            email="customer@test.com",
            username="customer",
            full_name="Test Customer",
            phone="+91-9123456789",
            role=models.UserRole.CUSTOMER,
            hashed_password=get_password_hash("customer123"[:72]),  # Truncate to 72 bytes
            is_active=True,
            is_verified=True
        )
        
        existing_customer = db.query(models.User).filter(models.User.email == "customer@test.com").first()
        if not existing_customer:
            db.add(customer)
            db.commit()
            db.refresh(customer)
            
            # Add sample address
            address = models.Address(
                user_id=customer.id,
                title="Home",
                full_name="Test Customer",
                phone="+91-9123456789",
                address_line_1="123 Test Street",
                address_line_2="Test Area",
                city="Mumbai",
                state="Maharashtra",
                postal_code="400001",
                is_default=True
            )
            db.add(address)
            db.commit()
            print("✅ Sample customer created! Email: customer@test.com, Password: customer123")
        else:
            print("ℹ️  Sample customer already exists")
        
        print("\n🎉 Database migration completed successfully!")
        print("\n📋 Summary:")
        print("- ✅ New multi-vendor schema created")
        print("- 👤 Admin user: admin@ecommerce.com / admin123")
        print("- 🏪 Vendor user: saptnova@vendor.com / vendor123")  
        print("- 👥 Customer user: customer@test.com / customer123")
        print(f"- 📂 {len(created_categories)} categories created")
        print(f"- 🛍️  {migrated_count} products migrated")
        print("- 🆕 Sample products added")
        print("\n🚀 Your eCommerce v2.0 platform is ready!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()