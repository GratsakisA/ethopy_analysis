# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Fresh installs were broken**: `datajoint` runs `import pkg_resources` at
  import time. It does declare setuptools as a dependency, but left it
  *unbounded* until 0.14.9, so a new environment could resolve to setuptools 82
  — the release that actually removed `pkg_resources` — and every
  `import ethopy_analysis` failed with
  `ModuleNotFoundError: No module named 'pkg_resources'`. Added an explicit
  `setuptools<82` runtime dependency. (Verified: `pkg_resources` still imports
  on setuptools 81, which only deprecates it; it is gone in 82.)
- **A fresh install could not connect to MySQL 5.7 at all**: PyMySQL 1.2.0,
  pulled in transitively and unbounded via datajoint, attempts TLS
  opportunistically, so connecting to a server with legacy TLS failed with
  `SSLV3_ALERT_HANDSHAKE_FAILURE`. No configuration works around it —
  datajoint's `use_tls=False` only omits the `ssl` argument and never passes
  PyMySQL's `ssl_disabled=True`, the sole setting that connects. Added a
  `pymysql<1.2.0` runtime cap.
- **`get_session_task` and `session-summary` crashed on `git_hash`**: the code
  read a `git_hash` column from `experiment.Session.Task`, which does not hold
  version information, so any database without that column raised
  `DataJointError: Attribute 'git_hash' not found`. EthoPy records code
  versions in `experiment.Session.Version` instead — see below.
- **`plot_licks_state` raised `KeyError: 'port'`**: `group_column_times` builds
  its result with `pd.DataFrame(results)`, which produces a frame with *no
  columns* when no events fall in the requested windows, so indexing `["port"]`
  raised `KeyError` instead of yielding an empty result. This hit any session
  with no trials matching `state_select` (default `"Reward"`) — 4 of the first
  40 sessions in a test database. `group_column_times` now returns its
  documented columns when empty, and `plot_licks_state` reports which state was
  missing and lists the states that are available, instead of crashing.
- **`get_trial_stimulus` failed for base-`Stimulus` sessions**: sessions run with
  EthoPy's base `Stimulus` class raised
  `Exception: Cannot find Stimulus table in stimulus schema`, because that class
  has no dedicated condition table. These sessions now fall back to
  `stimulus.StimCondition`, which carries their trial conditions. Explicitly
  requesting an unknown `stim_class` still raises.
- **`from ethopy_analysis.plots import *` raised `AttributeError`**: `__all__`
  listed `plot_first_lick_after`, which does not exist. Removed.
- **`generate-report` crashed for every animal**: the "handle sessions without
  behavior data" guard added in 0.1.3 referenced the loop variable
  `session_row` *before* the loop that defines it, so the command always failed
  with `cannot access local variable 'session_row'`. Moved the guard inside the
  per-session loop, where it now correctly reports "no behavior in this
  session" instead of crashing on `None:.3f`.
- **Python 3.8 incompatibility**: `plots/animal.py` and `config/settings.py` used
  PEP 585 builtin generics (`tuple[...]`) in evaluated annotations, which fail on
  the declared minimum. Switched to `typing.Tuple` and raised the floor to
  Python 3.9 (3.8 is end-of-life).

### Added
- **`get_session_version(animal_id, session, format="df")`**: returns the code
  version records EthoPy writes to `experiment.Session.Version` — one row per
  project directory (the EthoPy package, the plugins directory, ...) with
  `project_path`, `source_type` (`git`/`pypi`/`None`), `version` (git hash or
  package version), `repository_url` and `is_dirty`. Sessions with no records
  return an empty DataFrame rather than raising, and `session_summary` prints
  "Code version: not recorded for this session" for them.

### Changed
- **Dependency policy**: upper bounds are applied only where a specific,
  reproducible incompatibility exists (`datajoint<2.0.0`, `setuptools<82`,
  `pymysql<1.2.0`). Other runtime dependencies are intentionally uncapped —
  verified working against pandas 3.0.5, numpy 2.5.2 and matplotlib 3.11.1 on
  Python 3.13. Reproducibility is handled by the new `constraints.txt`, which
  records one fully-resolved, verified-working environment
  (`pip install -e . -c constraints.txt`).
- `.gitignore`: the blanket `*.png` / `*.pdf` rules are scoped to output
  directories so documentation images stay tracked, and
  `dj_conf.template.json` is no longer swept up by the `*.json` rule — the
  install docs tell users to copy it, so it has to be in the repo.
- Dropped unused runtime dependencies `networkx`, `plotly` and `tqdm`; moved
  `ipykernel` into a new `notebooks` extra.
- `requires-python` raised to `>=3.9`; added 3.12/3.13 classifiers.
- **Breaking**: `get_session_task()` now returns just the task filename (`str`)
  instead of a `(filename, git_hash)` tuple. Code version information moved to
  the new `get_session_version()`. Update call sites that unpack two values.

### Documentation
- README: corrected the stale dependency list, documented the `setuptools<82`
  and `pymysql<1.2.0` constraints, and added Usage (CLI + Python API) and
  "Extending the package" sections.
- Troubleshooting: added entries for `SSLV3_ALERT_HANDSHAKE_FAILURE` and
  `Attribute 'git_hash' not found`, and corrected the `pkg_resources` entry.

## [0.1.3] - 2026-06-09

### Added
- **EthoPy `local_conf.json` compatibility**: auto-detect and convert EthoPy's
  `~/.ethopy/local_conf.json` format (dot-notation `dj_local_conf` keys + `SCHEMATA`)
  to the internal config format, so existing EthoPy users need zero extra setup.
  Added as the lowest-priority config fallback in `find_config_file()`.
