import os
import subprocess
import json

os.chdir("/home/workspace/ledgersg")

# 1. Service Layer Purity Check
print("--- SERVICE LAYER PURITY CHECK ---")
banking_views_path = "apps/backend/apps/banking/views.py"
if os.path.exists(banking_views_path):
    with open(banking_views_path, 'r') as f:
        content = f.read()
        print("Banking Views (first 1500 chars):")
        print(content[:1500])
else:
    print("Banking views not found.")

# 2. API Contract Verification (Pagination)
print("\n--- API PAGINATION CHECK ---")
pagination_grep = subprocess.run(["grep", "-rn", "PageNumberPagination", "apps/backend/apps"], capture_output=True, text=True)
print(pagination_grep.stdout if pagination_grep.stdout else "No PageNumberPagination found in apps/")

# 3. Ghost Column Audit (TenantModel definition)
print("\n--- TENANT MODEL DEFINITION ---")
tenant_model_def = subprocess.run(["grep", "-A", "15", "class TenantModel", "apps/backend/common/models.py"], capture_output=True, text=True)
print(tenant_model_def.stdout if tenant_model_def.stdout else "TenantModel definition not found in common/models.py")

# 4. Schema Check for Ghost Columns
print("\n--- SCHEMA CHECK FOR CREATED_AT/UPDATED_AT ---")
schema_path = "apps/backend/database_schema.sql"
if os.path.exists(schema_path):
    with open(schema_path, 'r') as f:
        schema = f.read()
        # Check if core.bank_transaction has created_at
        if "core.bank_transaction" in schema:
            import re
            # Extract table definition
            match = re.search(r'CREATE TABLE core\.bank_transaction \((.*?)\);', schema, re.DOTALL)
            if match:
                print("core.bank_transaction columns:")
                print(match.group(1)[:500])

# 5. Security Posture: CORSJWTAuthentication
print("\n--- CORS JWT AUTHENTICATION ---")
auth_path = "apps/backend/apps/core/authentication.py"
if os.path.exists(auth_path):
    with open(auth_path, 'r') as f:
        print(f.read()[:1500])

# 6. Frontend Security Middleware
print("\n--- FRONTEND MIDDLEWARE ---")
fe_middleware = "apps/web/src/middleware.ts"
if os.path.exists(fe_middleware):
    with open(fe_middleware, 'r') as f:
        print(f.read()[:1000])
else:
    # Check root
    fe_middleware_root = "apps/web/middleware.ts"
    if os.path.exists(fe_middleware_root):
        with open(fe_middleware_root, 'r') as f:
            print(f.read()[:1000])

 # Result execute error ```