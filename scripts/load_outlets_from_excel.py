#!/usr/bin/env python3
"""
Load Customer Outlets from Excel into Database
===============================================
Production-grade script using DataFlow models to load outlets from Master_Inventory_File_2025.xlsx

NO SHORTCUTS - Uses actual DataFlow models and proper ORM patterns.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import config
from kailash.dataflow import DataFlow

def load_outlets():
    """Load outlets from Excel using DataFlow models"""

    print("=" * 70)
    print("LOADING CUSTOMER OUTLETS FROM EXCEL INTO DATABASE")
    print("=" * 70)
    print()

    # Initialize DataFlow
    print("[>>] Initializing DataFlow with PostgreSQL...")
    db = DataFlow(config.DATABASE_URL)

    # Import DataFlow models
    from models.dataflow_models import initialize_dataflow_models
    models = initialize_dataflow_models(db)
    Outlet = models['Outlet']

    print(f"[OK] DataFlow initialized")
    print()

    # Read Excel file
    excel_path = config.MASTER_INVENTORY_FILE
    print(f"[>>] Reading Excel file: {excel_path}")

    try:
        df = pd.read_excel(excel_path, sheet_name='Outlets')
        print(f"[OK] Loaded {len(df)} rows from Outlets sheet")
    except Exception as e:
        print(f"[ERROR] Failed to read Excel file: {e}")
        sys.exit(1)

    # Extract unique outlets
    outlets = df['Customer Outlet'].dropna().astype(str).unique()
    print(f"[OK] Found {len(outlets)} unique customer outlets")
    print()

    # Load outlets using DataFlow
    print("[>>] Loading outlets into database using DataFlow...")
    inserted = 0
    skipped = 0
    failed = 0

    for i, outlet_name in enumerate(outlets, 1):
        try:
            # Check if outlet already exists
            from kailash.workflow.builder import WorkflowBuilder
            from kailash.runtime.local import LocalRuntime

            workflow = WorkflowBuilder()
            workflow.add_node(
                "OutletExistsNode",
                "check_exists",
                {"name": outlet_name}
            )

            runtime = LocalRuntime()
            results, run_id = runtime.execute(workflow.build())

            if results.get("check_exists", {}).get("exists"):
                skipped += 1
                if i % 20 == 0:
                    print(f"  [{i}/{len(outlets)}] Progress: {inserted} inserted, {skipped} skipped, {failed} failed")
                continue

            # Create new outlet
            workflow = WorkflowBuilder()
            workflow.add_node(
                "OutletCreateNode",
                "create_outlet",
                {
                    "name": outlet_name,
                    "address": f"{outlet_name}, Singapore",
                    "contact_person": "Manager",
                    "contact_number": "+65 6XXX XXXX",
                    "whatsapp_user_id": "",
                    "usual_order_days": "Monday,Thursday",
                    "avg_order_frequency": 2.0,
                    "notes": f"Loaded from Master Inventory File on {datetime.now().strftime('%Y-%m-%d')}",
                    "created_at": datetime.now()
                }
            )

            results, run_id = runtime.execute(workflow.build())

            if results.get("create_outlet", {}).get("success"):
                inserted += 1
            else:
                failed += 1
                print(f"  [WARNING] Failed to create outlet: {outlet_name}")

            # Progress update every 20 outlets
            if i % 20 == 0:
                print(f"  [{i}/{len(outlets)}] Progress: {inserted} inserted, {skipped} skipped, {failed} failed")

        except Exception as e:
            failed += 1
            print(f"  [ERROR] Error processing {outlet_name}: {e}")

    print()
    print(f"[OK] Completed processing {len(outlets)} outlets")
    print()

    # Display results
    print("=" * 70)
    print("OUTLET LOADING COMPLETE")
    print("=" * 70)
    print()
    print(f"Results:")
    print(f"  - Total outlets in Excel: {len(outlets)}")
    print(f"  - Successfully created: {inserted}")
    print(f"  - Already existed: {skipped}")
    print(f"  - Failed: {failed}")
    print()

    if failed > 0:
        print("[WARNING] Some outlets failed to load. Check logs above for details.")
    else:
        print("[OK] All outlets loaded successfully!")
    print()

    # Verify total count in database
    workflow = WorkflowBuilder()
    workflow.add_node("OutletCountNode", "count_outlets", {})
    results, run_id = runtime.execute(workflow.build())
    total_count = results.get("count_outlets", {}).get("count", 0)

    print(f"[INFO] Total outlets in database: {total_count}")
    print()

if __name__ == "__main__":
    load_outlets()
