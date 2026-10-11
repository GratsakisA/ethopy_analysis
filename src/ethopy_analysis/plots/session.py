import bisect
import itertools
import logging
from datetime import timedelta
from typing import List, Optional, Tuple, Dict, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from ethopy_analysis.data.loaders import (
    get_trial_behavior,
    get_trial_experiment,
    get_trial_licks,
    get_trial_proximities,
    get_trial_states,
)
from ethopy_analysis.data.analysis import get_performance
from ethopy_analysis.data.utils import group_by_conditions
from ethopy_analysis.db.schemas import get_schema
from ethopy_analysis.plots.utils import save_plot

# Setup logger
logger = logging.getLogger(__name__)


def perf_difficulty(animal_id: int, session: int) -> Tuple[List, List]:
    """Calculate performance across different difficulty levels for an animal session.

    This function retrieves trial experiment conditions and states for a given animal
    and session, then calculates the performance for each unique difficulty level.

    Args:
        animal_id (int): Unique identifier for the animal.
        session (int): Session number or identifier.

    Returns:
        Tuple[List, List]: A tuple containing:
            - uniq_diffs (List): List of unique difficulty levels
            - diffs_perf (List[float]): List of performance values for each difficulty

    Example:
        >>> difficulties, performances = perf_difficulty(123, 1)
        >>> print(f"Difficulty levels: {difficulties}")
        >>> print(f"Performances: {performances}")
    """
    logger.info(
        f"Calculating performance by difficulty for animal {animal_id}, session {session}"
    )

    trial_exp_conds_df = get_trial_experiment(animal_id, session)
    trial_states_df = get_trial_states(animal_id, session)

    trials_by_diff = group_by_conditions(trial_exp_conds_df, ["difficulty"])
    uniq_diffs = trials_by_diff["trial_indices"].index.to_list()

    diffs_perf = []
    for diff, trial_idxs in zip(uniq_diffs, trials_by_diff["trial_indices"]):
        perf = get_performance(animal_id, session, trials=trial_idxs)
        diffs_perf.append(float(perf))
        logger.debug(f"Difficulty {diff}: performance {perf:.2f}")
        print(f"difficulty {diff}: performance {perf:.2f}")

    logger.info(
        f"Completed performance calculation for {len(uniq_diffs)} difficulty levels"
    )
    return uniq_diffs, diffs_perf


def plot_trials(trial_df: pd.DataFrame, params: Dict[str, Any], **kwargs) -> None:
    """Plot trial data with difficulty levels and visual offset.

    Creates a scatter plot of trials showing difficulty levels with a visual offset
    to prevent overlapping points. The offset is calculated based on trial bins
    to create a staggered appearance.

    Args:
        trial_df (pd.DataFrame): DataFrame containing trial data with columns:
            - 'difficulty': Difficulty levels for each trial
            - 'trial_idx': Trial indices
        params (dict): Parameters dictionary containing:
            - 'trial_bins': Number of trial bins for offset calculation
            - 'range': Range multiplier for offset calculation
        **kwargs: Additional keyword arguments passed to plt.scatter

    Returns:
        None: Function creates a matplotlib scatter plot

    Example:
        >>> params = {'trial_bins': 10, 'range': 0.9}
        >>> plot_trials(trial_df, params, s=10, c='red')
    """
    logger.debug(f"Plotting {len(trial_df)} trials with difficulty offset")

    # find difficulties per trials
    difficulties = trial_df["difficulty"].values
    trial_idxs = trial_df["trial_idx"].values
    # define offset (if trial_bins=10 then for trials = [0, 1,..., 10]
    # first part of offset=[-5., -4.,....,  4., -5.]
    offset = (
        ((trial_idxs - 1) % params["trial_bins"] - params["trial_bins"] / 2)
        * params["range"]
        * 0.1
    )
    plt.scatter(trial_idxs, difficulties + offset, zorder=20, **kwargs)
    logger.debug(
        f"Plotted trials with offset range: {offset.min():.3f} to {offset.max():.3f}"
    )


