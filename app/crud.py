from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from . import models, schemas
from .auth import get_password_hash
import uuid
from datetime import datetime


def _calculate_product_rating(db: Session, product_id: int):
    """Calculate average rating and review count for a product"""
    result = db.query(
        func.avg(models.Review.rating).label('average_rating'),
        func.count(models.Review.id).label('review_count')
    ).filter(
        models.Review.product_id == product_id,
        models.Review.is_approved == True
    ).first()
    
    return {
        'average_rating': round(float(result.average_rating), 1) if result.average_rating else None,
        'review_count': result.review_count or 0
    }


def _add_rating_to_product(db: Session, product: models.Product):
    """Add rating information to a product object"""
    if product:
        rating_data = _calculate_product_rating(db, product.id)
        product.average_rating = rating_data['average_rating']
        product.review_count = rating_data['review_count']
    return product


def _get_primary_image_url(product: models.Product):
    """Helper to fetch the primary image URL for a product"""
    if not product or not getattr(product, "images", None):
        return None
    primary_image = next((image for image in product.images if getattr(image, "is_primary", False)), None)
    return (primary_image or product.images[0]).image_url


def _serialize_session_cart_item(cart_item: models.SessionCart):
    """Serialize a session cart item with product snapshot details"""
    product = cart_item.product
    subtotal = float(product.price * cart_item.quantity) if product else 0.0
    return {
        "id": cart_item.id,
        "session_id": cart_item.session_id,
        "product_id": cart_item.product_id,
        "quantity": cart_item.quantity,
        "unit_price": float(product.price) if product else 0.0,
        "subtotal": subtotal,
        "product_name": product.name if product else None,
        "product_slug": product.slug if product else None,
        "product_image": _get_primary_image_url(product) if product else None,
        "stock_quantity": product.stock_quantity if product else None,
        "track_inventory": product.track_inventory if product else None,
    }

# User CRUD
def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    """Get user by email (case-insensitive)"""
    email_lower = email.lower()
    return db.query(models.User).filter(models.User.email == email_lower).first()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    """Update user information"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        for field, value in user_update.dict(exclude_unset=True).items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
    return db_user

# Address CRUD
def create_address(db: Session, address: schemas.AddressCreate, user_id: int):
    """Create a new address for user"""
    # If this is set as default, unset other default addresses
    if address.is_default:
        db.query(models.Address).filter(
            models.Address.user_id == user_id,
            models.Address.is_default == True
        ).update({"is_default": False})
    
    db_address = models.Address(**address.dict(), user_id=user_id)
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

def get_user_addresses(db: Session, user_id: int):
    """Get all addresses for a user"""
    return db.query(models.Address).filter(models.Address.user_id == user_id).all()

# Vendor CRUD
def create_vendor(db: Session, vendor: schemas.VendorCreate, user_id: int):
    """Create vendor profile"""
    db_vendor = models.Vendor(**vendor.dict(), user_id=user_id)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

def get_vendor_by_user_id(db: Session, user_id: int):
    """Get vendor profile by user ID"""
    return db.query(models.Vendor).filter(models.Vendor.user_id == user_id).first()

def get_vendors(db: Session, skip: int = 0, limit: int = 100, is_active: bool = True):
    """Get all vendors"""
    query = db.query(models.Vendor)
    if is_active is not None:
        query = query.filter(models.Vendor.is_active == is_active)
    return query.offset(skip).limit(limit).all()

def update_vendor(db: Session, vendor_id: int, vendor: schemas.VendorUpdate):
    """Update vendor information"""
    db_vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not db_vendor:
        return None
    
    for field, value in vendor.dict(exclude_unset=True).items():
        setattr(db_vendor, field, value)
    
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

def delete_vendor(db: Session, vendor_id: int):
    """Delete vendor"""
    db_vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not db_vendor:
        return False
    
    db.delete(db_vendor)
    db.commit()
    return True

# Category CRUD
def create_category(db: Session, category: schemas.CategoryCreate):
    """Create a new category"""
    import re
    
    # Auto-generate slug from name if not provided
    category_data = category.dict()
    if not category_data.get('slug'):
        # Create slug from name: lowercase, replace spaces with hyphens, remove special chars
        slug = re.sub(r'[^a-z0-9-]', '', category_data['name'].lower().replace(' ', '-'))
        category_data['slug'] = slug
    
    db_category = models.Category(**category_data)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def get_categories(db: Session, skip: int = 0, limit: int = 100, is_active: bool = True):
    """Get all categories"""
    query = db.query(models.Category)
    if is_active is not None:
        query = query.filter(models.Category.is_active == is_active)
    return query.order_by(models.Category.sort_order).offset(skip).limit(limit).all()

def get_category_by_slug(db: Session, slug: str):
    """Get category by slug"""
    return db.query(models.Category).filter(models.Category.slug == slug).first()

# Product CRUD
def create_product(db: Session, product: schemas.ProductCreate):
    """Create a new product"""
    # Extract nested data
    images_data = product.images
    variants_data = product.variants
    
    # Create product
    product_dict = product.dict(exclude={'images', 'variants'})
    db_product = models.Product(**product_dict)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Add images
    if images_data:
        for image_data in images_data:
            db_image = models.ProductImage(**image_data.dict(), product_id=db_product.id)
            db.add(db_image)
    
    # Add variants
    if variants_data:
        for variant_data in variants_data:
            db_variant = models.ProductVariant(**variant_data.dict(), product_id=db_product.id)
            db.add(db_variant)
    
    db.commit()
    db.refresh(db_product)
    return db_product

def get_products(db: Session, skip: int = 0, limit: int = 100, 
                category_id: Optional[int] = None, vendor_id: Optional[int] = None,
                status: Optional[schemas.ProductStatus] = None, is_featured: Optional[bool] = None):
    """Get products with filtering"""
    query = db.query(models.Product)
    
    if category_id:
        query = query.filter(models.Product.category_id == category_id)
    if vendor_id:
        query = query.filter(models.Product.vendor_id == vendor_id)
    if status:
        query = query.filter(models.Product.status == status)
    if is_featured is not None:
        query = query.filter(models.Product.is_featured == is_featured)
    
    products = query.offset(skip).limit(limit).all()
    
    # Add rating information to each product
    for product in products:
        _add_rating_to_product(db, product)
    
    return products

def get_product_by_id(db: Session, product_id: int):
    """Get product by ID"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    return _add_rating_to_product(db, product)

