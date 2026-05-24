import os
import subprocess
import re

os.chdir("/home/workspace/ledgersg")

# 1. Investigate Custom Pagination
print("--- CUSTOM PAGINATION IMPLEMENTATION ---")
wrap_response_grep = subprocess.run(["grep", "-rn", "wrap_response", "apps/backend/common/"], capture_output=True, text=True)
print("wrap_response definition:")
print(wrap_response_grep.stdout[:1000] if wrap_response_grep.stdout else "Not found")

# Check if list views manually format {results, count}
banking_views_content = ""
if os.path.exists("apps/backend/apps/banking/views.py"):
    with open("apps/backend/apps/banking/views.py", 'r') as f:
        banking_views_content = f.read()
        
# Look for 'results' and 'count' in the get method of BankAccountListView
match = re.search(r'class BankAccountListView.*?def get\(self, request.*?return Response\((.*?)\)', banking_views_content, re.DOTALL)
if match:
    print("\nBankAccountListView GET return payload:")
    print(match.group(1)[:500])

# 2. Investigate BaseModel and Ghost Columns
print("\n--- BASE MODEL DEFINITION ---")
base_model_grep = subprocess.run(["grep", "-A", "15", "class BaseModel", "apps/backend/common/models.py"], capture_output=True, text=True)
print(base_model_grep.stdout if base_model_grep.stdout else "BaseModel not found")

# 3. Check database_schema.sql for timestamp columns on a TenantModel table
print("\n--- SCHEMA TIMESTAMP CHECK ---")
schema_path = "apps/backend/database_schema.sql"
if os.path.exists(schema_path):
    with open(schema_path, 'r') as f:
        schema = f.read()
        # Check core.contact (which inherits TenantModel)
        match = re.search(r'CREATE TABLE core\.contact \((.*?)\);', schema, re.DOTALL)
        if match:
            print("core.contact table definition (truncated):")
            print(match.group(1)[:800])
        else:
            print("core.contact table not found with regex, trying broader search...")
            contact_idx = schema.find("CREATE TABLE core.contact")
            if contact_idx != -1:
                print(schema[contact_idx:contact_idx+600])

# 4. Check the 67 failing tests file to confirm the RLS context issue
print("\n--- FAILING TESTS FILE ANALYSIS ---")
test_file = "apps/backend/tests/test_api_endpoints.py"
if os.path.exists(test_file):
    with open(test_file, 'r') as f:
        content = f.read()
        if "current_org_id" in content or "RLS" in content:
            print("Test file contains RLS context setup.")
        else:
            print("Test file LACKS RLS context setup. This confirms the 403 bug root cause.")
            print("First 500 chars of test file:")
            print(content[:500])

 # Result 
--- CUSTOM PAGINATION IMPLEMENTATION ---
wrap_response definition:
apps/backend/common/views.py:16:def wrap_response(func: Callable) -> Callable:
apps/backend/common/views.py:28:    @wrap_response
Binary file apps/backend/common/__pycache__/views.cpython-312.pyc matches


BankAccountListView GET return payload:
{"results": serializer.data, "count": len(serializer.data

--- BASE MODEL DEFINITION ---
class BaseModel(models.Model):
    """
    Abstract base model with UUID primary key and timestamps.
    
    All models in the system inherit from this class.
    Uses unmanaged models since schema is DDL-managed.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="id",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,


--- SCHEMA TIMESTAMP CHECK ---
core.contact table not found with regex, trying broader search...

--- FAILING TESTS FILE ANALYSIS ---
Test file LACKS RLS context setup. This confirms the 403 bug root cause.
First 500 chars of test file:
"""
LedgerSG API Endpoint Test Suite

Comprehensive tests for all 53 API endpoints.
Run with: pytest tests/test_api_endpoints.py -v

Requirements:
- Database must be running with schema applied
- Redis must be running
- Django server should NOT be running (tests use test client)
"""

import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client
from django.contrib.auth.hashers import make_password
from rest_framework.test import APICli
