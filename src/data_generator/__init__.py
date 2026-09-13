"""
PulseCart Synthetic Data Generation Engine
Package initializing schemas, distribution parameters, generator, and CLI.
"""

from .schemas import (
    UserSchema,
    ProductSchema,
    SessionSchema,
    EventSchema,
    OrderSchema,
    OrderItemSchema,
    DatasetContainer,
)
from .distributions import (
    FUNNEL_STAGES,
    STAGE_NAMES,
    STAGE_STEP_MAP,
    BASE_TRANSITION_PROBABILITIES,
    AB_EXPERIMENT_CONFIG,
    DEVICE_MULTIPLIERS,
    CHANNEL_MULTIPLIERS,
    COUNTRY_MULTIPLIERS,
    SEGMENT_MULTIPLIERS,
    USER_TYPE_MULTIPLIERS,
    PRODUCT_CATEGORIES_CONFIG,
)
from .generator import (
    GeneratorConfig,
    SyntheticDataGenerator,
)

__all__ = [
    "UserSchema",
    "ProductSchema",
    "SessionSchema",
    "EventSchema",
    "OrderSchema",
    "OrderItemSchema",
    "DatasetContainer",
    "FUNNEL_STAGES",
    "STAGE_NAMES",
    "STAGE_STEP_MAP",
    "BASE_TRANSITION_PROBABILITIES",
    "AB_EXPERIMENT_CONFIG",
    "DEVICE_MULTIPLIERS",
    "CHANNEL_MULTIPLIERS",
    "COUNTRY_MULTIPLIERS",
    "SEGMENT_MULTIPLIERS",
    "USER_TYPE_MULTIPLIERS",
    "PRODUCT_CATEGORIES_CONFIG",
    "GeneratorConfig",
    "SyntheticDataGenerator",
]
