#!/usr/bin/env python3
"""
Load Products from Excel into PostgreSQL Database
==================================================

Production-ready script to load products from Master Inventory File into database.

Features:
- Reads from Excel file (data/inventory/Master_Inventory_File_2025.xlsx)
- Extracts unique products with SKU, description, category
- Direct SQL insert for efficiency (DataFlow has issues with Decimal->text conversion)
- Checks for existing products and updates if necessary
- Progress tracking with tqdm
- Comprehensive error handling and validation
- Dry-run mode for testing
- Summary statistics

NO MOCKING - Real Excel file, real database, real SQL operations.

NOTE: Using direct SQL instead of DataFlow due to DataFlow bug where Decimal
      fields are converted to Python Decimal objects but stored as text in PostgreSQL,
      causing "expected str, got Decimal" errors.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import argparse
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Configuration
EXCEL_FILE = project_root / "data" / "inventory" / "Master_Inventory_File_2025.xlsx"
SHEET_NAME = "DataEntry"
DEFAULT_UNIT_PRICE = "10.00"  # Default price in SGD

# Column mappings
EXCEL_COLUMNS = {
    'sku': 'SKU',
    'description': 'SKU Name',
    'uom': 'Pc/Carton',
    'customer': 'Customer'
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Load products from Excel into PostgreSQL database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be loaded without actually inserting to database'
    )
    parser.add_argument(
        '--skip-update',
        action='store_true',
        help='Skip updating existing products (only create new ones)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of products to process in each batch (default: 100)'
    )
    return parser.parse_args()


def get_db_connection():
    """Get PostgreSQL database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Parse connection string
    parts = database_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    host_port = host_db[0].split(':')

    return psycopg2.connect(
        host=host_port[0],
        port=host_port[1] if len(host_port) > 1 else 5432,
        database=host_db[1],
        user=user_pass[0],
        password=user_pass[1]
    )


def extract_products_from_excel(excel_path: Path) -> pd.DataFrame:
    """
    Extract unique products from Excel file

    Args:
        excel_path: Path to Excel file

    Returns:
        DataFrame with unique products

    Raises:
        FileNotFoundError: If Excel file doesn't exist
        ValueError: If required columns are missing
    """
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    print(f"\n[>>] Reading Excel file: {excel_path.name}")
    print(f"     Sheet: {SHEET_NAME}")

    # Read Excel file
    df = pd.read_excel(excel_path, sheet_name=SHEET_NAME)

    # Validate required columns
    for col_name, excel_col in EXCEL_COLUMNS.items():
        if excel_col not in df.columns:
            raise ValueError(f"Required column '{excel_col}' not found in Excel file")

    print(f"[OK] Loaded {len(df)} rows from Excel")

    # Extract relevant columns and get unique products
    products_df = df[[
        EXCEL_COLUMNS['sku'],
        EXCEL_COLUMNS['description'],
        EXCEL_COLUMNS['uom'],
        EXCEL_COLUMNS['customer']
    ]].copy()

    # Rename columns to match our model
    products_df.columns = ['sku', 'description', 'pc_per_carton', 'customer']

    # Drop duplicates based on SKU (keep first occurrence)
    products_df = products_df.drop_duplicates(subset=['sku'], keep='first')

    # Remove rows with missing SKU or description
    initial_count = len(products_df)
    products_df = products_df.dropna(subset=['sku', 'description'])
    dropped = initial_count - len(products_df)

    if dropped > 0:
        print(f"[INFO] Dropped {dropped} rows with missing SKU or description")

    print(f"[OK] Extracted {len(products_df)} unique products")

    return products_df


def categorize_product(customer: str, description: str) -> str:
    """
    Determine product category based on customer and description

    Args:
        customer: Customer name
        description: Product description

    Returns:
        Category string
    """
    desc_lower = description.lower()

    # Category mappings based on product type
    if any(word in desc_lower for word in ['box', 'container', 'tray', 'clamshell']):
        return 'Food Boxes'
    elif any(word in desc_lower for word in ['bag', 'pouch']):
        return 'Bags & Pouches'
    elif any(word in desc_lower for word in ['paper', 'liner', 'wrapper', 'greaseproof']):
        return 'Paper Products'
    elif any(word in desc_lower for word in ['lid', 'cover', 'cap']):
        return 'Lids & Covers'
    elif any(word in desc_lower for word in ['straw', 'fork', 'knife', 'spoon', 'utensil', 'cutlery']):
        return 'Utensils & Accessories'
    elif any(word in desc_lower for word in ['cup', 'glass']):
        return 'Cups & Drinkware'
    else:
        return 'General Packaging'


