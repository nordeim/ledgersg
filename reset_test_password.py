#!/usr/bin/env python3
"""
Reset test user password using Django shell.
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
sys.path.insert(0, "/home/project/Ledger-SG/apps/backend")

import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Update existing test user
user = User.objects.filter(email="test@example.com").first()
if user:
    user.set_password("testpass123")
    user.save()
    print(f"✅ Password reset for: {user.email}")
    print(f"   New password: testpass123")
else:
    print("❌ Test user not found")

# Also create a new workflow test user
user2, created = User.objects.update_or_create(
    email="workflow@ledgersg.sg",
    defaults={
        "first_name": "Workflow",
        "last_name": "Test",
        "is_active": True,
    },
)
user2.set_password("Workflow123!")
user2.save()
print(f"{'✅ Created' if created else '✅ Updated'} user: {user2.email}")
print(f"   Password: Workflow123!")
