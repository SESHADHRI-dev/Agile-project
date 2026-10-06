import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import db

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-admin-token"}


@pytest.fixture(autouse=True)
def reset_db():
    """Reseed demo database before each test for clean deterministic state."""
    db.seed_database()


def test_case_a_oos_purchase_exceeding_threshold_alert_disappears():
    """
    Case A: Product is out of stock (stock=0); purchase enough units to exceed the reorder threshold.
    Its alert must disappear.
    Target: PRD-1003 (Copper Wire), opening stock: 0, min_stock_level (threshold): 10.
    Initial state: 1 CRITICAL stockout alert.
    Purchase: 25 units.
    Result: stock becomes 25 > 10. Alert must be removed.
    """
    # 1. Before check
    prod_before = db.get_product_by_id("PRD-1003")
    assert prod_before["quantity"] == 0
    assert prod_before["min_stock_level"] == 10
    assert prod_before["status"] == "OUT OF STOCK"

    alerts_before = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    oos_alert = next((a for a in alerts_before if a["product_id"] == "PRD-1003"), None)
    assert oos_alert is not None
    assert oos_alert["severity"] == "CRITICAL"

    # 2. Record purchase of 25 units
    purchase_payload = {
        "product_id": "PRD-1003",
        "supplier_id": "SUP-004",
        "quantity": 25,
        "unit_cost": 1600.00
    }
    pur_res = client.post("/api/purchases", json=purchase_payload, headers=AUTH_HEADERS)
    assert pur_res.status_code == 201

    # 3. After check
    prod_after = db.get_product_by_id("PRD-1003")
    assert prod_after["quantity"] == 25
    assert prod_after["status"] == "IN STOCK"

    alerts_after = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    assert not any(a["product_id"] == "PRD-1003" for a in alerts_after)


def test_case_b_oos_purchase_below_threshold_alert_transitions_to_warning():
    """
    Case B: Product is out of stock (stock=0); purchase some units, but the final balance remains below the threshold.
    The alert must remain as a low-stock warning.
    Target: PRD-1010 (High-Tensile Industrial Fastener Nut Kit M12), opening stock: 0, min_stock_level: 15.
    Initial state: CRITICAL stockout alert.
    Purchase: 8 units (8 <= 15).
    Result: stock becomes 8. Alert must remain, but severity transitions to WARNING.
    """
    # 1. Before check
    prod_before = db.get_product_by_id("PRD-1010")
    assert prod_before["quantity"] == 0
    assert prod_before["min_stock_level"] == 15
    assert prod_before["status"] == "OUT OF STOCK"

    alerts_before = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    oos_alert = next((a for a in alerts_before if a["product_id"] == "PRD-1010"), None)
    assert oos_alert is not None
    assert oos_alert["severity"] == "CRITICAL"

    # 2. Record purchase of 8 units
    purchase_payload = {
        "product_id": "PRD-1010",
        "supplier_id": "SUP-002",
        "quantity": 8,
        "unit_cost": 350.00
    }
    pur_res = client.post("/api/purchases", json=purchase_payload, headers=AUTH_HEADERS)
    assert pur_res.status_code == 201

    # 3. After check
    prod_after = db.get_product_by_id("PRD-1010")
    assert prod_after["quantity"] == 8
    assert prod_after["status"] == "LOW STOCK"

    alerts_after = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    updated_alert = next((a for a in alerts_after if a["product_id"] == "PRD-1010"), None)
    assert updated_alert is not None
    assert updated_alert["severity"] == "WARNING"
    assert updated_alert["current_stock"] == 8
    assert "Deficit: 7 units" in updated_alert["message"]


