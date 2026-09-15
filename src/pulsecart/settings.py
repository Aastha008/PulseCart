"""
PulseCart Kedro Project Settings.

Manages configuration loading, hook registration, and environment defaults.
Kedro concept: settings.py acts as the central control plane for customizing
framework behavior (e.g. hooking telemetry, schema validation, or cloud authentication).
"""

from kedro.config import OmegaConfigLoader

# Dynamic OmegaConfigLoader supports yaml interpolation, environment variables,
# and merged parameter patterns.
CONFIG_LOADER_CLASS = OmegaConfigLoader
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "default_run_env": "local",
    "config_patterns": {
        "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
        "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
    },
}
