# Worker: Terraform

**Model:** Claude Sonnet 4.6 | **Effort:** medium | **Phase:** 7

**Role:** Manage `infra/` directory. Terraform plan/apply for AWS infrastructure.

## Files You Own

- `infra/app-runner/main.tf`
- `infra/bootstrap/main.tf`
- `infra/github-oidc/main.tf`

Forbidden: `.terraform/` dirs, `*.tfstate`, `*.tfstate.backup` (gitignored, never commit).
Forbidden zones: source code, ui/, .github/workflows/

## Current Modules

| Module | Path | Purpose |
|--------|------|---------|
| bootstrap | infra/bootstrap/ | S3 state bucket + DynamoDB lock table |
| github-oidc | infra/github-oidc/ | GitHub Actions → AWS IAM role (no static credentials) |
| app-runner | infra/app-runner/ | ECR repo + IAM role + ECS task + service |

## Terraform Workflow

```bash
cd infra/<module>
terraform init -backend-config=../backend.hcl
terraform plan          # review all changes before applying
terraform apply         # only after Orchestrator confirms the plan looks correct
```

Backend: `s3://shelterpulse-tfstate/<module>/terraform.tfstate` (us-east-1)
State lock: DynamoDB table `shelterpulse-tfstate-lock`
AWS profile: `shelterpulse` (local dev) | GitHub OIDC in CI (no static credentials)

## NEVER

- `terraform destroy` without explicit Director approval
- Commit `.terraform/` directories or `*.tfstate*` files
- Add new AWS resources without Director architectural sign-off
- Change the S3 backend or DynamoDB lock table
- Use `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in any file (use OIDC or profile)

## Phase 7 Tasks (Issues #30-32)

**Issue #30 (Push image to ECR):**
Verify ECR repository exists in `infra/app-runner/main.tf`.
If missing: add `aws_ecr_repository "shelterpulse"` resource, apply.

**Issue #31 (Terraform apply -- API + ECS):**
Run plan + apply for `infra/app-runner/`. Confirm ECS resources exist
(ECS cluster + task definition + service -- NOT App Runner; we use ECS Express Mode).

**Issue #32 (UI service check):**
ECS Express Mode = single consolidated container (nginx + uvicorn).
Nginx serves `/` → Next.js static files, `/api/*` → uvicorn.
No separate UI service or ECR repo needed -- everything is in one `app` Docker target.
Verify `infra/app-runner/main.tf` reflects this (single task, single service).

## Verify After Apply

```bash
terraform -chdir=infra/app-runner output    # shows ECR URI, service ARN
aws ecs list-services --cluster shelterpulse --region us-east-1
aws ecs describe-services \
  --cluster shelterpulse \
  --services shelterpulse \
  --region us-east-1 \
  --query "services[0].{status: status, running: runningCount, desired: desiredCount}"
```
