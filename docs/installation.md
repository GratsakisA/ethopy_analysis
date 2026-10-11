# Installation

## Prerequisites

- Python 3.9 or higher
- pip package manager
- Git (for development installation)

## Installation Methods

### Development Installation (Recommended)

For development or the latest features:

```bash
# Clone the repository
git clone <repository-url>
cd ethopy_analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Package Installation

```bash
pip install ethopy-analysis
```

## Optional Dependencies

### Documentation Tools
```bash
pip install -e ".[docs]"
```

Includes:
- mkdocs
- mkdocs-material
- mkdocstrings

### Development Tools
```bash
pip install -e ".[dev]"
```

Includes:
- pytest (testing)
- black (code formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)
- jupyter (notebooks)

## Reproducible Installation

`pyproject.toml` declares supported version *ranges*. To install one exact
combination verified end-to-end against a live EthoPy database:

```bash
pip install -e . -c constraints.txt
```

Use this first if you hit a dependency-related failure.

## Verify Installation

Test that the package is installed correctly:

```bash
# Test CLI
ethopy-analysis --help

# Test Python import
python -c "import ethopy_analysis; print('Installation successful')"
```

## Dependencies

### Core Dependencies
- **datajoint** (≥0.14.0, **<2.0.0**) - Database connectivity
- **setuptools** (**<82**) - Required by datajoint, see note below
- **pymysql** (**<1.2.0**) - MySQL driver, pulled in by datajoint, see note below
- **matplotlib** (≥3.5.0) - Plotting
- **pandas** (≥1.3.0) - Data manipulation
- **numpy** (≥1.20.0) - Numerical computing
- **seaborn** (≥0.11.0) - Statistical visualization
- **click** (≥8.0.0) - Command-line interface

Only the three capped dependencies above have a known, reproducible incompatibility. Everything else is left uncapped on purpose: a speculative upper bound cannot prevent breakage, it only makes the package uninstallable alongside newer dependencies. Verified working against pandas 3.0.5, numpy 2.5.2 and matplotlib 3.11.1. For an exact reproducible environment use `constraints.txt` instead.

!!! note "Why `setuptools<82`?"
    datajoint runs `import pkg_resources` at import time. It does declare setuptools as a dependency, but left it *unbounded* until 0.14.9, so an unpinned fresh install could resolve to setuptools 82 — the release that actually removed `pkg_resources` — and `import datajoint` then fails with `ModuleNotFoundError: No module named 'pkg_resources'`. setuptools 81 only deprecates it, with a warning. datajoint ≥0.14.9 declares `setuptools<82` itself, so this cap only matters if you resolve to an older datajoint.

!!! note "Why `pymysql<1.2.0`?"
    PyMySQL 1.2.0 attempts TLS opportunistically, so connecting to a server with legacy TLS (MySQL 5.7, for example) fails with `SSLV3_ALERT_HANDSHAKE_FAILURE`. It cannot be worked around from configuration: datajoint's `use_tls=False` only omits the `ssl` argument and never passes PyMySQL's `ssl_disabled=True`, which is the only setting that connects. The cap can be dropped once datajoint passes `ssl_disabled`, or once every server you connect to supports modern TLS.

## Database Setup

The package works without database configuration, but for full functionality:

1. **Configure database connection** (see [Configuration Guide](configuration.md))
2. **Test connection**:
   ```bash
   ethopy-analysis test-db-connection
   ```

## Troubleshooting

### Common Issues

**Import errors**:
```bash
# Reinstall with all dependencies
pip install -e ".[dev,docs]"
```

**Permission errors**:
```bash
# Use user installation
pip install --user -e .
```

**Database connection issues**:
- Check network connectivity
- Verify database credentials
- See [Configuration Guide](configuration.md)

### Getting Help

If you encounter issues:
1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Search existing GitHub issues
3. Create a new issue with error details