def difficultyPlot(animal_id: int, session: int, save_path=None, params=None) -> None:
    """Create a comprehensive difficulty plot for an animal session.

    Generates a visualization showing trial outcomes (reward, punish, abort) across
    different difficulty levels over time. The plot includes color-coded markers
    for different response ports and trial states.

    Args:
        animal_id (int): Unique identifier for the animal.
        session (int): Session number or identifier.

    Returns:
        None: Function creates and displays a matplotlib plot

    Example:
        >>> difficultyPlot(123, 1)
    """
    logger.info(f"Creating difficulty plot for animal {animal_id}, session {session}")

    trial_exp_conds_df = get_trial_experiment(animal_id, session)
    trial_states_df = get_trial_states(animal_id, session)

    difficulties = trial_exp_conds_df["difficulty"].values
    min_difficulty = np.min(difficulties)

    trials_state_cond = pd.merge(
        trial_exp_conds_df.drop(["time"], axis=1), trial_states_df
    )

    correct_trials_df = trials_state_cond.loc[trials_state_cond["state"] == "Reward"]
    missed_trials_df = trials_state_cond.loc[trials_state_cond["state"] == "Abort"]
    incorrect_trials_df = trials_state_cond.loc[trials_state_cond["state"] == "Punish"]

    trials_beh = get_trial_behavior(animal_id, session).drop(["time"], axis=1)
    ports_selection_corr_df = pd.merge(trials_beh, correct_trials_df, how="inner")
    perf_difficulty(animal_id, session)

    default_params = {
        "probe_colors": {
            1: [1, 0, 0],
            2: [0.12156863, 0.46666667, 0.70588235],
            -1: [1, 0, 0],
        },  # colors for correct
        "trial_bins": 10,  # how many trials on y axis
        "range": 0.9,  # define offset range(diff is int so offset range(0,1))
        "xlim": (-2,),  # plot lims
        "ylim": (min_difficulty - 0.6,),
        "figsize": (12, 10),
        "marker_size": 10,
    }

    if params is None:
        params = default_params
    else:
        # Merge user params with defaults, user params take priority
        params = {**default_params, **params}

    # create an array with colors for every correct trial based on the selected port
    clr_index_corr = np.array(
        [
            params["probe_colors"][x]
            for x in ports_selection_corr_df.sort_values("trial_idx")[
                "response_port"
            ].values
        ]
    )

    plt.figure(figsize=params["figsize"], tight_layout=True)
    plot_trials(correct_trials_df, params, s=params['marker_size'], c=clr_index_corr, label="reward")
    plot_trials(incorrect_trials_df, params, s=params['marker_size'], label="punish",
                facecolor="none", edgecolor="black", marker="o", linewidth=0.5)
    plot_trials(missed_trials_df, params, s=params['marker_size']*0.2, c="black", label="abort")

    plt.ylabel("difficulty levels", fontsize=12)
    plt.xlabel("trials", fontsize=12)
    plt.title(
        f"Animal:{animal_id}, Session:{session} \n\
        Reward: {len(correct_trials_df)}, Punish: {len(incorrect_trials_df)}, Abort: {len(missed_trials_df)}"
    )
    plt.ylim(params["ylim"][0])
    plt.xlim(params["xlim"][0])
    plt.yticks(np.unique(difficulties), fontsize=10)
    plt.xticks(fontsize=10)
    plt.box(False)
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="punish",
            markerfacecolor="none",
            markeredgecolor="black",
            markersize=params['marker_size'],
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="reward (port 1)",
            markerfacecolor="tab:red",
            markersize=params['marker_size'],
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="reward (port 2)",
            markerfacecolor="tab:blue",
            markersize=params['marker_size'],
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="abort",
            markerfacecolor="black",
            markersize=params['marker_size']*0.5,
        ),
    ]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.04, 1), loc="upper left")

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def find_diff_trials(key_animal_session: Dict[str, Any], diff: int) -> Any:
    """Find trials with specific difficulty level for a given animal session.

    This function identifies trials that match a specific difficulty level
    for either MatchToSample or MatchPort experiment types.

    Args:
        key_animal_session (dict): Dictionary containing animal_id and session keys
        diff (int): Difficulty level to filter trials

    Returns:
        DataJoint query object: Trials matching the specified difficulty level

    Raises:
        ValueError: If experiment class is not MatchToSample or MatchPort

    Example:
        >>> key = {'animal_id': 123, 'session': 1}
        >>> trials = find_diff_trials(key, difficulty=2)
    """
    logger.debug(
        f"Finding trials with difficulty {diff} for session {key_animal_session}"
    )

    experiment = get_schema("experiment")
    exp_key = experiment.Trial & key_animal_session

    # define the type of experiment in order to call the according conditions
    mts_flag = np.unique(
        (experiment.Condition & exp_key).fetch("experiment_class")
    ) == ["MatchToSample"]
    mp_flag = np.unique((experiment.Condition & exp_key).fetch("experiment_class")) == [
        "MatchPort"
    ]
    if mts_flag:
        cond_class = experiment.Condition.MatchToSample()
        logger.debug("Using MatchToSample experiment class")
    elif mp_flag:
        cond_class = experiment.Condition.MatchPort()
        logger.debug("Using MatchPort experiment class")
    else:
        error_msg = "Check if the key_animal_session is correct and if Experiment Class is MatchToSample or MatchPort"
        logger.error(error_msg)
        print(error_msg)
        raise ValueError(error_msg)

    result = (exp_key * cond_class & f"difficulty={diff}").proj("difficulty")
    logger.debug(f"Found {len(result)} trials with difficulty {diff}")
    return result