def determine_uom(pc_per_carton: float, description: str) -> str:
    """
    Determine unit of measure based on product details

    Args:
        pc_per_carton: Pieces per carton
        description: Product description

    Returns:
        UOM string (piece, box, pack, carton, etc.)
    """
    desc_lower = description.lower()

    # If pc_per_carton is 1 or NaN, likely sold individually
    if pd.isna(pc_per_carton) or pc_per_carton == 1:
        return 'piece'

    # Check description for UOM hints
    if 'carton' in desc_lower:
        return 'carton'
    elif 'box' in desc_lower:
        return 'box'
    elif 'pack' in desc_lower or 'packet' in desc_lower:
        return 'pack'
    elif 'sheet' in desc_lower or 'ream' in desc_lower:
        return 'ream'
    else:
        return 'piece'


def validate_product_data(row: pd.Series) -> Tuple[bool, str]:
    """
    Validate product data before insertion

    Args:
        row: Product row from DataFrame

    Returns:
        Tuple of (is_valid, error_message)
    """
    # SKU validation
    if not row['sku'] or len(str(row['sku']).strip()) == 0:
        return False, "SKU is empty"

    # Description validation
    if not row['description'] or len(str(row['description']).strip()) == 0:
        return False, "Description is empty"

    # SKU format validation
    sku = str(row['sku']).strip()
    if len(sku) < 5:
        return False, f"SKU '{sku}' too short"

    return True, ""


def prepare_product_tuple(row: pd.Series) -> Tuple:
    """
    Prepare product tuple for database insertion

    Args:
        row: Product row from DataFrame

    Returns:
        Tuple with product fields in correct order
    """
    category = categorize_product(row['customer'] if pd.notna(row['customer']) else '', row['description'])
    uom = determine_uom(row['pc_per_carton'], row['description'])

    min_order_qty = 1
    if pd.notna(row['pc_per_carton']) and row['pc_per_carton'] > 1:
        min_order_qty = int(row['pc_per_carton'])

    notes = f"Customer: {row['customer']}" if pd.notna(row['customer']) else ""

    return (
        str(row['sku']).strip(),
        str(row['description']).strip(),
        DEFAULT_UNIT_PRICE,
        uom,
        category,
        0,  # stock_quantity
        min_order_qty,
        True,  # is_active
        notes
    )


