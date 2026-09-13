"""
PulseCart Synthetic Data Generator - Distribution Models
Defines transition probabilities, dimensional multipliers, dwell time distributions,
and category parameters for realistic e-commerce simulation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# Funnel Stage Definitions in strict sequence
FUNNEL_STAGES: List[Tuple[int, str]] = [
    (1, "landing_page"),
    (2, "product_view"),
    (3, "add_to_cart"),
    (4, "checkout_started"),
    (5, "payment_started"),
    (6, "purchase"),
]

STAGE_NAMES: List[str] = [name for _, name in FUNNEL_STAGES]
STAGE_STEP_MAP: Dict[str, int] = {name: step for step, name in FUNNEL_STAGES}

# Base Transition Probabilities between consecutive stages
# S1 -> S2, S2 -> S3, S3 -> S4, S4 -> S5, S5 -> S6
BASE_TRANSITION_PROBABILITIES: Dict[str, float] = {
    "landing_to_product_view": 0.62,
    "product_view_to_add_to_cart": 0.44,
    "add_to_cart_to_checkout": 0.48,
    "checkout_to_payment_base": 0.72,
    "payment_to_purchase_base": 0.80,
}

# Parameterized Checkout A/B Experiment Target Lifts (Target: ~8.9% Compound Relative Lift)
# Step 4 (checkout -> payment): +4.5% boost
# Step 5 (payment -> purchase): +4.21% boost
# 1.045 * 1.0421 = 1.089005 (8.9005% compound relative lift)
AB_EXPERIMENT_CONFIG: Dict[str, Dict[str, float]] = {
    "control": {
        "checkout_to_payment_multiplier": 1.0000,
        "payment_to_purchase_multiplier": 1.0000,
    },
    "treatment": {
        "checkout_to_payment_multiplier": 1.0490,
        "payment_to_purchase_multiplier": 1.0460,
    },
}

# Orthogonal Multiplicative Variance Factors
DEVICE_MULTIPLIERS: Dict[str, float] = {
    "Desktop": 1.12,
    "Mobile": 0.88,
    "Tablet": 0.98,
}

CHANNEL_MULTIPLIERS: Dict[str, float] = {
    "Organic Search": 1.05,
    "Paid Search": 0.98,
    "Email": 1.20,
    "Direct": 1.15,
    "Social": 0.82,
    "Referral": 1.02,
}

COUNTRY_MULTIPLIERS: Dict[str, float] = {
    "US": 1.08,
    "UK": 1.04,
    "CA": 1.02,
    "DE": 0.96,
    "FR": 0.94,
    "AU": 1.00,
}

SEGMENT_MULTIPLIERS: Dict[str, float] = {
    "VIP": 1.35,
    "Regular": 1.10,
    "Bargain": 0.90,
}

USER_TYPE_MULTIPLIERS: Dict[str, float] = {
    "Returning User": 1.25,
    "New User": 0.85,
}

# Categorical Sampling Distributions & Proportions
DEVICE_DISTRIBUTION: Dict[str, float] = {
    "Desktop": 0.35,
    "Mobile": 0.55,
    "Tablet": 0.10,
}

CHANNEL_DISTRIBUTION: Dict[str, float] = {
    "Organic Search": 0.28,
    "Paid Search": 0.24,
    "Direct": 0.18,
    "Social": 0.15,
    "Email": 0.10,
    "Referral": 0.05,
}

COUNTRY_DISTRIBUTION: Dict[str, float] = {
    "US": 0.50,
    "UK": 0.18,
    "CA": 0.12,
    "DE": 0.08,
    "FR": 0.07,
    "AU": 0.05,
}

SEGMENT_DISTRIBUTION: Dict[str, float] = {
    "Regular": 0.60,
    "Bargain": 0.25,
    "VIP": 0.15,
}

PAYMENT_METHOD_DISTRIBUTION: Dict[str, float] = {
    "Credit Card": 0.45,
    "Apple Pay": 0.25,
    "PayPal": 0.20,
    "Klarna": 0.10,
}

# Dwell Time Log-Normal Parameters (mu, sigma) in seconds
DWELL_TIME_PARAMS: Dict[str, Tuple[float, float]] = {
    "landing_to_view": (3.0, 0.6),        # median ~20s
    "view_to_cart": (3.2, 0.7),           # median ~25s
    "cart_to_checkout": (3.4, 0.7),       # median ~30s
    "checkout_to_payment": (3.8, 0.6),    # median ~45s (filling billing/shipping address)
    "payment_to_purchase": (3.5, 0.5),    # median ~33s (entering payment & confirming)
}

# Product Catalog Parameters (5 Categories, 20 products each = 100 products conformed)
PRODUCT_CATEGORIES_CONFIG: Dict[str, Dict[str, Any]] = {
    "Electronics": {
        "price_min": 49.99,
        "price_max": 399.99,
        "target_margin_pct": 0.42,
        "prefix": "ELE",
        "sample_names": [
            "AeroPulse Wireless Headphones", "ProStream HD Webcam", "OmniCharge 65W GaN Charger",
            "SoundSphere Bluetooth Speaker", "ClarityView 27-inch Monitor", "KeyCraft Mechanical Keyboard",
            "GlideOptix Wireless Mouse", "PowerVault 20000mAh PowerBank", "HyperDrive 1TB Portable SSD",
            "AuraRGB LED Desk Lamp", "NanoLite Noise-Cancelling Earbuds", "UltraCast 4K Streaming Stick",
            "SmartHome Mini Hub", "FlexArm Dual Monitor Mount", "PulseFit Smart Fitness Tracker",
            "EchoWave Conference Speakerphone", "VividCapture 4K Capture Card", "ThermoGuard Smart Thermostat",
            "ProGamer Wired Headset", "SafeShield USB-C Security Key"
        ],
    },
    "Apparel": {
        "price_min": 24.99,
        "price_max": 129.99,
        "target_margin_pct": 0.58,
        "prefix": "APP",
        "sample_names": [
            "Classic Merino Wool Crewneck", "Everyday Flex Chino Pant", "Waterproof Commuter Jacket",
            "Breathable Mesh Running Tee", "All-Season Denim Jacket", "EcoWarm Recycled Fleece",
            "Tailored Oxford Dress Shirt", "Essential Cotton Crew Socks 3-Pack", "Urban Active Jogger Pants",
            "Thermal Ribbed Beanie", "Packable Windbreaker Jacket", "Heritage Canvas Weekender Bag",
            "Seamless Workout Leggings", "Vintage Washed Graphic Hoodie", "StormProof Rain Shell",
            "ComfortFit Lounge Sweatpants", "Lightweight Linen Summer Shirt", "UV Protection Outdoor Cap",
            "Heavyweight Loopback Sweatshirt", "Merino Wool Blend Scarf"
        ],
    },
    "Home & Kitchen": {
        "price_min": 29.99,
        "price_max": 189.99,
        "target_margin_pct": 0.52,
        "prefix": "HAK",
        "sample_names": [
            "Precision Pour-Over Coffee Kettle", "Cast Iron Pre-Seasoned Skillet 10in", "Stainless Steel Mixing Bowl Set",
            "Cold Brew Glass Carafe 1.5L", "ChefSeries 8-inch Chef Knife", "AromaMist Essential Oil Diffuser",
            "Silicone Cooking Utensil 8-Piece Set", "Double-Walled Espresso Glasses 4-Pack", "Bamboo Cutting Board with Juice Groove",
            "Heavyweight French Fry Press", "Digital Instant-Read Meat Thermometer", "Vacuum Insulated Travel Tumbler 20oz",
            "Under-Cabinet LED Strip Lighting", "Non-Stick Ceramic Baking Sheet Set", "UltraSoft Bamboo Cotton Towel Set",
            "AirTight Food Storage Canister 5-Pack", "Automatic Electric Salt & Pepper Grinders", "Compact Multi-Blade Spiralizer",
            "Stoneware Dinnerware Set 16-Piece", "Silicone Microwave Popcorn Popper"
        ],
    },
    "Beauty & Personal Care": {
        "price_min": 14.99,
        "price_max": 89.99,
        "target_margin_pct": 0.65,
        "prefix": "BPC",
        "sample_names": [
            "Hyaluronic Acid Deep Hydration Serum", "Revitalizing Vitamin C Daily Cleanser", "Nourishing Argan Oil Hair Mask",
            "Broad Spectrum SPF 50 Mineral Sunscreen", "Botanical Gentle Face Exfoliator", "Calming Lavender Night Repair Cream",
            "Peptide Firming Eye Complex", "Detoxifying Charcoal Clay Mask", "Volumizing Biotin Hair Shampoo",
            "Silk Smooth Moisturizing Body Butter", "Antioxidant Green Tea Facial Toner", "Gentle Sulfate-Free Body Wash",
            "Overnight Barrier Repair Balm", "Rejuvenating Rosehip Facial Oil", "Hydrating Coconut Lip Polish Set",
            "Clarifying Salicylic Acid Spot Treatment", "Mineral Rich Bath Soak Salts", "Brightening Niacinamide Concentrate",
            "Restorative Collagen Hand Cream", "Aromatherapy Shower Steamers 6-Pack"
        ],
    },
    "Sports & Outdoors": {
        "price_min": 19.99,
        "price_max": 249.99,
        "target_margin_pct": 0.48,
        "prefix": "SPO",
        "sample_names": [
            "ProGrip High-Density Yoga Mat", "Heavy-Duty Resistance Bands 5-Pack", "Insulated Hydro Canteen 32oz",
            "Ultralight Carbon Trekking Poles", "Compact Inflatable Camping Pillow", "Fast-Drying Microfiber Gym Towel",
            "Speed Jump Rope with Ball Bearings", "Tactical Folding Multi-Tool Knife", "Waterproof Dry Bag 20L Backpack",
            "Adjustable Dumbbell Set 5-25lbs", "High-Visibility Running Vest with LED", "Portable Aluminum Camping Chair",
            "TrailReady 500-Lumen Headlamp", "Foam Muscle Recovery Roller", "Heavy-Duty Kettlebell 16kg",
            "GripTech Weightlifting Gloves", "Quick-Pitch 2-Person Backpacking Tent", "Stainless Steel Campfire Mess Kit",
            "Electrolyte Hydration Flask 24oz", "Thermal Insulated Ski Gloves"
        ],
    },
}
