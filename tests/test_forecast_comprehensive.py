"""
Comprehensive Forecasting Verification Suite:
Covers all supported algorithms (SMA, WMA, SES), edge cases, mathematical invariants,
and REST API validation scenarios as specified in the testing criteria.
"""

import pytest
import math
import sys
import os

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from ml.forecaster import DemandForecaster

client = TestClient(app)


# ==============================================================================
# 1. INDEPENDENT MATHEMATICAL CALCULATION TESTS FOR ALGORITHMS
# ==============================================================================

def test_sma_independently_calculated():
    """
    Independent manual calculation:
    Sales series = [10, 20, 30, 40, 50, 60, 70]
    Window = 7
    SMA = (10+20+30+40+50+60+70) / 7 = 280 / 7 = 40.0
    """
    sales = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    res = DemandForecaster.simple_moving_average(sales, window=7)
    assert res == 40.0


def test_wma_independently_calculated():
    """
    Independent manual calculation:
    Sales series = [10, 20, 30]
    Weights = [1, 2, 3] -> sum = 6
    Weighted sum = 10*1 + 20*2 + 30*3 = 10 + 40 + 90 = 140
    WMA = 140 / 6 = 23.333333333333332
    """
    sales = [10.0, 20.0, 30.0]
    res = DemandForecaster.weighted_moving_average(sales, window=3)
    assert pytest.approx(res, rel=1e-3) == 23.333


def test_ses_independently_calculated():
    """
    Independent manual calculation:
    Sales series = [10, 20, 30], alpha = 0.3
    F0 = 10.0
    F1 = 0.3 * 20 + 0.7 * 10 = 6.0 + 7.0 = 13.0
    F2 = 0.3 * 30 + 0.7 * 13.0 = 9.0 + 9.1 = 18.1
    """
    sales = [10.0, 20.0, 30.0]
    res = DemandForecaster.exponential_smoothing(sales, alpha=0.3)
    assert pytest.approx(res, rel=1e-3) == 18.1


# ==============================================================================
# 2. EDGE CASE TESTING: EMPTY, INSUFFICIENT, ZERO, AND FLUCTUATING HISTORY
# ==============================================================================

def test_forecast_empty_history():
    """Empty history should gracefully yield 0 demand rate and 0 recommended restock without division by zero."""
    for method in ["moving_average", "weighted_moving_average", "exponential_smoothing", "sma", "wma", "ses"]:
        rec = DemandForecaster.generate_recommendation(
            sales_records=[],
            current_stock=20,
            method=method,
            forecast_horizon_days=30,
            lead_time_days=7
        )
        assert rec["daily_demand_rate"] == 0.0
        assert rec["predicted_demand"] == 0
        assert rec["recommended_restock"] == 0
        assert rec["urgency_status"] == "SUFFICIENT_STOCK"


def test_forecast_insufficient_history():
    """History of only 1 or 2 records should execute safely without crashing."""
    records_single = [{"sale_date": "2026-10-01T10:00:00Z", "quantity": 14}]
    rec_single = DemandForecaster.generate_recommendation(
        sales_records=records_single,
        current_stock=10,
        method="exponential_smoothing",
        forecast_horizon_days=10,
        lead_time_days=5
    )
    assert rec_single["daily_demand_rate"] == 14.0
    assert rec_single["predicted_demand"] == 140
    assert rec_single["recommended_restock"] > 0


def test_forecast_zero_sales():
    """Sales records with quantity = 0 should return zero velocity and zero projected demand."""
    records_zero = [
        {"sale_date": f"2026-09-{i:02d}T10:00:00Z", "quantity": 0}
        for i in range(1, 10)
    ]
    rec_zero = DemandForecaster.generate_recommendation(
        sales_records=records_zero,
        current_stock=15,
        method="moving_average",
        forecast_horizon_days=30,
        lead_time_days=7
    )
    assert rec_zero["daily_demand_rate"] == 0.0
    assert rec_zero["predicted_demand"] == 0
    assert rec_zero["recommended_restock"] == 0
    assert rec_zero["urgency_status"] == "SUFFICIENT_STOCK"


def test_forecast_fluctuating_demand():
    """Highly variable sales demand should produce a positive standard deviation and increased safety stock buffer."""
    records_volatile = [
        {"sale_date": f"2026-09-{i:02d}T10:00:00Z", "quantity": 50 if i % 2 == 0 else 2}
        for i in range(1, 15)
    ]
    rec = DemandForecaster.generate_recommendation(
        sales_records=records_volatile,
        current_stock=20,
        method="exponential_smoothing",
        forecast_horizon_days=30,
        lead_time_days=7
    )
    assert rec["demand_std_dev"] > 0
    assert rec["safety_stock"] > 0
    assert rec["recommended_restock"] > 0


