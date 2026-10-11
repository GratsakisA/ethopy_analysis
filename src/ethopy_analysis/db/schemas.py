"""
Unified database schema management for Ethopy analysis.

This module provides a simple, unified interface for database connections
and schema access with automatic caching and configuration management.
"""

import datajoint as dj
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Module-level cache for DataJoint schemas
# Simple cache using connection string as key
_cached_schemas: Dict[str, Dict[str, Any]] = {}

# Schemas that every ethopy installation is expected to provide. Any other
# configured schema (e.g. 'mice') is optional: it is never created on the
# server and a missing one only warns instead of breaking the connection.
REQUIRED_SCHEMAS = ("experiment", "stimulus", "behavior")


# Public API - Main user interface


def get_schema(schema_name: str, config: Optional[Dict[str, Any]] = None):
    """
    Get a specific schema by name.

    Args:
        schema_name: Name of the schema to retrieve ('experiment', 'behavior', or 'stimulus')
        config: Optional database configuration. If None, uses default config.

    Returns:
        DataJoint virtual module for the specified schema, or None if schema not found

    Example:
        from ethopy_analysis.config.settings import load_config
        config = load_config()
        experiment = get_schema('experiment', config)
        behavior = get_schema('behavior', config)
        stimulus = get_schema('stimulus', config)

        # Usage examples:
        trials_df = experiment.Trial.fetch(format='frame')
        licking_df = behavior.Licking.fetch(format='frame')
        conditions_df = stimulus.Condition.fetch(format='frame')
    """
    schemas = get_all_schemas(config)

    if schema_name not in schemas:
        logger.warning(
            f"Schema '{schema_name}' not found. Available schemas: {list(schemas.keys())}"
        )
        return None

    return schemas[schema_name]