def get_product_by_sku(db: Session, sku: str):
    """Get product by SKU"""
    product = db.query(models.Product).filter(models.Product.sku == sku).first()
    return _add_rating_to_product(db, product)

def get_product_by_slug(db: Session, slug: str):
    """Get product by slug"""
    product = db.query(models.Product).filter(models.Product.slug == slug).first()
    return _add_rating_to_product(db, product)

def update_product(db: Session, product_id: int, product: schemas.ProductUpdate):
    """Update product"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        update_data = product.dict(exclude_unset=True, exclude={'images', 'variants'})
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        # Handle images update if provided
        if hasattr(product, 'images') and product.images is not None:
            # Delete existing images
            db.query(models.ProductImage).filter(models.ProductImage.product_id == product_id).delete()
            # Add new images
            for image_data in product.images:
                db_image = models.ProductImage(**image_data.dict(), product_id=product_id)
                db.add(db_image)
        
        # Handle variants update if provided
        if hasattr(product, 'variants') and product.variants is not None:
            # Delete existing variants
            db.query(models.ProductVariant).filter(models.ProductVariant.product_id == product_id).delete()
            # Add new variants
            for variant_data in product.variants:
                db_variant = models.ProductVariant(**variant_data.dict(), product_id=product_id)
                db.add(db_variant)
        
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    """Delete product"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product

def search_products(db: Session, query: str, skip: int = 0, limit: int = 50):
    """Search products by name, description, or tags"""
    search_filter = or_(
        models.Product.name.ilike(f'%{query}%'),
        models.Product.short_description.ilike(f'%{query}%'),
        models.Product.description.ilike(f'%{query}%')
    )
    products = db.query(models.Product).filter(search_filter).offset(skip).limit(limit).all()
    
    # Add rating information to each product
    for product in products:
        _add_rating_to_product(db, product)
    
    return products

