output "runtime_role_arn" {
  description = "ARN da IAM Role para o AgentCore Runtime"
  value       = aws_iam_role.runtime.arn
}

output "lambda_role_arn" {
  description = "ARN da IAM Role para a Lambda WhatsApp"
  value       = aws_iam_role.lambda.arn
}

output "gateway_role_arn" {
  description = "ARN da IAM Role para o AgentCore Gateway"
  value       = aws_iam_role.gateway.arn
}
