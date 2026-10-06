# REST API Documentation

**Base URL (Local):** `http://localhost:8000/api`  
**Base URL (AWS API Gateway):** `https://{api-id}.execute-api.{region}.amazonaws.com/prod/api`  
**Content-Type:** `application/json`  

---

## 1. Authentication Endpoints

### 1.1 User Login
- **Endpoint:** `POST /auth/login`
- **Description:** Authenticates user credentials via Cognito (AWS Production Mode) or Local Auth Provider (Local Dev Mode).
- **Request Body:**
  ```json
  {
    "username": "admin@inventory.io",
    "password": "Password123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "token": "dev-admin-token",
    "user": {
      "id": "USR-001",
      "username": "admin@inventory.io",
      "role": "Admin",
      "name": "Dr. S. Sharma (Administrator)"
    }
  }
  ```

### 1.2 Authentication Mode Discovery
- **Endpoint:** `GET /auth/config`
- **Description:** Handshake endpoint returning current authentication and storage runtime configuration.
- **Response (200 OK):**
  ```json
  {
    "auth_mode": "local",
    "storage_mode": "local",
    "is_local": true,
    "cognito_configured": false,
    "default_admin": {
      "username": "admin@inventory.io",
      "role": "Admin",
      "name": "Dr. S. Sharma (Administrator)"
    }
  }
  ```

### 1.3 Rapid Local Demo Token
- **Endpoint:** `GET /auth/demo-token?role=Admin`
- **Description:** Generates instant dev Bearer token for automated tests or local evaluation without AWS Cognito dependency.
- **Query Parameters:** `role` (`Admin` or `Staff`, defaults to `Admin`).
- **Response (200 OK):**
  ```json
  {
    "token": "dev-admin-token",
    "token_type": "bearer",
    "user": {
      "id": "USR-LOCAL-ADMIN",
      "username": "admin@inventory.io",
      "role": "Admin",
      "name": "Dr. S. Sharma (Administrator)"
    }
  }
  ```

---

## 2. Product Management

### 2.1 List All Products
- **Endpoint:** `GET /products`
- **Query Parameters:**
  - `search` (string, optional): Search by product name or ID.
  - `category` (string, optional): Filter by category.
  - `sort_by` (string, optional): `name`, `price`, `quantity`, `created_at`.
  - `order` (string, optional): `asc`, `desc`.
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "count": 15,
    "data": [
      {
        "id": "PRD-1001",
        "name": "LED Bulb 9W Cool Day White (B22)",
        "category": "Electrical Components",
        "price": 120.00,
        "quantity": 100,
        "min_stock_level": 50,
        "supplier_id": "SUP-001",
        "supplier_name": "Sri Lakshmi Industrial Supplies",
        "hsn_code": "8539",
        "gst_rate": 18.0,
        "status": "IN STOCK",
        "is_active": true
      }
    ]
  }
  ```

### 2.2 Create Product
- **Endpoint:** `POST /products`
- **Authorization:** `Admin`
- **Request Body:**
  ```json
  {
    "name": "Modular Electrical Switch 16A (1-Way)",
    "category": "Electrical Components",
    "price": 95.00,
    "quantity": 22,
    "min_stock_level": 15,
    "supplier_id": "SUP-001",
    "hsn_code": "8536",
    "gst_rate": 18.0
  }
  ```
- **Response (201 Created):** Created product record.

### 2.3 Update Product
- **Endpoint:** `PUT /products/{id}`
- **Authorization:** `Admin`
- **Request Body:** Partial or complete product fields.

### 2.4 Delete / Deactivate Product
- **Endpoint:** `DELETE /products/{id}`
- **Authorization:** `Admin`

---

## 3. Supplier Management

### 3.1 List Suppliers
- **Endpoint:** `GET /suppliers`
- **Query Parameters:** `search`

### 3.2 Create Supplier
- **Endpoint:** `POST /suppliers`
- **Authorization:** `Admin`
- **Request Body:**
  ```json
  {
    "name": "Sri Lakshmi Industrial Supplies",
    "contact_person": "K. Sundaram",
    "phone": "+91 98421 54321",
    "email": "orders@srilakshmiind.in",
    "address": "148 GST Road, Guindy Industrial Estate, Chennai, Tamil Nadu - 600032, India",
    "supplied_categories": "Electrical Components, Industrial Tools",
    "gstin": "33AABCS1234A1Z1",
    "state": "Tamil Nadu",
    "pin_code": "600032"
  }
  ```

---

## 4. Purchase Transactions

### 4.1 Record Purchase Order
- **Endpoint:** `POST /purchases`
- **Description:** Records an inbound purchase order. Automatically increments inventory:
  $$\text{New Stock} = \text{Previous Stock} + \text{Purchased Quantity}$$
- **Request Body:**
  ```json
  {
    "product_id": "PRD-1001",
    "supplier_id": "SUP-001",
    "quantity": 50,
    "unit_cost": 95.00,
    "purchase_date": "2026-10-05T10:00:00Z"
  }
  ```
- **Response (201 Created):** Returns purchase transaction and updated product stock.

---

## 5. Sales Transactions

### 5.1 Record Customer Sale
- **Endpoint:** `POST /sales`
- **Description:** Records an outbound sale. Validates availability:
  - If $\text{Quantity Sold} > \text{Current Stock}$, returns `400 Bad Request` ("Cannot sell more than available stock").
  - Otherwise, deducts stock and logs the sale for demand modeling.
- **Request Body:**
  ```json
  {
    "product_id": "PRD-1001",
    "quantity": 5,
    "unit_price": 149.99,
    "sale_date": "2026-10-05T14:30:00Z"
  }
  ```
- **Response (201 Created):** Returns sale record and new stock balance.

---

## 6. Inventory & Low-Stock Alerts

### 6.1 Get Inventory Overview
- **Endpoint:** `GET /inventory`
- **Response:**
  ```json
  {
    "success": true,
    "total_products": 15,
    "total_units": 842,
    "total_inventory_value": 78940.50,
    "low_stock_count": 3,
    "out_of_stock_count": 1,
    "items": []
  }
  ```

### 6.2 Get Live Alerts
- **Endpoint:** `GET /alerts`
- **Description:** Returns active alerts for out-of-stock and low-stock products.

---

## 7. Intelligent Demand Forecasting

### 7.1 Calculate Demand Prediction & Restocking
- **Endpoint:** `POST /predictions/calculate`
- **Request Body:**
  ```json
  {
    "product_id": "PRD-1001",
    "method": "exponential_smoothing",
    "forecast_days": 30,
    "lead_time_days": 7,
    "safety_stock_factor": 1.65
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "product_id": "PRD-1001",
    "product_name": "LED Bulb 9W Cool Day White (B22)",
    "method_used": "Single Exponential Smoothing (alpha=0.3)",
    "historical_days_analyzed": 45,
    "total_historical_sales": 142,
    "forecast_period_days": 30,
    "predicted_demand": 72,
    "current_stock": 100,
    "safety_stock": 14,
    "recommended_restock": 0,
    "status": "SUFFICIENT_STOCK"
  }
  ```

---

## 8. Reports & Demo Seeding

### 8.1 Export Report (CSV / PDF)
- **Endpoint:** `GET /reports/export?report_type=inventory&format=csv`
- **Response:** CSV raw content or downloadable S3 pre-signed URL.

### 8.2 Seed Realistic Demo Data
- **Endpoint:** `POST /seed`
- **Description:** Populates 15 products, 5 suppliers, and 60+ historical sales and purchases across dates.