# Cart CRUD
def add_to_cart(db: Session, user_id: int, cart_item: schemas.CartItemCreate):
    """Add item to cart or update quantity if exists"""
    existing_item = db.query(models.CartItem).filter(
        and_(
            models.CartItem.user_id == user_id,
            models.CartItem.product_id == cart_item.product_id,
            models.CartItem.variant_id == cart_item.variant_id
        )
    ).first()
    
    if existing_item:
        existing_item.quantity += cart_item.quantity
        existing_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        db_cart_item = models.CartItem(**cart_item.dict(), user_id=user_id)
        db.add(db_cart_item)
        db.commit()
        db.refresh(db_cart_item)
        return db_cart_item

def get_user_cart(db: Session, user_id: int):
    """Get user's cart items"""
    return db.query(models.CartItem).filter(models.CartItem.user_id == user_id).all()

def update_cart_item(db: Session, cart_item_id: int, user_id: int, quantity: int):
    """Update cart item quantity"""
    db_item = db.query(models.CartItem).filter(
        and_(models.CartItem.id == cart_item_id, models.CartItem.user_id == user_id)
    ).first()
    if db_item:
        db_item.quantity = quantity
        db_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_item)
    return db_item

def remove_from_cart(db: Session, cart_item_id: int, user_id: int):
    """Remove item from cart"""
    db_item = db.query(models.CartItem).filter(
        and_(models.CartItem.id == cart_item_id, models.CartItem.user_id == user_id)
    ).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return db_item

def clear_user_cart(db: Session, user_id: int):
    """Clear all items from user's cart"""
    db.query(models.CartItem).filter(models.CartItem.user_id == user_id).delete()
    db.commit()

