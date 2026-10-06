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
    2. AWS Cloud Mode: Amazon DynamoDB Single-Table Design with live consistent reads
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
                self._sync_sqlite_from_dynamo_if_empty()
            except Exception as e:
                logger.warning(f"DynamoDB initialization notice: {e}. SQLite local engine remains active.")

    def _sync_sqlite_from_dynamo_if_empty(self):
        """Pre-populates SQLite cache from authoritative DynamoDB if local container DB is empty."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) as count FROM products")
                if cursor.fetchone()["count"] == 0:
                    logger.info("Initializing SQLite container mirror from authoritative DynamoDB items...")
                    products = self._dynamo_get_products()
                    suppliers = self._dynamo_get_suppliers()
                    for sup in suppliers:
                        cursor.execute("""
                        INSERT OR IGNORE INTO suppliers (id, name, contact_person, phone, email, address, supplied_categories, is_active, created_at, gstin, state, pin_code)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            sup["id"], sup["name"], sup.get("contact_person", ""), sup.get("phone", ""),
                            sup.get("email", ""), sup.get("address", ""), sup.get("supplied_categories", "General"),
                            sup.get("is_active", 1), sup.get("created_at", _utc_now_iso()), sup.get("gstin", ""),
                            sup.get("state", "Tamil Nadu"), sup.get("pin_code", "632007")
                        ))
                    for p in products:
                        cursor.execute("""
                        INSERT OR IGNORE INTO products (id, name, category, price, quantity, min_stock_level, supplier_id, is_active, created_at, updated_at, hsn_code, gst_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            p["id"], p["name"], p["category"], p["price"], p["quantity"], p["min_stock_level"],
                            p.get("supplier_id"), p.get("is_active", 1), p.get("created_at", _utc_now_iso()),
                            p.get("updated_at", _utc_now_iso()), p.get("hsn_code", "8536"), p.get("gst_rate", 18.0)
                        ))
                    conn.commit()
        except Exception as e:
            logger.warning(f"SQLite mirror sync notice: {e}")

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

        # Seed data if empty and running local mode
        if self.mode != "aws":
            self._ensure_sample_data()

    # ==========================================================================
    # Supplier Methods
    # ==========================================================================

    def _dynamo_get_suppliers(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression="begins_with(PK, :prefix) AND SK = :meta",
            ExpressionAttributeValues={":prefix": "SUPPLIER#", ":meta": "METADATA"}
        )
        items = resp.get("Items", [])
        suppliers = []
        for it in items:
            s = _decimal_to_native(it)
            s["id"] = s.get("supplier_id") or s["PK"].replace("SUPPLIER#", "")
            s["is_active"] = 1 if s.get("is_active", True) else 0
            if s["is_active"] != 1:
                continue
            if search and search.strip():
                st = search.strip().lower()
                if st not in s.get("name", "").lower() and st not in s.get("contact_person", "").lower():
                    continue
            suppliers.append(s)
        suppliers.sort(key=lambda x: x.get("name", ""))
        return suppliers

    def _dynamo_get_supplier_by_id(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        resp = self.table.get_item(Key={"PK": f"SUPPLIER#{supplier_id}", "SK": "METADATA"}, ConsistentRead=True)
        it = resp.get("Item")
        if not it:
            return None
        s = _decimal_to_native(it)
        s["id"] = s.get("supplier_id") or s["PK"].replace("SUPPLIER#", "")
        s["is_active"] = 1 if s.get("is_active", True) else 0
        return s

    def get_suppliers(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_suppliers(search=search)
            except Exception as e:
                logger.warning(f"DynamoDB get_suppliers error: {e}. Falling back to SQLite.")
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
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_supplier_by_id(supplier_id)
            except Exception as e:
                logger.warning(f"DynamoDB get_supplier_by_id error: {e}. Falling back to SQLite.")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_supplier(self, data: Dict[str, Any]) -> Dict[str, Any]:
        supplier_id = f"SUP-{uuid.uuid4().hex[:6].upper()}"
        now = _utc_now_iso()

        if self.mode == "aws" and self.table is not None:
            try:
                item = {
                    "PK": f"SUPPLIER#{supplier_id}",
                    "SK": "METADATA",
                    "supplier_id": supplier_id,
                    "name": data["name"],
                    "contact_person": data["contact_person"],
                    "phone": data["phone"],
                    "email": data["email"],
                    "address": data["address"],
                    "supplied_categories": data.get("supplied_categories", "General"),
                    "is_active": True,
                    "created_at": now,
                    "gstin": data.get("gstin", ""),
                    "state": data.get("state", "Tamil Nadu"),
                    "pin_code": data.get("pin_code", "632007")
                }
                self.table.put_item(Item=item)
            except Exception as e:
                logger.warning(f"DynamoDB create_supplier notice: {e}")

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

        if self.mode == "aws" and self.table is not None:
            try:
                sup = self.get_supplier_by_id(supplier_id)
                if sup:
                    update_expr = []
                    expr_names = {}
                    expr_vals = {}
                    for k, v in data.items():
                        if v is not None:
                            update_expr.append(f"#{k} = :{k}")
                            expr_names[f"#{k}"] = k
                            expr_vals[f":{k}"] = v
                    if update_expr:
                        self.table.update_item(
                            Key={"PK": f"SUPPLIER#{supplier_id}", "SK": "METADATA"},
                            UpdateExpression=f"SET {', '.join(update_expr)}",
                            ExpressionAttributeNames=expr_names,
                            ExpressionAttributeValues=expr_vals
                        )
            except Exception as e:
                logger.warning(f"DynamoDB update_supplier notice: {e}")

        return self.get_supplier_by_id(supplier_id)

    def delete_supplier(self, supplier_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE suppliers SET is_active = 0 WHERE id = ?", (supplier_id,))
            conn.commit()
            rc = cursor.rowcount > 0

        if self.mode == "aws" and self.table is not None:
            try:
                self.table.update_item(
                    Key={"PK": f"SUPPLIER#{supplier_id}", "SK": "METADATA"},
                    UpdateExpression="SET is_active = :a",
                    ExpressionAttributeValues={":a": False}
                )
            except Exception as e:
                logger.warning(f"DynamoDB delete_supplier notice: {e}")

        return rc

    # ==========================================================================
    # Product Methods
    # ==========================================================================

    def _dynamo_get_products(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = "name",
        order: Optional[str] = "asc"
    ) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression="begins_with(PK, :prefix) AND SK = :meta",
            ExpressionAttributeValues={":prefix": "PRODUCT#", ":meta": "METADATA"}
        )
        items = resp.get("Items", [])
        
        # Build supplier lookup map for supplier_name
        sup_map = {s["id"]: s["name"] for s in self._dynamo_get_suppliers()}

        results = []
        for it in items:
            p = _decimal_to_native(it)
            p["id"] = p.get("product_id") or p["PK"].replace("PRODUCT#", "")
            p["is_active"] = 1 if p.get("is_active", True) else 0
            if p["is_active"] != 1:
                continue
            p["quantity"] = int(p.get("quantity", 0))
            p["min_stock_level"] = int(p.get("min_stock_level", 0))
            p["price"] = float(p.get("price", 0.0))
            p["gst_rate"] = float(p.get("gst_rate", 18.0))
            p["supplier_name"] = sup_map.get(p.get("supplier_id"), "")
            p["status"] = InventoryLogic.evaluate_stock_status(p["quantity"], p["min_stock_level"])

            if category and category.strip() and category.strip().lower() != "all":
                if p.get("category", "").strip().lower() != category.strip().lower():
                    continue

            if search and search.strip():
                st = search.strip().lower()
                fields_to_check = [
                    p.get("name", ""),
                    p.get("id", ""),
                    p.get("category", ""),
                    p.get("hsn_code", ""),
                    p.get("supplier_name", "")
                ]
                if not any(st in str(f).lower() for f in fields_to_check):
                    continue

            results.append(p)

        reverse = (order.lower() == "desc") if order else False
        sort_key_fn = lambda x: (x.get(sort_by) is None, str(x.get(sort_by, "")).lower())
        if sort_by in ["price", "quantity"]:
            sort_key_fn = lambda x: float(x.get(sort_by, 0))
        results.sort(key=sort_key_fn, reverse=reverse)
        return results

    def _dynamo_get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        resp = self.table.get_item(Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"}, ConsistentRead=True)
        it = resp.get("Item")
        if not it:
            return None
        p = _decimal_to_native(it)
        p["id"] = p.get("product_id") or p["PK"].replace("PRODUCT#", "")
        p["is_active"] = 1 if p.get("is_active", True) else 0
        if p["is_active"] != 1:
            return None
        p["quantity"] = int(p.get("quantity", 0))
        p["min_stock_level"] = int(p.get("min_stock_level", 0))
        p["price"] = float(p.get("price", 0.0))
        p["gst_rate"] = float(p.get("gst_rate", 18.0))
        if p.get("supplier_id"):
            sup = self.get_supplier_by_id(p["supplier_id"])
            p["supplier_name"] = sup["name"] if sup else ""
        p["status"] = InventoryLogic.evaluate_stock_status(p["quantity"], p["min_stock_level"])
        return p

    def get_products(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: Optional[str] = "name",
        order: Optional[str] = "asc"
    ) -> List[Dict[str, Any]]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_products(search, category, sort_by, order)
            except Exception as e:
                logger.warning(f"DynamoDB get_products error: {e}. Falling back to SQLite.")

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
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_product_by_id(product_id)
            except Exception as e:
                logger.warning(f"DynamoDB get_product_by_id error: {e}. Falling back to SQLite.")

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

        if self.mode == "aws" and self.table is not None:
            try:
                item = {
                    "PK": f"PRODUCT#{product_id}",
                    "SK": "METADATA",
                    "product_id": product_id,
                    "name": data["name"],
                    "category": data["category"],
                    "price": _native_to_decimal(float(data["price"])),
                    "quantity": int(data["quantity"]),
                    "min_stock_level": int(data["min_stock_level"]),
                    "supplier_id": data.get("supplier_id"),
                    "hsn_code": data.get("hsn_code", "8536"),
                    "gst_rate": _native_to_decimal(float(data.get("gst_rate", 18.0))),
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now
                }
                self.table.put_item(Item=item)
            except Exception as e:
                logger.warning(f"DynamoDB create_product notice: {e}")

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

        if self.mode == "aws" and self.table is not None:
            try:
                update_expr = ["#ua = :ua"]
                expr_names = {"#ua": "updated_at"}
                expr_vals = {":ua": now}
                for k, v in data.items():
                    if v is not None:
                        update_expr.append(f"#{k} = :{k}")
                        expr_names[f"#{k}"] = k
                        if k in ["price", "gst_rate"]:
                            expr_vals[f":{k}"] = _native_to_decimal(float(v))
                        elif k in ["quantity", "min_stock_level"]:
                            expr_vals[f":{k}"] = int(v)
                        else:
                            expr_vals[f":{k}"] = v
                self.table.update_item(
                    Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"},
                    UpdateExpression=f"SET {', '.join(update_expr)}",
                    ExpressionAttributeNames=expr_names,
                    ExpressionAttributeValues=expr_vals
                )
            except Exception as e:
                logger.warning(f"DynamoDB update_product notice: {e}")

        return self.get_product_by_id(product_id)

    def delete_product(self, product_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
            conn.commit()
            rc = cursor.rowcount > 0

        if self.mode == "aws" and self.table is not None:
            try:
                self.table.update_item(
                    Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"},
                    UpdateExpression="SET is_active = :a",
                    ExpressionAttributeValues={":a": False}
                )
            except Exception as e:
                logger.warning(f"DynamoDB delete_product notice: {e}")

        return rc

    # ==========================================================================
    # Purchase Transactions (Current = Previous + Purchases)
    # ==========================================================================

    def _dynamo_record_purchase(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        product_id = data["product_id"]
        supplier_id = data["supplier_id"]
        purchase_qty = int(data["quantity"])
        unit_cost = float(data["unit_cost"])
        total_cost = round(purchase_qty * unit_cost, 2)
        purchase_date = data.get("purchase_date") or _utc_now_iso()
        purchase_id = f"PUR-{uuid.uuid4().hex[:6].upper()}"

        # Fetch product with ConsistentRead=True
        prod = self._dynamo_get_product_by_id(product_id)
        if not prod:
            raise ValueError(f"Product '{product_id}' not found or inactive.")

        previous_stock = prod["quantity"]
        new_stock = InventoryLogic.calculate_purchase_stock(previous_stock, purchase_qty)

        # Supplier GST calculation
        sup = self.get_supplier_by_id(supplier_id)
        sup_state = (sup["state"] if sup and sup.get("state") else "Tamil Nadu").strip().lower()
        gst_rate = float(data.get("gst_rate") or prod.get("gst_rate") or 18.0)
        taxable_amount = total_cost
        if sup_state in ["tamil nadu", "tamilnadu", "tn"]:
            cgst = round(taxable_amount * (gst_rate / 200.0), 2)
            sgst = round(taxable_amount * (gst_rate / 200.0), 2)
            igst = 0.0
        else:
            cgst = 0.0
            sgst = 0.0
            igst = round(taxable_amount * (gst_rate / 100.0), 2)
        total_tax = round(cgst + sgst + igst, 2)

        now = _utc_now_iso()

        # Update authoritative product stock in DynamoDB
        self.table.update_item(
            Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"},
            UpdateExpression="SET quantity = :q, updated_at = :u",
            ExpressionAttributeValues={":q": new_stock, ":u": now}
        )

        # Put purchase item in DynamoDB
        purchase_item = {
            "PK": f"PURCHASE#{purchase_id}",
            "SK": f"DATE#{purchase_date}",
            "GSI1_PK": f"PRODUCT#{product_id}",
            "GSI1_SK": f"PURCHASE#{purchase_date}",
            "purchase_id": purchase_id,
            "product_id": product_id,
            "supplier_id": supplier_id,
            "quantity": purchase_qty,
            "unit_cost": _native_to_decimal(unit_cost),
            "total_cost": _native_to_decimal(total_cost),
            "purchase_date": purchase_date,
            "created_by": user_email,
            "gst_rate": _native_to_decimal(gst_rate),
            "taxable_amount": _native_to_decimal(taxable_amount),
            "cgst": _native_to_decimal(cgst),
            "sgst": _native_to_decimal(sgst),
            "igst": _native_to_decimal(igst),
            "total_tax": _native_to_decimal(total_tax)
        }
        self.table.put_item(Item=purchase_item)

        # Mirror to local SQLite if initialized
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO purchases (id, product_id, supplier_id, quantity, unit_cost, total_cost, purchase_date, created_by, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    purchase_id, product_id, supplier_id, purchase_qty, unit_cost, total_cost, purchase_date,
                    user_email, gst_rate, taxable_amount, cgst, sgst, igst, total_tax
                ))
                cursor.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?", (new_stock, now, product_id))
                conn.commit()
        except Exception as e:
            logger.warning(f"Mirroring purchase to SQLite skipped: {e}")

        res = _decimal_to_native(purchase_item)
        res["id"] = purchase_id
        res["product_name"] = prod.get("name", "")
        res["supplier_name"] = sup.get("name", "") if sup else ""
        return res

    def record_purchase(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_record_purchase(data, user_email)
            except Exception as e:
                logger.warning(f"DynamoDB record_purchase error: {e}. Falling back to SQLite.")

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
                cgst = round(taxable_amount * (gst_rate / 200.0), 2)
                sgst = round(taxable_amount * (gst_rate / 200.0), 2)
                igst = 0.0
            else:
                cgst = 0.0
                sgst = 0.0
                igst = round(taxable_amount * (gst_rate / 100.0), 2)
            total_tax = round(cgst + sgst + igst, 2)

            previous_stock = prod["quantity"]
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

    def _dynamo_get_purchases(self, limit: int = 50) -> List[Dict[str, Any]]:
        resp = self.table.scan(
            FilterExpression="begins_with(PK, :prefix)",
            ExpressionAttributeValues={":prefix": "PURCHASE#"}
        )
        items = resp.get("Items", [])
        
        prod_map = {p["id"]: p["name"] for p in self._dynamo_get_products()}
        sup_map = {s["id"]: s for s in self._dynamo_get_suppliers()}

        purchases = []
        for it in items:
            pur = _decimal_to_native(it)
            pur["id"] = pur.get("purchase_id") or pur["PK"].replace("PURCHASE#", "")
            pur["product_name"] = prod_map.get(pur.get("product_id"), pur.get("product_id"))
            s_obj = sup_map.get(pur.get("supplier_id"), {})
            pur["supplier_name"] = s_obj.get("name", pur.get("supplier_id"))
            pur["supplier_gstin"] = s_obj.get("gstin", "")
            pur["supplier_state"] = s_obj.get("state", "Tamil Nadu")
            purchases.append(pur)

        purchases.sort(key=lambda x: x.get("purchase_date", ""), reverse=True)
        return purchases[:limit]

    def get_purchases(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_purchases(limit=limit)
            except Exception as e:
                logger.warning(f"DynamoDB get_purchases error: {e}. Falling back to SQLite.")

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

    def _dynamo_record_sale(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        product_id = data["product_id"]
        sale_qty = int(data["quantity"])
        unit_price = float(data["unit_price"])
        total_revenue = round(sale_qty * unit_price, 2)
        sale_date = data.get("sale_date") or _utc_now_iso()
        sale_id = f"SAL-{uuid.uuid4().hex[:6].upper()}"
        customer_name = data.get("customer_name") or "Sri Ganesh Traders (Vellore)"

        # Fetch product with ConsistentRead=True
        prod = self._dynamo_get_product_by_id(product_id)
        if not prod:
            raise ValueError(f"Product '{product_id}' not found or inactive.")

        previous_stock = prod["quantity"]
        new_stock = InventoryLogic.calculate_sale_stock(previous_stock, sale_qty)

        gst_rate = float(data.get("gst_rate") or prod.get("gst_rate") or 18.0)
        taxable_amount = total_revenue
        cgst = round(taxable_amount * (gst_rate / 200.0), 2)
        sgst = round(taxable_amount * (gst_rate / 200.0), 2)
        igst = 0.0
        total_tax = round(cgst + sgst, 2)

        now = _utc_now_iso()

        # Update authoritative product stock in DynamoDB
        self.table.update_item(
            Key={"PK": f"PRODUCT#{product_id}", "SK": "METADATA"},
            UpdateExpression="SET quantity = :q, updated_at = :u",
            ExpressionAttributeValues={":q": new_stock, ":u": now}
        )

        sale_item = {
            "PK": f"SALE#{sale_id}",
            "SK": f"DATE#{sale_date}",
            "GSI1_PK": f"PRODUCT#{product_id}",
            "GSI1_SK": f"SALE#{sale_date}",
            "sale_id": sale_id,
            "product_id": product_id,
            "quantity": sale_qty,
            "unit_price": _native_to_decimal(unit_price),
            "total_revenue": _native_to_decimal(total_revenue),
            "sale_date": sale_date,
            "created_by": user_email,
            "customer_name": customer_name,
            "gst_rate": _native_to_decimal(gst_rate),
            "taxable_amount": _native_to_decimal(taxable_amount),
            "cgst": _native_to_decimal(cgst),
            "sgst": _native_to_decimal(sgst),
            "igst": _native_to_decimal(igst),
            "total_tax": _native_to_decimal(total_tax)
        }
        self.table.put_item(Item=sale_item)

        # Mirror to local SQLite if initialized
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO sales (id, product_id, quantity, unit_price, total_revenue, sale_date, created_by, customer_name, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sale_id, product_id, sale_qty, unit_price, total_revenue, sale_date, user_email,
                    customer_name, gst_rate, taxable_amount, cgst, sgst, igst, total_tax
                ))
                cursor.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?", (new_stock, now, product_id))
                conn.commit()
        except Exception as e:
            logger.warning(f"Mirroring sale to SQLite skipped: {e}")

        res = _decimal_to_native(sale_item)
        res["id"] = sale_id
        res["product_name"] = prod.get("name", "")
        return res

    def record_sale(self, data: Dict[str, Any], user_email: str) -> Dict[str, Any]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_record_sale(data, user_email)
            except Exception as e:
                logger.warning(f"DynamoDB record_sale error: {e}. Falling back to SQLite.")

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
            new_stock = InventoryLogic.calculate_sale_stock(previous_stock, sale_qty)

            gst_rate = float(data.get("gst_rate") or prod["gst_rate"] or 18.0)
            taxable_amount = total_revenue
            cgst = round(taxable_amount * (gst_rate / 200.0), 2)
            sgst = round(taxable_amount * (gst_rate / 200.0), 2)
            igst = 0.0
            total_tax = round(cgst + sgst, 2)

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

            now = _utc_now_iso()
            cursor.execute("UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?", (new_stock, now, product_id))
            conn.commit()

        return self.get_sale_by_id(sale_id)

    def _dynamo_get_sales(self, limit: int = 100, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if product_id:
            resp = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1_PK = :gsi_pk AND begins_with(GSI1_SK, :gsi_sk)",
                ExpressionAttributeValues={
                    ":gsi_pk": f"PRODUCT#{product_id}",
                    ":gsi_sk": "SALE#"
                }
            )
        else:
            resp = self.table.scan(
                FilterExpression="begins_with(PK, :prefix)",
                ExpressionAttributeValues={":prefix": "SALE#"}
            )
        items = resp.get("Items", [])
        
        prods = {p["id"]: p for p in self._dynamo_get_products()}

        sales = []
        for it in items:
            s = _decimal_to_native(it)
            s["id"] = s.get("sale_id") or s["PK"].replace("SALE#", "")
            pr = prods.get(s.get("product_id"), {})
            s["product_name"] = pr.get("name", s.get("product_id"))
            s["product_category"] = pr.get("category", "")
            s["hsn_code"] = pr.get("hsn_code", "8536")
            sales.append(s)

        sales.sort(key=lambda x: x.get("sale_date", ""), reverse=True)
        return sales[:limit]

    def get_sales(self, limit: int = 100, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "aws" and self.table is not None:
            try:
                return self._dynamo_get_sales(limit=limit, product_id=product_id)
            except Exception as e:
                logger.warning(f"DynamoDB get_sales error: {e}. Falling back to SQLite.")

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
        """
        Calculates authoritative inventory summary KPIs.
        In AWS Mode, dynamically computes metrics from live DynamoDB table.
        """
        products = self.get_products()
        total_units = sum(int(p["quantity"]) for p in products)
        total_value = round(sum(int(p["quantity"]) * float(p["price"]) for p in products), 2)
        low_stock = [p for p in products if int(p["quantity"]) > 0 and int(p["quantity"]) <= int(p["min_stock_level"])]
        out_of_stock = [p for p in products if int(p["quantity"]) <= 0]

        return {
            "total_products": len(products),
            "total_units": total_units,
            "total_inventory_value": total_value,
            "low_stock_count": len(low_stock),
            "out_of_stock_count": len(out_of_stock),
            "products": products
        }

    def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Enforces strict inventory alert rules from authoritative persistent store:
        - Stock <= 0: CRITICAL (out of stock)
        - Stock > 0 and Stock <= min_stock_level: WARNING (low stock deficit)
        - Stock > min_stock_level: NO ALERT (healthy, excluded from active alerts)
        """
        products = self.get_products()
        alerts = []
        for p in products:
            qty = int(p["quantity"])
            min_thresh = int(p["min_stock_level"])
            if qty <= 0:
                alerts.append({
                    "id": f"ALT-OOS-{p['id']}",
                    "severity": "CRITICAL",
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "current_stock": qty,
                    "min_stock_level": min_thresh,
                    "message": f"Product '{p['name']}' is completely OUT OF STOCK! Immediate reorder required.",
                    "created_at": _utc_now_iso()
                })
            elif qty <= min_thresh:
                deficit = min_thresh - qty
                alerts.append({
                    "id": f"ALT-LOW-{p['id']}",
                    "severity": "WARNING",
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "current_stock": qty,
                    "min_stock_level": min_thresh,
                    "message": f"Product '{p['name']}' has fallen below minimum threshold ({qty} <= {min_thresh}). Deficit: {deficit} units.",
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
            cursor.execute("DELETE FROM predictions")
            cursor.execute("DELETE FROM sales")
            cursor.execute("DELETE FROM purchases")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM suppliers")

            # 1. Indian Suppliers
            suppliers_data = [
                ("SUP-001", "Sri Lakshmi Industrial Supplies", "K. Sundaram", "+91 98421 54321", "orders@srilakshmiind.in", "148 GST Road, Guindy Industrial Estate, Chennai, Tamil Nadu - 600032, India", "Electrical Components, Industrial Tools", "33AABCS1234A1Z1", "Tamil Nadu", "600032"),
                ("SUP-002", "Kovai Precision Tools & Hardware", "S. Ramanathan", "+91 94433 67890", "sales@kovaiprecision.co.in", "72 Avanashi Road, Peelamedu, Coimbatore, Tamil Nadu - 641004, India", "Hardware, Industrial Tools", "33BBCKP5678B1Z2", "Tamil Nadu", "641004"),
                ("SUP-003", "Tamil Nadu Packaging Solutions", "M. Vijayakumar", "+91 97890 12345", "contact@tnpackagingsolutions.in", "25 SIPCOT Industrial Complex, Ranipet, Vellore District, Tamil Nadu - 632403, India", "Packaging Materials, Office Supplies", "33CCCTN9012C1Z3", "Tamil Nadu", "632403"),
                ("SUP-004", "Sri Venkateswara Electrical Distributors", "R. Balaji", "+91 98840 98765", "balaji@srivenkateswaraelec.in", "112 Brough Road, Erode, Tamil Nadu - 638001, India", "Electrical Components, Power Equipment", "33DDFSX3456D1Z4", "Tamil Nadu", "638001"),
                ("SUP-005", "Southern Safety & Hardware Traders", "A. Murugan", "+91 99440 23456", "murugan@southernsafety.in", "85 Meyyanur Main Road, Salem, Tamil Nadu - 636004, India", "Safety Equipment, Hardware", "33EEGSS7890E1Z5", "Tamil Nadu", "636004")
            ]
            now = _utc_now_iso()
            for sup in suppliers_data:
                cursor.execute("""
                INSERT INTO suppliers (id, name, contact_person, phone, email, address, supplied_categories, is_active, created_at, gstin, state, pin_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (*sup[:7], now, *sup[7:]))

            # 2. Indian Products
            products_data = [
                ("PRD-1001", "LED Bulb 9W Cool Day White (B22)", "Electrical Components", 120.00, 100, 50, "SUP-001", "8539", 18.0),
                ("PRD-1002", "PVC Electrical Conduit 25mm (3m Pipe)", "Electrical Components", 180.00, 85, 30, "SUP-001", "3917", 18.0),
                ("PRD-1003", "Copper Wire 1.5 sq mm FR (90m Coil)", "Electrical Components", 1650.00, 0, 10, "SUP-004", "8544", 18.0),
                ("PRD-1004", "Modular Electrical Switch 16A (1-Way)", "Electrical Components", 95.00, 22, 15, "SUP-001", "8536", 18.0),
                ("PRD-1005", "Heavy Duty Corrugated Box (5-Ply 12x10x8)", "Packaging Materials", 45.00, 18, 50, "SUP-003", "4819", 12.0),
                ("PRD-1006", "Bopp Self-Adhesive Packaging Tape 48mm", "Packaging Materials", 65.00, 42, 20, "SUP-003", "3919", 18.0),
                ("PRD-1007", "Industrial Safety Helmet (IS:2925 ISI Mark)", "Safety Equipment", 280.00, 160, 40, "SUP-005", "6506", 18.0),
                ("PRD-1008", "Nitrile Coated Safety Hand Gloves (Pair)", "Safety Equipment", 85.00, 8, 25, "SUP-005", "6116", 12.0),
                ("PRD-1009", "Stainless Steel Hex Bolts M10x50 (Box of 50)", "Hardware", 450.00, 35, 15, "SUP-002", "7318", 18.0),
                ("PRD-1010", "High-Tensile Industrial Fastener Nut Kit M12", "Hardware", 380.00, 0, 15, "SUP-002", "7318", 18.0),
                ("PRD-1011", "A4 Copier Paper 75 GSM (500 Sheets Ream)", "Office Supplies", 320.00, 75, 25, "SUP-003", "4802", 12.0),
                ("PRD-1012", "CPVC Pipe 1 inch SDR 11 (3m Length)", "Plumbing Materials", 410.00, 31, 20, "SUP-002", "3917", 18.0),
                ("PRD-1013", "Industrial Cleaning Liquid Concentrate (5L)", "Cleaning Supplies", 550.00, 48, 15, "SUP-005", "3402", 18.0),
                ("PRD-1014", "USB Ergonomic Keyboard (Rupee Symbol Key)", "Computer Accessories", 650.00, 110, 40, "SUP-001", "8471", 18.0),
                ("PRD-1015", "Optical USB Mouse 1200 DPI", "Computer Accessories", 250.00, 12, 25, "SUP-001", "8471", 18.0)
            ]
            for p in products_data:
                cursor.execute("""
                INSERT INTO products (id, name, category, price, quantity, min_stock_level, supplier_id, is_active, created_at, updated_at, hsn_code, gst_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (*p[:7], now, now, p[7], p[8]))

            base_date = datetime.now(timezone.utc)
            sales_seed = []
            demo_customers = [
                "Sri Ganesh Traders (Vellore)", "Priya Enterprises (Katpadi)",
                "Vellore Tech Solutions", "Seshadhri & Co.",
                "Lakshmi Stores (Sathuvachari)", "S.K. Industrial Works (Ranipet)"
            ]

            for day_offset in range(45, 0, -1):
                d = (base_date - timedelta(days=day_offset)).strftime("%Y-%m-%d") + "T14:30:00Z"
                cust = demo_customers[day_offset % len(demo_customers)]
                if day_offset % 2 == 0:
                    qty = 10 + (day_offset % 6)
                    rev = round(qty * 120.00, 2)
                    cgst = round(rev * 0.09, 2)
                    sgst = round(rev * 0.09, 2)
                    sales_seed.append((f"SAL-SEED-{day_offset}A", "PRD-1001", qty, 120.00, rev, d, "staff@intellistock.in", cust, 18.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)))
                if day_offset % 3 != 0:
                    qty = 4 + (day_offset % 5)
                    rev = round(qty * 180.00, 2)
                    cgst = round(rev * 0.09, 2)
                    sgst = round(rev * 0.09, 2)
                    sales_seed.append((f"SAL-SEED-{day_offset}B", "PRD-1002", qty, 180.00, rev, d, "staff@intellistock.in", cust, 18.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)))
                if day_offset % 4 == 0:
                    qty = 8 + (day_offset % 8)
                    rev = round(qty * 45.00, 2)
                    cgst = round(rev * 0.06, 2)
                    sgst = round(rev * 0.06, 2)
                    sales_seed.append((f"SAL-SEED-{day_offset}C", "PRD-1005", qty, 45.00, rev, d, "staff@intellistock.in", cust, 12.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)))
                if day_offset % 3 == 1:
                    qty = 6 + (day_offset % 7)
                    rev = round(qty * 320.00, 2)
                    cgst = round(rev * 0.06, 2)
                    sgst = round(rev * 0.06, 2)
                    sales_seed.append((f"SAL-SEED-{day_offset}D", "PRD-1011", qty, 320.00, rev, d, "staff@intellistock.in", cust, 12.0, rev, cgst, sgst, 0.0, round(cgst + sgst, 2)))

            for s in sales_seed:
                cursor.execute("""
                INSERT INTO sales (id, product_id, quantity, unit_price, total_revenue, sale_date, created_by, customer_name, gst_rate, taxable_amount, cgst, sgst, igst, total_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, s)

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

        # Seed DynamoDB table if active in AWS mode
        if self.mode == "aws" and self.table is not None:
            try:
                with self.table.batch_writer() as batch:
                    for sup in suppliers_data:
                        batch.put_item(Item={
                            "PK": f"SUPPLIER#{sup[0]}",
                            "SK": "METADATA",
                            "supplier_id": sup[0],
                            "name": sup[1],
                            "contact_person": sup[2],
                            "phone": sup[3],
                            "email": sup[4],
                            "address": sup[5],
                            "supplied_categories": sup[6],
                            "gstin": sup[7],
                            "state": sup[8],
                            "pin_code": sup[9],
                            "is_active": True,
                            "created_at": now
                        })
                    for p in products_data:
                        batch.put_item(Item={
                            "PK": f"PRODUCT#{p[0]}",
                            "SK": "METADATA",
                            "product_id": p[0],
                            "name": p[1],
                            "category": p[2],
                            "price": _native_to_decimal(p[3]),
                            "quantity": p[4],
                            "min_stock_level": p[5],
                            "supplier_id": p[6],
                            "hsn_code": p[7],
                            "gst_rate": _native_to_decimal(p[8]),
                            "is_active": True,
                            "created_at": now,
                            "updated_at": now
                        })
            except Exception as e:
                logger.warning(f"DynamoDB batch seed notice: {e}")


# Singleton instance
db = Database()