def LickPlot(
    animal_id: int,
    session: int,
    conds_split: List[str] = ["response_port"],
    state_start: str = "PreTrial",
    stim_table: Optional[Any] = None,
    color_rew_pun: bool = False,
    difficulty: Optional[int] = None,
    period: Optional[str] = None,
    save_path=None,
    **kwargs,
) -> Tuple[Any, Any]:
    """Generate lick plots for animal behavior analysis.

    Creates subplot grids showing lick patterns across different conditions,
    with customizable filtering by difficulty, period, and response port.

    Args:
        animal_id (int): Unique identifier for the animal.
        session (int): Session number or identifier.
        conds_split (List[str], optional): Conditions to split data by.
            Defaults to ["response_port"].
        state_start (str, optional): Starting state for analysis.
            Defaults to "PreTrial".
        stim_table (DataJoint table, optional): Stimulus table to use.
            Defaults to None.
        color_rew_pun (bool, optional): Whether to color by reward/punishment.
            Defaults to False.
        difficulty (int, optional): Specific difficulty level to filter.
            Defaults to None.
        period (str, optional): Specific period to filter.
            Defaults to None.
        **kwargs: Additional parameters for plot customization.

    Returns:
        Tuple: (selected_trials, condition) data for further analysis

    Example:
        >>> data, cond = LickPlot(123, 1, difficulty=2, period="sample")
    """
    logger.info(f"Creating lick plot for animal {animal_id}, session {session}")
    logger.debug(f"Conditions split: {conds_split}, State start: {state_start}")

    experiment = get_schema("experiment")
    behavior = get_schema("behavior")
    stimulus = get_schema("stimulus")

    if stim_table is None:
        stim_table = stimulus.StimCondition()

    key_animal_session = {"animal_id": animal_id, "session": session}
    params = {
        "port_colors": ["tab:red", "tab:blue"],  # set function parameters with defaults
        "xlim": [-500, 10000],
        "figsize": (15, 15),
        "dotsize": 3,
        **kwargs,
    }

    conditions = (
        (
            (stimulus.StimCondition.Trial() & key_animal_session).proj(
                "stim_hash", stime="start_time"
            )
        )
        * stim_table
        * (
            (behavior.BehCondition.Trial() & key_animal_session).proj(btime="time")
            * behavior.MultiPort.Response()
        )
    )

    if difficulty is not None:
        conditions = conditions * find_diff_trials(key_animal_session, difficulty)

    all_stim_periods = np.unique(conditions.fetch("period"))
    if period is None and len(all_stim_periods) > 1:
        print(
            f"Stimulus are present in more than one period, select one from:{all_stim_periods}"
        )
        return None
    if period not in all_stim_periods and period is not None:
        print(
            f"Stimulus is not present at period {period}, select one from:{all_stim_periods}"
        )
    if period:
        conditions = conditions & f'period = "{period}"'

    conds_values = []

    for cond in conds_split:
        conds_values.append(conditions.fetch(cond, order_by=("trial_idx")))

    uniq_groups, groups_idx = np.unique(conds_values, axis=1, return_inverse=True)

    conditions_ = conditions.fetch(order_by="trial_idx")
    condition_groups = [conditions_[groups_idx == group] for group in set(groups_idx)]

    if len(condition_groups) == 0:
        print("Wrong Condtions or Stimulus table")

    for i in condition_groups:
        if len(i) == 0:
            print("Condition are 0")
    conds = condition_groups
    y_len_plot = -(-len(conds) // round(len(conds) ** 0.5))
    x_len_plot = round(len(conds) ** 0.5)
    if y_len_plot == 1:
        y_len_plot += 1
    fig, axs = plt.subplots(
        x_len_plot, y_len_plot, sharex=True, figsize=params["figsize"]
    )

    for idx, cond in enumerate(conds):  # iterate through conditions
        selected_trials = (
            behavior.Activity.Lick.proj(ltime="time")
            * (
                ((experiment.Trial & key_animal_session) - experiment.Trial.Aborted())
                & cond
            )
        ).proj(dtime="ltime - time")
        temp = behavior.Activity.Lick.proj(ltime="time") * (
            ((experiment.Trial & key_animal_session) - experiment.Trial.Aborted())
            & cond
        )
        state_trials = (
            experiment.Trial.StateOnset & f'state="{state_start}"' & key_animal_session
        ).proj(state_time="time")

        selected_trials = (temp * state_trials & "ltime>state_time").proj(
            dtime="ltime - state_time", state_temp="state"
        )

        trials, ports, times = selected_trials.fetch(
            "trial_idx", "port", "dtime", order_by="trial_idx"
        )

        if color_rew_pun:
            lick_state = (
                (
                    experiment.Trial.StateOnset
                    & key_animal_session
                    & ["state='Reward'", "state='Punish'"]
                ).proj(s_time="time")
                & cond
            ) * selected_trials

            ports = lick_state.fetch("state") == "Reward"
            params["port_colors"] = ["green", "red"]
            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="Reward",
                    markerfacecolor="tab:green",
                    markersize=8,
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="Punish",
                    markerfacecolor="tab:red",
                    markersize=8,
                ),
            ]
        else:
            legend_elements = [
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="lick port 1",
                    markerfacecolor="tab:red",
                    markersize=8,
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    label="lick port 2",
                    markerfacecolor="dodgerblue",
                    markersize=8,
                ),
            ]

        un_trials, idx_trials = np.unique(
            trials, return_inverse=True
        )  # get unique trials
        axs.item(idx).scatter(
            times,
            idx_trials,
            params["dotsize"],
            c=np.array(params["port_colors"])[ports - 1],
        )
        axs.item(idx).axvline(x=0, color="green", linestyle="-")

        conds_str = ""

        if len(un_trials) > 0:
            perf = len(
                (
                    experiment.Trial.StateOnset & key_animal_session & "state='Reward'"
                ).proj(s_time="time")
                & cond
            ) / len(un_trials)
            for j in range(uniq_groups.shape[0]):
                conds_str += f" {conds_split[j]}: {uniq_groups.T[idx][j]}"
            title = f"{conds_str},\n Performance:{perf:.2f}"
        else:
            title = ""
        axs.item(idx).set_title(title, fontsize=9)
        axs.item(idx).invert_yaxis()
        axs.item(idx).set_xlabel("time (ms)")
        axs.item(idx).set_ylabel("trial_id")
    plt.xlim(params["xlim"])
    fig.suptitle(key_animal_session)
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.04, 1), loc="upper left")

    if save_path:
        save_plot(fig, save_path)
    else:
        plt.show()

    return selected_trials, cond


