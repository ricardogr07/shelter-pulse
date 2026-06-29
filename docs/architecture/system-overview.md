# System Overview

ShelterPulse system context: who uses it and how the major pieces connect.

```mermaid
graph TB
    SM["Shelter Manager\n(browser)"] -->|HTTPS| UI["Next.js UI\nui/ -- static export"]
    Judge["Hackathon Judge"] -->|live URL or docker compose up| UI
    SM -->|terminal| CLI["Typer CLI\nshelterpulse/cli/main.py"]

    UI -->|HTTP /api/*| API["FastAPI\nshelterpulse/api/app.py"]
    API --> OPT["optimize/workflow.py\nsweep orchestrator"]
    API --> CORE["shelterpulse/core/\nengine - schema - interventions\nmontecarlo - export"]
    CLI --> OPT
    CLI --> CORE
    OPT --> IF["optimize/interface.py\nevaluate_candidate()"]
    IF --> CORE

    YAML["scenarios/whisker_haven.yaml\n(demo scenario)"] -->|load_scenario| CORE
    CORE --> SIMPY["SimPy DES\nnon-homogeneous Poisson\ncat lifecycle model"]

    API -. "TEMPORAL_ENABLED=False\n(flag-gated, arch-ready)" .-> TMP["Temporal\n(future)"]

    subgraph ECS ["AWS ECS Express Mode -- one ALB, one HTTPS URL"]
        NGINX["nginx :80\nserves Next.js static export\nproxies /api/* to :8000"]
        UV["uvicorn :8000\nFastAPI"]
        NGINX --> UV
    end

    UI -.->|"deployed as static export"| NGINX
    API -.->|"deployed"| UV
```

## Deployment note

The `app` Docker target (Dockerfile multi-stage) bundles the Next.js static export and the FastAPI server into one image. nginx serves static files at `:80` and reverse-proxies `/api/*` to uvicorn at `:8000` -- one container, one ALB, one HTTPS URL, no CORS. See [ADR-011](../adr/011-ecs-express-mode.md).
