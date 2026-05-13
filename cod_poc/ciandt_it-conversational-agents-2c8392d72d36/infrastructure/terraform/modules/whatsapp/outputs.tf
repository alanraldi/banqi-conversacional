output "webhook_url" {
  description = "WhatsApp Webhook URL (configure in Meta Developer Console)"
  value       = "${aws_apigatewayv2_api.whatsapp.api_endpoint}/${var.environment}/webhook"
}

output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.whatsapp.function_name
}

output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.whatsapp.arn
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.whatsapp.id
}

output "dedup_table_name" {
  description = "DynamoDB dedup table name"
  value       = aws_dynamodb_table.dedup.name
}

output "secret_arn" {
  description = "Secrets Manager ARN for WhatsApp credentials"
  value       = aws_secretsmanager_secret.whatsapp.arn
}