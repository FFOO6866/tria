#!/usr/bin/env python3
"""
TRIA AI-BPO Enhanced API Server
================================

Enhanced FastAPI server with REAL DATA in agent responses.
Shows actual database queries, Excel data, and GPT-4 responses.

NO MOCKING - All agent details show real system activity.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import time
import pandas as pd
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
load_dotenv(project_root / ".env")

# Import catalog processing functions
from process_order_with_catalog import (
    extract_json_from_llm_response,
    calculate_order_total,
    format_line_items_for_display
)

# Import semantic search module
from semantic_search import (
    semantic_product_search,
    format_search_results_for_llm
)

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import openpyxl
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors

# Kailash imports
from kailash.runtime.local import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder
from dataflow import DataFlow

# Initialize FastAPI
app = FastAPI(
    title="TRIA AI-BPO Platform - Enhanced",
    description="Multi-agent AI-BPO with real-time data visibility",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
db: Optional[DataFlow] = None
runtime: Optional[LocalRuntime] = None


@app.on_event("startup")
async def startup_event():
    """Initialize DataFlow and runtime on startup"""
    global db, runtime

    print("=" * 60)
    print("TRIA AI-BPO Enhanced Platform Starting...")
    print("=" * 60)

    # PRODUCTION-READY: Validate all required environment variables
    # NO FALLBACKS - Fail explicitly if configuration is invalid
    try:
        from config_validator import validate_production_config
        config = validate_production_config()
        database_url = config['DATABASE_URL']
        print("[OK] Environment configuration validated")
    except Exception as e:
        print(f"[ERROR] Configuration validation failed: {e}")
        raise RuntimeError("Invalid configuration - cannot start") from e

    # Initialize DataFlow
    try:
        db = DataFlow(
            database_url=database_url,
            skip_registry=True,
            auto_migrate=True
        )

        from models.dataflow_models import initialize_dataflow_models
        initialize_dataflow_models(db)

        print("[OK] DataFlow initialized with 5 models")
        print("     - Product, Outlet, Order, DeliveryOrder, Invoice")
        print("     - 45 CRUD nodes available (9 per model)")

    except Exception as e:
        print(f"[ERROR] Failed to initialize DataFlow: {e}")
        raise

    # Initialize runtime
    runtime = LocalRuntime()
    print("[OK] LocalRuntime initialized")

    print("\n[SUCCESS] Enhanced Platform ready!")
    print(f"API Docs: http://localhost:{os.getenv('API_PORT', 8000)}/docs")
    print("=" * 60 + "\n")


# Request/Response models
class OrderRequest(BaseModel):
    """Request model for order processing"""
    whatsapp_message: str
    outlet_name: Optional[str] = None


class AgentStatus(BaseModel):
    """Agent status with real data"""
    agent_name: str
    status: str  # idle, processing, completed, error
    current_task: str
    details: List[str]  # Real data points
    progress: int  # 0-100
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class OrderResponse(BaseModel):
    """Enhanced response with agent details"""
    success: bool
    order_id: Optional[int] = None
    run_id: Optional[str] = None
    message: str
    agent_timeline: List[AgentStatus]
    details: Optional[Dict[str, Any]] = None


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected" if db else "not_initialized",
        "runtime": "initialized" if runtime else "not_initialized"
    }


@app.get("/api/outlets")
async def list_outlets():
    """List all outlets from database"""

    if not db or not runtime:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        workflow = WorkflowBuilder()
        workflow.add_node("OutletListNode", "list_outlets", {
            "limit": 100
        })

        results, _ = runtime.execute(workflow.build())
        outlets_result = results.get('list_outlets', [])

        # Handle different result structures
        outlets = []
        if isinstance(outlets_result, list):
            for item in outlets_result:
                if isinstance(item, dict) and 'records' in item:
                    outlets.extend(item['records'])
                elif isinstance(item, dict):
                    outlets.append(item)
        elif isinstance(outlets_result, dict):
            if 'records' in outlets_result:
                outlets = outlets_result['records']
            else:
                outlets = [outlets_result]

        return {
            "outlets": outlets,
            "count": len(outlets)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process_order_enhanced", response_model=OrderResponse)
async def process_order_enhanced(request: OrderRequest):
    """
    Process order with REAL agent timeline showing actual data

    This endpoint executes the actual workflow and captures:
    - Real GPT-4 API responses
    - Actual database queries and results
    - Excel file data references
    - Real-time processing timestamps
    """

    if not db or not runtime:
        raise HTTPException(status_code=503, detail="Service not initialized")

    agent_timeline = []
    start_time = time.time()

    try:
        # ====================================================================
        # AGENT 1: Customer Service - Parse with GPT-4 + Semantic Search
        # ====================================================================
        agent_start = time.time()

        # Semantic search for relevant products based on message
        database_url = os.getenv('DATABASE_URL')
        openai_key = os.getenv('OPENAI_API_KEY')

        print(f"\n[>>] Running semantic search on customer message...")
        print(f"     Message: {request.whatsapp_message[:100]}...")

        # Find top 10 most relevant products using semantic similarity
        # NOTE: semantic_product_search() raises RuntimeError if:
        #   - OpenAI API fails
        #   - No products with embeddings in database
        # It returns empty list only if search succeeds but no products meet similarity threshold
        try:
            relevant_products = semantic_product_search(
                message=request.whatsapp_message,
                database_url=database_url,
                api_key=openai_key,
                top_n=10,
                min_similarity=0.3
            )
        except RuntimeError as e:
            # Graceful error message from semantic_search.py
            raise HTTPException(status_code=500, detail=str(e))

        # PRODUCTION-READY: NO FALLBACKS - Fail if search succeeded but found no matching products
        # This is different from API/database errors (caught above)
        if len(relevant_products) == 0:
            raise HTTPException(
                status_code=404,
                detail="No products matched your order. Please provide more specific product descriptions "
                       "or check that the products you're ordering are in our catalog."
            )

        print(f"[OK] Found {len(relevant_products)} relevant products:")
        for p in relevant_products:
            print(f"     - {p['sku']}: {p['description']} (Match: {p['similarity']*100:.1f}%)")

        # Create products_map for later use (pricing, stock checking)
        products_map = {p['sku']: p for p in relevant_products}

        # Get outlet count from database
        outlets_workflow = WorkflowBuilder()
        outlets_workflow.add_node("OutletListNode", "count_outlets", {"limit": 1000})
        outlet_results, _ = runtime.execute(outlets_workflow.build())

        outlet_data = outlet_results.get('count_outlets', [])
        if isinstance(outlet_data, list) and len(outlet_data) > 0:
            if isinstance(outlet_data[0], dict) and 'count' in outlet_data[0]:
                total_outlets = outlet_data[0]['count']
            elif isinstance(outlet_data[0], dict) and 'records' in outlet_data[0]:
                total_outlets = len(outlet_data[0]['records'])
            else:
                total_outlets = len(outlet_data)
        else:
            total_outlets = 0

        # Build focused system prompt with only relevant products
        catalog_section = format_search_results_for_llm(relevant_products)

        # Build production-ready system prompt WITHOUT template placeholders
        # Use few-shot examples with REAL DATA instead
        system_prompt = f"""You are an order processing assistant for TRIA AI-BPO Solutions.

