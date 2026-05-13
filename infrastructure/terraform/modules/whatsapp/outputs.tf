output "lambda_function_name" {
  description = "Nome da função Lambda do canal WhatsApp"
  value       = aws_lambda_function.whatsapp.function_name
}

output "api_gateway_url" {
  description = "URL base do API Gateway"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "webhook_url" {
  description = "URL completa do webhook para configurar no Meta Developer Portal"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/webhook"
}

output "dedup_table_name" {
  description = "Nome da tabela DynamoDB de deduplicação"
  value       = aws_dynamodb_table.dedup.name
}