def group_column_times(
    df: pd.DataFrame,
    start_times: np.ndarray,
    stop_times: np.ndarray,
    time_id: Optional[np.ndarray] = None,
    column: str = "port",
) -> pd.DataFrame:
    """Group events by time periods and specified column values.

    Processes time-series data by grouping events within specified time periods
    and counting occurrences by a specified column (e.g., port number).

    Args:
        df (pd.DataFrame): DataFrame containing time-series data with 'time' column
        start_times (array-like): Start times for each period to analyze
        stop_times (array-like): Stop times for each period to analyze
        time_id (array-like, optional): Custom IDs for each time period.
            Defaults to None (uses period index).
        column (str, optional): Column name to group by. Defaults to "port".

    Returns:
        pd.DataFrame: DataFrame with columns:
            - 'id': Period identifier
            - column: Values from the specified grouping column
            - 'event_count': Number of events in this period/column combination
            - 'timings': List of actual event times

    Example:
        >>> start_times = [0, 1000, 2000]
        >>> stop_times = [500, 1500, 2500]
        >>> result = group_column_times(lick_data, start_times, stop_times)
    """
    logger.debug(f"Grouping events by {column} across {len(start_times)} time periods")

    results = []

    # Process each time period
    for period_idx, (start_time, stop_time) in enumerate(zip(start_times, stop_times)):
        # Filter data for current time period
        period_data = df[(df["time"] >= start_time) & (df["time"] <= stop_time)]

        if len(period_data) == 0:
            logger.debug(
                f"No data found for period {period_idx} ({start_time}-{stop_time})"
            )
            continue

        # Group by column and calculate time for each column
        for id in period_data[column].unique():
            data = period_data[period_data[column] == id]
            times = sorted(data["time"].tolist())
            event_count = len(times)

            if time_id is not None:
                _id = time_id[period_idx]
            else:
                _id = period_idx

            results.append(
                {
                    "id": _id,
                    column: id,
                    "event_count": event_count,
                    "timings": times,
                }
            )

    logger.debug(f"Processed {len(results)} period/column combinations")

    if not results:
        # pd.DataFrame([]) has no columns at all, so a caller indexing e.g.
        # ["port"] gets a KeyError rather than an empty result. Return the
        # documented columns so "no events" behaves like an empty frame.
        return pd.DataFrame(columns=["id", column, "event_count", "timings"])

    return pd.DataFrame(results)


def select_trials(df: pd.DataFrame, state: str) -> pd.DataFrame:
    """Filter trials based on their state.

    Filters a DataFrame to include only trials that match a specific state.
    If an empty string is provided, returns all trials.

    Args:
        df (pd.DataFrame): DataFrame containing trial data with 'state' and 'trial_idx' columns
        state (str): State to filter by (e.g., 'Reward', 'Punish'). Empty string returns all trials.

    Returns:
        pd.DataFrame: Filtered DataFrame containing only trials with matching state

    Example:
        >>> reward_trials = select_trials(trials_df, 'Reward')
        >>> all_trials = select_trials(trials_df, '')
    """
    logger.debug(f"Filtering trials by state: '{state}'")

    # select trials that are Reward
    if state == "":
        logger.debug("Empty state filter - returning all trials")
        return df

    filter_trials = df.loc[df["state"] == state].trial_idx.values
    filtered_df = df[df["trial_idx"].isin(filter_trials)]
    logger.debug(f"Filtered to {len(filtered_df)} trials with state '{state}'")
    return filtered_df


def get_state_times(animal_id: int, session: int) -> pd.DataFrame:
    """Get state timing information for an animal session.

    Retrieves trial states and calculates start and stop times for each state
    by using the next state's start time as the current state's stop time.

    Args:
        animal_id (int): Unique identifier for the animal
        session (int): Session number or identifier

    Returns:
        pd.DataFrame: DataFrame with columns:
            - 'start_time': Start time of each state
            - 'stop_time': Stop time of each state (next state's start time)
            - Other columns from trial states data

    Example:
        >>> state_times = get_state_times(123, 1)
        >>> print(state_times[['state', 'start_time', 'stop_time']])
    """
    logger.debug(f"Getting state times for animal {animal_id}, session {session}")

    states = get_trial_states(animal_id, session)
    states["stop_time"] = states["time"].shift(-1).fillna(-1)
    result = states.rename(columns={"time": "start_time"})

    logger.debug(f"Retrieved {len(result)} state transitions")
    return result


