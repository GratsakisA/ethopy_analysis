"""
Data analysis functions for Ethopy experiments.

This module provides functions to analyze behavioral data,
calculate performance metrics, and generate session summaries.
"""

import os
from datetime import date
from typing import List, Optional, Union, Any
import pandas as pd
import numpy as np
from ethopy_analysis.db.schemas import get_schema


def get_trial_ids_at_difficulty(animal_id, session, difficulty) -> List[int]:
    """Return the trial indices of one session at the given difficulty or difficulties.

    Args:
        animal_id (int): Animal identifier
        session (int): Session identifier
        difficulty (int or list of int): One difficulty, e.g. 1, or several, e.g. [1, 2]

    Returns:
        List[int]: Trial indices whose difficulty is in the given value(s)
    """
    values = (
        [difficulty] if isinstance(difficulty, (int, np.integer)) else list(difficulty)
    )
    experiment = get_schema("experiment")
    return (
        experiment.Condition.MatchPort()
        * experiment.Trial()
        & f"difficulty in ({', '.join(str(d) for d in values)})"
        & {"animal_id": animal_id, "session": session}
    ).fetch("trial_idx")


def get_difficulties(animal_id, sessions: List[int]) -> List[int]:
    """Return the sorted difficulty levels that exist in the given sessions.

    Args:
        animal_id (int): Animal identifier
        sessions (List[int]): Session identifiers

    Returns:
        List[int]: Sorted unique difficulty levels, empty if none are found
    """
    experiment = get_schema("experiment")
    values = (
        experiment.Condition.MatchPort()
        * experiment.Trial()
        & {"animal_id": animal_id}
        & [f"session={session}" for session in sessions]
    ).fetch("difficulty")
    return sorted({int(d) for d in values})


def get_performance(
    animal_id,
    session,
    trials: Optional[List[int]] = None,
    difficulty: Optional[Union[int, List[int]]] = None,
) -> Optional[float]:
    """
    Calculate performance as the ratio of reward trials to total decisive trials.

    Args:
        animal_id (int): Animal identifier
        session (int): Session identifier
        trials (Optional[List[int]], optional): List of trial indices to filter by.
                                              Defaults to None.
        difficulty (Optional[Union[int, List[int]]], optional): Only use trials at this
                                              difficulty, or at any of these difficulties
                                              if a list is given. Defaults to None (all).

    Returns:
        Optional[float]: Performance ratio (0-1), or None if no decisive trials found

    Note:
        Decisive trials are those with state 'Reward' or 'Punish'.
        Performance is calculated as: count_reward_trials / (count_reward_trials + count_punish_trials)
    """
    from .loaders import get_trial_states

    df = get_trial_states(animal_id, session)
    if df is None or df.empty:
        print("Warning: DataFrame is empty or None - cannot calculate performance")
        return None

    # Filter by difficulty if provided
    if difficulty is not None:
        df = df[df["trial_idx"].isin(get_trial_ids_at_difficulty(animal_id, session, difficulty))]
        if df.empty:
            return None

    # Filter by trials if provided
    if trials is not None:
        df = df[df["trial_idx"].isin(trials)]
        if df.empty:
            print(
                "Warning: No trials found matching the provided trial list - cannot calculate performance"
            )
            return None

    # Filter to only decisive trials (Reward or Punish) - vectorized operation
    decisive_trials = df[df["state"].isin(["Reward", "Punish"])]

    if decisive_trials.empty:
        available_states = df["state"].unique()
        print(
            f"Warning: No Reward or Punish states found. Available states: {available_states}"
        )
        return None

    # Count using vectorized operations for speed
    state_counts = decisive_trials["state"].value_counts()
    count_reward_trials = state_counts.get("Reward", 0)
    count_punish_trials = state_counts.get("Punish", 0)

    # Handle division by zero edge case
    total_decisive = count_reward_trials + count_punish_trials
    if total_decisive == 0:
        print("Warning: Total decisive trials is zero - cannot calculate performance")
        return None

    return count_reward_trials / total_decisive


