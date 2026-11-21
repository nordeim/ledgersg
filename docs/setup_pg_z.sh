#!/usr/bin/env bash
# Rootless PostgreSQL install per skills/rootless-postgresql/SKILL.md,
# adapted to the home-furnishing-store repo contract:
#   prefix /home/z/my-project/pg, port 5432, role postgres/postgres, db app_db
# (same adaptation as Tasks 114-121 — matches drizzle.config.json)
set -euo pipefail

PG_ROOT="/home/z/my-project/pg/root"
PG_DATA="/home/z/my-project/pg/data"
PG_LOG_DIR="/home/z/my-project/pg/log"
PG_PORT="5432"
PG_ROLE="postgres"
PG_SECRET="postgres"
PG_DB="app_db"

mkdir -p "$PG_ROOT" "$PG_DATA" "$PG_LOG_DIR" /home/z/my-project/pg/deb

# Resolve major dynamically (trixie ships 17)
PG_MAJOR=$(apt-cache search --names-only '^postgresql-[0-9]+$' | grep -oE '[0-9]+' | sort -n | tail -1)
[ -n "$PG_MAJOR" ] || { echo "FAIL: no postgresql-N in apt cache"; exit 1; }
echo "[pg] resolved major: $PG_MAJOR"

if [ ! -x "/home/z/my-project/pg/root/usr/lib/postgresql/${PG_MAJOR}/bin/initdb" ]; then
  cd /home/z/my-project/pg/deb
  apt-get download "postgresql-${PG_MAJOR}" "postgresql-client-${PG_MAJOR}" postgresql-common libpq5
  for f in *.deb; do dpkg-deb -x "$f" "$PG_ROOT/"; done
fi
PGBIN="${PG_ROOT}/usr/lib/postgresql/${PG_MAJOR}/bin"
export PATH="${PGBIN}:${PATH}"
"$PGBIN/initdb" --version

if [ ! -f "${PG_DATA}/PG_VERSION" ]; then
  chmod 700 "$PG_DATA"
  "$PGBIN/initdb" -D "$PG_DATA" -U postgres --auth=trust --encoding=UTF8 --locale=C.UTF-8
fi

# Configure: port 5432, socket in data dir, TCP localhost, logs to owned dir
sed -i "s/^#port = 5432/port = ${PG_PORT}/" "$PG_DATA/postgresql.conf"
sed -i "s|^#unix_socket_directories = '/var/run/postgresql'|unix_socket_directories = '${PG_DATA}'|" "$PG_DATA/postgresql.conf"
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$PG_DATA/postgresql.conf"
sed -i "s|^#log_directory = 'log'|log_directory = '${PG_LOG_DIR}'|" "$PG_DATA/postgresql.conf"
sed -i "s/^#logging_collector = off/logging_collector = on/" "$PG_DATA/postgresql.conf"

# scram for TCP (repo contract: postgres:postgres@127.0.0.1:5432), trust for socket
if ! grep -q "nordhem scram" "$PG_DATA/pg_hba.conf"; then
  sed -i 's/^host    all             all             127.0.0.1\/32            trust/host    all             all             127.0.0.1\/32            scram-sha-256  # nordhem scram/' "$PG_DATA/pg_hba.conf"
  sed -i 's/^host    all             all             ::1\/128                 trust/host    all             all             ::1\/128                 scram-sha-256  # nordhem scram/' "$PG_DATA/pg_hba.conf"
fi

if "$PGBIN/pg_ctl" -D "$PG_DATA" status >/dev/null 2>&1; then
  echo "[pg] already running"
else
  "$PGBIN/pg_ctl" -D "$PG_DATA" -l "${PG_LOG_DIR}/postgres.log" -w -t 30 -o "-p ${PG_PORT}" start
fi

# idempotent role bootstrap: superuser postgres with password (scram TCP)
"$PGBIN/psql" -h "$PG_DATA" -p "$PG_PORT" -U postgres -d postgres -c "ALTER ROLE postgres PASSWORD 'postgres';" >/dev/null
if ! "$PGBIN/psql" -h "$PG_DATA" -p "$PG_PORT" -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
  "$PGBIN/psql" -h "$PG_DATA" -p "$PG_PORT" -U postgres -d postgres -c "CREATE DATABASE \"${PG_DB}\";"
fi

"$PGBIN/pg_isready" -h 127.0.0.1 -p "$PG_PORT"
PGPASSWORD=postgres "$PGBIN/psql" -h 127.0.0.1 -p "$PG_PORT" -U postgres -d app_db -c "SELECT current_user, current_database();"
echo "[pg] ready: postgresql://postgres:postgres@127.0.0.1:5432/app_db"
