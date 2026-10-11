# Troubleshooting

Common issues and solutions for the Ethopy Analysis package.

## Installation Issues

### `ModuleNotFoundError: No module named 'pkg_resources'`

**Problem**: Any import fails with a traceback ending in `datajoint/plugin.py: import pkg_resources`:

```
File ".../datajoint/plugin.py", line 4, in <module>
    import pkg_resources
ModuleNotFoundError: No module named 'pkg_resources'
```

**Cause**: datajoint imports `pkg_resources` at import time. It declares setuptools as a dependency, but left it *unbounded* until 0.14.9, so an environment that resolved to setuptools 82 — the release that removed `pkg_resources` — cannot import datajoint at all. setuptools 81 only deprecates it and still works, emitting a warning.

**Solution**: the package now pins `setuptools<82`. Reinstall to pick it up:

```bash
pip install -e .

# Or downgrade setuptools directly in an existing environment
pip install "setuptools<82"
```

### `SSLV3_ALERT_HANDSHAKE_FAILURE` when connecting

**Problem**: the connection fails before authentication, with:

```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on
'127.0.0.1' ([SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake
failure)")
```

**Cause**: PyMySQL 1.2.0 attempts TLS opportunistically. Servers with legacy TLS — MySQL 5.7 in particular — are rejected by modern OpenSSL. Setting `use_tls` to `false` does *not* help: datajoint only omits the `ssl` argument and never passes PyMySQL's `ssl_disabled=True`, which is the only setting that connects.

**Solution**: the package pins `pymysql<1.2.0`. In an environment that already
resolved to 1.2.0:

```bash
pip install "pymysql<1.2.0"
```

### Package Not Found After Installation

**Problem**: `ethopy-analysis` command not found or import errors

**Solutions**:
```bash
# Check if package is installed
pip show ethopy-analysis

# Reinstall in development mode
pip install -e .

# Verify installation
python -c "import ethopy_analysis; print('Success')"
```

### Permission Errors During Installation

**Problem**: Permission denied when installing package

**Solutions**:
```bash
# Use user installation
pip install --user -e .

# Or use virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

### Missing Dependencies

**Problem**: Import errors for specific modules

**Solutions**:
```bash
# Install all optional dependencies
pip install -e ".[dev,docs]"

# Install specific dependency groups
pip install -e ".[dev]"  # Development tools
pip install -e ".[docs]"  # Documentation tools

# Update all packages
pip install --upgrade -e .
```

## Database Connection Issues

### Cannot Connect to Database

**Problem**: Connection timeout or authentication errors

**Solutions**:
```bash
# Test connection
ethopy-analysis test-db-connection

# Check environment variables
echo $DJ_HOST
echo $DJ_USER
echo $DJ_PASSWORD

# Set environment variables
export DJ_HOST="database.example.org:3306"
export DJ_USER="your_username"
export DJ_PASSWORD="your_password"
```

### Configuration File Not Found

**Problem**: Configuration file not detected

**Solutions**:
```bash
# Create configuration file
cp dj_conf.template.json dj_conf.json

# Check file locations
ls -la dj_conf.json config.json ethopy_config.json

# Use absolute path
python -c "from ethopy_analysis.config.settings import load_config; print(load_config('/full/path/to/config.json'))"
```

### Schema Access Errors

**Problem**: Cannot access database schemas

**Solutions**:
```python
# Check schema configuration
pfrom ethopy_analysis.config.settings import get_database_config
rint(get_database_config())

# Test schema access
from ethopy_analysis.db.schemas import get_schema
experiment = get_schema("experiment")
```

## CLI Issues

### Command Not Found

**Problem**: `ethopy-analysis` command not available

**Solutions**:
```bash
# Check if CLI is installed
which ethopy-analysis

# Reinstall package
pip install -e .

# Run module directly
python -m ethopy_analysis.cli --help
```

### Output Directory Errors

**Problem**: Cannot create output directories

**Solutions**:
```bash
# Check directory permissions
ls -la ./plots

# Create directory manually
mkdir -p ./plots ./reports

