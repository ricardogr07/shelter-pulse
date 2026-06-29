# NOTE: this directory is still named `app-runner` (and the tfstate backend key is
# "app-runner/...") for state continuity. App Runner is dead (closed to new customers —
# see ADR-011). This module now provisions the ECR repo + the two IAM roles that ECS
# Express Mode requires. The Express service itself is created/updated via the AWS CLI
# (see deploy.yml), because its Terraform resource needs AWS provider v6 and this repo
# is pinned to v5.

terraform {
  required_version = ">= 1.5"

  backend "s3" {
    key = "app-runner/terraform.tfstate"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  default = "us-east-1"
}

# ECR repository for the consolidated container image (UI + API in one image)
resource "aws_ecr_repository" "app" {
  name                 = "shelterpulse"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Lifecycle policy — keep last 10 tagged images, expire untagged after 1 day
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

# --- ECS Express Mode IAM roles ---
# Express Mode requires two roles; AWS-managed policies provide the permissions.
#   1. Task execution role  — ECS pulls the image from ECR + writes CloudWatch logs.
#   2. Infrastructure role  — ECS provisions the ALB / networking on our behalf.
# Both ARNs are passed to `aws ecs create-express-gateway-service`.

resource "aws_iam_role" "ecs_task_execution" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_express_infra" {
  name = "ecsInfrastructureRoleForExpressServices"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowAccessInfrastructureForECSExpressServices"
      Effect    = "Allow"
      Principal = { Service = "ecs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_express_infra" {
  role       = aws_iam_role.ecs_express_infra.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "ECR repo URL for docker push"
}

output "ecs_task_execution_role_arn" {
  value       = aws_iam_role.ecs_task_execution.arn
  description = "Pass to: aws ecs create-express-gateway-service --execution-role-arn"
}

output "ecs_express_infra_role_arn" {
  value       = aws_iam_role.ecs_express_infra.arn
  description = "Pass to: aws ecs create-express-gateway-service --infrastructure-role-arn"
}
