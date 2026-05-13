output "guardrail_id" {
  description = "Bedrock Guardrail ID"
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_arn" {
  description = "Bedrock Guardrail ARN"
  value       = aws_bedrock_guardrail.this.guardrail_arn
}

output "guardrail_version" {
  description = "Bedrock Guardrail version"
  value       = aws_bedrock_guardrail.this.version
}
