#!/bin/bash

echo "🚀 Installing eCommerce v2.0 Dependencies..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created and activated"
fi

# Install core FastAPI dependencies
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0

# Install database dependencies
pip install sqlalchemy==2.0.23
pip install psycopg2-binary==2.9.9
pip install alembic==1.12.1

# Install authentication and security
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install python-multipart==0.0.6

# Install configuration and validation
pip install python-dotenv==1.0.0
pip install pydantic==2.5.0
pip install pydantic-settings==2.0.3
pip install email-validator==2.1.0

# Install additional utilities
pip install python-slugify==8.0.1
pip install Pillow==10.1.0
pip install requests==2.31.0

echo "✅ All dependencies installed successfully!"
echo "🏃 Run the migration script next: python migrate_to_v2.py"