def test_case_c_low_stock_purchase_exceeding_threshold_alert_disappears():
    """
    Case C: Product is below its threshold (low stock); purchase enough units to exceed it.
    Its alert must disappear.
    Target: PRD-1005 (Heavy Duty Corrugated Box), opening stock: 18, min_stock_level: 50.
    Initial state: WARNING alert.
    Purchase: 40 units (18 + 40 = 58 > 50).
    Result: stock becomes 58. Alert must be removed.
    """
    # 1. Before check
    prod_before = db.get_product_by_id("PRD-1005")
    assert prod_before["quantity"] == 18
    assert prod_before["min_stock_level"] == 50
    assert prod_before["status"] == "LOW STOCK"

    alerts_before = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    low_alert = next((a for a in alerts_before if a["product_id"] == "PRD-1005"), None)
    assert low_alert is not None
    assert low_alert["severity"] == "WARNING"

    # 2. Record purchase of 40 units
    purchase_payload = {
        "product_id": "PRD-1005",
        "supplier_id": "SUP-003",
        "quantity": 40,
        "unit_cost": 30.00
    }
    pur_res = client.post("/api/purchases", json=purchase_payload, headers=AUTH_HEADERS)
    assert pur_res.status_code == 201

    # 3. After check
    prod_after = db.get_product_by_id("PRD-1005")
    assert prod_after["quantity"] == 58
    assert prod_after["status"] == "IN STOCK"

    alerts_after = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    assert not any(a["product_id"] == "PRD-1005" for a in alerts_after)


def test_case_d_sale_taking_stock_below_threshold_creates_alert():
    """
    Case D: Record a sale that takes stock below the threshold. The appropriate alert must appear.
    Target: PRD-1004 (Modular Electrical Switch 16A), opening stock: 22, min_stock_level: 15.
    Initial state: IN STOCK (0 alerts).
    Sale: 10 units (22 - 10 = 12 <= 15).
    Result: stock becomes 12. WARNING alert must appear.
    """
    # 1. Before check
    prod_before = db.get_product_by_id("PRD-1004")
    assert prod_before["quantity"] == 22
    assert prod_before["min_stock_level"] == 15
    assert prod_before["status"] == "IN STOCK"

    alerts_before = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    assert not any(a["product_id"] == "PRD-1004" for a in alerts_before)

    # 2. Record sale of 10 units
    sale_payload = {
        "product_id": "PRD-1004",
        "customer_name": "Salem Hardware",
        "quantity": 10,
        "unit_price": 95.00
    }
    sale_res = client.post("/api/sales", json=sale_payload, headers=AUTH_HEADERS)
    assert sale_res.status_code == 201

    # 3. After check
    prod_after = db.get_product_by_id("PRD-1004")
    assert prod_after["quantity"] == 12
    assert prod_after["status"] == "LOW STOCK"

    alerts_after = client.get("/api/alerts", headers=AUTH_HEADERS).json()["data"]
    new_alert = next((a for a in alerts_after if a["product_id"] == "PRD-1004"), None)
    assert new_alert is not None
    assert new_alert["severity"] == "WARNING"
    assert new_alert["current_stock"] == 12
    assert "Deficit: 3 units" in new_alert["message"]


def test_case_e_no_duplicate_stock_increment_on_repeated_reads():
    """
    Case E: Transaction consistency and idempotency on queries.
    Repeated queries or sync reads must NEVER increment or change stock.
    """
    # Check initial stock
    p1 = db.get_product_by_id("PRD-1001")["quantity"]

    # Multiple inventory reads
    for _ in range(5):
        client.get("/api/inventory", headers=AUTH_HEADERS)
        client.get("/api/alerts", headers=AUTH_HEADERS)
        client.get("/api/products", headers=AUTH_HEADERS)

    # Stock must remain identical
    p2 = db.get_product_by_id("PRD-1001")["quantity"]
    assert p1 == p2


def test_case_f_dashboard_alert_counts_match_backend_alerts():
    """
    Case F: Verify dashboard alert counts (low_stock_count + out_of_stock_count)
    match the actual alerts returned by the backend /alerts endpoint.
    """
    inv_summary = client.get("/api/inventory", headers=AUTH_HEADERS).json()
    alerts_data = client.get("/api/alerts", headers=AUTH_HEADERS).json()

    # Invariants
    assert inv_summary["out_of_stock_count"] == alerts_data["critical_count"]
    assert inv_summary["low_stock_count"] == alerts_data["warning_count"]
    assert (inv_summary["out_of_stock_count"] + inv_summary["low_stock_count"]) == alerts_data["count"]
    assert len(alerts_data["data"]) == alerts_data["count"]
