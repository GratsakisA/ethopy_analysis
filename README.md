# Ethopy Analysis
[![PyPI Version](https://img.shields.io/pypi/v/ethopy.svg)](https://pypi.python.org/pypi/ethopy-analysis/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ethopy.svg)](https://pypi.org/project/ethopy-analysis/)
[![Documentation](https://img.shields.io/badge/docs-available-brightgreen.svg)](https://ef-lab.github.io/ethopy_analysis/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<img src="docs/Ethopy_analysis_logo.png" alt="Ethopy Analysis" width="200"/>

A comprehensive Python package for analyzing and visualizing behavioral data from Ethopy experiments.

👉 [Documentation](https://ef-lab.github.io/ethopy_analysis/)

## Overview

Ethopy Analysis provides a modern, modular approach to behavioral data analysis with the following key features:

- **DataFrame-based**: Most of plotting functions work with pandas DataFrames, making them independent of data source
- **Modular Design**: Composable functions for different analysis levels (animal, session, comparison)
- **DataJoint-based**: Works with DataJoint databases and provides DataFrame interfaces
- **Extensible**: Modular function-based architecture for easy extension
- **Production Ready**: Command-line interface, proper packaging, and configuration management

## Installation

Requires **Python 3.9+**.

### From Source (Development)

Use a virtual environment to keep the install isolated:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

Then install:

```bash
# Clone the repository
git clone <repository-url>
cd ethopy_analysis

# Install in development mode
pip install -e .
```

### Reproducible install

`pyproject.toml` declares supported version *ranges*. To install one exact combination that has been verified end-to-end against a live EthoPy database, use the checked-in constraints file:

```bash
pip install -e . -c constraints.txt
```

Use this if you hit a dependency-related failure; it pins every transitive package to a known-good version.

### Optional extras

```bash
pip install -e ".[notebooks]"  # Jupyter kernel for examples/
pip install -e ".[dev]"        # pytest, black, isort, flake8, mypy
pip install -e ".[docs]"       # mkdocs + material theme
```

### Dependencies

| Package | Range | Purpose |
|---|---|---|
| datajoint | >=0.14.0,**<2.0.0** | Database access |
| setuptools | **<82** | Required by datajoint |
| pymysql | **<1.2.0** | MySQL driver (via datajoint) |
| pandas | >=1.3.0 | DataFrame interchange |
| numpy | >=1.20.0 | Numerics |
| matplotlib | >=3.5.0 | Plotting |
| seaborn | >=0.11.0 | Statistical plots |
| click | >=8.0.0 | CLI |

## Package Structure

```
ethopy-analysis/
├── src/ethopy_analysis/
│   ├── data/                        # Data loading and processing
│   │   ├── loaders.py               # DB loaders: sessions, trials, states,
│   │   │                            #   licks, proximity, state windows,
│   │   │                            #   ON-OFF pairs, per-trial raster data
│   │   ├── analysis.py              # Derived metrics: performance,
│   │   │                            #   port-exit-to-lick latency, summaries
│   │   └── utils.py                 # Utilities: consecutive runs,
│   │                                #   column mapping, group helpers
│   ├── plots/                       # Plotting functions (DataFrame-based)
│   │   ├── animal.py                # Animal-level plots across sessions
│   │   ├── session.py               # Session-level plots: licks, proximity,
│   │   │                            #   states, trial-events raster
│   │   ├── comparison.py            # Multi-animal/condition comparisons
│   │   └── utils.py                 # Plotting utilities
│   ├── db/                          # Database connectivity
│   │   └── schemas.py               # DataJoint schema management and caching
│   ├── config/                      # Configuration management
│   │   ├── settings.py              # Config loading: ethopy_config.json,
│   │   │                            #   dj_conf.json, EthoPy local_conf.json,
│   │   │                            #   and environment variables
│   │   ├── styles.py                # Plot style presets
│   │   └── interactive.py           # Interactive credential prompts
│   └── cli.py                       # Command-line interface
├── examples/                        # Example notebooks
│   ├── load_example.ipynb           # Data loading walkthrough
│   ├── animal_analysis_example.ipynb # Animal-level analysis
│   └── session_analysis_example.ipynb # Session-level analysis incl.
│                                    #   proximity, state windows, raster plot
├── docs/                            # Documentation
├── pyproject.toml                   # Package configuration
└── README.md
```

## Configuration

### Already using EthoPy?

If EthoPy is installed, ethopy-analysis automatically reads `~/.ethopy/local_conf.json` —
no extra setup needed.

### Other options

| Method | How |
|--------|-----|
| Config file | Create `ethopy_config.json` in the project root (see [docs/configuration.md](docs/configuration.md)) |
| Environment variables | `export DJ_HOST=… DJ_USER=… DJ_PASSWORD=…` |
| Interactive | Run any loader — credentials are prompted if nothing else is found |

See [docs/configuration.md](docs/configuration.md) for the full priority order and format reference.

## Usage

### Verify your setup

```bash
ethopy-analysis config-summary      # which config file was picked up
ethopy-analysis test-db-connection  # confirm credentials + schema access
```

### Command line

```bash
# Print a text summary of one session
ethopy-analysis session-summary --animal-id 201 --session 71

# Generate the standard animal-level plots
ethopy-analysis analyze-animal --animal-id 201 --min-trials 20 \
    --save-plots --output-dir ./plots

# Full report for one animal
ethopy-analysis generate-report --animal-id 201 --output-dir ./reports
```

### Python API

The package is organised in three layers: **loaders** pull DataFrames out of the
DataJoint schemas, **analysis** derives metrics from them, and **plots** render
them.

```python
from ethopy_analysis.data.loaders import get_sessions, get_trials, get_trial_licks
from ethopy_analysis.data.analysis import get_performance, session_summary
from ethopy_analysis.plots.animal import plot_session_performance
from ethopy_analysis.plots.session import LickPlot

animal_id = 201

# 1. Which sessions does this animal have (with at least 20 trials)?
sessions_df = get_sessions(animal_id, min_trials=20)
sessions = sessions_df["session"].tolist()

# 2. Animal-level view: performance across sessions, shaded by protocol
plot_session_performance(animal_id, sessions, get_performance)

# 3. Session-level view
session = sessions[len(sessions) // 2]
session_summary(animal_id, session)
LickPlot(animal_id, session)
```

Loaders take a `format` argument: `format="df"` (default) returns a pandas DataFrame, `format="dj"` returns the underlying DataJoint expression so you can restrict or join it further before fetching.

```python
# Compose a query server-side, then fetch once
trials_dj = get_trials(animal_id, session, format="dj")
late_trials = (trials_dj & "trial_idx > 100").fetch(format="frame").reset_index()
```

## Extending the package

Plot functions are plain functions over DataFrames — there is no base class to subclass and no registry to update. To add an analysis, write a function, put it in the module that matches its level, and import it.

**1. Write the function.** Take a DataFrame (or `animal_id`/`session`), return
`(fig, ax)`:

```python
# src/ethopy_analysis/plots/animal.py
import matplotlib.pyplot as plt

def plot_learning_rate(performance_df, animal_id=None, save_path=None):
    """Session-over-session change in performance."""
    df = performance_df.sort_values("session").copy()
    df["learning_rate"] = df["correct_rate"].diff()

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df["session"], df["learning_rate"], marker="o")
    ax.axhline(0, color="grey", linestyle="--", linewidth=1)
    ax.set_xlabel("session")
    ax.set_ylabel("Δ correct rate")
    ax.set_title(f"Animal {animal_id}")

    if save_path:
        from ethopy_analysis.plots.utils import save_plot
        save_plot(fig, save_path)
    return fig, ax
```

**2. Export it** by adding the name to the imports *and* the `__all__` list in `src/ethopy_analysis/plots/__init__.py`. Both must agree — a name in `__all__` that is not imported makes `from ethopy_analysis.plots import *` raise `AttributeError`.

**3. Use it** — no registration step:

```python
from ethopy_analysis.plots.animal import plot_learning_rate
fig, ax = plot_learning_rate(performance_df, animal_id=201)
```

### Using your own (non-EthoPy) data

Because the plot layer only touches DataFrames, any data source works once the column names match:

```python
df = pd.read_csv("my_experiment.csv").rename(columns={
    "mouse_id": "animal_id",
    "day": "session",
    "success_percentage": "correct_rate",
})
```

Conventional column names: `animal_id`, `session`, `trial_idx`, `correct_rate`,
`outcome`.

### Adding a new stimulus or behavior type

Loaders resolve the per-session condition table by name from `experiment.Condition` (e.g. `stimulus_class == "Panda"` → `stimulus.Panda`), then join any child tables that hold rows for that session.
A new EthoPy stimulus class works automatically as long as its condition table name matches the class name. Sessions using EthoPy's base `Stimulus` class have no dedicated table and fall back to `stimulus.StimCondition`.

## Examples and Tutorials

Check out the `examples/` directory for comprehensive notebooks:

- **`load_example.ipynb`**: Data loading walkthrough
- **`animal_analysis_example.ipynb`**: Comprehensive animal-level analysis
- **`session_analysis_example.ipynb`**: Detailed session-level analysis

Install the notebook extra first: `pip install -e ".[notebooks]"`

## Contributing

### Code Style

- Functions over classes where possible
- Clear, descriptive function names
- Pandas DataFrames for data exchange
- Matplotlib for plotting
