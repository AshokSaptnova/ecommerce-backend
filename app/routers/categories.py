from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud, auth

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("/", response_model=List[schemas.Category])
def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool = True,
    db: Session = Depends(auth.get_db)
):
    """Get all categories"""
    return crud.get_categories(db=db, skip=skip, limit=limit, is_active=is_active)

@router.get("/{category_id}", response_model=schemas.Category)
def get_category(category_id: int, db: Session = Depends(auth.get_db)):
    """Get category by ID"""
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@router.get("/slug/{slug}", response_model=schemas.Category)
def get_category_by_slug(slug: str, db: Session = Depends(auth.get_db)):
    """Get category by slug"""
    db_category = crud.get_category_by_slug(db, slug)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@router.post("/", response_model=schemas.Category)
def create_category(
    category: schemas.CategoryCreate,
    current_user: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Create new category (admin only)"""
    # Check if slug already exists
    existing_category = crud.get_category_by_slug(db, category.slug)
    if existing_category:
        raise HTTPException(status_code=400, detail="Category slug already exists")
    
    return crud.create_category(db=db, category=category)

@router.put("/{category_id}", response_model=schemas.Category)
def update_category(
    category_id: int,
    category: schemas.CategoryUpdate,
    current_user: models.User = Depends(auth.get_current_admin_user),
    db: Session = Depends(auth.get_db)
):
    """Update category (admin only)"""
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if new slug conflicts with existing categories
    if category.slug != db_category.slug:
        existing_category = crud.get_category_by_slug(db, category.slug)
        if existing_category:
            raise HTTPException(status_code=400, detail="Category slug already exists")
    
    for field, value in category.dict(exclude_unset=True).items():
        setattr(db_category, field, value)
    
    db.commit()
    db.refresh(db_category)
    return db_category