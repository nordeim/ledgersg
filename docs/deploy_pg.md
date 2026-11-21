## Database installation — rootless PostgreSQL

The supported method installs and runs PostgreSQL **entirely as an
unprivileged user**: the server binaries are extracted from the official
Debian packages into a user-owned prefix, the cluster is initialized with
`initdb` under that prefix, and the server lifecycle runs through `pg_ctl`.
No `sudo`, no `apt-get install`, no systemd, no writes outside the prefix.
This fits restricted hosts — shared sandboxes, VPS user accounts, containers
without init systems — and it is the exact method behind this repository's
live-database verification (PostgreSQL 17.12, port 5432, database `app_db`).

The canonical version is the repo skill `skills/rootless-postgresql/SKILL.md`
(Debian trixie/sid, non-root user with a writable prefix). The commands
below are that method as executed for this codebase.

```bash
set -euo pipefail

# 0. Layout — any writable prefix works (the verification workspace used
#    /home/z/my-project/pg). Port/role/database match drizzle.config.json
#    and the .env.example default: zero configuration drift.
PG_BASE="$HOME/pg"                  # the prefix
PG_MAJOR=17                         # trixie ships 17; resolve dynamically with:
                                    # apt-cache search --names-only '^postgresql-[0-9]+$'
PG_ROOT="$PG_BASE/pgroot"           # extracted binaries (the "install")
PG_DATA="$PG_BASE/pgdata"           # the cluster
PG_LOG_DIR="$PG_BASE/pglog"         # server logs
PG_PORT=5432
PG_ROLE=postgres
PG_SECRET=postgres                  # dev default; scram-authenticated over TCP only
PG_DB=app_db

# 1. Probes — every check must pass before proceeding
[ "$(id -u)" -ne 0 ] || { echo "FAIL: run as a non-root user"; exit 1; }
mkdir -p "$PG_BASE" && [ -w "$PG_BASE" ] || { echo "FAIL: $PG_BASE not writable"; exit 1; }
mkdir -p "$PG_ROOT" "$PG_DATA" "$PG_LOG_DIR" "$PG_BASE/pgdeb"

# 2. Download the official .debs (download only — nothing is installed)
cd "$PG_BASE/pgdeb"
apt-get download "postgresql-${PG_MAJOR}" "postgresql-client-${PG_MAJOR}" \
                 postgresql-common libpq5

# 3. Extract them into the prefix
for f in *.deb; do dpkg-deb -x "$f" "$PG_ROOT/"; done
PGBIN="$PG_ROOT/usr/lib/postgresql/${PG_MAJOR}/bin"
"$PGBIN/initdb" --version     # sanity: the binaries run against system libs

# 4. Initialize the cluster (only if empty).
#    Socket auth = trust (admin convenience, local user only);
#    TCP auth = scram-sha-256 (the app carries the password).
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
  chmod 700 "$PG_DATA"
  "$PGBIN/initdb" -D "$PG_DATA" -U "$PG_ROLE" \
    --auth-local=trust --auth-host=scram-sha-256 \
    --encoding=UTF8 --locale=C.UTF-8
fi

# 5. Point the config at the prefix and the port (idempotent)
PGCONF="$PG_DATA/postgresql.conf"
sed -i "s/^#port = 5432/port = ${PG_PORT}/"                                       "$PGCONF"
sed -i "s|^#unix_socket_directories = .*|unix_socket_directories = '${PG_DATA}'|" "$PGCONF"
sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = 'localhost'/"      "$PGCONF"
sed -i "s/^#logging_collector = off/logging_collector = on/"                     "$PGCONF"
sed -i "s|^#log_directory = 'log'|log_directory = '${PG_LOG_DIR}'|"              "$PGCONF"

# 6. Start (pg_ctl, not systemd) — logs go to $PG_LOG_DIR/postgres.log
"$PGBIN/pg_ctl" -D "$PG_DATA" -l "$PG_LOG_DIR/postgres.log" -w -t 30 start

# 7. Role password + application database (over the trusted socket)
"$PGBIN/psql" -h "$PG_DATA" -p "$PG_PORT" -U "$PG_ROLE" -d postgres \
  -c "ALTER ROLE \"${PG_ROLE}\" WITH LOGIN PASSWORD '${PG_SECRET}';"
"$PGBIN/createdb" -h "$PG_DATA" -p "$PG_PORT" -U "$PG_ROLE" "$PG_DB" \
  || echo "database ${PG_DB} already exists"

# 8. Verify — TCP requires the scram password; this is the app's path
"$PGBIN/pg_isready" -h 127.0.0.1 -p "$PG_PORT"
```

On success the connection string is exactly what `.env` and
`drizzle.config.json` pin:

```
postgresql://postgres:postgres@127.0.0.1:5432/app_db
```

Operational notes:

- **Lifecycle** is `pg_ctl`: `… -D "$PG_DATA" status`, and
  `… -D "$PG_DATA" -m fast -w stop`. Keep start/stop/status scripts next to
  the prefix (the verification workspace keeps them under
  `<prefix>/scripts/`); the whole cluster is plain files under `$PG_DATA`
  — stop the server before copying it wholesale.
- **Auth split:** the Unix socket inside `$PG_DATA` trusts the local user
  (administrative commands never need the password); TCP on 127.0.0.1
  requires the scram password. The application always connects over TCP.
- **Change `PG_SECRET`** for anything exposed beyond loopback, and never
  expose this cluster directly to the internet — it is a single-user
  development-grade deployment.
- **Backups:** `pg_dump` / `pg_dumpall` from the same `$PGBIN` against
  `app_db`.

**Alternatives.** Any reachable PostgreSQL serves equally — a system
service (`apt-get install postgresql`), Docker, or a
managed provider. The application is indifferent; §5–§6 are the same either
way. The rootless method above is the one this repository documents,
verifies, and keeps in lockstep with its pinned connection string.
