from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
from backend.app.models import ProductCreate, ProductUpdate, ProductResponse
from backend.app.database import db
from backend.app.auth import get_current_user, require_role

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=Dict[str, Any])
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: Optional[str] = "name",
    order: Optional[str] = "asc",
    user: dict = Depends(get_current_user)
):
    """List and filter catalog products."""
    clean_search = search.strip() if search and search.strip() else None
    clean_category = category.strip() if category and category.strip() and category.strip().lower() != "all" else None
    products = db.get_products(search=clean_search, category=clean_category, sort_by=sort_by, order=order)
    return {
        "success": True,
        "count": len(products),
        "data": products
    }


@router.get("/{product_id}", response_model=Dict[str, Any])
def get_product(product_id: str, user: dict = Depends(get_current_user)):
    """Fetch single product details."""
    prod = db.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")
    return {"success": True, "data": prod}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
def create_product(
    payload: ProductCreate,
    user: dict = Depends(require_role(["Admin"]))
):
    """Add a new product to catalog. Restricted to Admin."""
    created = db.create_product(payload.model_dump())
    return {"success": True, "data": created, "message": "Product created successfully."}


@router.put("/{product_id}", response_model=Dict[str, Any])
def update_product(
    product_id: str,
    payload: ProductUpdate,
    user: dict = Depends(require_role(["Admin"]))
):
    """Update product details."""
    existing = db.get_product_by_id(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")
    
    updated = db.update_product(product_id, payload.model_dump(exclude_unset=True))
    return {"success": True, "data": updated, "message": "Product updated successfully."}


@router.delete("/{product_id}", response_model=Dict[str, Any])
def delete_product(
    product_id: str,
    user: dict = Depends(require_role(["Admin"]))
):
    """Soft delete / deactivate a product."""
    existing = db.get_product_by_id(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Product with ID '{product_id}' not found.")
    
    success = db.delete_product(product_id)
    return {"success": success, "message": f"Product '{product_id}' deactivated successfully."}
