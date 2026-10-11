from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ethopy_analysis.data.loaders import get_sessions
from ethopy_analysis.data.analysis import get_performance, trials_per_session
from ethopy_analysis.db.schemas import get_schema
from ethopy_analysis.plots.utils import save_plot


def plot_session_date(
    animal_id: int, min_trials: int = 0, save_path: Optional[str] = None
) -> Dict[date, List[int]]:
    """Plot sessions per date to visualize training schedule.

    Creates a bar chart showing the number of sessions conducted on each date
    for a specific animal. This helps visualize training consistency and patterns.

    Args:
        animal_id: The animal identifier to analyze.
        min_trials: Minimum number of trials required per session to include in analysis.
            Sessions with fewer trials will be excluded. Defaults to 0.
        save_path: Path to save the plot image. If None, plot is not saved.

    Returns:
        Dictionary mapping each date to a list of session IDs conducted on that date.

    """
    experiment = get_schema("experiment")
    animal_sessions_tc = get_sessions(
        animal_id, min_trials=min_trials, format="dj"
    ).proj(setup_="setup")
    tmst, session = (
        animal_sessions_tc
        * (experiment.Session & {"animal_id": animal_id} & "session>0")
    ).fetch("session_tmst", "session")
    session_same_date = defaultdict(list)
    # tmst[0].date()
    for i, _ in enumerate(tmst):
        if tmst[i].date() not in session_same_date:
            session_same_date[tmst[i].date()] = [session[i]]
        else:
            session_same_date[tmst[i].date()].append(session[i])
    dates_sess, sess_c = [], []
    for date_sess in session_same_date:
        dates_sess.append(date_sess)
        sess_c.append(len(session_same_date[date_sess]))

    plt.figure(figsize=(20, 7))
    plt.bar(dates_sess, sess_c)
    plt.xticks(dates_sess, rotation=90)
    plt.xlabel("dates")
    plt.ylabel("# sessions")
    plt.title(f"Animal id : {animal_id}")
    plt.grid()

    if save_path:
        save_plot(plt.gcf(), save_path)

    return session_same_date


