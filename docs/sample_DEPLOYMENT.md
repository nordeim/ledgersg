# Deployment Guide — Nordhem Furnishing Store

NORDHEM ships as a **single Next.js application over one PostgreSQL database**:
one Node process plus Postgres, nothing else. This revision (2026-11-21,
session 013) is rewritten from the operator's `docs/sample_DEPLOYMENT.md`
(structure and field-tested command sequences) with **every claim re-verified
against this codebase** — the sample was written for a sibling repo and its
facts (9 tables, 6 API routes, Pexels imagery, mock payments, an `{ok,data}`
envelope) do not apply here. (§1's header posture and §10's gate counts were
re-censed in session-013 — the repo has shipped HSTS since session-009.) Verified truths this guide is built on:
Drizzle ORM over `node-postgres` (`src/db/index.ts`, single `db` export), 7
tables in `src/db/schema.ts`, 11 page routes + 8 API route files under
`src/app/`, integer-cents money re-derived server-side at checkout
(`src/lib/shopping.ts` + `src/lib/cart-math.ts`), and a fail-loud error
posture (no static-catalog fallback).

## 1. Supported shape

- One Next.js 16 App Router app: 11 page routes (home, catch-all content
  pages, cart, category, checkout, favourites/shopping list, IKEA Family,
  order confirmation, product, search, track-order) + 8 API route files
  (12 methods) under `src/app/`. The current build compiles 25 app-path
  routes including `sitemap.xml`, `robots.txt` and `manifest.webmanifest`.
- One PostgreSQL database: **7 tables** — `categories`, `products`,
  `cart_items`, `favourites`, `orders`, `order_items`, `family_members`.
- No external services: no Redis, no queues, no object storage. Product
  imagery is hot-linked from the **IKEA CDN** (`www.ikea.com`) through plain
  `<img>` tags (`src/components/ui/smart-image.tsx`) — there is no local
  image pipeline and no `next/image` remotePatterns config.
- No authentication and **no payment step**: checkout offers two *delivery*
  methods (home delivery / click & collect) with the copy "Demo checkout: no
  payment is taken and no real order is placed". Identity is an opaque
  session cookie; there are no credentials to leak.
