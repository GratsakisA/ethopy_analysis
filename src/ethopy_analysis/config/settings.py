"""
Configuration management for Ethopy analysis.

This module handles loading and managing configuration from various sources
including JSON files, environment variables, and default settings.
"""

import copy
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "database": {
        "host": "",
        "user": "",
        "password": "",
        "schemas": {
            "experiment": "lab_experiments",
            "stimulus": "lab_stimuli",
            "behavior": "lab_behavior",
            # Optional schema, only needed for animal weight analysis
            "mice": "lab_mice",
        },
    },
    "paths": {"output_dir": "./output", "config_dir": "./config"},
}


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    display_path: bool = False,
) -> Dict[str, Any]:
    """Load configuration from file or use defaults.

    Args:
        config_path: Path to configuration file (optional)
        display_path: Print the resolved config file path to stdout. Defaults to False.

    Returns:
        Configuration dictionary
    """
    config, config_source = load_config_with_source(config_path)

    if display_path and config_source:
        if config_source.name == "local_conf.json":
            print(f"Configuration loaded from ethopy local_conf: {config_source}")
        else:
            print(f"Configuration loaded from: {config_source}")

    return config


def find_config_file() -> Optional[Path]:
    """Find configuration file in common locations.

    Searches for ethopy_analysis config files first, then falls back to the
    ethopy package's ``~/.ethopy/local_conf.json``.

    Returns:
        Path to config file if found, None otherwise
    """
    # ethopy_analysis config files (highest priority)
    config_names = ["ethopy_config.json", "config.json", "dj_conf.json"]
    search_paths = [
        Path.cwd(),
        Path.cwd() / "config",
        Path.home() / ".ethopy",
        Path(__file__).parent.parent.parent.parent,
    ]

    for path in search_paths:
        for config_name in config_names:
            config_file = path / config_name
            if config_file.exists():
                logger.debug(f"Found config file: {config_file}")
                return config_file

    # Fallback: ethopy package local_conf.json
    ethopy_conf = Path.home() / ".ethopy" / "local_conf.json"
    if ethopy_conf.exists():
        logger.debug(f"Found ethopy local_conf: {ethopy_conf}")
        return ethopy_conf

    return None


def _is_ethopy_local_conf(config: Dict[str, Any]) -> bool:
    """Return True if *config* is in ethopy ``local_conf.json`` format.

    The ethopy format is identified by the presence of a ``dj_local_conf``
    top-level key that stores DataJoint settings with dot-notation sub-keys
    (e.g. ``"database.host"``).

    Args:
        config: Parsed JSON dictionary to inspect.

    Returns:
        True if the dictionary uses the ethopy local_conf format.
    """
    return "dj_local_conf" in config


