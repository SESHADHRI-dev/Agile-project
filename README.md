# IntelliStock India — Cloud-Based Intelligent Inventory Management & Stock Prediction System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Bundler-Vite_8-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.14+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Tests](https://img.shields.io/badge/Pytest-86_Passed-brightgreen.svg?logo=pytest&logoColor=white)](https://pytest.org)
[![AWS Ready](https://img.shields.io/badge/AWS-Serverless_SAM-FF9900.svg?logo=amazonaws&logoColor=white)](https://aws.amazon.com)
[![Localization](https://img.shields.io/badge/Locale-India_(₹_INR_|_GST)-orange.svg)](https://en.wikipedia.org/wiki/Goods_and_Services_Tax_(India))

**IntelliStock India** is an enterprise-grade, cloud-native inventory management and intelligent replenishment system tailored for Indian manufacturing and distribution enterprises (headquartered in Katpadi, Vellore, Tamil Nadu).

It combines transactional record-keeping with proactive machine learning decision support, statutory GST calculations, over-sale guardrails, multi-format audit reporting (Excel, PDF, CSV), and dual-mode runtime deployment (zero-cost local development or production AWS Serverless).

---

## 1. Features & Capabilities

- **Catalog & Vendor Management:** Centralized product records with HSN codes, Indian GST tax slabs (5%, 12%, 18%, 28%), supplier profiles with validated state GSTINs, soft-deletion safety, and active status tracking.
- **Strict Transactional Integrity & Invariants:** Real-time stock recomputation enforcing fundamental warehouse domain math:
  $$\text{Current Stock} = \text{Previous Stock} + \text{Inbound Purchases} - \text{Outbound Sales}$$
- **Zero-Negative Stock Guardrails:** Strict server-side and UI-level prevention of over-selling beyond verified physical warehouse stock.
- **Automated Stockout & Reorder Alerts:** Instant warning when $\text{Current Stock} \le \text{Minimum Stock Level}$, and critical escalation when stock reaches 0 units.
- **Machine Learning Demand Forecasting:** Real-time time-series demand velocity prediction utilizing:
  - **Single Exponential Smoothing (SES)** ($\alpha = 0.3$)
  - **Weighted Moving Average (WMA)** with recency bias
  - **Simple Moving Average (SMA)** (14-day rolling window)
- **Scientific Restocking Optimization:**
  $$\text{Safety Stock} = Z \times \sigma_d \times \sqrt{L} \quad (Z = 1.65 \text{ for 95\% service level})$$
  $$\text{Recommended Restock} = \max\left(0, \lceil \text{Predicted Demand} + \text{Safety Stock} - \text{Current Stock} \rceil\right)$$
- **Indian Enterprise Localization:**
  - Native Indian Rupee (`₹` INR) currency display with Indian numbering formatting (Lakhs and Crores: `₹1,50,000`).
  - Automatic tax partitioning between intra-state transactions (CGST 9% + SGST 9%) and inter-state supplies (IGST 18%).
  - Asia/Kolkata (IST) timestamps and date formatting.
- **Multi-Format Export Engine:** Downloadable high-fidelity Excel workbooks (`.xlsx` via `openpyxl`), presentation-ready PDFs (`.pdf` via `reportlab`), and UTF-8 CSV reports for Inventory, Low Stock, Sales, Purchases, and Demand Forecasts.
- **Role-Based Access Control (RBAC):**
  - **Administrator:** Full catalog creation, editing, deletion, replenishment reorders, and settings configuration.
  - **Operations Staff (Seshadhri):** Day-to-day transaction recording (sales and purchases) with restricted administrative rights.
- **Dual-Mode Architecture:** Zero-dependency local developer mode (SQLite mirror with DynamoDB compatibility) and AWS Cloud production mode (DynamoDB, S3, Cognito, API Gateway, Lambda).

---

## 2. Technology Stack

| Layer | Technologies & Tools |
| :--- | :--- |
| **Frontend UI** | React 18, Vite 8, Modern CSS Design Tokens, Lucide React Iconography |
| **Backend API** | Python 3.14+, FastAPI 0.115+, Uvicorn, Pydantic v2, Mangum ASGI |
| **ML Engine** | Pure-Python numerical statistics (SES, WMA, SMA, Lead-Time Safety Buffers) |
| **Reporting** | OpenPyXL (Excel `.xlsx`), ReportLab (Vector PDF), Python CSV |
| **Databases** | Dual-Mode: Amazon DynamoDB (Single-table design) / SQLite (Local relational mirror) |
| **Cloud Services** | AWS SAM, Amazon API Gateway, AWS Lambda, Amazon Cognito, Amazon S3 |
| **Testing** | Pytest 9.1.1 (86 test cases), Puppeteer-Core E2E Browser Testing |

---

## 3. Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        React 18 Dashboard (Vite)                       │
│        (Indianized UI, Dark/Light Mode, Dual RBAC Profiles, IST)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI REST API Gateway                        │
│                (Auth Layer, Domain Engine, Pydantic v2)                │
└───────────────┬───────────────────┬───────────────────┬────────────────┘
                │                   │                   │
                v                   v                   v
┌────────────────────────┐ ┌────────────────┐ ┌──────────────────────────┐
│  Demand Forecaster     │ │ Export Engine  │ │ Storage Abstraction      │
│  - SES (α=0.3)         │ │ - OpenPyXL     │ │ - AWS DynamoDB (Cloud)   │
│  - Weighted MA         │ │ - ReportLab    │ │ - SQLite Mirror (Local)  │
│  - Simple MA           │ │ - UTF-8 CSV    │ │ - Amazon S3 (Archival)   │
└────────────────────────┘ └────────────────┘ └──────────────────────────┘
```

---

## 4. Repository Structure

```text
.
├── backend/                       # FastAPI REST API Backend
│   ├── app/
│   │   ├── auth.py                # Dual-mode authentication (Cognito & Local JWT)
│   │   ├── config.py              # Environment configuration & defaults
│   │   ├── database.py            # Dual-mode DB abstraction (SQLite / DynamoDB)
│   │   ├── domain.py              # Inventory domain invariants & validation rules
│   │   ├── main.py                # FastAPI application entrypoint & middleware
│   │   ├── models.py              # Pydantic v2 schemas & request/response models
│   │   └── routers/               # API route controllers
│   │       ├── auth.py            # Login, token validation, user profile
│   │       ├── products.py        # Product catalog CRUD & soft delete
│   │       ├── suppliers.py       # Vendor management & GSTIN tracking
│   │       ├── purchases.py       # Inbound stock transactions
│   │       ├── sales.py           # Outbound sales & over-sale rejection
│   │       ├── inventory.py       # Stock ledger & discrepancy detection
│   │       ├── predictions.py     # Demand forecast generation & restock orders
│   │       ├── reports.py         # Multi-format exports (CSV, PDF, Excel)
│   │       └── seed.py            # Initial Indian seed dataset
├── ml/                            # Machine Learning Demand Forecasting Engine
│   └── forecaster.py              # SES, WMA, SMA & Safety Stock formulas
├── frontend/                      # Modern React 18 Single-Page Application
│   ├── src/
│   │   ├── App.jsx                # Layout coordinator & view router
│   │   ├── api.js                 # Axios/Fetch API client with JWT handling
│   │   ├── index.css              # Glassmorphic CSS design system
│   │   └── components/
│   │       ├── Navbar.jsx         # Header bar, sync indicator, theme switch
│   │       ├── Sidebar.jsx        # Navigation links & active user profile
│   │       ├── LoginModal.jsx     # Fast authentication & demo role switcher
│   │       └── views/             # Views: Dashboard, Products, Sales, etc.
│   ├── run_browser_e2e.js         # End-to-end browser automation suite
│   ├── package.json               # Node dependencies & build scripts
│   └── vite.config.js             # Vite configuration
├── lambda/                        # AWS Lambda Deployment Handler
│   └── lambda_handler.py          # Mangum ASGI adapter for API Gateway
├── infrastructure/                # AWS SAM Infrastructure as Code
│   └── template.yaml              # CloudFormation Serverless template
├── tests/                         # Comprehensive Automated Test Suite
│   ├── test_api_endpoints.py      # Core REST API endpoint tests
│   ├── test_audit_fixes.py        # System audit & fix verification
│   ├── test_forecast_comprehensive.py # Mathematical ML forecasting tests
│   ├── test_full_system_verification.py # Full lifecycle integration tests
│   ├── test_inventory_math.py     # Inventory invariant & over-sale tests
│   ├── test_low_stock_alerts_sync.py # Alert thresholds & sync tests
│   ├── test_prediction.py         # Restock order pipeline tests
│   └── test_ui_forecasting_acceptance.js # Puppeteer UI acceptance test
├── .env.example                   # Environment configuration template
├── .gitignore                     # Production Git exclusion rules
├── requirements.txt               # Python package dependencies
├── API_DOCUMENTATION.md           # Exhaustive REST API specification
├── ARCHITECTURE.md                # System design & cloud data flow
├── DATABASE_DESIGN.md             # DynamoDB single-table schema documentation
├── DEPLOYMENT.md                  # AWS production deployment guide
├── COST_AND_FREE_TIER.md          # AWS Free Tier cost control guide
└── FINAL_TESTING_AND_VERIFICATION_REPORT.md # Audit verification report
```

---

## 5. Getting Started & Installation

### Prerequisites
- **Python:** 3.11+ (Python 3.14 supported)
- **Node.js:** v18+ (Node v22+ recommended)
- **Git**

### Step 1: Clone the Repository
```bash
git clone https://github.com/SESHADHRI-dev/Agile-project.git
cd Agile-project
```

### Step 2: Environment Setup
Copy the provided environment template to `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

By default, the application runs in zero-cost local mode (`STORAGE_MODE=local`, `AUTH_MODE=local`) without requiring any AWS account or cloud credentials.

### Step 3: Install Backend Dependencies
Set up a Python virtual environment and install the required packages:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 4: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

## 6. Running Locally

### Start Backend API Server
In your project root (with virtual environment activated):
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Endpoint: `http://127.0.0.1:8000`
- Interactive Swagger Documentation: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

### Start React Frontend
In a new terminal:
```bash
cd frontend
npm run dev
```
- Frontend Dashboard: `http://localhost:5173`

### Production Frontend Build
To verify or compile the production web application assets:
```bash
cd frontend
npm run build
```

---

## 7. Default Demo Accounts & Login

The application includes pre-configured local development identities for friction-free evaluation:

| Identity | Email / Username | Password | Role | Privileges |
| :--- | :--- | :--- | :--- | :--- |
| **Dr. S. Sharma** | `admin@intellistock.in` | `Password123!` | `Admin` | Full Administrative & Catalog Control |
| **Seshadhri** | `staff@intellistock.in` | `Password123!` | `Staff` | Day-to-day Sales & Purchase Transactions |

*Note: One-click fast login buttons for both Administrator and Operations Staff are integrated directly into the login modal.*

---

## 8. Automated Testing

### Backend Unit & Integration Tests (86 Tests)
Run the complete backend test suite using Pytest:
```bash
python -m pytest tests/ -v
```

All 86 test cases validate:
- System health and API authentication
- Product catalog CRUD and soft deletion
- Inventory calculation invariants ($S_t = S_{t-1} + P_t - S_t$)
- Negative stock rejection & over-sale guards
- Low-stock and out-of-stock alert threshold accuracy
- Time-series demand forecasting (SES, WMA, SMA) and restock recommendation math
- Multi-format report export generation (CSV, PDF, Excel)
- Full lifecycle business workflows

### Frontend Browser End-to-End Tests
Ensure both backend (`port 8000`) and frontend (`port 5173`) servers are running, then execute:
```bash
node frontend/run_browser_e2e.js
```

---

## 9. AWS Cloud Deployment (Production)

To deploy to Amazon Web Services using AWS SAM:

```bash
# Build the SAM application
sam build --template infrastructure/template.yaml

# Guided deployment to AWS ap-south-1 (Mumbai)
sam deploy --guided
```

This provisions:
- **Amazon DynamoDB:** Pay-Per-Request single-table inventory database.
- **Amazon Cognito:** User pool and client for secure cloud authentication.
- **AWS Lambda & API Gateway:** Serverless Python backend with Mangum ASGI adapter.
- **Amazon S3:** Private bucket for cloud report archival.

Refer to [DEPLOYMENT.md](file:///d:/1-fall%2026-27/software%20configuration%20management/scm%20test%20tasks/DEPLOYMENT.md) and [COST_AND_FREE_TIER.md](file:///d:/1-fall%2026-27/software%20configuration%20management/scm%20test%20tasks/COST_AND_FREE_TIER.md) for full deployment instructions.

---

## 10. License

This project was developed for the Integrated M.Tech in Software Engineering curriculum as an enterprise software configuration management and cloud-native computing capstone.
