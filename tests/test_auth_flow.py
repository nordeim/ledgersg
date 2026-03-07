import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
sys.path.insert(0, '/home/project/Ledger-SG/apps/backend')

import django
django.setup()

from django.test import RequestFactory
from rest_framework.request import Request
from apps.core.authentication import CORSJWTAuthentication

# Create an OPTIONS request
factory = RequestFactory()
http_request = factory.options('/api/v1/auth/me/', 
    HTTP_ORIGIN='http://localhost:3000',
    HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET'
)

print("=== Testing CORSJWTAuthentication ===")
print(f"Request method: {http_request.method}")

# Create DRF request
drf_request = Request(http_request)

# Test authentication
auth = CORSJWTAuthentication()
result = auth.authenticate(drf_request)

print(f"Authentication result: {result}")
print(f"Result type: {type(result)}")

if result is None:
    print("✅ Authentication skipped for OPTIONS (as expected)")
else:
    print(f"❌ Unexpected result: {result}")

