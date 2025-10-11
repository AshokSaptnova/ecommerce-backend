from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from .. import models, schemas, crud, auth
from ..database import get_db

router = APIRouter(prefix="/cart", tags=["shopping cart"])

@router.get("/", response_model=List[schemas.CartItem])
def get_cart(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Get user's cart items"""
    return crud.get_user_cart(db=db, user_id=current_user.id)

@router.post("/add", response_model=schemas.CartItem)
def add_to_cart(
    cart_item: schemas.CartItemCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Add item to cart"""
    # Verify product exists and is available
    product = crud.get_product_by_id(db, cart_item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.status != schemas.ProductStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Product is not available")
    
    # Check stock if inventory tracking is enabled
    if product.track_inventory and product.stock_quantity < cart_item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    return crud.add_to_cart(db=db, user_id=current_user.id, cart_item=cart_item)

@router.put("/{cart_item_id}", response_model=schemas.CartItem)
def update_cart_item(
    cart_item_id: int,
    cart_update: schemas.CartItemUpdate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Update cart item quantity"""
    if cart_update.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    
    db_item = crud.update_cart_item(
        db=db, 
        cart_item_id=cart_item_id, 
        user_id=current_user.id, 
        quantity=cart_update.quantity
    )
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    return db_item

@router.delete("/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Remove item from cart"""
    db_item = crud.remove_from_cart(db=db, cart_item_id=cart_item_id, user_id=current_user.id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    return {"message": "Item removed from cart"}

@router.delete("/")
def clear_cart(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Clear all items from cart"""
    crud.clear_user_cart(db=db, user_id=current_user.id)
    return {"message": "Cart cleared successfully"}

@router.get("/summary")
def get_cart_summary(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Get cart summary with totals"""
    cart_items = crud.get_user_cart(db=db, user_id=current_user.id)
    
    total_items = sum(item.quantity for item in cart_items)
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    
    # Calculate tax (18% GST for India)
    tax_rate = 0.18
    tax_amount = subtotal * tax_rate
    
    # Shipping calculation (free shipping over ₹500, no shipping for empty cart)
    shipping_threshold = 500
    shipping_amount = 0 if (subtotal == 0 or subtotal >= shipping_threshold) else 50
    
    total_amount = subtotal + tax_amount + shipping_amount
    
    return {
        "total_items": total_items,
        "subtotal": round(subtotal, 2),
        "tax_amount": round(tax_amount, 2),
        "tax_rate": tax_rate,
        "shipping_amount": shipping_amount,
        "shipping_threshold": shipping_threshold,
        "total_amount": round(total_amount, 2),
        "currency": "INR",
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "product_image": item.product.images[0].image_url if item.product.images else None,
                "product_slug": item.product.slug,
                "price": item.product.price,
                "quantity": item.quantity,
                "subtotal": round(item.product.price * item.quantity, 2)
            }
            for item in cart_items
        ]
    }

# Session-based cart endpoints for guest users
@router.post("/session/{session_id}/add")
def add_to_session_cart(
    session_id: str,
    cart_item: schemas.CartItemCreate,
    db: Session = Depends(get_db)
):
    """Add item to session cart (for guest users)"""
    # Verify product exists and is available
    product = crud.get_product_by_id(db, cart_item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.status != schemas.ProductStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Product is not available")
    
    # Check stock if inventory tracking is enabled
    if product.track_inventory and product.stock_quantity < cart_item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    return crud.add_to_session_cart(db=db, session_id=session_id, cart_item=cart_item)

@router.get("/session/{session_id}")
def get_session_cart(session_id: str, db: Session = Depends(get_db)):
    """Get session cart items (for guest users)"""
    return crud.get_session_cart(db=db, session_id=session_id)

@router.get("/session/{session_id}/summary")
def get_session_cart_summary(session_id: str, db: Session = Depends(get_db)):
    """Get session cart summary with totals"""
    return crud.get_session_cart(db=db, session_id=session_id)

@router.put("/session/{session_id}/update")
def update_session_cart_item(
    session_id: str,
    cart_item: schemas.CartItemUpdate,
    db: Session = Depends(get_db)
):
    """Update session cart item quantity"""
    result = crud.update_session_cart_item(
        db=db, 
        session_id=session_id, 
        product_id=cart_item.product_id, 
        quantity=cart_item.quantity
    )
    if not result:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return {"message": "Cart item updated successfully"}

@router.delete("/session/{session_id}/remove/{product_id}")
def remove_from_session_cart(
    session_id: str,
    product_id: int,
    db: Session = Depends(get_db)
):
    """Remove item from session cart"""
    result = crud.remove_from_session_cart(db=db, session_id=session_id, product_id=product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return {"message": "Item removed from cart"}

@router.delete("/session/{session_id}/clear")
def clear_session_cart(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Clear all items from session cart"""
    crud.clear_session_cart(db=db, session_id=session_id)
    return {"message": "Cart cleared successfully"}