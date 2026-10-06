"""
Regression and Verification Tests for Audit Fixes:
1. Staff identity named Seshadhri
2. XLSX Excel exports for all report types
3. PDF exports for all report types
4. Admin vs Staff authorization on deletion
5. Product soft deletion lifecycle
6. Supplier soft deletion lifecycle
7. Demand prediction validation and execution
"""

import io
import pytest
import openpyxl
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import db

client = TestClient(app)

ADMIN_HEADERS = {"Authorization": "Bearer dev-admin-token-xyz"}
STAFF_HEADERS = {"Authorization": "Bearer dev-staff-token-abc"}


@pytest.fixture(autouse=True)
def setup_seed():
    db.seed_database()


def test_staff_identity_seshadhri():
    """Verify Staff display name is Seshadhri in auth login and profile."""
    res = client.post("/api/auth/login", json={
        "username": "staff@intellistock.in",
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Seshadhri" in data["user"]["name"]
    assert data["user"]["role"] == "Staff"

    # Profile verification via /api/auth/me
    prof_res = client.get("/api/auth/me", headers=STAFF_HEADERS)
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert "Seshadhri" in prof_data["name"]
    assert prof_data["role"] == "Staff"


@pytest.mark.parametrize("report_type", [
    "inventory",
    "low_stock",
    "sales",
    "purchases",
    "predictions",
])
def test_export_xlsx_all_reports(report_type):
    """Verify Excel .xlsx export generates valid openpyxl workbooks."""
    res = client.get(f"/api/reports/export?report_type={report_type}&format=xlsx", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    assert f"report_{report_type}_" in res.headers.get("content-disposition", "")
    assert res.headers.get("content-disposition", "").endswith(".xlsx")

    # Parse with openpyxl to ensure file integrity
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    sheet = wb.active
    assert sheet is not None
    # Verify title header
    title_cell = sheet.cell(row=1, column=1).value
    assert title_cell is not None
    # Row 4 is column headers
    header_vals = [cell.value for cell in sheet[4] if cell.value is not None]
    assert len(header_vals) > 0


@pytest.mark.parametrize("report_type", [
    "inventory",
    "low_stock",
    "sales",
    "purchases",
    "predictions",
])
def test_export_pdf_all_reports(report_type):
    """Verify PDF export generates valid PDF documents starting with %PDF-."""
    res = client.get(f"/api/reports/export?report_type={report_type}&format=pdf", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert f"report_{report_type}_" in res.headers.get("content-disposition", "")
    assert res.headers.get("content-disposition", "").endswith(".pdf")
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 500


def test_product_deletion_admin_and_staff_roles():
    """Verify Admin can delete products and Staff is forbidden (403)."""
    # 1. Create a product as Admin
    prod_data = {
        "name": "Deletable Test Product",
        "category": "Electronics & Electricals",
        "price": 250.0,
        "quantity": 50,
        "min_stock_level": 10,
        "hsn_code": "8536",
        "gst_rate": 18.0,
    }
    create_res = client.post("/api/products", json=prod_data, headers=ADMIN_HEADERS)
    assert create_res.status_code == 201
    created = create_res.json()
    product_id = created["data"]["id"]

    # 2. Staff attempts deletion -> Must return 403 Forbidden
    staff_del_res = client.delete(f"/api/products/{product_id}", headers=STAFF_HEADERS)
    assert staff_del_res.status_code == 403
    assert "Access denied" in staff_del_res.json()["detail"]

    # 3. Admin deletes product -> 200 OK
    admin_del_res = client.delete(f"/api/products/{product_id}", headers=ADMIN_HEADERS)
    assert admin_del_res.status_code == 200
    assert admin_del_res.json()["success"] is True

    # 4. Verify product no longer returned in active list
    list_res = client.get("/api/products", headers=ADMIN_HEADERS)
    active_ids = [p["id"] for p in list_res.json()["data"]]
    assert product_id not in active_ids

    # 5. Verify soft delete in DB
    db_prod = db.get_product_by_id(product_id)
    assert db_prod is not None
    assert db_prod["is_active"] == 0


def test_supplier_deletion_admin_and_staff_roles():
    """Verify Admin can delete suppliers and Staff is forbidden (403)."""
    # 1. Create a supplier as Admin
    sup_data = {
        "name": "Deletable Test Supplier Pvt Ltd",
        "contact_person": "Venkatesh Rao",
        "email": "venkatesh@deltest.in",
        "phone": "+91 98765 43210",
        "address": "Peenya Industrial Area, Bengaluru, Karnataka",
        "state": "Karnataka",
        "gstin": "29AABCU9603R1Z2",
        "pin_code": "560058",
    }
    create_res = client.post("/api/suppliers", json=sup_data, headers=ADMIN_HEADERS)
    assert create_res.status_code == 201
    created = create_res.json()
    supplier_id = created["data"]["id"]

    # 2. Staff attempts deletion -> 403 Forbidden
    staff_del_res = client.delete(f"/api/suppliers/{supplier_id}", headers=STAFF_HEADERS)
    assert staff_del_res.status_code == 403
    assert "Access denied" in staff_del_res.json()["detail"]

    # 3. Admin deletes supplier -> 200 OK
    admin_del_res = client.delete(f"/api/suppliers/{supplier_id}", headers=ADMIN_HEADERS)
    assert admin_del_res.status_code == 200
    assert admin_del_res.json()["success"] is True

    # 4. Verify supplier no longer returned in active list
    list_res = client.get("/api/suppliers", headers=ADMIN_HEADERS)
    active_ids = [s["id"] for s in list_res.json()["data"]]
    assert supplier_id not in active_ids

    # 5. Verify soft delete in DB
    db_sup = db.get_supplier_by_id(supplier_id)
    assert db_sup is not None
    assert db_sup["is_active"] == 0


def test_demand_prediction_with_all_algorithms():
    """Verify demand forecasting calculates properly for all three algorithms."""
    # Get seeded products
    prods_res = client.get("/api/products", headers=ADMIN_HEADERS)
    assert prods_res.status_code == 200
    prods = prods_res.json()["data"]
    assert len(prods) > 0
    prod = prods[0]

    for algo in ["SMA", "WMA", "SES"]:
        res = client.post("/api/predictions/calculate", json={
            "product_id": prod["id"],
            "horizon_days": 30,
            "lead_time_days": 7,
            "method": algo
        }, headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["method"].upper() in ["SMA", "WMA", "SES", "EXPONENTIAL_SMOOTHING", "SIMPLE_MOVING_AVERAGE", "WEIGHTED_MOVING_AVERAGE"]
        assert data["predicted_demand"] >= 0
        assert data["safety_stock"] >= 0
        assert data["recommended_restock"] >= 0
        assert data["urgency_status"] in ["CRITICAL_OUT_OF_STOCK", "URGENT_RESTOCK_REQUIRED", "REORDER_RECOMMENDED", "SUFFICIENT_STOCK"]