def plot_licks_state(
    animal_id: int,
    session: int,
    check_state: str = "InterTrial",
    state_select: str = "Reward",
    save_path=None,
    **kwargs,
) -> None:
    """Analyze licking behavior at specific states for selected trial types.
    Creates a histogram showing lick counts per port during a specified state,
    filtered to include only trials of a specific outcome type.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        check_state: State to analyze licks during
        state_select: Trial type to include (e.g., "Reward", "Punish")
        **kwargs: Additional arguments passed to plt.hist()
    """
    # gets start_time and stop_time for each state
    states_df = get_state_times(animal_id, session)
    available_states = sorted(states_df["state"].unique())

    # select only trials that are reward
    select_trials_df = select_trials(states_df, state_select)
    if select_trials_df.empty:
        print(
            f"No trials with state '{state_select}' for animal {animal_id}, "
            f"session {session}. Available states: {available_states}"
        )
        return

    select_state_df = select_trials_df.loc[select_trials_df["state"] == check_state]
    if select_state_df.empty:
        print(
            f"No '{check_state}' state within '{state_select}' trials for animal "
            f"{animal_id}, session {session}. Available states: {available_states}"
        )
        return

    licks_df = get_trial_licks(animal_id, session)
    licks_port = group_column_times(
        licks_df,
        select_state_df["start_time"].values,
        select_state_df["stop_time"].values,
        time_id=select_state_df["trial_idx"].values,
        column="port",
    )
    if licks_port.empty:
        print(
            f"No licks recorded during '{check_state}' in '{state_select}' trials "
            f"for animal {animal_id}, session {session}."
        )
        return

    uniq_ports = licks_port["port"].unique()

    # Calculate global min and max across all ports to create uniform bins
    all_event_counts = licks_port["event_count"].values
    global_min = all_event_counts.min()
    global_max = all_event_counts.max()

    # Create uniform bins based on global range
    # You can adjust the number of bins as needed
    num_bins = kwargs.pop("bins", 20)  # Default to 20 bins, but allow override
    bins = np.linspace(global_min, global_max, num_bins + 1)

    for port in uniq_ports:
        licks_per_port = licks_port.loc[licks_port["port"] == port]
        print(f"port: {port}")
        print(f" mean licks: {licks_per_port.event_count.mean()}")
        print(f" trials count: {len(licks_per_port)}")

        # Use the same bins for all ports
        plt.hist(
            licks_per_port["event_count"],
            bins=bins,
            alpha=0.5,
            label=f"port {port}",
            **kwargs,
        )

    plt.title(f"licks at State:{check_state} \nfor {state_select} trials")
    plt.legend()
    plt.xlabel("licks")
    plt.ylabel("#")

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def find_ready_times_state(
    states_check_tr: pd.DataFrame, proximities: pd.DataFrame
) -> List[float]:
    """Find ready times based on proximity sensor data during specific states.

    Args:
        states_check_tr: DataFrame with state information including start_time and stop_time
        proximities: DataFrame with proximity sensor data

    Returns:
        List of ready time durations
    """
    prox_trials = proximities.loc[
        np.logical_and(
            proximities.time > states_check_tr.start_time.values[0],
            proximities.time < states_check_tr.stop_time.values[0],
        )
    ]
    if len(prox_trials) > 0:
        prox_trials_first_index = (
            prox_trials.index[0]
            if prox_trials.in_position.iloc[0] == 1
            else prox_trials.index[0] - 1
        )
        prox_trials_last_index = (
            prox_trials.index[-1] + 2
            if prox_trials.in_position.iloc[-1] == 1
            else prox_trials.index[-1] + 1
        )

        trial_proximities = proximities.iloc[
            prox_trials_first_index:prox_trials_last_index
        ]

        position = np.where((np.diff(trial_proximities["in_position"]) == -1))[0]

        time = trial_proximities.time.values
        return time[position + 1] - time[position]
    else:
        proximities_before_start = proximities.loc[
            proximities.time < states_check_tr.start_time.values[0]
        ]
        proximities_after_stop = proximities.loc[
            proximities.time > states_check_tr.stop_time.values[0]
        ]
        if len(proximities_before_start) > 0 and len(proximities_after_stop):
            before_pos = proximities_before_start.iloc[-1].in_position
            after_pos = proximities_after_stop.iloc[0].in_position

            if before_pos == 1 and after_pos == 0:
                return [
                    proximities_after_stop.iloc[0].time
                    - proximities_before_start.iloc[-1].time
                ]
    return [0]


