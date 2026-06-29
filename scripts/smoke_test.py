"""Smoke test for ShelterPulse -- auto-detects running services, validates health + functionality.

Usage:
    uv run python scripts/smoke_test.py          # full test suite
    uv run python scripts/smoke_test.py --quick  # health checks only (< 5s)
"""
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

# --- Config ---
CONSOLIDATED_PORT = 8080  # Mode D: app target (nginx + uvicorn)
API_PORT = 8000           # Mode A/B/C: standalone API
UI_PORT = 3000            # Mode A/B/C: standalone UI

UI_ROUTES = ["/en", "/en/demo", "/en/how-it-works", "/en/simulate"]
API_FUNCTIONAL = [
    ("GET", "/health", lambda d: d["status"] == "ok"),
    ("GET", "/baselines", lambda d: len(d) == 5),
    ("POST", "/simulate", lambda d: "mean_overflow_cat_days" in d, {"seed": 42}),
]
API_OPTIMIZE = ("POST", "/optimize", lambda d: len(d) >= 1)


# --- Helpers ---
@dataclass
class Results:
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        print(f"  \033[32mPASS\033[0m {msg}")

    def fail(self, msg: str, detail: str = "") -> None:
        self.failed.append(msg)
        extra = f" ({detail})" if detail else ""
        print(f"  \033[31mFAIL\033[0m {msg}{extra}")

    def summary(self) -> int:
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*50}")
        print(f"  \033[{'32' if not self.failed else '31'}m{len(self.passed)}/{total} passed\033[0m")
        if self.failed:
            print(f"  Failed: {', '.join(self.failed)}")
        return 0 if not self.failed else 1


def probe(port: int) -> bool:
    """Check if a port is responding to HTTP."""
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=2)
        return True
    except urllib.error.HTTPError:
        return True  # got a response (404 etc), port is alive
    except (urllib.error.URLError, OSError):
        return False


def http(method: str, url: str, body: dict | None = None, timeout: int = 30) -> tuple[int, any]:
    """Make an HTTP request, return (status_code, parsed_json_or_None)."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read().decode()
        try:
            return resp.status, json.loads(content)
        except json.JSONDecodeError:
            return resp.status, content
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e)


def check_page(url: str, results: Results) -> None:
    """Verify a page returns 200 and contains ShelterPulse."""
    status, body = http("GET", url)
    route = url.split(":", 2)[-1].split("/", 1)[-1] or "/"
    if status == 200:
        results.ok(f"UI {route} -> 200")
    else:
        results.fail(f"UI {route}", f"status={status}")


def check_api(base: str, method: str, path: str, validator, results: Results, *, body: dict | None = None, timeout: int = 30) -> None:
    """Verify an API endpoint returns 200 and passes validation."""
    payload = body if body else ({} if method == "POST" else None)
    status, data = http(method, f"{base}{path}", payload, timeout=timeout)
    if status == 200 and data is not None and validator(data):
        results.ok(f"API {method} {path}")
    else:
        results.fail(f"API {method} {path}", f"status={status}")


# --- Main ---
def main() -> int:
    quick = "--quick" in sys.argv
    results = Results()

    # Auto-detect
    consolidated = probe(CONSOLIDATED_PORT)
    api_up = probe(API_PORT)
    ui_up = probe(UI_PORT)

    if not consolidated and not api_up and not ui_up:
        print("\033[31mNo services detected.\033[0m")
        print("Start one of:")
        print("  docker compose up              (API:8000 + UI:3000)")
        print("  docker run -p 8080:8080 ...    (consolidated:8080)")
        print("  uv run uvicorn ...             (API:8000)")
        return 1

    # Report detected mode
    if consolidated:
        print(f"\033[36mDetected: consolidated container on :{CONSOLIDATED_PORT}\033[0m")
        api_base = f"http://localhost:{CONSOLIDATED_PORT}/api"
        ui_base = f"http://localhost:{CONSOLIDATED_PORT}"
    else:
        parts = []
        if api_up:
            parts.append(f"API:{API_PORT}")
        if ui_up:
            parts.append(f"UI:{UI_PORT}")
        print(f"\033[36mDetected: {' + '.join(parts)}\033[0m")
        api_base = f"http://localhost:{API_PORT}" if api_up else None
        ui_base = f"http://localhost:{UI_PORT}" if ui_up else None

    # --- Quick checks ---
    print("\n[Health Checks]")
    if api_base:
        check_api(api_base, "GET", "/health", lambda d: d.get("status") == "ok", results)
    if ui_base:
        check_page(f"{ui_base}/en", results)

    if quick:
        return results.summary()

    # --- Full checks ---
    if ui_base:
        print("\n[UI Routes]")
        for route in UI_ROUTES:
            check_page(f"{ui_base}{route}", results)

    if api_base:
        print("\n[API Functional]")
        for item in API_FUNCTIONAL:
            method, path, validator = item[0], item[1], item[2]
            body = item[3] if len(item) > 3 else None
            check_api(api_base, method, path, validator, results, body=body)

        print("\n[API Optimize (slow)]")
        check_api(
            api_base, "POST", "/optimize",
            lambda d: len(d) >= 1,
            results,
            body={"n_candidates": 4, "n_replications": 8, "use_bo": False},
            timeout=60,
        )

    return results.summary()


if __name__ == "__main__":
    sys.exit(main())
