#!/bin/bash
################################################################################
# Xero Configuration Script
################################################################################
# This script configures Xero credentials on the server
#
# Usage:
#   ./scripts/configure_xero.sh
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Xero Configuration Setup${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Navigate to app directory
cd /home/ubuntu/tria

echo "Updating .env file with Xero credentials..."

# Backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Backed up .env${NC}"

# Update or add Xero credentials
if grep -q "XERO_CLIENT_ID=" .env; then
    sed -i 's/XERO_CLIENT_ID=.*/XERO_CLIENT_ID=C7626087206C452B9A36A16BE915C891/' .env
else
    echo "XERO_CLIENT_ID=C7626087206C452B9A36A16BE915C891" >> .env
fi

if grep -q "XERO_CLIENT_SECRET=" .env; then
    sed -i 's/XERO_CLIENT_SECRET=.*/XERO_CLIENT_SECRET=CNcpQzdcfaho7UuEHajoLZ-Pa7ykMqaTjaGOE-S4Q6OPJnpE/' .env
else
    echo "XERO_CLIENT_SECRET=CNcpQzdcfaho7UuEHajoLZ-Pa7ykMqaTjaGOE-S4Q6OPJnpE" >> .env
fi

if grep -q "XERO_WEBHOOK_KEY=" .env; then
    sed -i 's|XERO_WEBHOOK_KEY=.*|XERO_WEBHOOK_KEY=pXo0Xjhd1VZabcWo+pUt03ByB7DbH822uRMpds4NyxQaK4yAxH4e3o1WYa7W/Cgkvfl+tDCo4aId59e0TYjjfA==|' .env
else
    echo "XERO_WEBHOOK_KEY=pXo0Xjhd1VZabcWo+pUt03ByB7DbH822uRMpds4NyxQaK4yAxH4e3o1WYa7W/Cgkvfl+tDCo4aId59e0TYjjfA==" >> .env
fi

if grep -q "XERO_REDIRECT_URI=" .env; then
    sed -i 's|XERO_REDIRECT_URI=.*|XERO_REDIRECT_URI=https://tria.himeet.ai/api/xero/callback|' .env
else
    echo "XERO_REDIRECT_URI=https://tria.himeet.ai/api/xero/callback" >> .env
fi

echo -e "${GREEN}✓ Updated .env with Xero credentials${NC}"
echo ""

echo -e "${YELLOW}Next step: Get OAuth tokens${NC}"
echo ""
echo "Run: python scripts/get_xero_tokens.py"
echo ""
echo "Then add XERO_REFRESH_TOKEN and XERO_TENANT_ID to .env"
echo ""
