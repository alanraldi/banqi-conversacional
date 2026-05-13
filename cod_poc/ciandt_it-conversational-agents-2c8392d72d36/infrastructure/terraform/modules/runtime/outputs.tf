output "runtime_arn" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "runtime_id" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
}

output "endpoint_arn" {
  value = aws_bedrockagentcore_agent_runtime_endpoint.this.agent_runtime_endpoint_arn
}

output "ecr_repository_url" {
  value = aws_ecr_repository.runtime.repository_url
}

