"""Smoke test for ShelterPulse -- auto-detects running services, validates health + functionality.

Usage:
    uv run python scripts/smoke_test.py                              # full test suite (local)
    uv run python scripts/smoke_test.py --quick                      # health checks only (< 5s)
    uv run python scripts/smoke_test.py --url=https://example.com    # test remote deployment
"""
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

# --- Config ---
CONSOLIDATED_PORT = 8080  # Mode D: app target (nginx + uvicorn)
API_PORT = 8000           # Mode A/B/C: standalone API
UI_PORT = 3000            # Mode A/B/C: standalone UI

UI_ROUTES = ["/en", "/en/demo", "/en/how-it-works", "/en/simulate"]

_BUILDER_BODY = {
    "duration_days": 30, "housing_capacity": 20, "isolation_slots": 5,
    "vet_tech_fte": 1.5, "intervention_budget": 5000, "mean_intake_per_day": 3.8,
    "kitten_fraction": 0.59, "base_adoption_rate": 0.08, "n_replications": 8,
}

# Endpoints checked here are all fast (a few seconds at most). /optimize/builder
# is synchronous too but intentionally excluded: a full BO sweep takes ~30s+,
# which defeats a smoke test; tests/e2e/test_duckdb_consent.py exercises it.
API_FUNCTIONAL: list[tuple[str, str, Callable[[object], bool], dict | None]] = [
    ("GET", "/health", lambda d: d["status"] == "ok", None),
    ("GET", "/baselines", lambda d: len(d) == 5, None),
    ("POST", "/simulate", lambda d: "mean_overflow_cat_days" in d, {"seed": 42}),
    # Note: an empty {} body is falsy in Python, so http()'s `if body else None`
    # would silently send no body at all (FastAPI then 422s on a missing
    # request body) - always pass a non-empty dict even when every field has
    # a default, mirroring the existing /simulate check below.
    ("POST", "/sensitivity", lambda d: len(d) == 6, {"seed": 42}),
    ("POST", "/simulate/timeline", lambda d: len(d) > 0 and all("day" in p and "housing_used" in p and "overflow" in p for p in d), {"seed": 42}),
    ("POST", "/simulate/builder", lambda d: "mean_overflow_cat_days" in d, _BUILDER_BODY),
    ("POST", "/sensitivity/builder", lambda d: len(d) == 6, _BUILDER_BODY),
    ("POST", "/simulate/timeline/builder", lambda d: len(d) == 30, _BUILDER_BODY),
    ("POST", "/simulate/timeline/builder/compare", lambda d: len(d["before"]) == 30 and len(d["after"]) == 30, _BUILDER_BODY),
    ("POST", "/optimize/builder/compare", lambda d: "winner" in d and len(d["baselines"]) == 5, _BUILDER_BODY),
    ("GET", "/runs/recent", lambda d: isinstance(d, list), None),
    ("GET", "/runs/analytics", lambda d: isinstance(d, dict), None),
]
API_OPTIMIZE = ("POST", "/optimize", lambda d: len(d) >= 1)

# These run multiple simulation evaluations per request (6 perturbations for
# sensitivity, a full baseline+BO comparison for optimize/builder/compare) and
# measured 70-75s against live prod - well past the 30s default, independent
# of the ALB's own idle timeout (which only bounds the server side).
_SLOW_PATHS = {"/sensitivity", "/sensitivity/builder", "/optimize/builder/compare"}
EXPORT_CHECK = ("POST", "/export", {"n_candidates": 4, "n_replications": 8, "use_bo": False})


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


def http(method: str, url: str, body: dict | None = None, timeout: int = 30) -> tuple[int, object]:
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


def check_export(base: str, method: str, path: str, body: dict, results: Results, *, timeout: int = 60) -> None:
    """Verify /export returns a non-trivial ZIP. Binary response - can't reuse http()'s JSON decode."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{base}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read()
        is_zip = content[:2] == b"PK"  # ZIP local file header magic bytes
        if resp.status == 200 and is_zip and len(content) > 100:
            results.ok(f"API {method} {path}")
        else:
            results.fail(f"API {method} {path}", f"status={resp.status} zip={is_zip} size={len(content)}")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        results.fail(f"API {method} {path}", str(e))


# --- Main ---
def main() -> int:
    quick = "--quick" in sys.argv
    results = Results()

    # Check for explicit --url flag (for CD pipeline use)
    remote_url: str | None = None
    for arg in sys.argv[1:]:
        if arg.startswith("--url="):
            remote_url = arg.split("=", 1)[1].rstrip("/")
            break

    if remote_url:
        print(f"\033[36mTarget: {remote_url}\033[0m")
        api_base = f"{remote_url}/api"
        ui_base = remote_url
    else:
        # Auto-detect local services
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
        for method, path, validator, body in API_FUNCTIONAL:
            timeout = 120 if path in _SLOW_PATHS else 30
            check_api(api_base, method, path, validator, results, body=body, timeout=timeout)

        print("\n[API Optimize (slow)]")
        check_api(
            api_base, "POST", "/optimize",
            lambda d: len(d) >= 1,
            results,
            body={"n_candidates": 4, "n_replications": 8, "use_bo": False},
            timeout=60,
        )

        print("\n[API Export]")
        check_export(api_base, *EXPORT_CHECK, results)

    return results.summary()


if __name__ == "__main__":
    sys.exit(main())
