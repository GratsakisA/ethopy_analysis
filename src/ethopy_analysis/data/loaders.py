"""
Main data loading functions for Ethopy analysis.

This module provides user-friendly functions to load behavioral data
and return it as pandas DataFrames or DataJoint expressions ready for analysis and visualization.
"""

from typing import List, Optional, Union, Any, Dict
import pandas as pd
import numpy as np
import os
from ethopy_analysis.db.schemas import get_schema
from ethopy_analysis.data.utils import combine_children_tables


def get_sessions(
    animal_id,
    from_date: str = "",
    to_date: str = "",
    format: str = "df",
    min_trials: Optional[int] = None,
):
    """
    Get sessions for an animal within a specified date range.

    Args:
        animal_id (int): The animal identifier
        from_date (str, optional): Start date in format 'YYYY-MM-DD'. Defaults to ''.
        to_date (str, optional): End date in format 'YYYY-MM-DD'. Defaults to ''.
        format(str, optional): if format equals 'dj' return datajoint expression.
        min_trials(int, optional): minimum number of trials per session.

    Returns:
        Union[pd.DataFrame, Any]: Session DataFrame if format="df",
                                 Session expression if format="dj"
    """
    from .analysis import trials_per_session

    experiment = get_schema("experiment")

    animal_session_tmt = experiment.Session & {"animal_id": animal_id}
    if from_date != "":
        animal_session_tmt = animal_session_tmt & f'session_tmst > "{from_date}"'

    if to_date != "":
        animal_session_tmt = animal_session_tmt & f'session_tmst < "{to_date}"'

    sessions_dj = animal_session_tmt - experiment.Session.Excluded
    if min_trials:
        trials_session = trials_per_session(animal_id, min_trials=2, format="dj")
        sessions_dj = trials_session * sessions_dj

    if format == "dj":
        return sessions_dj
    return sessions_dj.fetch(format="frame").reset_index()


