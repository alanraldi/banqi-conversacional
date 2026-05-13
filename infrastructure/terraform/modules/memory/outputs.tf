output "memory_id" {
  description = "ID do AgentCore Memory store"
  value       = aws_bedrockagentcore_memory.this.id
}

output "memory_arn" {
  description = "ARN do AgentCore Memory store"
  value       = aws_bedrockagentcore_memory.this.arn
}
