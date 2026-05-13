output "vpc_id" {
  value = local.vpc_id
}

output "private_subnet_ids" {
  value = local.private_subnet_ids
}

output "security_group_ids" {
  value = {
    runtime   = aws_security_group.runtime.id
    endpoints = aws_security_group.endpoints.id
    lambda    = aws_security_group.lambda.id
  }
}

output "waf_acl_arn" {
  value = aws_wafv2_web_acl.this.arn
}

output "aoss_vpce_id" {
  value = aws_vpc_endpoint.aoss.id
}

output "network_mode" {
  description = "Whether VPC resources are available (for runtime network_configuration)"
  value       = "VPC"
}
