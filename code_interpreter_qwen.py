import os
import subprocess

# 1. Clone the repo
repo_url = "https://github.com/nordeim/ledgersg.git"
if not os.path.exists("ledgersg"):
    result = subprocess.run(["git", "clone", repo_url], capture_output=True, text=True)
    print("Clone output:", result.stderr)

if os.path.exists("ledgersg"):
    os.chdir("ledgersg")
    print("Current dir:", os.getcwd())
    print("Files:", os.listdir("."))
    
    # 2. Check Schema & ORM Alignment
    print("\n--- SCHEMA & ORM ALIGNMENT ---")
    unmanaged_count = 0
    managed_count = 0
    for root, dirs, files in os.walk("apps/backend/apps"):
        for file in files:
            if file.endswith(".py") and "models" in root:
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                    if "managed = False" in content:
                        unmanaged_count += 1
                    elif "class Meta:" in content and "managed = False" not in content:
                        managed_count += 1
    print(f"Files with 'managed = False': {unmanaged_count}")
    print(f"Files with 'class Meta:' but NO 'managed = False': {managed_count}")

    # 3. Financial Precision Sweep
    print("\n--- FINANCIAL PRECISION SWEEP ---")
    float_usage = subprocess.run(["grep", "-rnw", "apps/backend", "-e", "FloatField", "-e", "float("], capture_output=True, text=True)
    print("FloatField / float() usage:")
    print(float_usage.stdout if float_usage.stdout else "None found (Good!)")

    # 4. RLS & Middleware Verification
    print("\n--- RLS MIDDLEWARE ---")
    middleware_path = "apps/backend/common/middleware/tenant_context.py"
    if os.path.exists(middleware_path):
        with open(middleware_path, 'r') as f:
            print(f.read()[:1000])
    else:
        print("Middleware file not found at expected path.")

    # 5. Ghost Column Check (TenantModel)
    print("\n--- GHOST COLUMN CHECK (TenantModel) ---")
    tenant_model_grep = subprocess.run(["grep", "-rn", "TenantModel", "apps/backend/apps"], capture_output=True, text=True)
    print("TenantModel usages:")
    print(tenant_model_grep.stdout[:1000] if tenant_model_grep.stdout else "None found")

    # 6. Testing & Fixture Isolation (The 403 Bug)
    print("\n--- TEST FIXTURE ISOLATION ---")
    conftest_path = "apps/backend/conftest.py"
    if os.path.exists(conftest_path):
        with open(conftest_path, 'r') as f:
            content = f.read()
            print(content[:1000])
    else:
        print("conftest.py not found in backend root.")

else:
    print("Failed to clone repository or directory not created.")

 # Result 
Clone output: Cloning into 'ledgersg'...