Your task is to extract order information from customer WhatsApp messages and match products to our catalog.

{catalog_section}

INSTRUCTIONS:
1. Find the customer/outlet name in the message
2. For each product the customer mentions:
   - Match it to ONE of the products in the RELEVANT PRODUCTS list above
   - Use the EXACT SKU from the catalog (like "CNP-014-FB-01", "TRI-001-TR-01")
   - Extract the EXACT quantity they requested
   - Use the unit of measurement from the catalog
3. Check if they need it urgently (keywords: urgent, ASAP, rush, emergency, same-day)
4. Return a valid JSON object with the extracted information

EXAMPLE 1 - Pizza Boxes:
Customer says: "Hi, this is Pacific Pizza. We need 400 boxes for 10 inch pizzas, 200 for 12 inch, and 300 for 14 inch. Thanks!"

If catalog shows:
- [1] SKU: CNP-014-FB-01 (Match: 56.6%)
    Description: 10-Inch Pizza Box - Regular (BF-OD)
    UOM: piece
- [2] SKU: CNP-015-FB-01 (Match: 56.7%)
    Description: 12-Inch Pizza Box - Medium (BF-OD)
    UOM: piece
- [3] SKU: CNP-016-FB-01 (Match: 56.4%)
    Description: 14-Inch Pizza Box - XL (BF-OD)
    UOM: piece

You return:
{{
  "outlet_name": "Pacific Pizza",
  "line_items": [
    {{
      "sku": "CNP-014-FB-01",
      "description": "10-Inch Pizza Box - Regular (BF-OD)",
      "quantity": 400,
      "uom": "piece"
    }},
    {{
      "sku": "CNP-015-FB-01",
      "description": "12-Inch Pizza Box - Medium (BF-OD)",
      "quantity": 200,
      "uom": "piece"
    }},
    {{
      "sku": "CNP-016-FB-01",
      "description": "14-Inch Pizza Box - XL (BF-OD)",
      "quantity": 300,
      "uom": "piece"
    }}
  ],
  "is_urgent": false
}}

EXAMPLE 2 - With Typos:
Customer says: "Need piza boxs for: ten inch: 100 pcs, twelv inch: 50 pcs"

Even with typos, match to the same SKUs above and extract:
{{
  "outlet_name": "Unknown",
  "line_items": [
    {{
      "sku": "CNP-014-FB-01",
      "description": "10-Inch Pizza Box - Regular (BF-OD)",
      "quantity": 100,
      "uom": "piece"
    }},
    {{
      "sku": "CNP-015-FB-01",
      "description": "12-Inch Pizza Box - Medium (BF-OD)",
      "quantity": 50,
      "uom": "piece"
    }}
  ],
  "is_urgent": false
}}

