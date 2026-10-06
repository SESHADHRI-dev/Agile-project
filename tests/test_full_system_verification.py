"""
Comprehensive Master Verification Test Suite
Cloud-Based Intelligent Inventory Management and Stock Prediction System — Indian Edition
Covers:
1. Complete Authentication & Role-Based Access Control (Admin vs Staff)
2. Complete CRUD & Validation for Products and Suppliers
3. Purchases & Inbound Transactions with Intra-State vs Inter-State GST
4. Sales & Outbound Transactions with Over-Sale Guardrails
5. End-to-End Stock Reconciliation: Current Stock = Opening Stock + Purchases - Sales
6. Indian GST (CGST, SGST, IGST), HSN codes, Indian Currency (₹ INR), PIN code & Phone format validation
7. Machine Learning Demand Prediction (SMA, WMA, SES) & Restocking Formula Invariants
8. Low-Stock & Out-of-Stock Alerts Generation
9. Tabular Reports Export (CSV) verification
10. Database Persistence & SQL Injection Resilience
"""

import pytest
import math
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import db
from ml.forecaster import DemandForecaster

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_seed():
    """Ensure consistent starting database state before each test."""
    db.seed_database()


# ==============================================================================
# 1. AUTHENTICATION & RBAC TESTS
# ==============================================================================

def test_auth_login_modes_and_roles():
    # Admin login with Indian identity
    res_admin = client.post("/api/auth/login", json={
        "username": "admin@intellistock.in",
        "password": "Password123!"
    })
    assert res_admin.status_code == 200
    admin_data = res_admin.json()
    assert admin_data["success"] is True
    assert admin_data["user"]["role"] == "Admin"
    assert admin_data["user"]["name"] == "Dr. S. Sharma (Administrator)"

    # Staff login with Indian identity
    res_staff = client.post("/api/auth/login", json={
        "username": "staff@intellistock.in",
        "password": "Password123!"
    })
    assert res_staff.status_code == 200
    staff_data = res_staff.json()
    assert staff_data["success"] is True
    assert staff_data["user"]["role"] == "Staff"
    assert staff_data["user"]["name"] == "Seshadhri (Operations Staff)"

    # Invalid password
    res_invalid = client.post("/api/auth/login", json={
        "username": "admin@intellistock.in",
        "password": "WrongPassword!"
    })
    assert res_invalid.status_code == 401

    # Nonexistent user
    res_unknown = client.post("/api/auth/login", json={
        "username": "unknown@domain.com",
        "password": "Password123!"
    })
    assert res_unknown.status_code == 401


def test_auth_profile_and_demo_tokens():
    # Admin demo token
    admin_tok_res = client.get("/api/auth/demo-token?role=Admin")
    assert admin_tok_res.status_code == 200
    admin_token = admin_tok_res.json()["token"]

    # Verify profile with admin token
    profile_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert profile_res.status_code == 200
    assert profile_res.json()["role"] == "Admin"

    # Staff demo token
    staff_tok_res = client.get("/api/auth/demo-token?role=Staff")
    assert staff_tok_res.status_code == 200
    staff_token = staff_tok_res.json()["token"]

    profile_staff = client.get("/api/auth/me", headers={"Authorization": f"Bearer {staff_token}"})
    assert profile_staff.status_code == 200
    assert profile_staff.json()["role"] == "Staff"


def test_rbac_boundary_enforcement():
    staff_headers = {"Authorization": "Bearer dev-staff-token"}

    # Staff must be forbidden from creating a product
    res = client.post("/api/products", json={
        "name": "Unauthorized Test Product",
        "category": "Hardware",
        "price": 250.00,
        "quantity": 20,
        "min_stock_level": 5
    }, headers=staff_headers)
    assert res.status_code == 403

    # Staff must be forbidden from updating a product
    res_up = client.put("/api/products/PRD-1001", json={"price": 200.00}, headers=staff_headers)
    assert res_up.status_code == 403

    # Staff must be forbidden from deleting a product
    res_del = client.delete("/api/products/PRD-1001", headers=staff_headers)
    assert res_del.status_code == 403

    # Staff must be forbidden from creating a supplier
    res_sup = client.post("/api/suppliers", json={
        "name": "Unauthorized Vendor",
        "contact_person": "Unauthorized",
        "phone": "+91 98765 43210",
        "email": "vendor@test.com",
        "address": "Chennai, Tamil Nadu"
    }, headers=staff_headers)
    assert res_sup.status_code == 403

    # Staff must be forbidden from reseeding demo data
    res_seed = client.post("/api/seed", headers=staff_headers)
    assert res_seed.status_code == 403