- The build output is the plain `.next/` directory served by `next start`.
  `next.config.ts` sets: `poweredByHeader: false`, six security headers
  (X-Content-Type-Options `nosniff`, X-Frame-Options `DENY`,
  Referrer-Policy `strict-origin-when-cross-origin`, Permissions-Policy
  `camera=(), microphone=(), geolocation=(), payment=()`, and — since
  session-009 — `Strict-Transport-Security: max-age=31536000;
  includeSubDomains` (HSTS; the dev/prod split is in §8) — all
  e2e-pinned) and
  three 307 redirects (`/profile` → `/ikea-family`,
  `/customer-service/track-manage-order` → `/track-order`,
  `/ikea-family/:path+` → `/ikea-family`), and since session-007 a
  **Content-Security-Policy** (`default-src 'self'; img-src 'self'
  https://www.ikea.com; style-src 'self' 'unsafe-inline';
  script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self';
  form-action 'self'; frame-ancestors 'none'` — the inline allowances are
  Next's RSC bootstrap and the two JSON-LD blocks).

## 2. Prerequisites

- **Node.js ≥ 20** (verified on Node 24). npm is the package manager;
  `package-lock.json` is the lockfile.
- **A reachable PostgreSQL server.** The **rootless install in §4 is the
  documented and verified method** (PostgreSQL 17 served the live
  verification cycles — seeding, checkout round-trip, tracking). Any other
  PostgreSQL — system service, **Docker (§4b)**, or a managed instance —
  works identically: the application only ever sees `DATABASE_URL`.

## 3. Install and configure

```bash
git clone https://github.com/nordeim/nordhem-furnishing-store.git
cd nordhem-furnishing-store
npm install
cp .env.example .env    # then edit DATABASE_URL
```

Three operator variables are read (nothing else — verified by grep over
`src/` and `scripts/`):

| Variable | Required | Read by | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | `src/db/index.ts` (throws at module load, including during `next build`) | PostgreSQL connection string |
| `NEXT_PUBLIC_SITE_URL` | recommended | `src/lib/seo.ts` → `siteBaseUrl()` | Public origin for sitemap/robots/canonicals/JSON-LD; **inlined at build time** into the prerendered sitemap/robots — changing it requires a rebuild |
| `TRUSTED_PROXY_DEPTH` | no | `src/lib/http.ts` → `clientKey()` | Opt-in proxy trust for rate limiting (§8) |

A shell-exported `DATABASE_URL` **always beats `.env`** (dotenv never
overrides existing process env) — if the app reads the wrong database, check
`env | grep DATABASE_URL` before touching code.

## 4. Database installation — rootless PostgreSQL (primary method)

`docs/setup_pg_z.sh` performs this entire sequence idempotently (prefix
`/home/z/my-project/pg`, port 5432, role `postgres`/`postgres`, database
`app_db` — matching `drizzle.config.json`):

```bash
bash docs/setup_pg_z.sh
# [pg] ready: postgresql://postgres:postgres@127.0.0.1:5432/app_db
```

What it does, for reference on other hosts (see
`skills/rootless-postgresql/SKILL.md` for the full runbook):

1. `apt-get download postgresql-17 postgresql-client-17 postgresql-common
   libpq5`, extract with `dpkg-deb -x` into a user-owned prefix (no root).
2. `initdb -D pg/data -U postgres --auth=trust` → then `pg_hba.conf` is set
   to `scram-sha-256` for TCP and `trust` for the local socket.
3. `pg_ctl start` on port 5432, `listen_addresses='localhost'`
   (loopback-only), logs under `pg/log/`.
4. `ALTER ROLE postgres PASSWORD 'postgres'; CREATE DATABASE app_db;`

Stop / status:
```bash
/home/z/my-project/pg/root/usr/lib/postgresql/17/bin/pg_ctl -D /home/z/my-project/pg/data status
# stop: same command with "stop" (or "restart")
```

### 4b. Docker alternative

The repo's `docker-compose.yml` runs the same PostgreSQL 17 with the same
credentials/port as `drizzle.config.json`:

```bash
docker compose up -d          # postgres:17-alpine, 127.0.0.1:5432, volume postgres_data
docker compose logs -f postgres
docker compose down           # stop (data persists in the named volume)
docker compose down -v        # WARNING: deletes all data
```

The port is published as `127.0.0.1:5432:5432` — loopback only, because
`postgres:postgres` must never be network-reachable. After the first
`up -d`, run `npm run db:setup` (§5) to create the 7 tables and seed.

## 5. Schema push

```bash
npm run db:push        # drizzle-kit push (no migration journal — dev-posture by design)
```

**Dual-config drift trap:** `drizzle.config.json` pins its own
`postgresql://postgres:postgres@127.0.0.1:5432/app_db` and does **not** read
`.env`. If you point `.env` at a different database, `db:push` will still
act on the URL in `drizzle.config.json` — keep the two in lockstep (or edit
`drizzle.config.json` for your environment before pushing).

## 6. Seeding — automatic on first read

```bash
npm run db:seed        # explicit: tsx scripts/seed-cli.ts (dotenv loads BEFORE the src/db import graph)
# or the one-command path:
npm run db:setup       # db:push + db:seed
```

Seeding is `ensureCatalog()` in `src/db/seed.ts`: it runs lazily on the
**first catalog read of a process** (every `src/lib/catalog.ts` query and
`productExists()` call it), guarded by `pg_advisory_xact_lock(727_001)` and
a row-count check on `categories`, with `onConflictDoNothing` — idempotent,
single-flight, and it **never overwrites live rows**. It seeds **22
categories** (21 from `src/content/home.json` + 1 synthetic collection:
`lowest-price`) and **242 products** from
`src/content/catalog.json`. The result is memoized per process; a failure is
not cached (the next request retries).

Verify:

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d app_db \
  -c "SELECT (SELECT count(*) FROM categories) AS categories, (SELECT count(*) FROM products) AS products;"
#  categories | products
#         22 |      242
```

**Reseed from scratch** (destroys orders/carts — dev only):

```sql
TRUNCATE order_items, orders, cart_items, favourites, family_members, products, categories RESTART IDENTITY CASCADE;
```

…then restart the app (or run `npm run db:seed`) and open `/`.

## 7. Build and run

```bash
rm -rf .next           # cold build — a warm Turbopack cache can mask CSS scanner failures
npm run build          # plain .next/ output (NO standalone bundle)
npm run start          # next start on $PORT (default 3000)
```

Build-time-prerendered surfaces: `/sitemap.xml`, `/robots.txt`,
`/ikea-family`, `/track-order`, `/manifest.webmanifest`, `/icon.svg`,
`/_not-found`, `/_global-error`. Everything else is `force-dynamic`.
**Consequence:** `NEXT_PUBLIC_SITE_URL` changes and catalog changes require
a rebuild for the sitemap/robots to reflect them.

Set the public origin before building in production:
```bash
NEXT_PUBLIC_SITE_URL="https://your-origin" npm run build
```

## 8. Production notes

- **Money**: integer cents at every boundary. Delivery is a flat **$49.00**,
  free at ≥ **$500.00** net; click & collect is free; max line quantity 99.
  The server re-reads prices **inside the checkout transaction** — the
  client never sends amounts. The checkout transaction locks only the
  session's cart rows (`FOR UPDATE OF cart_items`) so concurrent
  same-session checkouts cannot double-order without cross-session
  contention on product rows.
- **Sessions**: `ikea_sid` UUID cookie — `HttpOnly`, `SameSite=Lax`,
  `Secure` whenever `x-forwarded-proto: https` **or** `NODE_ENV=production`.
  A production server that terminates TLS itself (no proxy) must serve
  HTTPS or the browser refuses the cookie. No accounts, no PII.
- **API surface and rate limits** (in-memory fixed windows, per instance):

  | Route | Methods | Limit |
  |---|---|---|
  | `/api/cart` | GET/POST/PATCH/DELETE | 120/min combined across methods, per client |
  | `/api/favourites` | POST/DELETE | 120/min |
  | `/api/search` | GET | 90/min |
  | `/api/checkout` | POST | 10/min |
  | `/api/orders/track` | POST | 10/min |
  | `/api/family` | POST | 5/min |
  | `/api/health` | GET | unlimited (select-1 probe, orchestrator path) |
  | `/api/summary` | GET | 120/min (runs DB queries — not a probe; session-012 S12-L1) |

- **Rate-limit keying**: `clientKey()` in `src/lib/http.ts`. With **no proxy
  trust declared** (`TRUSTED_PROXY_DEPTH` unset/garbage — the default),
  BOTH `x-forwarded-for` and `x-real-ip` are ignored as client-authored and
  every caller shares the `"unknown"` bucket. Behind a trusted proxy, set
  `TRUSTED_PROXY_DEPTH=1` (or 2 for two chained proxies): the key is then
  the entry N hops from the END of `x-forwarded-for` (proxies append),
  falling back to a proxy-set `x-real-ip`; the CSRF check likewise
  honors `x-forwarded-host` only under declared trust. Forward
  `X-Forwarded-Proto: https` so cookie attributes and the CSRF origin check
  stay correct.
- **Direct-exposure ceiling**: with no proxy trust declared, every caller
  shares the `unknown` bucket, so checkout is effectively **10/min total
  across all users** (family 5/min, track 10/min). Fine for a single-user
  demo; for real traffic put a proxy in front and set
  `TRUSTED_PROXY_DEPTH=1`.
- **Security headers** (next.config.ts via the tested `src/lib/security-headers.ts` seam):
  `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS — browsers ignore
  it over plain HTTP, so local dev is unaffected), `X-Frame-Options: DENY`, `nosniff`,
  strict referrer policy, restrictive Permissions-Policy, and the CSP allowlist. The CSP
  gains `script-src 'unsafe-eval'` ONLY when `NODE_ENV=development` (React's dev runtime
  requires eval); production stays strict. `allowedDevOrigins: ["127.0.0.1"]` lets the dev
  server be browsed via the loopback IP (Next 16 blocks cross-origin dev resources by
  default — without it, hydration silently dies on 127.0.0.1).