- **New data loaders** (`data/loaders.py`): `get_state_windows`, `get_licks_per_state`,
  `get_first_lick_after_state`, `get_first_port_exit_after_state`,
  `get_licks_during_proximity`, `get_proximity_on_off_pairs`,
  `get_trial_proximity_timings`, `get_session_proximity_data`.
- **New analysis function** (`data/analysis.py`): `get_port_exit_to_lick_latency`.
- **New utilities** (`data/utils.py`): `find_consecutive_runs`, `add_column_by_key`.
- **New plot** (`plots/session.py`): `plot_trial_events_raster` — per-trial raster of
  proximity ON-OFF pairs, licks, and states with flexible alignment and sorting.

### Changed
- Updated documentation: configuration discovery priority table, side-by-side format
  docs, quickstart simplification, project logo, and GitHub Pages documentation link.
- Updated `session_analysis_example.ipynb` with usage examples for the new functions.

### Fixed
- Pin `datajoint` to `<2.0.0` to avoid breaking API changes in the 2.x release.
- `generate-report`: fix `datetime.now` usage and handle sessions without behavior data.
- Config: fix shallow-copy bug (`DEFAULT_CONFIG.copy()` → `copy.deepcopy()`) that let
  nested-dict mutations leak into the global default; deduplicate
  `load_config`/`load_config_with_source`.

## [0.1.0] - 2024-01-XX

### Added
- Initial release of ethopy-analysis package
- **Data Loading System**: Comprehensive data loading functions for Ethopy experiments
  - `get_sessions()` - Load session data with date filtering
  - `get_trials()` - Load trial data with optional abort removal
  - `get_trial_states()` - Load trial state onset data
  - `get_trial_experiment()` - Load experiment condition data
  - `get_trial_behavior()` - Load behavior condition data
  - `get_trial_stimulus()` - Load stimulus condition data
  - `get_trial_licks()` - Load lick event data
  - `get_trial_proximities()` - Load proximity sensor data
- **Analysis Functions**: Performance and session analysis
  - `get_performance()` - Calculate performance metrics
  - `session_summary()` - Generate session summaries
  - `trials_per_session()` - Count trials per session
- **Visualization System**: DataFrame-based plotting functions
  - **Animal-level plots**: `plot_session_performance()`, `plot_performance_liquid()`, `plot_session_date()`, `plot_trial_per_session()`
  - **Session-level plots**: `difficultyPlot()`, `LickPlot()`, `plot_licks_state()`, `plot_first_lick_after()`, `plot_valid_proximity_state()`, `plot_proximities_dur()`, `plot_trial_time()`, `liquidsPlot()`, `plot_states_in_time()`, `plot_licks_time()`
  - **Comparison plots**: Multi-animal analysis functions
- **Database Integration**: DataJoint ORM support
  - Schema management with `get_schema()` and `get_all_schemas()`
  - Flexible data format support (DataFrame/DataJoint)
  - Database connection testing utilities
- **Configuration System**: Unified configuration management
  - Support for JSON config files and environment variables
  - Hierarchical configuration loading (env vars > config files > defaults)
  - Database credential management
  - Configuration validation and security checks
- **Command Line Interface**: Full-featured CLI
  - `ethopy-analysis analyze-animal` - Animal-level analysis
  - `ethopy-analysis compare-animals` - Multi-animal comparisons
  - `ethopy-analysis generate-report` - Comprehensive reporting
  - `ethopy-analysis test-db-connection` - Database connectivity testing
- **Documentation**: Comprehensive documentation system
  - MkDocs-based documentation with Material theme
  - API reference documentation
  - Example notebooks for common workflows
  - Developer guide with contribution guidelines
- **Example Notebooks**: 
  - `animal_analysis_example.ipynb` - Animal-level analysis examples
  - `session_analysis_example.ipynb` - Session-level analysis examples
  - `load_example.ipynb` - Data loading function examples
- **Package Infrastructure**:
  - Modern Python packaging with `pyproject.toml`
  - Automated version management with setuptools_scm
  - Code quality tools (ruff, black, isort, mypy)
  - GitHub Actions for automated releases
  - PyPI publishing workflow

### Technical Details
- **Python Support**: Python 3.8+
- **Key Dependencies**: pandas, matplotlib, seaborn, datajoint, click, numpy, plotly
- **Architecture**: Modular design with DataFrame-first approach
- **Database**: DataJoint ORM with MySQL/MariaDB support
- **Visualization**: Matplotlib/Seaborn-based with optional Plotly support

### Dependencies
- datajoint>=0.13.0
- matplotlib>=3.5.0
- networkx>=2.6.0
- numpy>=1.20.0
- pandas>=1.3.0
- plotly>=5.0.0
- seaborn>=0.11.0
- click>=8.0.0
- tqdm>=4.60.0
- ipykernel>=6.0.0

## Release Notes Template

For future releases, use this template:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features and functionality

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security improvements and fixes
```

## Development Guidelines

### Version Numbering
- **Major** (X.0.0): Breaking changes, major new features
- **Minor** (X.Y.0): New features, backward compatible
- **Patch** (X.Y.Z): Bug fixes, backward compatible

### Changelog Maintenance
- Update CHANGELOG.md with every release
- Follow Keep a Changelog format
- Include migration notes for breaking changes
- Link to relevant issues and pull requests where applicable

### Release Process
1. Update CHANGELOG.md with new version section
2. Move items from [Unreleased] to new version section
3. Add release date
4. Create and push version tag
5. GitHub Actions will automatically create release with changelog excerpt

[Unreleased]: https://github.com/ef-lab/ethopy_analysis/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/ef-lab/ethopy_analysis/compare/v0.1.2...v0.1.3
[0.1.0]: https://github.com/ef-lab/ethopy_analysis/releases/tag/v0.1.0