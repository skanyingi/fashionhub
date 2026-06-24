# FashionHub E-Commerce Platform

FashionHub is a professional-grade, deployment-ready e-commerce platform built with Python (Django). It features a highly normalized database, robust payment integrations, and automated delivery calculations, specifically designed for the Kenyan fashion retail market.

##  Key Features

- **3NF Database Architecture:** Fully normalized schema ensuring high data integrity and "Price Persistence" (historical price stability).
- **M-Pesa Integration:** Real-world payment processing using M-Pesa STK Push with automated callback verification.
- **Geospatial Logistics:** Real-time delivery fee calculation using the Google Maps API based on precise customer location.
- **Professional Review System:** Features 'Verified Purchase' badges and peer-voted 'Helpful' engagement logic.
- **Admin BI Dashboard:** Automated reporting suite for sales analysis, inventory tracking, and low-stock alerts.
- **Real-time UI:** Powered by Alpine.js and HTMX for an "App-like" experience with partial-page updates.
- **Automated Document Generation:** Instant PDF receipt generation and email dispatch upon successful payment.

## 🛠 Tech Stack

- **Backend:** Python 3.11, Django 5.2
- **Frontend:** HTML5, CSS3, Alpine.js, HTMX
- **Database:** PostgreSQL (with 3NF normalization)
- **APIs:** M-Pesa Daraja API, Google Maps Platform
- **Testing:** Pytest, Playwright (E2E), Django TestCase
- **Infrastructure:** Gunicorn, WhiteNoise, Render (Deployment)

## 🏁 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Google Maps API Key
- M-Pesa Consumer Key/Secret

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd FashionV3
   ```

2. **Set up Virtual Environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   playwright install
   ```

4. **Configure Environment:**
   Create a `.env` file in the root directory and provide your API keys and database credentials.

5. **Run Migrations & Initialize:**

   ```bash
   python manage.py migrate

   # Load all products
   python manage.py loaddata shop/fixtures/products.json

   # Or load the full database export (products + orders + users + etc.)
   python manage.py loaddata database_export.json
   ```

6. **Start Server:**
   ```bash
   python manage.py runserver
   ```

##  Testing

FashionHub includes a comprehensive suite of **55 automated tests**. To run the tests:

```bash
# Run all tests
python manage.py test shop.test

# Run E2E tests (Playwright)
pytest shop/test/e2e
```

##  Database Design (ERD)

The project follows strict **Third Normal Form (3NF)** principles. Key entities include:

- **User/Buyer:** Authenticated customers.
- **Order & OrderItem:** Business contracts with price persistence.
- **Transaction:** Decoupled financial records for payment auditing.
- **Review & ReviewHelpful:** Social interaction and feedback.

## 📦 Exported Database

The file `database_export.json` is a complete database dump in Django fixture format. It contains **156 records** across all models including products (143), orders, order items, users, transactions, receipts, reports, and reviews.

### Sample Entry

```json
[
  {
    "model": "shop.product",
    "pk": 1,
    "fields": {
      "name": "dress",
      "description": "African wear with vibrant color good for outdoors",
      "price": 1500,
      "image": "products/w1.jpg",
      "category": "women",
      "subcategory": "clothing",
      "stock": 5
    }
  }
]
```

### Load the Export

```bash
python manage.py loaddata database_export.json
```

---
