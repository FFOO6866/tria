"""
Xero SDK Rollback Script
=========================

This script reverts the Xero integration from SDK back to REST API
if the SDK migration encounters issues.

Usage:
    python scripts/rollback_xero_sdk.py [--confirm]

Options:
    --confirm    Skip confirmation prompt (use with caution)

What this does:
1. Creates backup of current SDK-based xero_client.py
2. Restores REST API-based xero_client.py from git
3. Verifies the rollback was successful
4. Provides next steps for restarting services
"""

import sys
import os
from pathlib import Path
import subprocess
import shutil
from datetime import datetime

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def confirm_rollback():
    """Ask user to confirm rollback"""
    print_header("XERO SDK ROLLBACK")

    print(f"{Colors.BOLD}You are about to rollback the Xero SDK integration.{Colors.END}")
    print()
    print("This will:")
    print("  1. Backup the current SDK-based xero_client.py")
    print("  2. Restore the REST API-based xero_client.py from git history")
    print("  3. Require service restart")
    print()
    print_warning("This action will replace your current Xero integration!")
    print()

    response = input(f"{Colors.BOLD}Are you sure you want to continue? (yes/no): {Colors.END}").strip().lower()

    return response in ['yes', 'y']


def check_git_available():
    """Check if git is available"""
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Git is not available. Cannot perform rollback.")
        print("Please install git or manually restore xero_client.py from backup.")
        return False


def backup_current_file():
    """Backup current SDK-based xero_client.py"""
    try:
        project_root = Path(__file__).parent.parent
        current_file = project_root / "src" / "integrations" / "xero_client.py"

        if not current_file.exists():
            print_error(f"File not found: {current_file}")
            return False

        # Create backup directory
        backup_dir = project_root / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"xero_client_sdk_{timestamp}.py"

        shutil.copy2(current_file, backup_file)

        print_success(f"Current file backed up to: {backup_file}")
        return True

    except Exception as e:
        print_error(f"Failed to backup current file: {e}")
        return False


def restore_rest_api_version():
    """Restore REST API version from git"""
    try:
        project_root = Path(__file__).parent.parent

        # First, try to find the commit before SDK migration
        result = subprocess.run(
            ['git', 'log', '--oneline', '--grep', 'SDK', '-1'],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        # Get the file from previous commit
        result = subprocess.run(
            ['git', 'show', 'HEAD~1:src/integrations/xero_client.py'],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )

        # Write restored content
        target_file = project_root / "src" / "integrations" / "xero_client.py"
        target_file.write_text(result.stdout)

        print_success("REST API version restored from git history")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to restore from git: {e}")
        print()
        print("Alternative: Manually restore from backup:")
        print("  1. Find latest backup in backups/ directory")
        print("  2. Copy REST API version to src/integrations/xero_client.py")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def verify_rollback():
    """Verify the rollback was successful"""
    try:
        project_root = Path(__file__).parent.parent
        target_file = project_root / "src" / "integrations" / "xero_client.py"

        # Read file and check for REST API markers
        content = target_file.read_text()

        # Check for SDK imports (should NOT be present)
        if 'from xero_python.api_client import ApiClient' in content:
            print_warning("File still contains SDK imports - rollback may have failed")
            return False

        # Check for REST API markers (should be present)
        if 'import requests' not in content:
            print_warning("File missing REST API imports - rollback may have failed")
            return False

        if 'REST API Implementation' not in content:
            print_warning("File missing REST API marker - rollback may have failed")
            return False

        print_success("Rollback verification passed")
        return True

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False


def print_next_steps():
    """Print next steps for user"""
    print_header("NEXT STEPS")

    print(f"{Colors.BOLD}1. Restart Services{Colors.END}")
    print("   The Xero integration has been rolled back, but services need restart:")
    print()
    print("   docker-compose restart")
    print("   # Or restart backend manually:")
    print("   python -m uvicorn src.enhanced_api:app --reload")
    print()

    print(f"{Colors.BOLD}2. Verify REST API Works{Colors.END}")
    print("   Test the restored REST API integration:")
    print()
    print("   python scripts/test_order_with_xero.py")
    print()

    print(f"{Colors.BOLD}3. Review Logs{Colors.END}")
    print("   Monitor logs for any errors:")
    print()
    print("   tail -f logs/app.log")
    print()

    print(f"{Colors.BOLD}4. Update Documentation{Colors.END}")
    print("   Mark the SDK migration as failed in documentation:")
    print()
    print("   - Update docs/XERO_SDK_MIGRATION.md status")
    print("   - Document reason for rollback")
    print()


def main():
    """Main rollback procedure"""
    # Check for --confirm flag
    skip_confirm = '--confirm' in sys.argv

    # Confirm with user
    if not skip_confirm:
        if not confirm_rollback():
            print()
            print_warning("Rollback cancelled by user")
            return 1

    print()

    # Step 1: Check git availability
    print(f"{Colors.BOLD}[1/4] Checking git availability...{Colors.END}")
    if not check_git_available():
        return 1
    print()

    # Step 2: Backup current file
    print(f"{Colors.BOLD}[2/4] Backing up current SDK-based file...{Colors.END}")
    if not backup_current_file():
        return 1
    print()

    # Step 3: Restore REST API version
    print(f"{Colors.BOLD}[3/4] Restoring REST API version from git...{Colors.END}")
    if not restore_rest_api_version():
        return 1
    print()

    # Step 4: Verify rollback
    print(f"{Colors.BOLD}[4/4] Verifying rollback...{Colors.END}")
    if not verify_rollback():
        print_warning("Verification failed - please check manually")
        return 1
    print()

    # Success!
    print_header("ROLLBACK SUCCESSFUL")
    print_success("Xero SDK has been rolled back to REST API implementation")
    print()

    print_next_steps()

    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print_warning("Rollback interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
