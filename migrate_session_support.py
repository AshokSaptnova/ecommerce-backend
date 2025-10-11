#!/usr/bin/env python3
"""Database migration script to add session-based cart and order support."""

import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


def _migrate_sqlite(db_path: Path) -> None:
    """Add required columns and tables for SQLite deployments."""
    print(f"Migrating SQLite database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Adding session support to orders table...")

        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1] for col in cursor.fetchall()}

        if "session_id" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN session_id TEXT")
            print("✅ Added session_id column to orders")

        if "customer_email" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN customer_email TEXT")
            print("✅ Added customer_email column to orders")

        if "customer_name" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT")
            print("✅ Added customer_name column to orders")

        if "customer_phone" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN customer_phone TEXT")
            print("✅ Added customer_phone column to orders")

        if "payment_method" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
            print("✅ Added payment_method column to orders")

        print("Creating session_cart table if missing...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_cart_session_id ON session_cart(session_id)"
        )
        print("✅ Session cart support ready for SQLite")

        conn.commit()
        print("🎉 SQLite migration completed successfully!")

    except Exception as exc:  # pragma: no cover - log and bubble up
        print(f"❌ SQLite migration error: {exc}")
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_postgres(database_url: str) -> None:
    """Apply session cart/order schema updates for PostgreSQL deployments."""
    print(f"Migrating PostgreSQL database at: {database_url}")

    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            print("Ensuring orders table supports guest checkout fields...")
            connection.execute(text("ALTER TABLE orders ALTER COLUMN user_id DROP NOT NULL"))
            connection.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS session_id VARCHAR(255)")
            )
            connection.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_email VARCHAR(255)")
            )
            connection.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255)")
            )
            connection.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_phone VARCHAR(50)")
            )
            connection.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id)")
            )

        print("Ensuring session_cart table exists...")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS session_cart (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        product_id INTEGER NOT NULL REFERENCES products(id),
                        quantity INTEGER NOT NULL DEFAULT 1,
                        added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_session_cart_session_id ON session_cart(session_id)"
                )
            )

        print("🎉 PostgreSQL migration completed successfully!")

    except SQLAlchemyError as exc:  # pragma: no cover - log for visibility
        print(f"❌ PostgreSQL migration error: {exc}")
        raise
    finally:
        engine.dispose()


def migrate_database() -> None:
    """Detect database backend and apply migration."""
    if load_dotenv:
        load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if database_url and database_url.startswith("postgresql"):
        _migrate_postgres(database_url)
    else:
        db_path = Path(__file__).parent / "ecommerce.db"
        _migrate_sqlite(db_path)


if __name__ == "__main__":
    migrate_database()