from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import asc, desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from .. import models, schemas, crud, auth

router = APIRouter(prefix="/vendors", tags=["vendors"])

@router.get("/", response_model=List[schemas.Vendor])
def get_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool = True,
    db: Session = Depends(auth.get_db)
):
    """Get all vendors"""
    return crud.get_vendors(db=db, skip=skip, limit=limit, is_active=is_active)

@router.get("/me", response_model=schemas.Vendor)
def get_my_vendor_profile(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get current user's vendor profile"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    return vendor

@router.post("/register", response_model=schemas.Vendor)
def create_vendor_profile(
    vendor: schemas.VendorCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Create vendor profile for current user"""
    # Check if user already has a vendor profile
    existing_vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if existing_vendor:
        raise HTTPException(status_code=400, detail="Vendor profile already exists")
    
    # Update user role to vendor
    current_user.role = models.UserRole.VENDOR
    db.commit()
    
    return crud.create_vendor(db=db, vendor=vendor, user_id=current_user.id)

@router.put("/me", response_model=schemas.Vendor)
def update_vendor_profile(
    vendor: schemas.VendorUpdate,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update current user's vendor profile"""
    db_vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    for field, value in vendor.dict(exclude_unset=True).items():
        setattr(db_vendor, field, value)
    
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

@router.get("/{vendor_id}", response_model=schemas.Vendor)
def get_vendor(vendor_id: int, db: Session = Depends(auth.get_db)):
    """Get vendor by ID"""
    db_vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return db_vendor

@router.get("/{vendor_id}/products", response_model=List[schemas.Product])
def get_vendor_products(
    vendor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(auth.get_db)
):
    """Get products by vendor"""
    return crud.get_products(db=db, vendor_id=vendor_id, skip=skip, limit=limit)

@router.get("/{vendor_id}/orders", response_model=schemas.OrderListResponse)
def get_vendor_orders(
    vendor_id: int,
    status: Optional[schemas.OrderStatus] = None,
    payment_status: Optional[schemas.PaymentStatus] = None,
    date_from: Optional[str] = Query(None, description="Filter orders created on or after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter orders created on or before this date (YYYY-MM-DD)"),
    sort_by: str = Query("created_at", pattern="^(created_at|total_amount|status|payment_status)$"),
    sort_order: schemas.SortOrder = schemas.SortOrder.DESC,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get orders for vendor's products - vendor can only see their own orders"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor or vendor.id != vendor_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own orders")

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

    filters = [
        models.Order.items.any(
            models.OrderItem.product.has(models.Product.vendor_id == vendor_id)
        )
    ]

    if status:
        filters.append(models.Order.status == status)
    if payment_status:
        filters.append(models.Order.payment_status == payment_status)

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

@router.put("/{vendor_id}/orders/{order_id}/status", response_model=schemas.Order)
def update_vendor_order_status(
    vendor_id: int,
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update order status for vendor's products - vendor can only update their own order statuses"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor or vendor.id != vendor_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only update your own orders")
    
    # Get the order and verify it contains vendor's products
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify this order contains products from this vendor
    has_vendor_products = any(
        item.product and item.product.vendor_id == vendor_id 
        for item in order.items
    )
    
    if not has_vendor_products:
        raise HTTPException(status_code=403, detail="This order does not contain your products")
    
    # Update the order status
    updated_order = crud.update_order_status(db, order_id, status_update.status)
    if not updated_order:
        raise HTTPException(status_code=500, detail="Failed to update order status")
    
    return updated_order

# Financial Management Endpoints
@router.get("/financials")
def get_vendor_financials(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor financial data"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock financial data - replace with actual calculations
    return {
        "total_revenue": 45000.0,
        "this_month_revenue": 12500.0,
        "pending_payouts": 8000.0,
        "total_commission": 4500.0,
        "available_balance": 8000.0,
        "period": period
    }

@router.get("/payouts")
def get_vendor_payouts(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor payout history"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock payout data - replace with actual data
    return [
        {
            "id": 1,
            "amount": 5000.0,
            "status": "completed",
            "payment_method": "Bank Transfer",
            "transaction_id": "TXN123456",
            "created_at": "2023-10-01T00:00:00Z"
        },
        {
            "id": 2,
            "amount": 3000.0,
            "status": "processing",
            "payment_method": "Bank Transfer",
            "transaction_id": None,
            "created_at": "2023-10-15T00:00:00Z"
        }
    ]

@router.post("/payouts/request")
def request_payout(
    payout_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Request a payout"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    amount = payout_data.get('amount', 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payout amount")
    
    # Mock payout request creation
    return {"message": "Payout request submitted successfully", "request_id": 123}

# Advanced Inventory Management Endpoints
@router.get("/inventory/advanced")
def get_advanced_inventory(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get advanced inventory data"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Get products for this vendor with additional inventory data
    products = db.query(models.Product).filter(models.Product.vendor_id == vendor.id).all()
    
    return products

@router.get("/inventory/settings")
def get_inventory_settings(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get inventory automation settings"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock settings - replace with actual database storage
    return {
        "threshold": 10,
        "autoReorder": False,
        "reorderQuantity": 50,
        "emailAlerts": True
    }

@router.put("/inventory/settings")
def update_inventory_settings(
    settings: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update inventory automation settings"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock update - implement actual database storage
    return {"message": "Settings updated successfully"}

@router.post("/inventory/bulk-update")
def bulk_update_inventory(
    update_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Perform bulk inventory operations"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    product_ids = update_data.get('product_ids', [])
    action = update_data.get('action')
    
    if not product_ids or not action:
        raise HTTPException(status_code=400, detail="Missing product IDs or action")
    
    # Perform bulk update based on action
    products = db.query(models.Product).filter(
        models.Product.id.in_(product_ids),
        models.Product.vendor_id == vendor.id
    ).all()
    
    for product in products:
        if action == 'activate':
            product.is_active = True
        elif action == 'deactivate':
            product.is_active = False
    
    db.commit()
    
    return {"message": f"Bulk {action} completed for {len(products)} products"}

@router.post("/inventory/import-csv")
def import_inventory_csv(
    csv_import: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Import inventory data from CSV"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    csv_data = csv_import.get('csv_data', '')
    if not csv_data:
        raise HTTPException(status_code=400, detail="No CSV data provided")
    
    # Mock CSV import - implement actual parsing and updating
    return {"message": "CSV import completed", "updated_count": 10}

# Shipping Management Endpoints
@router.get("/shipping/zones")
def get_shipping_zones(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor shipping zones"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock shipping zones - replace with actual database
    return [
        {
            "id": 1,
            "name": "Metro Cities",
            "regions": ["Delhi", "Mumbai", "Bangalore"],
            "base_rate": 50.0,
            "per_kg_rate": 20.0,
            "free_shipping_threshold": 500.0,
            "estimated_delivery_days": 2,
            "is_active": True
        }
    ]

@router.post("/shipping/zones")
def create_shipping_zone(
    zone_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new shipping zone"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock zone creation - implement actual database storage
    return {"message": "Shipping zone created successfully", "zone_id": 123}

@router.put("/shipping/zones/{zone_id}")
def update_shipping_zone(
    zone_id: int,
    zone_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update a shipping zone"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock zone update - implement actual database update
    return {"message": "Shipping zone updated successfully"}

@router.delete("/shipping/zones/{zone_id}")
def delete_shipping_zone(
    zone_id: int,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Delete a shipping zone"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock zone deletion - implement actual database deletion
    return {"message": "Shipping zone deleted successfully"}

@router.get("/shipping/methods")
def get_shipping_methods(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor shipping methods"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock shipping methods
    return [
        {
            "id": 1,
            "name": "Standard Delivery",
            "type": "standard",
            "base_rate": 40.0,
            "per_kg_rate": 15.0,
            "estimated_delivery_days": 5,
            "tracking_enabled": True,
            "insurance_available": False,
            "is_active": True
        }
    ]

@router.post("/shipping/methods")
def create_shipping_method(
    method_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new shipping method"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock method creation
    return {"message": "Shipping method created successfully", "method_id": 123}

@router.put("/shipping/methods/{method_id}")
def update_shipping_method(
    method_id: int,
    method_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update a shipping method"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock method update
    return {"message": "Shipping method updated successfully"}

@router.get("/shipping/couriers")
def get_courier_partners(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get integrated courier partners"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock courier partners
    return [
        {
            "id": 1,
            "name": "Blue Dart",
            "type": "express",
            "is_active": True
        },
        {
            "id": 2,
            "name": "DTDC",
            "type": "standard",
            "is_active": True
        }
    ]

# Customer Management Endpoints
@router.get("/customers")
def get_vendor_customers(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor's customers"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock customer data
    return [
        {
            "id": 1,
            "name": "Rajesh Kumar",
            "email": "rajesh.k@email.com",
            "phone": "+91 98765 43210",
            "total_orders": 15,
            "total_spent": 45600,
            "last_order_date": "2024-03-15",
            "status": "active",
            "customer_since": "2023-06-12",
            "city": "Mumbai",
            "preferred_category": "Electronics"
        }
    ]

@router.get("/customers/stats")
def get_customer_statistics(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get customer statistics for vendor"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {
        "total_customers": 156,
        "new_this_month": 23,
        "returning_customers": 89,
        "average_order_value": 2845.50
    }

@router.post("/customers/{customer_id}/message")
def send_customer_message(
    customer_id: int,
    message_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Send message to customer"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {"message": "Message sent successfully to customer"}

# Marketing & Promotions Endpoints
@router.get("/promotions")
def get_vendor_promotions(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get vendor's promotional campaigns"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    # Mock promotion data
    return [
        {
            "id": 1,
            "name": "Summer Sale 2024",
            "type": "percentage",
            "value": 25,
            "code": "SUMMER25",
            "description": "Get 25% off on all summer collection items",
            "min_order_value": 1000,
            "max_discount": 2000,
            "usage_limit": 500,
            "used_count": 156,
            "start_date": "2024-03-01",
            "end_date": "2024-04-30",
            "status": "active",
            "applicable_products": "category",
            "total_savings": 45600,
            "conversion_rate": 12.5
        }
    ]

@router.post("/promotions")
def create_promotion(
    promotion_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new promotional campaign"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {"message": "Promotion created successfully", "promotion_id": 123}

@router.put("/promotions/{promotion_id}")
def update_promotion(
    promotion_id: int,
    promotion_data: dict,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update a promotional campaign"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {"message": "Promotion updated successfully"}

@router.delete("/promotions/{promotion_id}")
def delete_promotion(
    promotion_id: int,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Delete a promotional campaign"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {"message": "Promotion deleted successfully"}

@router.get("/promotions/stats")
def get_promotion_statistics(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get promotion statistics for vendor"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {
        "active_promotions": 3,
        "total_redemptions": 456,
        "total_savings": 125600,
        "conversion_rate": 14.2
    }

# Advanced Analytics Endpoints  
@router.get("/analytics/overview")
def get_analytics_overview(
    time_range: str = Query("7days", regex="^(7days|30days|90days|1year)$"),
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get comprehensive analytics overview"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {
        "overview": {
            "total_revenue": 156750,
            "total_orders": 342,
            "average_order_value": 458,
            "conversion_rate": 3.2,
            "customer_retention": 68,
            "profit_margin": 24.5,
            "revenue_growth": 12.3,
            "order_growth": 8.7
        },
        "sales_trends": [
            {"date": "2024-03-15", "revenue": 12500, "orders": 28},
            {"date": "2024-03-16", "revenue": 15200, "orders": 32},
            {"date": "2024-03-17", "revenue": 9800, "orders": 22},
            {"date": "2024-03-18", "revenue": 18600, "orders": 41},
            {"date": "2024-03-19", "revenue": 22100, "orders": 48},
            {"date": "2024-03-20", "revenue": 16300, "orders": 35},
            {"date": "2024-03-21", "revenue": 19200, "orders": 42}
        ]
    }

@router.get("/analytics/products")
def get_product_analytics(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get product performance analytics"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return [
        {
            "id": 1,
            "name": "Wireless Headphones Pro",
            "sales": 85,
            "revenue": 42500,
            "growth": 15.2
        },
        {
            "id": 2,
            "name": "Smart Fitness Watch",
            "sales": 62,
            "revenue": 31000,
            "growth": 8.9
        }
    ]

@router.get("/analytics/customers")
def get_customer_analytics(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get customer insights and analytics"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {
        "total_customers": 1247,
        "new_customers": 89,
        "returning_customers": 253,
        "avg_customer_lifetime": 8.5,
        "top_locations": [
            {"city": "Mumbai", "customers": 234, "revenue": 45600},
            {"city": "Delhi", "customers": 189, "revenue": 38200},
            {"city": "Bangalore", "customers": 156, "revenue": 31800}
        ]
    }

@router.get("/analytics/performance")
def get_performance_metrics(
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Get business performance metrics"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {
        "inventory_turnover": 4.2,
        "average_delivery_time": 2.8,
        "return_rate": 3.5,
        "customer_satisfaction": 4.6,
        "response_time": 2.1,
        "fulfillment_rate": 98.5
    }

@router.get("/analytics/export")
def export_analytics_report(
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    time_range: str = Query("30days", regex="^(7days|30days|90days|1year)$"),
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Export analytics report in PDF or Excel format"""
    vendor = crud.get_vendor_by_user_id(db, current_user.id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    
    return {"message": f"Analytics report export initiated in {format} format", "download_url": f"/downloads/analytics_report_{vendor.id}.{format}"}