• Implementation Complete ✅

All critical fixes from the feedback have been successfully applied:

🔧 Fixes Applied Summary

 Issue                       Before                        After                  Location
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Frontend Chunk Validation   No minimum check              Fails if < 10 chunks   Lines 146-149
 Static Copy Silent Fail     || true (ignored)             Exits with error       Lines 140-143
 CASCADE Warning             No warning                    Clear warning shown    Lines 419-421, 428-431
 Log Path Mismatch           /tmp/backend_logs/error.log   /tmp/backend.log       Line 531
 Health Check Timeout        start-period=60s              start-period=120s      Line 645

Key Changes

1. Frontend Build Verification (Lines 138-150)

# Before: Silent failure on copy, no chunk validation
cp -r .next/static .next/standalone/.next/ 2>/dev/null || true; \

# After: Explicit error handling + minimum chunk count
cp -r .next/static .next/standalone/.next/ || { \
    echo "ERROR: Failed to copy static files"; \
    exit 1; \
}; \
...
if [ "$STATIC_COUNT" -lt 10 ]; then \
    echo "ERROR: Only $STATIC_COUNT JS chunks found. Expected 20+"; \
    exit 1; \
fi && \

2. Schema CASCADE Warning (Lines 416-431)

# Before: No warning
echo "  → Applying database schema (first run)..."

# After: Clear warning about data loss risk
echo "  ⚠  WARNING: This schema uses DROP SCHEMA IF EXISTS... CASCADE"
echo "      Re-running the schema will DESTROY all existing data!"
...
echo "  ⚠  TO RE-APPLY SCHEMA (DATA WILL BE LOST):"
echo "      1. Backup your data first!"

3. Log Path Fix (Line 531)

# Before: Wrong path
tail -50 /tmp/backend_logs/error.log

# After: Correct path
tail -50 /tmp/backend.log

4. Health Check Timeout (Line 645)

# Before: 60 seconds (too short)
HEALTHCHECK ... --start-period=60s ...

# After: 120 seconds (allows full initialization)
HEALTHCHECK ... --start-period=120s ...

Expected Behavior After Deploy

• Frontend: Build fails explicitly if static files can't be copied or if fewer than 10 JS chunks
• Schema: Users see clear warning about CASCADE data loss before any schema operation
• Debugging: Backend error logs accessible via curl http://localhost:7860/logs/backend
• Health Checks: Container won't be marked unhealthy during normal 90-120 second startup

---

```text
diff --git a/docker/Dockerfile b/docker/Dockerfile
index b98eb9c..e91c4ad 100644
--- a/docker/Dockerfile
+++ b/docker/Dockerfile
@@ -137,10 +137,17 @@ RUN cd /app/apps/web && \
     fi && \
     if [ ! -d ".next/standalone/.next/static" ]; then \
         echo "WARNING: Static files not in standalone folder, copying..."; \
-        cp -r .next/static .next/standalone/.next/ 2>/dev/null || true; \
+        cp -r .next/static .next/standalone/.next/ || { \
+            echo "ERROR: Failed to copy static files"; \
+            exit 1; \
+        }; \
     fi && \
     STATIC_COUNT=$(ls .next/standalone/.next/static/chunks/*.js 2>/dev/null | wc -l) && \
-    echo "✓ Standalone build verified: $STATIC_COUNT JS chunks" && \
+    if [ "$STATIC_COUNT" -lt 10 ]; then \
+        echo "ERROR: Only $STATIC_COUNT JS chunks found. Expected 20+"; \
+        exit 1; \
+    fi && \
+    echo "✓ Standalone build verified: $STATIC_COUNT JS chunks" && 
     chown -R user:user /app/apps/web
 
 # ═══════════════════════════════════════════════════════════════════════════════
@@ -408,11 +415,20 @@ TABLE_COUNT=$(sudo -u user ${PG_BIN}/psql -h localhost -p 5432 -d ${DB_NAME} -t
 
 if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq "0" ]; then
     echo "  → Applying database schema (first run)..."
+    echo ""
+    echo "  ⚠  WARNING: This schema uses DROP SCHEMA IF EXISTS... CASCADE"
+    echo "      Re-running the schema will DESTROY all existing data!"
+    echo ""
     sudo -u user ${PG_BIN}/psql -h localhost -p 5432 -d ${DB_NAME} -f /app/apps/backend/database_schema.sql
     echo "  ✓ Schema applied"
 else
     echo "  ✓ Database schema already exists ($TABLE_COUNT tables found)"
     echo "  ℹ  Skipping schema application to preserve data"
+    echo ""
+    echo "  ⚠  TO RE-APPLY SCHEMA (DATA WILL BE LOST):"
+    echo "      1. Backup your data first!"
+    echo "      2. Drop the database and recreate"
+    echo "      3. Container will auto-apply schema on next startup"
 fi
 
 # ═══════════════════════════════════════════════════════════════════════════════
@@ -512,7 +528,7 @@ done
 if [ "$BACKEND_READY" = false ]; then
     echo "⚠ Backend API may not be fully ready (continuing)"
     echo "📋 Last 50 lines of error log:"
-    tail -50 /tmp/backend_logs/error.log 2>/dev/null || echo "  (log not available)"
+    tail -50 /tmp/backend.log 2>/dev/null || echo "  (log not available)"
 fi
 
 # ═══════════════════════════════════════════════════════════════════════════════
@@ -626,7 +642,7 @@ EXPOSE ${APP_PORT} ${FRONTEND_PORT} ${BACKEND_PORT}
 
 # Health check - flexible for any exposed port
 # HF Space will configure which port the URL maps to
-HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
+HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
     CMD curl -f http://localhost:${FRONTEND_PORT} 2>/dev/null || \
         curl -f http://localhost:${APP_PORT}/health 2>/dev/null || \
         exit 1
```
