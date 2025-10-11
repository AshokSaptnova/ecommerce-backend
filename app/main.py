from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, crud
from .database import engine, SessionLocal, get_db
from .routers import auth, products, cart, orders, categories, vendors, admin, addresses, wishlist, payments

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-Vendor eCommerce API",
    description="A comprehensive multi-vendor eCommerce platform API with user management, product catalog, shopping cart, orders, and payment processing",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(categories.router)
app.include_router(vendors.router)
app.include_router(admin.router)
app.include_router(addresses.router)
app.include_router(wishlist.router)
app.include_router(payments.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Legacy endpoints for backward compatibility
@app.get("/products", response_model=list[schemas.Product])
def read_products_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint - get all products"""
    return crud.get_products(db)

@app.get("/products/{product_id}", response_model=schemas.Product)
def read_product_legacy(product_id: str, db: Session = Depends(get_db)):
    """Legacy endpoint - get product by old product_id"""
    # Try to find by old product_id field for backward compatibility
    db_product = db.query(models.Product).filter(models.Product.sku == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.post("/products", response_model=schemas.Product)
def create_product_legacy(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """Legacy endpoint - create product"""
    return crud.create_product_legacy(db, product)

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product_legacy(product_id: str, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    """Legacy endpoint - update product"""
    db_product = crud.update_product(db, product_id, product)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.delete("/products/{product_id}")
def delete_product_legacy(product_id: str, db: Session = Depends(get_db)):
    """Legacy endpoint - delete product"""
    db_product = crud.delete_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Multi-Vendor eCommerce API is running"}

@app.get("/products", response_model=list[schemas.Product])
def read_products(db: Session = Depends(get_db)):
    return crud.get_products(db)

@app.get("/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: str, db: Session = Depends(get_db)):
    db_product = crud.get_product_by_id(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.post("/products", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: str, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_product = crud.update_product(db, product_id, product)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.delete("/products/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db)):
    db_product = crud.delete_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}