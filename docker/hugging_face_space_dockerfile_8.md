• Now I have a complete picture. The issue is:

1. Django's LOGGING config defines a 'file' handler pointing to /tmp/ledgersg_api.log
2. This handler is defined but NOT used by any logger (only 'console' is used)
3. Django still validates ALL handlers at startup → fails on file handler → crash

---

Implementation Plan

Phase 1: Fix Django Settings

• Remove the unused 'file' handler from LOGGING
• Keep console-only logging (already the active configuration)

Phase 2: Fix Entrypoint Script

• Remove unnecessary /tmp/backend_logs directory creation
• Update Gunicorn to use stdout/stderr (- for logfiles)
• Update health check to read from /tmp/backend.log instead

Phase 3: Fix boot.py

• Update log file paths to match new locations

---

• Implementation Complete

All critical fixes have been applied successfully. Here's the summary:

🔧 Fixes Applied

 File                         Change                                       Purpose
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 config/settings/service.py   Removed unused 'file' handler from LOGGING   Eliminates ValueError: Unable to configure handler 'file'
 docker/Dockerfile            Removed log directory creation               Cleanup - no longer needed
 docker/Dockerfile            Gunicorn logs to stdout/stderr (-)           Container best practice
 docker/Dockerfile            Output redirected to /tmp/backend.log        Centralized log access
 docker/Dockerfile            Health check reads from /tmp/backend.log     Correct log path

Key Changes

1. Django LOGGING (service.py)

# BEFORE: Had unused 'file' handler causing crash
'handlers': {
    'console': {...},
    'file': {  # ← Removed
        'filename': '/tmp/ledgersg_api.log',
    },
},

# AFTER: Console-only logging
'handlers': {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
},

2. Gunicorn Configuration (Dockerfile entrypoint)

# BEFORE: File-based logging
--access-logfile /tmp/backend_logs/access.log \
--error-logfile /tmp/backend_logs/error.log \

# AFTER: stdout/stderr logging (container best practice)
--access-logfile - \
--error-logfile - \
" > /tmp/backend.log 2>&1 &

Expected Result After Deploy

════════════════════════════════════════════════════════════════
   Service Status Summary
════════════════════════════════════════════════════════════════
  ✅ Backend API:    http://localhost:8000 (Gunicorn)
  ✅ Frontend:       http://localhost:3000
  ✅ Redis:          localhost:6379
  ✅ PostgreSQL:     localhost:5432
  ℹ  Monitor:        http://localhost:7860 (boot.py)

🎉 All critical services are ready!

The backend should now start successfully without the logging configuration error.

