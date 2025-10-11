from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import razorpay
import hmac
import hashlib
import os
from dotenv import load_dotenv

from .. import models, schemas, crud
from ..database import get_db
from ..auth import get_current_active_user

load_dotenv()

router = APIRouter(prefix="/payments", tags=["payments"])

# Initialize Razorpay client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@router.post("/create-order")
async def create_razorpay_order(
    order_data: schemas.PaymentOrderCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay order for payment
    """
    try:
        # Calculate amount in paise (smallest currency unit)
        amount_in_paise = int(order_data.amount * 100)
        
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paise,
            "currency": order_data.currency or "INR",
            "payment_capture": 1,  # Auto capture
            "notes": {
                "user_id": current_user.id,
                "customer_email": order_data.customer_email or current_user.email,
                "order_items": str(order_data.items_count or 0)
            }
        })
        
        return {
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": RAZORPAY_KEY_ID
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment order: {str(e)}"
        )


@router.post("/verify")
async def verify_razorpay_payment(
    payment_data: schemas.PaymentVerification,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment signature and create order
    """
    try:
        # Verify signature
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{payment_data.razorpay_order_id}|{payment_data.razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != payment_data.razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature"
            )
        
        # Fetch payment details from Razorpay
        payment = razorpay_client.payment.fetch(payment_data.razorpay_payment_id)
        
        if payment["status"] != "captured":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment not captured"
            )
        
        # Create order from cart
        order_create_data = payment_data.order_data
        
        # Get user's cart
        cart_items = crud.get_user_cart(db=db, user_id=current_user.id)
        
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        # Calculate totals
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        tax_amount = subtotal * 0.18
        shipping_amount = 0 if subtotal >= 500 else 50
        total_amount = subtotal + tax_amount + shipping_amount
        
        # Create order items
        order_items = []
        for cart_item in cart_items:
            order_items.append(schemas.OrderItemCreate(
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price
            ))
        
        # Prepare addresses
        shipping_addr = order_create_data.shipping_address
        billing_addr = order_create_data.billing_address or shipping_addr
        
        # Create order
        order = schemas.OrderCreate(
            items=order_items,
            customer_email=order_create_data.customer_email or current_user.email,
            customer_name=order_create_data.customer_name or current_user.full_name,
            customer_phone=order_create_data.customer_phone or current_user.phone,
            shipping_address=shipping_addr,
            billing_address=billing_addr,
            payment_method="online_payment",
            subtotal_amount=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            notes=order_create_data.notes or ""
        )
        
        # Create order in database
        db_order = crud.create_order(db=db, order=order, user_id=current_user.id)
        
        # Update order with payment info
        db_order.payment_status = "paid"
        db_order.payment_id = payment_data.razorpay_payment_id
        db_order.payment_method = "razorpay"
        db.commit()
        db.refresh(db_order)
        
        # Update product stock
        for item in cart_items:
            product = crud.get_product_by_id(db, item.product_id)
            if product and product.track_inventory:
                product.stock_quantity -= item.quantity
                db.commit()
        
        # Clear user's cart
        crud.clear_user_cart(db=db, user_id=current_user.id)
        
        return {
            "success": True,
            "message": "Payment verified and order created successfully",
            "order_id": db_order.id,
            "order_number": db_order.order_number,
            "payment_id": payment_data.razorpay_payment_id,
            "amount": payment["amount"] / 100,  # Convert from paise to rupees
            "status": db_order.status,
            "total_amount": db_order.total_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )


@router.get("/payment/{payment_id}")
async def get_payment_details(
    payment_id: str,
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get payment details from Razorpay
    """
    try:
        payment = razorpay_client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found: {str(e)}"
        )


@router.post("/refund")
async def create_refund(
    refund_data: schemas.RefundCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a refund for a payment (Admin only)
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can process refunds"
        )
    
    try:
        # Create refund in Razorpay
        refund = razorpay_client.payment.refund(
            refund_data.payment_id,
            {
                "amount": int(refund_data.amount * 100),  # Convert to paise
                "speed": "normal",
                "notes": refund_data.notes or {}
            }
        )
        
        # Update order status in database
        order = db.query(models.Order).filter(
            models.Order.payment_id == refund_data.payment_id
        ).first()
        
        if order:
            order.payment_status = "refunded"
            order.status = models.OrderStatus.CANCELLED
            db.commit()
        
        return {
            "success": True,
            "refund_id": refund["id"],
            "amount": refund["amount"] / 100,
            "status": refund["status"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund failed: {str(e)}"
        )