def get_no_repeat_performance(
    animal_id, session, difficulty: Optional[Union[int, List[int]]] = None
) -> Optional[float]:
    """
    Calculate performance excluding repeated trials.

    Repeated trials are removed as follows:
        - Only the first Punish of each consecutive Punish sequence is kept.
        - A Reward immediately following a repeated Punish is dropped.

    Args:
        animal_id (int): Animal identifier
        session (int): Session identifier
        difficulty (Optional[Union[int, List[int]]], optional): Only use trials at
                                              this difficulty, or at any of these
                                              difficulties if a list is given.
                                              Defaults to None (all difficulties).

    Returns:
        Optional[float]: Performance ratio (0-1), or None if no decisive trials found

    Note:
        Decisive trials are those with state 'Reward' or 'Punish'. Trials are
        ordered by trial_idx before the repeat logic is applied.
        Performance is calculated as: n_reward / (n_reward + n_punish) on the kept trials.
    """
    from .loaders import get_trial_states

    df = get_trial_states(animal_id, session)
    if df is None or df.empty:
        print("Warning: DataFrame is empty or None - cannot calculate performance")
        return None

    # Filter by difficulty if provided
    if difficulty is not None:
        df = df[df["trial_idx"].isin(get_trial_ids_at_difficulty(animal_id, session, difficulty))]
        if df.empty:
            return None

    # Keep only decisive trials, in chronological order
    decisive_trials = df[df["state"].isin(["Reward", "Punish"])]
    if decisive_trials.empty:
        print("Warning: No Reward or Punish states found - cannot calculate performance")
        return None
    decisive_trials = decisive_trials.sort_values("trial_idx").reset_index(drop=True)

    is_reward = decisive_trials["state"] == "Reward"
    is_punish = decisive_trials["state"] == "Punish"

    # First Punish of each consecutive Punish sequence
    first_punish = is_punish & ~is_punish.shift(1, fill_value=False)

    # Punish trials that repeat the previous Punish
    repeated_punish = is_punish & is_punish.shift(1, fill_value=False)

    # Reward immediately following a repeated Punish
    reward_after_repeated_punish = is_reward & repeated_punish.shift(1, fill_value=False)

    keep = (is_reward & ~reward_after_repeated_punish) | first_punish
    kept = decisive_trials[keep]

    count_reward_trials = (kept["state"] == "Reward").sum()
    count_punish_trials = (kept["state"] == "Punish").sum()

    total_decisive = count_reward_trials + count_punish_trials
    if total_decisive == 0:
        print("Warning: Total decisive trials is zero - cannot calculate performance")
        return None

    return count_reward_trials / total_decisive


def session_summary(animal_id: int, session: int) -> None:
    """
    Print a comprehensive summary of a session including metadata and performance.

    Args:
        animal_id (int): The animal identifier
        session (int): The session number

    Prints:
        - Animal ID and session number
        - User name and setup information
        - Session start time and duration
        - Experiment, stimulus, and behavior classes
        - Task filename and the code version records for the session
        - Session performance and number of trials
    """
    from .loaders import (
        get_session_classes,
        get_session_duration,
        get_session_task,
        get_session_version,
        get_trial_states,
    )
    
    session_classes = get_session_classes(animal_id, session)
    print(f"Animal id: {animal_id}, session: {session}")
    print(f"User name: {session_classes['user_name'].values[0]}")
    print(f"Setup: {session_classes['setup'].values[0]}")
    print(f"Session start: {pd.to_datetime(session_classes['session_tmst'].values[0])}")
    print(f"Session duration: {get_session_duration(animal_id, session)}")

    print()
    print("Experiment: ", session_classes["experiment_class"].values[0])
    print("Stimulus: ", session_classes["stimulus_class"].values[0])
    print("Behavior: ", session_classes["behavior_class"].values[0])

    filename = get_session_task(animal_id, session, save_file=False)
    print()
    print(f"Task filename: {filename}")

    versions = get_session_version(animal_id, session)
    if versions.empty:
        print("Code version: not recorded for this session")
    else:
        print("Code version:")
        for _, row in versions.iterrows():
            project = row["project_path"]
            dirty = " (uncommitted changes)" if row["is_dirty"] else ""
            print(f"  {project}: {row['version']} [{row['source_type']}]{dirty}")

    df = get_trial_states(animal_id, session)
    print()
    print(f"Session performance: {get_performance(animal_id, session)}")
    print(f"Number of trials: {max(df['trial_idx'])}")


