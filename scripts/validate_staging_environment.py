#!/usr/bin/env python3
"""
Validate Staging Environment Readiness
======================================

Checks all prerequisites for deploying the comprehensive Phase 1 + DSPy architecture.

Usage:
    python scripts/validate_staging_environment.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
    print(f"[INFO] Loaded environment variables from .env file")
except ImportError:
    print(f"[WARNING] python-dotenv not installed, environment variables may not be loaded")
except Exception as e:
    print(f"[WARNING] Could not load .env file: {e}")

def validate_redis():
    """Check Redis connection"""
    try:
        import redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        password = os.getenv("REDIS_PASSWORD", None)

        r = redis.Redis(
            host=host,
            port=port,
            db=0,
            password=password,
            socket_connect_timeout=5
        )
        r.ping()

        # Get some stats
        info = r.info()
        memory_mb = info.get('used_memory', 0) / (1024 * 1024)

        print(f"[OK] Redis: Connected ({host}:{port})")
        print(f"     Memory: {memory_mb:.2f} MB")
        print(f"     Version: {info.get('redis_version', 'unknown')}")
        return True

    except ImportError:
        print("[ERROR] Redis: Package not installed (pip install redis)")
        return False
    except Exception as e:
        print(f"[ERROR] Redis: {e}")
        print("     Try: docker run -d --name tria-redis -p 6379:6379 redis:alpine")
        return False


def validate_chromadb():
    """Check ChromaDB availability"""
    try:
        import chromadb
        from pathlib import Path

        persist_dir = project_root / "data" / "chromadb"

        if not persist_dir.exists():
            print(f"[WARNING] ChromaDB: Persist directory doesn't exist: {persist_dir}")
            print(f"          Creating directory...")
            persist_dir.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(persist_dir))
        collections = client.list_collections()

        print(f"[OK] ChromaDB: Connected")
        print(f"     Path: {persist_dir}")
        print(f"     Collections: {len(collections)}")

        if collections:
            for col in collections[:5]:  # Show first 5
                count = col.count()
                print(f"       - {col.name}: {count} items")

        return True

    except ImportError:
        print("[ERROR] ChromaDB: Package not installed (pip install chromadb)")
        return False
    except Exception as e:
        print(f"[ERROR] ChromaDB: {e}")
        return False


def validate_openai():
    """Check OpenAI API access"""
    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[ERROR] OpenAI: OPENAI_API_KEY not set in environment")
            return False

        if api_key.startswith("sk-"):
            key_preview = f"{api_key[:10]}...{api_key[-4:]}"
        else:
            key_preview = "Invalid format (should start with sk-)"

        client = OpenAI(api_key=api_key, timeout=10.0)

        # Try to list models (lightweight check)
        models = client.models.list()
        model_ids = [m.id for m in models.data if "gpt" in m.id][:5]

        print(f"[OK] OpenAI API: Connected")
        print(f"     Key: {key_preview}")
        print(f"     Available models: {', '.join(model_ids[:3])}...")

        return True

    except ImportError:
        print("[ERROR] OpenAI: Package not installed (pip install openai)")
        return False
    except Exception as e:
        print(f"[ERROR] OpenAI: {e}")
        return False


def validate_env_vars():
    """Check required environment variables"""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for LLM calls",
        "REDIS_HOST": "Redis server host (default: localhost)",
        "REDIS_PORT": "Redis server port (default: 6379)",
    }

    optional_vars = {
        "REDIS_PASSWORD": "Redis password (if auth enabled)",
        "REDIS_DB": "Redis database number (default: 0)",
        "LOG_LEVEL": "Logging level (default: INFO)",
        "DSPY_EVAL_DB": "PostgreSQL connection for DSPy eval storage",
    }

    missing = []
    present = []

    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "PASSWORD" in var:
                display = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
            else:
                display = value
            present.append(f"       {var}={display}")
        else:
            missing.append(f"       {var}: {description}")

    if missing:
        print("[ERROR] Environment Variables: Missing required vars:")
        for m in missing:
            print(m)
        return False
    else:
        print("[OK] Environment Variables: All required vars present")
        for p in present:
            print(p)

        # Show optional vars
        optional_present = [var for var in optional_vars if os.getenv(var)]
        if optional_present:
            print(f"     Optional vars: {', '.join(optional_present)}")

        return True


def validate_python_packages():
    """Check if all required Python packages are installed"""
    required_packages = {
        "openai": "OpenAI Python client",
        "redis": "Redis client",
        "chromadb": "ChromaDB client",
        "fastapi": "FastAPI web framework",
        "uvicorn": "ASGI server",
        "pydantic": "Data validation",
        "sentence-transformers": "Semantic similarity",
        "dspy-ai": "DSPy optimization framework",
    }

    missing = []
    installed = []

    for package, description in required_packages.items():
        try:
            __import__(package.replace("-", "_"))
            installed.append(package)
        except ImportError:
            missing.append(f"       {package}: {description}")

    if missing:
        print("[ERROR] Python Packages: Missing packages:")
        for m in missing:
            print(m)
        print("\n     Install with: pip install -r requirements.txt")
        return False
    else:
        print(f"[OK] Python Packages: All installed ({len(installed)} packages)")
        return True


def validate_file_structure():
    """Check if required files and directories exist"""
    required_paths = {
        "src/agents/async_customer_service_agent.py": "Async agent",
        "src/services/multilevel_cache.py": "Multi-level cache",
        "src/optimization/dspy_framework.py": "DSPy framework",
        "src/prompts/prompt_manager.py": "Prompt manager",
        "src/services/streaming_service.py": "Streaming service",
        "src/enhanced_api.py": "Enhanced API",
        "tests/tier3_e2e/test_full_integration.py": "Integration tests",
        "scripts/benchmark_performance.py": "Performance benchmarks",
    }

    required_dirs = {
        "data/chromadb": "ChromaDB persistence",
        "logs": "Application logs",
        "results": "Test results",
    }

    missing_files = []
    missing_dirs = []

    for path, description in required_paths.items():
        full_path = project_root / path
        if not full_path.exists():
            missing_files.append(f"       {path}: {description}")

    for path, description in required_dirs.items():
        full_path = project_root / path
        if not full_path.exists():
            print(f"[WARNING] Creating directory: {path}")
            full_path.mkdir(parents=True, exist_ok=True)

    if missing_files:
        print("[ERROR] File Structure: Missing required files:")
        for m in missing_files:
            print(m)
        return False
    else:
        print(f"[OK] File Structure: All required files present")
        return True


def validate_python_version():
    """Check Python version"""
    import sys

    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}"

    if major < 3 or (major == 3 and minor < 10):
        print(f"[ERROR] Python Version: {version_str} (requires 3.10+)")
        return False
    else:
        print(f"[OK] Python Version: {version_str}")
        return True


def main():
    """Run all validation checks"""
    print("=" * 70)
    print("Staging Environment Validation")
    print("=" * 70)
    print()

    validators = [
        ("Python Version", validate_python_version),
        ("Python Packages", validate_python_packages),
        ("File Structure", validate_file_structure),
        ("Environment Variables", validate_env_vars),
        ("Redis", validate_redis),
        ("ChromaDB", validate_chromadb),
        ("OpenAI API", validate_openai),
    ]

    results = {}

    for name, validator in validators:
        print(f"\n{name}:")
        print("-" * 70)
        try:
            results[name] = validator()
        except Exception as e:
            print(f"[ERROR] {name}: Unexpected error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, result in results.items():
        status = "[OK]" if result else "[ERROR]"
        print(f"{status} {name}")

    print()
    print(f"Results: {passed}/{total} checks passed")

    if all(results.values()):
        print("\nENVIRONMENT STATUS: READY")
        print("\nNext steps:")
        print("  1. Run integration tests: pytest tests/tier3_e2e/ -v")
        print("  2. Run benchmarks: python scripts/benchmark_performance.py")
        print("  3. Deploy to staging: uvicorn src.enhanced_api:app --reload")
        return 0
    else:
        print("\nENVIRONMENT STATUS: NOT READY")
        print("\nPlease fix the errors above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
