# Shared S3 backend config — used by all modules via:
#   terraform init -backend-config=../backend.hcl
#
# Each module sets its own `key` in its backend block, e.g.:
#   terraform { backend "s3" { key = "github-oidc/terraform.tfstate" } }

bucket         = "shelterpulse-tfstate"
dynamodb_table = "shelterpulse-tflock"
region         = "us-east-1"
encrypt        = true
