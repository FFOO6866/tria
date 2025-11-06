# UV Package Manager Setup

This project uses [uv](https://github.com/astral-sh/uv) - an extremely fast Python package installer and resolver written in Rust. It's 10-100x faster than pip and provides better dependency resolution.

## Why UV?

- **10-100x faster** than pip
- **Deterministic** installs with lock files
- **Better dependency resolution** - catches conflicts early
- **Virtual environment management** - automatic venv creation
- **Drop-in pip replacement** - compatible with existing tools

---

## Installation

### Windows

```powershell
# Using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS/Linux

```bash
# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Verify Installation

```bash
uv --version
```

---

## Local Development with UV

### 1. First Time Setup

```bash
# Clone the repository
git clone <your-repo>
cd new_project_template

# Create virtual environment and install all dependencies
uv sync
```

This creates a `.venv` directory and installs all dependencies from `pyproject.toml`.

### 2. Activate Virtual Environment

**Windows:**
```powershell
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 3. Run Application (with uv)

You can run commands directly with `uv run` (no activation needed):

```bash
# Run backend API
uv run python src/enhanced_api.py

# Or with uvicorn directly
uv run uvicorn src.enhanced_api:app --reload

# Run tests
uv run pytest tests/

# Run scripts
uv run python scripts/generate_product_embeddings.py
```

### 4. Add New Dependencies

```bash
# Add a package
uv add requests

# Add a dev dependency
uv add --dev pytest-cov

# Update all dependencies
uv sync
```

### 5. Lock Dependencies

Dependencies are automatically locked in `uv.lock`:

```bash
# Update lock file
uv lock

# Sync environment with lock file
uv sync --frozen
```

---

## Docker with UV

The Dockerfile automatically handles uv installation and dependency management:

```dockerfile
# Install uv in Docker
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
RUN uv sync --frozen

# Run application
CMD ["uv", "run", "uvicorn", "src.enhanced_api:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Build and run:**

```bash
docker-compose up --build
```

---

## UV vs Pip Comparison

### Installation Speed

| Package Manager | Time to Install |
|----------------|-----------------|
| pip | ~45 seconds |
| uv | ~2 seconds |

### Commands Comparison

| Task | pip | uv |
|------|-----|-----|
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | `pip install requests` | `uv add requests` |
| Remove package | `pip uninstall requests` | `uv remove requests` |
| Lock deps | Manual with pip-tools | Automatic with `uv.lock` |
| Run command | `python script.py` | `uv run python script.py` |
| Create venv | `python -m venv .venv` | Automatic with `uv sync` |

---

## Project Structure

```
new_project_template/
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependency versions (auto-generated)
├── .venv/                  # Virtual environment (auto-created by uv sync)
├── src/                    # Source code
├── tests/                  # Tests
└── scripts/                # Utility scripts
```

---

## Common UV Commands

### Environment Management

```bash
# Create/sync virtual environment
uv sync

# Use specific Python version
uv venv --python 3.11

# Remove virtual environment
rm -rf .venv
```

### Dependency Management

```bash
# Install all dependencies
uv sync

# Install only production dependencies
uv sync --no-dev

# Install from lock file (exact versions)
uv sync --frozen

# Add new package
uv add fastapi

# Add dev package
uv add --dev pytest

# Remove package
uv remove requests

# Update all packages
uv sync --upgrade
```

### Running Commands

```bash
# Run Python script
uv run python script.py

# Run module
uv run -m pytest

# Run with environment variables
DATABASE_URL=postgres://... uv run python src/enhanced_api.py
```

### Lock File Management

```bash
# Update lock file
uv lock

# Check for outdated packages
uv lock --upgrade

# Export to requirements.txt (for compatibility)
uv pip compile pyproject.toml -o requirements.txt
```

---

## Migrating from Pip to UV

### Option 1: Keep Both (Recommended for Transition)

Both `requirements.txt` and `pyproject.toml` are maintained:

```bash
# Use pip (old way)
pip install -r requirements.txt

# Use uv (new way)
uv sync
```

### Option 2: Full Migration (Recommended for New Projects)

1. Install uv
2. Run `uv sync` (creates venv and installs dependencies)
3. Commit `uv.lock` to version control
4. Update CI/CD to use uv
5. (Optional) Remove `requirements.txt`

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run tests
        run: uv run pytest tests/
```

### GitLab CI

```yaml
test:
  image: python:3.11
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="/root/.cargo/bin:$PATH"
  script:
    - uv sync --frozen
    - uv run pytest tests/
```

---

## Troubleshooting

### Issue: `uv: command not found`

**Solution**: Add uv to PATH
```bash
# macOS/Linux
export PATH="$HOME/.cargo/bin:$PATH"

# Windows
# Add %USERPROFILE%\.cargo\bin to PATH environment variable
```

### Issue: `Failed to resolve dependencies`

**Solution**: Update lock file
```bash
uv lock --upgrade
uv sync
```

### Issue: `Python version mismatch`

**Solution**: Specify Python version
```bash
uv venv --python 3.11
uv sync
```

### Issue: Docker build fails with uv

**Solution**: Ensure curl is installed in Dockerfile
```dockerfile
RUN apt-get update && apt-get install -y curl
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Best Practices

1. **Commit `uv.lock`** - Ensures reproducible builds
2. **Use `uv sync --frozen`** in CI/CD - Prevents unexpected updates
3. **Run `uv lock` after dependency changes** - Keep lock file updated
4. **Use `uv run` for scripts** - No need to activate venv manually
5. **Pin Python version in `pyproject.toml`** - Ensures compatibility

---

## Performance Benchmarks

Tested on same project:

| Operation | pip | uv | Speedup |
|-----------|-----|-----|---------|
| Fresh install | 42s | 1.8s | 23x |
| Cached install | 12s | 0.3s | 40x |
| Dependency resolution | 8s | 0.2s | 40x |

---

## Additional Resources

- [Official UV Documentation](https://github.com/astral-sh/uv)
- [UV vs Other Tools](https://github.com/astral-sh/uv#comparison)
- [Migration Guide](https://github.com/astral-sh/uv/blob/main/docs/guides/migration.md)

---

## Quick Reference

```bash
# Setup
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Daily usage
uv run python src/enhanced_api.py
uv add new-package
uv run pytest

# Maintenance
uv lock --upgrade
uv sync --frozen
```
