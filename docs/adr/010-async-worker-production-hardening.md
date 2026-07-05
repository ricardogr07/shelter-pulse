# ADR-010: Async Worker Production Hardening

**Status:** Accepted (NAT Gateway is a temporary component, see Decision 5)
**Date:** 2026-07-02
**Decision makers:** Ricardo (project lead)

## Context

`POST /optimize/builder` in production was returning `429 Too many active jobs` even though nobody was actively using the site. Root-cause investigation surfaced a chain of independent, previously-undiscovered production gaps in the async worker pipeline (ADR-008), each masking the next:

1. `JobStore` had no expiry mechanism — a job stuck in `queued`/`running` forever (for any reason) permanently counted against `count_active_by_ip()`, eventually exhausting the 3-job-per-IP limit.
2. The consolidated Docker image (`api`/`app` Dockerfile stages) never installed the `aws` extra (`boto3`), so any request reaching `QUEUE_BACKEND=sqs` crashed with `ModuleNotFoundError` before it could publish to the queue at all.
3. The ECS task had no IAM task role (`taskRoleArn: null`) — even with `boto3` present, `sqs:SendMessage` failed with `NoCredentialsError`.
4. Lambda's `API_URL` env var still pointed at the old `.on.aws` Express Mode endpoint instead of `https://shelter-pulse.com`, and `INTERNAL_KEY` was empty on both Lambda and ECS (technically matching, but not a real secret).
5. Lambda is VPC-attached (required for its EFS/DuckDB mount) and the VPC has no NAT Gateway, so Lambda has no path to the public internet — its webhook callback times out regardless of (4) being fixed.

Each fix got the pipeline one step further (`500` → `500` with a different traceback → `202` + real SQS publish → Lambda picks up and runs the job → webhook times out), verified live at each step rather than assumed.

## Decisions

### 1. TTL sweep for stuck jobs (Accepted, implemented)

Added `JobStore.sweep_stale(ttl_seconds=300)`: fails any `queued`/`running` job whose `updated_at` is older than 5 minutes (`error: "Job timed out"`), notifies SSE subscribers so the UI shows an error instead of hanging, and purges `completed`/`failed` jobs older than 30 minutes to bound memory growth. Called lazily at the top of `create()` and `count_active_by_ip()` — no background task/timer needed, since the store already has no persistence across restarts.

This is a general safety net independent of *why* a worker never calls back (crash, bad auth, network partition, or the NAT Gateway gap below) — it converts "job hangs forever" into "job fails after 5 minutes," which is what actually unblocked the reported 429s.

### 2. Install `boto3` in the consolidated image (Accepted, implemented)

`Dockerfile`'s `api` stage now runs `uv sync ... --extra aws` alongside the existing `optimize`/`worker`/`store` extras. `lambda/Dockerfile` does not need this — `lambda/handler.py` calls the API via `urllib`, not boto3, and consumes SQS via the native Lambda event source mapping rather than a boto3 client.

### 3. ECS task IAM role for SQS publish (Accepted, implemented)