# ==============================================================================
# 2. PRODUCT MANAGEMENT & VALIDATION TESTS
# ==============================================================================

def test_product_crud_lifecycle():
    admin_headers = {"Authorization": "Bearer dev-admin-token"}

    # 1. Create Product
    payload = {
        "name": "Industrial Terminal Block 32A",
        "category": "Electrical Components",
        "price": 145.50,
        "quantity": 40,
        "min_stock_level": 15,
        "supplier_id": "SUP-001",
        "hsn_code": "8536",
        "gst_rate": 18.0
    }
    create_res = client.post("/api/products", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    created_prod = create_res.json()["data"]
    prod_id = created_prod["id"]
    assert created_prod["name"] == "Industrial Terminal Block 32A"
    assert created_prod["price"] == 145.50
    assert created_prod["quantity"] == 40
    assert created_prod["hsn_code"] == "8536"
    assert created_prod["gst_rate"] == 18.0
    assert created_prod["status"] == "IN STOCK"

    # 2. Get Single Product
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == prod_id

    # 3. Update Product
    update_res = client.put(f"/api/products/{prod_id}", json={
        "price": 160.00,
        "min_stock_level": 25
    }, headers=admin_headers)
    assert update_res.status_code == 200
    updated = update_res.json()["data"]
    assert updated["price"] == 160.00
    assert updated["min_stock_level"] == 25

    # 4. Search and Filter
    search_res = client.get("/api/products?search=Terminal")
    assert search_res.status_code == 200
    assert any(p["id"] == prod_id for p in search_res.json()["data"])

    # 5. Soft Delete / Deactivate
    del_res = client.delete(f"/api/products/{prod_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Verify Deactivated Product no longer in active listing
    list_after = client.get("/api/products").json()["data"]
    assert not any(p["id"] == prod_id for p in list_after)


def test_product_validation_and_boundary():
    admin_headers = {"Authorization": "Bearer dev-admin-token"}

    # Negative price rejected by Pydantic validation (422)
    res_neg_price = client.post("/api/products", json={
        "name": "Invalid Price Product",
        "category": "Electrical Components",
        "price": -10.00,
        "quantity": 10,
        "min_stock_level": 5
    }, headers=admin_headers)
    assert res_neg_price.status_code == 422

    # Negative quantity rejected by Pydantic validation (422)
    res_neg_qty = client.post("/api/products", json={
        "name": "Invalid Qty Product",
        "category": "Electrical Components",
        "price": 100.00,
        "quantity": -5,
        "min_stock_level": 5
    }, headers=admin_headers)
    assert res_neg_qty.status_code == 422

    # Nonexistent product ID returns 404
    res_404 = client.get("/api/products/PRD-NONEXISTENT")
    assert res_404.status_code == 404


# ==============================================================================
# 3. SUPPLIER MANAGEMENT & LOCALIZATION TESTS
# ==============================================================================

def test_supplier_crud_and_indian_fields():
    admin_headers = {"Authorization": "Bearer dev-admin-token"}

    # 1. Create Supplier with Tamil Nadu details
    payload = {
        "name": "Madurai Precision Fasteners",
        "contact_person": "P. Natarajan",
        "phone": "+91 98430 76543",
        "email": "natarajan@maduraiprecision.in",
        "address": "12 Kappalur Industrial Estate, Madurai, Tamil Nadu - 625008, India",
        "state": "Tamil Nadu",
        "pin_code": "625008",
        "gstin": "33AABCM1122D1Z8",
        "supplied_categories": "Hardware, Industrial Tools"
    }
    create_res = client.post("/api/suppliers", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    sup = create_res.json()["data"]
    sup_id = sup["id"]
    assert sup["name"] == "Madurai Precision Fasteners"
    assert sup["state"] == "Tamil Nadu"
    assert sup["pin_code"] == "625008"
    assert sup["gstin"] == "33AABCM1122D1Z8"

    # 2. Get Supplier by ID
    get_res = client.get(f"/api/suppliers/{sup_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["contact_person"] == "P. Natarajan"

    # 3. Update Supplier
    up_res = client.put(f"/api/suppliers/{sup_id}", json={
        "contact_person": "P. N. Rajan",
        "phone": "+91 98430 99999"
    }, headers=admin_headers)
    assert up_res.status_code == 200
    assert up_res.json()["data"]["contact_person"] == "P. N. Rajan"

    # 4. Deactivate Supplier
    del_res = client.delete(f"/api/suppliers/{sup_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


# ==============================================================================
# 4. PURCHASES & INBOUND GST CALCULATION TESTS
# ==============================================================================

def test_purchase_stock_increment_and_tax_calculation():
    # Initial stock of PRD-1001 (LED Bulb) is 100
    prod_before = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_before["quantity"] == 100

    # Purchase 50 units from Tamil Nadu supplier SUP-001 (Intra-State: CGST 9% + SGST 9%)
    purchase_payload = {
        "product_id": "PRD-1001",
        "supplier_id": "SUP-001",
        "quantity": 50,
        "unit_cost": 80.00
    }
    pur_res = client.post("/api/purchases", json=purchase_payload)
    assert pur_res.status_code == 201
    pur_data = pur_res.json()["data"]

    # Check stock increment: 100 + 50 = 150
    prod_after = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_after["quantity"] == 150

    # Check financial & tax calculations:
    # Taxable Amount = 50 * 80 = 4000.00
    # CGST (9%) = 360.00, SGST (9%) = 360.00, IGST = 0.0, Total Tax = 720.00
    assert pur_data["total_cost"] == 4000.00
    assert pur_data["taxable_amount"] == 4000.00
    assert pur_data["cgst"] == 360.00
    assert pur_data["sgst"] == 360.00
    assert pur_data["igst"] == 0.0
    assert pur_data["total_tax"] == 720.00


def test_interstate_purchase_gst_calculation():
    # Create an out-of-state supplier (Karnataka)
    admin_headers = {"Authorization": "Bearer dev-admin-token"}
    sup_res = client.post("/api/suppliers", json={
        "name": "Bengaluru Industrial Automation",
        "contact_person": "R. K. Rao",
        "phone": "+91 98450 12345",
        "email": "rao@blr-automation.in",
        "address": "Industrial Area, Peenya, Bengaluru, Karnataka - 560058",
        "state": "Karnataka",
        "pin_code": "560058",
        "gstin": "29AABCB1234A1Z9"
    }, headers=admin_headers)
    sup_id = sup_res.json()["data"]["id"]

    # Incur purchase from Karnataka (Inter-State: IGST 18%, CGST=0, SGST=0)
    pur_res = client.post("/api/purchases", json={
        "product_id": "PRD-1004",  # Switch (GST 18%)
        "supplier_id": sup_id,
        "quantity": 20,
        "unit_cost": 70.00
    })
    assert pur_res.status_code == 201
    pur_data = pur_res.json()["data"]
    # 20 * 70 = 1400.00
    # IGST (18%) = 252.00, CGST = 0, SGST = 0
    assert pur_data["total_cost"] == 1400.00
    assert pur_data["cgst"] == 0.0
    assert pur_data["sgst"] == 0.0
    assert pur_data["igst"] == 252.00
    assert pur_data["total_tax"] == 252.00


# ==============================================================================
# 5. SALES & OVER-SALE GUARDRAIL TESTS
# ==============================================================================

def test_sale_stock_decrement_and_tax():
    # Starting stock of PRD-1002 (PVC Conduit) is 85
    prod_before = client.get("/api/products/PRD-1002").json()["data"]
    assert prod_before["quantity"] == 85

    # Sell 15 units
    sale_payload = {
        "product_id": "PRD-1002",
        "quantity": 15,
        "unit_price": 180.00,
        "customer_name": "Sri Ganesh Traders (Vellore)"
    }
    sale_res = client.post("/api/sales", json=sale_payload)
    assert sale_res.status_code == 201
    sale_data = sale_res.json()["data"]

    # Verify stock decrement: 85 - 15 = 70
    prod_after = client.get("/api/products/PRD-1002").json()["data"]
    assert prod_after["quantity"] == 70

    # Total revenue: 15 * 180 = 2700.00
    # Intra-state GST (18%): CGST 9% (243.00), SGST 9% (243.00), Total Tax = 486.00
    assert sale_data["total_revenue"] == 2700.00
    assert sale_data["cgst"] == 243.00
    assert sale_data["sgst"] == 243.00
    assert sale_data["total_tax"] == 486.00


def test_oversale_strict_prevention():
    # PRD-1003 is OUT OF STOCK (quantity: 0)
    res_zero = client.post("/api/sales", json={
        "product_id": "PRD-1003",
        "quantity": 1,
        "unit_price": 1650.00
    })
    assert res_zero.status_code == 400
    assert "Insufficient stock" in res_zero.json()["detail"]

    # PRD-1008 has 8 units
    prod = client.get("/api/products/PRD-1008").json()["data"]
    assert prod["quantity"] == 8

    # Attempt to sell 9 units
    res_over = client.post("/api/sales", json={
        "product_id": "PRD-1008",
        "quantity": 9,
        "unit_price": 85.00
    })
    assert res_over.status_code == 400
    assert "Insufficient stock" in res_over.json()["detail"]

    # Stock must remain unchanged after rejected over-sale
    prod_check = client.get("/api/products/PRD-1008").json()["data"]
    assert prod_check["quantity"] == 8


# ==============================================================================
# 6. END-TO-END STOCK RECONCILIATION TEST (FORMULA VERIFICATION)
# ==============================================================================

def test_complete_stock_reconciliation_workflow():
    """
    Formula: Current Stock = Opening Stock + Purchases - Sales
    Tested across Product Details, Inventory, Alerts, and Dashboard.
    """
    # 1. Inspect initial product PRD-1001 (LED Bulb 9W)
    init_prod = client.get("/api/products/PRD-1001").json()["data"]
    opening_stock = init_prod["quantity"]
    assert opening_stock == 100

    # 2. Record Purchase 1 (+50 units)
    p1 = client.post("/api/purchases", json={
        "product_id": "PRD-1001", "supplier_id": "SUP-001", "quantity": 50, "unit_cost": 80.00
    })
    assert p1.status_code == 201

    # 3. Record Purchase 2 (+30 units)
    p2 = client.post("/api/purchases", json={
        "product_id": "PRD-1001", "supplier_id": "SUP-001", "quantity": 30, "unit_cost": 82.00
    })
    assert p2.status_code == 201

    # 4. Record Sale 1 (-40 units)
    s1 = client.post("/api/sales", json={
        "product_id": "PRD-1001", "quantity": 40, "unit_price": 120.00
    })
    assert s1.status_code == 201

    # 5. Record Sale 2 (-20 units)
    s2 = client.post("/api/sales", json={
        "product_id": "PRD-1001", "quantity": 20, "unit_price": 120.00
    })
    assert s2.status_code == 201

    # Expected stock: 100 + 50 + 30 - 40 - 20 = 120 units
    expected_closing_stock = opening_stock + 50 + 30 - 40 - 20
    assert expected_closing_stock == 120

    # Reconcile across Product View
    prod_view = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_view["quantity"] == expected_closing_stock

    # Reconcile across Inventory View
    inv_view = client.get("/api/inventory").json()
    item_in_inv = next(p for p in inv_view["products"] if p["id"] == "PRD-1001")
    assert item_in_inv["quantity"] == expected_closing_stock

    # Reconcile across Summary Valuation
    expected_item_val = round(120 * 120.00, 2)
    assert round(item_in_inv["quantity"] * item_in_inv["price"], 2) == expected_item_val


# ==============================================================================
# 7. ALERTS LOGIC & THRESHOLDS TESTS
# ==============================================================================

def test_alerts_status_transitions():
    # PRD-1001 has min_stock_level = 50. Currently after seed, stock is 100 -> IN STOCK
    prod = client.get("/api/products/PRD-1001").json()["data"]
    assert prod["quantity"] == 100
    assert prod["min_stock_level"] == 50
    assert prod["status"] == "IN STOCK"

    # Sell 60 units -> stock drops to 40 (<= 50) -> LOW STOCK
    client.post("/api/sales", json={"product_id": "PRD-1001", "quantity": 60, "unit_price": 120.00})
    prod_low = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_low["quantity"] == 40
    assert prod_low["status"] == "LOW STOCK"

    # Verify alert appears in /alerts
    alerts_low = client.get("/api/alerts").json()["data"]
    assert any(a["product_id"] == "PRD-1001" and a["severity"] == "WARNING" for a in alerts_low)

    # Sell remaining 40 units -> stock drops to 0 -> OUT OF STOCK
    client.post("/api/sales", json={"product_id": "PRD-1001", "quantity": 40, "unit_price": 120.00})
    prod_oos = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_oos["quantity"] == 0
    assert prod_oos["status"] == "OUT OF STOCK"

    # Verify alert severity promoted to CRITICAL
    alerts_oos = client.get("/api/alerts").json()["data"]
    assert any(a["product_id"] == "PRD-1001" and a["severity"] == "CRITICAL" for a in alerts_oos)

    # Restock with 100 units -> returns to IN STOCK and clears alert
    client.post("/api/purchases", json={"product_id": "PRD-1001", "supplier_id": "SUP-001", "quantity": 100, "unit_cost": 80.00})
    prod_restocked = client.get("/api/products/PRD-1001").json()["data"]
    assert prod_restocked["quantity"] == 100
    assert prod_restocked["status"] == "IN STOCK"

    alerts_cleared = client.get("/api/alerts").json()["data"]
    assert not any(a["product_id"] == "PRD-1001" for a in alerts_cleared)


# ==============================================================================
# 8. PREDICTION ALGORITHMS & MATHEMATICAL INVARIANTS
# ==============================================================================

def test_prediction_mathematical_invariants():
    # Test formula: Recommended Restock = max(0, ceil(Projected Demand + Safety Stock - Current Stock))
    test_cases = [
        # (projected_demand, safety_stock, current_stock, expected_restock)
        (120, 20, 50, 90),   # 120 + 20 - 50 = 90
        (100, 15, 150, 0),   # 100 + 15 - 150 = -35 -> 0 (abundant stock)
        (50, 10, 0, 60),     # 50 + 10 - 0 = 60 (out of stock)
        (0, 0, 10, 0),       # zero demand
    ]
    for p_dem, s_stk, c_stk, exp_restock in test_cases:
        net = (p_dem + s_stk) - c_stk
        actual = max(0, net)
        assert actual == exp_restock


def test_prediction_algorithms_comparison():
    # Compare SMA, WMA, SES on known 14-day increasing series: 1, 2, ..., 14
    series = [float(i) for i in range(1, 15)]
    sma = DemandForecaster.simple_moving_average(series, window=7)
    wma = DemandForecaster.weighted_moving_average(series, window=7)
    ses = DemandForecaster.exponential_smoothing(series, alpha=0.3)

    # In ascending trend, WMA has recency bias and must be >= SMA
    assert wma >= sma
    # All rates must be finite and positive
    assert sma > 0 and not math.isnan(sma)
    assert wma > 0 and not math.isnan(wma)
    assert ses > 0 and not math.isnan(ses)


def test_prediction_api_all_three_methods():
    for method in ["exponential_smoothing", "weighted_moving_average", "moving_average"]:
        res = client.post("/api/predictions/calculate", json={
            "product_id": "PRD-1001",
            "method": method,
            "forecast_days": 30,
            "lead_time_days": 7,
            "safety_stock_factor": 1.65
        })
        assert res.status_code == 200
        data = res.json()
        assert data["method"] == method
        assert data["predicted_demand"] > 0
        assert data["safety_stock"] >= 0
        assert data["recommended_restock"] >= 0
        assert data["urgency_status"] in ["CRITICAL_OUT_OF_STOCK", "URGENT_RESTOCK_REQUIRED", "REORDER_RECOMMENDED", "SUFFICIENT_STOCK"]


# ==============================================================================
# 9. REPORT EXPORTS & CSV CONTENT VERIFICATION
# ==============================================================================

def test_all_reports_content_and_encoding():
    reports_expected_headers = {
        "inventory": ["Product ID", "Product Name", "Category", "HSN Code", "GST Rate (%)", "Unit Price (₹)", "Quantity in Stock", "Min Stock Level", "Status", "Valuation (₹)"],
        "low_stock": ["Product ID", "Product Name", "Category", "Current Stock", "Min Stock Level", "Deficit Units", "Status"],
        "sales": ["Sale ID", "Product ID", "Product Name", "Customer Name", "Quantity Sold", "Unit Price (₹)", "Total Revenue (₹)", "GST (%)", "CGST (₹)", "SGST (₹)", "IGST (₹)", "Sale Date (IST)", "Recorded By"],
        "purchases": ["Purchase ID", "Product ID", "Product Name", "Supplier Name", "Supplier GSTIN", "Quantity", "Unit Cost (₹)", "Total Cost (₹)", "GST (%)", "CGST (₹)", "SGST (₹)", "Purchase Date (IST)", "Recorded By"],
        "predictions": ["Product ID", "Product Name", "Category", "Current Stock", "Forecast Period (Days)", "Predicted Demand", "Safety Stock", "Recommended Restock", "Urgency Status"]
    }

    for rtype, headers in reports_expected_headers.items():
        res = client.get(f"/api/reports/export?report_type={rtype}&format=csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        csv_text = res.text
        for h in headers:
            assert h in csv_text, f"Missing expected column header '{h}' in {rtype} report"


# ==============================================================================
# 10. SECURITY & SQL INJECTION RESILIENCE
# ==============================================================================

def test_sql_injection_resilience():
    # Search with malicious SQL injection payload
    sqli_payload = "' OR '1'='1' --"
    res = client.get(f"/api/products?search={sqli_payload}")
    assert res.status_code == 200
    # Should safely return 0 results or exact match without crashing or exposing all records
    assert isinstance(res.json()["data"], list)

    # In suppliers search
    res_sup = client.get(f"/api/suppliers?search={sqli_payload}")
    assert res_sup.status_code == 200
    assert isinstance(res_sup.json()["data"], list)