- **Never set `NODE_ENV` manually.** The security-header seam keys off it: an explicit
  `NODE_ENV=development next build` is RESPECTED by Next (with a warning) and would bake
  the dev-only `unsafe-eval` CSP into a production build; symmetrically
  `NODE_ENV=production npm run dev` re-breaks dev hydration. Plain `next dev` /
  `next build` / `next start` set the right value themselves, and the e2e pin (production
  CSP must not contain unsafe-eval) backstops a polluted build.
- **Error posture**: fail loud. A database outage returns 500 via `guard()`
  and the error boundary — only the sitemap degrades (static routes) so a
  build never dies on a DB hiccup. Success responses are raw JSON payloads;
  failures are `{ error: { code, message, details? } }`.
- **SEO**: `/sitemap.xml` (274 URLs: 2 static + 8 info routes — canonical
  roots only, deep pages fold into their prefix canonicals — + 22
  categories/collections + 242 products), `/robots.txt` disallows private
  session surfaces (`/cart`, `/checkout`, `/orders/`, `/track-order`,
  `/favourites`, `/search`, `/api/`), canonical links on `/cat/*` and
  `/p/*`, Organization/WebSite/Product JSON-LD, `noindex` on private pages.
  Unknown content paths return a **real 404** (no soft-200s).

## 9. Updating an existing deployment

