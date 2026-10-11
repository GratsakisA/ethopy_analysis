# Configuration

The Ethopy Analysis package uses a unified configuration system for database connections and analysis settings. Configuration is **optional** - the package works with defaults.

## Quick Setup

### Method 1: Already using EthoPy? Zero extra setup needed

If EthoPy is installed on your machine, ethopy-analysis automatically reads your existing
`~/.ethopy/local_conf.json`. No extra configuration is required — just run your analysis.

```
~/.ethopy/local_conf.json   ← detected and used automatically
```

To verify it was picked up correctly:

```bash
ethopy-analysis config-summary
```

### Method 2: Template File
```bash
# Copy template and add your credentials
cp dj_conf.template.json dj_conf.json
# Edit dj_conf.json with your database details
```

### Method 3: Environment Variables
```bash
export DJ_HOST="database.example.org:3306"
export DJ_USER="your_username"
export DJ_PASSWORD="your_password"
```

### Method 4: Custom Configuration File
```bash
ethopy-analysis create-config --output-path config.json
```

## Configuration Discovery

The system searches for a configuration file in this priority order and uses the **first one found**:

| Priority | Location | File(s) |
|----------|----------|---------|
| 1 | Current directory | `ethopy_config.json`, `config.json`, `dj_conf.json` |
| 2 | `./config/` subdirectory | `ethopy_config.json`, `config.json`, `dj_conf.json` |
| 3 | `~/.ethopy/` | `ethopy_config.json`, `config.json`, `dj_conf.json` |
| 4 | Package directory | `ethopy_config.json`, `config.json`, `dj_conf.json` |
| 5 *(fallback)* | `~/.ethopy/` | `local_conf.json` (EthoPy format, auto-converted) |

Environment variables (`DJ_HOST`, `DJ_USER`, `DJ_PASSWORD`) are applied **after** the file is
loaded and always override file values.

## Supported Configuration Formats

### ethopy-analysis format

Used by Methods 2–4 above.

```json
{
  "database": {
    "host": "your-database-host:3306",
    "user": "your_username",
    "password": "your_password",
    "schemas": {
      "experiment": "lab_experiments",
      "stimulus": "lab_stimuli",
      "behavior": "lab_behavior",
      "mice": "lab_mice"
    }
  },
  "paths": {
    "data_dir": "./data",
    "output_dir": "./output"
  }
}
```

### EthoPy `local_conf.json` format (auto-detected)

If `~/.ethopy/local_conf.json` is the only config found, it is automatically converted.
The relevant fields that are read are:

```json
{
  "dj_local_conf": {
    "database.host": "your-database-host",
    "database.user": "your_username",
    "database.password": "your_password",
    "database.port": 3306
  },
  "SCHEMATA": {
    "experiment": "lab_experiments",
    "behavior": "lab_behavior",
    "stimulus": "lab_stimuli",
    "mice": "lab_mice"
  }
}
```

All other fields in `local_conf.json` (e.g. `source_path`, `Channels`, `logging`) are ignored.
If `SCHEMATA` is absent, default schema names are used.

## Database Configuration

### Required Fields
- `host`: Database host and port (e.g. `"database.example.org:3306"`)
- `user`: Database username
- `password`: Database password
- `schemas`: Schema name mappings

### Schema Mapping
```json
{
  "schemas": {
    "experiment": "lab_experiments",
    "stimulus": "lab_stimuli",
    "behavior": "lab_behavior",
    "mice": "lab_mice"
  }
}
```

`experiment`, `stimulus` and `behavior` are required. `mice` is optional and only needed for the animal weight functions. It is never created on the server: if the schema does not exist, it is skipped with a warning and everything else keeps working.

## Environment Variables

Environment variables are applied after the config file and override any file values:

```bash
export DJ_HOST="database.example.org:3306"
export DJ_USER="your_username"
export DJ_PASSWORD="your_password"
export ETHOPY_OUTPUT_DIR="/path/to/output"
```

## Security Best Practices

### 1. Use Environment Variables (recommended for CI/CD)
```bash
export DJ_HOST="database.example.org:3306"
export DJ_USER="your_username"
export DJ_PASSWORD="your_secure_password"
```

### 2. Local Configuration File
The recommended file name is `ethopy_config.json` (highest priority in the search order).
All `*.json` files are in `.gitignore`, so credentials are never accidentally committed.

```bash
# create your local config — it will never be committed
cp dj_conf.template.json ethopy_config.json
# edit ethopy_config.json and add your credentials
```

`dj_conf.json` and `config.json` are also supported and equally git-safe.

### 3. Never Commit Passwords
- All `.json` files are excluded by `.gitignore`
- Use environment variables for CI/CD pipelines
- If you use EthoPy, `~/.ethopy/local_conf.json` is already outside the repo

## Testing Configuration

### Test Database Connection
```bash
ethopy-analysis test-db-connection
```

### View Current Configuration
```bash
ethopy-analysis config-summary
```

## Usage Examples

<!-- ### Basic Usage (No Configuration)
```python
from ethopy_analysis.plots.animal import plot_animal_performance

# Works with defaults
plot_animal_performance(your_dataframe)
``` -->

<!-- ### With Database
```python
from ethopy_analysis.data.loaders import load_animal_data

# Uses configured database
animal_data = load_animal_data(animal_id=123)
``` -->

### Load Specific Config
```python
from ethopy_analysis.config.settings import load_config

# Load specific file
config = load_config("my_config.json")
```

## Troubleshooting

### Configuration Not Found
- Run `ethopy-analysis config-summary` to see which file (if any) was loaded
- Check that the file is named exactly `ethopy_config.json`, `config.json`, or `dj_conf.json`
- Use an absolute path to force a specific file: `load_config("/full/path/to/config.json")`

### EthoPy `local_conf.json` Not Picked Up
- Confirm the file exists at `~/.ethopy/local_conf.json`
- Check it contains a `dj_local_conf` key — that is how the format is detected
- If a higher-priority config file exists (e.g. `dj_conf.json` in the current directory), it takes precedence

### Database Connection Issues
- Verify `host` is in `host:port` format (e.g. `"db.lab.org:3306"`)
- Check credentials with `ethopy-analysis test-db-connection`
- Confirm the schema names match your database

## No Configuration Required

The package works without configuration:
- Database: Uses environment variables or prompts
- Paths: Uses current directory
- Analysis: Uses reasonable defaults

Configure only what you need to customize!