"""
Add sample reviews to products for testing dynamic ratings
"""
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
import random

def add_sample_reviews():
    db = SessionLocal()
    try:
        # Get all products
        products = db.query(models.Product).all()
        
        # Get all users (for reviewer attribution)
        users = db.query(models.User).all()
        
        if not users:
            print("No users found. Please create at least one user first.")
            return
        
        if not products:
            print("No products found. Please create products first.")
            return
        
        print(f"Found {len(products)} products and {len(users)} users")
        
        # Sample review data
        review_titles = [
            "Excellent product!",
            "Really works!",
            "Great quality",
            "Highly recommend",
            "Good value for money",
            "Very effective",
            "Amazing results",
            "Worth every penny",
            "Life changing",
            "Best purchase ever"
        ]
        
        review_comments = [
            "This product has exceeded my expectations. I've been using it for a month now and can see real results.",
            "Great quality product. Definitely worth the price. Will buy again!",
            "I was skeptical at first, but this really works. Highly recommended!",
            "Been using this for 3 weeks now and I'm very satisfied with the results.",
            "Excellent Ayurvedic formulation. Natural and effective.",
            "My family has been using this for months now. Very happy with the product.",
            "Good product with visible benefits. Delivery was also quick.",
            "This is authentic and effective. Much better than other brands I've tried.",
            "The quality is superb. I can feel the difference in my health.",
            "Highly effective product. Noticed improvements within 2 weeks."
        ]
        
        reviews_added = 0
        
        # Add 2-5 reviews for each product
        for product in products:
            num_reviews = random.randint(2, 5)
            
            for _ in range(num_reviews):
                review = models.Review(
                    user_id=random.choice(users).id,
                    product_id=product.id,
                    rating=random.randint(4, 5),  # Random rating between 4-5 stars
                    title=random.choice(review_titles),
                    comment=random.choice(review_comments),
                    is_verified_purchase=random.choice([True, False]),
                    is_approved=True
                )
                db.add(review)
                reviews_added += 1
        
        db.commit()
        print(f"\n✓ Successfully added {reviews_added} sample reviews to {len(products)} products!")
        
        # Show some statistics
        print("\nRating Statistics:")
        for product in products:
            reviews = db.query(models.Review).filter(
                models.Review.product_id == product.id,
                models.Review.is_approved == True
            ).all()
            
            if reviews:
                avg_rating = sum(r.rating for r in reviews) / len(reviews)
                print(f"  {product.name}: {avg_rating:.1f} stars ({len(reviews)} reviews)")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Adding sample reviews to products...")
    add_sample_reviews()
