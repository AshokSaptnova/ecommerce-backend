from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from enum import Enum

from .. import models, schemas, crud, auth
from ..database import get_db

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=schemas.Order)
def create_order(
    order: schemas.OrderCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new order"""
    # Validate all products in the order
    for item in order.items:
        product = crud.get_product_by_id(db, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.status != schemas.ProductStatus.ACTIVE:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is not available")
        
        # Check stock
        if product.track_inventory and product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}"
            )
    
    # Create the order
    db_order = crud.create_order(db=db, order=order, user_id=current_user.id)
    
    # Update product stock quantities
    for item in order.items:
        product = crud.get_product_by_id(db, item.product_id)
        if product and product.track_inventory:
            product.stock_quantity -= item.quantity
    
    db.commit()
    db.refresh(db_order)
    
    # Clear user's cart after successful order
    crud.clear_user_cart(db=db, user_id=current_user.id)
    
    return db_order

@router.get("/", response_model=List[schemas.Order])
def get_user_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Get user's orders"""
    return crud.get_user_orders(db=db, user_id=current_user.id, skip=skip, limit=limit)

@router.get("/session/{session_id}", response_model=List[schemas.Order])
def get_orders_for_session(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get guest orders created for a specific session id"""
    return crud.get_orders_by_session_id(db=db, session_id=session_id, skip=skip, limit=limit)

@router.get("/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Get order by ID"""
    db_order = crud.get_order_by_id(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Users can only see their own orders, unless admin
    if current_user.role != models.UserRole.ADMIN and db_order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return db_order

@router.get("/number/{order_number}", response_model=schemas.Order)
def get_order_by_number(
    order_number: str,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Get order by order number"""
    db_order = crud.get_order_by_number(db, order_number)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Users can only see their own orders, unless admin
    if current_user.role != models.UserRole.ADMIN and db_order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return db_order

@router.put("/{order_id}/status", response_model=schemas.Order)
def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update order status (admin only)"""
    db_order = crud.update_order_status(db=db, order_id=order_id, status=status_update.status)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return db_order

@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Cancel order"""
    db_order = crud.get_order_by_id(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Users can only cancel their own orders
    if db_order.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    # Only allow cancellation if order is still pending or confirmed
    if db_order.status not in [schemas.OrderStatus.PENDING, schemas.OrderStatus.CONFIRMED]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled at this stage")
    
    # Update order status
    db_order = crud.update_order_status(db=db, order_id=order_id, status=schemas.OrderStatus.CANCELLED)
    
    # Restore product stock quantities
    for item in db_order.items:
        product = crud.get_product_by_id(db, item.product_id)
        if product and product.track_inventory:
            product.stock_quantity += item.quantity
            db.commit()
    
    return {"message": "Order cancelled successfully"}

@router.post("/checkout", response_model=dict)
def create_order_from_cart(
    checkout_data: schemas.CheckoutRequest,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create order from user's cart"""
    # Get user's cart
    cart_items = crud.get_user_cart(db=db, user_id=current_user.id)
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Validate stock availability
    for item in cart_items:
        product = item.product
        if product.track_inventory and product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Only {product.stock_quantity} available"
            )
    
    # Calculate totals
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    tax_amount = subtotal * 0.18  # 18% GST
    shipping_amount = 0 if subtotal >= 500 else 50
    total_amount = subtotal + tax_amount + shipping_amount
    
    # Create order items data
    order_items = []
    for cart_item in cart_items:
        order_items.append(schemas.OrderItemCreate(
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price
        ))
    
    # Create order data
    # Convert address objects to dictionaries for OrderCreate schema
    shipping_addr = checkout_data.shipping_address.dict() if hasattr(checkout_data.shipping_address, 'dict') else checkout_data.shipping_address
    billing_addr = (checkout_data.billing_address or checkout_data.shipping_address)
    if hasattr(billing_addr, 'dict'):
        billing_addr = billing_addr.dict()
    
    order_create = schemas.OrderCreate(
        items=order_items,
        shipping_address=shipping_addr,
        billing_address=billing_addr,
        payment_method=checkout_data.payment_method,
        notes=checkout_data.notes
    )
    
    # Create the order using existing endpoint logic
    order = crud.create_order(db=db, order=order_create, user_id=current_user.id)
    
    # Update product stock quantities after order creation
    for cart_item in cart_items:
        product = cart_item.product
        if product.track_inventory:
            product.stock_quantity -= cart_item.quantity
    
    db.commit()
    db.refresh(order)
    
    # Clear user's cart after successful order creation
    crud.clear_user_cart(db=db, user_id=current_user.id)
    
    return {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "total_amount": order.total_amount,
        "payment_method": order.payment_method,
        "status": order.status,
        "message": "Order created successfully"
    }

@router.post("/session/{session_id}/checkout", response_model=dict)
def create_order_from_session_cart(
    session_id: str,
    checkout_data: schemas.CheckoutCreate,
    db: Session = Depends(get_db)
):
    """Create order from session cart (for guest users)"""
    # Get cart data - it returns a dict, not a list
    cart_data = crud.get_session_cart(db=db, session_id=session_id)
    
    if not cart_data or not cart_data.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    try:
        # Use the crud function to create order
        order = crud.create_order_from_session_cart(db=db, session_id=session_id, checkout_data=checkout_data)
    except ValueError as e:
        # Handle stock validation errors
        raise HTTPException(status_code=400, detail=str(e))
    
    if not order:
        raise HTTPException(status_code=400, detail="Failed to create order")
    
    return {
        "success": True,
        "id": order.id,
        "order_number": order.order_number,
        "session_id": order.session_id,
        "customer_email": order.customer_email,
        "customer_name": order.customer_name,
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_method": order.payment_method,
        "message": "Order created successfully"
    }