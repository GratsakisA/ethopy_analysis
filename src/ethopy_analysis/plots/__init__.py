"""
Plotting utilities for Ethopy analysis.

This module provides visualization functions that work with pandas DataFrames,
making them independent of the data source (database, files, etc.).
"""

from .animal import (
    plot_session_performance,
    plot_performance_liquid,
    plot_session_date,
    plot_trial_per_session,
)
from .session import (
    plot_trials,
    difficultyPlot,
    LickPlot,
    plot_licks_state,
    valid_ready_state,
    plot_valid_proximity_state,
    plot_proximities_dur,
    calculate_proximity_duration,
    liquidsPlot,
    plot_trial_time,
    plot_states_in_time,
    plot_licks_time,
    plot_trial_events_raster,
)

from .utils import validate_dataframe, create_figure

__all__ = [
    # Animal-level plots
    "plot_session_performance",
    "plot_performance_liquid",
    "plot_session_date",
    "plot_trial_per_session",
    # Session-level plots
    "plot_trials",
    "difficultyPlot",
    "LickPlot",
    "plot_licks_state",
    "valid_ready_state",
    "plot_valid_proximity_state",
    "plot_proximities_dur",
    "calculate_proximity_duration",
    "plot_trial_time",
    "liquidsPlot",
    "plot_states_in_time",
    "plot_licks_time",
    "plot_trial_events_raster",
    # Utilities
    "validate_dataframe",
    "create_figure",
]
