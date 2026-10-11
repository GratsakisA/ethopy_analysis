"""
Data access and analysis package for Ethopy experiments.

This package provides convenient access to data loading, analysis, and utility functions
for behavioral experiments. Import the main functions you need directly from this package.
"""

# Main data loading functions
from .loaders import (
    get_sessions,
    get_trials,
    get_trial_states,
    get_trial_experiment,
    get_trial_behavior,
    get_trial_stimulus,
    get_trial_licks,
    get_trial_proximities,
    get_session_classes,
    get_session_duration,
    get_session_task,
    get_session_version,
    get_state_windows,
    get_licks_per_state,
    get_first_lick_after_state,
    get_first_port_exit_after_state,
    get_licks_during_proximity,
    get_proximity_on_off_pairs,
    get_trial_proximity_timings,
    get_session_proximity_data,
)

# Analysis functions
from .analysis import (
    get_performance,
    session_summary,
    trials_per_session,
    get_port_exit_to_lick_latency,
)

# Utility functions
from .utils import (
    find_combination,
    get_setup,
    check_hashable_columns,
    group_trials,
    group_by_conditions,
    group_trial_hash,
    convert_ms_to_time,
    find_consecutive_runs,
    add_column_by_key,
)

__all__ = [
    # Data loaders
    "get_sessions",
    "get_trials",
    "get_trial_states",
    "get_trial_experiment",
    "get_trial_behavior",
    "get_trial_stimulus",
    "get_trial_licks",
    "get_trial_proximities",
    "get_session_classes",
    "get_session_duration",
    "get_session_task",
    "get_session_version",
    "get_state_windows",
    "get_licks_per_state",
    "get_first_lick_after_state",
    "get_first_port_exit_after_state",
    "get_licks_during_proximity",
    "get_proximity_on_off_pairs",
    "get_trial_proximity_timings",
    "get_session_proximity_data",
    # Analysis functions
    "get_performance",
    "session_summary",
    "trials_per_session",
    "get_port_exit_to_lick_latency",
    # Utility functions
    "find_combination",
    "get_setup",
    "check_hashable_columns",
    "group_trials",
    "group_by_conditions",
    "group_trial_hash",
    "convert_ms_to_time",
    "find_consecutive_runs",
    "add_column_by_key",
]