def get_port_exit_to_lick_latency(
    animal_id: int,
    session: int,
    state: str = "Trial",
    port: int = 3,
) -> pd.DataFrame:
    """Calculate the time from leaving a proximity sensor to the first lick.

    Measures how quickly the animal responds (licks) after moving away from
    the center port, combining data from
    :func:`~ethopy_analysis.data.loaders.get_first_port_exit_after_state` and
    :func:`~ethopy_analysis.data.loaders.get_first_lick_after_state`.

    Args:
        animal_id (int): The animal identifier.
        session (int): The session number.
        state (str, optional): State used as the reference for both off-position
            and first-lick searches. Defaults to ``"Trial"``.
        port (int, optional): Proximity port monitored for the off-position
            event. Defaults to ``3`` (center port).

    Returns:
        pd.DataFrame: One row per trial that has both an off-position event and
            a subsequent lick. Columns: ``trial_idx``, ``state``,
            ``state_onset``, ``off_position``, ``off_port``, ``lick``,
            ``lick_port``, ``off_to_lick`` (time in ms from off-position to
            first lick).
    """
    from .loaders import get_first_port_exit_after_state, get_first_lick_after_state

    off_pos = get_first_port_exit_after_state(animal_id, session, state=state, port=port)
    first_lick = get_first_lick_after_state(animal_id, session, state=state)
    first_lick = first_lick.rename(columns={"ltime": "lick", "port": "lick_port"})

    merged = off_pos.merge(
        first_lick[["trial_idx", "lick", "lick_port"]],
        on="trial_idx",
        how="inner",
    )
    merged = merged.rename(columns={"port": "off_port"})
    merged["off_to_lick"] = merged["lick"] - merged["off_position"]

    return merged.reset_index(drop=True)


def trials_per_session(animal_id: int, min_trials=2, format="df"):
    """Returns the number of trials per session

    Args:
        animal_id (int): The animal identifier
        min_trials (int, optional): Minimum number of trials to include session. Defaults to 2.
        format (str, optional): Return format, either "df" for DataFrame or "dj" for DataJoint expression.
                               Defaults to "df".

    Returns:
        Union[pd.DataFrame, Any]: DataFrame with trials_count column if format="df",
                                 DataJoint expression if format="dj"
    """
    experiment = get_schema("experiment")

    session_trials_dj = (experiment.Session & {"animal_id": animal_id}).aggr(
        experiment.Trial & {"animal_id": animal_id}, trials_count="count(trial_idx)"
    ) - experiment.Session.Excluded & f"trials_count>{min_trials}"
    
    if format == "dj":
        return session_trials_dj
    return session_trials_dj.fetch(format="frame").reset_index()