# Order CRUD
def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    """Create a new order"""
    # Generate unique order number
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Calculate totals
    subtotal = sum(item.quantity * item.unit_price for item in order.items)
    # Add tax calculation logic here
    tax_amount = subtotal * 0.18  # 18% GST for example
    # Add shipping calculation logic here
    shipping_amount = 0.0 if subtotal > 500 else 50.0  # Free shipping above 500
    total_amount = subtotal + tax_amount + shipping_amount
    
    db_order = models.Order(
        order_number=order_number,
        user_id=user_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_amount=shipping_amount,
        discount_amount=0.0,
        total_amount=total_amount,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        customer_notes=order.customer_notes
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Add order items
    for item_data in order.items:
        # Get product details for snapshot
        product = get_product_by_id(db, item_data.product_id)
        if product:
            db_order_item = models.OrderItem(
                order_id=db_order.id,
                product_id=item_data.product_id,
                variant_id=item_data.variant_id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_data.quantity * item_data.unit_price
            )
            db.add(db_order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

def get_user_orders(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get user's orders"""
    return (
        db.query(models.Order)
        .options(
            selectinload(models.Order.items).selectinload(models.OrderItem.product),
            selectinload(models.Order.user),
        )
        .filter(models.Order.user_id == user_id)
        .order_by(models.Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_orders_by_session_id(db: Session, session_id: str, skip: int = 0, limit: int = 100):
    """Get orders associated with a guest session"""
    return (
        db.query(models.Order)
        .options(
            selectinload(models.Order.items).selectinload(models.OrderItem.product),
            selectinload(models.Order.user),
        )
        .filter(models.Order.session_id == session_id)
        .order_by(models.Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_order_by_id(db: Session, order_id: int):
    """Get order by ID"""
    return (
        db.query(models.Order)
        .options(
            selectinload(models.Order.items).selectinload(models.OrderItem.product),
            selectinload(models.Order.user),
        )
        .filter(models.Order.id == order_id)
        .first()
    )

def get_order_by_number(db: Session, order_number: str):
    """Get order by order number"""
    return (
        db.query(models.Order)
        .options(
            selectinload(models.Order.items).selectinload(models.OrderItem.product),
            selectinload(models.Order.user),
        )
        .filter(models.Order.order_number == order_number)
        .first()
    )

def update_order_status(db: Session, order_id: int, status: schemas.OrderStatus):
    """Update order status"""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        db_order.status = status
        if status == schemas.OrderStatus.SHIPPED:
            db_order.shipped_at = datetime.utcnow()
        elif status == schemas.OrderStatus.DELIVERED:
            db_order.delivered_at = datetime.utcnow()
        db.commit()
        db.refresh(db_order)
    return db_order

# Review CRUD
def create_review(db: Session, review: schemas.ReviewCreate, user_id: int):
    """Create a product review"""
    db_review = models.Review(**review.dict(), user_id=user_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

def get_product_reviews(db: Session, product_id: int, skip: int = 0, limit: int = 50):
    """Get reviews for a product"""
    return db.query(models.Review).filter(
        and_(models.Review.product_id == product_id, models.Review.is_approved == True)
    ).order_by(models.Review.created_at.desc()).offset(skip).limit(limit).all()

# Coupon CRUD
def get_coupon_by_code(db: Session, code: str):
    """Get coupon by code"""
    return db.query(models.Coupon).filter(
        and_(
            models.Coupon.code == code,
            models.Coupon.is_active == True,
            models.Coupon.valid_from <= datetime.utcnow(),
            models.Coupon.valid_until >= datetime.utcnow()
        )
    ).first()

def validate_coupon(db: Session, code: str, user_id: int, order_total: float):
    """Validate coupon for use"""
    coupon = get_coupon_by_code(db, code)
    if not coupon:
        return None, "Invalid or expired coupon"
    
    if coupon.minimum_amount > order_total:
        return None, f"Minimum order amount is ₹{coupon.minimum_amount}"
    
    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        return None, "Coupon usage limit exceeded"
    
    # Check user usage limit (implement user-specific usage tracking)
    # This would require a separate table to track user-coupon usage
    
    return coupon, None

# Legacy CRUD for backward compatibility
def create_product_legacy(db: Session, product: schemas.ProductCreate):
    """Legacy product creation method"""
    db_benefits = [models.Benefit(text=benefit.text) for benefit in product.benefits]
    db_ingredients = [models.Ingredient(**ingredient.dict()) for ingredient in product.ingredients]
    
    db_product = models.Product(
        **product.dict(exclude={'benefits', 'ingredients'}),
        benefits=db_benefits,
        ingredients=db_ingredients
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# Additional CRUD operations for Admin Panel

def get_vendor_by_id(db: Session, vendor_id: int):
    """Get vendor by ID"""
    return db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()

def get_category_by_id(db: Session, category_id: int):
    """Get category by ID"""
    return db.query(models.Category).filter(models.Category.id == category_id).first()

def update_category(db: Session, category_id: int, category: schemas.CategoryUpdate):
    """Update category"""
    import re
    
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category:
        update_data = category.dict(exclude_unset=True)
        
        # Auto-generate slug from name if name is being updated but slug is not provided
        if 'name' in update_data and 'slug' not in update_data:
            slug = re.sub(r'[^a-z0-9-]', '', update_data['name'].lower().replace(' ', '-'))
            update_data['slug'] = slug
        
        for field, value in update_data.items():
            setattr(db_category, field, value)
        db.commit()
        db.refresh(db_category)
    return db_category

def get_order_by_id(db: Session, order_id: int):
    """Get order by ID"""
    return db.query(models.Order).filter(models.Order.id == order_id).first()

# Session Cart CRUD
def add_to_session_cart(db: Session, session_id: str, cart_item: schemas.CartItemCreate):
    """Add item to session cart"""
    # Check if item already exists in cart
    existing_item = db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id,
        models.SessionCart.product_id == cart_item.product_id
    ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += cart_item.quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        # Create new cart item
        db_cart_item = models.SessionCart(
            session_id=session_id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity
        )
        db.add(db_cart_item)
        db.commit()
        db.refresh(db_cart_item)
        return db_cart_item

def get_session_cart(db: Session, session_id: str):
    """Get session cart with items"""
    cart_items = db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id
    ).all()

    serialized_items = [_serialize_session_cart_item(item) for item in cart_items]

    total_items = sum(item["quantity"] for item in serialized_items)
    subtotal = sum(item["subtotal"] for item in serialized_items)
    tax_rate = 0.18  # Align with authenticated cart tax rate
    tax_amount = round(subtotal * tax_rate, 2)
    shipping_threshold = 500.0
    shipping_amount = 0.0 if subtotal >= shipping_threshold or subtotal == 0 else 50.0
    total_amount = round(subtotal + tax_amount + shipping_amount, 2)

    return {
        "session_id": session_id,
        "items": serialized_items,
        "total_items": total_items,
        "subtotal": round(subtotal, 2),
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "shipping_amount": shipping_amount,
        "shipping_threshold": shipping_threshold,
        "total_amount": total_amount,
        "currency": "INR"
    }

def update_session_cart_item(db: Session, session_id: str, product_id: int, quantity: int):
    """Update quantity of item in session cart"""
    cart_item = db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id,
        models.SessionCart.product_id == product_id
    ).first()
    
    if cart_item:
        if quantity <= 0:
            db.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.commit()
        if quantity > 0:
            db.refresh(cart_item)
        return cart_item
    return None

def remove_from_session_cart(db: Session, session_id: str, product_id: int):
    """Remove item from session cart"""
    cart_item = db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id,
        models.SessionCart.product_id == product_id
    ).first()
    
    if cart_item:
        db.delete(cart_item)
        db.commit()
        return True
    return False

def clear_session_cart(db: Session, session_id: str):
    """Clear all items from session cart"""
    db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id
    ).delete()
    db.commit()
    return True

# Order CRUD functions
def create_order_from_session_cart(db: Session, session_id: str, checkout_data: schemas.CheckoutCreate):
    """Create order from session cart"""
    # Get cart items
    cart_items = db.query(models.SessionCart).filter(
        models.SessionCart.session_id == session_id
    ).all()
    
    if not cart_items:
        return None
    
    # Validate stock availability before creating order
    for cart_item in cart_items:
        product = cart_item.product
        if not product:
            raise ValueError(f"Product not found")
        
        if product.status != schemas.ProductStatus.ACTIVE:
            raise ValueError(f"Product {product.name} is not available")
        
        if product.track_inventory and product.stock_quantity < cart_item.quantity:
            raise ValueError(
                f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {cart_item.quantity}"
            )
    
    # Calculate totals
    subtotal = sum(item.quantity * item.product.price for item in cart_items)
    tax_rate = 0.18
    tax_amount = round(subtotal * tax_rate, 2)
    shipping_threshold = 500.0
    shipping_amount = 0.0 if subtotal >= shipping_threshold or subtotal == 0 else 50.0
    total = round(subtotal + tax_amount + shipping_amount, 2)
    
    # Generate order number
    import time
    order_number = f"ORD-{int(time.time())}-{session_id[:8]}"
    
    customer_info = checkout_data.customer_info
    customer_name = " ".join(
        filter(None, [customer_info.first_name, customer_info.last_name])
    ).strip() or customer_info.first_name

    shipping_address = checkout_data.shipping_address.model_dump()
    billing_address = (checkout_data.billing_address or checkout_data.shipping_address).model_dump()

    # Create order
    db_order = models.Order(
        order_number=order_number,
        session_id=session_id,
        customer_email=customer_info.email,
        customer_name=customer_name,
        customer_phone=customer_info.phone,
        shipping_address=shipping_address,
        billing_address=billing_address,
        payment_method=checkout_data.payment_method,
        subtotal=float(round(subtotal, 2)),
        tax_amount=float(tax_amount),
        shipping_amount=float(shipping_amount),
        discount_amount=0.0,
        total_amount=float(total),
        status=models.OrderStatus.PENDING
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # Create order items
    for cart_item in cart_items:
        product = cart_item.product
        
        # Check stock availability
        if product.track_inventory and product.stock_quantity < cart_item.quantity:
            # Rollback and raise error if insufficient stock
            db.rollback()
            raise ValueError(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}")
        
        order_item = models.OrderItem(
            order_id=db_order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=float(product.price),
            total_price=float(product.price * cart_item.quantity),
            product_name=product.name,
            product_sku=product.sku
        )
        db.add(order_item)
        
        # Reduce stock quantity if tracking is enabled
        if product.track_inventory:
            product.stock_quantity -= cart_item.quantity
    
    # Clear cart after creating order
    clear_session_cart(db, session_id)
    
    db.commit()
    return db_order

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()