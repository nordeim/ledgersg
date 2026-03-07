import os
import sys
import django

# Check which settings module is being used
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, '/home/project/Ledger-SG/apps/backend')

django.setup()

from django.conf import settings

print("\n=== CURRENT DJANGO SETTINGS ===")
print(f"Settings module: {settings.SETTINGS_MODULE}")
print(f"\nCORS Configuration:")
print(f"  CORS_ALLOW_ALL_ORIGINS: {getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', 'Not set')}")
print(f"  CORS_ALLOWED_ORIGINS: {getattr(settings, 'CORS_ALLOWED_ORIGINS', 'Not set')}")
print(f"  CORS_ALLOW_CREDENTIALS: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', 'Not set')}")
print(f"\nMiddleware stack:")
for i, mw in enumerate(settings.MIDDLEWARE):
    if 'cors' in mw.lower() or 'security' in mw.lower() or 'auth' in mw.lower():
        print(f"  {i}: {mw}")
print(f"\nINSTALLED_APPS (cors related):")
for app in settings.INSTALLED_APPS:
    if 'cors' in app.lower():
        print(f"  - {app}")
