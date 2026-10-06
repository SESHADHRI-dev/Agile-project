"""
Inventory Core Domain Logic and Invariants
Enforces strict stock formulas, validation checks, and status calculations.
"""

from typing import Tuple, Dict, Any


class InventoryLogic:
    """Core domain rules for inventory management."""

    @staticmethod
    def calculate_purchase_stock(previous_stock: int, purchase_quantity: int) -> int:
        """
        Formula: Current Stock = Previous Stock + Purchases
        Mandatory test case: 100 stock + 50 purchase = 150
        """
        if purchase_quantity <= 0:
            raise ValueError("Purchase quantity must be greater than zero.")
        if previous_stock < 0:
            raise ValueError("Previous stock cannot be negative.")
        return previous_stock + purchase_quantity

    @staticmethod
    def calculate_sale_stock(current_stock: int, sale_quantity: int) -> int:
        """
        Formula: Current Stock = Previous Stock - Sales
        Mandatory test case: 150 stock - 30 sale = 120
        Guardrail: Cannot sell more than available stock (10 stock, 15 sale -> REJECT)
        """
        if sale_quantity <= 0:
            raise ValueError("Sale quantity must be greater than zero.")
        if sale_quantity > current_stock:
            raise ValueError(
                f"Insufficient stock! Requested sale quantity ({sale_quantity}) exceeds available stock ({current_stock})."
            )
        return current_stock - sale_quantity

    @staticmethod
    def evaluate_stock_status(current_stock: int, min_stock_level: int) -> str:
        """
        Evaluates product stock status.
        - OUT OF STOCK: current_stock <= 0
        - LOW STOCK: current_stock <= min_stock_level
        - IN STOCK: current_stock > min_stock_level
        """
        if current_stock <= 0:
            return "OUT OF STOCK"
        elif current_stock <= min_stock_level:
            return "LOW STOCK"
        else:
            return "IN STOCK"

    @staticmethod
    def calculate_inventory_valuation(quantity: int, unit_price: float) -> float:
        """Calculates monetary valuation of held inventory."""
        if quantity < 0 or unit_price < 0:
            raise ValueError("Quantity and unit price must be non-negative.")
        return round(float(quantity) * float(unit_price), 2)
