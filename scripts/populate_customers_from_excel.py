"""
Populate Customers/Outlets from Excel Data
==========================================

Reads the actual customer-outlet structure from Master_Inventory_File_2025.xlsx
and creates realistic outlet data with Singapore addresses, contact persons, and phone numbers.

Then loads to both database and Xero.

Usage:
    python scripts/populate_customers_from_excel.py [--load-to-xero]
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
import pandas as pd
import random
from typing import List, Dict, Any
from sqlalchemy import text

from database import get_db_engine
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Singapore location data for realistic addresses
SINGAPORE_ADDRESSES = {
    # Malls and landmarks
    "Jewel": "78 Airport Boulevard, Jewel Changi Airport",
    "Jurong Point": "1 Jurong West Central 2, Jurong Point",
    "Bugis": "201 Victoria Street, Bugis Junction",
    "Century Square": "2 Tampines Central 5, Century Square",
    "Hillion": "17 Petir Road, Hillion Mall",
    "Orchard": "290 Orchard Road, Paragon Shopping Centre",
    "Suntec City": "3 Temasek Boulevard, Suntec City Mall",
    "Tampines": "4 Tampines Central 5, Tampines Mall",
    "Waterway Point": "83 Punggol Central, Waterway Point",
    "Westgate": "3 Gateway Drive, Westgate",
    "Plaza Sing": "68 Orchard Road, Plaza Singapura",
    "MBS": "10 Bayfront Avenue, Marina Bay Sands",
    "Vivo": "1 Harbourfront Walk, VivoCity",
    "Bedok Mall": "311 New Upper Changi Road, Bedok Mall",
    "Causeway Point": "1 Woodlands Square, Causeway Point",
    "Novena": "238 Thomson Road, Novena Square",
    "City Square Mall": "180 Kitchener Road, City Square Mall",
    "Lucky Plaza": "304 Orchard Road, Lucky Plaza",

    # Neighborhoods/Towns
    "Anchorvale Village": "326 Anchorvale Road",
    "Canberra": "133 Canberra View",
    "Mandai Lake": "80 Mandai Lake Road",
    "Northshore": "418 Northshore Drive",
    "Bedok": "210 New Upper Changi Road",
    "Bukit Batok": "2 Bukit Batok Street 24",
    "Bukit Timah": "587 Bukit Timah Road",
    "Changi Road": "850 Changi Road",
    "Choa Chu Kang": "21 Choa Chu Kang Avenue 4",
    "Jurong West": "497 Jurong West Street 41",
    "Kampung Bahru": "3 Kampong Bahru Road",
    "Kim Keat": "123 Kim Keat Avenue",
    "Kovan": "209 Hougang Street 21",
    "Pandan Crescent": "450 Pandan Gardens",
    "Pasir Ris": "1 Pasir Ris Central Street 3",
    "Punggol": "168 Punggol Field",
    "Serangoon Gardens": "49 Serangoon Garden Way",
    "Toa Payoh": "126 Lorong 1 Toa Payoh",
    "Woodlands": "768 Woodlands Avenue 6",
    "Yishun": "51 Yishun Avenue 11",
    "Clementi": "3155 Commonwealth Avenue West",
    "Bukit Merah": "115 Bukit Merah View",
    "Ang Mo Kio Hub": "53 Ang Mo Kio Avenue 3",
    "Bishan": "9 Bishan Place, Junction 8",
    "King Albert Park": "130 Bukit Timah Road",
    "Paya Lebar": "1 Paya Lebar Link",
    "Sembawang": "604 Sembawang Road",
    "Fusionpolis": "1 Fusionopolis Way",
    "Aperia": "12 Kallang Avenue, Aperia",
    "Tai Seng": "3 Irving Road, Tai Seng",
    "Sims Drive": "10 Jalan Besar",

    # Special locations
    "HQ": "8 Pandan Crescent, FLOW SERVICES PTE LTD HQ",
    "Central Kitchen": "15 Kaki Bukit Road 1, Central Kitchen",
    "Changi Warehouse": "50 Loyang Way, Changi Warehouse",
    "NUS": "21 Lower Kent Ridge Road, NUS",
    "GWC": "3 Gateway Drive, GWC Building",
    "Lazada One": "51 Bras Basah Road, Lazada One",
}


# Contact person name pools (Singapore-appropriate names)
FIRST_NAMES = [
    "David", "Emily", "Michael", "Sarah", "Daniel", "Jessica", "Ryan", "Amanda",
    "Wei Ming", "Li Ying", "Raj", "Priya", "Ahmad", "Fatimah", "Kumar", "Siti"
]

LAST_NAMES = [
    "Tan", "Lee", "Lim", "Ng", "Teo", "Wong", "Chan", "Chua",
    "Kumar", "Singh", "Rahman", "Abdullah", "Chen", "Wang", "Ho", "Goh"
]


def generate_singapore_phone():
    """Generate realistic Singapore phone number"""
    # Singapore mobile: +65 8XXX XXXX or 9XXX XXXX
    prefix = random.choice(['8', '9'])
    number = f"{prefix}{random.randint(1000000, 9999999)}"
    return f"+65 {number[:4]} {number[4:]}"


def generate_contact_person():
    """Generate realistic contact person name"""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def get_address_for_location(location: str) -> str:
    """
    Get Singapore address for a location name.
    Uses best match from known addresses or generates generic one.
    """
    location_lower = location.lower()

    # Direct match
    for key, address in SINGAPORE_ADDRESSES.items():
        if key.lower() in location_lower or location_lower in key.lower():
            return address

    # Generic address for unknown locations
    block = random.randint(1, 999)
    street = random.choice(["Street", "Avenue", "Road", "Drive"])
    number = random.randint(1, 99)
    return f"{block} {location} {street} {number}, Singapore"


def extract_customers_from_excel(excel_file: str) -> List[Dict[str, Any]]:
    """
    Extract customer-outlet data from Master Inventory Excel file

    Returns:
        List of outlet dictionaries with customer, outlet, address, contact, phone
    """
    logger.info(f"Reading customer data from {excel_file}...")

    # Read DataEntry sheet
    df = pd.read_excel(excel_file, sheet_name='DataEntry')

    # Get unique customer-outlet combinations
    customer_outlets = df[['Customer', 'Customer Outlet']].dropna().drop_duplicates()
    customer_outlets = customer_outlets.sort_values(['Customer', 'Customer Outlet'])

    logger.info(f"Found {len(customer_outlets)} unique customer-outlet combinations")

    # Generate complete outlet data
    outlets = []
    for _, row in customer_outlets.iterrows():
        customer = row['Customer']
        outlet_location = row['Customer Outlet']

        # Create outlet name: "Customer - Location"
        outlet_name = f"{customer} - {outlet_location}"

        # Generate realistic data
        address = get_address_for_location(outlet_location)
        contact_person = generate_contact_person()
        phone = generate_singapore_phone()

        outlets.append({
            'name': outlet_name,
            'customer_brand': customer,
            'location': outlet_location,
            'address': address,
            'contact_person': contact_person,
            'contact_number': phone
        })

    logger.info(f"Generated {len(outlets)} outlet records")
    return outlets


def insert_outlets_to_database(outlets: List[Dict[str, Any]]):
    """Insert outlet data into database"""
    logger.info("Inserting outlets into database...")

    engine = get_db_engine(config.DATABASE_URL)

    # Clear existing outlets
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE outlets RESTART IDENTITY CASCADE"))
        conn.commit()
        logger.info("Cleared existing outlets")

    # Insert new outlets
    with engine.connect() as conn:
        for outlet in outlets:
            query = text("""
                INSERT INTO outlets (name, address, contact_person, contact_number)
                VALUES (:name, :address, :contact_person, :contact_number)
            """)

            conn.execute(query, {
                'name': outlet['name'],
                'address': outlet['address'],
                'contact_person': outlet['contact_person'],
                'contact_number': outlet['contact_number']
            })

        conn.commit()

    logger.info(f"✓ Inserted {len(outlets)} outlets into database")


def load_customers_to_xero(outlets: List[Dict[str, Any]], dry_run: bool = False):
    """Load customer contacts to Xero"""
    from integrations.xero_client import get_xero_client
    import time

    logger.info(f"Loading customers to Xero (dry_run={dry_run})...")

    xero_client = get_xero_client()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for idx, outlet in enumerate(outlets, 1):
        name = outlet['name']

        try:
            # Rate limiting: 1.2 seconds between requests
            if idx > 1:
                time.sleep(1.2)

            # Check if customer already exists
            existing = xero_client.verify_customer(name)

            if existing:
                logger.info(f"  ✓ Customer already exists: {name}")
                skipped_count += 1
                continue

            if dry_run:
                logger.info(f"  [DRY RUN] Would create customer: {name}")
                created_count += 1
                continue

            # Create contact in Xero
            contact_data = {
                'Name': name,
                'IsCustomer': True
            }

            # Add contact person as FirstName/LastName
            if outlet['contact_person']:
                names = outlet['contact_person'].split()
                contact_data['FirstName'] = names[0] if names else None
                if len(names) > 1:
                    contact_data['LastName'] = ' '.join(names[1:])

            # Add phone
            if outlet['contact_number']:
                contact_data['Phones'] = [{
                    'PhoneType': 'DEFAULT',
                    'PhoneNumber': outlet['contact_number']
                }]

            # Add address
            if outlet['address']:
                contact_data['Addresses'] = [{
                    'AddressType': 'STREET',
                    'AddressLine1': outlet['address']
                }]

            # Make API request
            response = xero_client._make_request(
                'POST',
                '/Contacts',
                data={'Contacts': [contact_data]}
            )

            data = response.json()
            if data.get('Contacts'):
                created_contact = data['Contacts'][0]
                logger.info(f"  ✓ Created customer: {name}")
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


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Populate customers from Excel')
    parser.add_argument('--load-to-xero', action='store_true', help='Also load to Xero')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Customer/Outlet Population from Excel")
    logger.info("=" * 60)

    excel_file = config.MASTER_INVENTORY_FILE
    if not os.path.exists(excel_file):
        logger.error(f"Excel file not found: {excel_file}")
        sys.exit(1)

    try:
        # Step 1: Extract from Excel
        outlets = extract_customers_from_excel(excel_file)

        # Show summary
        logger.info("\nCustomer Summary:")
        logger.info("-" * 60)
        customers = {}
        for outlet in outlets:
            brand = outlet['customer_brand']
            if brand not in customers:
                customers[brand] = []
            customers[brand].append(outlet['location'])

        for customer, locations in sorted(customers.items()):
            logger.info(f"{customer}: {len(locations)} branches")

        logger.info(f"\nTotal: {len(customers)} customers, {len(outlets)} outlets")
        logger.info("")

        # Step 2: Insert to database
        if not args.dry_run:
            insert_outlets_to_database(outlets)
        else:
            logger.info("[DRY RUN] Skipping database insert")

        # Step 3: Load to Xero (optional)
        if args.load_to_xero:
            load_customers_to_xero(outlets, dry_run=args.dry_run)

        logger.info("\n" + "=" * 60)
        logger.info("Customer population completed!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
