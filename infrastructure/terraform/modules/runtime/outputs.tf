output "runtime_arn" {
  description = "ARN do AgentCore Runtime"
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "runtime_endpoint" {
  description = "URL do endpoint do AgentCore Runtime"
  value       = aws_bedrockagentcore_agent_runtime_endpoint.this.endpoint_url
}

output "ecr_repository_url" {
  description = "URL do repositório ECR"
  value       = aws_ecr_repository.runtime.repository_url
}
