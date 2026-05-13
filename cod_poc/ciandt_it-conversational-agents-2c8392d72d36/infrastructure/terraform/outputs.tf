output "runtime_arn" {
  description = "AgentCore Runtime ARN"
  value       = module.runtime.runtime_arn
}

output "memory_id" {
  description = "AgentCore Memory ID"
  value       = module.memory.memory_id
}

output "gateway_arn" {
  description = "AgentCore Gateway ARN"
  value       = module.gateway.gateway_arn
}

output "ecr_uri" {
  description = "ECR repository URI for runtime container"
  value       = module.runtime.ecr_repository_url
}

output "iam_role_arns" {
  description = "IAM role ARNs"
  value = {
    runtime = module.iam.runtime_role_arn
    lambda  = module.iam.lambda_role_arn
    gateway = module.iam.gateway_role_arn
  }
}

output "guardrail_id" {
  description = "Bedrock Guardrail ID"
  value       = module.guardrails.guardrail_id
}

output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID (empty if KB not enabled)"
  value       = length(module.knowledge_base) > 0 ? module.knowledge_base[0].knowledge_base_id : ""
}

output "knowledge_base_s3_bucket" {
  description = "S3 bucket for KB documents"
  value       = length(module.knowledge_base) > 0 ? module.knowledge_base[0].s3_bucket_name : ""
}

output "whatsapp_webhook_url" {
  description = "WhatsApp Webhook URL (empty if WhatsApp not enabled)"
  value       = length(module.whatsapp) > 0 ? module.whatsapp[0].webhook_url : ""
}

output "gateway_oauth_config" {
  description = "OAuth credentials for GatewayTokenManager (null when AWS_IAM)"
  value       = module.gateway.oauth_config
  sensitive   = true
}