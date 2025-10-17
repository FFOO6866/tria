@echo off
REM TRIA AI-BPO Frontend Setup Script
REM Automates installation and configuration

echo ============================================
echo TRIA AI-BPO Frontend Setup
echo ============================================
echo.

REM Check Node.js installation
echo [1/4] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found:
node --version
echo.

REM Check npm installation
echo [2/4] Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found!
    pause
    exit /b 1
)
echo [OK] npm found:
npm --version
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
echo This may take a few minutes...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully
echo.

REM Setup environment file
echo [4/4] Setting up environment...
if not exist .env.local (
    copy .env.local.example .env.local
    echo [OK] Created .env.local from template
) else (
    echo [OK] .env.local already exists
)
echo.

echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Start backend: python src/simple_api.py
echo 2. Start frontend: npm run dev
echo 3. Open browser: http://localhost:3000
echo.
echo Run "npm run dev" to start the development server
echo.
pause