def valid_ready_state(
    animal_id: int, session: int, state: str = "PreTrial"
) -> pd.Series:
    """Calculate valid ready times for a specific state.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        state: State to analyze ready times for

    Returns:
        Series with ready times grouped by trial
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")
    key_animal_session = {"animal_id": animal_id, "session": session}

    states = (
        (experiment.Trial.StateOnset & key_animal_session)
        .fetch(format="frame")
        .reset_index()
    )
    states["stop_time"] = states["time"].shift(-1).fillna(-1)

    proximities = (
        (behavior.Activity.Proximity & key_animal_session & "port=3")
        .fetch(format="frame")
        .reset_index()
    )

    states_check = states.loc[states["state"] == state]
    states_check = states_check.rename(columns={"time": "start_time"})

    ready_times_state = states_check.groupby("trial_idx").apply(
        find_ready_times_state, proximities
    )

    return ready_times_state


def plot_valid_proximity_state(
    animal_id: int, session: int, state: str = "Trial", save_path=None
) -> None:
    """Plot histogram of valid proximity durations for a specific state.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        state: State to analyze proximity for
    """
    ready_times_state = valid_ready_state(animal_id, session, state="Trial")
    plt.figure(figsize=(10, 5))
    plt.hist(list(itertools.chain(*ready_times_state)), bins=100)
    plt.title(
        f"Animal id: {animal_id}, session: {session}\nAll valid Ready time(on-off proximity)\n at state: {state}"
    )
    plt.xlabel("time(ms)")
    plt.ylabel("#")

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def calculate_proximity_duration(
    animal_id: int, session: int, ports: Optional[List] = None
) -> pd.DataFrame:
    """Calculate duration of proximity sensor activations.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        ports: Optional list of ports to analyze

    Returns:
        DataFrame with proximity duration data
    """
    proximity_key = get_trial_proximities(animal_id, session, format="dj")
    # the position where diff equals -1 which means on - off position (1-0)
    position = np.where((np.diff(proximity_key.fetch("in_position")) == -1))[0]
    time = proximity_key.fetch("time")
    # find the difference only for on-off pairs
    d = time[position + 1] - time[position]
    proximity_df = proximity_key.fetch(format="frame").reset_index()

    # Create a proper copy and make all modifications
    selected_prox = proximity_df.iloc[position].copy()
    selected_prox = selected_prox.rename(
        columns={"time": "time_on"}
    )  # rename returns a new df
    selected_prox["time_off"] = proximity_df.iloc[position + 1]["time"].values
    selected_prox["duration"] = d
    return selected_prox


def plot_proximities_dur(
    animal_id: int, session: int, ports: List[int] = [], save_path=None, **kwargs
) -> None:
    """Plot histogram of proximity durations.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        ports: List of port IDs to plot. If empty, plots all ports
        **kwargs: Additional arguments passed to plt.hist()
    """
    proximity_key = get_trial_proximities(animal_id, session, ports, format="dj")
    ports = np.unique(proximity_key.fetch("port"))

    prox_duration = calculate_proximity_duration(animal_id, session)

    plt.hist(prox_duration["duration"].values, **kwargs)
    plt.title(f"Animal id {animal_id}, session: {session}\nPorts = {ports}")
    plt.xlabel("Proximity duration\n(on_time - off_time)")
    plt.ylabel("#")

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def plot_trial_time(
    animal_id: int,
    session: int,
    trials: List[int],
    display_tables: bool = True,
    port: int = 3,
    save_path=None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Any]:
    """Plot timeline of trial events including states, licks, and proximity.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        trials: List of trial indices to plot
        display_tables: Whether to print data tables
        port: Port number for proximity data

    Returns:
        Tuple of (trial_states, trial_licks, trial_prox) DataFrames
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")
    key_animal_session = {"animal_id": animal_id, "session": session}
    trials_idxs = [f"trial_idx='{trial}'" for trial in trials]
    trial_states = (
        (experiment.Trial.StateOnset & key_animal_session & trials_idxs)
        .fetch(format="frame")
        .reset_index()
    )
    trial_licks = (
        (behavior.Activity.Lick & key_animal_session & trials_idxs)
        .fetch(format="frame")
        .reset_index()
    )
    trial_prox = (
        behavior.Activity.Proximity & key_animal_session & trials_idxs & f"port={port}"
    )
    trial_prox_on = (trial_prox & "in_position=1").fetch(format="frame").reset_index()
    trial_prox_off = (trial_prox & "in_position=0").fetch(format="frame").reset_index()
    trial_states["time_spend"] = -trial_states["time"].diff(-1).fillna(0)

    if display_tables:
        print("states of Trial")
        print(trial_states)
        print("Licks of Trial")
        print(trial_licks)
        print("Proximities of Trial")
        print(trial_prox.fetch(format="frame").reset_index())

    color = plt.cm.Paired(np.linspace(0, 1, len(trial_states)))
    fig = plt.figure(figsize=(20, 5))
    fig.add_subplot(111)
    for i, st in enumerate(trial_states["state"]):
        # single line
        plt.vlines(
            x=trial_states.iloc[i].time, ymin=0, ymax=1, colors=color[i], label=st
        )
    plt.scatter(trial_licks["time"], np.ones(len(trial_licks)))
    plt.scatter(
        trial_prox_on["time"],
        np.zeros(len(trial_prox_on)) + 0.5,
        color="green",
        label=" prox on",
    )
    plt.scatter(
        trial_prox_off["time"],
        np.zeros(len(trial_prox_off)) + 0.5,
        color="red",
        label="prox off",
    )
    tmsts_ = []
    tmsts_ += list(trial_states.time.values)
    plt.xticks(tmsts_, rotation=90)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    plt.xlabel("time(ms)")
    plt.yticks([0.5, 1], ["proximity", "licks"])
    plt.title(f"Animal id:{animal_id}, session: {session} \ntrials: {trials}")

    if save_path:
        save_plot(plt.gcf(), save_path)

    return trial_states, trial_licks, trial_prox


