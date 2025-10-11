from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

@router.get("/", response_model=List[schemas.Wishlist])
def get_user_wishlist(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all wishlist items for the current user"""
    from sqlalchemy.orm import joinedload
    
    wishlist_items = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id
    ).options(joinedload(models.Wishlist.product)).all()
    return wishlist_items

@router.post("/", response_model=schemas.Wishlist, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    wishlist_item: schemas.WishlistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Add a product to wishlist"""
    # Check if product exists
    product = db.query(models.Product).filter(
        models.Product.id == wishlist_item.product_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already in wishlist
    existing = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == wishlist_item.product_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Product already in wishlist"
        )
    
    # Create wishlist item
    db_wishlist = models.Wishlist(
        user_id=current_user.id,
        product_id=wishlist_item.product_id
    )
    db.add(db_wishlist)
    db.commit()
    db.refresh(db_wishlist)
    return db_wishlist

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Remove a product from wishlist"""
    wishlist_item = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == product_id
    ).first()
    
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    
    db.delete(wishlist_item)
    db.commit()
    return None

@router.post("/{product_id}/toggle", response_model=dict)
def toggle_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Toggle product in wishlist (add if not exists, remove if exists)"""
    # Check if product exists
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already in wishlist
    existing = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == product_id
    ).first()
    
    if existing:
        # Remove from wishlist
        db.delete(existing)
        db.commit()
        return {"action": "removed", "in_wishlist": False}
    else:
        # Add to wishlist
        db_wishlist = models.Wishlist(
            user_id=current_user.id,
            product_id=product_id
        )
        db.add(db_wishlist)
        db.commit()
        return {"action": "added", "in_wishlist": True}

@router.get("/check/{product_id}", response_model=dict)
def check_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Check if a product is in wishlist"""
    existing = db.query(models.Wishlist).filter(
        models.Wishlist.user_id == current_user.id,
        models.Wishlist.product_id == product_id
    ).first()
    
    return {"in_wishlist": existing is not None}