```bash
git pull
npm install
npm run db:setup       # after schema changes (drizzle-kit push + idempotent seed)
rm -rf .next && npm run build   # cold build
# restart the server process
```

### Pruning abandoned cart rows

Sessions are cookie-only UUIDs with no sessions table, so abandoned carts
and favourites accumulate rows. Prune them on a cron (weekly is plenty):

```bash
DATABASE_URL=... node scripts/prune-abandoned-carts.mjs            # report only (dry-run default)
DATABASE_URL=... node scripts/prune-abandoned-carts.mjs --apply    # delete rows untouched > 180 days (cookie maxAge)
MAX_AGE_DAYS=90 ...                                                 # override threshold — see the script's footgun note
```

The script is deliberately not wired into any request path — a hot-path scan
would couple checkout latency to table size.

## 10. Verification checklist

```bash
npm run lint && npm run typecheck && npm run typecheck:tests   # 0 problems (app + tests + configs)
npm test                                                      # Vitest: 110 unit tests, 17 files
npm run build                                                 # cold build succeeds
BASE_URL=http://127.0.0.1:3100 scripts/smoke.sh               # 21 HTTP checks (server must be running)
npx playwright install chromium                               # once per environment
npm run test:e2e                                              # 53 e2e against the production build on :3100 (incl. the axe a11y sweeps — npx playwright install chromium first)
curl -s http://127.0.0.1:3000/api/health                      # {"ok":true} when the DB answers (SELECT 1)
curl -s http://127.0.0.1:3000/sitemap.xml | grep -c "<url>"   # 274
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/no-such-page   # 404
curl -s "http://127.0.0.1:3000/api/search?q=billy" | head -c 200              # live suggestions
```

Track-order probe body: `{"orderNo":"IKSG-0123456789","email":"…"}`
(uppercase `IKSG-`, 10 digits). A wrong email and a nonexistent order
return the same generic 404 — enumeration-safe by design.

The smoke script requires a loopback `BASE_URL`: it exercises the 403
foreign-origin CSRF gate, 415/413 body gates, quantity clamping at 99,
cross-session order isolation, and track right/wrong email. A production
server on plain HTTP without `x-forwarded-proto: https` will refuse its own
`Secure` cookie jar.

## 11. Common production issues

| Symptom | Cause | Fix |
|---|---|---|
| Build fails `CssSyntaxError: Missed semicolon` at a huge CSS offset | Prose leaked into the Tailwind scanner — a class-shaped arbitrary value in a scanned root file | Check the `@source not` guard in `src/app/globals.css` covers every root file (root targets need the `../../` prefix; `docker-compose.yml` is guarded since session 006), then `rm -rf .next` |
| `DATABASE_URL is required` at import/build time | `.env` missing or a shell env shadows it | `cp .env.example .env`; `env \| grep DATABASE_URL` |
| App reads the wrong DB but `db:push` acts on the right one | `drizzle.config.json` doesn't read `.env` (§5 drift trap) | Keep both in lockstep |
| Cart always empty on plain-HTTP production | `Secure` cookie refused without HTTPS | Serve HTTPS or terminate TLS at a proxy that forwards `x-forwarded-proto: https` |
| Everything rate-limits to 429 quickly behind a proxy | Proxy trust not declared | `TRUSTED_PROXY_DEPTH=1` (or your hop count) |
| Sitemap/robots show the old origin after an env change | They are build-time prerendered | Rebuild with `NEXT_PUBLIC_SITE_URL` set |
| e2e fails on pages you didn't touch | Stale `:3100` server | Restart the production server before re-running |

## 12. Pushing changes to this repository

No hosted CI — the local gate (§10) is the only gate. Run it green, commit
to `main` (no feature branches), then push with the SSH wrapper so the
deploy key never touches the tree:

```bash
# key -> a 0600 file OUTSIDE the repo (e.g. /tmp/deploy.key)
python3 docs/ssh_git_wrapper_v3.py --key-file /tmp/deploy.key \
  --remote git@github.com:nordeim/nordhem-furnishing-store.git
```

**The `--remote` override is mandatory**: the wrapper's default remote is a
stale `nordeim/ely-beauty` (its line 104 predates this repo). The wrapper
verifies the remote ref equals local HEAD after the push and shreds its temp
key copy; shred your key file afterwards. Full instructions:
`docs/how-to-git-push-using-ssh-wrapper_SKILL.md` (for sandboxes without an
OpenSSH binary it also documents the paramiko `ssh` shim to put on `PATH`).
`.gitignore` rejects `.env`, `*.key` and `ssh-key.txt`.