def liquidsPlot(animal_id: int, days: int = 15, save_path=None) -> None:
    """plot liquid delivered per day

    Args:
        animal_id (int):
        days (int, optional): how many days before to plot. Defaults to 15.
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")
    reward_animal = behavior.Rewards & {"animal_id": animal_id}
    liquids = (reward_animal * experiment.Session()).fetch(
        "session_tmst", "reward_amount"
    )

    # convert timestamps to dates
    tstmps = liquids[0].tolist()
    dates = [d.date() for d in tstmps]

    # find first index for plot, i.e. for last 15 days
    last_date = dates[-1]
    starting_date = last_date - timedelta(days=days)  # keep only last 15 days
    starting_idx = bisect.bisect_right(dates, starting_date)

    # keep only 15 last days
    # construct the list of tuples (date,reward)
    dates_ = dates[starting_idx:]  # lick dates, for last 15 days
    liqs_ = liquids[1][starting_idx:].tolist()  # lick rewards for last 15 days
    tuples_list = list(zip(dates_, liqs_))

    # construct tuples (unique_date, total_reward_per_day)
    dates_liqs_unique = [
        (dt, sum(v for d, v in grp))
        for dt, grp in itertools.groupby(tuples_list, key=lambda x: x[0])
    ]
    print(
        f"############### last date: {dates_liqs_unique[-1][0]}, amount: {dates_liqs_unique[-1][1]} ###############"
    )

    dates_to_plot = [tpls[0] for tpls in dates_liqs_unique]
    liqs_to_plot = [tpls[1] for tpls in dates_liqs_unique]

    # plot
    plt.figure(figsize=(14, 4))
    plt.plot(dates_to_plot, liqs_to_plot, linestyle="--", marker="o")
    plt.ylabel("liquid (μL)")
    plt.xlabel("date")
    plt.xticks(rotation=45)
    plt.grid()

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def roll_time(
    timestamps: np.ndarray, binaries: np.ndarray, seconds_offset: int = 60
) -> pd.Series:
    """Group binary events into time bins.

    Args:
        timestamps: Array of timestamps
        binaries: Array of binary values
        seconds_offset: Bin size in seconds

    Returns:
        Series with summed binary values per time bin
    """
    # Convert the timestamps to a DatetimeIndex
    timestamps_dt = pd.to_datetime(timestamps, unit="ms")
    timestamps_dt_index = pd.DatetimeIndex(timestamps_dt)
    # Create a range of DatetimeIndex objects for every 10 minutes
    start = timestamps_dt[0].floor(f"{seconds_offset}s")
    end = timestamps_dt[-1].ceil(f"{seconds_offset}s")
    time_range = pd.date_range(start, end, freq=f"{seconds_offset}s")
    bins = pd.cut(timestamps_dt_index, time_range)
    # Group the binary values by the bins and sum them - ADD observed=False here
    grouped = pd.Series(binaries, index=bins).groupby(level=0, observed=False).sum()
    # Fill in any missing intervals with zero values
    return grouped.reindex(time_range, fill_value=0)


def plot_states_in_time(
    animal_id: int, session: int, seconds: int = 30, save_path=None
) -> None:
    """Plot trial states over time.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        seconds: Time bin size in seconds
    """
    stateonset = get_trial_states(animal_id, session)
    # Select rows where state is 'Reward' or 'Punish'
    selected_rows = stateonset[stateonset["state"].isin(["Reward", "Punish", "Abort"])]
    timestamps = selected_rows["time"].values

    plt.figure(figsize=(21, 4))
    states_ = ["Abort", "Punish", "Reward"]
    color = ["grey", "red", "green"]

    for i, state in enumerate(states_):
        binaries = (selected_rows["state"] == state).astype(int).values
        result = roll_time(timestamps, binaries, seconds_offset=seconds)
        plt.plot(result.values, label=state, color=color[i])

    plt.xlabel(f"time\n(unit:{seconds} sec)")
    plt.ylabel("#")
    plt.title("Number of Trials through time")
    plt.legend()
    plt.grid()

    if save_path:
        save_plot(plt.gcf(), save_path)


def plot_licks_time(
    animal_id: int, session: int, bins: int = 50, save_path=None
) -> None:
    """Plot lick counts over time by port.

    Args:
        animal_id: Unique identifier for the animal
        session: Session number or identifier
        bins: Number of time bins
    """
    trial_licks = get_trial_licks(animal_id, session)
    plt.figure(figsize=(15, 6))

    # Convert time from milliseconds to minutes
    time_minutes = trial_licks["time"] / (1000 * 60)

    # Create time bins in minutes
    time_bins = np.linspace(time_minutes.min(), time_minutes.max(), bins)
    bin_centers = (time_bins[:-1] + time_bins[1:]) / 2

    # Get unique ports
    unique_ports = trial_licks["port"].unique()
    colors = plt.cm.Set1(np.linspace(0, 1, len(unique_ports)))

    # Calculate bar width
    bar_width = (bin_centers[1] - bin_centers[0]) / (len(unique_ports) + 1)

    # Plot bars for each port
    for port_idx, port in enumerate(unique_ports):
        port_data = trial_licks[trial_licks["port"] == port]
        port_time_minutes = port_data["time"] / (1000 * 60)

        binned_counts = []
        for i in range(len(time_bins) - 1):
            mask = (port_time_minutes >= time_bins[i]) & (
                port_time_minutes < time_bins[i + 1]
            )
            binned_counts.append(mask.sum())

        # Offset bars for each port
        x_offset = bin_centers + (port_idx - len(unique_ports) / 2 + 0.5) * bar_width

        plt.bar(
            x_offset,
            binned_counts,
            width=bar_width,
            label=f"Port {port}",
            color=colors[port_idx],
            alpha=0.7,
        )

    plt.xlabel("Time (minutes)")
    plt.ylabel("Lick Count")
    plt.title("Lick Count by Time and Port")
    plt.legend()
    plt.grid(True, alpha=0.3)

    if save_path:
        save_plot(plt.gcf(), save_path)
    else:
        plt.show()


def plot_trial_events_raster(
    session_df: pd.DataFrame,
    animal_id: Optional[int] = None,
    session: Optional[int] = None,
    align_to: str = "Trial",
    sort_by: Optional[str] = None,
    xlim: Tuple[int, int] = (-100, 2000),
    figsize: Tuple[int, int] = (20, 12),
    state_color: Optional[Dict[str, str]] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot per-trial ON-OFF proximity, lick, and state data as a raster.

    Designed to accept the output of
    :func:`~ethopy_analysis.data.loaders.get_session_proximity_data` directly,
    but the caller can pre-filter or modify ``session_df`` before passing it
    in (e.g. select only rewarded trials, change column order).

    Each trial is drawn as one horizontal row. The vertical axis lists trial
    indices; the horizontal axis is time relative to the chosen alignment
    event.

    Args:
        session_df (pd.DataFrame): One row per trial, as produced by
            :func:`~ethopy_analysis.data.loaders.get_session_proximity_data`.
            Required columns: ``trial_idx``, ``state_times``,
            ``all_on_off_pairs``, ``all_lick_times``, ``main_on_time``,
            ``main_off_time``, ``response_lick_time``, ``outcome_time``.
        animal_id (Optional[int], optional): Used for the plot title only.
            Defaults to ``None``.
        session (Optional[int], optional): Used for the plot title only.
            Defaults to ``None``.
        align_to (str, optional): Column or state name to use as ``t=0`` for
            each trial. Accepted values:

            - ``"main_on_time"`` — last ON event during the main state
            - ``"main_off_time"`` — last OFF event during the main state
            - ``"response_lick_time"`` — first response lick
            - any key present in the ``state_times`` dict (e.g. ``"Trial"``,
              ``"Reward"``, ``"PreTrial"``)

            Defaults to ``"main_on_time"``.
        sort_by (Optional[str], optional): Column in *session_df* to sort
            trials by (ascending). ``None`` preserves ``trial_idx`` order.
            Common choices: ``"main_on_off_dur"``, ``"reaction_time"``.
            Defaults to ``None``.
        xlim (Tuple[int, int], optional): X-axis limits in ms. Defaults to
            ``(-100, 2000)``.
        figsize (Tuple[int, int], optional): Figure size as ``(width, height)``
            in inches. Defaults to ``(20, 12)``.
        state_color (Optional[Dict[str, str]], optional): Mapping of state
            name to colour string. If ``None``, a default palette is used.
            Defaults to ``None``.

    Returns:
        Tuple[plt.Figure, plt.Axes]: The matplotlib figure and axes objects.

    Note:
        Trials whose alignment reference is ``NaN`` (e.g. no lick detected for
        ``align_to="response_lick_time"``) are silently skipped. The number of
        skipped trials is printed as a warning.
    """
    if state_color is None:
        state_color = {
            "PreTrial": "purple",
            "Trial": "blue",
            "Abort": "black",
            "InterTrial": "orange",
            "Punish": "darkred",
            "Reward": "darkgreen",
            "Offtime": "grey",
            "Hydrate": "yellow",
        }

    df = session_df.copy()

    if align_to in df.columns.tolist():
        df["ref_time"] = df[align_to]
    else:
        df["ref_time"] = df["state_times"].apply(lambda d: d.get(align_to))

    skipped = df[df["ref_time"].isna()]["trial_idx"].tolist()
    df = df.dropna(subset=["ref_time"]).reset_index(drop=True)

    if sort_by is not None and sort_by in df.columns:
        df = df.sort_values(sort_by, na_position="last").reset_index(drop=True)

    trial_list = df["trial_idx"].tolist()
    pos_map = {trl: i for i, trl in enumerate(trial_list)}

    fig, ax = plt.subplots(figsize=figsize)
    seen_labels: set = set()

    def _scatter(x, y, color, label, marker=".", s=20):
        if not len(x):
            return
        lbl = label if label not in seen_labels else "_nolegend_"
        seen_labels.add(label)
        ax.scatter(x, y, s=s, alpha=0.7, color=color, marker=marker, label=lbl, zorder=3)

    def _span(x0, x1, ypos, color, label, alpha=0.25):
        lbl = label if label not in seen_labels else "_nolegend_"
        seen_labels.add(label)
        ax.fill_betweenx(
            [ypos - 0.45, ypos + 0.45], x0, x1,
            alpha=alpha, color=color, zorder=2, label=lbl,
        )

    for _, row in df.iterrows():
        trl = row["trial_idx"]
        ref = row["ref_time"]
        ypos = pos_map[trl]

        on_t, off_t = [], []
        for pair in row["all_on_off_pairs"]:
            t_on = pair["time_on"] - ref
            t_off = pair["time_off"] - ref
            _span(t_on, t_off, ypos, color="grey", label="In sensor")
            on_t.append(t_on)
            off_t.append(t_off)

        _scatter(np.array(on_t), np.full(len(on_t), ypos), "green", "ON")
        _scatter(np.array(off_t), np.full(len(off_t), ypos), "red", "OFF")

        lick_t = np.array(row["all_lick_times"]) - ref
        _scatter(lick_t, np.full(len(lick_t), ypos), "green", "Lick", marker="x")

        if row["response_lick_time"] is not None:
            ml = row["response_lick_time"] - ref
            lbl = "Response lick" if "Response lick" not in seen_labels else "_nolegend_"
            seen_labels.add("Response lick")
            ax.scatter([ml], [ypos], s=50, color="green", marker="*",
                       label=lbl, zorder=5, alpha=0.9)

        for st, st_abs in row["state_times"].items():
            if st not in state_color:
                continue
            st_t = st_abs - ref
            lbl = st if st not in seen_labels else "_nolegend_"
            seen_labels.add(st)
            ax.scatter(st_t, ypos, s=7, alpha=1, color=state_color[st],
                       marker=">", label=lbl, zorder=3)

            if st in ("Reward", "Punish", "Abort") and off_t:
                valid = [x for x in off_t if x <= st_t]
                if valid:
                    _span(valid[-1], st_t, ypos, color=state_color[st], label=st + " period")

    ax.axvline(0, color="black", linewidth=1, linestyle=":", alpha=0.6, zorder=4)

    ax.set_yticks(range(len(trial_list)))
    ax.set_yticklabels(trial_list, fontsize=8)
    ax.set_ylim(-1, len(trial_list))
    ax.set_xlim(*xlim)
    ax.set_xticks(np.arange(xlim[0], xlim[1] + 50, 50))
    ax.grid(zorder=1)

    sort_label = f"  |  sorted by: {sort_by}" if sort_by else ""
    id_label = f"Animal {animal_id}  —  Session {session}  —  " if animal_id else ""
    fig.suptitle("Centerport On-Off & State timing", fontsize=20, weight="bold")
    ax.set_title(f"{id_label}aligned to: {align_to}{sort_label}", fontsize=13)
    ax.set_xlabel("Time (ms)", fontsize=20, weight="bold")
    ax.set_ylabel("Trial Index", fontsize=20, weight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 0.9), fontsize=17)

    if skipped:
        print(f"Warning: {len(skipped)} trial(s) skipped (no '{align_to}'): {skipped}")

    return fig, ax
