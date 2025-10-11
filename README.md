# 🛒 SAPTNOVA eCommerce - Backend API

FastAPI-based backend for multi-vendor eCommerce platform with Razorpay payment integration.

## 🚀 Features

- ✅ RESTful API with FastAPI
- ✅ JWT Authentication
- ✅ PostgreSQL Database
- ✅ Razorpay Payment Integration
- ✅ Multi-vendor Support
- ✅ Order Management
- ✅ Product Catalog
- ✅ Shopping Cart & Wishlist
- ✅ Admin & Vendor Panels

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL
- Razorpay Account

## 🔧 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AshokSaptnova/ecommerce-backend.git
   cd ecommerce-backend
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database:**
   ```bash
   # Update DATABASE_URL in .env
   python setup_db.py
   python migrate_payment_fields.py
   ```

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

## 🌐 API Documentation

Once running, visit:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## 🔐 Environment Variables

Create `.env` file with:

```env
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
ALLOWED_ORIGINS=http://localhost:3000
```

## 📦 Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** JWT (python-jose)
- **Payment:** Razorpay SDK
- **Validation:** Pydantic
- **CORS:** FastAPI CORS middleware

## 🚀 Deployment

### Render.com (Recommended)

1. Push to GitHub
2. Connect to Render.com
3. Render auto-detects `render.yaml`
4. Add environment variables
5. Deploy!

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

## 📝 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user

### Products
- `GET /products` - List products
- `GET /products/{id}` - Get product details
- `POST /products` - Create product (vendor)
- `PUT /products/{id}` - Update product (vendor)
- `DELETE /products/{id}` - Delete product (vendor)

### Cart
- `GET /cart` - Get cart items
- `POST /cart/items` - Add to cart
- `PUT /cart/items/{id}` - Update cart item
- `DELETE /cart/items/{id}` - Remove from cart

### Orders
- `POST /orders/checkout` - Place order
- `GET /orders` - List orders
- `GET /orders/{id}` - Get order details

### Payments
- `POST /payments/create-order` - Create Razorpay order
- `POST /payments/verify` - Verify payment
- `GET /payments/payment/{id}` - Get payment details
- `POST /payments/refund` - Process refund (admin)

### Wishlist
- `GET /wishlist` - Get wishlist items
- `POST /wishlist` - Add to wishlist
- `DELETE /wishlist/{id}` - Remove from wishlist

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Ashok Saptnova**
- GitHub: [@AshokSaptnova](https://github.com/AshokSaptnova)

## 🙏 Acknowledgments

- FastAPI framework
- Razorpay payment gateway
- SQLAlchemy ORM

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Backend Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** October 11, 2025
