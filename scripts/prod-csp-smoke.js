// Production CSP hydration smoke (P16/FE-C1).
//
// The gate the dev-mode suite structurally cannot run: boots the REAL
// standalone production build and asserts that the nonce-based CSP lets
// Next.js hydrate. Pre-P16, every page shipped non-nonced inline bootstrap
// scripts under `script-src 'self'` — browsers blocked them and the
// production app was inert server HTML, while the whole test suite
// (running against `next dev`, whose CSP allows unsafe-inline) stayed
// green.
//
// Usage (from apps/web, after `npm run build:server`):
//   NODE_PATH=apps/web/node_modules node ../../scripts/prod-csp-smoke.js
//
// Checks:
//   1. the served Content-Security-Policy header carries a nonce
//   2. script-src has no 'unsafe-inline' in production
//   3. hydration happened — the Next client runtime booted (window.next)
//   4. zero CSP-violation console errors
//   5. (regression guard) the served page contains the app title

const { chromium } = require(
  require("path").join(__dirname, "..", "apps", "web", "node_modules", "@playwright", "test")
);
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const WEB_DIR = path.resolve(__dirname, "..", "apps", "web");
const PORT = process.env.SMOKE_PORT || 3111;
const BASE = `http://127.0.0.1:${PORT}`;

function waitForServer(url, timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const probe = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`server did not come up on ${url}`));
        } else {
          setTimeout(probe, 500);
        }
      });
    };
    probe();
  });
}

(async () => {
  const server = spawn("node", [".next/standalone/server.js"], {
    cwd: WEB_DIR,
    env: { ...process.env, PORT: String(PORT), NODE_ENV: "production" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const bootLog = [];
  server.stdout.on("data", (d) => bootLog.push(d.toString()));
  server.stderr.on("data", (d) => bootLog.push(d.toString()));

  const results = [];
  const check = (name, ok, detail = "") =>
    results.push({ name, ok, detail });

  let browser;
  try {
    await waitForServer(`${BASE}/login/`);
    browser = await chromium.launch();
    const page = await browser.newPage();
    const violations = [];
    page.on("console", (m) => {
      if (m.text().includes("Content Security Policy")) {
        violations.push(m.text().slice(0, 120));
      }
    });

    const response = await page.goto(`${BASE}/login/`, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });

    const csp = response.headers()["content-security-policy"] || "";
    check(
      "[prod-csp] served CSP carries a nonce",
      /'nonce-[A-Za-z0-9+/=]+'/.test(csp),
      csp.split(";")[1]?.trim().slice(0, 80) || "no CSP header"
    );
    check(
      "[prod-csp] script-src has no unsafe-inline in production",
      !/script-src[^;]*unsafe-inline/.test(csp),
      ""
    );

    // The hydration proof: the Next client runtime only exists if the
    // inline bootstrap scripts (nonce-gated) actually executed.
    const hydrated = await page
      .waitForFunction(() => {
        const w = window;
        return Boolean(
          w.next?.version || w.next?.router || w.__NEXT_F?.length > 0
        );
      }, null, { timeout: 20000 })
      .then(() => true)
      .catch(() => false);
    check("[prod-csp] hydration happened (window.next booted)", hydrated, "");

    check(
      "[prod-csp] zero CSP-violation console errors",
      violations.length === 0,
      violations.slice(0, 3).join(" | ")
    );

    const title = await page.title();
    check(
      "[prod-csp] the app shell rendered",
      /LedgerSG/.test(title),
      title
    );
  } catch (err) {
    check("[prod-csp] smoke ran", false, String(err).slice(0, 200));
  } finally {
    if (browser) await browser.close();
    server.kill("SIGTERM");
  }

  const failed = results.filter((r) => !r.ok);
  for (const r of results) {
    console.log(`${r.ok ? "PASS" : "FAIL"} ${r.name}${r.detail ? ` — ${r.detail}` : ""}`);
  }
  if (failed.length > 0) {
    if (bootLog.length) console.log("\n--- server boot log (tail) ---");
    console.log(bootLog.slice(-10).join("").slice(-1500));
    process.exit(1);
  }
  console.log(`\n${results.length}/${results.length} passed`);
})();
