from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_, or_, asc, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from .. import models, schemas, crud, auth

router = APIRouter(prefix="/admin", tags=["admin-panel"])

# Dashboard Analytics
@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard_stats(
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get admin dashboard statistics"""
    
    # Basic counts
    total_users = db.query(models.User).count()
    total_vendors = db.query(models.Vendor).count()
    total_products = db.query(models.Product).count()
    total_orders = db.query(models.Order).count()
    active_vendors = db.query(models.Vendor).filter(models.Vendor.is_active == True).count()
    
    # Revenue calculations
    total_revenue = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.status.in_(["confirmed", "processing", "shipped", "delivered"])
    ).scalar() or 0
    
    # Recent orders (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.created_at >= thirty_days_ago
    ).scalar() or 0
    
    recent_revenue = db.query(func.sum(models.Order.total_amount)).filter(
        and_(
            models.Order.created_at >= thirty_days_ago,
            models.Order.status.in_(["confirmed", "processing", "shipped", "delivered"])
        )
    ).scalar() or 0
    
    # Top selling products
    top_products = db.query(
        models.Product.name,
        func.sum(models.OrderItem.quantity).label('total_sold')
    ).join(models.OrderItem).group_by(models.Product.id, models.Product.name)\
     .order_by(func.sum(models.OrderItem.quantity).desc()).limit(5).all()
    
    # Vendor performance
    vendor_stats = db.query(
        models.Vendor.business_name,
        func.count(models.Product.id).label('product_count'),
        func.sum(models.Order.total_amount).label('revenue')
    ).outerjoin(models.Product, models.Vendor.id == models.Product.vendor_id)\
     .outerjoin(models.OrderItem, models.Product.id == models.OrderItem.product_id)\
     .outerjoin(models.Order, models.OrderItem.order_id == models.Order.id)\
     .group_by(models.Vendor.id, models.Vendor.business_name)\
     .order_by(func.sum(models.Order.total_amount).desc()).limit(5).all()
    
    return {
        "overview": {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "active_vendors": active_vendors,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue)
        },
        "recent_performance": {
            "orders_last_30_days": recent_orders,
            "revenue_last_30_days": float(recent_revenue)
        },
        "top_products": [
            {"name": name, "total_sold": int(sold)} 
            for name, sold in top_products
        ],
        "vendor_performance": [
            {
                "business_name": name,
                "product_count": int(count or 0),
                "revenue": float(revenue or 0)
            }
            for name, count, revenue in vendor_stats
        ]
    }

# User Management
@router.get("/orders", response_model=schemas.OrderListResponse)
def get_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: Optional[schemas.OrderStatus] = None,
    payment_status: Optional[schemas.PaymentStatus] = None,
    user_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    date_from: Optional[str] = Query(None, description="Filter orders created on or after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter orders created on or before this date (YYYY-MM-DD)"),
    sort_by: str = Query("created_at", pattern="^(created_at|total_amount|status|payment_status)$"),
    sort_order: schemas.SortOrder = schemas.SortOrder.DESC,
    db: Session = Depends(auth.get_db)
):
    """Get all users with filtering options"""
    query = db.query(models.User)
    def _parse_date(value: Optional[str], *, inclusive_end: bool = False) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
            if inclusive_end:
                parsed = parsed + timedelta(days=1)
            return parsed
        except ValueError:
            return None

    filters = []

    if status:
        filters.append(models.Order.status == status)
    if payment_status:
        filters.append(models.Order.payment_status == payment_status)
    if user_id:
        filters.append(models.Order.user_id == user_id)
    if vendor_id:
        filters.append(
            models.Order.items.any(
                models.OrderItem.product.has(models.Product.vendor_id == vendor_id)
            )
        )

    start_date = _parse_date(date_from)
    end_date = _parse_date(date_to, inclusive_end=True)

    if start_date:
        filters.append(models.Order.created_at >= start_date)
    if end_date:
        filters.append(models.Order.created_at < end_date)

    base_query = db.query(models.Order).filter(*filters)

    total = base_query.order_by(None).count()

    status_counts = dict(
        db.query(models.Order.status, func.count(models.Order.id))
        .filter(*filters)
        .group_by(models.Order.status)
        .all()
    )

    payment_counts = dict(
        db.query(models.Order.payment_status, func.count(models.Order.id))
        .filter(*filters)
        .group_by(models.Order.payment_status)
        .all()
    )

    data_query = base_query.options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.user)
    )

    sort_columns = {
        "created_at": models.Order.created_at,
        "total_amount": models.Order.total_amount,
        "status": models.Order.status,
        "payment_status": models.Order.payment_status
    }
    sort_column = sort_columns.get(sort_by, models.Order.created_at)
    sort_expression = asc(sort_column) if sort_order == schemas.SortOrder.ASC else desc(sort_column)

    offset = (page - 1) * page_size
    orders = data_query.order_by(sort_expression, models.Order.id.asc()).offset(offset).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size if total else 0

    return {
        "items": orders,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": total_pages,
            "status_counts": {k.value if hasattr(k, "value") else k: v for k, v in status_counts.items()},
            "payment_status_counts": {k.value if hasattr(k, "value") else k: v for k, v in payment_counts.items()}
        }
    }
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Delete a user (admin only)"""
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == schemas.UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

# Vendor Management
@router.get("/vendors", response_model=List[schemas.Vendor])
def get_all_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_verified: bool = None,
    is_active: bool = None,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get all vendors with filtering"""
    query = db.query(models.Vendor)
    
    if is_verified is not None:
        query = query.filter(models.Vendor.is_verified == is_verified)
    if is_active is not None:
        query = query.filter(models.Vendor.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()

@router.put("/vendors/{vendor_id}/verify")
def verify_vendor(
    vendor_id: int,
    request_data: dict,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Verify or unverify a vendor"""
    vendor = crud.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    vendor.is_verified = request_data.get('is_verified', vendor.is_verified)
    db.commit()
    db.refresh(vendor)
    
    return {"message": f"Vendor {'verified' if vendor.is_verified else 'unverified'} successfully"}

@router.put("/vendors/{vendor_id}/status")
def update_vendor_status(
    vendor_id: int,
    request_data: dict,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Activate or deactivate a vendor"""
    vendor = crud.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    vendor.is_active = request_data.get('is_active', vendor.is_active)
    db.commit()
    db.refresh(vendor)
    
    return {"message": f"Vendor {'activated' if vendor.is_active else 'deactivated'} successfully"}

@router.post("/vendors", response_model=schemas.Vendor)
def create_vendor_admin(
    vendor_data: schemas.VendorCreate,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new vendor (admin only)"""
    # Create a user for the vendor first
    from ..auth import get_password_hash
    import secrets
    import string
    
    # Generate a temporary password
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(12))
    
    # Create user with vendor role
    user_data = models.User(
        email=vendor_data.business_email or f"vendor_{secrets.randbelow(10000)}@temp.com",
        hashed_password=get_password_hash(temp_password),
        role=models.UserRole.VENDOR,
        is_active=True
    )
    
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    
    # Create vendor profile
    db_vendor = models.Vendor(
        user_id=user_data.id,
        business_name=vendor_data.business_name,
        business_description=vendor_data.business_description,
        business_email=vendor_data.business_email,
        business_phone=vendor_data.business_phone,
        gst_number=vendor_data.gst_number,
        pan_number=vendor_data.pan_number,
        business_address=vendor_data.business_address,
        logo_url=vendor_data.logo_url,
        is_verified=False,
        is_active=True,
        commission_rate=10.0  # Default commission rate
    )
    
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    return db_vendor

@router.put("/vendors/{vendor_id}", response_model=schemas.Vendor)
def update_vendor_admin(
    vendor_id: int,
    vendor_data: schemas.VendorUpdate,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update vendor information (admin only)"""
    vendor = crud.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Update vendor fields
    for field, value in vendor_data.dict(exclude_unset=True).items():
        setattr(vendor, field, value)
    
    db.commit()
    db.refresh(vendor)
    
    return vendor

@router.delete("/vendors/{vendor_id}")
def delete_vendor_admin(
    vendor_id: int,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Delete a vendor and associated user (admin only)"""
    vendor = crud.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Check if vendor has products
    products_count = db.query(models.Product).filter(models.Product.vendor_id == vendor_id).count()
    if products_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete vendor with {products_count} products. Remove or transfer products first."
        )
    
    # Check if vendor has orders
    orders_count = db.query(models.Order).join(models.OrderItem).join(models.Product).filter(
        models.Product.vendor_id == vendor_id
    ).count()
    if orders_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete vendor with {orders_count} orders. Archive the vendor instead."
        )
    
    # Get associated user
    user = db.query(models.User).filter(models.User.id == vendor.user_id).first()
    
    # Delete vendor
    db.delete(vendor)
    
    # Delete associated user if it exists
    if user:
        db.delete(user)
    
    db.commit()
    
    return {"message": "Vendor deleted successfully"}

