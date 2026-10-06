"""
Machine Learning & Time-Series Demand Forecasting Engine
Part of Cloud-Based Intelligent Inventory Management & Stock Prediction System

Algorithms implemented:
1. Simple Moving Average (SMA)
2. Weighted Moving Average (WMA)
3. Single Exponential Smoothing (SES)
4. Dynamic Safety Stock & Reorder Quantity Calculator
"""

import math
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta


class DemandForecaster:
    """
    Forecasting engine for product sales demand and replenishment recommendation.
    Designed for zero-dependency portability and seamless execution in AWS Lambda.
    """

    @staticmethod
    def simple_moving_average(daily_sales: List[float], window: int = 7) -> float:
        """
        Calculates Simple Moving Average (SMA) daily demand rate.
        SMA = sum(sales in last k days) / k
        """
        if not daily_sales:
            return 0.0
        
        effective_window = min(window, len(daily_sales))
        recent_sales = daily_sales[-effective_window:]
        return sum(recent_sales) / effective_window

    @staticmethod
    def weighted_moving_average(daily_sales: List[float], window: int = 7) -> float:
        """
        Calculates Weighted Moving Average (WMA) daily demand rate.
        Assigns linearly ascending weights to give higher priority to recent transactions.
        """
        if not daily_sales:
            return 0.0
        
        effective_window = min(window, len(daily_sales))
        recent_sales = daily_sales[-effective_window:]
        
        # Weights: 1, 2, ..., n
        weights = list(range(1, effective_window + 1))
        weight_sum = sum(weights)
        
        weighted_sum = sum(s * w for s, w in zip(recent_sales, weights))
        return weighted_sum / weight_sum

    @staticmethod
    def exponential_smoothing(daily_sales: List[float], alpha: float = 0.3) -> float:
        """
        Calculates Single Exponential Smoothing (SES) daily demand rate.
        F_t = alpha * A_{t-1} + (1 - alpha) * F_{t-1}
        alpha in range [0.1, 0.5]
        """
        if not daily_sales:
            return 0.0
        
        if len(daily_sales) == 1:
            return daily_sales[0]
        
        alpha = max(0.01, min(0.99, alpha))
        forecast = daily_sales[0]
        for actual in daily_sales[1:]:
            forecast = alpha * actual + (1.0 - alpha) * forecast
        return forecast

    @staticmethod
    def calculate_standard_deviation(values: List[float]) -> float:
        """Calculates sample standard deviation of daily demand."""
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        return math.sqrt(variance)

    @classmethod
    def generate_recommendation(
        cls,
        sales_records: List[Dict[str, Any]],
        current_stock: int,
        method: str = "exponential_smoothing",
        forecast_horizon_days: int = 30,
        lead_time_days: int = 7,
        safety_stock_factor: float = 1.65,
        alpha: float = 0.3,
        window: int = 14
    ) -> Dict[str, Any]:
        """
        Main pipeline: Ingests sales, prepares daily time-series, forecasts future demand,
        computes safety stock, and produces an actionable restocking recommendation.
        
        Recommendation Formula:
        Recommended Restock = max(0, ceil(Predicted Demand during horizon + Safety Stock - Current Stock))
        """
        # Step 1: Aggregate sales by date
        daily_map: Dict[str, float] = {}
        for record in sales_records:
            date_str = str(record.get("sale_date", ""))[:10]  # YYYY-MM-DD
            qty = float(record.get("quantity", 0))
            if date_str:
                daily_map[date_str] = daily_map.get(date_str, 0.0) + qty

        # If sparse or empty, build an ordered array
        sorted_dates = sorted(daily_map.keys())
        if not sorted_dates:
            daily_series = [0.0]
        else:
            # Fill missing days between min and max date with 0 for accurate time-series modeling
            start_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d")
            end_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d")
            delta_days = (end_date - start_date).days + 1
            daily_series = []
            for i in range(max(1, delta_days)):
                d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                daily_series.append(daily_map.get(d, 0.0))

        # Step 2: Forecast Daily Demand Rate
        method_str = (method or "exponential_smoothing").strip()
        method_lower = method_str.lower()
        if method_lower in ["moving_average", "sma", "simple_moving_average"]:
            daily_rate = cls.simple_moving_average(daily_series, window=window)
            algorithm_name = f"Simple Moving Average (Window={min(window, len(daily_series))} days)"
            method_normalized = method_str if method_str.upper() in ["SMA", "SIMPLE_MOVING_AVERAGE"] else "moving_average"
        elif method_lower in ["weighted_moving_average", "wma"]:
            daily_rate = cls.weighted_moving_average(daily_series, window=window)
            algorithm_name = f"Weighted Moving Average (Window={min(window, len(daily_series))} days)"
            method_normalized = method_str if method_str.upper() in ["WMA", "WEIGHTED_MOVING_AVERAGE"] else "weighted_moving_average"
        else:
            daily_rate = cls.exponential_smoothing(daily_series, alpha=alpha)
            algorithm_name = f"Single Exponential Smoothing (Alpha={alpha})"
            method_normalized = method_str if method_str.upper() in ["SES", "EXPONENTIAL_SMOOTHING"] else "exponential_smoothing"

        # Projected demand over the forecast horizon
        projected_demand = math.ceil(daily_rate * forecast_horizon_days)

        # Step 3: Compute Safety Stock based on demand variance and lead time
        # Safety Stock = Z * sqrt(Lead Time) * std_dev(daily demand)
        std_dev = cls.calculate_standard_deviation(daily_series)
        lead_time_factor = math.sqrt(max(1, lead_time_days))
        calculated_safety_stock = math.ceil(safety_stock_factor * lead_time_factor * std_dev)
        # Apply a sensible floor of at least 15% of projected demand or 5 units if product has sales
        safety_stock = max(calculated_safety_stock, math.ceil(0.15 * projected_demand) if projected_demand > 0 else 0)

        # Step 4: Compute Restocking Recommendation
        # Recommended Restock = max(0, Projected Demand + Safety Stock - Current Stock)
        net_required = (projected_demand + safety_stock) - current_stock
        recommended_restock = max(0, net_required)

        # Urgency classification
        if current_stock == 0:
            urgency = "CRITICAL_OUT_OF_STOCK"
        elif current_stock < safety_stock:
            urgency = "URGENT_RESTOCK_REQUIRED"
        elif recommended_restock > 0:
            urgency = "REORDER_RECOMMENDED"
        else:
            urgency = "SUFFICIENT_STOCK"

        return {
            "method": method_normalized,
            "algorithm_name": algorithm_name,
            "historical_days_analyzed": len(daily_series),
            "total_historical_sales_units": int(sum(daily_series)),
            "daily_demand_rate": round(daily_rate, 2),
            "forecast_horizon_days": forecast_horizon_days,
            "lead_time_days": lead_time_days,
            "predicted_demand": projected_demand,
            "current_stock": current_stock,
            "demand_std_dev": round(std_dev, 2),
            "safety_stock": safety_stock,
            "recommended_restock": recommended_restock,
            "urgency_status": urgency,
            "formula_explanation": (
                f"Recommended Restock ({recommended_restock}) = "
                f"Predicted Demand ({projected_demand}) + Safety Stock ({safety_stock}) - Current Stock ({current_stock})"
            )
        }