# Use different directory
ethopy-analysis analyze-animal --animal-id 123 --output-dir ~/analysis
```

### No Data Found for Animal

**Problem**: "No sessions found for animal X"

**Solutions**:
```bash
# Check animal ID exists in database
ethopy-analysis session-summary --animal-id 123 --session 1

# Adjust minimum trials threshold
ethopy-analysis analyze-animal --animal-id 123 --min-trials 1

# Check date range
python -c "from ethopy_analysis.data.loaders import get_sessions; print(get_sessions(123))"
```

## Python API Issues

### Import Errors

**Problem**: Cannot import package modules

**Solutions**:
```python
# Check package installation
import sys
print(sys.path)

# Try explicit imports
from ethopy_analysis.data.loaders import get_sessions
from ethopy_analysis.plots.animal import plot_session_performance

# Check for missing dependencies
try:
    import matplotlib
    import pandas
    import datajoint
except ImportError as e:
    print(f"Missing dependency: {e}")
```

### Plotting Errors

**Problem**: Matplotlib or plotting function errors

**Solutions**:
```python
# Check matplotlib backend
import matplotlib
print(matplotlib.get_backend())

# Set backend if needed
matplotlib.use('Agg')  # For headless systems

# Check data before plotting
print(df.shape)
print(df.head())

# Use save_path to avoid display issues
from ethopy_analysis.plots.animal import plot_session_performance
fig, ax = plot_session_performance(123, sessions, save_path="test.png")
```

## Performance Issues

### Slow Data Loading

**Problem**: Data loading takes too long

**Solutions**:
```python
# Use date filters
sessions = get_sessions(animal_id=123, from_date="2023-01-01", to_date="2023-12-31")

# Filter by minimum trials
sessions = get_sessions(animal_id=123, min_trials=10)

# Use specific session
trials = get_trials(animal_id=123, session=5)
```

### Memory Issues

**Problem**: Out of memory errors

**Solutions**:
```python
# Process sessions in smaller batches
session_list = sessions['session'].values
for batch in [session_list[i:i+10] for i in range(0, len(session_list), 10)]:
    # Process batch
    pass

# Use specific date ranges
sessions = get_sessions(animal_id=123, from_date="2023-01-01", to_date="2023-01-31")
```

## Development Issues

### Code Style Errors

**Problem**: Linting or formatting issues

**Solutions**:
```bash
# Check with ruff
ruff check src/

# Fix automatically
ruff check --fix src/

# Check with pylint
pylint src/ethopy_analysis/

# Format code
black src/ethopy_analysis/
```

### Test Failures

**Problem**: Unit tests failing

**Solutions**:
```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_data_loaders.py

# Run with coverage
pytest --cov=ethopy_analysis tests/
```

## Environment Issues

### Jupyter Notebook Problems

**Problem**: Cannot run notebooks in examples/

**Solutions**:
```bash
# Install jupyter
pip install jupyter

# Install kernel
python -m ipykernel install --user --name=ethopy-analysis

# Start notebook
jupyter notebook examples/
```

### Virtual Environment Issues

**Problem**: Package not available in virtual environment

**Solutions**:
```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package in virtual environment
pip install -e .

# Check virtual environment
which python
which pip
```

## Getting Help

### Check Documentation
- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)
- [API Reference](api-reference.md)

### Debug Information
```python
# System information
import sys
print(f"Python version: {sys.version}")

# Package information
import ethopy_analysis
print(f"Package location: {ethopy_analysis.__file__}")

# Database connection
from ethopy_analysis.db.schemas import test_connection
print(f"Database connection: {test_connection()}")
```

### Common Commands for Debugging
```bash
# Check package version
pip show ethopy-analysis

# Test CLI
ethopy-analysis --help

# Test database
ethopy-analysis test-db-connection

# Check configuration
python -c "from ethopy_analysis.config.settings import get_config_summary; print(get_config_summary())"
```

### Reporting Issues
When reporting bugs, include:
- Python version
- Package version
- Error messages
- Configuration details (without passwords)
- Steps to reproduce

### Community Support
- GitHub Issues: Report bugs and feature requests
- Examples: Check `examples/` directory for working code
- Documentation: Complete API reference available