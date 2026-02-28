• Meticulous Analysis of Feedback

Based on the comprehensive feedback from both review documents, I've identified critical issues that must be fixed:

🔴 CRITICAL Issues (Must Fix)

 Issue              Impact                     Root Cause
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Backend Crash      API completely down        Django logging config - log directory doesn't exist
 Data Destruction   All data lost on restart   Schema applied every time with DROP SCHEMA IF EXISTS
 Missing netcat     No port check fallback     Package not installed

🟠 HIGH Priority Issues

 Issue                         Impact                              Root Cause
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Frontend build verification   May fail if static files missing    No fallback copying
 Backend health check          Times out without detecting crash   No process monitoring

---
Implementation Plan

Phase 1: Critical Fixes

1. Add netcat-openbsd to system dependencies (for port checking)
2. Create log directory before starting Gunicorn (/tmp/backend_logs)
3. Make schema application idempotent - check table count before applying
4. Fix backend health check - monitor Gunicorn process, not just HTTP

Phase 2: Robustness Improvements

5. Add static file fallback - copy if not in standalone folder
6. Improve error logging - better diagnostic output

---

• Implementation Complete

I've meticulously applied all the critical fixes identified in the feedback. Here's a summary:

🔴 Critical Fixes Applied

 Issue                     Fix                                                           Location in Dockerfile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Backend Crash (logging)   Created /tmp/backend_logs before Gunicorn starts              Lines 488-491
 Data Destruction          Idempotent schema check - counts ALL tables before applying   Lines 440-454
 Missing netcat            Added netcat-openbsd to system packages                       Line 53

🟠 High Priority Improvements

 Issue                    Fix                                                         Location in Dockerfile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Backend Health Check     Monitors Gunicorn process with pgrep + port check with nc   Lines 519-558
 Static File Fallback     Copies static files if not in standalone folder             Lines 133-137
 Better Error Reporting   Detailed log output on startup failures                     Various locations

Key Changes in Detail

1. Idempotent Schema Application (Lines 440-454)

TABLE_COUNT=$(sudo -u user ${PG_BIN}/psql -h localhost -p 5432 -d ${DB_NAME} -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema IN ('core','coa','gst','journal','invoicing','banking','audit');" 2>/dev/null | tr -d ' ' || echo "0")

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq "0" ]; then
    echo "  → Applying database schema (first run)..."
    # Apply schema
else
    echo "  ✓ Database schema already exists ($TABLE_COUNT tables found)"
    echo "  ℹ  Skipping schema application to preserve data"
fi

2. Backend Log Directory (Lines 488-491)

mkdir -p /tmp/backend_logs
chown user:user /tmp/backend_logs
chmod 755 /tmp/backend_logs

3. Process-Aware Health Check (Lines 519-558)

# Check if Gunicorn process died
if ! pgrep -f "gunicorn.*config.wsgi" > /dev/null 2>&1; then
    echo "✗ Backend Gunicorn process died"
    tail -50 /tmp/backend_logs/error.log
    break
fi

# Fallback port check with netcat
if nc -z localhost ${BACKEND_PORT} 2>/dev/null; then
    echo "✓ Backend port listening"
    break
fi

4. Frontend Build Error Handling (Lines 126-137)

if [ ! -d ".next/standalone/.next/static" ]; then
    echo "WARNING: Static files not in standalone folder, copying...";
    cp -r .next/static .next/standalone/.next/ 2>/dev/null || true;
fi

---
Next Steps

1. Rebuild the HF Space with the updated Dockerfile
2. Verify backend starts without logging errors
3. Test data persistence - add data, restart container, verify data remains
4. Check boot monitor at http://your-space.hf.space/ for service status

The Dockerfile is now robust against the critical issues identified in the feedback reports.

