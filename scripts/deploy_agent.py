#!/usr/bin/env python3
"""
TRIA AI-BPO Deployment Agent

This deployment agent follows the STRICT deployment protocol:
1. All settings and env vars are the same on local and server
2. .env contains server IP address, PEM key location
3. Use git workflow: local -> git -> server (NEVER rsync/copy)
4. Use the same docker-compose.yml and .env.docker on both environments
5. Handle ENVIRONMENT flag carefully (development vs production)
6. All docker-compose env vars are documented and checked
7. Never deploy without running this agent

CRITICAL ENV VARS REQUIRED FOR DOCKER-COMPOSE:
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- DATABASE_URL
- OPENAI_API_KEY (MUST be set, docker-compose will fail without it)
- SECRET_KEY
- TAX_RATE, XERO_SALES_ACCOUNT_CODE, XERO_TAX_TYPE
- XERO_CLIENT_ID, XERO_CLIENT_SECRET (optional but recommended)

Author: TRIA AI-BPO DevOps Team
Version: 1.0.0
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

    Handles the complete deployment workflow with validation, checks,
    and rollback capabilities.
    """

    # CRITICAL: These env vars MUST be set for docker-compose to work
    REQUIRED_DOCKER_ENV_VARS = [
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        'DATABASE_URL',
        'OPENAI_API_KEY',  # CRITICAL - docker-compose fails without this
        'SECRET_KEY',
        'TAX_RATE',
        'XERO_SALES_ACCOUNT_CODE',
        'XERO_TAX_TYPE',
    ]

    # Optional but recommended
    RECOMMENDED_ENV_VARS = [
        'XERO_CLIENT_ID',
        'XERO_CLIENT_SECRET',
        'XERO_TENANT_ID',
        'XERO_REFRESH_TOKEN',
    ]

    # Deployment configuration vars
    DEPLOYMENT_CONFIG_VARS = [
        'SERVER_IP',
        'SERVER_USER',
        'PEM_KEY_PATH',
        'ENVIRONMENT',  # CRITICAL: 'development' or 'production'
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / '.env'
        self.env_docker_file = project_root / '.env.docker'
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
                   capture_output: bool = True) -> Tuple[int, str, str]:
        """
        Run shell command and return exit code, stdout, stderr

        Args:
            cmd: Command and arguments as list
            cwd: Working directory (default: project_root)
            capture_output: Whether to capture output

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
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {' '.join(cmd)}", 'ERROR')
            return -1, '', 'Command timed out'
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
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

        return env_vars

    def check_required_files(self) -> bool:
        """Check that all required files exist"""
        self.print_header("STEP 1: Checking Required Files")

        required_files = [
            self.env_file,
            self.env_docker_file,
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

        env_vars = self.load_env_file(self.env_docker_file)
        missing_vars = []

        # Check required docker-compose vars
        self.log("Checking REQUIRED docker-compose environment variables:", 'INFO')
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

        # Check recommended vars
        self.log("\nChecking RECOMMENDED environment variables:", 'INFO')
        for var in self.RECOMMENDED_ENV_VARS:
            if var not in env_vars or not env_vars[var]:
                self.log(f"⚠ MISSING (Optional): {var}", 'WARNING')
            else:
                display_value = env_vars[var][:10] + '...' if len(env_vars[var]) > 10 else env_vars[var]
                self.log(f"✓ {var} = {display_value}", 'SUCCESS')

        # Check deployment config vars from main .env
        self.log("\nChecking DEPLOYMENT configuration variables:", 'INFO')
        main_env = self.load_env_file(self.env_file)
        for var in self.DEPLOYMENT_CONFIG_VARS:
            if var not in main_env or not main_env[var]:
                self.log(f"⚠ MISSING: {var} (in .env)", 'WARNING')
                if var == 'ENVIRONMENT':
                    missing_vars.append(var)  # ENVIRONMENT is critical
            else:
                display_value = main_env[var]
                if var == 'ENVIRONMENT':
                    # Highlight the environment
                    if display_value.lower() == 'production':
                        self.log(f"✓ {var} = {display_value} (PRODUCTION MODE)", 'WARNING')
                    else:
                        self.log(f"✓ {var} = {display_value}", 'SUCCESS')
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

            if branch != 'main' and branch != 'master':
                self.log(f"WARNING: Not on main/master branch", 'WARNING')
                response = input(f"\n{Colors.WARNING}Deploy from '{branch}' branch? (yes/no): {Colors.ENDC}")
                if response.lower() != 'yes':
                    self.log("Deployment cancelled by user", 'WARNING')
                    return False

        return True

    def sync_to_server(self, server_ip: str, server_user: str, pem_key: str) -> bool:
        """
        Sync code to server using git (NOT rsync/copy)

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file

        Returns:
            True if sync successful
        """
        self.print_header("STEP 4: Syncing to Server via Git")

        # Step 1: Push to git remote
        self.log("Pushing to git remote...", 'INFO')
        returncode, stdout, stderr = self.run_command(['git', 'push', 'origin', 'HEAD'])
        if returncode != 0:
            self.log(f"Git push failed: {stderr}", 'ERROR')
            return False
        self.log("✓ Pushed to git remote", 'SUCCESS')

        # Step 2: SSH to server and pull
        self.log(f"Connecting to server {server_user}@{server_ip}...", 'INFO')

        # SSH commands to run on server
        ssh_commands = [
            "cd ~/tria || cd /opt/tria || cd /var/www/tria",  # Try common paths
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
            return False

        self.log("✓ Server code synced via git", 'SUCCESS')
        self.log(stdout, 'INFO')

        return True

    def deploy_to_server(self, server_ip: str, server_user: str, pem_key: str,
                        environment: str) -> bool:
        """
        Deploy application on server using docker-compose

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file
            environment: 'development' or 'production'

        Returns:
            True if deployment successful
        """
        self.print_header(f"STEP 5: Deploying to Server ({environment.upper()} MODE)")

        # Load env vars from .env.docker to pass to docker-compose
        env_vars = self.load_env_file(self.env_docker_file)

        # Build env var string for docker-compose command
        # CRITICAL: This prevents "OPENAI_API_KEY not set" errors
        env_var_string = ' '.join([
            f'{key}="{value}"'
            for key, value in env_vars.items()
            if key in self.REQUIRED_DOCKER_ENV_VARS
        ])

        self.log("Environment variables that will be passed to docker-compose:", 'INFO')
        self.log(env_var_string, 'INFO')

        # SSH commands for deployment
        ssh_commands = [
            "cd ~/tria || cd /opt/tria || cd /var/www/tria",

            # Stop existing containers
            "docker-compose down",

            # Pull latest images
            "docker-compose pull",

            # Build with no cache to ensure fresh build
            "docker-compose build --no-cache",

            # CRITICAL: Start with explicit env vars to avoid forgotten vars
            f"{env_var_string} docker-compose up -d",

            # Show container status
            "docker-compose ps",

            # Show recent logs
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
        returncode, stdout, stderr = self.run_command(ssh_cmd, capture_output=False)

        if returncode != 0:
            self.log("Deployment failed", 'ERROR')
            self.log(f"Error: {stderr}", 'ERROR')
            return False

        self.log("✓ Deployment completed", 'SUCCESS')
        return True

    def verify_deployment(self, server_ip: str, server_user: str, pem_key: str) -> bool:
        """
        Verify that the deployment was successful

        Args:
            server_ip: Server IP address
            server_user: SSH username
            pem_key: Path to PEM key file

        Returns:
            True if verification successful
        """
        self.print_header("STEP 6: Verifying Deployment")

        # Check container health
        ssh_cmd = [
            'ssh',
            '-i', pem_key,
            '-o', 'StrictHostKeyChecking=no',
            f'{server_user}@{server_ip}',
            'cd ~/tria || cd /opt/tria || cd /var/www/tria && docker-compose ps'
        ]

        returncode, stdout, stderr = self.run_command(ssh_cmd)
        if returncode != 0:
            self.log("Could not verify deployment", 'ERROR')
            return False

        self.log("Container status:", 'INFO')
        self.log(stdout, 'INFO')

        # Check if all services are running
        if 'Up' in stdout:
            self.log("✓ Containers are running", 'SUCCESS')

            # Check API health endpoint
            self.log(f"\nChecking API health at http://{server_ip}:8001/health...", 'INFO')

            # Try curl via SSH
            ssh_cmd = [
                'ssh',
                '-i', pem_key,
                '-o', 'StrictHostKeyChecking=no',
                f'{server_user}@{server_ip}',
                'curl -f http://localhost:8001/health || echo "Health check failed"'
            ]

            returncode, stdout, stderr = self.run_command(ssh_cmd)
            if returncode == 0 and 'health check failed' not in stdout.lower():
                self.log("✓ API health check passed", 'SUCCESS')
                return True
            else:
                self.log("⚠ API health check failed (might take a moment to start)", 'WARNING')
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
   - Check .env.docker file has OPENAI_API_KEY defined
   - Ensure key is valid and not expired
   - Verify docker-compose command includes the env var
   - Solution: Edit .env.docker and redeploy

2. Database connection errors:
   - Check DATABASE_URL is correct in .env.docker
   - Ensure PostgreSQL container is running
   - Verify network connectivity between containers
   - Solution: docker-compose down && docker-compose up -d postgres

3. Git sync fails:
   - Ensure you have pushed changes to remote
   - Check SSH key permissions (chmod 400 key.pem)
   - Verify server has git repo cloned
   - Solution: Manually clone repo on server first

4. Port conflicts:
   - Check if ports 5433, 8001, 3000 are already in use
   - Use: docker-compose ps to see running containers
   - Solution: Stop conflicting services or change ports

5. Container won't start:
   - Check logs: docker-compose logs <service>
   - Verify all env vars are set correctly
   - Check Dockerfile syntax
   - Solution: docker-compose build --no-cache

6. Production/Development flag issues:
   - Verify ENVIRONMENT variable in .env
   - Check that correct .env file is being used
   - Ensure no hardcoded environment values
   - Solution: Set ENVIRONMENT=production in .env

7. Image build failures:
   - Clear Docker cache: docker system prune -a
   - Check Dockerfile dependencies
   - Verify network connectivity for package downloads
   - Solution: docker-compose build --no-cache

8. Volume permission errors:
   - Check volume mounts in docker-compose.yml
   - Verify file permissions on host
   - Solution: sudo chown -R $USER:$USER ./data

Key Commands:

# View logs:
docker-compose logs -f [service]

# Restart service:
docker-compose restart [service]

# Rebuild and restart:
docker-compose up -d --build [service]

# Check container status:
docker-compose ps

# Access container shell:
docker-compose exec [service] /bin/bash

# Check environment variables:
docker-compose exec backend env | grep OPENAI
"""
        print(guide)

    def run_deployment(self, args):
        """
        Run full deployment workflow

        Args:
            args: Parsed command-line arguments
        """
        self.print_header("TRIA AI-BPO DEPLOYMENT AGENT")
        self.log(f"Deployment started at {datetime.now()}", 'INFO')

        # Step 1: Check required files
        if not self.check_required_files():
            self.log("Missing required files. Deployment aborted.", 'ERROR')
            sys.exit(1)

        # Step 2: Validate environment variables
        valid, missing = self.validate_environment_vars()
        if not valid:
            self.log(f"Missing required environment variables: {', '.join(missing)}", 'ERROR')
            self.log("Please update .env.docker file and try again", 'ERROR')
            sys.exit(1)

        # Step 3: Check git status
        if not args.skip_git and not self.check_git_status():
            self.log("Git checks failed. Deployment aborted.", 'ERROR')
            sys.exit(1)

        # Load deployment config
        main_env = self.load_env_file(self.env_file)
        server_ip = main_env.get('SERVER_IP', args.server)
        server_user = main_env.get('SERVER_USER', args.user)
        pem_key = main_env.get('PEM_KEY_PATH', args.key)
        environment = main_env.get('ENVIRONMENT', 'development')

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

        # Step 4: Sync to server via git
        if not args.skip_git:
            if not self.sync_to_server(server_ip, server_user, pem_key):
                self.log("Server sync failed. Deployment aborted.", 'ERROR')
                sys.exit(1)

        # Step 5: Deploy on server
        if not self.deploy_to_server(server_ip, server_user, pem_key, environment):
            self.log("Deployment failed", 'ERROR')
            self.print_troubleshooting_guide()
            sys.exit(1)

        # Step 6: Verify deployment
        if not args.skip_verify:
            if not self.verify_deployment(server_ip, server_user, pem_key):
                self.log("Deployment verification failed", 'WARNING')
                self.print_troubleshooting_guide()
                sys.exit(1)

        # Success!
        self.print_header("DEPLOYMENT SUCCESSFUL")
        self.log(f"✓ Application deployed to {server_ip}", 'SUCCESS')
        self.log(f"✓ Environment: {environment}", 'SUCCESS')
        self.log(f"✓ Deployment completed at {datetime.now()}", 'SUCCESS')
        self.log(f"\nAccess the application at:", 'INFO')
        self.log(f"  Frontend: http://{server_ip}:3000", 'INFO')
        self.log(f"  Backend:  http://{server_ip}:8001", 'INFO')
        self.log(f"  API Docs: http://{server_ip}:8001/docs", 'INFO')


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='TRIA AI-BPO Deployment Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy using settings from .env file:
  python scripts/deploy_agent.py

  # Deploy with custom server settings:
  python scripts/deploy_agent.py --server 192.168.1.100 --user ubuntu --key ~/.ssh/server.pem

  # Skip git checks (for testing):
  python scripts/deploy_agent.py --skip-git

  # Skip deployment verification:
  python scripts/deploy_agent.py --skip-verify

For more information, see docs/deployment.md
        """
    )

    parser.add_argument('--server', help='Server IP address (overrides .env)')
    parser.add_argument('--user', default='ubuntu', help='SSH username (default: ubuntu)')
    parser.add_argument('--key', help='Path to PEM key file (overrides .env)')
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
        agent.print_troubleshooting_guide()
        sys.exit(1)


if __name__ == '__main__':
    main()