def _parse_ethopy_local_conf(ethopy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an ethopy ``local_conf.json`` dict to ethopy_analysis config format.

    Ethopy stores database credentials under ``dj_local_conf`` using dot-notation
    keys (``"database.host"``, ``"database.user"``, etc.) and schema names under
    the ``SCHEMATA`` key.  This function maps them to the ethopy_analysis
    ``database`` structure.

    Args:
        ethopy_config: Dictionary loaded from ``~/.ethopy/local_conf.json``.

    Returns:
        Dictionary in the standard ethopy_analysis config format with a
        ``"database"`` top-level key.
    """
    dj_conf = ethopy_config.get("dj_local_conf", {})
    schemata = ethopy_config.get("SCHEMATA", {})

    default_schemas = DEFAULT_CONFIG["database"]["schemas"]
    schemas = {
        "experiment": schemata.get("experiment", default_schemas["experiment"]),
        "behavior": schemata.get("behavior", default_schemas["behavior"]),
        "stimulus": schemata.get("stimulus", default_schemas["stimulus"]),
        "mice": schemata.get("mice", default_schemas["mice"]),
    }

    host = dj_conf.get("database.host", "")
    port = dj_conf.get("database.port", 3306)
    # Append port to host if not already included (ethopy stores them separately)
    if host and ":" not in str(host):
        host = f"{host}:{port}"

    return {
        "database": {
            "host": host,
            "user": dj_conf.get("database.user", ""),
            "password": dj_conf.get("database.password", ""),
            "schemas": schemas,
        }
    }


def merge_configs(
    base_config: Dict[str, Any], override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Recursively merge two configuration dictionaries.

    Args:
        base_config: Base configuration dictionary
        override_config: Configuration to merge in

    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_configs(result[key], value)
        else:
            # Override or add new key
            result[key] = value

    return result


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Args:
        config: Base configuration dictionary

    Returns:
        Configuration with environment overrides applied
    """
    result = config.copy()

    # Database configuration overrides
    if "DJ_HOST" in os.environ:
        result["database"]["host"] = os.environ["DJ_HOST"]

    if "DJ_USER" in os.environ:
        result["database"]["user"] = os.environ["DJ_USER"]

    if "DJ_PASSWORD" in os.environ:
        result["database"]["password"] = os.environ["DJ_PASSWORD"]

    if "ETHOPY_OUTPUT_DIR" in os.environ:
        result["paths"]["output_dir"] = os.environ["ETHOPY_OUTPUT_DIR"]

    return result


def get_database_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get database configuration.

    Args:
        config: Full configuration dictionary (optional, will load if None)

    Returns:
        Database configuration dictionary
    """
    if config is None:
        config = load_config()

    return config.get("database", {})




def set_default_config(new_defaults: Dict[str, Any]):
    """Update default configuration values.

    Args:
        new_defaults: Dictionary with new default values
    """
    global DEFAULT_CONFIG

    DEFAULT_CONFIG = merge_configs(DEFAULT_CONFIG, new_defaults)

    logger.info("Updated default configuration")


def save_config(config: Dict[str, Any], config_path: Union[str, Path]):
    """Save configuration to a JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path where to save the configuration
    """
    config_file = Path(config_path)

    # Create directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Configuration saved to: {config_file}")

    except Exception as e:
        logger.error(f"Failed to save configuration to {config_file}: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration structure and values.

    Checks for:
    - Required sections and keys
    - Invalid value types
    - Security issues

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    is_valid = True

    # Check for required sections
    required_sections = ["database", "paths"]
    for section in required_sections:
        if section not in config:
            logger.error(f"Missing required configuration section: {section}")
            is_valid = False

    # Validate database config if present
    if "database" in config:
        db_config = config["database"]
        required_db_keys = ["host", "user", "schemas"]

        for key in required_db_keys:
            if key not in db_config:
                logger.error(f"Missing required database configuration key: {key}")
                is_valid = False

        # Validate schema mappings
        if "schemas" in db_config:
            if not isinstance(db_config["schemas"], dict):
                logger.error("database.schemas must be a dictionary")
                is_valid = False
            else:
                required_schemas = ["experiment", "stimulus", "behavior"]
                for schema in required_schemas:
                    if schema not in db_config["schemas"]:
                        logger.warning(f"Missing schema mapping for '{schema}'")

    if is_valid:
        logger.debug("Configuration validation passed")
    else:
        logger.error("Configuration validation failed")

    return is_valid


def load_config_with_source(
    config_path: Optional[Union[str, Path]] = None,
) -> Tuple[Dict[str, Any], Optional[Path]]:
    """Load configuration and return both config and source file path.

    Args:
        config_path: Path to configuration file (optional)

    Returns:
        Tuple of (configuration dictionary, source file path or None)
    """
    # Start with a deep copy so mutations never bleed into DEFAULT_CONFIG
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_source = None

    # Try to load from file
    if config_path:
        config_file = Path(config_path)
    else:
        # Search for config file in common locations
        config_file = find_config_file()

    if config_file and config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)

            # Detect and convert ethopy local_conf.json format
            if _is_ethopy_local_conf(file_config):
                logger.info("Detected ethopy local_conf.json format — converting")
                file_config = _parse_ethopy_local_conf(file_config)

            config = merge_configs(config, file_config)
            config_source = config_file
            logger.info(f"Loaded configuration from: {config_file}")

        except Exception as e:
            logger.warning(f"Failed to load config from {config_file}: {e}")
            logger.info("Using default configuration")
    else:
        logger.info("No config file found, using defaults")

    # Apply environment variable overrides
    config = apply_env_overrides(config)

    # Validate configuration
    if not validate_config(config):
        logger.warning("Configuration validation failed")

    return config, config_source


def get_config_summary() -> str:
    """Get a summary of the current configuration.

    Returns:
        String summary of configuration
    """
    config, config_source = load_config_with_source()

    summary = "Ethopy Analysis Configuration Summary:\n"
    summary += "=" * 50 + "\n"

    # Configuration source
    if config_source:
        if config_source.name == "local_conf.json":
            summary += f"Configuration file: {config_source} (ethopy local_conf)\n"
        else:
            summary += f"Configuration file: {config_source}\n"
    else:
        summary += "Configuration file: Using defaults (no file found)\n"
    
    # Check for environment variable overrides
    env_vars = ["DJ_HOST", "DJ_USER", "DJ_PASSWORD", "ETHOPY_OUTPUT_DIR"]
    active_env_vars = [var for var in env_vars if var in os.environ]
    if active_env_vars:
        summary += f"Environment overrides: {', '.join(active_env_vars)}\n"
    
    summary += "\n"

    # Database info (without password)
    db_config = config["database"]
    summary += f"Database Host: {db_config.get('host', 'Not set')}\n"
    summary += f"Database User: {db_config.get('user', 'Not set')}\n"
    password_status = "Set" if db_config.get('password') else "Not set"
    summary += f"Database Password: {password_status}\n"
    summary += f"Schemas: {len(db_config.get('schemas', {}))}\n"

    # List schema mappings
    if db_config.get('schemas'):
        summary += "Schema mappings:\n"
        for schema_type, schema_name in db_config['schemas'].items():
            summary += f"  {schema_type}: {schema_name}\n"

    # Paths info
    paths_config = config["paths"]
    summary += f"\nOutput Directory: {paths_config.get('output_dir', './output')}\n"

    return summary
