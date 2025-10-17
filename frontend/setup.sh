#!/bin/bash
# TRIA AI-BPO Frontend Setup Script
# Automates installation and configuration

set -e

echo "============================================"
echo "TRIA AI-BPO Frontend Setup"
echo "============================================"
echo ""

# Check Node.js installation
echo "[1/4] Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found!"
    echo "Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi
echo "[OK] Node.js found:"
node --version
echo ""

# Check npm installation
echo "[2/4] Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm not found!"
    exit 1
fi
echo "[OK] npm found:"
npm --version
echo ""

# Install dependencies
echo "[3/4] Installing dependencies..."
echo "This may take a few minutes..."
npm install
echo "[OK] Dependencies installed successfully"
echo ""

# Setup environment file
echo "[4/4] Setting up environment..."
if [ ! -f .env.local ]; then
    cp .env.local.example .env.local
    echo "[OK] Created .env.local from template"
else
    echo "[OK] .env.local already exists"
fi
echo ""

echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Start backend: python src/simple_api.py"
echo "2. Start frontend: npm run dev"
echo "3. Open browser: http://localhost:3000"
echo ""
echo "Run 'npm run dev' to start the development server"
echo ""
