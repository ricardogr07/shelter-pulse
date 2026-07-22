# ShelterPulse static cutover runbook

Goal: stop the always-on AWS cost (ECS Express = a 24/7 Fargate task + an ALB,
roughly USD 30 to 55 per month plus egress) by serving a free static showcase
on Cloudflare Pages at `shelter-pulse.com`. Credits are low; this brings the
monthly cost to about USD 0 to 2.

The static UI is already coded on branch `chore/static-showcase-cutover`
(env-gated by `NEXT_PUBLIC_STATIC_MODE`, so it is a no-op on the normal backend
build). The `/demo` wizard replays the recorded Whisker Haven sweep from
`ui/src/data/whisker-haven-sweep.json`; the custom builder shows a "run locally"
banner and refuses custom runs with a friendly message.

## Timing

Judging runs Fri Jul 17 and Sat Jul 18. Do NOT touch the live site or DNS until
judging is done. Execute Sun Jul 19 or Mon Jul 20 morning. The ECS stack stays
up until Cloudflare is verified serving the domain, so there is no downtime.

## Prereqs

- This branch checked out with the static-mode UI.
- Cloudflare account (free) and `wrangler` (`npm i -g wrangler`), or the CF dashboard.
- AWS CLI v2 + creds for teardown.
- Registrar access for `shelter-pulse.com` to change nameservers.

## Phase 1: build + deploy static to Cloudflare (no live impact yet)

    cd ui
    NEXT_PUBLIC_STATIC_MODE=1 npm ci && npm run build   # produces ui/out (14 pages)
    npx serve ui/out                                    # local smoke at http://localhost:3000/en

Verify locally:
- `/en` loads; `/en/demo` runs the wizard on canned data (baseline, optimize,
  compare, then Export downloads a CSV); the amber "Static showcase" banner shows;
  no console fetch errors.
- `/en/simulate` shows the banner; a custom run surfaces "Live compute is paused".

Deploy the prebuilt output:

    wrangler pages project create shelter-pulse --production-branch=main
    wrangler pages deploy ui/out --project-name=shelter-pulse   # gives a *.pages.dev URL

Verify the `*.pages.dev` preview the same way. (Alternative: connect the GitHub
repo in the CF dashboard with build command
`cd ui && NEXT_PUBLIC_STATIC_MODE=1 npm ci && npm run build`, output dir `ui/out`,
env `NEXT_PUBLIC_STATIC_MODE=1`.)

## Phase 2: point the domain at Cloudflare (the cutover)

1. Cloudflare: add site `shelter-pulse.com`. CF gives 2 nameservers and imports
   existing records. KEEP any MX/TXT (email); REMOVE the old ALB A/alias records.
2. CF Pages project, Custom domains: add `shelter-pulse.com` and
   `www.shelter-pulse.com`. CF provisions TLS and CNAME-flattens the apex.
3. Registrar: change the domain nameservers to the 2 Cloudflare ones. If the
   domain is at the Route53 Registrar: Route53 console, Registered domains,
   `shelter-pulse.com`, Edit name servers.
4. Wait for propagation (usually under 1 hour, up to 48). Verify, and keep the
   ECS stack UP until this passes:

       dig shelter-pulse.com +short
       curl -sI https://shelter-pulse.com/en | grep -i cf-ray

## Phase 3: tear down the always-on AWS (only after Phase 2 verifies)

Discover:

    SVC=$(gh variable get ECS_EXPRESS_SERVICE_ARN -R ricardogr07/shelter-pulse)
    aws ecs describe-services --services "$SVC"      # note cluster + the ALB it made
    aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName,'shelterpulse')]"

Delete (ECS Express is CLI-managed, mirroring deploy.yml's update verb):

    aws ecs delete-express-gateway-service --service-arn "$SVC"   # removes service + ALB + TGs + listeners
    # fallback if that verb is unavailable:
    #   aws ecs update-service --cluster <c> --service <s> --desired-count 0
    #   aws ecs delete-service --cluster <c> --service <s> --force
    #   then delete the ALB, target groups, and listeners via elbv2

Stop CI from recreating it, then remove the now-moot DNS module:

    gh variable set ECS_EXPRESS_SERVICE_ARN -R ricardogr07/shelter-pulse --body ""
    cd infra/dns && terraform destroy        # ACM cert + old Route53 alias records
    cd ../async-workers && terraform destroy  # optional: SQS + Lambda, idle ~0 but tidy

KEEP `infra/bootstrap` (TF state), `infra/github-oidc`, and `infra/app-runner`
(ECR + IAM roles) so live compute can be restored fast. Optional: empty the ECR
repo to zero storage.

## Phase 4: verify and fix references

- AWS: no running Fargate tasks, no ALB. Cost Explorer next day shows Fargate and
  ALB at 0.
- Portfolio (`ricardogr07.github.io` `src/content/projects.ts`): `docsUrl`
  `https://shelter-pulse.com/api/docs` now 404s (Swagger gone), remove it or point
  it at the repo. `liveUrl` `.../en` still works. Adjust the "Live at
  shelter-pulse.com" copy if desired.
- Close the board issue with Actual (your time) and Work-value.

## Rollback

- DNS: point the nameservers back to Route53 (or re-add the A/alias in whatever
  DNS is authoritative).
- Compute: the image is still in ECR. Recreate the ECS Express service, reset the
  `ECS_EXPRESS_SERVICE_ARN` var, and `terraform apply infra/dns`. About 15 to 30 minutes.

## Merge note

This branch is safe to merge any time (the static path only activates with
`NEXT_PUBLIC_STATIC_MODE=1`, which the ECS build never sets). It does not need to
be merged before the cutover; the Cloudflare build uses it directly.
