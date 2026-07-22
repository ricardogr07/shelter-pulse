# Custom domain configuration for the ShelterPulse static site.
#
# This module:
# 1. Requests an ACM certificate for shelter-pulse.com + *.shelter-pulse.com
#    (us-east-1, which is also what CloudFront requires)
# 2. Validates the certificate via Route 53 DNS records
# 3. Creates Route 53 A alias records pointing apex + www at the CloudFront
#    distribution that serves the static export from S3
#
# The distribution, S3 bucket, and CloudFront Function are hand-managed for
# now (see docs/static-cutover.md); codifying them as infra/static-site is the
# deferred Phase 4 of the backend retirement plan. The ALB listener/rule
# resources this module managed in the ECS era were removed when that stack
# was destroyed.

terraform {
  required_version = ">= 1.5"

  backend "s3" {
    key = "dns/terraform.tfstate"
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

variable "domain_name" {
  default = "shelter-pulse.com"
}

variable "cloudfront_distribution_id" {
  default     = "E3QGGSZBB1R96B"
  description = "CloudFront distribution serving the static site"
}

# ---------------------------------------------------------------------------
# ACM Certificate
# ---------------------------------------------------------------------------

resource "aws_acm_certificate" "main" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Project = "shelterpulse"
  }
}

# ---------------------------------------------------------------------------
# Route 53 Hosted Zone (data source - already exists)
# ---------------------------------------------------------------------------

data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# ---------------------------------------------------------------------------
# DNS Validation Records
# ---------------------------------------------------------------------------

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# ---------------------------------------------------------------------------
# CloudFront distribution (data source - hand-managed, see header comment)
# ---------------------------------------------------------------------------

data "aws_cloudfront_distribution" "site" {
  id = var.cloudfront_distribution_id
}

# ---------------------------------------------------------------------------
# Route 53 Alias Records
# ---------------------------------------------------------------------------

resource "aws_route53_record" "apex" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = data.aws_cloudfront_distribution.site.domain_name
    zone_id                = data.aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = data.aws_cloudfront_distribution.site.domain_name
    zone_id                = data.aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "certificate_arn" {
  value       = aws_acm_certificate.main.arn
  description = "ACM certificate ARN"
}

output "cloudfront_domain" {
  value       = data.aws_cloudfront_distribution.site.domain_name
  description = "CloudFront distribution domain the alias records point at"
}

output "app_url" {
  value       = "https://${var.domain_name}"
  description = "Production URL"
}