# ==============================================================================
# 3. STOCK LEVEL INVARIANTS: ZERO STOCK VS ADEQUATE STOCK
# ==============================================================================

def test_forecast_zero_current_stock():
    """Zero current stock must be flagged as CRITICAL_OUT_OF_STOCK."""
    records = [{"sale_date": "2026-09-10T10:00:00Z", "quantity": 5}]
    rec = DemandForecaster.generate_recommendation(
        sales_records=records,
        current_stock=0,
        method="moving_average",
        forecast_horizon_days=30,
        lead_time_days=7
    )
    assert rec["current_stock"] == 0
    assert rec["urgency_status"] == "CRITICAL_OUT_OF_STOCK"
    assert rec["recommended_restock"] == rec["predicted_demand"] + rec["safety_stock"]


def test_forecast_adequate_current_stock():
    """Stock far exceeding demand + safety buffer must yield recommended_restock = 0 and SUFFICIENT_STOCK."""
    records = [{"sale_date": "2026-09-10T10:00:00Z", "quantity": 2}]
    rec = DemandForecaster.generate_recommendation(
        sales_records=records,
        current_stock=5000,
        method="exponential_smoothing",
        forecast_horizon_days=30,
        lead_time_days=7
    )
    assert rec["recommended_restock"] == 0
    assert rec["urgency_status"] == "SUFFICIENT_STOCK"


# ==============================================================================
# 4. REST API VALIDATION TESTS: HTTP 404, HTTP 422, AND SUPPORTED METHODS
# ==============================================================================

def test_api_prediction_missing_product_404():
    """Requesting forecast for non-existent product ID must return HTTP 404."""
    resp = client.post("/api/predictions/calculate", json={
        "product_id": "PRD-NONEXISTENT-9999",
        "method": "exponential_smoothing",
        "forecast_days": 30,
        "lead_time_days": 7
    }, headers={"Authorization": "Bearer dev-admin-token"})
    assert resp.status_code == 404
    data = resp.json()
    assert "not found" in data["detail"].lower()


def test_api_prediction_invalid_negative_horizon_422():
    """Forecast days <= 0 must fail Pydantic validation with HTTP 422."""
    resp = client.post("/api/predictions/calculate", json={
        "product_id": "PRD-1011",
        "method": "exponential_smoothing",
        "forecast_days": -10,
        "lead_time_days": 7
    }, headers={"Authorization": "Bearer dev-admin-token"})
    assert resp.status_code == 422


def test_api_prediction_invalid_lead_time_422():
    """Lead time days <= 0 must fail Pydantic validation with HTTP 422."""
    resp = client.post("/api/predictions/calculate", json={
        "product_id": "PRD-1011",
        "method": "exponential_smoothing",
        "forecast_days": 30,
        "lead_time_days": 0
    }, headers={"Authorization": "Bearer dev-admin-token"})
    assert resp.status_code == 422


def test_api_prediction_empty_product_id_422():
    """Empty product ID string must fail Pydantic validation with HTTP 422."""
    resp = client.post("/api/predictions/calculate", json={
        "product_id": "",
        "method": "exponential_smoothing",
        "forecast_days": 30,
        "lead_time_days": 7
    }, headers={"Authorization": "Bearer dev-admin-token"})
    assert resp.status_code == 422


def test_api_prediction_all_supported_algorithms():
    """Verify all algorithm names and common shorthand aliases execute via REST API."""
    algorithms = [
        "exponential_smoothing",
        "weighted_moving_average",
        "moving_average",
        "ses",
        "wma",
        "sma"
    ]
    for algo in algorithms:
        resp = client.post("/api/predictions/calculate", json={
            "product_id": "PRD-1011",
            "method": algo,
            "forecast_days": 30,
            "lead_time_days": 7,
            "safety_stock_factor": 1.65
        }, headers={"Authorization": "Bearer dev-admin-token"})
        assert resp.status_code == 200, f"Algorithm {algo} failed with status {resp.status_code}"
        data = resp.json()
        assert data["success"] is True
        assert "predicted_demand" in data
        assert "safety_stock" in data
        assert "recommended_restock" in data
        assert "urgency_status" in data
        assert data["recommended_restock"] >= 0