def weight_check(
    animal_id: int,
    count_from: int = 5,
    weight_days: int = 8,
    weight_percentage: float = 0.7,
    weight_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Check the weight of an animal against its water deprivation reference weight.

    Prints a warning if the last weight is below `weight_percentage` of the
    reference weight, or if the animal has not been weighted for more than
    `weight_days` days.

    Args:
        animal_id (int): The animal identifier
        count_from (int, optional): Index of the weight measurement used as the
            reference weight, counted from the first one, after sorting by
            timestamp. Adjust it to the start of water deprivation. Defaults to 5.
        weight_days (int, optional): Maximum accepted number of days since the
            last weighting. Defaults to 8.
        weight_percentage (float, optional): Minimum accepted fraction of the
            reference weight. Defaults to 0.7.
        weight_df (pd.DataFrame, optional): Weight measurements as returned by
            get_mouse_weight. Fetched from the database if None.

    Returns:
        dict: reference_weight, last_weight, percentage, days_since_last,
            below_threshold and overdue

    Raises:
        ValueError: If the animal has no weight measurements or fewer than
            count_from + 1 of them.
    """
    from .loaders import get_mouse_weight

    if weight_df is None:
        weight_df = get_mouse_weight(animal_id)

    if weight_df.empty:
        raise ValueError(f"No weight measurements for animal_id: {animal_id}")

    if len(weight_df) <= count_from:
        raise ValueError(
            f"animal_id: {animal_id} has {len(weight_df)} weight measurements, "
            f"count_from={count_from} needs at least {count_from + 1}"
        )

    reference_weight = weight_df["weight"].iloc[count_from]
    last_weight = weight_df["weight"].iloc[-1]
    percentage = round(last_weight * 100 / reference_weight, 2)

    last_date = pd.to_datetime(weight_df["timestamp"].iloc[-1]).date()
    days_since_last = (date.today() - last_date).days

    below_threshold = last_weight < weight_percentage * reference_weight
    overdue = days_since_last > weight_days

    if below_threshold:
        print(f"Check the animal_id: {animal_id}, it's weight is at {percentage}%")

    if overdue:
        print(
            f"animal_id: {animal_id} has not been weighted for "
            f"{days_since_last} days"
        )

    return {
        "reference_weight": reference_weight,
        "last_weight": last_weight,
        "percentage": percentage,
        "days_since_last": days_since_last,
        "below_threshold": below_threshold,
        "overdue": overdue,
    }


def get_response_counts(
    animal_id: int,
    from_session: int,
    to_session: int,
    difficulties: Optional[List[int]] = None,
    manual_exclusion_sessions: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Count Reward, Punish and Abort trials per session.

    Args:
        animal_id (int): Animal identifier
        from_session (int): First session number to include
        to_session (int): Last session number to include
        difficulties (Optional[List[int]], optional): Only count trials at these
            difficulties, e.g. [1, 2]. Defaults to None (all difficulties).
        manual_exclusion_sessions (Optional[List[int]], optional): Sessions to skip.
            Defaults to None.

    Returns:
        pd.DataFrame: One row per session and state, with columns session, state and
        n_trials. Empty (but with these columns) if no session has trials.
    """
    experiment = get_schema("experiment")
    stimulus = get_schema("stimulus")
    manual_exclusion_sessions = manual_exclusion_sessions or []

    difficulty = (
        experiment.Condition.MatchPort() * experiment.Trial()
    ).proj("difficulty")
    restr = experiment.Session() & {"animal_id": animal_id}
    valid_sessions = (restr - experiment.Session.Excluded).fetch("session")

    rows = []
    for session in range(from_session, to_session + 1):
        if session not in valid_sessions or session in manual_exclusion_sessions:
            continue

        key = {"animal_id": animal_id, "session": session}
        query = (
            stimulus.StimCondition.Trial
            * experiment.Trial.StateOnset
            * difficulty
            & key
            & 'state in ("Reward", "Punish", "Abort")'
        )
        if difficulties is not None:
            query = query & [{"difficulty": d} for d in difficulties]

        session_trials = query.fetch(format="frame").reset_index()
        if session_trials.empty:
            continue

        for state in ["Reward", "Punish", "Abort"]:
            rows.append(
                {
                    "session": session,
                    "state": state,
                    "n_trials": int((session_trials["state"] == state).sum()),
                }
            )

    return pd.DataFrame(rows, columns=["session", "state", "n_trials"])

