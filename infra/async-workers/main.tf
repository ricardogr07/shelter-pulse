# Async workers infrastructure: SQS FIFO queue, Lambda worker, EFS persistence, ECR repo.
# All resources stay within AWS Free Tier ($0/month for expected usage).
#
# Apply: cd infra/async-workers && terraform init -backend-config=../backend.hcl && terraform apply

terraform {
  required_version = ">= 1.5"

  backend "s3" {
    key = "async-workers/terraform.tfstate"
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

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# --- Networking (lookup existing VPC resources) ---

data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }

  filter {
    name   = "subnet-id"
    values = var.subnet_ids
  }
}

# --- SQS FIFO Queue ---

resource "aws_sqs_queue" "jobs_dlq" {
  name                        = "shelterpulse-jobs-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  message_retention_seconds   = 1209600 # 14 days
  sqs_managed_sse_enabled     = true    # SSE-SQS, AWS-managed key, no KMS to provision/pay for

  tags = {
    Project = "shelterpulse"
    Purpose = "dead-letter-queue"
  }
}

resource "aws_sqs_queue" "jobs" {
  name                        = "shelterpulse-jobs.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 300   # 5 min (Lambda timeout + buffer)
  message_retention_seconds   = 86400 # 1 day
  receive_wait_time_seconds   = 20    # long polling
  sqs_managed_sse_enabled     = true  # SSE-SQS, AWS-managed key, no KMS to provision/pay for

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Project = "shelterpulse"
    Purpose = "optimization-jobs"
  }
}

# --- ECR Repository for Worker Image ---

resource "aws_ecr_repository" "worker" {
  name                 = "shelterpulse-worker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Project = "shelterpulse"
    Purpose = "lambda-worker-image"
  }
}

resource "aws_ecr_lifecycle_policy" "worker" {
  repository = aws_ecr_repository.worker.name

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
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = { type = "expire" }
      }
    ]
  })
}

# --- EFS File System (DuckDB persistence) ---

resource "aws_efs_file_system" "data" {
  creation_token = "shelterpulse-data"
  encrypted      = true

  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  lifecycle_policy {
    transition_to_ia = "AFTER_14_DAYS"
  }

  tags = {
    Name    = "shelterpulse-data"
    Project = "shelterpulse"
    Purpose = "duckdb-persistence"
  }
}

resource "aws_efs_access_point" "shelterpulse" {
  file_system_id = aws_efs_file_system.data.id

  posix_user {
    uid = 1000
    gid = 1000
  }

  root_directory {
    path = "/shelterpulse"
    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "755"
    }
  }

  tags = {
    Name    = "shelterpulse-ap"
    Project = "shelterpulse"
  }
}

# Security group for Lambda + EFS communication
resource "aws_security_group" "lambda" {
  name        = "shelterpulse-lambda-sg"
  description = "Security group for Lambda worker - allows outbound + NFS to EFS"
  vpc_id      = var.vpc_id

  # Outbound: all (Lambda needs internet for webhook to API)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "shelterpulse-lambda-sg"
    Project = "shelterpulse"
  }
}

resource "aws_security_group" "efs" {
  name        = "shelterpulse-efs-sg"
  description = "Security group for EFS - allows NFS from Lambda"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "NFS from Lambda"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "shelterpulse-efs-sg"
    Project = "shelterpulse"
  }
}

# Mount targets - one per subnet so Lambda can reach EFS
resource "aws_efs_mount_target" "data" {
  for_each = toset(var.subnet_ids)

  file_system_id  = aws_efs_file_system.data.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

# --- IAM Role for Lambda ---

resource "aws_iam_role" "lambda_worker" {
  name = "shelterpulse-lambda-worker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project = "shelterpulse"
  }
}

# Basic execution (CloudWatch logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access (ENI management for VPC-attached Lambda)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# SQS consume + EFS mount
resource "aws_iam_role_policy" "lambda_app" {
  name = "shelterpulse-lambda-app"
  role = aws_iam_role.lambda_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.jobs.arn,
          aws_sqs_queue.jobs_dlq.arn
        ]
      },
      {
        Sid    = "EFSMount"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:DescribeMountTargets"
        ]
        Resource = aws_efs_file_system.data.arn
      }
    ]
  })
}

# --- IAM Role for ECS Task (API side - publishes jobs to SQS) ---
# Express Mode never assigned a task role, so the API container has no AWS
# credentials for boto3. Attach via `--task-role-arn` on the Express service.