def load_products(conn, products_df: pd.DataFrame, batch_size: int, skip_update: bool = False, dry_run: bool = False):
    """
    Load products into database

    Args:
        conn: Database connection
        products_df: DataFrame with product data
        batch_size: Batch size for inserts
        skip_update: Skip updating existing products
        dry_run: Preview without actually inserting

    Returns:
        Tuple of (created_count, updated_count, failed_count)
    """
    cur = conn.cursor()

    # Check existing products
    print("\n[>>] Checking for existing products...")
    cur.execute("SELECT sku FROM products")
    existing_skus = set(row[0] for row in cur.fetchall())
    print(f"[OK] Found {len(existing_skus)} existing products")

    # Prepare products
    print("\n[>>] Validating and preparing product data...")
    products_to_create = []
    products_to_update = []
    invalid_count = 0

    for _, row in products_df.iterrows():
        is_valid, error_msg = validate_product_data(row)

        if not is_valid:
            invalid_count += 1
            continue

        product_tuple = prepare_product_tuple(row)
        sku = product_tuple[0]

        if sku in existing_skus:
            products_to_update.append(product_tuple)
        else:
            products_to_create.append(product_tuple)

    print(f"[OK] Prepared {len(products_to_create)} new products, {len(products_to_update)} updates, {invalid_count} invalid")

    if dry_run:
        print(f"\n[DRY-RUN] Sample products to be created:")
        for i, product in enumerate(products_to_create[:5], 1):
            print(f"\n  Product {i}:")
            print(f"    SKU: {product[0]}")
            print(f"    Description: {product[1]}")
            print(f"    Category: {product[4]}")
            print(f"    UOM: {product[3]}")
            print(f"    Price: ${product[2]}")
        if len(products_to_create) > 5:
            print(f"\n  ... and {len(products_to_create) - 5} more")
        return len(products_to_create), len(products_to_update), invalid_count

    # Insert new products
    created_count = 0
    failed_count = 0

    if products_to_create:
        print(f"\n[>>] Inserting {len(products_to_create)} new products...")

        insert_sql = """
            INSERT INTO products (
                sku, description, unit_price, uom, category,
                stock_quantity, min_order_qty, is_active, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        try:
            execute_batch(cur, insert_sql, products_to_create, page_size=batch_size)
            conn.commit()
            created_count = len(products_to_create)
            print(f"[OK] Successfully created {created_count} products")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Batch insert failed: {e}")
            failed_count = len(products_to_create)

    # Update existing products
    updated_count = 0

    if products_to_update and not skip_update:
        print(f"\n[>>] Updating {len(products_to_update)} existing products...")

        update_sql = """
            UPDATE products SET
                description = %s,
                unit_price = %s,
                uom = %s,
                category = %s,
                min_order_qty = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE sku = %s
        """

        # Reorder tuple for UPDATE statement
        update_tuples = [
            (p[1], p[2], p[3], p[4], p[6], p[8], p[0])  # description, unit_price, uom, category, min_order_qty, notes, sku
            for p in products_to_update
        ]

        try:
            execute_batch(cur, update_sql, update_tuples, page_size=batch_size)
            conn.commit()
            updated_count = len(products_to_update)
            print(f"[OK] Successfully updated {updated_count} products")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Batch update failed: {e}")
            failed_count += len(products_to_update)

    cur.close()
    return created_count, updated_count, failed_count + invalid_count


def main():
    """Main execution function"""
    args = parse_args()

    print("=" * 70)
    print("LOADING PRODUCTS FROM EXCEL INTO DATABASE")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  - Excel file: {EXCEL_FILE}")
    print(f"  - Sheet: {SHEET_NAME}")
    print(f"  - Batch size: {args.batch_size}")
    print(f"  - Dry run: {args.dry_run}")
    print(f"  - Skip updates: {args.skip_update}")

    # Extract products from Excel
    try:
        products_df = extract_products_from_excel(EXCEL_FILE)
    except Exception as e:
        print(f"\n[ERROR] Failed to read Excel file: {e}")
        sys.exit(1)

    if args.dry_run:
        conn = None
        try:
            conn = get_db_connection()
            created, updated, failed = load_products(conn, products_df, args.batch_size, args.skip_update, dry_run=True)
        except Exception as e:
            print(f"\n[ERROR] Dry run failed: {e}")
            sys.exit(1)
        finally:
            if conn:
                conn.close()

        print("\n" + "=" * 70)
        print("DRY-RUN COMPLETE")
        print("=" * 70)
        print(f"\nStatistics:")
        print(f"  - Would create: {created}")
        print(f"  - Would update: {updated}")
        print(f"  - Invalid: {failed}")
        print(f"\nRun without --dry-run to actually load products into database")
        return

    # Load products
    conn = None
    try:
        conn = get_db_connection()
        created, updated, failed = load_products(conn, products_df, args.batch_size, args.skip_update)
    except Exception as e:
        print(f"\n[ERROR] Database operation failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

    # Summary
    print("\n" + "=" * 70)
    print("PRODUCT LOADING COMPLETE")
    print("=" * 70)
    print(f"\nResults:")
    print(f"  - Total products in Excel: {len(products_df)}")
    print(f"  - Successfully created: {created}")
    print(f"  - Successfully updated: {updated}")
    print(f"  - Failed/Invalid: {failed}")

    if created > 0 or updated > 0:
        print(f"\n[OK] Products loaded successfully!")
        print(f"\nNext steps:")
        print(f"  1. Generate embeddings: python scripts/generate_product_embeddings.py")
        print(f"  2. Start API server: python src/enhanced_api.py")
        print(f"  3. Verify: curl http://localhost:8001/api/products")

    if failed > 0:
        print(f"\n[WARNING] {failed} products failed or were invalid")

    print("=" * 70)


if __name__ == "__main__":
    main()
