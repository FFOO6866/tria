#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Environment Setup and Validation
======================================

This script:
1. Checks for conflicting processes on port 8003
2. Validates Python environment and dependencies
3. Starts the API server with proper error handling
4. Validates the server is responding correctly
5. Provides clear instructions for load testing

Usage:
    python scripts/setup_test_environment.py

Options:
    --kill-existing  Kill existing processes on port 8003
    --validate-only  Only validate, don't start server
"""

import sys
import os
from pathlib import Path
import subprocess
import time
import requests
import psutil
import argparse

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8003
HOST = "127.0.0.1"


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'=' * 70}")
    print(f" {text}")
    print(f"{'=' * 70}\n")


def print_status(emoji, text):
    """Print a status message"""
    print(f"{emoji} {text}")


def check_port_in_use(port):
    """Check if a port is in use and return the PIDs"""
    pids = []
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            pids.append(conn.pid)
    return pids


def kill_processes_on_port(port):
    """Kill all processes using the specified port"""
    pids = check_port_in_use(port)

    if not pids:
        print_status("✓", f"No processes found on port {port}")
        return True

    print_status("⚠", f"Found {len(pids)} process(es) on port {port}: {pids}")

    killed = []
    for pid in pids:
        try:
            process = psutil.Process(pid)
            process_name = process.name()
            print(f"  Killing process {pid} ({process_name})...")
            process.terminate()
            process.wait(timeout=5)
            killed.append(pid)
            print_status("✓", f"Killed process {pid}")
        except psutil.NoSuchProcess:
            print_status("✓", f"Process {pid} already terminated")
            killed.append(pid)
        except psutil.AccessDenied:
            print_status("✗", f"Access denied for process {pid} (run as administrator)")
        except Exception as e:
            print_status("✗", f"Failed to kill process {pid}: {e}")

    # Verify port is free
    time.sleep(1)
    remaining = check_port_in_use(port)
    if remaining:
        print_status("✗", f"Port {port} still in use by PIDs: {remaining}")
        return False

    print_status("✓", f"Port {port} is now free")
    return True


def validate_environment():
    """Validate Python environment and dependencies"""
    print_header("Validating Environment")

    issues = []

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 11):
        print_status("✓", f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        issues.append(f"Python 3.11+ required, found {python_version.major}.{python_version.minor}")
        print_status("✗", f"Python version: {python_version.major}.{python_version.minor} (need 3.11+)")

    # Check critical dependencies
    dependencies = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("openai", "OpenAI"),
        ("requests", "Requests"),
        ("redis", "Redis"),
    ]

    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            print_status("✓", f"{display_name} installed")
        except ImportError:
            issues.append(f"{display_name} not installed")
            print_status("✗", f"{display_name} missing")

    # Check .env file
    env_file = project_root / ".env"
    if env_file.exists():
        print_status("✓", ".env file found")

        # Check critical env vars
        from dotenv import load_dotenv
        load_dotenv(env_file)

        required_vars = ["OPENAI_API_KEY"]
        for var in required_vars:
            if os.getenv(var):
                print_status("✓", f"{var} configured")
            else:
                issues.append(f"{var} not configured in .env")
                print_status("✗", f"{var} missing")
    else:
        issues.append(".env file not found")
        print_status("✗", ".env file missing")

    # Check source files
    api_file = project_root / "src" / "enhanced_api.py"
    if api_file.exists():
        print_status("✓", "API source file found")
    else:
        issues.append("src/enhanced_api.py not found")
        print_status("✗", "API source file missing")

    return issues


def start_server():
    """Start the API server"""
    print_header("Starting API Server")

    print(f"Starting uvicorn on {HOST}:{PORT}...")
    print("(Press Ctrl+C to stop)")
    print()

    try:
        # Start uvicorn directly
        cmd = [
            sys.executable, "-m", "uvicorn",
            "src.enhanced_api:app",
            "--host", HOST,
            "--port", str(PORT),
            "--reload"
        ]

        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Wait for server to start
        print("Waiting for server to initialize...")
        time.sleep(5)

        # Stream output for a bit to see startup
        for _ in range(20):
            line = process.stdout.readline()
            if line:
                print(line.rstrip())
            if "Application startup complete" in line:
                break
            time.sleep(0.5)

        return process

    except Exception as e:
        print_status("✗", f"Failed to start server: {e}")
        return None


def validate_server(max_attempts=5):
    """Validate the server is responding correctly"""
    print_header("Validating Server")

    url = f"http://{HOST}:{PORT}/health"

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}/{max_attempts}: Testing {url}")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                print_status("✓", f"Server responding correctly (200 OK)")
                print(f"Response: {response.text[:200]}")
                return True
            else:
                print_status("⚠", f"Server returned {response.status_code}")
                print(f"Response: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print_status("⚠", f"Connection refused (server may still be starting)")
        except requests.exceptions.Timeout:
            print_status("⚠", f"Request timed out")
        except Exception as e:
            print_status("⚠", f"Error: {e}")

        if attempt < max_attempts:
            print(f"Waiting 3 seconds before retry...")
            time.sleep(3)

    print_status("✗", "Server validation failed after all attempts")
    return False


def test_chatbot_endpoint():
    """Test the chatbot endpoint"""
    print_header("Testing Chatbot Endpoint")

    url = f"http://{HOST}:{PORT}/api/chatbot"
    payload = {
        "message": "Hello, this is a test",
        "session_id": "test_session_123"
    }

    try:
        print(f"Testing POST {url}")
        print(f"Payload: {payload}")

        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_status("✓", "Chatbot endpoint working correctly")
            print(f"Response preview: {str(data)[:200]}")
            return True
        else:
            print_status("✗", f"Chatbot endpoint returned {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except Exception as e:
        print_status("✗", f"Chatbot endpoint test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup and validate test environment")
    parser.add_argument("--kill-existing", action="store_true",
                       help="Kill existing processes on port 8003")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate environment, don't start server")
    parser.add_argument("--no-server-test", action="store_true",
                       help="Skip server validation tests")

    args = parser.parse_args()

    print_header("Test Environment Setup & Validation")

    # Step 1: Validate environment
    issues = validate_environment()

    if issues:
        print("\n❌ Environment validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease fix these issues before proceeding.")
        return 1

    print_status("✓", "Environment validation passed")

    if args.validate_only:
        print("\n✅ Validation complete (--validate-only specified)")
        return 0

    # Step 2: Check port availability
    if args.kill_existing:
        if not kill_processes_on_port(PORT):
            print("\n❌ Failed to free port. Try running as administrator.")
            return 1
    else:
        pids = check_port_in_use(PORT)
        if pids:
            print_status("⚠", f"Port {PORT} is in use by PIDs: {pids}")
            print(f"\nRun with --kill-existing to automatically kill these processes")
            print(f"Or manually kill them: taskkill /F /PID {' /PID '.join(map(str, pids))}")
            return 1
        else:
            print_status("✓", f"Port {PORT} is available")

    # Step 3: Start server
    process = start_server()
    if not process:
        return 1

    if args.no_server_test:
        print("\n✅ Server started (--no-server-test specified)")
        print(f"\nServer is running. Press Ctrl+C to stop.")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n\nStopping server...")
            process.terminate()
        return 0

    # Step 4: Validate server
    try:
        if not validate_server():
            print("\n❌ Server validation failed")
            process.terminate()
            return 1

        # Step 5: Test chatbot endpoint
        if not test_chatbot_endpoint():
            print("\n⚠ Chatbot endpoint test failed, but server is running")
            print("You may need to check the server logs")

        # Success
        print_header("Setup Complete ✅")
        print("Server is running and validated!")
        print()
        print("Next steps:")
        print("  1. Run load tests: python scripts/load_test_chat_api.py")
        print("  2. View API docs: http://localhost:8003/docs")
        print("  3. Test endpoint: curl -X POST http://localhost:8003/api/chatbot \\")
        print("                     -H 'Content-Type: application/json' \\")
        print("                     -d '{\"message\": \"test\", \"session_id\": \"test\"}'")
        print()
        print("Press Ctrl+C to stop the server")
        print()

        # Keep server running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n\nStopping server...")
            process.terminate()
            process.wait(timeout=5)
            print_status("✓", "Server stopped")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if process:
            process.terminate()
        return 1


if __name__ == "__main__":
    exit(main())
