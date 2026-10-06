from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==============================================================================
# Auth & User Models
# ==============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str  # "Admin" or "Staff"
    name: str

class LoginResponse(BaseModel):
    success: bool
    token: str
    user: UserResponse


# ==============================================================================
# Product Models (India / GST & HSN Support)
# ==============================================================================

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    category: str = Field(..., min_length=2, max_length=100)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)
    min_stock_level: int = Field(..., ge=0)
    supplier_id: Optional[str] = None
    hsn_code: Optional[str] = "8536"
    gst_rate: Optional[float] = 18.0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    min_stock_level: Optional[int] = Field(None, ge=0)
    supplier_id: Optional[str] = None
    is_active: Optional[bool] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    category: str
    price: float
    quantity: int
    min_stock_level: int
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    status: str  # "IN STOCK", "LOW STOCK", "OUT OF STOCK"
    is_active: bool
    hsn_code: Optional[str] = "8536"
    gst_rate: Optional[float] = 18.0
    created_at: str
    updated_at: str


# ==============================================================================
# Supplier Models (India / GSTIN, State & PIN Code Support)
# ==============================================================================

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contact_person: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=5, max_length=30)
    email: str = Field(..., max_length=120)
    address: str = Field(..., min_length=3, max_length=250)
    supplied_categories: Optional[str] = "General"
    gstin: Optional[str] = None
    state: Optional[str] = "Tamil Nadu"
    pin_code: Optional[str] = "632007"

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    supplied_categories: Optional[str] = None
    is_active: Optional[bool] = None
    gstin: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None

class SupplierResponse(BaseModel):
    id: str
    name: str
    contact_person: str
    phone: str
    email: str
    address: str
    supplied_categories: str
    is_active: bool
    gstin: Optional[str] = None
    state: Optional[str] = "Tamil Nadu"
    pin_code: Optional[str] = "632007"
    created_at: str


# ==============================================================================
# Transaction Models (India / GST, CGST, SGST, IGST Breakdown Support)
# ==============================================================================

class PurchaseCreate(BaseModel):
    product_id: str
    supplier_id: str
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)
    purchase_date: Optional[str] = None
    gst_rate: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None

class PurchaseResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    supplier_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    total_cost: float
    purchase_date: str
    created_by: str
    gst_rate: Optional[float] = 18.0
    taxable_amount: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_tax: Optional[float] = None

class SaleCreate(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    sale_date: Optional[str] = None
    customer_name: Optional[str] = "Walk-in Customer"
    gst_rate: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None

class SaleResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total_revenue: float
    sale_date: str
    created_by: str
    customer_name: Optional[str] = "Walk-in Customer"
    gst_rate: Optional[float] = 18.0
    taxable_amount: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_tax: Optional[float] = None


# ==============================================================================
# Prediction Models
# ==============================================================================

class PredictionRequest(BaseModel):
    product_id: str = Field(..., min_length=1, description="Target Product SKU identifier")
    method: Optional[str] = Field("exponential_smoothing", description="Forecasting algorithm (SES, WMA, SMA)")
    forecast_days: Optional[int] = Field(None, ge=1, le=180, description="Forecast horizon in days")
    horizon_days: Optional[int] = Field(None, ge=1, le=180, description="Forecast horizon alias in days")
    lead_time_days: Optional[int] = Field(7, ge=1, le=90, description="Supplier lead time in days")
    safety_stock_factor: Optional[float] = Field(1.65, ge=0.0, le=5.0, description="Safety stock quantile multiplier")

    @property
    def effective_horizon_days(self) -> int:
        return self.forecast_days or self.horizon_days or 30

class PredictionResponse(BaseModel):
    product_id: str
    product_name: str
    method: str
    algorithm_name: str
    historical_days_analyzed: int
    total_historical_sales_units: int
    daily_demand_rate: float
    forecast_horizon_days: int
    lead_time_days: int
    predicted_demand: int
    current_stock: int
    demand_std_dev: float
    safety_stock: int
    recommended_restock: int
    urgency_status: str
    formula_explanation: str