def get_trials(
    animal_id: int, session: int, format: str = "df", remove_abort: bool = False
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve trial data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".
        remove_abort (bool): remove abort trials

    Returns:
        Union[pd.DataFrame, Any]: Trial DataFrame if format="df",
                                 DataJoint expression if format="dj"
    """
    experiment = get_schema("experiment")
    trials_dj = experiment.Trial & {"animal_id": animal_id, "session": session}
    if remove_abort:
        trials_dj = trials_dj - experiment.Trial.Aborted()
    if format == "dj":
        return trials_dj
    return trials_dj.fetch(format="frame").reset_index()


def get_trial_states(
    animal_id: int, session: int, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve trial state onset data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Trial states DataFrame if format="df",
                                 DataJoint expression if format="dj"
    """
    experiment = get_schema("experiment")
    key_animal_session = {"animal_id": animal_id, "session": session}

    trial_states_dj = experiment.Trial.StateOnset & key_animal_session

    if format == "dj":
        return trial_states_dj

    trial_states_df = trial_states_dj.fetch(format="frame").reset_index()
    return trial_states_df


def get_trial_experiment(
    animal_id: int, session: int, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve trial experiment condition data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Trial experiment conditions DataFrame if format="df",
                                 DataJoint expression if format="dj"

    Note:
        This function combines trial data with experiment conditions based on the
        experiment_type from the session classes.
    """
    experiment = get_schema("experiment")
    key_animal_session = {"animal_id": animal_id, "session": session}
    combined_df = get_session_classes(animal_id, session)
    exp_conds = getattr(experiment.Condition, combined_df["experiment_type"].values[0])
    conditions_dj = (experiment.Trial & key_animal_session) * experiment.Condition
    trial_exp_conditions_dj = conditions_dj * exp_conds

    if format == "dj":
        return trial_exp_conditions_dj

    trial_exp_conditions_df = trial_exp_conditions_dj.fetch(
        format="frame"
    ).reset_index()
    return trial_exp_conditions_df


def get_trial_behavior(
    animal_id: int, session: int, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve trial behavior condition data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Trial behavior conditions DataFrame if format="df",
                                 DataJoint expression if format="dj"

    Note:
        This function combines trial data with behavior conditions, handling cases
        where multiple behavior child tables need to be combined.
    """
    behavior = get_schema("behavior")
    key_animal_session = {"animal_id": animal_id, "session": session}
    combined_df = get_session_classes(animal_id, session)
    beh_conds = getattr(behavior, combined_df["behavior_class"].values[0])
    children = beh_conds.children(as_objects=True)

    if len(children) > 1:
        comb_tables = combine_children_tables(children)
    elif len(children) == 1:
        comb_tables = children[0]
    else:
        comb_tables = beh_conds

    trial_beh_conditions_dj = (
        behavior.BehCondition.Trial() & key_animal_session
    ) * comb_tables

    if format == "dj":
        return trial_beh_conditions_dj

    trial_beh_conditions_df = trial_beh_conditions_dj.fetch(
        format="frame"
    ).reset_index()
    return trial_beh_conditions_df


def get_trial_stimulus(
    animal_id: int, session: int, stim_class: Optional[str] = None, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve trial stimulus condition data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        stim_class (Optional[str], optional): Specific stimulus class to use.
                                            If None, uses the stimulus class from session data.
                                            Defaults to None.
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Trial behavior conditions DataFrame if format="df",
                                 DataJoint expression if format="dj"
    Raises:
        Exception: If an explicitly requested stimulus class table is not found in
            the stimulus schema

    Note:
        This function combines trial data with stimulus conditions and all related
        child tables that contain data for the session.

        Sessions run with EthoPy's base ``Stimulus`` class have no dedicated
        condition table - their conditions live directly on ``StimCondition``.
        Those sessions fall back to ``StimCondition`` instead of raising.
    """
    stimulus = get_schema("stimulus")
    combined_df = get_session_classes(animal_id, session)
    key_animal_session = {"animal_id": animal_id, "session": session}

    is_base_stimulus = False
    if stim_class is None:
        stim_class_name = combined_df["stimulus_class"].values[0]
        if "Panda" in stim_class_name:
            stim_class_name = "Panda"
        # The base Stimulus class stores no extra conditions, so there is no
        # `Stimulus` table - StimCondition alone carries the trial conditions.
        if stim_class_name == "Stimulus":
            stim_conds = stimulus.StimCondition
            is_base_stimulus = True
        else:
            try:
                stim_conds = getattr(stimulus, stim_class_name)
            except AttributeError as e:
                raise Exception(
                    f"Cannot find {stim_class_name} table in stimulus schema"
                ) from e
    else:
        try:
            stim_conds = getattr(stimulus, stim_class)
        except AttributeError as e:
            raise Exception(f"Cannot find {stim_class} table in stimulus schema") from e

    # StimCondition's children are every stimulus-type table in the schema, so
    # expanding them would join unrelated stimuli onto the base-class result.
    children = [] if is_base_stimulus else stim_conds.children(as_objects=True)
    base_dj = (stimulus.StimCondition.Trial & key_animal_session) * stim_conds
    all_stims = base_dj

    for child in children:
        comb_stims = base_dj * child
        if len(comb_stims) > 0:
            all_stims = all_stims * child

    trial_stim_conditions_dj = all_stims
    if format == "dj":
        return trial_stim_conditions_dj
    trial_stim_conditions_df = trial_stim_conditions_dj.fetch(
        format="frame"
    ).reset_index()
    return trial_stim_conditions_df


def get_trial_licks(
    animal_id: int, session: int, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve all licks of a session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Trial behavior conditions DataFrame if format="df",
                                 DataJoint expression if format="dj"
    """
    behavior = get_schema("behavior")
    key = {"animal_id": animal_id, "session": session}
    lick_dj = behavior.Activity.Lick & key
    if format == "dj":
        return lick_dj
    return lick_dj.fetch(format="frame").reset_index()


def get_trial_proximities(
    animal_id, session, ports: Optional[List] = None, format="df"
):
    """
    Retrieve proximity sensor data for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        ports (Optional[List]): List of port numbers to filter by
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Proximity data DataFrame if format="df",
                                 DataJoint expression if format="dj"
    """
    behavior = get_schema("behavior")
    if ports:
        proximity_dj = (
            behavior.Activity.Proximity
            & {"animal_id": animal_id, "session": session}
            & [f"port={p}" for p in ports]
        )
    else:
        proximity_dj = behavior.Activity.Proximity & {
            "animal_id": animal_id,
            "session": session,
        }
    if format == "dj":
        return proximity_dj
    return proximity_dj.fetch(format="frame").reset_index()


def get_session_classes(animal_id: int, session: int) -> pd.DataFrame:
    """
    Retrieve session information and experimental classes for a specific animal session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number

    Returns:
        pd.DataFrame: Combined DataFrame containing session information and unique
                     combinations of stimulus_class, behavior_class, and experiment_class

    Raises:
        Exception: If no session found for the given animal_id and session
    """
    experiment = get_schema("experiment")
    key_animal_session = {"animal_id": animal_id, "session": session}
    session_info_df = (
        (experiment.Session & key_animal_session).fetch(format="frame").reset_index()
    )

    conditions_dj = (experiment.Trial & key_animal_session) * experiment.Condition
    conditions_df = conditions_dj.fetch(format="frame").reset_index()

    # Get unique combinations
    unique_combinations = conditions_df[
        ["stimulus_class", "behavior_class", "experiment_class"]
    ].drop_duplicates()

    # Combine session_info_df and unique_combinations side by side
    combined_df = pd.concat(
        [session_info_df, unique_combinations.reset_index(drop=True)], axis=1
    )
    return combined_df


def get_session_duration(animal_id: int, session: int) -> Optional[str]:
    """
    Calculate the duration of a session based on the last state onset time.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number

    Returns:
        Optional[str]: Formatted duration string (e.g., "1.2 hours (4320.0 seconds)")
                      or None if no state times found
    """
    from .utils import convert_ms_to_time

    experiment = get_schema("experiment")
    state_times = (
        experiment.Trial.StateOnset & {"animal_id": animal_id, "session": session}
    ).fetch("time")
    if len(state_times) < 1:
        return None
    return convert_ms_to_time(state_times[-1])["formatted"]


def get_session_task(animal_id: int, session: int, save_file: bool = True) -> str:
    """
    Retrieve and optionally save the task configuration file for a specific session.

    Args:
        animal_id (int): Animal identifier
        session (int): Session identifier
        save_file (bool, optional): Whether to save the file to disk. Defaults to True.

    Returns:
        str: The task filename.

    Note:
        If save_file is True, the file is saved with a modified name including
        animal_id and session for uniqueness.

        Code version information is not part of this table. Use
        :func:`get_session_version` for the git hash or package version that
        produced the session.
    """
    key_animal_session = {"animal_id": animal_id, "session": session}
    experiment = get_schema("experiment")
    file, task_name = (experiment.Session.Task & key_animal_session).fetch1(
        "task_file", "task_name"
    )
    filename = task_name.split("/")[-1]

    if save_file:
        filename = f"{filename[:-3]}_animal_id_{animal_id}_session_{session}.py"
        print(f"Save task at path: {os.getcwd()}/{filename}")
        file.tofile(filename)
    return filename


def get_session_version(
    animal_id: int, session: int, format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Retrieve the code version records for a session.

    EthoPy writes one row per project directory to ``experiment.Session.Version``
    - typically the EthoPy package and the plugins directory - recording the git
    hash or the installed package version that produced the session.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: Version records DataFrame if format="df",
                                 DataJoint expression if format="dj". The
                                 DataFrame is empty when the session has no
                                 version records.

    Note:
        Columns are ``project_path``, ``source_type`` ("git", "pypi" or "None"),
        ``version`` (git hash or package version), ``repository_url`` and
        ``is_dirty`` (uncommitted changes present at run time).

        Not every session has version records: sessions predating the table, or
        runs where EthoPy could not resolve a project, have none.
    """
    key = {"animal_id": animal_id, "session": session}
    experiment = get_schema("experiment")
    version_dj = experiment.Session.Version & key
    if format == "dj":
        return version_dj
    return version_dj.fetch(format="frame").reset_index()


def get_state_windows(
    animal_id: int,
    session: int,
    states: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Get start and end times for each state occurrence per trial.

    End time is inferred as the onset of the next state within the same trial.
    The last state of each trial has ``NaN`` as its end time.

    This is the foundation for any analysis that needs to bound events to a
    specific state (e.g. licks during Reward, port entries during Trial).

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        states (Optional[List[str]], optional): If provided, only rows for the
            listed states are returned. Defaults to None (all states).

    Returns:
        pd.DataFrame: DataFrame with columns ``animal_id``, ``session``,
            ``trial_idx``, ``state``, ``state_start``, ``state_end``.
    """
    experiment = get_schema("experiment")
    key = {"animal_id": animal_id, "session": session}

    all_onsets = (
        (experiment.Trial.StateOnset & key)
        .fetch(format="frame")
        .sort_values(["trial_idx", "time"])
        .reset_index()
    )

    all_onsets["state_start"] = all_onsets["time"]
    all_onsets["state_end"] = all_onsets["time"].shift(-1)
    all_onsets = all_onsets.drop("time", axis=1)

    if states is not None:
        all_onsets = all_onsets[all_onsets["state"].isin(states)]

    return all_onsets.reset_index(drop=True)


def get_licks_per_state(
    animal_id: int,
    session: int,
    states: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Get all licks with their corresponding state window.

    Uses :func:`pandas.merge_asof` to assign each lick to the state active at
    that moment, then filters to only licks that fall before the state ends.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        states (Optional[List[str]], optional): If provided, only licks that
            fall within the listed states are returned. Defaults to None
            (all states).

    Returns:
        pd.DataFrame: DataFrame with columns ``trial_idx``, ``lick_time``,
            ``port``, ``animal_id``, ``session``, ``state``, ``state_start``,
            ``state_end``.
    """
    behavior = get_schema("behavior")
    key = {"animal_id": animal_id, "session": session}

    state_windows = get_state_windows(animal_id, session)

    licks = (
        (behavior.Activity.Lick & key)
        .fetch(format="frame")
        .reset_index()[["trial_idx", "time", "port"]]
        .rename(columns={"time": "lick_time"})
        .sort_values("lick_time")
    )

    # Range join: assign each lick to the state active at that moment.
    # merge_asof matches each lick to the last state_start <= lick_time.
    merged = pd.merge_asof(
        licks,
        state_windows.sort_values("state_start"),
        left_on="lick_time",
        right_on="state_start",
        by="trial_idx",
        direction="backward",
    )

    # Drop licks that fall after the state ended (last state has NaN end → keep).
    merged = merged[
        merged["state_end"].isna() | (merged["lick_time"] < merged["state_end"])
    ]

    if states is not None:
        merged = merged[merged["state"].isin(states)]

    return merged.reset_index(drop=True)


def get_first_lick_after_state(
    animal_id: int,
    session: int,
    state: str = "Response",
    sub_state: str = "",
) -> pd.DataFrame:
    """Get the first lick per trial after a specific state onset.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        state (str, optional): State after whose onset to measure the first
            lick. Defaults to ``"Response"``.
        sub_state (str, optional): If non-empty, restrict results to trials
            that also contain this state. Defaults to ``""`` (no restriction).

    Returns:
        pd.DataFrame: One row per trial. Columns include ``animal_id``,
            ``session``, ``trial_idx``, ``port``, ``ltime`` (lick time),
            ``time`` (state onset time), ``state``, and ``time_to_lick``
            (``ltime - time`` in ms).
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")

    key_animal_session = {"animal_id": animal_id, "session": session}

    state_onsets = experiment.Trial.StateOnset & key_animal_session & f"state='{state}'"
    lick_time_dj = (behavior.Activity.Lick.proj(ltime="time") * state_onsets).proj(
        time_to_lick="ltime - time"
    )
    f_lick = (
        (lick_time_dj & "ltime>time")
        .fetch(format="frame")
        .reset_index()
        .sort_values("ltime")
        .drop_duplicates(subset=["trial_idx"])
    )

    if sub_state:
        sub_select_trial = (
            (experiment.Trial.StateOnset & key_animal_session & f"state='{sub_state}'")
            .fetch(format="frame")
            .reset_index()
        )
        mask = np.isin(f_lick["trial_idx"], sub_select_trial["trial_idx"])
        f_lick = f_lick.loc[mask]

    return f_lick.reset_index(drop=True)


def get_first_port_exit_after_state(
    animal_id: int,
    session: int,
    state: str = "Trial",
    port: Optional[int] = 3,
) -> pd.DataFrame:
    """Get the first time the animal leaves a proximity sensor after a state onset.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        state (str, optional): State after whose onset to look for the first
            off-position event. Defaults to ``"Trial"``.
        port (Optional[int], optional): Proximity port to monitor. If ``None``,
            all ports are considered. Defaults to ``3`` (center port).

    Returns:
        pd.DataFrame: One row per trial with columns ``trial_idx``, ``state``,
            ``state_onset``, ``off_position`` (time of first off-position
            event in ms), and ``port``.

    Raises:
        RuntimeError: If no state onset or proximity data is found for the
            given animal and session.
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")

    key_session = {"animal_id": animal_id, "session": session}

    state_onsets = pd.DataFrame(
        (experiment.Trial.StateOnset & key_session & f'state="{state}"').fetch(
            "trial_idx", "time", "state", as_dict=True
        )
    ).rename(columns={"time": "state_onset"})

    if state_onsets.empty:
        raise RuntimeError(
            f'No state="{state}" found for animal {animal_id}, session {session}'
        )

    prox_query = behavior.Activity.Proximity & key_session
    if port is not None:
        prox_query = prox_query & f"port={port}"

    proximity = pd.DataFrame(
        prox_query.fetch("trial_idx", "time", "in_position", "port", as_dict=True)
    )

    if proximity.empty:
        raise RuntimeError(
            f"No proximity data found for animal {animal_id}, session {session}"
        )

    proximity = proximity.merge(state_onsets, on="trial_idx", how="inner")

    off_position = proximity[
        (proximity["time"] >= proximity["state_onset"]) & (proximity["in_position"] == 0)
    ].copy()

    if off_position.empty:
        print(f"Warning: No off-position events found after state '{state}'")
        return pd.DataFrame(columns=["trial_idx", "state", "state_onset", "off_position", "port"])

    first_off = (
        off_position.sort_values("time").groupby("trial_idx", as_index=False).first()
    )
    first_off = first_off.rename(columns={"time": "off_position"})

    return first_off[["trial_idx", "state", "state_onset", "off_position", "port"]]


def get_licks_during_proximity(
    animal_id: int,
    session: int,
    port: Optional[int] = None,
) -> pd.DataFrame:
    """Report licks that occurred while the animal was inside a proximity sensor.

    This is primarily a quality-control function: while ``in_position=1`` the
    animal is at the sensor, so licks on a *different* port are unexpected.
    Windows where ``has_lick=True`` indicate a potential anomaly.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        port (Optional[int], optional): Filter to a specific sensor port. If
            ``None``, all ports are checked. Defaults to ``None``.

    Returns:
        pd.DataFrame: One row per ON-OFF proximity window with columns
            ``trial_idx``, ``port``, ``on_time``, ``off_time``,
            ``duration_ms``, ``n_licks``, ``lick_times``, ``lick_ports``,
            ``has_lick``. Only rows where ``has_lick=True`` indicate a problem.
    """
    behavior = get_schema("behavior")
    key = {"animal_id": animal_id, "session": session}

    prox_query = behavior.Activity.Proximity & key
    if port is not None:
        prox_query = prox_query & f"port={port}"

    proximity = pd.DataFrame(
        prox_query.fetch("trial_idx", "time", "in_position", "port", as_dict=True)
    ).sort_values(["port", "time"]).reset_index(drop=True)

    licks = pd.DataFrame(
        (behavior.Activity.Lick & key).fetch("trial_idx", "time", "port", as_dict=True)
    ).rename(columns={"time": "lick_time", "port": "lick_port"})

    # Build ON-OFF windows per port: for each ON, the next event is the OFF.
    proximity["next_in_position"] = proximity.groupby("port")["in_position"].shift(-1)
    proximity["off_time"] = proximity.groupby("port")["time"].shift(-1)

    on_off = (
        proximity[
            (proximity["in_position"] == 1) & (proximity["next_in_position"] == 0)
        ]
        .rename(columns={"time": "on_time"})[["trial_idx", "port", "on_time", "off_time"]]
        .copy()
        .reset_index(drop=True)
    )

    on_off["duration_ms"] = on_off["off_time"] - on_off["on_time"]

    # Check licks per window via numpy broadcasting.
    lick_times = licks["lick_time"].values
    lick_ports = licks["lick_port"].values
    on_times = on_off["on_time"].values
    off_times = on_off["off_time"].values

    in_window = (lick_times[None, :] > on_times[:, None]) & (
        lick_times[None, :] < off_times[:, None]
    )

    on_off["n_licks"] = in_window.sum(axis=1)
    on_off["has_lick"] = on_off["n_licks"] > 0
    on_off["lick_times"] = [lick_times[mask].tolist() for mask in in_window]
    on_off["lick_ports"] = [lick_ports[mask].tolist() for mask in in_window]

    return on_off


def _state_at(trial_states: pd.DataFrame, t: float) -> str:
    """Return the name of the state active at time *t* within a single trial.

    Args:
        trial_states (pd.DataFrame): State rows for one trial. Must have
            columns ``state``, ``start_time``, and ``stop_time``.
        t (float): Time point in milliseconds.

    Returns:
        str: Name of the active state, or ``"unknown"`` if none matches.
    """
    active = trial_states[
        (trial_states["start_time"] <= t)
        & (trial_states["stop_time"].isna() | (trial_states["stop_time"] > t))
    ]
    return active["state"].iloc[0] if not active.empty else "unknown"


def get_proximity_on_off_pairs(
    trial_states: pd.DataFrame,
    proximities: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """Find all ON-OFF proximity pairs across the full trial window.

    Spans from the first state onset to the last state end of the trial.
    Carry-over is handled: if the trial starts with the animal already inside
    the sensor (no ON event within the trial), the preceding ON event is
    included.

    Args:
        trial_states (pd.DataFrame): All state rows for **one** trial. Must
            have columns ``start_time`` and ``stop_time``.
        proximities (pd.DataFrame): Full session proximity data for one port.
            Must have columns ``time`` and ``in_position``.

    Returns:
        List[Dict[str, Any]]: Each element is a dict with keys ``time_on``,
            ``time_off``, ``duration`` (all in ms, as float), and ``state``
            (name of the state active at ``time_on``).
    """
    trial_start = trial_states["start_time"].min()
    trial_end = trial_states["stop_time"].max()  # NaN for the last trial

    if pd.isna(trial_end):
        prox_in = proximities.loc[proximities["time"] > trial_start]
    else:
        prox_in = proximities.loc[
            (proximities["time"] > trial_start) & (proximities["time"] < trial_end)
        ]

    if len(prox_in) == 0:
        # Carry-over: check if a pair spans the entire trial window.
        prox_before = proximities.loc[proximities["time"] < trial_start]
        prox_after = proximities.loc[
            proximities["time"] > (trial_end if not pd.isna(trial_end) else trial_start)
        ]
        if (
            len(prox_before) > 0
            and len(prox_after) > 0
            and prox_before.iloc[-1]["in_position"] == 1
            and prox_after.iloc[0]["in_position"] == 0
        ):
            t_on = float(prox_before.iloc[-1]["time"])
            t_off = float(prox_after.iloc[0]["time"])
            return [
                {
                    "time_on": t_on,
                    "time_off": t_off,
                    "duration": t_off - t_on,
                    "state": _state_at(trial_states, t_on),
                }
            ]
        return []

    # Expand slice: step back if first event is OFF (carry-over ON before trial).
    first_idx = (
        prox_in.index[0]
        if prox_in["in_position"].iloc[0] == 1
        else prox_in.index[0] - 1
    )
    last_idx = prox_in.index[-1] + 1  # exclusive slice end

    trial_prox = proximities.iloc[first_idx:last_idx]
    positions = np.where(np.diff(trial_prox["in_position"].values) == -1)[0]
    times = trial_prox["time"].values

    return [
        {
            "time_on": float(times[i]),
            "time_off": float(times[i + 1]),
            "duration": float(times[i + 1] - times[i]),
            "state": _state_at(trial_states, times[i]),
        }
        for i in positions
    ]


def get_trial_proximity_timings(
    animal_id: int,
    session: int,
    port: int = 3,
) -> pd.DataFrame:
    """Get all valid ON-OFF proximity timings for each trial across the full session.

    Captures every ON-OFF pair across all states (PreTrial → InterTrial),
    including carry-overs where the animal enters the sensor before a state
    boundary.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        port (int, optional): Proximity port to analyse. Defaults to ``3``
            (center port).

    Returns:
        pd.DataFrame: One row per ON-OFF pair with columns ``trial_idx``,
            ``time_on``, ``time_off``, ``duration`` (ms), and ``state``
            (state active at ``time_on``).
    """
    experiment = get_schema("experiment")
    behavior = get_schema("behavior")
    key = {"animal_id": animal_id, "session": session}

    states = (
        (experiment.Trial.StateOnset & key).fetch(format="frame").reset_index()
    )
    states["stop_time"] = states.groupby("trial_idx")["time"].shift(-1)
    states = states.rename(columns={"time": "start_time"})

    proximities = (
        (behavior.Activity.Proximity & key & f"port={port}")
        .fetch(format="frame")
        .reset_index()
    )

    rows = []
    for trial_idx, grp in states.groupby("trial_idx"):
        pairs = get_proximity_on_off_pairs(grp, proximities)
        for p in pairs:
            rows.append({"trial_idx": trial_idx, **p})

    if not rows:
        return pd.DataFrame(columns=["trial_idx", "time_on", "time_off", "duration", "state"])
    return pd.DataFrame(rows)


def get_session_proximity_data(
    animal_id: int,
    session: int,
    trials: Optional[List[int]] = None,
    main_state: str = "Trial",
    port: int = 3,
) -> pd.DataFrame:
    """Build a per-trial DataFrame with proximity and lick data for a session.

    For each trial the output provides scalar columns for the key events
    (suitable for alignment and sorting) and list columns for full plotting
    context.

    **Scalar columns** (easy to use for alignment/sorting):

    - ``main_on_time``: ``time_on`` of the first ON-OFF pair whose OFF falls
      within ``main_state``.
    - ``main_off_time``: ``time_off`` of that pair.
    - ``main_on_off_dur``: duration of that pair (ms).
    - ``response_lick_time``: first lick after ``main_off_time``.
    - ``reaction_time``: ``response_lick_time - main_off_time`` (ms).
    - ``outcome``: outcome state name (``"Reward"``, ``"Punish"``,
      ``"Abort"``).
    - ``outcome_time``: onset time of the outcome state (ms).
    - ``state_times``: dict mapping state name → onset time for all states in
      the trial.

    **List columns** (for full plotting context):

    - ``all_on_off_pairs``: list of dicts
      ``[{time_on, time_off, duration, state}, ...]``.
    - ``all_lick_times``: list of lick times within the trial window.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        trials (Optional[List[int]], optional): Subset of trial indices to
            process. ``None`` includes all trials. Defaults to ``None``.
        main_state (str, optional): State used to identify the main ON-OFF
            pair per trial (the first pair whose ``time_off`` falls within this
            state). Defaults to ``"Trial"``.
        port (int, optional): Proximity port to use. Defaults to ``3``
            (center port).

    Returns:
        pd.DataFrame: One row per trial.
    """
    key = {"animal_id": animal_id, "session": session}
    exp = get_schema("experiment")
    beh = get_schema("behavior")

    state_df = (exp.Trial.StateOnset & key).fetch(format="frame").reset_index()
    state_df["stop_time"] = state_df.groupby("trial_idx")["time"].shift(-1)
    state_df = state_df.rename(columns={"time": "start_time"})

    proximities = (
        (beh.Activity.Proximity & key & f"port={port}")
        .fetch(format="frame")
        .reset_index()
    )

    licks_all = pd.DataFrame(
        (beh.Activity.Lick & key).fetch("trial_idx", "time", as_dict=True)
    ).sort_values("time").reset_index(drop=True)

    trial_list = (
        sorted(trials)
        if trials is not None
        else sorted(state_df["trial_idx"].unique())
    )

    rows = []
    for trl in trial_list:
        trl_states = state_df[state_df["trial_idx"] == trl]
        if trl_states.empty:
            continue

        state_times = dict(
            zip(trl_states["state"], trl_states["start_time"].astype(float))
        )
        trial_start = trl_states["start_time"].min()
        trial_end = trl_states["stop_time"].max()  # NaN for last trial

        all_pairs = get_proximity_on_off_pairs(trl_states, proximities)

        # Main ON-OFF: first pair whose OFF falls within main_state window.
        main_state_row = trl_states[trl_states["state"] == main_state]
        main_on_time = main_off_time = main_on_off_dur = None
        if not main_state_row.empty and all_pairs:
            ms_start = float(main_state_row["start_time"].iloc[0])
            ms_end_raw = main_state_row["stop_time"].iloc[0]
            ms_end = float(ms_end_raw) if not pd.isna(ms_end_raw) else np.inf
            main_pairs = [
                p for p in all_pairs if ms_start <= p["time_off"] <= ms_end
            ]
            if main_pairs:
                mp = main_pairs[0]
                main_on_time = mp["time_on"]
                main_off_time = mp["time_off"]
                main_on_off_dur = mp["duration"]

        outcome_row = trl_states[trl_states["state"].isin(["Reward", "Punish", "Abort"])]
        outcome = outcome_row["state"].iloc[0] if not outcome_row.empty else None
        outcome_time = (
            float(outcome_row["start_time"].iloc[0]) if not outcome_row.empty else None
        )

        if pd.isna(trial_end):
            trl_licks = licks_all.loc[
                licks_all["time"] >= trial_start, "time"
            ].tolist()
        else:
            trl_licks = licks_all.loc[
                (licks_all["time"] >= trial_start) & (licks_all["time"] <= trial_end),
                "time",
            ].tolist()

        response_lick_time = None
        if main_off_time is not None:
            after = [t for t in trl_licks if t > main_off_time]
            response_lick_time = float(after[0]) if after else None

        reaction_time = (
            response_lick_time - main_off_time
            if response_lick_time is not None and main_off_time is not None
            else None
        )

        rows.append(
            {
                "trial_idx": trl,
                "outcome": outcome,
                "outcome_time": outcome_time,
                "state_times": state_times,
                "main_on_time": main_on_time,
                "main_off_time": main_off_time,
                "main_on_off_dur": main_on_off_dur,
                "response_lick_time": response_lick_time,
                "reaction_time": reaction_time,
                "all_on_off_pairs": all_pairs,
                "all_lick_times": trl_licks,
            }
        )

    return pd.DataFrame(rows)


def get_mouse_weight(
    animal_id: int, from_date: str = "", to_date: str = "", format: str = "df"
) -> Union[pd.DataFrame, Any]:
    """
    Get the weight measurements of an animal, sorted by timestamp.

    Requires the optional 'mice' schema to be configured and available.

    Args:
        animal_id (int): The animal identifier
        from_date (str, optional): Start date in format 'YYYY-MM-DD'. Defaults to ''.
        to_date (str, optional): End date in format 'YYYY-MM-DD'. Defaults to ''.
        format (str, optional): if format equals 'dj' return datajoint expression.

    Returns:
        Union[pd.DataFrame, Any]: DataFrame with columns 'animal_id', 'timestamp'
            and 'weight' sorted by timestamp if format="df", MouseWeight
            expression if format="dj"

    Raises:
        ValueError: If the 'mice' schema is not available.
    """
    mice = get_schema("mice")
    if mice is None:
        raise ValueError(
            "The 'mice' schema is not available. Add it to the 'schemas' section "
            "of your configuration file, e.g. \"mice\": \"lab_mice\"."
        )

    weight_dj = mice.MouseWeight & {"animal_id": animal_id}
    if from_date != "":
        weight_dj = weight_dj & f'timestamp > "{from_date}"'
    if to_date != "":
        weight_dj = weight_dj & f'timestamp < "{to_date}"'

    if format == "dj":
        return weight_dj

    weight_df = weight_dj.fetch(format="frame").reset_index()
    return weight_df.sort_values("timestamp").reset_index(drop=True)
