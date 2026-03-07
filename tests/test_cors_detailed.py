import sys
sys.path.insert(0, '/home/project/Ledger-SG/apps/backend')

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'

import django
django.setup()

from django.test import RequestFactory
from corsheaders.middleware import CorsMiddleware
from django.contrib.auth.models import AnonymousUser

# Create a fake OPTIONS request
factory = RequestFactory()
request = factory.options('/api/v1/auth/me/', 
    HTTP_ORIGIN='http://localhost:3000',
    HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET'
)

print("=== Testing CorsMiddleware directly ===")
print(f"Request method: {request.method}")
print(f"Request path: {request.path}")
print(f"Origin header: {request.META.get('HTTP_ORIGIN')}")

# Get middleware
middleware = CorsMiddleware(lambda x: x)

# Process request
response = middleware(request)
print(f"\nResponse status: {response.status_code}")
print(f"Response headers:")
for key, val in response.items():
    if 'Access-Control' in key or 'Origin' in key:
        print(f"  {key}: {val}")