Added `aws_iam_role.ecs_task` (`shelterpulse-ecs-task`) + `aws_iam_role_policy.ecs_task_sqs` to `infra/async-workers/main.tf`, scoped to exactly `sqs:SendMessage` + `sqs:GetQueueAttributes` on `shelterpulse-jobs.fifo`. Attached to the running ECS Express service via `aws ecs update-express-gateway-service --task-role-arn ...` (imperative, since the Express service itself isn't Terraform-managed — see ADR-007).

### 4. Correct `API_URL` / `INTERNAL_KEY` (Accepted, implemented)

`terraform apply` on `infra/async-workers` (Lambda side) with `api_url = "https://shelter-pulse.com"` (already the module's documented default — the deployed function simply predated it) and a freshly generated 64-char `internal_key`. The same value was set on the ECS task definition's `INTERNAL_KEY` env var via the same `--cli-input-json` mechanism used for the task role, so both sides authenticate with a real shared secret instead of both being empty.

### 5. NAT Gateway for Lambda internet egress (Accepted, implemented, temporary)

Lambda genuinely needs both the VPC/EFS attachment (for `shelterpulse.store.save_run`/`log_consent`, which Lambda calls directly when a user consents to storage) **and** internet access (for the webhook callback) at the same time. Lambda ENIs never get public IPs regardless of subnet configuration, so a NAT Gateway (or NAT instance) is the only way to give a VPC-attached Lambda outbound internet access — there is no $0 workaround for this specific combination.

Lambda previously shared its six subnets with the ECS Express service, which relies on a direct Internet Gateway route (works for ECS because Fargate tasks get real public IPs; does not work as a return path for Lambda's private-IP-only ENIs, and can't simply be repointed at a NAT Gateway without risking the live site's own IGW-dependent inbound/outbound path). Built instead: two new dedicated subnets for Lambda only (`shelterpulse-lambda-egress-a`/`b`), a NAT Gateway (`shelterpulse-lambda-nat`) in one of the *existing* public subnets, and a new route table (`0.0.0.0/0 → NAT Gateway`) associated only with the two new subnets. `terraform plan` confirmed `0 to destroy` before applying — the existing ECS/ALB subnets and their route table were never touched.

**This is deliberately temporary**, at a real recurring cost of **~$32-35/month** (breaks this module's documented $0/month goal — see [design-decisions.md](../design-decisions.md#7-queue-abstraction-rabbitmq-local-sqslambda-prod)). Built 2026-07-02 to cover the hackathon judging window; intended teardown ~2026-07-15 once judging concludes (remove the new subnet/EIP/NAT-gateway/route-table resources from `infra/async-workers/main.tf`, revert Lambda's `vpc_config.subnet_ids` to `var.subnet_ids`, `terraform apply`).

### 6. `API_URL` needed the `/api` prefix (Accepted, implemented)

Once the NAT Gateway made Lambda's webhook request actually reach `shelter-pulse.com` (instead of timing out), it immediately 404'd — a different, previously-invisible bug. `deploy/nginx-app.conf` only proxies paths under `/api/*` to uvicorn; a bare-origin request (`https://shelter-pulse.com/internal/jobs/...`) falls into nginx's static-file location block, which has no matching route. Confirmed directly: `POST https://shelter-pulse.com/internal/jobs/test/progress` → `404` (nginx), `POST https://shelter-pulse.com/api/internal/jobs/test/progress` → `422` (reaches FastAPI). Fixed by changing `infra/async-workers/variables.tf`'s `api_url` default (and the applied value) from `https://shelter-pulse.com` to `https://shelter-pulse.com/api`.

This bug could not have been found without first fixing the NAT Gateway gap — Lambda's requests never got far enough to hit it before.

## Consequences

- The async pipeline is verified working end-to-end in production: a real `POST /optimize/builder` returned `202`, Lambda consumed the SQS message, ran the sweep, called back successfully, and `GET /optimize/{id}/results` returned real ranked `EvaluationOut` data.
- Any job that still fails for some other reason (crash, bad payload) times out after 5 minutes via `sweep_stale()` rather than hanging forever or exhausting the per-IP job limit — the original reported symptom (429s) is resolved independent of this specific fix chain.
- `docs/aws-async-infra.md` (previously stated "Status: NOT YET CREATED" for resources that had, in fact, all been created) was retired; its content is folded into [architecture/async-workers.md](../architecture/async-workers.md), which now also documents the current resource list, including the temporary NAT Gateway/subnets, so the two don't drift out of sync again.
- **Action item:** tear down the NAT Gateway + dedicated subnets after judging concludes (~2026-07-15) to stop the ~$32-35/month charge. See the teardown steps in Decision 5 above and the matching note in async-workers.md.

## Verification

Each fix was verified against live production state (not assumed from the diff) before moving to the next: `aws ecs describe-task-definition` / `aws lambda get-function-configuration` for config (using length-only queries for secret values, never printing them), a real `docker build` + boto3 import check before pushing, `aws ecs update-express-gateway-service --monitor-mode TEXT-ONLY` / `terraform apply` to confirm each rolling deployment and infra change landed as planned (`terraform plan` reviewed for `0 to destroy` before every apply touching shared resources), and a real `POST /optimize/builder` against `https://shelter-pulse.com` at each stage of the fix chain — culminating in a full `202 → running → completed` job with real optimization results returned through the webhook path.