def get_all_schemas(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get all three schemas (experiment, behavior, stimulus) at once.

    This is the main function that handles caching and schema creation.

    Args:
        config: Optional database configuration. If None, uses default config.

    Returns:
        Dictionary with keys 'experiment', 'behavior', 'stimulus' containing
        the corresponding DataJoint virtual modules

    Example:
        from ethopy_analysis.config.settings import load_config
        config = load_config()
        schemas = get_all_schemas(config)
        trials = schemas['experiment'].Trial.fetch(format='frame')
        licking = schemas['behavior'].Licking.fetch(format='frame')
        conditions = schemas['stimulus'].Condition.fetch(format='frame')
    """
    # Get configuration (pass explicitly instead of loading internally)
    if config is None:
        # Import here to avoid circular imports
        from ..config.settings import get_database_config

        config = get_database_config()

    # Create simple cache key from configuration
    cache_key = _create_cache_key(config)

    # Return cached schemas if they exist
    if cache_key in _cached_schemas:
        logger.debug(f"Using cached schemas for: {_get_host_from_config(config)}")
        return _cached_schemas[cache_key]

    # Create new schemas (expensive operation)
    logger.info(f"Creating DataJoint schemas for: {_get_host_from_config(config)}")

    try:
        # Set up database connection and create schemas
        schemas = _setup_database_connection(config=config)

        # Cache the schemas
        _cached_schemas[cache_key] = schemas
        logger.info(f"Successfully cached schemas for: {_get_host_from_config(config)}")

        return schemas

    except Exception as e:
        logger.error(f"Failed to create DataJoint schemas: {e}")
        raise ConnectionError(f"Failed to create DataJoint schemas: {e}")


def clear_schema_cache():
    """
    Clear all cached schemas.

    Useful for testing, configuration changes, or when you want to force
    recreation of schemas.

    Example:
        clear_schema_cache()
        schemas = get_all_schemas()  # Will recreate schemas
    """
    global _cached_schemas
    _cached_schemas.clear()
    logger.info("Schema cache cleared")


def show_cached_schemas() -> Dict[str, str]:
    """
    Show information about currently cached schemas.

    Returns:
        Dictionary with cache keys and basic info about cached schemas

    Example:
        cached_info = show_cached_schemas()
        print(f"Cached configurations: {list(cached_info.keys())}")
    """
    cache_info = {}

    for cache_key, schemas in _cached_schemas.items():
        # Extract host from simple cache key format (host_user_hash)
        try:
            host = cache_key.split("_")[0]
        except IndexError:
            host = "unknown"

        cache_info[cache_key] = {
            "host": host,
            "schemas": list(schemas.keys()),
            "num_schemas": len(schemas),
        }

    logger.info(f"Currently cached: {len(cache_info)} configurations")
    return cache_info


def test_connection(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Test database connection and schema access.

    Args:
        config: Optional database configuration. If None, uses default config.

    Returns:
        True if connection successful, False otherwise

    Example:
        from ethopy_analysis.config.settings import load_config
        config = load_config()
        if test_connection(config):
            print("Database connection successful!")
        else:
            print("Database connection failed!")
    """
    try:
        if config is None:
            # Import here to avoid circular imports
            from ..config.settings import get_database_config

            config = get_database_config()

        # Test connection by creating schemas (without caching)
        _setup_database_connection(config=config)

        # Try a simple query to test the connection
        dj.conn().ping()

        logger.info("Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def validate_schema_config(config: Dict[str, Any]) -> bool:
    """
    Validate that configuration contains required schema information.

    Args:
        config: Database configuration dictionary

    Returns:
        True if valid, raises ValueError if invalid
    """
    # Handle both full config and database-only config
    if "database" in config:
        db_config = config["database"]
    else:
        db_config = config

    required_fields = ["host", "user", "password", "schemas"]
    missing_fields = [field for field in required_fields if field not in db_config]

    if missing_fields:
        raise ValueError(f"Missing required configuration fields: {missing_fields}")

    required_schemas = ["experiment", "behavior", "stimulus"]
    missing_schemas = [
        schema for schema in required_schemas if schema not in db_config["schemas"]
    ]

    if missing_schemas:
        raise ValueError(f"Missing required schema configurations: {missing_schemas}")

    return True


# Internal API - Lower-level functions
def _setup_database_connection(
    host: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    custom_schemata: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Configure and establish database connection.

    Args:
        host: Database host address.
        user: Database username.
        password: Database password.
        custom_schemata: Dictionary mapping schema names to database names.
        config: Full configuration dictionary (alternative to individual params).

    Returns:
        A dictionary of schema virtual modules.

    Raises:
        ValueError: If required database parameters are missing.
    """
    # If config is provided, extract database parameters from it
    if config is not None:
        # Handle both full config and database-only config
        if "database" in config:
            db_config = config["database"]
        else:
            db_config = config

        host = host or db_config.get("host")
        user = user or db_config.get("user")
        password = password or db_config.get("password")
        custom_schemata = custom_schemata or db_config.get("schemas")
    else:
        # Load configuration using the unified system
        from ..config.settings import load_config, get_database_config

        config = load_config()
        db_config = get_database_config(config)

        host = host or db_config.get("host")
        user = user or db_config.get("user")
        password = password or db_config.get("password")
        custom_schemata = custom_schemata or db_config.get("schemas")

    # Use provided parameters, falling back to config values
    db_params = {
        "host": host,
        "user": user,
        "password": password,
    }

    # Check environment variables for any missing parameters
    if not db_params["host"]:
        db_params["host"] = os.environ.get("DJ_HOST")
    if not db_params["user"]:
        db_params["user"] = os.environ.get("DJ_USER")
    if not db_params["password"]:
        db_params["password"] = os.environ.get("DJ_PASSWORD")

    # If missing credentials, use interactive configuration
    missing_params = [k for k, v in db_params.items() if not v]
    if missing_params:
        logger.info("Missing database credentials, using interactive configuration...")
        try:
            from ..config.interactive import get_database_config_interactive

            interactive_db_config = get_database_config_interactive()

            # Update with interactive values
            db_params["host"] = interactive_db_config["host"]
            db_params["user"] = interactive_db_config["user"]
            db_params["password"] = interactive_db_config["password"]

        except Exception as e:
            error_msg = f"Failed to get database configuration: {e}"
            logger.critical(error_msg)
            raise ValueError(error_msg)

    # Configure datajoint
    dj.config["enable_python_native_blobs"] = True
    dj.config["database.host"] = db_params["host"]
    dj.config["database.user"] = db_params["user"]
    dj.config["database.password"] = db_params["password"]
    # Control TLS for the DB connection. Default False = never request SSL,
    # which avoids "SSL is required but the server doesn't support it" errors
    # against servers without TLS. NOTE: with this DataJoint version, use_tls
    # of None/True both add an SSL param and the no-SSL fallback only catches
    # InternalError (not the OperationalError 2026 raised here), so False is the
    # only reliable value for non-TLS servers. Override via the "use_tls" key in
    # the database config (set to True or a dict to require/configure TLS).
    dj.config["database.use_tls"] = db_config.get("use_tls", False)
    logger.info("DataJoint configuration completed")

    # Create schema virtual modules
    schemas = _create_schemas(custom_schemata)

    return schemas


def _create_schemas(custom_schemata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create virtual modules for schemas based on configuration.

    Args:
        custom_schemata: Dictionary mapping schema names to database names.

    Returns:
        A dictionary of schema virtual modules.

    Raises:
        Exception: If error occurs loading schema mappings.
    """
    # If custom schema mappings are provided, use them directly
    if custom_schemata is not None:
        logger.info("Using custom schema mappings")
        schemata = custom_schemata
    else:
        # Default schema mappings if no config found
        logger.warning("No schema configuration found, using defaults")
        schemata = {
            "experiment": "lab_experiments",
            "stimulus": "lab_stimuli",
            "behavior": "lab_behavior",
            "mice": "lab_mice",
        }

    # Create virtual modules for each schema
    schemas = {}
    for schema_name, actual_schema in schemata.items():
        logger.debug(f"Creating virtual module for {schema_name} -> {actual_schema}")
        if schema_name in REQUIRED_SCHEMAS:
            schemas[schema_name] = dj.create_virtual_module(
                schema_name, actual_schema, create_tables=True, create_schema=True
            )
            continue

        # Optional schema: attach to it only if it already exists on the server
        try:
            schemas[schema_name] = dj.create_virtual_module(
                schema_name, actual_schema, create_tables=False, create_schema=False
            )
        except Exception as e:
            logger.warning(
                f"Optional schema '{schema_name}' -> '{actual_schema}' is not "
                f"available and was skipped: {e}"
            )

    logger.info(f"Created {len(schemas)} virtual schema modules")
    return schemas


def _create_cache_key(config: Dict[str, Any]) -> str:
    """Create a simple cache key from database configuration."""
    # Handle both full config and database-only config
    if "database" in config:
        db_config = config["database"]
    else:
        db_config = config

    # Use host, user, and schema hash for simple but effective caching
    host = db_config.get("host", "unknown")
    user = db_config.get("user", "unknown")
    schemas_hash = hash(str(sorted(db_config.get("schemas", {}).items())))

    return f"{host}_{user}_{schemas_hash}"


def _get_host_from_config(config: Dict[str, Any]) -> str:
    """Extract host from config for logging purposes."""
    if "database" in config:
        return config["database"].get("host", "unknown")
    else:
        return config.get("host", "unknown")


# Initialize logging
logger.info("DataJoint schema manager loaded")