# Product Management
@router.get("/products", response_model=List[schemas.Product])
def get_all_products_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: schemas.ProductStatus = None,
    vendor_id: int = None,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get all products for admin review"""
    query = db.query(models.Product)
    
    if status:
        query = query.filter(models.Product.status == status)
    if vendor_id:
        query = query.filter(models.Product.vendor_id == vendor_id)
    
    return query.offset(skip).limit(limit).all()

@router.put("/products/{product_id}/status")
def update_product_status(
    product_id: int,
    status: schemas.ProductStatus,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update product status (admin approval/rejection)"""
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.status = status
    db.commit()
    db.refresh(product)
    
    return {"message": f"Product status updated to {status.value}"}

# Order Management
@router.get("/orders", response_model=List[schemas.Order])
def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: schemas.OrderStatus = None,
    user_id: int = None,
    vendor_id: int = None,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get all orders with filtering"""
    query = db.query(models.Order).options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.user)
    )
    
    if status:
        query = query.filter(models.Order.status == status)
    if user_id:
        query = query.filter(models.Order.user_id == user_id)
    if vendor_id:
        # Filter orders that contain products from specific vendor
        query = query.join(models.OrderItem).join(models.Product).filter(
            models.Product.vendor_id == vendor_id
        )

    query = query.order_by(models.Order.id)
    return query.distinct(models.Order.id).offset(skip).limit(limit).all()

@router.put("/orders/{order_id}/status", response_model=schemas.Order)
def update_order_status_admin(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update order status (admin override)"""
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update the order status
    updated_order = crud.update_order_status(db, order_id, status_update.status)
    if not updated_order:
        raise HTTPException(status_code=500, detail="Failed to update order status")
    
    return updated_order

