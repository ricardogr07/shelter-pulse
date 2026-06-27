terraform {
  required_version = ">= 1.5"

  backend "s3" {
    key = "github-oidc/terraform.tfstate"
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

variable "github_repo" {
  default = "ricardogr07/shelter-pulse"
}

# OIDC provider — GitHub's token issuer
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}

# IAM role that GitHub Actions assumes
resource "aws_iam_role" "github_actions" {
  name = "shelterpulse-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

# Policy: ECR push/pull + App Runner management
resource "aws_iam_role_policy" "deploy" {
  name = "shelterpulse-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECR"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:DescribeRepositories",
          "ecr:CreateRepository"
        ]
        Resource = "*"
      },
      {
        Sid    = "AppRunner"
        Effect = "Allow"
        Action = [
          "apprunner:CreateService",
          "apprunner:UpdateService",
          "apprunner:DescribeService",
          "apprunner:ListServices",
          "apprunner:StartDeployment",
          "apprunner:ListOperations",
          "apprunner:TagResource",
          "apprunner:CreateAutoScalingConfiguration",
          "apprunner:DescribeAutoScalingConfiguration"
        ]
        Resource = "*"
      },
      {
        Sid    = "AppRunnerECRAccess"
        Effect = "Allow"
        Action = [
          "iam:PassRole",
          "iam:CreateServiceLinkedRole"
        ]
        Resource = "*"
      }
    ]
  })
}

output "role_arn" {
  value       = aws_iam_role.github_actions.arn
  description = "Add this as GitHub secret AWS_ROLE_ARN"
}
