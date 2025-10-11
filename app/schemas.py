from pydantic import BaseModel, EmailStr, validator, model_validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class UserRole(str, Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Address Schemas
class AddressBase(BaseModel):
    title: str
    full_name: str
    phone: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(AddressBase):
    pass

class Address(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Vendor Schemas
class VendorBase(BaseModel):
    business_name: str
    business_description: Optional[str] = None
    business_email: Optional[str] = None
    business_phone: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    business_address: Optional[str] = None
    logo_url: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(VendorBase):
    pass

class Vendor(VendorBase):
    id: int
    user_id: int
    is_verified: bool
    is_active: bool
    commission_rate: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    created_at: datetime
    subcategories: List['Category'] = []
    
    class Config:
        from_attributes = True

# Product Image Schemas
class ProductImageBase(BaseModel):
    image_url: str
    alt_text: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0

class ProductImageCreate(ProductImageBase):
    pass

class ProductImage(ProductImageBase):
    id: int
    
    class Config:
        from_attributes = True

# Product Variant Schemas
class ProductVariantBase(BaseModel):
    name: str
    value: str
    price_adjustment: float = 0.0
    stock_quantity: int = 0
    sku_suffix: Optional[str] = None

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariant(ProductVariantBase):
    id: int
    
    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    name: str
    slug: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    price: float
    compare_price: Optional[float] = None
    stock_quantity: int = 0
    low_stock_threshold: int = 10
    track_inventory: bool = True
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: ProductStatus = ProductStatus.ACTIVE
    is_featured: bool = False
    is_digital: bool = False
    requires_shipping: bool = True

class ProductCreate(ProductBase):
    vendor_id: int
    category_id: int
    sku: str
    images: Optional[List[ProductImageCreate]] = []
    variants: Optional[List[ProductVariantCreate]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    price: Optional[float] = None
    compare_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    track_inventory: Optional[bool] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ProductStatus] = None
    is_featured: Optional[bool] = None
    is_digital: Optional[bool] = None
    requires_shipping: Optional[bool] = None
    category_id: Optional[int] = None
    images: Optional[List[ProductImageCreate]] = []
    variants: Optional[List[ProductVariantCreate]] = []

class Product(ProductBase):
    id: int
    vendor_id: int
    category_id: int
    sku: str
    cost_price: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relationships
    vendor: Optional[Vendor] = None
    category: Optional[Category] = None
    images: List[ProductImage] = []
    variants: List[ProductVariant] = []
    
    # Rating information (computed from reviews)
    average_rating: Optional[float] = None
    review_count: int = 0
    
    class Config:
        from_attributes = True

# Cart Schemas
class CartItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = 1

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    product_id: int
    quantity: int

class CartItem(CartItemBase):
    id: int
    user_id: int
    added_at: datetime
    updated_at: Optional[datetime] = None
    
    product: Optional[Product] = None
    variant: Optional[ProductVariant] = None
    
    class Config:
        from_attributes = True

# Order Schemas
class OrderItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    unit_price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    product_name: str
    product_sku: str
    variant_name: Optional[str] = None
    total_price: float
    
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    customer_notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    admin_notes: Optional[str] = None

class Order(OrderBase):
    id: int
    order_number: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: Optional[str] = None
    subtotal: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total_amount: float
    status: OrderStatus
    payment_status: PaymentStatus
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    user: Optional[User] = None
    items: List[OrderItem] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    status_counts: Dict[str, int] = Field(default_factory=dict)
    payment_status_counts: Dict[str, int] = Field(default_factory=dict)


class OrderListResponse(BaseModel):
    items: List[Order]
    meta: PaginationMeta

# Payment Schemas
class PaymentBase(BaseModel):
    payment_method: str
    amount: float
    currency: str = "INR"

class PaymentCreate(PaymentBase):
    order_id: int

class Payment(PaymentBase):
    id: int
    order_id: int
    payment_id: str
    status: PaymentStatus
    gateway_response: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Review Schemas
class ReviewBase(BaseModel):
    product_id: int
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    comment: Optional[str] = None

class Review(ReviewBase):
    id: int
    user_id: int
    order_id: Optional[int] = None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    
    user: Optional[User] = None
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

# Coupon Schemas
class CouponBase(BaseModel):
    code: str
    description: str
    discount_type: str  # 'percentage' or 'fixed'
    discount_value: float
    minimum_amount: float = 0.0
    maximum_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    user_usage_limit: int = 1
    valid_from: datetime
    valid_until: datetime

class CouponCreate(CouponBase):
    pass

class CouponUpdate(CouponBase):
    is_active: Optional[bool] = None

class Coupon(CouponBase):
    id: int
    usage_count: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Keep backward compatibility schemas
class BenefitBase(BaseModel):
    text: str

class BenefitCreate(BenefitBase):
    pass

class Benefit(BenefitBase):
    id: int
    class Config:
        from_attributes = True

class IngredientBase(BaseModel):
    name: str
    latin: str
    quantity: str
    description: str

class IngredientCreate(IngredientBase):
    pass

class Ingredient(IngredientBase):
    id: int
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Response Schemas
class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

# Checkout and Order Schemas
class AddressBase(BaseModel):
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "USA"
    full_name: Optional[str] = None
    phone: Optional[str] = None

class CustomerInfoBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: str
    phone: str

class CheckoutCreate(BaseModel):
    customer_info: Optional[CustomerInfoBase] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: AddressBase
    billing_address: Optional[AddressBase] = None
    payment_method: str
    notes: Optional[str] = None
    use_same_address: bool = True

    @model_validator(mode="before")
    def populate_customer_info(cls, values: Dict[str, Any]):
        if "customer_info" not in values or values.get("customer_info") is None:
            full_name = values.get("customer_name") or "Guest"
            email = values.get("customer_email")
            phone = values.get("customer_phone")

            first_name = full_name.strip()
            last_name = None

            if " " in first_name:
                first_name, last_name = first_name.split(" ", 1)

            if email or phone:
                values["customer_info"] = {
                    "first_name": first_name or "Guest",
                    "last_name": last_name,
                    "email": email or "",
                    "phone": phone or ""
                }
        return values

    @model_validator(mode="after")
    def ensure_customer_info(cls, model: "CheckoutCreate"):
        if not model.customer_info:
            raise ValueError("Customer information is required for checkout")

        if model.use_same_address and model.billing_address is None:
            model.billing_address = model.shipping_address

        return model

class CheckoutRequest(BaseModel):
    # Customer info (for guest checkout)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Addresses
    shipping_address: AddressBase
    billing_address: Optional[AddressBase] = None
    
    # Payment
    payment_method: str  # cash_on_delivery, online_payment, upi, etc.
    
    # Optional
    notes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None

class PaymentRequest(BaseModel):
    order_id: str
    payment_method: str
    amount: float

class PaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None  # For online payments
    message: str

# Razorpay Payment Schemas
class PaymentOrderCreate(BaseModel):
    amount: float
    currency: Optional[str] = "INR"
    customer_email: Optional[str] = None
    items_count: Optional[int] = 0

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    order_data: CheckoutRequest

class RefundCreate(BaseModel):
    payment_id: str
    amount: float
    notes: Optional[Dict[str, Any]] = None

# Wishlist Schemas
class WishlistBase(BaseModel):
    product_id: int

class WishlistCreate(WishlistBase):
    pass

class Wishlist(WishlistBase):
    id: int
    user_id: int
    created_at: datetime
    product: Optional[Product] = None
    
    class Config:
        from_attributes = True

# Update Category for self-reference
Category.model_rebuild()