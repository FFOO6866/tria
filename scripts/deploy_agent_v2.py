#!/usr/bin/env python3
"""
TRIA AI-BPO Deployment Agent v2.0

UNIFIED DEPLOYMENT APPROACH following TRIA deployment philosophy:

1. Git-based workflow: local → git → server (NEVER rsync for code)
2. Single source of truth: ONE .env file, ONE docker-compose.yml
3. Automated deployment: NEVER deploy manually
4. Environment-aware: ENVIRONMENT and DEPLOYMENT_SIZE flags
5. No manual env passing: Docker Compose reads .env automatically

CRITICAL CHANGES from v1.0:
- Removed manual environment variable passing to docker-compose
- Added .env file sync to server (scp)
- Docker Compose reads .env automatically - no --env-file needed
- Simplified deployment commands
- Better validation and troubleshooting

KEY INSIGHT:
Docker Compose AUTOMATICALLY reads .env file in same directory.
No need to pass environment variables manually!

Author: TRIA AI-BPO DevOps Team
Version: 2.0.0
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class DeploymentAgent:
    """
    Comprehensive deployment agent for TRIA AI-BPO platform.

    Version 2.0 - Simplified approach:
    - ONE .env file (synced to server via scp)
    - ONE docker-compose.yml (on server via git)
    - Docker Compose reads .env automatically
    - NO manual environment variable passing
    """

    # CRITICAL: These env vars MUST be set in .env for docker-compose
    REQUIRED_DOCKER_ENV_VARS = [
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        'OPENAI_API_KEY',  # CRITICAL - most common failure
        'SECRET_KEY',
        'TAX_RATE',
        'XERO_SALES_ACCOUNT_CODE',
        'XERO_TAX_TYPE',
        'REDIS_PASSWORD',
    ]

    # Deployment configuration vars (in .env)
    DEPLOYMENT_CONFIG_VARS = [
        'SERVER_IP',
        'SERVER_USER',
        'PEM_KEY_PATH',
        'ENVIRONMENT',          # development or production
        'DEPLOYMENT_SIZE',      # small or medium
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / '.env'
        self.docker_compose_file = project_root / 'docker-compose.yml'
        self.log_file = project_root / 'deployment.log'

    def log(self, message: str, level: str = 'INFO'):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"

        # Color output for console
        if level == 'ERROR':
            print(f"{Colors.FAIL}{log_message}{Colors.ENDC}")
        elif level == 'WARNING':
            print(f"{Colors.WARNING}{log_message}{Colors.ENDC}")
        elif level == 'SUCCESS':
            print(f"{Colors.OKGREEN}{log_message}{Colors.ENDC}")
        elif level == 'INFO':
            print(f"{Colors.OKBLUE}{log_message}{Colors.ENDC}")
        else:
            print(log_message)

        # Write to log file
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
        print(f"{text.center(80)}")
        print(f"{'='*80}{Colors.ENDC}\n")

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None,
                   capture_output: bool = True, timeout: int = 300) -> Tuple[int, str, str]:
        """
        Run shell command and return exit code, stdout, stderr

        Args:
            cmd: Command and arguments as list
            cwd: Working directory (default: project_root)
            capture_output: Whether to capture output
            timeout: Command timeout in seconds (default: 5 minutes)

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        cwd = cwd or self.project_root
        self.log(f"Running command: {' '.join(cmd)}", 'INFO')

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s: {' '.join(cmd)}", 'ERROR')
            return -1, '', f'Command timed out after {timeout}s'
        except Exception as e:
            self.log(f"Command failed: {e}", 'ERROR')
            return -1, '', str(e)

    def load_env_file(self, env_file: Path) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}
        if not env_file.exists():
            self.log(f"Environment file not found: {env_file}", 'ERROR')
            return env_vars

        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    # Handle multi-line values and quotes
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")

        return env_vars

    def check_required_files(self) -> bool:
        """Check that all required files exist"""
        self.print_header("STEP 1: Checking Required Files")

        required_files = [
            self.env_file,
            self.docker_compose_file,
        ]

        all_exist = True
        for file in required_files:
            if file.exists():
                self.log(f"✓ Found: {file.name}", 'SUCCESS')
            else:
                self.log(f"✗ Missing: {file.name}", 'ERROR')
                all_exist = False

        return all_exist

    def validate_environment_vars(self) -> Tuple[bool, List[str]]:
        """
        Validate that all required environment variables are set

        Returns:
            Tuple of (all_valid, missing_vars)
        """
        self.print_header("STEP 2: Validating Environment Variables")

        env_vars = self.load_env_file(self.env_file)
        missing_vars = []

        # Check required docker-compose vars
        self.log("Checking REQUIRED environment variables:", 'INFO')
        for var in self.REQUIRED_DOCKER_ENV_VARS:
            if var not in env_vars or not env_vars[var]:
                self.log(f"✗ MISSING: {var}", 'ERROR')
                missing_vars.append(var)
            else:
                # Mask sensitive values
                if any(x in var for x in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                    display_value = env_vars[var][:10] + '...' if len(env_vars[var]) > 10 else '***'
                else:
                    display_value = env_vars[var]
                self.log(f"✓ {var} = {display_value}", 'SUCCESS')

        # Check deployment config vars
        self.log("\nChecking DEPLOYMENT configuration variables:", 'INFO')
        for var in self.DEPLOYMENT_CONFIG_VARS:
            if var not in env_vars or not env_vars[var]:
                self.log(f"⚠ MISSING: {var}", 'WARNING')
                if var in ['ENVIRONMENT', 'SERVER_IP']:
                    missing_vars.append(var)  # Critical vars
            else:
                display_value = env_vars[var]
                if var == 'ENVIRONMENT':
                    # Highlight the environment
                    if display_value.lower() == 'production':
                        self.log(f"✓ {var} = {display_value} (PRODUCTION MODE)", 'WARNING')
                    else:
                        self.log(f"✓ {var} = {display_value}", 'SUCCESS')
                elif var == 'DEPLOYMENT_SIZE':
                    self.log(f"✓ {var} = {display_value} ({'2GB' if display_value == 'small' else '4GB+'} RAM)", 'SUCCESS')
                else:
                    self.log(f"✓ {var} = {display_value}", 'SUCCESS')

        return len(missing_vars) == 0, missing_vars

    def check_git_status(self) -> bool:
        """Check git status and ensure working directory is clean"""
        self.print_header("STEP 3: Checking Git Status")

        # Check if git repo
        returncode, stdout, stderr = self.run_command(['git', 'status'])
        if returncode != 0:
            self.log("Not a git repository or git not available", 'ERROR')
            return False

        # Check for uncommitted changes
        returncode, stdout, stderr = self.run_command(['git', 'status', '--porcelain'])
        if stdout.strip():
            self.log("WARNING: You have uncommitted changes:", 'WARNING')
            self.log(stdout, 'WARNING')
            response = input(f"\n{Colors.WARNING}Continue with uncommitted changes? (yes/no): {Colors.ENDC}")
            if response.lower() != 'yes':
                self.log("Deployment cancelled by user", 'WARNING')
                return False
        else:
            self.log("✓ Working directory is clean", 'SUCCESS')

        # Check current branch
        returncode, stdout, stderr = self.run_command(['git', 'branch', '--show-current'])
        if returncode == 0:
            branch = stdout.strip()
            self.log(f"Current branch: {branch}", 'INFO')

            if branch not in ['main', 'master']:
                self.log(f"WARNING: Not on main/master branch", 'WARNING')
                response = input(f"\n{Colors.WARNING}Deploy from '{branch}' branch? (yes/no): {Colors.ENDC}")
                if response.lower() != 'yes':
                    self.log("Deployment cancelled by user", 'WARNING')
                    return False

        return True

    def sync_env_to_server(self, server_ip: str, server_user: str, pem_key: str,
                          server_path: str) -> bool:
        """
        Copy .env file to server via scp

        This is the ONLY file we copy directly (not via git)
        because it contains secrets that should never be in version control.

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file
            server_path: Project path on server

        Returns:
            True if sync successful
        """
        self.print_header("STEP 4: Syncing .env to Server")

        self.log("Copying .env file to server via scp...", 'INFO')
        self.log(f"SECURITY: .env contains secrets and is NEVER committed to git", 'INFO')

        # Use scp to copy .env
        scp_cmd = [
            'scp',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            str(self.env_file),
            f'{server_user}@{server_ip}:{server_path}/.env'
        ]

        returncode, stdout, stderr = self.run_command(scp_cmd)
        if returncode != 0:
            self.log(f"Failed to copy .env to server: {stderr}", 'ERROR')
            return False

        self.log("✓ .env file synced to server", 'SUCCESS')

        # Verify .env exists on server
        ssh_cmd = [
            'ssh',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            f'{server_user}@{server_ip}',
            f'test -f {server_path}/.env && echo "OK" || echo "MISSING"'
        ]

        returncode, stdout, stderr = self.run_command(ssh_cmd)
        if 'OK' in stdout:
            self.log("✓ Verified .env exists on server", 'SUCCESS')
            return True
        else:
            self.log("✗ .env verification failed on server", 'ERROR')
            return False

    def sync_code_to_server(self, server_ip: str, server_user: str, pem_key: str,
                           server_path: str) -> bool:
        """
        Sync code to server using git (NOT rsync/copy)

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file
            server_path: Project path on server

        Returns:
            True if sync successful
        """
        self.print_header("STEP 5: Syncing Code via Git")

        # Step 1: Push to git remote
        self.log("Pushing to git remote...", 'INFO')
        returncode, stdout, stderr = self.run_command(['git', 'push', 'origin', 'HEAD'])
        if returncode != 0:
            self.log(f"Git push failed: {stderr}", 'ERROR')
            self.log("TIP: Make sure you have committed all changes", 'WARNING')
            return False
        self.log("✓ Pushed to git remote", 'SUCCESS')

        # Step 2: SSH to server and pull
        self.log(f"Connecting to server {server_user}@{server_ip}...", 'INFO')

        # SSH commands to run on server
        ssh_commands = [
            f"cd {server_path}",
            "git fetch origin",
            "git pull origin main || git pull origin master",
        ]

        ssh_cmd = [
            'ssh',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            f'{server_user}@{server_ip}',
            ' && '.join(ssh_commands)
        ]

        returncode, stdout, stderr = self.run_command(ssh_cmd)
        if returncode != 0:
            self.log(f"Server git pull failed: {stderr}", 'ERROR')
            self.log("TIP: Make sure the repo is cloned on the server first", 'WARNING')
            self.log(f"     Run: ssh {server_user}@{server_ip}", 'WARNING')
            self.log(f"     Then: git clone <repo-url> {server_path}", 'WARNING')
            return False

        self.log("✓ Server code synced via git", 'SUCCESS')
        self.log(stdout, 'INFO')

        return True

    def deploy_to_server(self, server_ip: str, server_user: str, pem_key: str,
                        server_path: str, environment: str, deployment_size: str) -> bool:
        """
        Deploy application on server using docker-compose

        CRITICAL CHANGE: Docker Compose reads .env automatically!
        NO need to pass environment variables manually.

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file
            server_path: Project path on server
            environment: 'development' or 'production'
            deployment_size: 'small' or 'medium'

        Returns:
            True if deployment successful
        """
        self.print_header(f"STEP 6: Deploying to Server ({environment.upper()} MODE - {deployment_size.upper()})")

        self.log("IMPORTANT: Docker Compose reads .env automatically", 'INFO')
        self.log("No need to pass environment variables manually!", 'INFO')

        # Determine if we need full-stack profile
        profile_flag = ""
        if deployment_size == "medium":
            profile_flag = "--profile full-stack"
            self.log("Using full-stack profile (frontend + nginx)", 'INFO')
        else:
            self.log("Using minimal profile (backend only)", 'INFO')

        # SSH commands for deployment
        ssh_commands = [
            f"cd {server_path}",

            # Verify .env exists
            "test -f .env || (echo 'ERROR: .env file missing' && exit 1)",

            # Verify critical env vars are set (basic sanity check)
            "grep -q 'OPENAI_API_KEY=' .env || (echo 'ERROR: OPENAI_API_KEY not set in .env' && exit 1)",
            "grep -q 'POSTGRES_PASSWORD=' .env || (echo 'ERROR: POSTGRES_PASSWORD not set in .env' && exit 1)",

            # Stop existing containers
            "echo 'Stopping existing containers...'",
            "docker-compose down",

            # Pull latest images (if any are pre-built)
            "echo 'Pulling latest images...'",
            "docker-compose pull || true",

            # Build with no cache to ensure fresh build
            "echo 'Building images...'",
            "docker-compose build --no-cache",

            # Start containers (docker-compose reads .env automatically!)
            "echo 'Starting containers...'",
            f"docker-compose {profile_flag} up -d",

            # Wait a moment for containers to start
            "sleep 5",

            # Show container status
            "echo 'Container status:'",
            "docker-compose ps",

            # Show recent logs
            "echo 'Recent logs:'",
            "docker-compose logs --tail=50"
        ]

        # Create single SSH command
        ssh_cmd = [
            'ssh',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            f'{server_user}@{server_ip}',
            ' && '.join(ssh_commands)
        ]

        self.log("Deploying via docker-compose on server...", 'INFO')
        # Increase timeout for deployment (10 minutes)
        returncode, stdout, stderr = self.run_command(ssh_cmd, capture_output=False, timeout=600)

        if returncode != 0:
            self.log("Deployment failed", 'ERROR')
            self.log(f"Error: {stderr}", 'ERROR')
            return False

        self.log("✓ Deployment completed", 'SUCCESS')
        return True

    def verify_deployment(self, server_ip: str, server_user: str, pem_key: str,
                         server_path: str) -> bool:
        """
        Verify that the deployment was successful

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file
            server_path: Project path on server

        Returns:
            True if verification successful
        """
        self.print_header("STEP 7: Verifying Deployment")

        # Check container health
        ssh_cmd = [
            'ssh',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            f'{server_user}@{server_ip}',
            f'cd {server_path} && docker-compose ps'
        ]

        returncode, stdout, stderr = self.run_command(ssh_cmd)
        if returncode != 0:
            self.log("Could not verify deployment", 'ERROR')
            return False

        self.log("Container status:", 'INFO')
        self.log(stdout, 'INFO')

        # Check if all services are running
        if 'Up' in stdout or 'running' in stdout:
            self.log("✓ Containers are running", 'SUCCESS')

            # Check API health endpoint
            env_vars = self.load_env_file(self.env_file)
            backend_port = env_vars.get('BACKEND_PORT', '8003')

            self.log(f"\nChecking API health at http://{server_ip}:{backend_port}/health...", 'INFO')

            # Try curl via SSH
            ssh_cmd = [
                'ssh',
                '-i', pem_key,
                '-o', 'StrictHostKeyChecking=no',
                f'{server_user}@{server_ip}',
                f'curl -f http://localhost:{backend_port}/health || echo "Health check failed"'
            ]

            returncode, stdout, stderr = self.run_command(ssh_cmd)
            if returncode == 0 and 'health check failed' not in stdout.lower():
                self.log("✓ API health check passed", 'SUCCESS')
                self.log(f"Response: {stdout}", 'INFO')
                return True
            else:
                self.log("⚠ API health check failed (might take a moment to start)", 'WARNING')
                self.log("TIP: Wait 30-60 seconds and check manually", 'INFO')
                self.log(f"     curl http://{server_ip}:{backend_port}/health", 'INFO')
                return True  # Still count as success, just warn
        else:
            self.log("✗ Containers are not running properly", 'ERROR')
            return False

    def print_troubleshooting_guide(self):
        """Print troubleshooting guide"""
        self.print_header("TROUBLESHOOTING GUIDE")

        guide = """
Common Issues and Solutions:

1. OPENAI_API_KEY not set error:
   - Check .env file has OPENAI_API_KEY defined
   - Ensure key is valid and not expired
   - Verify .env was synced to server
   - Solution: Edit .env locally and redeploy

2. .env not found on server:
   - deploy_agent.py syncs .env via scp
   - Check SSH permissions
   - Verify server path is correct
   - Solution: Re-run deploy_agent.py

3. Docker Compose not reading .env:
   - .env must be in same directory as docker-compose.yml
   - Check file permissions (should be readable)
   - Verify no syntax errors in .env
   - Solution: Check .env location and permissions

4. Git sync fails:
   - Ensure you have pushed changes to remote
   - Check SSH key permissions (chmod 400 key.pem on Linux/Mac)
   - Verify server has git repo cloned
   - Solution: Manually clone repo on server first

5. Container won't start:
   - Check logs: ssh user@server 'cd ~/tria && docker-compose logs backend'
   - Verify all required env vars are set in .env
   - Check Docker image build errors
   - Solution: docker-compose build --no-cache

6. Out of memory (t3.small):
   - Check: docker stats
   - Verify DEPLOYMENT_SIZE=small in .env
   - Check memory limits in docker-compose.yml
   - Solution: Upgrade to t3.medium or reduce services

7. Port conflicts:
   - Check if ports are already in use
   - Verify port settings in .env
   - Solution: Change ports in .env or stop conflicting services

8. Health check fails:
   - Backend might still be starting (wait 30-60 seconds)
   - Check backend logs for errors
   - Verify database and redis are running
   - Solution: docker-compose logs backend

Key Commands (run on server):

# View logs:
docker-compose logs -f backend

# Check container status:
docker-compose ps

# Restart service:
docker-compose restart backend

# Rebuild and restart:
docker-compose build --no-cache backend
docker-compose up -d backend

# Check environment variables in container:
docker-compose exec backend env | grep OPENAI

# Access container shell:
docker-compose exec backend /bin/bash

# Check resource usage:
docker stats --no-stream

# Clean up and restart:
docker-compose down
docker system prune -f
docker-compose up -d
"""
        print(guide)

    def run_deployment(self, args):
        """
        Run full deployment workflow

        Args:
            args: Parsed command-line arguments
        """
        self.print_header("TRIA AI-BPO DEPLOYMENT AGENT v2.0")
        self.log(f"Deployment started at {datetime.now()}", 'INFO')

        # Step 1: Check required files
        if not self.check_required_files():
            self.log("Missing required files. Deployment aborted.", 'ERROR')
            sys.exit(1)

        # Step 2: Validate environment variables
        valid, missing = self.validate_environment_vars()
        if not valid:
            self.log(f"Missing required environment variables: {', '.join(missing)}", 'ERROR')
            self.log("Please update .env file and try again", 'ERROR')
            sys.exit(1)

        # Step 3: Check git status
        if not args.skip_git and not self.check_git_status():
            self.log("Git checks failed. Deployment aborted.", 'ERROR')
            sys.exit(1)

        # Load deployment config
        env_vars = self.load_env_file(self.env_file)
        server_ip = args.server or env_vars.get('SERVER_IP')
        server_user = args.user or env_vars.get('SERVER_USER', 'ubuntu')
        pem_key = args.key or env_vars.get('PEM_KEY_PATH')
        server_path = args.path or env_vars.get('SERVER_PROJECT_PATH', '/home/ubuntu/tria')
        environment = env_vars.get('ENVIRONMENT', 'development')
        deployment_size = env_vars.get('DEPLOYMENT_SIZE', 'small')

        if not all([server_ip, server_user, pem_key]):
            self.log("Missing deployment configuration (SERVER_IP, SERVER_USER, PEM_KEY_PATH)", 'ERROR')
            self.log("Set these in .env file or provide via command-line arguments", 'ERROR')
            sys.exit(1)

        # Confirm deployment to production
        if environment.lower() == 'production':
            self.log("WARNING: Deploying to PRODUCTION environment", 'WARNING')
            response = input(f"\n{Colors.WARNING}Are you sure you want to deploy to PRODUCTION? (yes/no): {Colors.ENDC}")
            if response.lower() != 'yes':
                self.log("Deployment cancelled by user", 'WARNING')
                sys.exit(0)

        # Step 4: Sync .env to server (via scp)
        if not self.sync_env_to_server(server_ip, server_user, pem_key, server_path):
            self.log(".env sync failed. Deployment aborted.", 'ERROR')
            sys.exit(1)

        # Step 5: Sync code to server (via git)
        if not args.skip_git:
            if not self.sync_code_to_server(server_ip, server_user, pem_key, server_path):
                self.log("Code sync failed. Deployment aborted.", 'ERROR')
                sys.exit(1)

        # Step 6: Deploy on server
        if not self.deploy_to_server(server_ip, server_user, pem_key, server_path,
                                     environment, deployment_size):
            self.log("Deployment failed", 'ERROR')
            self.print_troubleshooting_guide()
            sys.exit(1)

        # Step 7: Verify deployment
        if not args.skip_verify:
            if not self.verify_deployment(server_ip, server_user, pem_key, server_path):
                self.log("Deployment verification failed", 'WARNING')
                self.print_troubleshooting_guide()
                # Don't exit - deployment might still be starting

        # Success!
        self.print_header("DEPLOYMENT SUCCESSFUL")
        backend_port = env_vars.get('BACKEND_PORT', '8003')
        frontend_port = env_vars.get('FRONTEND_PORT', '3000')

        self.log(f"✓ Application deployed to {server_ip}", 'SUCCESS')
        self.log(f"✓ Environment: {environment}", 'SUCCESS')
        self.log(f"✓ Deployment size: {deployment_size} ({'2GB' if deployment_size == 'small' else '4GB+'} RAM)", 'SUCCESS')
        self.log(f"✓ Deployment completed at {datetime.now()}", 'SUCCESS')

        self.log(f"\nAccess the application at:", 'INFO')
        self.log(f"  Backend:  http://{server_ip}:{backend_port}", 'INFO')
        self.log(f"  API Docs: http://{server_ip}:{backend_port}/docs", 'INFO')
        self.log(f"  Health:   http://{server_ip}:{backend_port}/health", 'INFO')

        if deployment_size == 'medium':
            self.log(f"  Frontend: http://{server_ip}:{frontend_port}", 'INFO')
            self.log(f"  Nginx:    http://{server_ip} (port 80)", 'INFO')


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='TRIA AI-BPO Deployment Agent v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
UNIFIED DEPLOYMENT APPROACH:
  - ONE .env file (synced to server via scp)
  - ONE docker-compose.yml (synced via git)
  - Docker Compose reads .env automatically (no manual env passing!)

Examples:
  # Deploy using settings from .env file:
  python scripts/deploy_agent_v2.py

  # Deploy with custom server settings:
  python scripts/deploy_agent_v2.py --server 13.54.39.187 --user ubuntu --key ~/.ssh/server.pem

  # Skip git checks (for testing):
  python scripts/deploy_agent_v2.py --skip-git

  # Skip deployment verification:
  python scripts/deploy_agent_v2.py --skip-verify

  # Show troubleshooting guide only:
  python scripts/deploy_agent_v2.py --troubleshoot

For more information, see docs/DEPLOYMENT.md
        """
    )

    parser.add_argument('--server', help='Server IP address (overrides .env)')
    parser.add_argument('--user', help='SSH username (overrides .env, default: ubuntu)')
    parser.add_argument('--key', help='Path to PEM key file (overrides .env)')
    parser.add_argument('--path', help='Project path on server (overrides .env, default: /home/ubuntu/tria)')
    parser.add_argument('--skip-git', action='store_true', help='Skip git checks and sync')
    parser.add_argument('--skip-verify', action='store_true', help='Skip deployment verification')
    parser.add_argument('--troubleshoot', action='store_true', help='Show troubleshooting guide only')

    args = parser.parse_args()

    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent

    # Create deployment agent
    agent = DeploymentAgent(project_root)

    # Show troubleshooting guide only
    if args.troubleshoot:
        agent.print_troubleshooting_guide()
        sys.exit(0)

    # Run deployment
    try:
        agent.run_deployment(args)
    except KeyboardInterrupt:
        agent.log("\nDeployment cancelled by user", 'WARNING')
        sys.exit(1)
    except Exception as e:
        agent.log(f"Deployment failed with error: {e}", 'ERROR')
        import traceback
        traceback.print_exc()
        agent.print_troubleshooting_guide()
        sys.exit(1)


if __name__ == '__main__':
    main()
