"""
Tria AIBPO - External Integrations Module

This module provides integration clients for external services:
- Xero: Accounting and financial management (OAuth2.0, API client, workflow orchestrator)
- Future: Twilio, SendGrid, WhatsApp Business, etc.
"""

from .xero_client import XeroClient, get_xero_client
from .xero_order_orchestrator import XeroOrderOrchestrator, get_xero_orchestrator

__all__ = [
    'XeroClient',
    'get_xero_client',
    'XeroOrderOrchestrator',
    'get_xero_orchestrator'
]
