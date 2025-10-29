#!/usr/bin/env python3
"""
Initialize Tria AIBPO Database with Sample Data
================================================

Loads sample outlets and products into the database for demo purposes.

NO MOCKING - Uses real DataFlow models and PostgreSQL database.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
load_dotenv(project_root / ".env")

from kailash.runtime.local import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder
from dataflow import DataFlow

print("=" * 70)
print("TRIA AIBPO DATABASE INITIALIZATION")
print("=" * 70)

# Initialize DataFlow
print("\n[>>] Initializing DataFlow...")
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("[ERROR] DATABASE_URL not found in environment")
    sys.exit(1)

db = DataFlow(
    database_url=database_url,
    skip_registry=True,
    auto_migrate=True
)

# Register models
from models.dataflow_models import initialize_dataflow_models
from models.conversation_models import initialize_conversation_models

initialize_dataflow_models(db)
initialize_conversation_models(db)

runtime = LocalRuntime()
print("[OK] DataFlow initialized with 8 models")

# Load sample outlets
print("\n[>>] Loading sample outlets...")
outlets_file = project_root / "data" / "sample_data" / "demo_outlets.json"

if not outlets_file.exists():
    print(f"[ERROR] Sample outlets file not found: {outlets_file}")
    sys.exit(1)

with open(outlets_file, 'r') as f:
    sample_outlets = json.load(f)

print(f"[OK] Found {len(sample_outlets)} sample outlets")

# Check if outlets already exist
print("\n[>>] Checking existing outlets...")
list_workflow = WorkflowBuilder()
list_workflow.add_node("OutletListNode", "list_outlets", {})
results, _ = runtime.execute(list_workflow.build())

existing_count = 0
outlet_list = results.get('list_outlets', [])
if isinstance(outlet_list, list) and len(outlet_list) > 0:
    if isinstance(outlet_list[0], dict) and 'records' in outlet_list[0]:
        existing_count = len(outlet_list[0]['records'])

print(f"[OK] Found {existing_count} existing outlets in database")

if existing_count > 0:
    print("\n[SKIP] Outlets already exist in database")
    print("       Delete existing outlets first if you want to reload sample data")
else:
    # Create outlets
    print("\n[>>] Creating sample outlets...")
    for idx, outlet_data in enumerate(sample_outlets, 1):
        workflow = WorkflowBuilder()
        workflow.add_node("OutletCreateNode", f"create_outlet_{idx}", {
            "name": outlet_data["name"],
            "address": outlet_data["address"],
            "contact_person": outlet_data["contact_person"],
            "contact_number": outlet_data["contact_number"],
            "whatsapp_user_id": outlet_data.get("whatsapp_user_id", ""),
            "usual_order_days": json.dumps(outlet_data.get("usual_order_days", [])),
            "avg_order_frequency": outlet_data.get("avg_order_frequency", 0.0)
        })

        try:
            results, _ = runtime.execute(workflow.build())
            print(f"  [{idx}/{len(sample_outlets)}] Created: {outlet_data['name']}")
        except Exception as e:
            print(f"  [{idx}/{len(sample_outlets)}] ERROR creating {outlet_data['name']}: {e}")

    print(f"[OK] Sample outlets loaded successfully")

# Load products from Excel
print("\n[>>] Checking products in database...")
products_workflow = WorkflowBuilder()
products_workflow.add_node("ProductListNode", "list_products", {"limit": 10})
results, _ = runtime.execute(products_workflow.build())

product_list = results.get('list_products', [])
product_count = 0
if isinstance(product_list, list) and len(product_list) > 0:
    if isinstance(product_list[0], dict) and 'records' in product_list[0]:
        product_count = len(product_list[0]['records'])

print(f"[OK] Found {product_count} products in database")

if product_count == 0:
    print("\n[INFO] No products found in database")
    print("       To load products, please:")
    print("       1. Ensure data/inventory/Master_Inventory_File_2025.xlsx exists")
    print("       2. Create a script to parse Excel and load into database")
    print("       3. Or manually add products via API")
else:
    print(f"[OK] Products already loaded")

# Summary
print("\n" + "=" * 70)
print("DATABASE INITIALIZATION COMPLETE")
print("=" * 70)
print(f"\nResults:")
print(f"  - Outlets in database: {existing_count if existing_count > 0 else len(sample_outlets)}")
print(f"  - Products in database: {product_count}")

print(f"\nNext steps:")
print(f"  1. Start API server: python src/enhanced_api.py")
print(f"  2. Test API: curl http://localhost:8001/health")
print(f"  3. List outlets: curl http://localhost:8001/api/outlets")

if product_count > 0:
    print(f"  4. Generate embeddings: python scripts/generate_product_embeddings.py")

print("=" * 70)
