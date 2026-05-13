output "private_subnet_ids" {
  description = "IDs das subnets privadas"
  value       = local.private_subnet_ids
}

output "security_group_ids" {
  description = "Map com IDs dos security groups: lambda, runtime, endpoints"
  value = {
    lambda    = aws_security_group.lambda.id
    runtime   = aws_security_group.runtime.id
    endpoints = aws_security_group.endpoints.id
  }
}

output "waf_acl_arn" {
  description = "ARN do WAF WebACL"
  value       = aws_wafv2_web_acl.this.arn
}

output "vpc_id" {
  description = "ID da VPC"
  value       = local.vpc_id
}

output "aoss_vpce_id" {
  description = "Placeholder para compatibilidade (AOSS não usado neste domínio)"
  value       = ""
}
