"""
Ethopy Analysis: Data analysis and visualization package for Ethopy behavioral experiments.

This package provides tools for:
- Loading and processing behavioral data from Ethopy experiments
- Creating visualizations for animal and session-level analysis
- Exporting data to various formats
- Database connectivity with DataJoint

Key modules:
- data: Data loading and transformation functions
- plots: Plotting functions that work with pandas DataFrames
- db: Database connection
- config: Configuration management
"""

try:
    from ._version import __version__
except ImportError:
    # Fallback for development installations
    try:
        from setuptools_scm import get_version
        __version__ = get_version(root='../..', relative_to=__file__)
    except ImportError:
        __version__ = "unknown"

__author__ = "Ethopy Analysis Contributors"


# Convenient imports for common data functions
from ethopy_analysis.data import (
    get_sessions,
    get_trials,
    get_trial_states,
    get_trial_experiment,
    get_trial_behavior,
    get_trial_stimulus,
    get_trial_licks,
    get_trial_proximities,
    get_performance,
    get_no_repeat_performance,
    session_summary,
)

# Database and configuration functions
from ethopy_analysis.db.schemas import (
    get_schema,
    get_all_schemas,
    test_connection,
)

from ethopy_analysis.config.settings import (
    load_config,
    get_config_summary,
)

# Also import modules for advanced users
from ethopy_analysis.data import loaders
from ethopy_analysis.plots import animal
from ethopy_analysis.db import schemas

__all__ = [
    # Data loading functions
    "get_sessions",
    "get_trials",
    "get_trial_states",
    "get_trial_experiment",
    "get_trial_behavior",
    "get_trial_stimulus",
    "get_trial_licks",
    "get_trial_proximities",
    # Analysis functions
    "get_performance",
    "session_summary",
    "get_no_repeat_performance",
    # Database schema access
    "get_schema",
    "get_all_schemas",
    # Utility functions
    "test_connection",
    "load_config",
    "get_config_summary",
    # Modules for advanced users
    "loaders",
    "animal",
    "schemas",
]
