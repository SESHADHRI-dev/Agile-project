"""
AWS Lambda Handler for Inventory Management & Stock Prediction System
Adapts Amazon API Gateway (REST API / HTTP API) proxy events to FastAPI via Mangum.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path so modules can be imported inside Lambda runtime
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure Lambda writable data directory and initialize pre-seeded database
if "AWS_LAMBDA_FUNCTION_NAME" in os.environ or os.getenv("LAMBDA_TASK_ROOT"):
    import shutil
    tmp_data = Path("/tmp/data")
    tmp_data.mkdir(parents=True, exist_ok=True)
    tmp_reports = Path("/tmp/data/reports")
    tmp_reports.mkdir(parents=True, exist_ok=True)
    tmp_db = tmp_data / "inventory_local.db"
    bundled_db = ROOT_DIR / "backend" / "data" / "inventory_local.db"
    if not tmp_db.exists() and bundled_db.exists():
        try:
            shutil.copy2(bundled_db, tmp_db)
        except Exception:
            pass

from mangum import Mangum
from backend.app.main import app

# Standard Mangum ASGI Lambda handler
handler = Mangum(app, lifespan="off")


def lambda_handler(event, context):
    """
    Primary AWS Lambda entrypoint invoked by Amazon API Gateway.
    Compatible with API Gateway REST API (payload format 1.0) and HTTP API (payload format 2.0).
    """
    return handler(event, context)
