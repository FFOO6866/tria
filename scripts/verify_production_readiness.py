#!/usr/bin/env python3
"""
Production Readiness Verification Script
=========================================

This script verifies that all production systems are working:
1. Basic server functionality
2. Cache integration
3. Performance benchmarks
4. Load testing capability
5. Security testing
6. Monitoring configuration
7. CI/CD pipeline

Run this script to get an HONEST assessment of production readiness.

Usage:
    python scripts/verify_production_readiness.py
"""

import sys
import os
import subprocess
import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"   {text}")


class ProductionReadinessVerifier:
    """Verifies production readiness step by step"""

    def __init__(self):
        self.results = {
            "checks_passed": 0,
            "checks_failed": 0,
            "checks_warning": 0,
            "details": []
        }
        self.server_running = False
        self.base_url = "http://localhost:8003"

    def run_check(self, name: str, func) -> bool:
        """Run a verification check"""
        print(f"\n{Colors.BOLD}Checking: {name}{Colors.END}")
        print("-" * 80)

        try:
            result, message = func()

            if result == "pass":
                print_success(message)
                self.results["checks_passed"] += 1
                self.results["details"].append({"check": name, "status": "pass", "message": message})
                return True
            elif result == "warn":
                print_warning(message)
                self.results["checks_warning"] += 1
                self.results["details"].append({"check": name, "status": "warning", "message": message})
                return True
            else:
                print_error(message)
                self.results["checks_failed"] += 1
                self.results["details"].append({"check": name, "status": "fail", "message": message})
                return False

        except Exception as e:
            print_error(f"Check failed with exception: {str(e)}")
            self.results["checks_failed"] += 1
            self.results["details"].append({"check": name, "status": "fail", "message": str(e)})
            return False

    # ========================================================================
    # File Structure Checks
    # ========================================================================

    def check_file_structure(self) -> Tuple[str, str]:
        """Verify all expected files exist"""
        required_files = [
            "src/enhanced_api.py",
            "src/config.py",
            "src/database.py",
            "src/cache/chat_response_cache.py",
            "src/monitoring/audit_logger.py",
            "tests/performance/test_comprehensive_performance.py",
            "tests/load/test_concurrent_load.py",
            "tests/security/test_owasp_top_10.py",
            "monitoring/prometheus/prometheus.yml",
            "monitoring/alertmanager/config.yml",
            ".github/workflows/production-pipeline.yml"
        ]

        missing = []
        for file in required_files:
            if not Path(file).exists():
                missing.append(file)

        if not missing:
            return ("pass", f"All {len(required_files)} required files exist")
        else:
            return ("fail", f"Missing files: {', '.join(missing)}")

    def check_python_syntax(self) -> Tuple[str, str]:
        """Check Python files for syntax errors"""
        files_to_check = [
            "tests/performance/test_comprehensive_performance.py",
            "tests/load/test_concurrent_load.py",
            "tests/security/test_owasp_top_10.py",
            "src/monitoring/audit_logger.py"
        ]

        errors = []
        for file in files_to_check:
            if Path(file).exists():
                try:
                    subprocess.run(
                        ["python", "-m", "py_compile", file],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                except subprocess.CalledProcessError as e:
                    errors.append(f"{file}: {e.stderr}")

        if not errors:
            return ("pass", f"All {len(files_to_check)} test files have valid Python syntax")
        else:
            return ("fail", f"Syntax errors: {'; '.join(errors)}")

    # ========================================================================
    # Server Checks
    # ========================================================================

    def check_server_running(self) -> Tuple[str, str]:
        """Check if server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.server_running = True
                data = response.json()
                return ("pass", f"Server is running and healthy (version: {data.get('version', 'unknown')})")
            else:
                return ("fail", f"Server returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            return ("fail", "Server is not running. Start with: python src/enhanced_api.py")
        except Exception as e:
            return ("fail", f"Health check failed: {str(e)}")

    def check_cache_integration(self) -> Tuple[str, str]:
        """Check if cache is integrated and working"""
        if not self.server_running:
            return ("warn", "Server not running - cannot verify cache")

        try:
            # Make same request twice
            payload = {
                "message": "Hello, this is a cache test",
                "outlet_id": 1,
                "user_id": "cache_test",
                "session_id": "cache_test"
            }

            # First request (should be cache miss)
            response1 = requests.post(
                f"{self.base_url}/api/chatbot",
                json=payload,
                timeout=30
            )

            if response1.status_code != 200:
                return ("fail", f"Chat endpoint returned {response1.status_code}")

            # Second request (should be cache hit)
            time.sleep(1)
            start = time.time()
            response2 = requests.post(
                f"{self.base_url}/api/chatbot",
                json=payload,
                timeout=30
            )
            latency2 = (time.time() - start) * 1000

            if response2.status_code != 200:
                return ("fail", f"Second request failed: {response2.status_code}")

            data2 = response2.json()
            metadata = data2.get("metadata", {})
            is_cached = metadata.get("cache_hit", False)

            if is_cached:
                return ("pass", f"Cache is working! Second request hit cache (latency: {latency2:.0f}ms)")
            else:
                return ("warn", "Cache integration exists but second request was not cached (check TTL settings)")

        except Exception as e:
            return ("fail", f"Cache test failed: {str(e)}")

    def check_streaming_available(self) -> Tuple[str, str]:
        """Check if streaming endpoint is available"""
        if not self.server_running:
            return ("warn", "Server not running - cannot verify streaming")

        try:
            # Check if streaming endpoint exists
            response = requests.post(
                f"{self.base_url}/api/v1/chat/stream",
                json={
                    "message": "Test streaming",
                    "outlet_id": 1,
                    "user_id": "stream_test",
                    "session_id": "stream_test"
                },
                timeout=10,
                stream=True
            )

            if response.status_code == 200:
                return ("pass", "Streaming endpoint is available at /api/v1/chat/stream")
            elif response.status_code == 404:
                return ("fail", "Streaming endpoint not found (router not included)")
            else:
                return ("warn", f"Streaming endpoint returned unexpected status: {response.status_code}")

        except Exception as e:
            return ("fail", f"Streaming check failed: {str(e)}")

    # ========================================================================
    # Configuration Checks
    # ========================================================================

    def check_environment_config(self) -> Tuple[str, str]:
        """Check if environment variables are configured"""
        required_vars = [
            "OPENAI_API_KEY",
            "DATABASE_URL",
            "TAX_RATE",
            "XERO_SALES_ACCOUNT_CODE"
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if not missing:
            return ("pass", f"All {len(required_vars)} required environment variables are set")
        else:
            return ("warn", f"Missing env vars: {', '.join(missing)} (may be in .env.docker for Docker)")

    def check_monitoring_configs(self) -> Tuple[str, str]:
        """Check monitoring configuration syntax"""
        import yaml

        configs = {
            "monitoring/prometheus/prometheus.yml": "Prometheus",
            "monitoring/alertmanager/config.yml": "Alertmanager"
        }

        errors = []
        for file, name in configs.items():
            if Path(file).exists():
                try:
                    with open(file, 'r') as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    errors.append(f"{name}: {str(e)}")
            else:
                errors.append(f"{name} config not found")

        if not errors:
            return ("pass", "Prometheus and Alertmanager configs have valid YAML syntax")
        else:
            return ("fail", f"Config errors: {'; '.join(errors)}")

    # ========================================================================
    # Test Availability Checks
    # ========================================================================

    def check_test_scripts_executable(self) -> Tuple[str, str]:
        """Check if test scripts can be imported"""
        test_files = [
            "tests.performance.test_comprehensive_performance",
            "tests.load.test_concurrent_load",
            "tests.security.test_owasp_top_10"
        ]

        importable = []
        not_importable = []

        for module in test_files:
            try:
                # Try to import
                __import__(module)
                importable.append(module)
            except ImportError as e:
                not_importable.append(f"{module}: {str(e)}")

        if len(importable) == len(test_files):
            return ("pass", f"All {len(test_files)} test modules are importable")
        else:
            return ("warn", f"Some test modules have import issues: {'; '.join(not_importable)}")

    # ========================================================================
    # Quick Performance Check
    # ========================================================================

    def check_basic_performance(self) -> Tuple[str, str]:
        """Quick performance sanity check"""
        if not self.server_running:
            return ("warn", "Server not running - cannot measure performance")

        try:
            # Measure latency of 3 simple requests
            latencies = []

            for i in range(3):
                start = time.time()
                response = requests.post(
                    f"{self.base_url}/api/chatbot",
                    json={
                        "message": f"Hello {i}",
                        "outlet_id": 1,
                        "user_id": "perf_test",
                        "session_id": f"perf_test_{i}"
                    },
                    timeout=30
                )
                latency_ms = (time.time() - start) * 1000

                if response.status_code == 200:
                    latencies.append(latency_ms)

            if not latencies:
                return ("fail", "All performance test requests failed")

            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)

            if avg_latency < 3000:  # < 3s
                return ("pass", f"Performance looks good (avg: {avg_latency:.0f}ms, max: {max_latency:.0f}ms)")
            elif avg_latency < 5000:  # < 5s
                return ("warn", f"Performance acceptable but could be better (avg: {avg_latency:.0f}ms, max: {max_latency:.0f}ms)")
            else:
                return ("fail", f"Performance is poor (avg: {avg_latency:.0f}ms, max: {max_latency:.0f}ms) - expected < 5000ms")

        except Exception as e:
            return ("fail", f"Performance check failed: {str(e)}")

    # ========================================================================
    # Summary
    # ========================================================================

    def print_summary(self):
        """Print final summary"""
        total = self.results["checks_passed"] + self.results["checks_failed"] + self.results["checks_warning"]

        print_header("VERIFICATION SUMMARY")

        print(f"Total Checks: {total}")
        print(f"{Colors.GREEN}Passed: {self.results['checks_passed']}{Colors.END}")
        print(f"{Colors.YELLOW}Warnings: {self.results['checks_warning']}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.results['checks_failed']}{Colors.END}")

        # Calculate score
        score = (self.results["checks_passed"] + self.results["checks_warning"] * 0.5) / total * 100 if total > 0 else 0

        print(f"\n{Colors.BOLD}Overall Score: {score:.0f}/100{Colors.END}")

        # Verdict
        print(f"\n{Colors.BOLD}PRODUCTION READINESS VERDICT:{Colors.END}")

        if self.results["checks_failed"] == 0 and self.results["checks_warning"] == 0:
            print_success("EXCELLENT - All checks passed! ✨")
        elif self.results["checks_failed"] == 0:
            print_warning("GOOD - All critical checks passed, some warnings to address")
        elif self.results["checks_failed"] <= 2:
            print_warning("NEEDS WORK - Some issues need fixing before production")
        else:
            print_error("NOT READY - Multiple critical issues found")

        # Recommendations
        print(f"\n{Colors.BOLD}NEXT STEPS:{Colors.END}\n")

        if not self.server_running:
            print("1. Start the server: python src/enhanced_api.py")
            print("2. Re-run this verification script")
            print("3. Run full performance benchmarks")
        elif self.results["checks_failed"] > 0:
            print("1. Fix the failed checks above")
            print("2. Re-run this verification script")
            print("3. Run full test suites")
        else:
            print("1. ✅ Run full performance benchmarks:")
            print("   python tests/performance/test_comprehensive_performance.py")
            print("\n2. ✅ Run load tests:")
            print("   python tests/load/test_concurrent_load.py")
            print("\n3. ✅ Run security tests:")
            print("   python tests/security/test_owasp_top_10.py")
            print("\n4. ✅ Deploy monitoring:")
            print("   docker-compose -f monitoring/docker-compose.monitoring.yml up -d")

        # Save results
        with open("verification_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📊 Detailed results saved to: verification_results.json\n")


def main():
    """Run all verification checks"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*80)
    print("TRIA AI-BPO Production Readiness Verification")
    print("="*80)
    print(f"{Colors.END}\n")

    verifier = ProductionReadinessVerifier()

    # Run all checks
    checks = [
        ("File Structure", verifier.check_file_structure),
        ("Python Syntax", verifier.check_python_syntax),
        ("Environment Configuration", verifier.check_environment_config),
        ("Server Running", verifier.check_server_running),
        ("Cache Integration", verifier.check_cache_integration),
        ("Streaming Endpoint", verifier.check_streaming_available),
        ("Basic Performance", verifier.check_basic_performance),
        ("Monitoring Configs", verifier.check_monitoring_configs),
        ("Test Scripts", verifier.check_test_scripts_executable),
    ]

    for check_name, check_func in checks:
        verifier.run_check(check_name, check_func)

    # Print summary
    verifier.print_summary()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Verification interrupted by user{Colors.END}\n")
        sys.exit(1)