def plot_performance_liquid(
    animal_id: int,
    animal_sessions: pd.DataFrame,
    xaxis: str = "session",
    save_path: Optional[str] = None,
) -> None:
    """Plot performance vs liquid reward consumption over sessions.

    Creates a dual-axis plot showing both behavioral performance and liquid reward
    consumption across sessions. This helps identify relationships between motivation
    (liquid consumption) and task performance.

    Args:
        animal_id: The animal identifier to analyze.
        animal_sessions: DataFrame containing session information with columns:
            - 'session': Session identifiers
            - 'session_tmst': Session timestamps (required if xaxis='date')
        xaxis: X-axis format, either 'session' for session IDs or 'date' for timestamps.
            Defaults to 'session'.
        save_path: Path to save the plot image. If None, plot is not saved.

    """
    behavior = get_schema("behavior")
    sessions = animal_sessions["session"].values
    if len(sessions) == 0:
        print("No session available")
    perfs = [get_performance(animal_id, sess) for sess in sessions]
    liquid = []
    for sess in sessions:
        reward_animal = behavior.Rewards & {"animal_id": animal_id, "session": sess}
        reward_animal_df = reward_animal.fetch(format="frame").reset_index()
        liquid.append(
            np.sum(
                reward_animal_df.drop_duplicates(subset=["trial_idx"])["reward_amount"]
            )
        )

    assert len(liquid) == len(perfs)

    # Style of plots
    mpl.rcParams["axes.spines.right"] = True
    fig, ax1 = plt.subplots(figsize=(20, 7))

    color = "tab:red"
    ax1.set_xlabel("session id")
    ax1.set_ylabel("performace", color=color)
    ax1.plot(
        range(1, len(sessions) + 1, 1), perfs, color=color, linestyle="--", marker="o"
    )
    ax1.tick_params(axis="y", labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = "tab:blue"
    ax2.set_ylabel(
        "liquid (μL)", color=color
    )  # we already handled the x-label with ax1
    ax2.plot(
        range(1, len(sessions) + 1, 1), liquid, color=color, linestyle="--", marker="o"
    )
    ax2.tick_params(axis="y", labelcolor=color)

    if xaxis == "session":
        ax1.set_xticks(range(1, len(sessions) + 1, 1), sessions, rotation=90)
    elif xaxis == "date":
        ax1.set_xticks(
            range(1, len(sessions) + 1, 1), animal_sessions["session_tmst"], rotation=90
        )

    plt.grid()

    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    if save_path:
        save_plot(fig, save_path)


def find_uniq_pos(arr: List) -> Tuple[List, List[int]]:
    """Find unique values and their starting positions in a list.

    Helper function that identifies unique consecutive values in a list
    and returns both the unique values and their starting positions.

    Args:
        arr: Input list to analyze for unique consecutive values.

    Returns:
        A tuple containing:
        - List of unique consecutive values
        - List of starting positions for each unique value

    """
    uniq_starts = []
    uniq_value = []
    for i in range(len(arr)):
        if len(uniq_value) == 0:
            uniq_value.append(arr[i])
            uniq_starts.append(i)
        else:
            if arr[i] != arr[uniq_starts[-1]]:
                uniq_value.append(arr[i])
                uniq_starts.append(i)

    return uniq_value, uniq_starts


def plot_session_performance(
    animal_id: int,
    sessions: List[int],
    perf_func: callable,
    save_path: Optional[str] = None,
) -> List[float]:
    """Plot session performance over time with protocol visualization.

    Creates a line plot showing performance across sessions, with colored background
    regions indicating different experimental protocols. This helps visualize how
    performance changes over time and across different task conditions.

    Args:
        animal_id: The animal identifier to analyze.
        sessions: List of session IDs to include in the analysis.
        perf_func: Function that calculates performance for a given animal_id and session.
            Should have signature: perf_func(animal_id: int, session: int) -> float
        save_path: Path to save the plot image. If None, plot is not saved.

    Returns:
        List of performance values for each session, in the same order as input sessions.

    """
    experiment = get_schema("experiment")
    protocols, color_layer = [], [0]
    task_session_dj = (
        experiment.Session.Task()
        & [f"session={session}" for session in sessions]
        & f"animal_id={animal_id}"
    )
    prtcls = task_session_dj.fetch("task_name")
    prtcls = [prtcl.split("/")[-1] for prtcl in prtcls]
    sessions = task_session_dj.fetch("session")
    if len(sessions) == 0:
        print("No session available")
    perfs = [perf_func(animal_id, sess) for sess in sessions]

    protocols, color_layer = find_uniq_pos(prtcls)
    color_layer.append(sessions[-1])
    plt.figure(figsize=(20, 5))
    plt.plot(range(1, len(perfs) + 1, 1), perfs, marker=11)
    plt.xticks(range(1, len(perfs) + 1, 1), sessions, rotation=45)
    color = plt.cm.Pastel1(np.linspace(0, 1, len(color_layer)))
    for i in range(0, len(color_layer) - 1):
        plt.axvspan(
            color_layer[i] + 0.5,
            color_layer[i + 1] + 0.5,
            facecolor=color[i],
            label=protocols[i],
        )
    plt.xlim(0, len(perfs) + 1)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    plt.title(f"Animal_id: {animal_id}")
    plt.xlabel("Session _ids")
    plt.ylabel("Performace")
    plt.grid()

    if save_path:
        save_plot(plt.gcf(), save_path)

    return perfs


def plot_trial_per_session(
    animal_id: int, min_trials: int = 2, save_path: Optional[str] = None
) -> None:
    """Plot the distribution of trials per session.

    Creates a bar chart showing the number of trials completed in each session
    for a specific animal. This helps assess session length consistency and
    identify potential issues with session termination.

    Args:
        animal_id: The animal identifier to analyze.
        min_trials: Minimum number of trials required per session to include in analysis.
            Sessions with fewer trials will be excluded. Defaults to 2.
        save_path: Path to save the plot image. If None, plot is not saved.

    """
    animal_sessions_tc = trials_per_session(animal_id, min_trials)
    animal_id = animal_sessions_tc["animal_id"].iloc[0]
    plt.figure(figsize=(15, 5))
    sess = animal_sessions_tc["session"].values
    trials_c = animal_sessions_tc["trials_count"].values
    plt.bar(list(range(len(sess))), trials_c)
    plt.xticks(list(range(len(sess))), sess)
    plt.title(f"Animal id: {animal_id}")
    plt.ylabel("# trials")
    plt.xlabel("session id")
    plt.grid()

    if save_path:
        save_plot(plt.gcf(), save_path)


def plot_animal_weight(
    weight_df: pd.DataFrame,
    animal_id: Optional[int] = None,
    count_from: int = 5,
    thresholds: Tuple[float, ...] = (0.7, 0.8, 0.9),
    save_path: Optional[str] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot the weight of an animal over time with water deprivation limits.

    Creates a line plot of every weight measurement, with a horizontal line for
    each fraction of the reference weight, so weight loss can be tracked against
    the humane endpoints.

    Args:
        weight_df: DataFrame of weight measurements with columns:
            - 'timestamp': Time of the measurement
            - 'weight': Weight in grams
            - 'animal_id': Animal identifier (used if animal_id is None)
        animal_id: The animal identifier, used for the title. Taken from the
            DataFrame if None.
        count_from: Index of the measurement used as the reference weight,
            counted from the first one. Adjust it to the start of water
            deprivation. Defaults to 5.
        thresholds: Fractions of the reference weight to draw as limit lines.
            Defaults to (0.7, 0.8, 0.9).
        save_path: Path to save the plot image. If None, plot is not saved.

    Returns:
        Tuple of the figure and axes of the plot.

    Raises:
        ValueError: If the DataFrame is empty or has fewer than
            count_from + 1 measurements.
    """
    if weight_df.empty:
        raise ValueError("No weight measurements to plot")

    if len(weight_df) <= count_from:
        raise ValueError(
            f"{len(weight_df)} weight measurements, "
            f"count_from={count_from} needs at least {count_from + 1}"
        )

    if animal_id is None:
        animal_id = weight_df["animal_id"].iloc[0]

    weight_df = weight_df.sort_values("timestamp")
    reference_weight = weight_df["weight"].iloc[count_from]

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(
        weight_df["timestamp"],
        weight_df["weight"],
        linestyle="--",
        marker="o",
        label="weight",
    )

    colors = ["red", "pink", "green", "orange", "purple"]
    for i, threshold in enumerate(thresholds):
        ax.axhline(
            threshold * reference_weight,
            linestyle="--",
            color=colors[i % len(colors)],
            label=f"-{round((1 - threshold) * 100)}%",
        )

    ax.set_ylabel("Mouse weight (gr)")
    ax.set_xlabel("Time")
    ax.set_title(f"Animal id: {animal_id}")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%y"))
    ax.tick_params(axis="x", labelrotation=45)
    ax.grid()
    ax.legend()
    fig.tight_layout()

    if save_path:
        save_plot(fig, save_path)

    return fig, ax
