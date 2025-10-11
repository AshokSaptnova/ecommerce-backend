from pydantic import BaseModel
from typing import List, Optional

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

class ProductBase(BaseModel):
    product_id: str
    name: str
    tagline: str
    category: str
    type: str
    packing: str
    mrp: int
    old_mrp: int
    dosage: str
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    benefits: List[BenefitCreate]
    ingredients: List[IngredientCreate]

class ProductUpdate(ProductBase):
    benefits: List[BenefitCreate]
    ingredients: List[IngredientCreate]

class Product(ProductBase):
    id: int
    benefits: List[Benefit] = []
    ingredients: List[Ingredient] = []
    class Config:
        from_attributes = True

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

class ProductBase(BaseModel):
    product_id: str
    name: str
    tagline: str
    category: str
    type: str
    packing: str
    mrp: int
    old_mrp: int
    dosage: str
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    benefits: List[BenefitCreate]
    ingredients: List[IngredientCreate]

class ProductUpdate(ProductBase):
    benefits: List[BenefitCreate]
    ingredients: List[IngredientCreate]

class Product(ProductBase):
    id: int
    benefits: List[Benefit]
    ingredients: List[Ingredient]
    class Config:
        orm_mode = True