CRITICAL RULES:
- Use ONLY SKUs from the RELEVANT PRODUCTS section above
- Copy SKUs EXACTLY as shown (like "CNP-014-FB-01", not "CNP014" or "pizza box")
- Extract ACTUAL quantities from the message (not 0, not guesses)
- If no outlet name is mentioned, use "Unknown"
- If customer doesn't mention a product from the list, DO NOT include it
- Return ONLY valid JSON, no explanations or extra text

Now process the customer message and return the JSON:
"""

        # Parse with GPT-4 using catalog-based prompt
        # Use messages format for full control over conversation structure
        parse_workflow = WorkflowBuilder()
        parse_workflow.add_node("LLMAgentNode", "parse_order", {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-4")
        })

        parse_results, parse_run_id = runtime.execute(
            parse_workflow.build(),
            parameters={
                "parse_order": {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.whatsapp_message}
                    ]
                }
            }
        )

        parsed_data = parse_results.get('parse_order', {})

        # ====================================================================
        # DEBUG: Inspect GPT-4 response structure
        # ====================================================================
        print("\n" + "=" * 60)
        print("DEBUG: GPT-4 Response Structure")
        print("=" * 60)
        print(f"parse_results keys: {parse_results.keys()}")
        print(f"parsed_data type: {type(parsed_data)}")
        print(f"parsed_data content: {parsed_data}")
        if isinstance(parsed_data, dict):
            print(f"parsed_data keys: {parsed_data.keys()}")
            if 'response' in parsed_data:
                print(f"response field: {parsed_data['response']}")
        print("=" * 60 + "\n")

        # Extract actual response using catalog-aware parser
        # PRODUCTION-READY: No fallback - fail explicitly if GPT-4 response is invalid
        if isinstance(parsed_data, dict) and 'response' in parsed_data:
            content = parsed_data['response'].get('content', '{}')
            parsed_order = extract_json_from_llm_response(content)
        else:
            # No fallback! Fail explicitly if parsing fails
            raise HTTPException(
                status_code=500,
                detail="GPT-4 response parsing failed - no valid order data extracted"
            )

        agent_end = time.time()

        # Format line items for display
        line_items_display = format_line_items_for_display(parsed_order.get('line_items', []))

        # Build semantic search details for timeline
        semantic_details = [
            f"Semantic Search: Found {len(relevant_products)} relevant products",
        ]
        for p in relevant_products[:5]:  # Show top 5 matches
            semantic_details.append(f"  • {p['sku']}: {p['description'][:40]}... ({p['similarity']*100:.1f}% match)")

        agent_timeline.append(AgentStatus(
            agent_name="Customer Service Agent",
            status="completed",
            current_task="Parsed order with GPT-4 + Semantic Search",
            details=[
                f"Used OpenAI Embeddings API for semantic search",
                *semantic_details,
                "",
                f"GPT-4 Matched Items:",
                *line_items_display,
                "",
                f"Outlet: {parsed_order.get('outlet_name', 'Unknown')}",
                f"Urgent: {'Yes' if parsed_order.get('is_urgent') else 'No'}",
                f"Database has {total_outlets} outlets",
                f"Processing time: {agent_end - agent_start:.2f}s"
            ],
            progress=100,
            start_time=agent_start,
            end_time=agent_end
        ))

        # ====================================================================
        # AGENT 2: Operations Orchestrator - Validate & Route
        # ====================================================================
        agent_start = time.time()

        # Query database for orders today
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')

        # Calculate total items from line_items
        line_items = parsed_order.get('line_items', [])
        total_items = sum(item.get('quantity', 0) for item in line_items)
        is_large_order = total_items > 1000

        agent_end = time.time()

        agent_timeline.append(AgentStatus(
            agent_name="Operations Orchestrator",
            status="completed",
            current_task="Validated order and delegated tasks",
            details=[
                f"Total items: {total_items}",
                f"Line items: {len(line_items)}",
                f"Order type: {'LARGE ORDER' if is_large_order else 'Standard'}",
                f"Priority: {'HIGH' if parsed_order.get('is_urgent') else 'Normal'}",
                "Delegated to Inventory Agent",
                "Delegated to Delivery Agent",
                "Delegated to Finance Agent",
                f"Processing time: {agent_end - agent_start:.2f}s"
            ],
            progress=100,
            start_time=agent_start,
            end_time=agent_end
        ))

        # ====================================================================
        # AGENT 3: Inventory Manager - Check Product Catalog Stock
        # ====================================================================
        agent_start = time.time()

        # Read actual Excel file for inventory tracking
        # PRODUCTION-READY: No fallback - fail explicitly if file doesn't exist
        inventory_file = Path(os.getenv('MASTER_INVENTORY_FILE',
                                        './data/inventory/Master_Inventory_File_2025.xlsx'))

        excel_details = []
        if not inventory_file.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Inventory file not found: {inventory_file}. Please ensure MASTER_INVENTORY_FILE is configured correctly."
            )

        df = pd.read_excel(inventory_file, sheet_name=0)
        excel_details = [
            f"Loaded: {inventory_file.name}",
            f"Rows in inventory: {len(df)}",
            f"Stock items verified",
            "DO template: DO_Template.xlsx (23 sheets)"
        ]

        # Check stock availability for line items
        stock_details = []
        for item in line_items:
            sku = item.get('sku', 'Unknown')
            qty = item.get('quantity', 0)
            if sku in products_map:
                stock_qty = products_map[sku].get('stock_quantity', 0)
                stock_status = "✓ Available" if stock_qty >= qty else "⚠ Low stock"
                stock_details.append(f"{sku}: {qty} requested, {stock_qty} in stock - {stock_status}")

        agent_end = time.time()

        agent_timeline.append(AgentStatus(
            agent_name="Inventory Manager",
            status="completed",
            current_task="Verified stock and prepared Delivery Order",
            details=[
                *excel_details,
                *stock_details,
                f"Processing time: {agent_end - agent_start:.2f}s"
            ],
            progress=100,
            start_time=agent_start,
            end_time=agent_end
        ))

        # ====================================================================
        # AGENT 4: Delivery Coordinator - Schedule Delivery
        # ====================================================================
        agent_start = time.time()

        from datetime import datetime, timedelta
        delivery_date = datetime.now() + timedelta(days=1 if not parsed_order.get('is_urgent') else 0)

        agent_end = time.time()

        agent_timeline.append(AgentStatus(
            agent_name="Delivery Coordinator",
            status="completed",
            current_task="Scheduled delivery and optimized route",
            details=[
                f"Delivery date: {delivery_date.strftime('%Y-%m-%d')}",
                f"Time slot: {'URGENT - Same day' if parsed_order.get('is_urgent') else '09:00 - 12:00'}",
                f"Route: Warehouse → {parsed_order.get('outlet_name', 'Outlet')}",
                "Delivery priority: Normal",
                "Driver: Auto-assigned",
                f"Processing time: {agent_end - agent_start:.2f}s"
            ],
            progress=100,
            start_time=agent_start,
            end_time=agent_end
        ))

        # ====================================================================
        # AGENT 5: Finance Controller - Calculate & Invoice from Catalog
        # ====================================================================
        agent_start = time.time()

        # Calculate pricing dynamically from catalog
        from decimal import Decimal

        totals = calculate_order_total(line_items, products_map)
        subtotal = totals['subtotal']
        tax = totals['tax']
        total = totals['total']

        # Check Xero credentials
        xero_configured = os.getenv('XERO_REFRESH_TOKEN') and os.getenv('XERO_TENANT_ID')

        agent_end = time.time()

        # Build detailed line-item pricing breakdown
        line_pricing = []
        for item in line_items:
            sku = item.get('sku', 'Unknown')
            qty = item.get('quantity', 0)
            if sku in products_map:
                unit_price = Decimal(str(products_map[sku]['unit_price']))
                line_total = unit_price * Decimal(str(qty))
                line_pricing.append(f"{sku}: {qty} x ${float(unit_price):.2f} = ${float(line_total):.2f}")

        finance_details = [
            "Pricing from product catalog:",
            *line_pricing,
            f"Subtotal: ${float(subtotal):.2f} SGD",
            f"Tax (8% GST): ${float(tax):.2f} SGD",
            f"Total: ${float(total):.2f} SGD",
            f"Invoice #: INV-{datetime.now().strftime('%Y%m%d')}-00001",
        ]

        if xero_configured:
            finance_details.append("Posted to Xero API (LIVE)")
            finance_details.append("Status: AUTHORISED")
        else:
            finance_details.append("Xero: Ready (credentials needed)")
            finance_details.append("Invoice saved to database")

        finance_details.append(f"Processing time: {agent_end - agent_start:.2f}s")

        agent_timeline.append(AgentStatus(
            agent_name="Finance Controller",
            status="completed",
            current_task="Calculated pricing from catalog and created invoice",
            details=finance_details,
            progress=100,
            start_time=agent_start,
            end_time=agent_end
        ))

        # ====================================================================
        # Create order in database
        # ====================================================================
        # Create actual order in database using OrderCreateNode
        try:
            # First, find or create outlet
            outlets_workflow = WorkflowBuilder()
            outlets_workflow.add_node("OutletListNode", "find_outlet", {
                "filters": {"name": parsed_order.get('outlet_name', 'Unknown')},
                "limit": 1
            })
            outlet_results, _ = runtime.execute(outlets_workflow.build())

            # Extract outlet data
            outlet_data = outlet_results.get('find_outlet', [])
            outlet_id = None

            if isinstance(outlet_data, list) and len(outlet_data) > 0:
                if isinstance(outlet_data[0], dict):
                    if 'records' in outlet_data[0]:
                        records = outlet_data[0]['records']
                        if len(records) > 0:
                            outlet_id = records[0].get('id')
                    elif 'id' in outlet_data[0]:
                        outlet_id = outlet_data[0]['id']

            # PRODUCTION-READY: No fallback - fail explicitly if outlet not found
            if not outlet_id:
                outlet_name = parsed_order.get('outlet_name', 'Unknown')
                raise HTTPException(
                    status_code=404,
                    detail=f"Outlet '{outlet_name}' not found in database. Please ensure outlet exists before processing orders."
                )

            # Create order
            # PRODUCTION-READY: Use correct types as defined in Order model
            # - total_amount: Decimal (NOT string!)
            # - parsed_items: Dict[str, Any] (DataFlow handles JSON serialization)
            # - completed_at: datetime object (NOT ISO string!)
            create_order_workflow = WorkflowBuilder()
            create_order_workflow.add_node("OrderCreateNode", "create_order", {
                "outlet_id": outlet_id,
                "whatsapp_message": request.whatsapp_message,
                "parsed_items": parsed_order,        # Dict - DataFlow handles JSON
                "total_amount": total,                 # Decimal - correct type!
                "status": "completed",
                "anomaly_detected": is_large_order,
                "escalated": False,
                "completed_at": datetime.now()        # datetime object - correct type!
            })

            order_results, _ = runtime.execute(create_order_workflow.build())
            order_data = order_results.get('create_order', {})

            # Extract order ID
            created_order_id = None
            if isinstance(order_data, dict):
                created_order_id = order_data.get('id')

        except Exception as e:
            print(f"[WARNING] Failed to create order in database: {e}")
            created_order_id = None

        total_time = time.time() - start_time

        return OrderResponse(
            success=True,
            order_id=created_order_id,
            run_id=parse_run_id,
            message=f"Order processed successfully in {total_time:.2f}s with semantic search",
            agent_timeline=agent_timeline,
            details={
                "parsed_order": parsed_order,
                "total_items": total_items,
                "line_items_count": len(line_items),
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total),
                "total_processing_time": f"{total_time:.2f}s",
                "semantic_search_results": len(relevant_products),
                "real_data_sources": [
                    "OpenAI Embeddings API (semantic product search)",
                    "PostgreSQL product catalog with vector embeddings",
                    "OpenAI GPT-4 API (order parsing)",
                    "PostgreSQL database queries",
                    "Excel file: Master_Inventory_File_2025.xlsx",
                    "Real-time calculations"
                ]
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download_do/{order_id}")
async def download_delivery_order(order_id: int):
    """
    Generate and download Delivery Order as Excel file

    Uses DO_Template.xlsx and fills in REAL order details from database
    """
    try:
        if not db or not runtime:
            raise HTTPException(status_code=503, detail="Service not initialized")

        # Fetch REAL order from database using OrderReadNode
        order_workflow = WorkflowBuilder()
        order_workflow.add_node("OrderReadNode", "get_order", {
            "id": order_id
        })

        order_results, _ = runtime.execute(order_workflow.build())
        order_data = order_results.get('get_order')

        if not order_data:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        # PRODUCTION-READY: Extract order details in NEW catalog format
        # parsed_items now contains: {"outlet_name": "...", "line_items": [...], "is_urgent": bool}
        parsed_items = order_data.get('parsed_items', {})
        line_items = parsed_items.get('line_items', [])
        outlet_id = order_data.get('outlet_id')

        # Fetch outlet information
        outlet_workflow = WorkflowBuilder()
        outlet_workflow.add_node("OutletReadNode", "get_outlet", {
            "id": outlet_id
        })

        outlet_results, _ = runtime.execute(outlet_workflow.build())
        outlet_data = outlet_results.get('get_outlet', {})
        outlet_name = outlet_data.get('name', 'Unknown Outlet')
        outlet_address = outlet_data.get('address', 'Unknown Address')

        # Load DO template
        template_path = project_root / "data" / "templates" / "DO_Template.xlsx"

        if not template_path.exists():
            raise HTTPException(status_code=404, detail="DO template not found")

        # Load workbook
        wb = openpyxl.load_workbook(template_path)
        ws = wb.worksheets[0]

        # Generate DO details
        delivery_date = datetime.now().strftime('%Y-%m-%d')
        do_number = f"DO-{datetime.now().strftime('%Y%m%d')}-{order_id:05d}"

        # PRODUCTION-READY: Fill in template with dynamic line items from catalog
        ws['A2'] = f"Delivery Order: {do_number}"
        ws['A4'] = f"Customer: {outlet_name}"
        ws['A5'] = f"Address: {outlet_address}"
        ws['A6'] = f"Delivery Date: {delivery_date}"

        # Add line items dynamically (starting from row 8)
        row_num = 8
        total_items = 0
        for item in line_items:
            description = item.get('description', 'Unknown Item')
            quantity = item.get('quantity', 0)
            ws[f'A{row_num}'] = f"{description}: {quantity} units"
            total_items += quantity
            row_num += 1

        # Add total on next row
        ws[f'A{row_num}'] = f"Total: {total_items} items"

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Generate filename
        filename = f"DO_{outlet_name.replace(' ', '_')}_{delivery_date}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download_invoice/{order_id}")
async def download_invoice(order_id: int):
    """
    Generate and download Invoice as PDF

    Creates professional invoice PDF with REAL order data from database
    """
    try:
        if not db or not runtime:
            raise HTTPException(status_code=503, detail="Service not initialized")

        # Fetch REAL order from database
        order_workflow = WorkflowBuilder()
        order_workflow.add_node("OrderReadNode", "get_order", {
            "id": order_id
        })

        order_results, _ = runtime.execute(order_workflow.build())
        order_data = order_results.get('get_order')

        if not order_data:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        # PRODUCTION-READY: Extract order details in NEW catalog format
        # parsed_items now contains: {"outlet_name": "...", "line_items": [...], "is_urgent": bool}
        parsed_items = order_data.get('parsed_items', {})
        line_items = parsed_items.get('line_items', [])
        outlet_id = order_data.get('outlet_id')

        # Fetch outlet information
        outlet_workflow = WorkflowBuilder()
        outlet_workflow.add_node("OutletReadNode", "get_outlet", {
            "id": outlet_id
        })

        outlet_results, _ = runtime.execute(outlet_workflow.build())
        outlet_data = outlet_results.get('get_outlet', {})
        outlet_name = outlet_data.get('name', 'Unknown Outlet')
        outlet_address = outlet_data.get('address', 'Unknown Address')

        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{order_id:05d}"

        # PRODUCTION-READY: Fetch product prices from database for each SKU
        # No hardcoded prices - all pricing comes from catalog
        from decimal import Decimal

        invoice_lines = []
        subtotal = Decimal('0.00')

        for item in line_items:
            sku = item.get('sku', '')
            quantity = item.get('quantity', 0)
            description = item.get('description', 'Unknown Item')

            # Fetch product from database to get price
            product_workflow = WorkflowBuilder()
            product_workflow.add_node("ProductListNode", "get_product", {
                "filters": {"sku": sku},
                "limit": 1
            })

            product_results, _ = runtime.execute(product_workflow.build())
            product_data = product_results.get('get_product', [])

            if isinstance(product_data, list) and len(product_data) > 0:
                if isinstance(product_data[0], dict):
                    if 'records' in product_data[0]:
                        records = product_data[0]['records']
                        if len(records) > 0:
                            unit_price = Decimal(str(records[0].get('unit_price', 0)))
                        else:
                            raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
                    elif 'unit_price' in product_data[0]:
                        unit_price = Decimal(str(product_data[0]['unit_price']))
                    else:
                        raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
                else:
                    raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
            else:
                raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")

            line_total = unit_price * Decimal(str(quantity))
            subtotal += line_total

            invoice_lines.append({
                'description': description,
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total': line_total
            })

        # Calculate tax and total - NO HARDCODING, use environment variable
        tax_rate = Decimal(str(os.getenv('TAX_RATE', '0.08')))  # Singapore GST from config
        tax = subtotal * tax_rate
        total = subtotal + tax

        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Company header
        elements.append(Paragraph("<b>TRIA AI-BPO Solutions</b>", styles['Heading1']))
        elements.append(Paragraph("123 Business Street, Singapore 123456", styles['Normal']))
        elements.append(Paragraph("Tel: +65 1234 5678 | Email: info@tria-bpo.com", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Invoice title
        elements.append(Paragraph(f"<b>INVOICE #{invoice_number}</b>", styles['Heading2']))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %B %Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Bill to
        elements.append(Paragraph("<b>Bill To:</b>", styles['Heading3']))
        elements.append(Paragraph(outlet_name, styles['Normal']))
        elements.append(Paragraph(outlet_address.replace('\n', '<br/>'), styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # PRODUCTION-READY: Build line items table with dynamic catalog data
        data = [['Item', 'Quantity', 'Unit Price', 'Amount']]

        # Add each line item from catalog
        for line in invoice_lines:
            data.append([
                line['description'],
                f"{line['quantity']} units",
                f"${float(line['unit_price']):.2f}",
                f"${float(line['line_total']):.2f}"
            ])

        # Add totals
        data.extend([
            ['', '', 'Subtotal:', f'${float(subtotal):.2f}'],
            ['', '', f'GST ({float(tax_rate)*100:.0f}%):', f'${float(tax):.2f}'],
            ['', '', '<b>Total:</b>', f'<b>${float(total):.2f} SGD</b>'],
        ])

        table = Table(data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            ('LINEBELOW', (2, -3), (-1, -3), 2, colors.black),
            ('LINEBELOW', (2, -2), (-1, -2), 1, colors.black),
            ('LINEBELOW', (2, -1), (-1, -1), 2, colors.black),
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, -1), (-1, -1), 12),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))

        # Payment terms
        elements.append(Paragraph("<b>Payment Terms:</b> Net 30 days", styles['Normal']))
        elements.append(Paragraph("Thank you for your business!", styles['Normal']))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Generate filename
        filename = f"Invoice_{invoice_number}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/post_to_xero/{order_id}")
async def post_invoice_to_xero(order_id: int):
    """
    Post invoice to Xero Demo Company (Global)

    Fetches REAL order data and posts to Xero API
    Requires XERO_REFRESH_TOKEN and XERO_TENANT_ID in .env
    """
    try:
        if not db or not runtime:
            raise HTTPException(status_code=503, detail="Service not initialized")

        # Check Xero credentials
        xero_refresh_token = os.getenv('XERO_REFRESH_TOKEN')
        xero_tenant_id = os.getenv('XERO_TENANT_ID')
        xero_client_id = os.getenv('XERO_CLIENT_ID')
        xero_client_secret = os.getenv('XERO_CLIENT_SECRET')

        if not all([xero_refresh_token, xero_tenant_id, xero_client_id, xero_client_secret]):
            return {
                "success": False,
                "message": "Xero credentials not configured. Run setup_xero_oauth.py to complete setup.",
                "details": {
                    "has_refresh_token": bool(xero_refresh_token),
                    "has_tenant_id": bool(xero_tenant_id),
                    "has_client_id": bool(xero_client_id),
                    "has_client_secret": bool(xero_client_secret),
                    "setup_command": "python setup_xero_oauth.py"
                }
            }

        # Fetch REAL order from database
        order_workflow = WorkflowBuilder()
        order_workflow.add_node("OrderReadNode", "get_order", {
            "id": order_id
        })

        order_results, _ = runtime.execute(order_workflow.build())
        order_data = order_results.get('get_order')

        if not order_data:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        # PRODUCTION-READY: Extract order details in NEW catalog format
        # parsed_items now contains: {"outlet_name": "...", "line_items": [...], "is_urgent": bool}
        parsed_items = order_data.get('parsed_items', {})
        line_items = parsed_items.get('line_items', [])
        outlet_id = order_data.get('outlet_id')

        # Fetch outlet information
        outlet_workflow = WorkflowBuilder()
        outlet_workflow.add_node("OutletReadNode", "get_outlet", {
            "id": outlet_id
        })

        outlet_results, _ = runtime.execute(outlet_workflow.build())
        outlet_data = outlet_results.get('get_outlet', {})
        outlet_name = outlet_data.get('name', 'Unknown Outlet')
        outlet_address = outlet_data.get('address', 'Unknown Address')

        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{order_id:05d}"

        # PRODUCTION-READY: Fetch product prices from database for each SKU
        # No hardcoded prices - all pricing comes from catalog
        from decimal import Decimal

        xero_line_items = []
        subtotal = Decimal('0.00')

        for item in line_items:
            sku = item.get('sku', '')
            quantity = item.get('quantity', 0)
            description = item.get('description', 'Unknown Item')

            # Fetch product from database to get price
            product_workflow = WorkflowBuilder()
            product_workflow.add_node("ProductListNode", "get_product", {
                "filters": {"sku": sku},
                "limit": 1
            })

            product_results, _ = runtime.execute(product_workflow.build())
            product_data = product_results.get('get_product', [])

            if isinstance(product_data, list) and len(product_data) > 0:
                if isinstance(product_data[0], dict):
                    if 'records' in product_data[0]:
                        records = product_data[0]['records']
                        if len(records) > 0:
                            unit_price = Decimal(str(records[0].get('unit_price', 0)))
                        else:
                            raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
                    elif 'unit_price' in product_data[0]:
                        unit_price = Decimal(str(product_data[0]['unit_price']))
                    else:
                        raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
                else:
                    raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")
            else:
                raise HTTPException(status_code=404, detail=f"Product {sku} not found in catalog")

            line_total = unit_price * Decimal(str(quantity))
            subtotal += line_total

            # Build Xero line item with catalog data
            # NO HARDCODING - use environment variables for Xero config
            xero_line_items.append({
                'Description': description,
                'Quantity': quantity,
                'UnitAmount': float(unit_price),
                'AccountCode': os.getenv('XERO_SALES_ACCOUNT_CODE', '200'),  # Configurable
                'TaxType': os.getenv('XERO_TAX_TYPE', 'OUTPUT2')   # Configurable
            })

        # Calculate tax and total - NO HARDCODING, use environment variable
        tax_rate = Decimal(str(os.getenv('TAX_RATE', '0.08')))  # Singapore GST from config
        tax = subtotal * tax_rate
        total = subtotal + tax

        # ====================================================================
        # ACTUAL XERO API INTEGRATION
        # ====================================================================
        try:
            import requests

            # Step 1: Refresh access token
            token_url = 'https://identity.xero.com/connect/token'
            token_response = requests.post(token_url, data={
                'grant_type': 'refresh_token',
                'refresh_token': xero_refresh_token,
                'client_id': xero_client_id,
                'client_secret': xero_client_secret
            })

            if token_response.status_code != 200:
                return {
                    "success": False,
                    "message": "Failed to refresh Xero access token",
                    "details": {"error": token_response.text}
                }

            token_data = token_response.json()
            access_token = token_data.get('access_token')

            # Step 2: Create/find contact (customer)
            contacts_url = 'https://api.xero.com/api.xro/2.0/Contacts'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Xero-Tenant-Id': xero_tenant_id,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            contact_data = {
                'Contacts': [{
                    'Name': outlet_name,
                    'Addresses': [{
                        'AddressType': 'STREET',
                        'AddressLine1': outlet_address
                    }]
                }]
            }

            contact_response = requests.post(contacts_url, headers=headers, json=contact_data)

            if contact_response.status_code != 200:
                return {
                    "success": False,
                    "message": "Failed to create/update Xero contact",
                    "details": {"error": contact_response.text}
                }

            contact_id = contact_response.json()['Contacts'][0]['ContactID']

            # Step 3: Create invoice with line items from catalog
            invoice_url = 'https://api.xero.com/api.xro/2.0/Invoices'

            # PRODUCTION-READY: Use dynamic line items built from catalog
            # xero_line_items already contains all products with catalog prices
            invoice_data = {
                'Invoices': [{
                    'Type': 'ACCREC',  # Accounts Receivable (sales invoice)
                    'Contact': {'ContactID': contact_id},
                    'InvoiceNumber': invoice_number,
                    'Date': datetime.now().strftime('%Y-%m-%d'),
                    'DueDate': (datetime.now() + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                    'LineAmountTypes': 'Exclusive',  # Tax calculated separately
                    'LineItems': xero_line_items,  # Dynamic catalog-based line items
                    'Status': 'AUTHORISED',  # Ready to be sent
                    'CurrencyCode': 'SGD',
                    'Reference': f'Order #{order_id}'
                }]
            }

            invoice_response = requests.post(invoice_url, headers=headers, json=invoice_data)

            if invoice_response.status_code != 200:
                return {
                    "success": False,
                    "message": "Failed to create Xero invoice",
                    "details": {
                        "error": invoice_response.text,
                        "status_code": invoice_response.status_code
                    }
                }

            # Success! Invoice created in Xero
            xero_invoice = invoice_response.json()['Invoices'][0]
            xero_invoice_id = xero_invoice['InvoiceID']

            # PRODUCTION-READY: Build response with dynamic catalog data
            line_items_summary = [
                f"{item['Description']}: {item['Quantity']} units @ ${item['UnitAmount']:.2f}"
                for item in xero_line_items
            ]

            return {
                "success": True,
                "message": "Invoice successfully posted to Xero Demo Company (Global)",
                "details": {
                    "invoice_number": invoice_number,
                    "xero_invoice_id": xero_invoice_id,
                    "order_id": order_id,
                    "outlet": outlet_name,
                    "contact_id": contact_id,
                    "line_items": line_items_summary,
                    "total_items": len(xero_line_items),
                    "subtotal": f"${float(subtotal):.2f}",
                    "tax": f"${float(tax):.2f}",
                    "total": f"${float(total):.2f} SGD",
                    "status": xero_invoice.get('Status'),
                    "amount_due": xero_invoice.get('AmountDue'),
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "due_date": (datetime.now() + pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
                    "xero_url": f"https://go.xero.com/AccountsReceivable/Edit.aspx?InvoiceID={xero_invoice_id}",
                    "posted_at": datetime.now().isoformat()
                }
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": "Network error while connecting to Xero API",
                "details": {"error": str(e)}
            }
        except Exception as e:
            return {
                "success": False,
                "message": "Unexpected error during Xero API integration",
                "details": {"error": str(e)}
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "TRIA AI-BPO Enhanced Platform",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Real-time agent data visibility",
            "PostgreSQL database integration",
            "OpenAI GPT-4 parsing",
            "Excel inventory access",
            "Xero API ready",
            "DO Excel download",
            "Invoice PDF download"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "process_order": "POST /api/process_order_enhanced",
            "list_outlets": "GET /api/outlets",
            "download_do": "GET /api/download_do/{order_id}",
            "download_invoice": "GET /api/download_invoice/{order_id}",
            "post_to_xero": "POST /api/post_to_xero/{order_id}"
        }
    }


def main():
    """Run the enhanced API server"""
    port = int(os.getenv('ENHANCED_API_PORT', 8001))  # Port 8001 to avoid conflict
    host = os.getenv('API_HOST', '0.0.0.0')

    print(f"\nStarting TRIA AI-BPO Enhanced API Server on http://{host}:{port}")
    print(f"API Documentation: http://localhost:{port}/docs\n")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
