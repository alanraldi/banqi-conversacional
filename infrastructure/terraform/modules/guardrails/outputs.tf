output "guardrail_id" {
  description = "ID do Bedrock Guardrail"
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_arn" {
  description = "ARN do Bedrock Guardrail"
  value       = aws_bedrock_guardrail.this.guardrail_arn
}
