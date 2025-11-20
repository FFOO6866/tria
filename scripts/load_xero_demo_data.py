"""
Load Demo Data to Xero (REST API Version)
==========================================

This script loads customer and inventory data from the Tria database
into your Xero demo organization using direct REST API calls.

Usage:
    python scripts/load_xero_demo_data.py [--customers-only] [--products-only] [--dry-run]

Requirements:
- XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_REFRESH_TOKEN, XERO_TENANT_ID in .env
- Database connection configured in .env
- Products table populated in database

What it does:
1. Reads outlets/customers from database
2. Creates missing customers in Xero
3. Reads products from database
4. Creates missing products/items in Xero

Production-grade implementation:
- Real Xero API integration (no mocks)
- Comprehensive error handling
- Progress tracking
- Dry-run mode for testing
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from typing import List, Dict, Any
from sqlalchemy import text
import time

from database import get_db_engine
from config import config
from integrations.xero_client import get_xero_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_customers_from_database() -> List[Dict[str, Any]]:
    """Load all customers/outlets from database"""
    logger.info("Loading customers from database...")

    engine = get_db_engine(config.DATABASE_URL)

    query = text("""
        SELECT id, name, address, contact_person, contact_number
        FROM outlets
        ORDER BY name
    """)

    customers = []
    with engine.connect() as conn:
        result = conn.execute(query)
        for row in result:
            customers.append({
                'id': row[0],
                'name': row[1],
                'address': row[2] or '',
                'contact_person': row[3] or '',
                'phone': row[4] or '',
                'email': ''  # No email in database
            })

    logger.info(f"Loaded {len(customers)} customers from database")
    return customers


def load_products_from_database() -> List[Dict[str, Any]]:
    """Load all active products from database"""
    logger.info("Loading products from database...")

    engine = get_db_engine(config.DATABASE_URL)

    query = text("""
        SELECT sku, description, unit_price, uom, category, stock_quantity
        FROM products
        WHERE is_active = true
        ORDER BY sku
    """)

    products = []
    with engine.connect() as conn:
        result = conn.execute(query)
        for row in result:
            products.append({
                'sku': row[0],
                'description': row[1],
                'unit_price': float(row[2]),
                'uom': row[3],
                'category': row[4],
                'stock_quantity': int(row[5])
            })

    logger.info(f"Loaded {len(products)} products from database")
    return products


def create_customers_in_xero(customers: List[Dict[str, Any]], dry_run: bool = False):
    """
    Create customers in Xero if they don't already exist.

    Args:
        customers: List of customer dictionaries
        dry_run: If True, only show what would be created
    """
    logger.info(f"Creating customers in Xero (dry_run={dry_run})...")

    xero_client = get_xero_client()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for idx, customer in enumerate(customers, 1):
        name = customer['name']

        try:
            # Rate limiting: Stay under 60 requests/minute
            # Wait 1.2 seconds between requests (50 requests/minute max)
            if idx > 1:
                time.sleep(1.2)

            # Check if customer already exists
            existing = xero_client.verify_customer(name)

            if existing:
                logger.info(f"  ✓ Customer already exists: {name}")
                skipped_count += 1
                continue

            # Create new customer
            if dry_run:
                logger.info(f"  [DRY RUN] Would create customer: {name}")
                created_count += 1
                continue

            # Create contact in Xero via REST API
            contact_data = {
                'Name': name,
                'IsCustomer': True
            }

            # Add optional fields if available
            if customer['email']:
                contact_data['EmailAddress'] = customer['email']

            if customer['contact_person']:
                names = customer['contact_person'].split()
                contact_data['FirstName'] = names[0] if names else None
                if len(names) > 1:
                    contact_data['LastName'] = ' '.join(names[1:])

            if customer['phone']:
                contact_data['Phones'] = [{'PhoneType': 'DEFAULT', 'PhoneNumber': customer['phone']}]

            if customer['address']:
                contact_data['Addresses'] = [{'AddressType': 'STREET', 'AddressLine1': customer['address']}]

            # Make API request
            response = xero_client._make_request(
                'POST',
                '/Contacts',
                data={'Contacts': [contact_data]}
            )

            data = response.json()
            if data.get('Contacts'):
                created_contact = data['Contacts'][0]
                logger.info(f"  ✓ Created customer: {name} (ID: {created_contact['ContactID']})")
                created_count += 1
            else:
                logger.error(f"  ✗ Failed to create customer: {name}")
                error_count += 1

        except Exception as e:
            logger.error(f"  ✗ Error creating customer {name}: {e}")
            error_count += 1

    logger.info(f"\nCustomer creation summary:")
    logger.info(f"  Created: {created_count}")
    logger.info(f"  Skipped (already exists): {skipped_count}")
    logger.info(f"  Errors: {error_count}")


def create_products_in_xero(products: List[Dict[str, Any]], dry_run: bool = False):
    """
    Create products/items in Xero if they don't already exist.

    Args:
        products: List of product dictionaries
        dry_run: If True, only show what would be created
    """
    logger.info(f"Creating products in Xero (dry_run={dry_run})...")

    xero_client = get_xero_client()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for idx, product in enumerate(products, 1):
        sku = product['sku']

        try:
            # Rate limiting: Stay under 60 requests/minute
            # Wait 1.2 seconds between requests (50 requests/minute max)
            if idx > 1:
                time.sleep(1.2)

            # Check if product already exists
            existing = xero_client.check_inventory(sku)

            if existing:
                logger.info(f"  ✓ Product already exists: {sku}")
                skipped_count += 1
                continue

            # Create new product
            if dry_run:
                logger.info(f"  [DRY RUN] Would create product: {sku} - {product['description'][:50]}")
                created_count += 1
                continue

            # Create item in Xero via REST API
            # Simplified payload without inventory tracking to avoid errors
            item_data = {
                'Code': sku,
                'Name': product['description'][:50],  # Xero limits name to 50 chars
                'Description': product['description'],
                'IsSold': True,
                'IsPurchased': False,  # Simplified - just tracking sales
                'SalesDetails': {
                    'UnitPrice': product['unit_price'],
                    'AccountCode': config.XERO_SALES_ACCOUNT_CODE,
                    'TaxType': config.XERO_TAX_TYPE
                }
            }

            # Make API request
            response = xero_client._make_request(
                'POST',
                '/Items',
                data={'Items': [item_data]}
            )

            data = response.json()
            if data.get('Items'):
                created_item = data['Items'][0]
                logger.info(f"  ✓ Created product: {sku} - {product['description'][:50]}")
                created_count += 1
            else:
                logger.error(f"  ✗ Failed to create product: {sku}")
                error_count += 1

        except Exception as e:
            # Enhanced error logging - show actual response
            error_msg = str(e)
            if hasattr(e, 'response'):
                try:
                    error_details = e.response.json()
                    logger.error(f"  ✗ Error creating product {sku}: {error_details}")
                except:
                    logger.error(f"  ✗ Error creating product {sku}: {error_msg}")
            else:
                logger.error(f"  ✗ Error creating product {sku}: {error_msg}")
            error_count += 1

    logger.info(f"\nProduct creation summary:")
    logger.info(f"  Created: {created_count}")
    logger.info(f"  Skipped (already exists): {skipped_count}")
    logger.info(f"  Errors: {error_count}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Load demo data to Xero')
    parser.add_argument('--customers-only', action='store_true', help='Load only customers')
    parser.add_argument('--products-only', action='store_true', help='Load only products')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual creation)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Xero Demo Data Loader")
    logger.info("=" * 60)

    # Check Xero configuration
    if not config.xero_configured:
        logger.error("Xero is not configured!")
        logger.error("Please set XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_REFRESH_TOKEN, XERO_TENANT_ID in .env")
        sys.exit(1)

    logger.info(f"Xero Tenant ID: {config.XERO_TENANT_ID}")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info("")

    try:
        # Load customers
        if not args.products_only:
            logger.info("Step 1: Loading customers...")
            customers = load_customers_from_database()
            if customers:
                create_customers_in_xero(customers, dry_run=args.dry_run)
            else:
                logger.warning("No customers found in database")
            logger.info("")

        # Load products
        if not args.customers_only:
            logger.info("Step 2: Loading products...")
            products = load_products_from_database()
            if products:
                create_products_in_xero(products, dry_run=args.dry_run)
            else:
                logger.warning("No products found in database")
            logger.info("")

        logger.info("=" * 60)
        logger.info("Xero demo data loading completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
