from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/vendors/{vendor_id}/customers", tags=["customers"])

@router.get("/", response_model=List[schemas.Customer])
def get_vendor_customers(vendor_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_vendor_user)):
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Find all users who have placed orders for this vendor's products
    orders = db.query(models.Order).join(models.Product, models.Order.items.any(models.OrderItem.product_id == models.Product.id)).filter(models.Product.vendor_id == vendor_id).all()
    customer_map = {}
    for order in orders:
        if order.user_id:
            user = db.query(models.User).filter(models.User.id == order.user_id).first()
            if user and user.id not in customer_map:
                customer_map[user.id] = {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "created_at": user.created_at,
                    "total_orders": 1,
                    "total_spent": order.total_amount,
                    "last_order_date": order.created_at
                }
            elif user:
                customer_map[user.id]["total_orders"] += 1
                customer_map[user.id]["total_spent"] += order.total_amount
                if order.created_at > customer_map[user.id]["last_order_date"]:
                    customer_map[user.id]["last_order_date"] = order.created_at
    return list(customer_map.values())
