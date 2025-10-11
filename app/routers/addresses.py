from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(prefix="/addresses", tags=["addresses"])

@router.get("/", response_model=List[schemas.Address])
def get_user_addresses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all addresses for the current user"""
    addresses = crud.get_user_addresses(db, user_id=current_user.id)
    return addresses

@router.post("/", response_model=schemas.Address, status_code=status.HTTP_201_CREATED)
def create_address(
    address: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new address for the current user"""
    # If this is set as default, unset all other default addresses
    if address.is_default:
        user_addresses = crud.get_user_addresses(db, user_id=current_user.id)
        for addr in user_addresses:
            if addr.is_default:
                addr.is_default = False
        db.commit()
    
    db_address = crud.create_address(db=db, address=address, user_id=current_user.id)
    return db_address

@router.get("/{address_id}", response_model=schemas.Address)
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific address"""
    address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return address

@router.put("/{address_id}", response_model=schemas.Address)
def update_address(
    address_id: int,
    address_update: schemas.AddressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update an address"""
    # Check if address exists and belongs to user
    db_address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If setting as default, unset all other default addresses
    if address_update.is_default:
        user_addresses = crud.get_user_addresses(db, user_id=current_user.id)
        for addr in user_addresses:
            if addr.id != address_id and addr.is_default:
                addr.is_default = False
        db.commit()
    
    # Update address fields
    for field, value in address_update.dict(exclude_unset=True).items():
        setattr(db_address, field, value)
    
    db.commit()
    db.refresh(db_address)
    return db_address

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete an address"""
    db_address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    db.delete(db_address)
    db.commit()
    return None

@router.post("/{address_id}/set-default", response_model=schemas.Address)
def set_default_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Set an address as default"""
    db_address = db.query(models.Address).filter(
        models.Address.id == address_id,
        models.Address.user_id == current_user.id
    ).first()
    
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Unset all other default addresses
    user_addresses = crud.get_user_addresses(db, user_id=current_user.id)
    for addr in user_addresses:
        if addr.id != address_id and addr.is_default:
            addr.is_default = False
    
    db_address.is_default = True
    db.commit()
    db.refresh(db_address)
    return db_address
