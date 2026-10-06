from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from backend.app.models import PredictionRequest, PredictionResponse
from backend.app.database import db
from backend.app.auth import get_current_user
from ml.forecaster import DemandForecaster

router = APIRouter(prefix="/predictions", tags=["Demand Forecasting & ML"])


@router.post("/calculate", response_model=Dict[str, Any])
def calculate_product_prediction(
    payload: PredictionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Executes the intelligent demand forecasting and replenishment pipeline for a product:
    1. Historical sales retrieval
    2. Daily time-series generation
    3. Selected demand forecasting algorithm (SMA / WMA / SES)
    4. Safety stock calculation based on lead time and demand variability
    5. Actionable restocking recommendation
    """
    prod = db.get_product_by_id(payload.product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with ID '{payload.product_id}' not found.")

    sales = db.get_sales(limit=500, product_id=payload.product_id)

    forecast_res = DemandForecaster.generate_recommendation(
        sales_records=sales,
        current_stock=prod["quantity"],
        method=payload.method or "exponential_smoothing",
        forecast_horizon_days=payload.effective_horizon_days,
        lead_time_days=payload.lead_time_days or 7,
        safety_stock_factor=payload.safety_stock_factor or 1.65
    )

    return {
        "success": True,
        "product_id": prod["id"],
        "product_name": prod["name"],
        "category": prod["category"],
        "price": prod["price"],
        **forecast_res
    }


@router.get("/recommendations", response_model=Dict[str, Any])
def get_all_recommendations(
    method: str = "exponential_smoothing",
    user: dict = Depends(get_current_user)
):
    """
    Calculates batch restocking recommendations across all catalog products.
    Sorted by urgency: CRITICAL first, then URGENT, then REORDER, then SUFFICIENT.
    """
    products = db.get_products()
    results = []

    urgency_rank = {
        "CRITICAL_OUT_OF_STOCK": 0,
        "URGENT_RESTOCK_REQUIRED": 1,
        "REORDER_RECOMMENDED": 2,
        "SUFFICIENT_STOCK": 3
    }

    for prod in products:
        sales = db.get_sales(limit=200, product_id=prod["id"])
        rec = DemandForecaster.generate_recommendation(
            sales_records=sales,
            current_stock=prod["quantity"],
            method=method,
            forecast_horizon_days=30,
            lead_time_days=7
        )
        results.append({
            "product_id": prod["id"],
            "product_name": prod["name"],
            "category": prod["category"],
            "unit_price": prod["price"],
            **rec
        })

    # Sort by urgency
    results.sort(key=lambda x: (urgency_rank.get(x["urgency_status"], 99), -x["recommended_restock"]))

    return {
        "success": True,
        "count": len(results),
        "total_units_recommended": sum(r["recommended_restock"] for r in results),
        "data": results
    }