# Category Management
@router.post("/categories", response_model=schemas.Category)
def create_category_admin(
    category: schemas.CategoryCreate,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new category"""
    return crud.create_category(db=db, category=category)

@router.put("/categories/{category_id}")
def update_category_admin(
    category_id: int,
    category: schemas.CategoryUpdate,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update a category"""
    return crud.update_category(db=db, category_id=category_id, category=category)

@router.delete("/categories/{category_id}")
def delete_category_admin(
    category_id: int,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Delete a category"""
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has products
    products_count = db.query(models.Product).filter(models.Product.category_id == category_id).count()
    if products_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category with {products_count} products. Move products to another category first."
        )
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}

# Reports
@router.get("/reports/sales")
def get_sales_report(
    start_date: datetime = None,
    end_date: datetime = None,
    vendor_id: int = None,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Generate sales reports"""
    query = db.query(
        func.date(models.Order.created_at).label('date'),
        func.count(models.Order.id).label('order_count'),
        func.sum(models.Order.total_amount).label('revenue')
    ).filter(models.Order.status.in_(["confirmed", "processing", "shipped", "delivered"]))
    
    if start_date:
        query = query.filter(models.Order.created_at >= start_date)
    if end_date:
        query = query.filter(models.Order.created_at <= end_date)
    if vendor_id:
        query = query.join(models.OrderItem).join(models.Product).filter(
            models.Product.vendor_id == vendor_id
        )
    
    results = query.group_by(func.date(models.Order.created_at)).order_by(
        func.date(models.Order.created_at).desc()
    ).limit(30).all()
    
    return {
        "sales_data": [
            {
                "date": str(date),
                "order_count": int(count),
                "revenue": float(revenue or 0)
            }
            for date, count, revenue in results
        ]
    }

@router.get("/reports/inventory")
def get_inventory_report(
    low_stock_only: bool = False,
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Generate inventory reports"""
    query = db.query(models.Product).filter(models.Product.track_inventory == True)
    
    if low_stock_only:
        query = query.filter(models.Product.stock_quantity <= models.Product.low_stock_threshold)
    
    products = query.all()
    
    return {
        "inventory_items": [
            {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "low_stock_threshold": product.low_stock_threshold,
                "vendor_name": product.vendor.business_name,
                "status": product.status.value,
                "is_low_stock": product.stock_quantity <= product.low_stock_threshold
            }
            for product in products
        ]
    }

@router.get("/reports")
def get_reports_summary(
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get comprehensive reports summary for admin panel"""
    from datetime import datetime as dt
    
    # Parse dates
    start = dt.fromisoformat(start_date) if start_date else dt.utcnow() - timedelta(days=30)
    end = dt.fromisoformat(end_date) if end_date else dt.utcnow()
    
    # Sales Summary
    sales_query = db.query(
        func.count(models.Order.id).label('total_orders'),
        func.sum(models.Order.total_amount).label('total_revenue'),
        func.avg(models.Order.total_amount).label('avg_order_value')
    ).filter(
        and_(
            models.Order.created_at >= start,
            models.Order.created_at <= end,
            models.Order.status.in_(["confirmed", "processing", "shipped", "delivered"])
        )
    ).first()
    
    # Active customers
    active_customers = db.query(func.count(func.distinct(models.Order.user_id))).filter(
        and_(
            models.Order.created_at >= start,
            models.Order.created_at <= end
        )
    ).scalar() or 0
    
    # Vendor Performance
    vendor_performance = db.query(
        models.Vendor.id,
        models.Vendor.business_name,
        func.count(func.distinct(models.Product.id)).label('product_count'),
        func.sum(models.Order.total_amount).label('revenue')
    ).outerjoin(models.Product, models.Vendor.id == models.Product.vendor_id)\
     .outerjoin(models.OrderItem, models.Product.id == models.OrderItem.product_id)\
     .outerjoin(models.Order, 
                and_(
                    models.OrderItem.order_id == models.Order.id,
                    models.Order.created_at >= start,
                    models.Order.created_at <= end
                ))\
     .group_by(models.Vendor.id, models.Vendor.business_name)\
     .order_by(func.sum(models.Order.total_amount).desc())\
     .limit(10).all()
    
    # Product Analytics
    product_analytics = db.query(
        models.Product.id,
        models.Product.name,
        func.sum(models.OrderItem.quantity).label('units_sold'),
        func.sum(models.OrderItem.quantity * models.OrderItem.price).label('revenue')
    ).join(models.OrderItem)\
     .join(models.Order)\
     .filter(
         and_(
             models.Order.created_at >= start,
             models.Order.created_at <= end,
             models.Order.status.in_(["confirmed", "processing", "shipped", "delivered"])
         )
     )\
     .group_by(models.Product.id, models.Product.name)\
     .order_by(func.sum(models.OrderItem.quantity).desc())\
     .limit(10).all()
    
    return {
        "salesSummary": {
            "total_orders": int(sales_query.total_orders or 0),
            "total_revenue": float(sales_query.total_revenue or 0),
            "avg_order_value": float(sales_query.avg_order_value or 0),
            "active_customers": active_customers
        },
        "vendorPerformance": [
            {
                "id": v_id,
                "business_name": name,
                "product_count": int(p_count or 0),
                "revenue": float(revenue or 0)
            }
            for v_id, name, p_count, revenue in vendor_performance
        ],
        "productAnalytics": [
            {
                "id": p_id,
                "name": name,
                "units_sold": int(units or 0),
                "revenue": float(rev or 0)
            }
            for p_id, name, units, rev in product_analytics
        ]
    }

# System Settings
@router.get("/settings")
def get_system_settings(
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Get system settings"""
    # For now, return default settings
    # In production, these should be stored in a settings table
    return {
        "platform_name": "Multi-Vendor eCommerce",
        "platform_email": "admin@ecommerce.com",
        "currency": "INR",
        "tax_rate": 18,
        "commission_rate": 5,
        "auto_approve_vendors": False,
        "auto_approve_products": False,
        "maintenance_mode": False
    }

@router.put("/settings")
def update_system_settings(
    settings: Dict[str, Any],
    current_admin: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update system settings"""
    # For now, just return success
    # In production, save to database settings table
    return {
        "message": "Settings updated successfully",
        "settings": settings
    }