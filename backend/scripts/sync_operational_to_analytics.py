"""PulseCart Operational Data to Analytics Pipeline Exporter

Exports operational backend orders into warehouse-compatible Parquet and CSV formats.
Maintains strict segregation between transactional operational data and synthetic A/B experiment data:
- `data_source` = 'operational_backend'
- `ab_variant` = None (operational orders are NOT part of simulated A/B testing)
- `session_id` = None (REST API checkout transactions do not carry web clickstream tracking)
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("operational_exporter")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "operational"
RAW_ORDERS_PATH = DATA_DIR / "raw" / "orders.parquet"


def get_expected_schema():
    """Reads expected schema from existing raw orders table."""
    if RAW_ORDERS_PATH.exists():
        table = pq.read_table(RAW_ORDERS_PATH)
        return table.schema
    return None


def export_from_records(records: list) -> pd.DataFrame:
    """Converts raw order dictionary records into analytics-compatible DataFrame."""
    if not records:
        logger.warning("No records to export. Creating empty DataFrame with schema.")
        columns = [
            "order_id", "session_id", "user_id", "order_date", "order_timestamp",
            "subtotal", "tax_amount", "shipping_fee", "discount_amount", "total_amount",
            "payment_method", "status", "ab_variant", "data_source"
        ]
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(records)
    # Ensure types and column order
    required_cols = [
        "order_id", "session_id", "user_id", "order_date", "order_timestamp",
        "subtotal", "tax_amount", "shipping_fee", "discount_amount", "total_amount",
        "payment_method", "status", "ab_variant", "data_source"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df["subtotal"] = pd.to_numeric(df["subtotal"], errors="coerce").round(2)
    df["tax_amount"] = pd.to_numeric(df["tax_amount"], errors="coerce").round(2)
    df["shipping_fee"] = pd.to_numeric(df["shipping_fee"], errors="coerce").round(2)
    df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").round(2)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").round(2)
    df["data_source"] = "operational_backend"

    return df[required_cols]


def save_operational_data(df: pd.DataFrame):
    """Saves DataFrame as Parquet and CSV in data/operational/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = OUTPUT_DIR / "operational_orders.parquet"
    csv_path = OUTPUT_DIR / "operational_orders.csv"

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    logger.info(f"Successfully exported {len(df)} operational orders to:")
    logger.info(f"  - Parquet: {parquet_path}")
    logger.info(f"  - CSV:     {csv_path}")


def sample_operational_orders():
    """Generates verified operational backend orders for standalone pipeline testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "order_id": "OP-ORD-LIVE-001",
            "session_id": None,
            "user_id": "OP-USR-101",
            "order_date": now.strftime("%Y-%m-%d"),
            "order_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "subtotal": 320.99,
            "tax_amount": 25.68,
            "shipping_fee": 0.00,
            "discount_amount": 0.00,
            "total_amount": 346.67,
            "payment_method": "CREDIT_CARD",
            "status": "CONFIRMED",
            "ab_variant": None,
            "data_source": "operational_backend"
        },
        {
            "order_id": "OP-ORD-LIVE-002",
            "session_id": None,
            "user_id": "OP-USR-102",
            "order_date": now.strftime("%Y-%m-%d"),
            "order_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "subtotal": 80.00,
            "tax_amount": 6.40,
            "shipping_fee": 5.00,
            "discount_amount": 0.00,
            "total_amount": 91.40,
            "payment_method": "DEBIT_CARD",
            "status": "CONFIRMED",
            "ab_variant": None,
            "data_source": "operational_backend"
        }
    ]


if __name__ == "__main__":
    records = sample_operational_orders()
    df = export_from_records(records)
    save_operational_data(df)
    print("\nExported Operational Orders Sample:")
    print(df.to_string())
