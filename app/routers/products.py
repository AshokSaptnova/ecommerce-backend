from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas, crud, auth

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=List[schemas.Product])
def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    status: Optional[schemas.ProductStatus] = None,
    is_featured: Optional[bool] = None,
    db: Session = Depends(auth.get_db)
):
    """Get products with filtering options"""
    return crud.get_products(
        db=db, 
        skip=skip, 
        limit=limit,
        category_id=category_id,
        vendor_id=vendor_id,
        status=status,
        is_featured=is_featured
    )

@router.get("/search", response_model=List[schemas.Product])
def search_products(
    q: str = Query(..., min_length=2),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(auth.get_db)
):
    """Search products by name, description, or tags"""
    return crud.search_products(db=db, query=q, skip=skip, limit=limit)

@router.get("/featured", response_model=List[schemas.Product])
def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(auth.get_db)
):
    """Get featured products"""
    return crud.get_products(db=db, limit=limit, is_featured=True)

@router.get("/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(auth.get_db)):
    """Get product by ID"""
    db_product = crud.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.get("/slug/{slug}", response_model=schemas.Product)
def get_product_by_slug(slug: str, db: Session = Depends(auth.get_db)):
    """Get product by slug"""
    db_product = crud.get_product_by_slug(db, slug=slug)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.post("/", response_model=schemas.Product)
def create_product(
    product: schemas.ProductCreate,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Create a new product (vendor only)"""
    # Ensure vendor can only create products for their own vendor account
    if current_user.role == models.UserRole.VENDOR:
        vendor = crud.get_vendor_by_user_id(db, current_user.id)
        if not vendor or product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only create products for your own vendor account"
            )
    
    # Check if SKU already exists
    existing_product = crud.get_product_by_sku(db, product.sku)
    if existing_product:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    return crud.create_product(db=db, product=product)

@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: int,
    product: schemas.ProductUpdate,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Update product (vendor/admin only)"""
    db_product = crud.get_product_by_id(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Ensure vendor can only update their own products
    if current_user.role == models.UserRole.VENDOR:
        vendor = crud.get_vendor_by_user_id(db, current_user.id)
        if not vendor or db_product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own products"
            )
    
    return crud.update_product(db=db, product_id=product_id, product=product)

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current_user: models.User = Depends(auth.get_current_vendor_user),
    db: Session = Depends(auth.get_db)
):
    """Delete product (vendor/admin only)"""
    db_product = crud.get_product_by_id(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Ensure vendor can only delete their own products
    if current_user.role == models.UserRole.VENDOR:
        vendor = crud.get_vendor_by_user_id(db, current_user.id)
        if not vendor or db_product.vendor_id != vendor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own products"
            )
    
    crud.delete_product(db=db, product_id=product_id)
    return {"message": "Product deleted successfully"}

@router.get("/{product_id}/reviews", response_model=List[schemas.Review])
def get_product_reviews(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(auth.get_db)
):
    """Get reviews for a product"""
    return crud.get_product_reviews(db=db, product_id=product_id, skip=skip, limit=limit)

@router.post("/{product_id}/reviews", response_model=schemas.Review)
def create_product_review(
    product_id: int,
    review: schemas.ReviewCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(auth.get_db)
):
    """Create a review for a product"""
    # Verify product exists
    product = crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Ensure review is for the correct product
    if review.product_id != product_id:
        raise HTTPException(status_code=400, detail="Product ID mismatch")
    
    # Check if user already reviewed this product
    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == product_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    
    return crud.create_review(db=db, review=review, user_id=current_user.id)