# Worker: Terraform

**Model:** Claude Sonnet 4.6 | **Effort:** medium

**Role:** Manage `infra/` directory. Terraform plan/apply for AWS infrastructure.

## Files You Own

- `infra/app-runner/main.tf`
- `infra/async-workers/main.tf`
- `infra/dns/main.tf`
- `infra/bootstrap/main.tf`
- `infra/github-oidc/main.tf`

Forbidden: `.terraform/` dirs, `*.tfstate`, `*.tfstate.backup` (gitignored, never commit).
Forbidden zones: source code, ui/, .github/workflows/

## Current Modules

| Module | Path | Purpose |
|--------|------|---------|
| bootstrap | infra/bootstrap/ | S3 state bucket + DynamoDB lock table |
| github-oidc | infra/github-oidc/ | GitHub Actions → AWS IAM role (no static credentials) |
| app-runner | infra/app-runner/ | ECR repo (`app` image) + IAM roles for ECS. Named `app-runner` from an earlier decision (see below); actually provisions ECS Express Mode resources, not App Runner. |
| async-workers | infra/async-workers/ | SQS queue + DLQ, Lambda worker ECR repo, EFS (DuckDB persistence), Lambda/ECS IAM roles, NAT Gateway for Lambda VPC egress |
| dns | infra/dns/ | Custom domain (shelter-pulse.com): ACM cert, Route 53 validation + alias records, attaches cert to the Express Mode ALB listener |

**Note on the `app-runner` naming:** an early deployment attempt used AWS App Runner; that
approach hit a permanent account-level limitation (new AWS accounts can no longer subscribe
to App Runner) and the project moved to ECS Express Mode instead. The Terraform module kept
the `app-runner` directory name rather than a disruptive rename mid-build. If you're touching
this module and have a natural opportunity to rename it to something like `ecs-app`, that's a
welcome cleanup -- just coordinate with Director since it touches CI/CD paths.

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