Current dir: /home/workspace/ledgersg
Files: ['PAD_UPDATE_COMPLETE.md', 'GEMINI.md', 'AUTHENTICATION_REMEDIATION_PROGRESS.md', 'README_v2.md', 'apps', 'DASHBOARD_LOADING_ISSUE_DIAGNOSIS.md', 'PAD_2.md', 'E2E_FRONTEND_TEST_PLAN.md', 'frontend_login.png', 'test_setup_seed_data.py', 'Phase3_AP_Integration_TDD_SubPlan.md', 'API_workflow_examples_and_tips_guide.md', 'TDD_RLS_FIX_PLAN.md', 'start_apps.sh', 'start_backend_log.txt', 'Current_Project_Status_0311.md', 'LedgerSG_E2E_Executive_Summary.md', 'Phase2_SchemaFixes_TDD_SubPlan.md', 'RLS_FIX_VALIDATION_REPORT.md', 'Current_Project_Status.md', 'FINAL_ACCOMPLISHMENT_SUMMARY.md', 'e2e_test_phases_7_15_simplified.py', 'E2E_TESTING_EXPERIENCE_REPORT.md', 'INTEGRATION_REMEDIATION_COMPLETE.md', 'Code_Review_Audit_20260524.md', 'COMPREHENSIVE_README_VALIDATION_REPORT.md', 'AUTHENTICATION_FLOW_REMEDIATION_PLAN.md', 'status_14.md', 'GEMINI_old.md', 'InvoiceNow_Implementation_Plan_Updated.md', 'AUTHENTICATION_REMEDIATION_COMPLETE.md', 'PAD_UPDATE_PLAN.md', 'API_CLI_Usage_Guide.md', 'debug_ledger.py', 'README_UPDATE_SUMMARY.md', 'docs', 'Phase2_SchemaFix_TDD_SubPlan.md', 'CORS_COMREHENSIVE_VALIDATED_REMEDIATION_PLAN.md', 'UUID_PATTERNS_GUIDE.md', 'Agent-Browser-howto.md', 'GEMINI.temp', 'TDD_RLS_FIXES_SUBPLAN.md', 'TDD_IMPLEMENTATION_REPORT.md', 'InvoiceNow_Implementation_Validation_Report.md', 'startup_log.txt', 'E2E_TEST_FINDINGS.md', 'requirements.txt', '.gitignore', 'sample_guide_for_reference.md', 'API_WORKFLOW_END_TO_END_REPORT.md', 'Phase2_XMLServices_TDD_SubPlan.md', 'PAD_3.md', 'Project_Architecture_Document.md', 'TEST_SUITE_VALIDATION_REPORT.md', 'TEST_SUITE_COMPLETION_REPORT.md', 'Test_suite_Singapore_SMB_workflow-2.md', 'API_WORKFLOW_VALIDATION_SUMMARY.md', 'Current_Project_Status_0310.md', 'REMEDIATION_PLAN_TDD.md', '.git', 'status_new.md', 'InvoiceNow_Phase3-4_Completion_Summary.md', 'frontend_web.png', 'docker', 'frontend_dashboard_2.png', 'status_15.md', 'API_WORKFLOW_IMPLEMENTATION_PLAN.md', 'CORS_FIX_IMPLEMENTATION_COMPLETE.md', 'Phase2_Task2_4_TDD_SubPlan.md', 'TDD_VIEW_LAYER_FIXES_SUBPLAN.md', 'README_old.md', 'CORS_FIX_SUCCESSFUL.md', 'DASHBOARD_LOADING_FIX_COMPLETE.md', 'PYTEST_FIX_VALIDATION_REPORT.md', 'reset_test_password.py', 'AGENT_BRIEF_UPDATE_PLAN.md', 'schema_model_gap_analysis.json', 'BACKEND_REMEDIATION_FINAL_REPORT.md', 'Invoice_Schema_Validation_Report.md', 'Phase4_Integration_TDD_SubPlan.md', 'review_plan_InvoiceNow.md', 'DOCUMENTATION_UPDATE_SUMMARY.md', 'PAD_3_VALIDATION_REPORT.md', 'Test_suite_Singapore_SMB_workflow-3.md', 'DASHBOARD_NO_ORG_ROOT_CAUSE_ANALYSIS.md', 'tests', 'to_validate_before_implementing_plan_for_InvoiceNow.md', 'frontend_dashboard.png', 'README.md', 'status_16.md', 'Current_Project_Status_0309.md', 'status_12.md', 'Test_suite_Singapore_SMB_workflow-1.md', 'Project_Summary.md', 'Phase1_Foundation_TDD_SubPlan.md', 'AGENT_BRIEF.md', 'status_13.md', 'API_CLI_USAGE_GUIDE_VALIDATION_REPORT.md', '__pycache__', 'database_connect.sh', 'status_10.md', 'AUTHENTICATION_MILESTONE_SUMMARY.md', 'API_CLI_VALIDATION_SUMMARY.md', 'e2e_test_phases_7_15.py', 'BACKEND_CORS_FINAL_STATUS.md', 'PAD_1.md', 'INTEGRATION_AUDIT_REPORT.md', 'initialize_database.sh', 'backup', 'BACKEND_ISSUES_REMEDIATION_PLAN.md', 'skills', 'CORS_FIX_SUMMARY.md', 'CORS_INVESTIGATION_FINAL_REPORT.md', 'start_frontend.md', 'run_test_suite.sh', 'CLAUDE.md', 'status_11.md', 'AGENTS.md', 'plan', 'start_frontend_log.txt', 'Phase2_Remaining_Tasks_TDD_SubPlan.md', 'GEMINI.bak', 'ACCOMPLISHMENTS.md', 'TDD_NEXT_STEPS_SUBPLAN.md', '.github', 'InvoiceNow_Implementation_Status_Report.md', 'E2E_TEST_REMEDIATION.md']

