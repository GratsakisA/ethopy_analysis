"""
Plotting utilities and common functions for Ethopy analysis.
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import logging
import zlib
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


def get_task_color(task_name: str):
    """Return the color for a task name.

    The color depends only on the name, so the same task gets the same color
    in every plot. Two different tasks can still share a color, since the
    palette has a fixed number of colors.

    Args:
        task_name: Name of the task.

    Returns:
        An RGBA tuple from the Pastel1 palette.
    """
    palette = plt.cm.Pastel1.colors
    return palette[zlib.crc32(task_name.encode("utf-8")) % len(palette)]



def validate_dataframe(
    df: pd.DataFrame, required_columns: List[str], plot_name: str = "plot"
) -> bool:
    """Validate that a DataFrame has required columns for plotting.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        plot_name: Name of the plot for error messages

    Returns:
        True if valid, False otherwise
    """
    if df.empty:
        logger.error(f"{plot_name}: DataFrame is empty")
        return False

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"{plot_name}: Missing required columns: {missing_columns}")
        logger.debug(f"Available columns: {list(df.columns)}")
        return False

    return True


def create_figure(
    figsize: Tuple[int, int] = (10, 6), title: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """Create a standardized figure and axes.

    Args:
        figsize: Figure size as (width, height)
        title: Optional title for the plot

    Returns:
        Tuple of (figure, axes)
    """
    fig, ax = plt.subplots(figsize=figsize)

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")

    return fig, ax


def add_trial_markers(
    ax: plt.Axes, trials_df: pd.DataFrame, marker_column: str = "outcome"
):
    """Add trial outcome markers to a plot.

    Args:
        ax: Matplotlib axes to add markers to
        trials_df: DataFrame with trial information
        marker_column: Column to use for marker styling
    """
    if marker_column not in trials_df.columns:
        return

    # Define marker styles for different outcomes
    marker_styles = {
        "reward": {"color": "green", "marker": "o", "alpha": 0.7},
        "punish": {"color": "red", "marker": "x", "alpha": 0.7},
        "abort": {"color": "grey", "marker": "s", "alpha": 0.7},
    }

    for outcome, style in marker_styles.items():
        outcome_trials = trials_df[trials_df[marker_column] == outcome]
        if not outcome_trials.empty and "trial_idx" in outcome_trials.columns:
            ax.scatter(
                outcome_trials["trial_idx"],
                [0] * len(outcome_trials),
                label=outcome,
                **style,
            )


def format_time_axis(ax: plt.Axes, time_column: str, df: pd.DataFrame):
    """Format time axis with appropriate labels and ticks.

    Args:
        ax: Matplotlib axes to format
        time_column: Name of the time column
        df: DataFrame containing the time data
    """
    if time_column not in df.columns:
        return

    time_data = df[time_column]

    # Determine appropriate time unit based on data range
    time_range = time_data.max() - time_data.min()

    if time_range < pd.Timedelta(minutes=1):
        # Seconds
        ax.set_xlabel("Time (seconds)")
    elif time_range < pd.Timedelta(hours=1):
        # Minutes
        ax.set_xlabel("Time (minutes)")
    elif time_range < pd.Timedelta(days=1):
        # Hours
        ax.set_xlabel("Time (hours)")
    else:
        # Days
        ax.set_xlabel("Time (days)")


def save_plot(fig: plt.Figure, filename: str, dpi: int = 300, format: str = "png"):
    """Save a plot with standardized settings.

    Args:
        fig: Figure to save
        filename: Output filename (without extension)
        dpi: Resolution for raster formats
        format: Output format ("png", "pdf", "svg")
    """
    output_path = f"{filename}.{format}"

    fig.savefig(
        output_path, dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none"
    )

    logger.info(f"Plot saved to: {output_path}")


def create_subplot_grid(
    nrows: int, ncols: int, figsize: Optional[Tuple[int, int]] = None
) -> Tuple[plt.Figure, np.ndarray]:
    """Create a grid of subplots with consistent styling.

    Args:
        nrows: Number of rows
        ncols: Number of columns
        figsize: Figure size, if None will be calculated automatically

    Returns:
        Tuple of (figure, axes_array)
    """
    if figsize is None:
        figsize = (4 * ncols, 3 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)

    # Ensure axes is always an array
    if nrows == 1 and ncols == 1:
        axes = np.array([axes])
    elif nrows == 1 or ncols == 1:
        axes = axes.reshape(-1)

    fig.tight_layout(pad=3.0)

    return fig, axes

