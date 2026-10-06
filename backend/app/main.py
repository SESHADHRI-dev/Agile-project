from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from backend.app.config import STORAGE_MODE, PORT, HOST
from backend.app.routers import (
    auth,
    products,
    suppliers,
    purchases,
    sales,
    inventory,
    predictions,
    reports,
    seed
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory-api")

app = FastAPI(
    title="Cloud-Based Intelligent Inventory Management & Stock Prediction System",
    description="Integrated M.Tech Software Engineering Project REST API",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local React Vite dev server (5173), preview (4173), and Amplify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Report-Filename", "X-Report-Format"],
)

# No-Cache Middleware for dynamic API endpoints (prevents stale stock/alert caching)
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": str(exc), "path": str(request.url.path)}
    )

# Health & Status Endpoint
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Inventory Management & Stock Prediction API",
        "storage_mode": STORAGE_MODE,
        "academic_degree": "Integrated M.Tech Software Engineering",
        "version": "1.0.0"
    }

# Mount Routers under /api
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(seed.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=True)