--- SCHEMA & ORM ALIGNMENT ---
Files with 'managed = False': 25
Files with 'class Meta:' but NO 'managed = False': 0

--- FINANCIAL PRECISION SWEEP ---
FloatField / float() usage:
apps/backend/MASTER_EXECUTION_PLAN.md:403:**Key design**: Override `JSONRenderer` to use a custom encoder that calls `str()` on `Decimal` values instead of `float()`. This prevents precision loss in API responses.


--- RLS MIDDLEWARE ---
"""
Tenant Context Middleware

THE MOST CRITICAL MIDDLEWARE IN THE SYSTEM.

For EVERY request to an org-scoped URL:
1. Extract org_id from URL path
2. Verify the authenticated user belongs to that org
3. Execute SET LOCAL app.current_org_id = '...' within the atomic transaction
4. Execute SET LOCAL app.current_user_id = '...'
5. Store org_id in contextvars for application-level access

Uses contextvars (NOT threading.local) per Python 3.13+ best practices
for compatibility with async contexts and ASGI.
"""

import contextvars
import uuid
from typing import Optional
import logging

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.cache import cache
from django.contrib.auth import get_user_model

from common.exceptions import UnauthorizedOrgAccess

User = get_user_model()
logger = logging.getLogger(__name__)


# Contextvars for application-layer access
_current_org_id: contextvars.ContextVar[Optional[uuid.UUID]] = contextva

--- GHOST COLUMN CHECK (TenantModel) ---
TenantModel usages:
apps/backend/apps/core/models/bank_transaction.py:9:from common.models import TenantModel
apps/backend/apps/core/models/bank_transaction.py:12:class BankTransaction(TenantModel):
apps/backend/apps/core/models/contact.py:8:from common.models import TenantModel
apps/backend/apps/core/models/contact.py:11:class Contact(TenantModel):
apps/backend/apps/core/models/gst_return.py:8:from common.models import TenantModel
apps/backend/apps/core/models/gst_return.py:11:class GSTReturn(TenantModel):
apps/backend/apps/core/models/role.py:10:from common.models import TenantModel
apps/backend/apps/core/models/role.py:13:class Role(TenantModel):
apps/backend/apps/core/models/fiscal_period.py:10:from common.models import TenantModel
apps/backend/apps/core/models/fiscal_period.py:13:class FiscalPeriod(TenantModel):
apps/backend/apps/core/models/document_sequence.py:8:from common.models import TenantModel
apps/backend/apps/core/models/document_sequence.py:11:class DocumentSequence(TenantModel):
apps/back

--- TEST FIXTURE ISOLATION ---
"""
Pytest configuration and fixtures for LedgerSG.
"""

import pytest
from decimal import Decimal


@pytest.fixture
def sample_money():
    """Sample decimal money value."""
    return Decimal("100.0000")


@pytest.fixture
def sample_gst_amount():
    """Sample GST amount (9% of 100)."""
    return Decimal("9.0000")


@pytest.fixture
def sample_inclusive_amount():
    """Sample GST-inclusive amount."""
    return Decimal("109.0000")

