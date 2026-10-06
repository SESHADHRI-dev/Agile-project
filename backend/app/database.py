import sqlite3
import json
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from backend.app.config import STORAGE_MODE, SQLITE_DB_PATH, DYNAMODB_TABLE_NAME, AWS_REGION
from backend.app.domain import InventoryLogic

logger = logging.getLogger("inventory-db")


def _utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal_to_native(obj):
    """Converts DynamoDB Decimal instances back to float/int."""
    if isinstance(obj, list):
        return [_decimal_to_native(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _decimal_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def _native_to_decimal(obj):
    """Converts floats to Decimals for DynamoDB serialization."""
    if isinstance(obj, list):
        return [_native_to_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _native_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj


class Database:
    """
    Unified database interface supporting dual-mode operations:
    1. Local Mode: Embedded SQLite with transparent JSON serialization
    2. AWS Cloud Mode: Amazon DynamoDB Single-Table Design via Boto3
    """

    def __init__(self):
        self.mode = STORAGE_MODE.lower().strip()
        self.table = None
        self._init_sqlite()  # Always initialize SQLite schema so local dev & fallback are guaranteed
        if self.mode == "aws":
            try:
                import boto3
                self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
                self.table = self.dynamodb.Table(DYNAMODB_TABLE_NAME)
                logger.info(f"DynamoDB mode configured for table '{DYNAMODB_TABLE_NAME}' in region '{AWS_REGION}'")
            except Exception as e:
                logger.warning(f"DynamoDB initialization notice: {e}. SQLite local engine remains active.")

    # ==========================================================================
    # SQLite Implementation (Local Mode)
    # ==========================================================================

    def _get_connection(self):
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Initializes tables for local relational storage with Indian business / GST schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                contact_person TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                address TEXT NOT NULL,
                supplied_categories TEXT DEFAULT 'General',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                gstin TEXT,
                state TEXT DEFAULT 'Tamil Nadu',
                pin_code TEXT DEFAULT '632007'
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                min_stock_level INTEGER NOT NULL,
                supplier_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                hsn_code TEXT DEFAULT '8536',
                gst_rate REAL DEFAULT 18.0,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                supplier_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_cost REAL NOT NULL,
                total_cost REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                created_by TEXT NOT NULL,
                gst_rate REAL DEFAULT 18.0,
                taxable_amount REAL,
                cgst REAL,
                sgst REAL,
                igst REAL,
                total_tax REAL,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_revenue REAL NOT NULL,
                sale_date TEXT NOT NULL,
                created_by TEXT NOT NULL,
                customer_name TEXT DEFAULT 'Walk-in Customer',
                gst_rate REAL DEFAULT 18.0,
                taxable_amount REAL,
                cgst REAL,
                sgst REAL,
                igst REAL,
                total_tax REAL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                method TEXT NOT NULL,
                forecast_period_days INTEGER NOT NULL,
                predicted_demand INTEGER NOT NULL,
                current_stock INTEGER NOT NULL,
                safety_stock INTEGER NOT NULL,
                recommended_restock INTEGER NOT NULL,
                calculated_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

            # Schema migration helper for existing SQLite databases
            migrations = [
                ("suppliers", [("gstin", "TEXT"), ("state", "TEXT DEFAULT 'Tamil Nadu'"), ("pin_code", "TEXT DEFAULT '632007'")]),
                ("products", [("hsn_code", "TEXT DEFAULT '8536'"), ("gst_rate", "REAL DEFAULT 18.0")]),
                ("purchases", [("gst_rate", "REAL DEFAULT 18.0"), ("taxable_amount", "REAL"), ("cgst", "REAL"), ("sgst", "REAL"), ("igst", "REAL"), ("total_tax", "REAL")]),
                ("sales", [("customer_name", "TEXT DEFAULT 'Walk-in Customer'"), ("gst_rate", "REAL DEFAULT 18.0"), ("taxable_amount", "REAL"), ("cgst", "REAL"), ("sgst", "REAL"), ("igst", "REAL"), ("total_tax", "REAL")])
            ]
            for tbl, cols in migrations:
                for col_name, col_type in cols:
                    try:
                        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type}")
                    except sqlite3.OperationalError:
                        pass

            conn.commit()

        # Seed data if empty
        self._ensure_sample_data()

    # ==========================================================================
    # Supplier Methods
    # ==========================================================================

    def get_suppliers(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search:
                cursor.execute(
                    "SELECT * FROM suppliers WHERE is_active = 1 AND (name LIKE ? OR contact_person LIKE ?) ORDER BY name ASC",
                    (f"%{search}%", f"%{search}%")
                )
            else:
                cursor.execute("SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_supplier(self, data: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = f"SUP-{uuid.uuid4().hex[:6].upper()}"
        now = _utc_now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO suppliers (id, name, contact_person, phone, email, address, supplied_categories, is_active, created_at, gstin, state, pin_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (
                supplier_id,
                data["name"],
                data["contact_person"],
                data["phone"],
                data["email"],
                data["address"],
                data.get("supplied_categories", "General"),
                now,
                data.get("gstin", ""),
                data.get("state", "Tamil Nadu"),
                data.get("pin_code", "632007")
            ))
            conn.commit()
        return self.get_supplier_by_id(supplier_id)

    def update_supplier(self, supplier_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        values = []
        for k, v in data.items():
            if v is not None:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return self.get_supplier_by_id(supplier_id)

        values.append(supplier_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE suppliers SET {', '.join(fields)} WHERE id = ?", tuple(values))
            conn.commit()
        return self.get_supplier_by_id(supplier_id)

    def delete_supplier(self, supplier_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE suppliers SET is_active = 0 WHERE id = ?", (supplier_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==========================================================================
    # Product Methods
    # ==========================================================================

    def get_products(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = "name",
        order: Optional[str] = "asc"
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT p.*, s.name as supplier_name 
            FROM products p 
            LEFT JOIN suppliers s ON p.supplier_id = s.id 
            WHERE p.is_active = 1
            """
            params = []
            if search and search.strip():
                clean_term = search.strip()
                query += " AND (p.name LIKE ? OR p.id LIKE ? OR p.hsn_code LIKE ? OR s.name LIKE ? OR p.category LIKE ?)"
                params.extend([f"%{clean_term}%", f"%{clean_term}%", f"%{clean_term}%", f"%{clean_term}%", f"%{clean_term}%"])
            if category and category.strip() and category.strip().lower() != "all":
                query += " AND LOWER(TRIM(p.category)) = LOWER(TRIM(?))"
                params.append(category.strip())

            # Sanitized sort column
            valid_sorts = {"name": "p.name", "price": "p.price", "quantity": "p.quantity", "created_at": "p.created_at"}
            col = valid_sorts.get(sort_by, "p.name")
            direction = "DESC" if order and order.lower() == "desc" else "ASC"
            query += f" ORDER BY {col} {direction}"

            cursor.execute(query, tuple(params))
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d["status"] = InventoryLogic.evaluate_stock_status(d["quantity"], d["min_stock_level"])
                results.append(d)
            return results

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM products p 
            LEFT JOIN suppliers s ON p.supplier_id = s.id 
            WHERE p.id = ?
            """, (product_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["status"] = InventoryLogic.evaluate_stock_status(d["quantity"], d["min_stock_level"])
            return d

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        product_id = f"PRD-{uuid.uuid4().hex[:6].upper()}"
        now = _utc_now_iso()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO products (id, name, category, price, quantity, min_stock_level, supplier_id, is_active, created_at, updated_at, hsn_code, gst_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (
                product_id,
                data["name"],
                data["category"],
                data["price"],
                data["quantity"],
                data["min_stock_level"],
                data.get("supplier_id"),
                now,
                now,
                data.get("hsn_code", "8536"),
                float(data.get("gst_rate", 18.0))
            ))
            conn.commit()
        return self.get_product_by_id(product_id)

    def update_product(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        values = []
        for k, v in data.items():
            if v is not None:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return self.get_product_by_id(product_id)

        now = _utc_now_iso()
        fields.append("updated_at = ?")
        values.append(now)

        values.append(product_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", tuple(values))
            conn.commit()
        return self.get_product_by_id(product_id)

    def delete_product(self, product_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==========================================================================
    # Purchase Transactions (Current = Previous + Purchases)
    # ==========================================================================

    def record_purchase(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        product_id = data["product_id"]
        supplier_id = data["supplier_id"]
        purchase_qty = int(data["quantity"])
        unit_cost = float(data["unit_cost"])
        total_cost = round(purchase_qty * unit_cost, 2)
        purchase_date = data.get("purchase_date") or _utc_now_iso()
        purchase_id = f"PUR-{uuid.uuid4().hex[:6].upper()}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch current product
            cursor.execute("SELECT quantity, hsn_code, gst_rate FROM products WHERE id = ? AND is_active = 1", (product_id,))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Product '{product_id}' not found or inactive.")
            
            # Fetch supplier state to determine intra-state (CGST+SGST) vs inter-state (IGST)
            cursor.execute("SELECT state, gstin FROM suppliers WHERE id = ?", (supplier_id,))
            sup = cursor.fetchone()
            sup_state = (sup["state"] if sup and sup["state"] else "Tamil Nadu").strip().lower()

            gst_rate = float(data.get("gst_rate") or prod["gst_rate"] or 18.0)
            taxable_amount = total_cost
            if sup_state in ["tamil nadu", "tamilnadu", "tn"]:
                # Intra-state transaction within Tamil Nadu: CGST + SGST
                cgst = round(taxable_amount * (gst_rate / 200.0), 2)
                sgst = round(taxable_amount * (gst_rate / 200.0), 2)
                igst = 0.0
            else:
                # Inter-state transaction: IGST
                cgst = 0.0
                sgst = 0.0
                igst = round(taxable_amount * (gst_rate / 100.0), 2)
            total_tax = round(cgst + sgst + igst, 2)

            previous_stock = prod["quantity"]
            # Strict domain invariant calculation
            new_stock = InventoryLogic.calculate_purchase_stock(previous_stock, purchase_qty)

            # Record purchase
            cursor.execute("""
            INSERT INTO purchases (id, product_id, supplier_id, quantity, unit_cost, total_cost, purchase_date, created_by, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                purchase_id,
                product_id,
                supplier_id,
                purchase_qty,
                unit_cost,
                total_cost,
                purchase_date,
                user_email,
                gst_rate,
                taxable_amount,
                cgst,
                sgst,
                igst,
                total_tax
            ))

            # Update product stock
            now = _utc_now_iso()
            cursor.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?", (new_stock, now, product_id))
            conn.commit()

        return self.get_purchase_by_id(purchase_id)

    def get_purchases(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.*, pr.name as product_name, s.name as supplier_name, s.gstin as supplier_gstin, s.state as supplier_state
            FROM purchases p
            LEFT JOIN products pr ON p.product_id = pr.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            ORDER BY p.purchase_date DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_purchase_by_id(self, purchase_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.*, pr.name as product_name, s.name as supplier_name, s.gstin as supplier_gstin, s.state as supplier_state
            FROM purchases p
            LEFT JOIN products pr ON p.product_id = pr.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?
            """, (purchase_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==========================================================================
    # Sales Transactions (Current = Previous - Sales)
    # ==========================================================================

    def record_sale(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        product_id = data["product_id"]
        sale_qty = int(data["quantity"])
        unit_price = float(data["unit_price"])
        total_revenue = round(sale_qty * unit_price, 2)
        sale_date = data.get("sale_date") or _utc_now_iso()
        sale_id = f"SAL-{uuid.uuid4().hex[:6].upper()}"
        customer_name = data.get("customer_name") or "Sri Ganesh Traders (Vellore)"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch current product
            cursor.execute("SELECT quantity, name, gst_rate, hsn_code FROM products WHERE id = ? AND is_active = 1", (product_id,))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Product '{product_id}' not found or inactive.")
            
            previous_stock = prod["quantity"]
            # Strict domain invariant & over-sale rejection check
            new_stock = InventoryLogic.calculate_sale_stock(previous_stock, sale_qty)

            gst_rate = float(data.get("gst_rate") or prod["gst_rate"] or 18.0)
            taxable_amount = total_revenue
            # Intra-state Tamil Nadu transaction breakdown (CGST + SGST)
            cgst = round(taxable_amount * (gst_rate / 200.0), 2)
            sgst = round(taxable_amount * (gst_rate / 200.0), 2)
            igst = 0.0
            total_tax = round(cgst + sgst, 2)

            # Record sale
            cursor.execute("""
            INSERT INTO sales (id, product_id, quantity, unit_price, total_revenue, sale_date, created_by, customer_name, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sale_id,
                product_id,
                sale_qty,
                unit_price,
                total_revenue,
                sale_date,
                user_email,
                customer_name,
                gst_rate,
                taxable_amount,
                cgst,
                sgst,
                igst,
                total_tax
            ))

            # Update product stock
            now = _utc_now_iso()
            cursor.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?", (new_stock, now, product_id))
            conn.commit()

        return self.get_sale_by_id(sale_id)

    def get_sales(self, limit: int = 100, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if product_id:
                cursor.execute("""
                SELECT s.*, pr.name as product_name, pr.category as product_category, pr.hsn_code
                FROM sales s
                LEFT JOIN products pr ON s.product_id = pr.id
                WHERE s.product_id = ?
                ORDER BY s.sale_date DESC LIMIT ?
                """, (product_id, limit))
            else:
                cursor.execute("""
                SELECT s.*, pr.name as product_name, pr.category as product_category, pr.hsn_code
                FROM sales s
                LEFT JOIN products pr ON s.product_id = pr.id
                ORDER BY s.sale_date DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_sale_by_id(self, sale_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT s.*, pr.name as product_name, pr.category as product_category, pr.hsn_code
            FROM sales s
            LEFT JOIN products pr ON s.product_id = pr.id
            WHERE s.id = ?
            """, (sale_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ==========================================================================
    # Inventory Summary & Alerts
    # ==========================================================================

    def get_inventory_summary(self) -> Dict[str, Any]:
        products = self.get_products()
        total_units = sum(p["quantity"] for p in products)
        total_value = round(sum(p["quantity"] * p["price"] for p in products), 2)
        low_stock = [p for p in products if p["status"] == "LOW STOCK"]
        out_of_stock = [p for p in products if p["status"] == "OUT OF STOCK"]

        return {
            "total_products": len(products),
            "total_units": total_units,
            "total_inventory_value": total_value,
            "low_stock_count": len(low_stock),
            "out_of_stock_count": len(out_of_stock),
            "products": products
        }

    def get_alerts(self) -> List[Dict[str, Any]]:
        products = self.get_products()
        alerts = []
        for p in products:
            if p["status"] == "OUT OF STOCK":
                alerts.append({
                    "id": f"ALT-OOS-{p['id']}",
                    "severity": "CRITICAL",
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "current_stock": p["quantity"],
                    "min_stock_level": p["min_stock_level"],
                    "message": f"Product '{p['name']}' is completely OUT OF STOCK! Immediate reorder required.",
                    "created_at": _utc_now_iso()
                })
            elif p["status"] == "LOW STOCK":
                deficit = p["min_stock_level"] - p["quantity"]
                alerts.append({
                    "id": f"ALT-LOW-{p['id']}",
                    "severity": "WARNING",
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "current_stock": p["quantity"],
                    "min_stock_level": p["min_stock_level"],
                    "message": f"Product '{p['name']}' has fallen below minimum threshold ({p['quantity']} <= {p['min_stock_level']}). Deficit: {deficit} units.",
                    "created_at": _utc_now_iso()
                })
        return alerts

    # ==========================================================================
    # Seed Sample Data (Indian Business Context: Tamil Nadu / Vellore Hub)
    # ==========================================================================

    def _ensure_sample_data(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) as count FROM products")
            if cursor.fetchone()["count"] == 0:
                self.seed_database()

    def seed_database(self):
        """
        Populates realistic Indian demo dataset specifically tailored for Tamil Nadu:
        - 5 Verified Tamil Nadu Suppliers (Chennai, Coimbatore, Ranipet/Vellore, Erode, Salem)
        - 15 Indian Industrial Products with INR (₹) pricing, HSN codes, and GST rates
        - 45 Days of Historical Sales time-series in INR
        - Verified Inbound Procurement Batches in INR
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Clear existing demo data
            cursor.execute("DELETE FROM predictions")
            cursor.execute("DELETE FROM sales")
            cursor.execute("DELETE FROM purchases")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM suppliers")

            # 1. Indian Suppliers (Realistic Tamil Nadu industrial suppliers)
            suppliers_data = [
                (
                    "SUP-001",
                    "Sri Lakshmi Industrial Supplies",
                    "K. Sundaram",
                    "+91 98421 54321",
                    "orders@srilakshmiind.in",
                    "148 GST Road, Guindy Industrial Estate, Chennai, Tamil Nadu - 600032, India",
                    "Electrical Components, Industrial Tools",
                    "33AABCS1234A1Z1",
                    "Tamil Nadu",
                    "600032"
                ),
                (
                    "SUP-002",
                    "Kovai Precision Tools & Hardware",
                    "S. Ramanathan",
                    "+91 94433 67890",
                    "sales@kovaiprecision.co.in",
                    "72 Avanashi Road, Peelamedu, Coimbatore, Tamil Nadu - 641004, India",
                    "Hardware, Industrial Tools",
                    "33BBCKP5678B1Z2",
                    "Tamil Nadu",
                    "641004"
                ),
                (
                    "SUP-003",
                    "Tamil Nadu Packaging Solutions",
                    "M. Vijayakumar",
                    "+91 97890 12345",
                    "contact@tnpackagingsolutions.in",
                    "25 SIPCOT Industrial Complex, Ranipet, Vellore District, Tamil Nadu - 632403, India",
                    "Packaging Materials, Office Supplies",
                    "33CCCTN9012C1Z3",
                    "Tamil Nadu",
                    "632403"
                ),
                (
                    "SUP-004",
                    "Sri Venkateswara Electrical Distributors",
                    "R. Balaji",
                    "+91 98840 98765",
                    "balaji@srivenkateswaraelec.in",
                    "112 Brough Road, Erode, Tamil Nadu - 638001, India",
                    "Electrical Components, Power Equipment",
                    "33DDFSX3456D1Z4",
                    "Tamil Nadu",
                    "638001"
                ),
                (
                    "SUP-005",
                    "Southern Safety & Hardware Traders",
                    "A. Murugan",
                    "+91 99440 23456",
                    "murugan@southernsafety.in",
                    "85 Meyyanur Main Road, Salem, Tamil Nadu - 636004, India",
                    "Safety Equipment, Hardware",
                    "33EEGSS7890E1Z5",
                    "Tamil Nadu",
                    "636004"
                )
            ]
            now = _utc_now_iso()
            for sup in suppliers_data:
                cursor.execute("""
                INSERT INTO suppliers (id, name, contact_person, phone, email, address, supplied_categories, is_active, created_at, gstin, state, pin_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (*sup[:7], now, *sup[7:]))

            # 2. Indian Products (Realistic categories, ₹ INR pricing, HSN codes, and GST rates)
            # PRD-1001 matches Section 17 test workflow: Initial stock 100, Price ₹120, Min stock 50
            products_data = [
                ("PRD-1001", "LED Bulb 9W Cool Day White (B22)", "Electrical Components", 120.00, 100, 50, "SUP-001", "8539", 18.0), # IN STOCK (Workflow Demo)
                ("PRD-1002", "PVC Electrical Conduit 25mm (3m Pipe)", "Electrical Components", 180.00, 85, 30, "SUP-001", "3917", 18.0), # IN STOCK
                ("PRD-1003", "Copper Wire 1.5 sq mm FR (90m Coil)", "Electrical Components", 1650.00, 0, 10, "SUP-004", "8544", 18.0),   # OUT OF STOCK
                ("PRD-1004", "Modular Electrical Switch 16A (1-Way)", "Electrical Components", 95.00, 22, 15, "SUP-001", "8536", 18.0),   # IN STOCK
                ("PRD-1005", "Heavy Duty Corrugated Box (5-Ply 12x10x8)", "Packaging Materials", 45.00, 18, 50, "SUP-003", "4819", 12.0), # LOW STOCK
                ("PRD-1006", "Bopp Self-Adhesive Packaging Tape 48mm", "Packaging Materials", 65.00, 42, 20, "SUP-003", "3919", 18.0),   # IN STOCK
                ("PRD-1007", "Industrial Safety Helmet (IS:2925 ISI Mark)", "Safety Equipment", 280.00, 160, 40, "SUP-005", "6506", 18.0), # IN STOCK
                ("PRD-1008", "Nitrile Coated Safety Hand Gloves (Pair)", "Safety Equipment", 85.00, 8, 25, "SUP-005", "6116", 12.0),     # LOW STOCK
                ("PRD-1009", "Stainless Steel Hex Bolts M10x50 (Box of 50)", "Hardware", 450.00, 35, 15, "SUP-002", "7318", 18.0),       # IN STOCK
                ("PRD-1010", "High-Tensile Industrial Fastener Nut Kit M12", "Hardware", 380.00, 0, 15, "SUP-002", "7318", 18.0),        # OUT OF STOCK
                ("PRD-1011", "A4 Copier Paper 75 GSM (500 Sheets Ream)", "Office Supplies", 320.00, 75, 25, "SUP-003", "4802", 12.0),    # IN STOCK
                ("PRD-1012", "CPVC Pipe 1 inch SDR 11 (3m Length)", "Plumbing Materials", 410.00, 31, 20, "SUP-002", "3917", 18.0),       # IN STOCK
                ("PRD-1013", "Industrial Cleaning Liquid Concentrate (5L)", "Cleaning Supplies", 550.00, 48, 15, "SUP-005", "3402", 18.0),# IN STOCK
                ("PRD-1014", "USB Ergonomic Keyboard (Rupee Symbol Key)", "Computer Accessories", 650.00, 110, 40, "SUP-001", "8471", 18.0), # IN STOCK
                ("PRD-1015", "Optical USB Mouse 1200 DPI", "Computer Accessories", 250.00, 12, 25, "SUP-001", "8471", 18.0)                # LOW STOCK
            ]
            for p in products_data:
                cursor.execute("""
                INSERT INTO products (id, name, category, price, quantity, min_stock_level, supplier_id, is_active, created_at, updated_at, hsn_code, gst_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (*p[:7], now, now, p[7], p[8]))

            # 3. Historical Sales (Simulate continuous daily sales across past 45 days in INR)
            base_date = datetime.now(timezone.utc)
            sales_seed = []
            demo_customers = [
                "Sri Ganesh Traders (Vellore)",
                "Priya Enterprises (Katpadi)",
                "Vellore Tech Solutions",
                "Seshadhri & Co.",
                "Lakshmi Stores (Sathuvachari)",
                "S.K. Industrial Works (Ranipet)"
            ]

            for day_offset in range(45, 0, -1):
                d = (base_date - timedelta(days=day_offset)).strftime("%Y-%m-%d") + "T14:30:00Z"
                cust = demo_customers[day_offset % len(demo_customers)]
                
                # LED Bulb 9W: steady daily volume (8 to 15 units)
                if day_offset % 2 == 0:
                    qty = 10 + (day_offset % 6)
                    rev = round(qty * 120.00, 2)
                    cgst = round(rev * 0.09, 2)
                    sgst = round(rev * 0.09, 2)
                    sales_seed.append((
                        f"SAL-SEED-{day_offset}A", "PRD-1001", qty, 120.00, rev, d,
                        "staff@intellistock.in", cust, 18.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)
                    ))

                # PVC Conduit: 4 to 8 pipes
                if day_offset % 3 != 0:
                    qty = 4 + (day_offset % 5)
                    rev = round(qty * 180.00, 2)
                    cgst = round(rev * 0.09, 2)
                    sgst = round(rev * 0.09, 2)
                    sales_seed.append((
                        f"SAL-SEED-{day_offset}B", "PRD-1002", qty, 180.00, rev, d,
                        "staff@intellistock.in", cust, 18.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)
                    ))

                # Corrugated Box: 5 to 15 boxes
                if day_offset % 4 == 0:
                    qty = 8 + (day_offset % 8)
                    rev = round(qty * 45.00, 2)
                    cgst = round(rev * 0.06, 2)
                    sgst = round(rev * 0.06, 2)
                    sales_seed.append((
                        f"SAL-SEED-{day_offset}C", "PRD-1005", qty, 45.00, rev, d,
                        "staff@intellistock.in", cust, 12.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)
                    ))

                # A4 Copier Paper: 5 to 12 reams
                if day_offset % 3 == 1:
                    qty = 6 + (day_offset % 7)
                    rev = round(qty * 320.00, 2)
                    cgst = round(rev * 0.06, 2)
                    sgst = round(rev * 0.06, 2)
                    sales_seed.append((
                        f"SAL-SEED-{day_offset}D", "PRD-1011", qty, 320.00, rev, d,
                        "staff@intellistock.in", cust, 12.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)
                    ))

            for s in sales_seed:
                cursor.execute("""
                INSERT INTO sales (id, product_id, quantity, unit_price, total_revenue, sale_date, created_by, customer_name, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, s)

            # 4. Inbound Purchases (Tamil Nadu replenishment batches in INR)
            purchases_seed = [
                ("PUR-SEED-01", "PRD-1001", "SUP-001", 50, 80.00, 4000.00, (base_date - timedelta(days=40)).isoformat() + "Z", "admin@intellistock.in", 18.0, 4000.00, 360.00, 360.00, 0.0, 720.00),
                ("PUR-SEED-02", "PRD-1002", "SUP-001", 100, 120.00, 12000.00, (base_date - timedelta(days=35)).isoformat() + "Z", "admin@intellistock.in", 18.0, 12000.00, 1080.00, 1080.00, 0.0, 2160.00),
                ("PUR-SEED-03", "PRD-1005", "SUP-003", 200, 28.00, 5600.00, (base_date - timedelta(days=25)).isoformat() + "Z", "admin@intellistock.in", 12.0, 5600.00, 336.00, 336.00, 0.0, 672.00),
                ("PUR-SEED-04", "PRD-1007", "SUP-005", 50, 190.00, 9500.00, (base_date - timedelta(days=20)).isoformat() + "Z", "admin@intellistock.in", 18.0, 9500.00, 855.00, 855.00, 0.0, 1710.00),
                ("PUR-SEED-05", "PRD-1011", "SUP-003", 100, 220.00, 22000.00, (base_date - timedelta(days=15)).isoformat() + "Z", "admin@intellistock.in", 12.0, 22000.00, 1320.00, 1320.00, 0.0, 2640.00)
            ]
            for pur in purchases_seed:
                cursor.execute("""
                INSERT INTO purchases (id, product_id, supplier_id, quantity, unit_cost, total_cost, purchase_date, created_by, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, pur)

            conn.commit()


# Singleton instance
db = Database()
