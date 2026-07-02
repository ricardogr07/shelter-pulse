# Custom domain configuration for ShelterPulse ECS Express Mode service.
#
# This module:
# 1. Requests an ACM certificate for shelter-pulse.com + *.shelter-pulse.com
# 2. Validates the certificate via Route 53 DNS records
# 3. Looks up the ECS Express Mode ALB and HTTPS listener
# 4. Attaches the certificate to the listener
# 5. Imports and modifies the Express Mode listener rule to accept the custom
#    domain hostname (preserving Express Mode's blue/green target group management)
# 6. Creates a www -> apex 301 redirect rule
# 7. Creates Route 53 A alias records pointing to the ALB
#
# Express Mode manages the priority-1 rule's forward action (blue/green TG weights).
# We only modify its host-header condition to include shelter-pulse.com.
# The action block is ignored via lifecycle to avoid conflicts with Express Mode.

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

variable "alb_name" {
  default     = "ecs-express-gateway-alb-7e687b2f"
  description = "Name of the ALB created by ECS Express Mode"
}

variable "express_rule_arn" {
  default     = "arn:aws:elasticloadbalancing:us-east-1:612962922955:listener-rule/app/ecs-express-gateway-alb-7e687b2f/e3184b0b6175fbf1/fcc8252bdd1f4803/499dc81bf4b2100c"
  description = "ARN of the Express Mode listener rule (priority 1) to import"
}

variable "active_target_group_arn" {
  default     = "arn:aws:elasticloadbalancing:us-east-1:612962922955:targetgroup/ecs-gateway-tg-d1c3da90bbdc3cd46/d0a494038785db97"
  description = "ARN of the currently active target group (used in imported rule action)"
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
# ALB + Listener (data sources - managed by ECS Express Mode)
# ---------------------------------------------------------------------------

data "aws_lb" "express" {
  name = var.alb_name
}

data "aws_lb_listener" "https" {
  load_balancer_arn = data.aws_lb.express.arn
  port              = 443
}

# ---------------------------------------------------------------------------
# HTTP listener - redirect all traffic to HTTPS
# ---------------------------------------------------------------------------

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = data.aws_lb.express.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = {
    Project = "shelterpulse"
  }
}

# ---------------------------------------------------------------------------
# Attach custom certificate to the HTTPS listener
# ---------------------------------------------------------------------------

resource "aws_lb_listener_certificate" "custom_domain" {
  listener_arn    = data.aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate_validation.main.certificate_arn
}

# ---------------------------------------------------------------------------
# Express Mode Listener Rule (imported)
#
# Express Mode creates this rule at priority 1 with the .on.aws hostname.
# We import it into state and add shelter-pulse.com to the host-header
# condition. Express Mode manages the action (blue/green TG weights),
# so we ignore_changes on action to avoid conflicts.
# ---------------------------------------------------------------------------

resource "aws_lb_listener_rule" "express" {
  listener_arn = data.aws_lb_listener.https.arn
  priority     = 1

  condition {
    host_header {
      values = [
        var.domain_name,
        "sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws"
      ]
    }
  }

  action {
    type             = "forward"
    target_group_arn = var.active_target_group_arn
  }

  tags = {
    AmazonECSManaged = "true"
  }

  lifecycle {
    ignore_changes = [action]
  }
}

# ---------------------------------------------------------------------------
# www redirect rule
# ---------------------------------------------------------------------------

resource "aws_lb_listener_rule" "www_redirect" {
  listener_arn = data.aws_lb_listener.https.arn
  priority     = 20

  condition {
    host_header {
      values = ["www.${var.domain_name}"]
    }
  }

  action {
    type = "redirect"

    redirect {
      host        = var.domain_name
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ---------------------------------------------------------------------------
# Route 53 Alias Records
# ---------------------------------------------------------------------------

# A record for apex domain -> ALB
resource "aws_route53_record" "apex" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = data.aws_lb.express.dns_name
    zone_id                = data.aws_lb.express.zone_id
    evaluate_target_health = true
  }
}

# A record for www -> ALB (so the redirect rule can fire)
resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = data.aws_lb.express.dns_name
    zone_id                = data.aws_lb.express.zone_id
    evaluate_target_health = true
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "certificate_arn" {
  value       = aws_acm_certificate.main.arn
  description = "ACM certificate ARN"
}

output "alb_dns_name" {
  value       = data.aws_lb.express.dns_name
  description = "ALB DNS name (for reference)"
}

output "app_url" {
  value       = "https://${var.domain_name}"
  description = "Production URL"
}