resource "aws_iam_role" "ecs_task" {
  name = "shelterpulse-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Project = "shelterpulse"
  }
}

resource "aws_iam_role_policy" "ecs_task_sqs" {
  name = "shelterpulse-ecs-task-sqs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SQSPublish"
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.jobs.arn
      }
    ]
  })
}

# --- Lambda internet egress (NAT Gateway) ---
# Lambda needs both the VPC/EFS attachment (DuckDB) and internet access (webhook
# callback) at once - Lambda ENIs never get public IPs, so a NAT Gateway is the
# only way to give a VPC-attached Lambda outbound internet access. Dedicated
# subnets + route table here so this never touches the subnets/routing that
# ECS Express Mode and the ALB depend on (see ADR-010).
#
# TEMPORARY for the hackathon judging window: built 2026-07-02, intended to be
# torn down (terraform destroy -target on these resources, or revert this
# block) after judging concludes ~2026-07-15. ~$32-35/month while running.

resource "aws_subnet" "lambda_a" {
  vpc_id            = var.vpc_id
  cidr_block        = "172.31.96.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name    = "shelterpulse-lambda-egress-a"
    Project = "shelterpulse"
    Purpose = "lambda-nat-egress-temporary"
  }
}

resource "aws_subnet" "lambda_b" {
  vpc_id            = var.vpc_id
  cidr_block        = "172.31.97.0/24"
  availability_zone = "us-east-1b"

  tags = {
    Name    = "shelterpulse-lambda-egress-b"
    Project = "shelterpulse"
    Purpose = "lambda-nat-egress-temporary"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name    = "shelterpulse-lambda-nat"
    Project = "shelterpulse"
    Purpose = "lambda-nat-egress-temporary"
  }
}

# Placed in an existing public subnet (already has the default VPC's IGW route)
# so it doesn't touch ECS/ALB's routing at all - only the two new subnets above
# route through it.
resource "aws_nat_gateway" "lambda" {
  allocation_id = aws_eip.nat.id
  subnet_id     = var.subnet_ids[0] # us-east-1a public subnet

  tags = {
    Name    = "shelterpulse-lambda-nat"
    Project = "shelterpulse"
    Purpose = "lambda-nat-egress-temporary"
  }
}

resource "aws_route_table" "lambda_egress" {
  vpc_id = var.vpc_id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.lambda.id
  }

  tags = {
    Name    = "shelterpulse-lambda-egress"
    Project = "shelterpulse"
    Purpose = "lambda-nat-egress-temporary"
  }
}

resource "aws_route_table_association" "lambda_a" {
  subnet_id      = aws_subnet.lambda_a.id
  route_table_id = aws_route_table.lambda_egress.id
}

resource "aws_route_table_association" "lambda_b" {
  subnet_id      = aws_subnet.lambda_b.id
  route_table_id = aws_route_table.lambda_egress.id
}

# --- Lambda Function ---

resource "aws_lambda_function" "worker" {
  function_name = "shelterpulse-worker"
  role          = aws_iam_role.lambda_worker.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.worker.repository_url}:latest"
  timeout       = 240  # 4 min (sweep is ~30s, buffer for cold start + EFS)
  memory_size   = 1024 # 1 GB (BO + SimPy need headroom)

  vpc_config {
    # Dedicated NAT-routed subnets (see above), not var.subnet_ids - those are
    # ECS/ALB's public subnets and have no route back for Lambda's private-only
    # ENIs. EFS mount targets stay in var.subnet_ids; VPC-local routing reaches
    # them fine regardless of which subnet Lambda's ENI lands in.
    subnet_ids         = [aws_subnet.lambda_a.id, aws_subnet.lambda_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  file_system_config {
    arn              = aws_efs_access_point.shelterpulse.arn
    local_mount_path = "/mnt/efs"
  }

  environment {
    variables = {
      API_URL      = var.api_url
      INTERNAL_KEY = var.internal_key
      DUCKDB_PATH  = "/mnt/efs/shelterpulse.duckdb"
    }
  }

  # Don't fail on initial apply before the image is pushed
  lifecycle {
    ignore_changes = [image_uri]
  }

  depends_on = [
    aws_efs_mount_target.data,
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy.lambda_app
  ]

  tags = {
    Project = "shelterpulse"
    Purpose = "bo-sweep-worker"
  }
}

# --- SQS -> Lambda Event Source Mapping ---

resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.jobs.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1 # One job per invocation (each sweep is heavy)
  enabled          = true

  scaling_config {
    maximum_concurrency = 5 # Limit parallel sweeps
  }
}
