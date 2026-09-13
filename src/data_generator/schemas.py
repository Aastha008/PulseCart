"""
PulseCart Synthetic Data Generator - Schema Definitions
Defines relational table schemas, column types, and data contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass(frozen=True)
class UserSchema:
    """User entity representing the customer master record."""
    user_id: str
    created_at: datetime
    country: str
    acquisition_channel: str
    customer_segment: str
    device_preference: str = "Mobile"

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "user_id",
            "created_at",
            "country",
            "acquisition_channel",
            "customer_segment",
            "device_preference",
        ]


@dataclass(frozen=True)
class ProductSchema:
    """Product catalog conformed dimension entity."""
    product_id: str
    product_name: str
    category: str
    cost: float
    price: float
    margin: float
    inventory_count: int = 500
    created_at: Optional[datetime] = None

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "product_id",
            "product_name",
            "category",
            "cost",
            "price",
            "margin",
            "inventory_count",
            "created_at",
        ]


@dataclass(frozen=True)
class SessionSchema:
    """Session browsing visit entity."""
    session_id: str
    user_id: str
    session_start: datetime
    session_end: datetime
    device_type: str
    country: str
    traffic_source: str
    channel: str
    is_bounce: bool
    is_returning_user: bool
    is_new_user: bool
    ab_variant: str
    experiment_id: str = "exp_checkout_streamline_v1"

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "session_id",
            "user_id",
            "session_start",
            "session_end",
            "device_type",
            "country",
            "traffic_source",
            "channel",
            "is_bounce",
            "is_returning_user",
            "is_new_user",
            "ab_variant",
            "experiment_id",
        ]


@dataclass(frozen=True)
class EventSchema:
    """Clickstream telemetry event entity."""
    event_id: str
    session_id: str
    user_id: str
    event_timestamp: datetime
    event_name: str
    event_type: str
    step_number: int
    page_url: str
    product_id: Optional[str] = None
    cart_value: float = 0.0

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "event_id",
            "session_id",
            "user_id",
            "event_timestamp",
            "event_name",
            "event_type",
            "step_number",
            "page_url",
            "product_id",
            "cart_value",
        ]


@dataclass(frozen=True)
class OrderSchema:
    """Order transaction entity."""
    order_id: str
    session_id: str
    user_id: str
    order_date: str
    order_timestamp: datetime
    subtotal: float
    tax_amount: float
    shipping_fee: float
    discount_amount: float
    total_amount: float
    payment_method: str
    status: str = "completed"
    ab_variant: str = "control"

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "order_id",
            "session_id",
            "user_id",
            "order_date",
            "order_timestamp",
            "subtotal",
            "tax_amount",
            "shipping_fee",
            "discount_amount",
            "total_amount",
            "payment_method",
            "status",
            "ab_variant",
        ]


@dataclass(frozen=True)
class OrderItemSchema:
    """Individual line item within an order entity."""
    order_item_id: str
    order_id: str
    product_id: str
    quantity: int
    unit_price: float
    unit_cost: float
    line_total: float
    total_item_price: float
    line_profit: float

    @classmethod
    def column_names(cls) -> List[str]:
        return [
            "order_item_id",
            "order_id",
            "product_id",
            "quantity",
            "unit_price",
            "unit_cost",
            "line_total",
            "total_item_price",
            "line_profit",
        ]


@dataclass
class DatasetContainer:
    """Container holding all six generated DataFrames."""
    users: Any
    products: Any
    sessions: Any
    events: Any
    orders: Any
    order_items: Any
