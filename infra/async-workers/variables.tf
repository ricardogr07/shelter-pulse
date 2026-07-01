variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID where Lambda and EFS will be placed"
  type        = string
  default     = "vpc-0a169e0f5391fdcf6"
}

variable "subnet_ids" {
  description = "Subnet IDs for Lambda VPC config and EFS mount targets"
  type        = list(string)
  default = [
    "subnet-08f1845b1289b4a14",
    "subnet-0221413ae56333974",
    "subnet-0775cba9efa9422cb",
    "subnet-026c08f41dd140924",
    "subnet-0d2186c2d2fa9b097",
    "subnet-0dd5e346a1083feef"
  ]
}

variable "api_url" {
  description = "Base URL of the API for webhook callbacks (ECS Express Mode ALB URL)"
  type        = string
  default     = "https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws"
}

variable "internal_key" {
  description = "Shared secret for internal webhook authentication (X-Internal-Key header)"
  type        = string
  sensitive   = true
}
