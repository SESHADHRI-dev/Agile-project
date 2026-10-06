import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch

def test_dynamo_mode_live():
    with patch.dict(os.environ, {"STORAGE_MODE": "aws"}):
        from backend.app.database import Database
        aws_db = Database()
        if aws_db.table is not None:
            # 1. Test get_products
            prods = aws_db.get_products()
            assert len(prods) == 15
            for p in prods:
                assert "id" in p
                assert "quantity" in p
                assert "min_stock_level" in p
                assert "status" in p

            # 2. Test get_product_by_id
            p1003 = aws_db.get_product_by_id("PRD-1003")
            assert p1003 is not None
            assert p1003["id"] == "PRD-1003"
            assert "min_stock_level" in p1003

            # 3. Test get_alerts
            alerts = aws_db.get_alerts()
            assert isinstance(alerts, list)
            for a in alerts:
                assert a["severity"] in ["CRITICAL", "WARNING"]
                assert a["current_stock"] <= a["min_stock_level"]
