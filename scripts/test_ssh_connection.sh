#!/bin/bash
# SSH Connection Test Script
# This script helps you test and diagnose SSH connectivity

set -e

echo "======================================"
echo "SSH Connection Test"
echo "======================================"
echo ""

# Configuration
SERVER_IP="13.214.14.130"
SERVER_USER="${1:-ubuntu}"  # Default to ubuntu, or use first argument
PEM_KEY_PATH="${2:-}"       # Optional PEM key path

echo "Testing connection to: $SERVER_USER@$SERVER_IP"
echo ""

# Test 1: Can we reach the server?
echo "[Test 1/5] Checking if server is reachable..."
if ping -c 3 $SERVER_IP &> /dev/null; then
    echo "✅ Server is reachable"
else
    echo "❌ Server is not reachable - check IP address or network"
    exit 1
fi
echo ""

# Test 2: Is SSH port open?
echo "[Test 2/5] Checking if SSH port (22) is open..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$SERVER_IP/22" 2>/dev/null; then
    echo "✅ SSH port is open"
else
    echo "❌ SSH port is not accessible - firewall may be blocking"
    exit 1
fi
echo ""

# Test 3: Try SSH connection
echo "[Test 3/5] Testing SSH connection..."
if [ -n "$PEM_KEY_PATH" ]; then
    echo "Using PEM key: $PEM_KEY_PATH"
    SSH_CMD="ssh -i \"$PEM_KEY_PATH\" -o ConnectTimeout=10 -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP"
else
    echo "Using password authentication (you'll be prompted)"
    SSH_CMD="ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP"
fi

echo "Running: $SSH_CMD whoami"
echo ""

if $SSH_CMD "whoami" 2>&1; then
    echo ""
    echo "✅ SSH connection successful!"
else
    echo ""
    echo "❌ SSH connection failed"
    echo ""
    echo "Common issues:"
    echo "1. Wrong username (try: ubuntu, ec2-user, root)"
    echo "2. Wrong PEM key path"
    echo "3. PEM key permissions (should be 400)"
    echo "4. Server doesn't allow password authentication"
    echo ""
    echo "Try:"
    echo "  ./test_ssh_connection.sh ubuntu /path/to/key.pem"
    echo "  ./test_ssh_connection.sh ec2-user /path/to/key.pem"
    exit 1
fi
echo ""

# Test 4: Check if Docker is installed
echo "[Test 4/5] Checking if Docker is installed on server..."
if $SSH_CMD "docker --version" 2>&1; then
    echo "✅ Docker is installed"
else
    echo "❌ Docker is not installed or not in PATH"
fi
echo ""

# Test 5: Check if tria directory exists
echo "[Test 5/5] Checking if tria directory exists..."
if $SSH_CMD "[ -d ~/tria ] && echo 'exists' || [ -d /opt/tria ] && echo 'exists' || [ -d /home/ubuntu/tria ] && echo 'exists'" | grep -q "exists"; then
    echo "✅ Tria directory found"
    $SSH_CMD "find ~ /opt /home/ubuntu -maxdepth 2 -name tria -type d 2>/dev/null | head -1" | while read dir; do
        echo "   Location: $dir"
    done
else
    echo "⚠️  Tria directory not found in common locations"
    echo "   You may need to clone the repository first"
fi
echo ""

echo "======================================"
echo "✅ Connection Test Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. SSH into server:"
echo "   $SSH_CMD"
echo ""
echo "2. Navigate to tria directory"
echo "3. Pull latest code:"
echo "   git pull origin main"
echo ""
echo "4. Run deployment:"
echo "   ./scripts/comprehensive_deploy.sh"
echo ""
