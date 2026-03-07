import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
sys.path.insert(0, '/home/project/Ledger-SG/apps/backend')

import django
django.setup()

from rest_framework.test import APIRequestFactory
from apps.core.views.auth import me_view

# Create an OPTIONS request with CORS headers
factory = APIRequestFactory()
request = factory.options('/api/v1/auth/me/',
    HTTP_ORIGIN='http://localhost:3000',
    HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET'
)

print("=== Testing me_view OPTIONS ===")
print(f"Request method: {request.method}")

try:
    response = me_view(request)
    print(f"✅ Response status: {response.status_code}")
    print(f"Response headers:")
    for k, v in response.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()

