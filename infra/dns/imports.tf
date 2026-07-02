# Import the existing Express Mode listener rule into Terraform state.
# This rule was created by ECS Express Mode at priority 1.
# After import, we manage its host-header condition (adding shelter-pulse.com)
# while letting Express Mode continue to manage the action (TG weights).

import {
  to = aws_lb_listener_rule.express
  id = "arn:aws:elasticloadbalancing:us-east-1:612962922955:listener-rule/app/ecs-express-gateway-alb-7e687b2f/e3184b0b6175fbf1/fcc8252bdd1f4803/499dc81bf4b2100c"
}
