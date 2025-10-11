#!/usr/bin/env python3
"""
Database setup and initialization script for PostgreSQL
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'admin',
        'database': 'postgres'  # Connect to default postgres database first
    }
    
    target_db = 'saptnova_db'
    
    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (target_db,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{target_db}"')
            print(f"✅ Database '{target_db}' created successfully!")
        else:
            print(f"ℹ️  Database '{target_db}' already exists.")
            
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Error creating database: {e}")
        sys.exit(1)

def initialize_tables():
    """Initialize database tables"""
    from app.database import engine
    from app.models import Base
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

def seed_sample_data():
    """Seed the database with sample products"""
    from app.database import SessionLocal
    from app.models import Product, Benefit, Ingredient
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_products = db.query(Product).count()
        if existing_products > 0:
            print(f"ℹ️  Database already contains {existing_products} products. Skipping seed.")
            return
            
        # Sample product data
        sample_product = Product(
            product_id="SAPTNOVA_001",
            name="SAPTNOVA",
            tagline="Standard prescription for General Fatigue, Weakness, Anemia, Frequent Illness, Malnutrition",
            category="General Health",
            type="Capsule",
            packing="60 Veg. Capsules & 20 Veg. Capsules",
            mrp=650,
            old_mrp=750,
            dosage="1-2 Capsule twice a day or as directed by the physician",
            image_url="/images/saptnova.jpg"
        )
        
        db.add(sample_product)
        db.commit()
        db.refresh(sample_product)
        
        # Add benefits
        benefits = [
            "Helps to Prevent Deficiency of Vitamins",
            "Rich Source of Iron, Improves Hemoglobin Level",
            "Maintain Normal function of Bones & Muscles",
            "Protect Body Tissues from Oxidative Damage"
        ]
        
        for benefit_text in benefits:
            benefit = Benefit(text=benefit_text, product_id=sample_product.id)
            db.add(benefit)
        
        # Add ingredients
        ingredients = [
            {"name": "Ashwagandha", "latin": "Withania somnifera", "quantity": "50 mg", 
             "description": "Adaptogenic herb that helps reduce stress, boost energy, and support immune resilience"},
            {"name": "Safed Musli", "latin": "Chlorophytum borivilianum", "quantity": "40 mg",
             "description": "Natural tonic that enhances stamina, physical strength, and immune function"},
            {"name": "Shatavari", "latin": "Asparagus racemosus", "quantity": "40 mg",
             "description": "Rejuvenative herb that supports hormonal balance and strengthens immunity"}
        ]
        
        for ing_data in ingredients:
            ingredient = Ingredient(
                name=ing_data["name"],
                latin=ing_data["latin"],
                quantity=ing_data["quantity"],
                description=ing_data["description"],
                product_id=sample_product.id
            )
            db.add(ingredient)
        
        db.commit()
        print("✅ Sample data seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Setting up PostgreSQL database...")
    
    # Step 1: Create database
    create_database_if_not_exists()
    
    # Step 2: Create tables
    initialize_tables()
    
    # Step 3: Seed sample data
    seed_sample_data()
    
    print("✅ Database setup completed successfully!")
    print("🎉 Your eCommerce application is ready to use!")