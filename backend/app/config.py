import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Authentication Mode: "local" (zero-dependency dev tokens & local JWT) or "aws" (Amazon Cognito JWT)
AUTH_MODE = os.getenv("AUTH_MODE", "local").lower().strip()

# Storage Mode: "local" (SQLite relational mirror) or "aws" (Amazon DynamoDB & S3)
STORAGE_MODE = os.getenv("STORAGE_MODE", "local").lower().strip()

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# AWS Settings (used when AUTH_MODE=aws or STORAGE_MODE=aws)
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "InventoryManagementTable")
S3_REPORTS_BUCKET = os.getenv("S3_REPORTS_BUCKET", "inventory-reports-mtech-storage")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")

# Forecasting Defaults
FORECAST_METHOD = os.getenv("FORECAST_METHOD", "exponential_smoothing")
DEFAULT_LEAD_TIME_DAYS = int(os.getenv("DEFAULT_LEAD_TIME_DAYS", "7"))
DEFAULT_SAFETY_STOCK_FACTOR = float(os.getenv("DEFAULT_SAFETY_STOCK_FACTOR", "1.65"))
FORECAST_HORIZON_DAYS = int(os.getenv("FORECAST_HORIZON_DAYS", "30"))

# Local Data Paths (Lambda environments only allow writes to /tmp)
if os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT"):
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DB_PATH = DATA_DIR / "inventory_local.db"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
